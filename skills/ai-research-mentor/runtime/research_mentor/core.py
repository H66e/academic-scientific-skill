"""Acquisition-to-ledger use cases.  Provider observations mint their own receipts."""
from __future__ import annotations
import hashlib
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
import urllib.parse
import uuid

from .anchors import AnchorError, normalize_text, quote_text, sha256_text
from .contracts import Envelope, PACKAGE_VERSION
from .ledger import Ledger, LedgerError, canonical_json, digest, utc_now
from .privacy import PrivacyError, check_outbound
from .providers import ProviderError, normalize_identifier, search_url, resolve_url, arxiv_papers, crossref_papers
from .transport import Transport, TransportError, Response, checked_url

NOTICE = "Acquisition/anchoring checks do not prove faithful reading, coverage, novelty, or scientific correctness."

class _HtmlBlocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.parts, self.skip, self.section = [], [], 0, "unknown"
        self.current_kind = "paragraph"

    def flush(self):
        text = " ".join("".join(self.parts).split())
        self.parts = []
        if text:
            if self.current_kind == "heading":
                self.section = text
            self.blocks.append({"id": f"B-{len(self.blocks) + 1:04d}", "kind": self.current_kind,
                                "section": self.section, "text": text, "lossy": True})

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "math"}:
            self.skip += 1
        if not self.skip and tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "figcaption", "br"}:
            self.flush()
            self.current_kind = "heading" if tag.startswith("h") and tag[1:].isdigit() else "paragraph"

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg", "math"} and self.skip:
            self.skip -= 1
        if not self.skip and tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "figcaption"}:
            self.flush()
            self.current_kind = "paragraph"

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def parse_document(body: bytes, media_type: str) -> dict:
    if "pdf" in media_type or body.startswith(b"%PDF"):
        return {"text": "", "blocks": [], "extractor": "pdf-unextracted-v1",
                "limitations": ["PDF bytes acquired; no text extractor available. Host page/figure/equation review is required."],
                "needs_host_extraction": True}
    try:
        text = body.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ValueError("source is not UTF-8; explicit host conversion is required") from exc
    if "html" in media_type or text.lstrip().lower().startswith(("<!doctype html", "<html")):
        parser = _HtmlBlocks()
        parser.feed(text)
        parser.flush()
        blocks = parser.blocks
        text = "\n\n".join(block["text"] for block in blocks)
        return {"text": text, "blocks": blocks, "extractor": "html-stdlib-v1",
                "limitations": ["HTML extraction omits scripts, styles, SVG and MathML; inspect critical formulas, tables and figures in the source."],
                "needs_host_extraction": False}
    return {"text": text, "blocks": [{"id": "B-0001", "kind": "text", "section": "unknown", "text": text, "lossy": False}],
            "extractor": "text-utf8-v1", "limitations": [], "needs_host_extraction": False}

def verify_receipt(project: str | Path, receipt: dict) -> dict:
    errors = []
    root = Path(project).resolve()
    if not isinstance(receipt, dict):
        return {"valid": False, "errors": ["receipt must be an object"]}
    relative = receipt.get("artifact")
    if not isinstance(relative, str) or not relative:
        return {"valid": False, "errors": ["receipt has no raw artifact"]}
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return {"valid": False, "errors": ["receipt artifact escapes project"]}
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != receipt.get("raw_sha256"):
            errors.append("raw artifact hash mismatch")
        if len(raw) != receipt.get("bytes"):
            errors.append("raw artifact size mismatch")
    except OSError:
        errors.append("raw artifact is missing or unreadable")
    if receipt.get("generated_by") != "research-mentor-python-acquisition-v1":
        errors.append("unknown receipt generator")
    return {"valid": not errors, "errors": errors}

class ResearchCore:
    def __init__(self, project: str | Path, *, transport=None):
        self.ledger = Ledger(project)
        self.transport = transport or Transport()

    def _save(self, data: bytes, *, suffix: str = ".bin") -> str:
        identity = hashlib.sha256(data).hexdigest()
        path = self.ledger.project / "sources" / (identity + suffix)
        try:
            path.resolve().relative_to(self.ledger.project)
        except ValueError as exc:
            raise LedgerError("source output escapes project through a symbolic link") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != data:
                raise LedgerError("content-addressed artifact collision or corruption")
        else:
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        return path.relative_to(self.ledger.project).as_posix()

    def _receipt(self, response: Response, provider: str, request: dict) -> dict:
        receipt = response.receipt(provider)
        receipt.update({"artifact": self._save(response.body), "generated_by": "research-mentor-python-acquisition-v1", "request": request})
        return receipt

    def init(self) -> Envelope:
        verification = self.ledger.verify()
        if not verification["valid"]:
            return Envelope.failure("; ".join(verification["errors"]))
        if self.ledger.read():
            return Envelope.success({"project": str(self.ledger.project), "ledger": verification}, status="existing")
        event = self.ledger.append("project.init", {"project_id": "PROJECT-" + uuid.uuid4().hex[:16], "core_version": PACKAGE_VERSION})
        return Envelope.success({"project": str(self.ledger.project)}, ledger_events=[event["id"]], warnings=[NOTICE])

    def search(self, query: str, *, provider: str = "arxiv", sensitivity: str = "private",
               limit: int = 10, family: str = "unspecified", offline: bool = False) -> Envelope:
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            return Envelope.failure("query must contain 1-2000 characters")
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            return Envelope.failure("limit must be an integer from 1 to 100")
        data, executed = None, False
        try:
            url = search_url(provider, query, limit)
            data = {"id": "S-" + uuid.uuid4().hex[:16], "query": query, "provider": provider,
                    "family": family, "requested_params": {"limit": limit, "start": 0}, "limit": limit,
                    "result_paper_ids": [], "papers": [], "limitations": [], "executed": False}
            if offline:
                data.update(status="offline", stop_reason="offline_requested")
                event = self.ledger.append("search.result", data)
                return Envelope.success(data, status="offline", ledger_events=[event["id"]], warnings=["No external query was executed."])
            check_outbound(query, sensitivity=sensitivity)
            executed = True
            data["executed"] = True
            response = self.transport.get(url, allowed_hosts={urllib.parse.urlsplit(url).hostname}, trusted_provider=True)
            data["receipt"] = self._receipt(response, provider, {"operation": "search", "query": query, "limit": limit, "family": family})
            if response.status != 200:
                data.update(status="failed", stop_reason=f"http_{response.status}")
                event = self.ledger.append("search.result", data)
                return Envelope(False, "failed", data, errors=[f"provider returned HTTP {response.status}"], ledger_events=[event["id"]])
            papers, total = arxiv_papers(response.body) if provider == "arxiv" else crossref_papers(response.body)
            papers = list({paper["id"]: paper for paper in papers}.values())
            data.update(papers=papers, result_paper_ids=[paper["id"] for paper in papers], total_results=total)
            complete = total is not None and total <= len(papers)
            data.update(status="complete" if complete else "partial", stop_reason="provider_results_exhausted" if complete else "limit_or_parse_boundary")
            data["limitations"] = ["A provider result boundary is not field-wide coverage."]
            if not complete:
                data["limitations"].append("Search stopped at the requested result limit or an unconfirmed provider total; extend queries/providers as needed.")
            event = self.ledger.append("search.result", data)
            return Envelope.success(data, status=data["status"], ledger_events=[event["id"]], warnings=[NOTICE])
        except (PrivacyError, ProviderError, TransportError, OSError, ValueError) as exc:
            status = "blocked" if isinstance(exc, PrivacyError) else "failed"
            if data is not None and executed and not isinstance(exc, LedgerError):
                data.update(status="failed", stop_reason="request_or_parse_failure", limitations=[str(exc)])
                event = self.ledger.append("search.result", data)
                return Envelope(False, status, data, errors=[str(exc)], ledger_events=[event["id"]])
            return Envelope.failure(str(exc), status=status)

    def resolve(self, identifier: str, *, sensitivity: str = "public", offline: bool = False) -> Envelope:
        try:
            kind, identity = normalize_identifier(identifier)
            if offline:
                return Envelope.success({"identifiers": {kind: identity}, "status": "offline", "resolved": False}, status="offline")
            check_outbound(identifier, sensitivity=sensitivity)
            provider, url = resolve_url(kind, identity)
            response = self.transport.get(url, allowed_hosts={urllib.parse.urlsplit(url).hostname}, trusted_provider=True)
            receipt = self._receipt(response, provider, {"operation": "resolve", "identifier": identity, "kind": kind})
            if response.status != 200:
                return Envelope.failure(f"provider returned HTTP {response.status}", status="unresolved")
            papers, _ = arxiv_papers(response.body) if provider == "arxiv" else crossref_papers(response.body, resolve=True)
            matching = [paper for paper in papers if paper["identifiers"].get(kind) == identity or
                        (kind == "arxiv" and not re.search(r"v[1-9]\d*$", identity) and
                         re.sub(r"v[1-9]\d*$", "", paper["identifiers"].get(kind, "")) == identity)]
            if len(matching) != 1:
                return Envelope.failure("provider did not return exactly the requested identity/version", status="unresolved")
            data = dict(matching[0], status="resolved", receipt=receipt)
            event = self.ledger.append("paper.resolve", data)
            return Envelope.success(data, status="resolved", ledger_events=[event["id"]], warnings=[NOTICE])
        except (PrivacyError, ProviderError, TransportError, OSError, ValueError) as exc:
            return Envelope.failure(str(exc), status="blocked" if isinstance(exc, PrivacyError) else "unresolved")

    def fetch(self, *, local_path: str | Path | None = None, url: str | None = None, paper_id: str | None = None,
              identifier: str | None = None, sensitivity: str = "private", offline: bool = False) -> Envelope:
        try:
            if sum(value is not None for value in (local_path, url, identifier)) != 1:
                raise ValueError("provide exactly one local_path, URL or identifier")
            identity_binding = {"status": "unconfirmed", "paper_id": paper_id, "version": "unknown"}
            if local_path is not None:
                path = Path(local_path)
                if path.stat().st_size > 20 * 1024 * 1024:
                    raise ValueError("local source exceeds 20 MiB budget")
                body = path.read_bytes()
                media_type = "application/pdf" if path.suffix.lower() == ".pdf" else "text/html" if path.suffix.lower() in {".html", ".htm"} else "text/plain"
                response = Response("local:artifact", 200, {"content-type": media_type}, body, "local")
                receipt = self._receipt(response, "local", {"operation": "fetch", "origin": "local", "path_recorded": False})
                source_url = None
            else:
                if offline:
                    return Envelope.success({"status": "offline", "acquired": False}, status="offline")
                trusted_provider = False
                if identifier:
                    kind, identity = normalize_identifier(identifier)
                    if kind != "arxiv":
                        raise ValueError("automatic fulltext URL requires arXiv identity; for DOI use a public publisher URL")
                    url = "https://arxiv.org/html/" + urllib.parse.quote(identity, safe="/")
                    trusted_provider = True
                check_outbound(url, sensitivity=sensitivity)
                parsed = checked_url(url)
                response = self.transport.get(url, allowed_hosts={parsed.hostname}, trusted_provider=trusted_provider)
                if response.status != 200:
                    raise ValueError(f"fulltext returned HTTP {response.status}")
                media_type = response.headers.get("content-type", "application/octet-stream").split(";")[0].lower()
                receipt = self._receipt(response, "arxiv" if identifier else "public_url", {"operation": "fetch", "url": url})
                source_url = response.url
                if identifier and re.search(r"v[1-9]\d*$", identity) and source_url == url:
                    resolved = next((event for event in reversed(self.ledger.read()) if event["type"] == "paper.resolve"
                                     and event["data"].get("identifiers", {}).get("arxiv") == identity), None)
                    if resolved and paper_id in (None, resolved["data"]["id"]):
                        paper_id = resolved["data"]["id"]
                        identity_binding = {"status": "provider_url_bound", "paper_id": paper_id,
                                            "version": resolved["data"]["version"], "resolve_event": resolved["id"],
                                            "identifier": identity, "basis": "fixed_version_provider_resource_url"}
            ir = parse_document(response.body, media_type)
            text = ir["text"]
            ir["normalization"] = "NFC-whitespace-v1"
            ir_path = self._save(canonical_json(ir).encode("utf-8"), suffix=".ir.json")
            data = {"id": "SRC-" + receipt["raw_sha256"][:16], "paper_id": paper_id,
                    "source_identity": identity_binding,
                    "source_url": source_url, "media_type": media_type, "receipt": receipt,
                    "raw_sha256": receipt["raw_sha256"], "text_sha256": sha256_text(normalize_text(text)),
                    "ir_sha256": hashlib.sha256(canonical_json(ir).encode("utf-8")).hexdigest(),
                    "ir_path": ir_path, "extractor": ir["extractor"], "normalization": ir["normalization"],
                    "block_count": len(ir["blocks"]), "read_scope": "not_read", "needs_host_review": True,
                    "needs_host_extraction": ir["needs_host_extraction"], "limitations": ir["limitations"]}
            event = self.ledger.append("source.fetch", data)
            return Envelope.success(data, status="needs_host_extraction" if ir["needs_host_extraction"] else "acquired",
                                    ledger_events=[event["id"]], warnings=[NOTICE, *ir["limitations"]])
        except (PrivacyError, TransportError, OSError, ValueError) as exc:
            return Envelope.failure(str(exc), status="blocked" if isinstance(exc, PrivacyError) else "failed")

    def source(self, source_id: str) -> tuple[dict, dict]:
        if not self.ledger.verify()["valid"]:
            raise AnchorError("ledger hash chain is invalid")
        events = self.ledger.read()
        source = next((event for event in reversed(events) if event["type"] == "source.fetch" and
                       (event["data"].get("id") == source_id or event["id"] == source_id)), None)
        if not source:
            raise AnchorError("unknown acquired source ID")
        data = source["data"]
        if not isinstance(data.get("receipt"), dict) or data["receipt"].get("content_type") != data.get("media_type"):
            raise AnchorError("source media type does not match receipt")
        check = verify_receipt(self.ledger.project, data["receipt"])
        if not check["valid"]:
            raise AnchorError("source receipt failed: " + "; ".join(check["errors"]))
        path = (self.ledger.project / data["ir_path"]).resolve()
        path.relative_to(self.ledger.project)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != data["ir_sha256"]:
            raise AnchorError("source IR hash mismatch")
        ir = json.loads(raw)
        if sha256_text(normalize_text(ir["text"])) != data["text_sha256"]:
            raise AnchorError("source text hash mismatch")
        original = (self.ledger.project / data["receipt"]["artifact"]).read_bytes()
        observed = parse_document(original, data["media_type"])
        observed["normalization"] = "NFC-whitespace-v1"
        if observed != ir:
            raise AnchorError("source IR does not match extraction from raw artifact")
        return source, ir

    def quote(self, source_id: str, excerpt: str, *, locator: str = "", block_id: str | None = None) -> Envelope:
        try:
            if len(excerpt) > 20000:
                raise AnchorError("quote exceeds 20000 character budget")
            if not self.ledger.verify()["valid"]:
                raise AnchorError("ledger hash chain is invalid")
            source, ir = self.source(source_id)
            text = ir["text"]
            block = None
            if block_id:
                block = next((item for item in ir["blocks"] if item["id"] == block_id), None)
                if block is None:
                    raise AnchorError("unknown source block ID")
                text = block["text"]
            anchor = quote_text(source["data"]["id"], text, excerpt, locator=locator or (block_id or "text"))
            anchor.update(source_event=source["id"], source_ir_sha256=source["data"]["ir_sha256"],
                          read_scope="not_read", block_id=block_id, section=block["section"] if block else "unknown",
                          lossy=bool(block["lossy"]) if block else any(item["lossy"] for item in ir["blocks"]))
            anchor["id"] = "E-" + hashlib.sha256(canonical_json(anchor).encode("utf-8")).hexdigest()[:16]
            event = self.ledger.append("evidence.anchor", anchor)
            return Envelope.success(anchor, status="anchored", ledger_events=[event["id"]], warnings=[NOTICE])
        except (AnchorError, LedgerError, OSError, ValueError) as exc:
            return Envelope.failure(str(exc))

    def inspect_source(self, source_id: str) -> Envelope:
        try:
            source, ir = self.source(source_id)
            return Envelope.success({"source": source["data"], "document": ir}, status="parsed", warnings=["Delivery of source text does not record that it was read."])
        except (AnchorError, OSError, ValueError) as exc:
            return Envelope.failure(str(exc))

    def confirm_source_identity(self, source_id: str, paper_id: str, version: str, statement: str, *, human: bool = False) -> Envelope:
        """Record an explicit page/metadata check without authenticating a user."""
        try:
            if not human:
                raise ValueError("source identity confirmation requires explicit human confirmation")
            if not isinstance(statement, str) or not statement.strip() or not isinstance(version, str) or not version.strip():
                raise ValueError("version and identity-check statement are required")
            source, _ = self.source(source_id)
            resolved = next((event for event in reversed(self.ledger.read()) if event["type"] == "paper.resolve"
                             and event["data"].get("id") == paper_id), None)
            if not resolved:
                raise ValueError("source identity confirmation requires an acquired paper.resolve ID")
            if resolved["data"].get("version") not in {"unknown", version}:
                raise ValueError("confirmed version conflicts with acquired paper identity")
            data = {"source_id": source["data"]["id"], "source_event": source["id"], "paper_id": paper_id,
                    "version": version, "resolve_event": resolved["id"], "statement": statement,
                    "source_snapshot": digest(source["data"]), "status": "human_confirmed"}
            event = self.ledger.append("source.identity.confirm", data, actor="user", trust="T1")
            return Envelope.success(data, status="human_confirmed", ledger_events=[event["id"]],
                                    warnings=["This is a human declaration, not an identity authentication mechanism."])
        except (AnchorError, LedgerError, OSError, ValueError) as exc:
            return Envelope.failure(str(exc))

    def verify_artifacts(self) -> dict:
        errors, verified = [], 0
        chain = self.ledger.verify()
        if not chain["valid"]:
            return {"valid": False, "errors": chain["errors"], "receipts_verified": 0}
        for event in self.ledger.read():
            data = event["data"]
            receipt = data.get("receipt")
            if event["type"] in {"paper.resolve", "source.fetch"} and not receipt:
                errors.append(f"{event['id']}: acquisition event has no receipt")
            if event["type"] == "search.result" and data.get("status") in {"complete", "partial"} and not receipt:
                errors.append(f"{event['id']}: executed search has no receipt")
            if receipt:
                check = verify_receipt(self.ledger.project, receipt)
                if not check["valid"]:
                    errors.extend(f"{event['id']}: {error}" for error in check["errors"])
                else:
                    verified += 1
                    try:
                        self._verify_observation(event)
                    except (ProviderError, AnchorError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                        errors.append(f"{event['id']}: {exc}")
            if event["type"] == "source.fetch":
                try:
                    self.source(event["id"])
                except (AnchorError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                    errors.append(f"{event['id']}: {exc}")
            if event["type"] == "evidence.anchor":
                try:
                    source, ir = self.source(data["source_event"])
                    if source["data"]["id"] != data["source"] or source["data"]["ir_sha256"] != data["source_ir_sha256"]:
                        raise AnchorError("anchor is bound to the wrong source/version")
                    text, section, lossy = ir["text"], "unknown", any(item["lossy"] for item in ir["blocks"])
                    if data.get("block_id"):
                        block = next((item for item in ir["blocks"] if item["id"] == data["block_id"]), None)
                        if block is None:
                            raise AnchorError("anchor block does not exist")
                        text, section, lossy = block["text"], block["section"], block["lossy"]
                    expected = quote_text(data["source"], text, data["quote"], locator=data["locator"])
                    if any(data.get(key) != value for key, value in expected.items()) or data.get("section") != section or data.get("lossy") != lossy:
                        raise AnchorError("anchor quote/hash/offset does not match acquired source")
                    anchor_payload = {key: value for key, value in data.items() if key != "id"}
                    expected_id = "E-" + hashlib.sha256(canonical_json(anchor_payload).encode("utf-8")).hexdigest()[:16]
                    if data.get("id") != expected_id:
                        raise AnchorError("anchor identity does not match its payload")
                except (AnchorError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                    errors.append(f"{event['id']}: {exc}")
        return {"valid": not errors, "errors": errors, "receipts_verified": verified}

    def _verify_observation(self, event: dict) -> None:
        """Bind provider metadata and query intent to the preserved raw response."""
        data = event["data"]
        receipt = data["receipt"]
        if event["type"] == "source.fetch":
            identity = data.get("source_identity", {})
            if identity.get("status") == "provider_url_bound":
                resolved = self.ledger.get(identity["resolve_event"])
                if resolved["type"] != "paper.resolve" or resolved["data"].get("id") != identity.get("paper_id") or \
                   data.get("paper_id") != identity.get("paper_id") or resolved["data"].get("version") != identity.get("version") or \
                   resolved["data"].get("identifiers", {}).get("arxiv") != identity.get("identifier"):
                    raise ProviderError("provider source identity does not match resolved paper/version")
                expected_url = "https://arxiv.org/html/" + urllib.parse.quote(identity["identifier"], safe="/")
                if data.get("source_url") != expected_url or receipt.get("url") != expected_url or receipt.get("request", {}).get("url") != expected_url:
                    raise ProviderError("provider source identity does not match fetched resource URL")
            elif identity.get("status") != "unconfirmed":
                raise ProviderError("unknown source identity binding status")
            return
        if event["type"] not in {"paper.resolve", "search.result"}:
            return
        request = receipt.get("request", {})
        raw = (self.ledger.project / receipt["artifact"]).read_bytes()
        provider = data["provider"]
        if receipt.get("provider") != provider:
            raise ProviderError("receipt provider does not match event")
        if event["type"] == "search.result":
            if request.get("operation") != "search" or request.get("query") != data["query"] or request.get("limit") != data["limit"] or request.get("family") != data["family"]:
                raise ProviderError("search receipt parameters do not match query event")
            expected_url = search_url(provider, data["query"], data["limit"])
            if receipt.get("url") != expected_url:
                raise ProviderError("search receipt URL does not match provider query")
            if data["status"] not in {"complete", "partial"}:
                return
            papers, total = arxiv_papers(raw) if provider == "arxiv" else crossref_papers(raw)
            papers = list({paper["id"]: paper for paper in papers}.values())
            if data.get("papers") != papers or data.get("result_paper_ids") != [paper["id"] for paper in papers] or data.get("total_results") != total:
                raise ProviderError("search results do not match preserved provider response")
            complete = total is not None and total <= len(papers)
            if data["status"] != ("complete" if complete else "partial"):
                raise ProviderError("search completeness status does not match provider boundary")
        else:
            papers, _ = arxiv_papers(raw) if provider == "arxiv" else crossref_papers(raw, resolve=True)
            paper = next((item for item in papers if item["id"] == data.get("id")), None)
            if paper is None or any(data.get(key) != value for key, value in paper.items()):
                raise ProviderError("resolved metadata does not match preserved provider response")
            kind, identity = request.get("kind"), request.get("identifier")
            if request.get("operation") != "resolve" or not kind or not identity:
                raise ProviderError("resolution request missing from receipt")
            _, expected_url = resolve_url(kind, identity)
            if receipt.get("url") != expected_url:
                raise ProviderError("resolution receipt URL does not match requested identity")
