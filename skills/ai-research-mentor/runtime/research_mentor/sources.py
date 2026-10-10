"""Bounded native source acquisition with the retained dossier JSON contract.

Provider metadata and lossy HTML blocks are observations, never evidence of
reading or approval. Actual HTTPS uses the common pinned/TLS transport. Tests
can inject a transport, or synchronous fetch/lookup observations without DNS.
"""
from __future__ import annotations

import codecs
import hashlib
import ipaddress
import json
import math
import os
from pathlib import Path
import queue
import re
import stat
import threading
import time
import unicodedata
import urllib.parse
from datetime import datetime, timezone

from .privacy import check_outbound
from .transport import Transport, Response, checked_url
from .audit import _JS_SPACE

NOTICE = "Acquisition and identity checks only; source existence does not prove faithful reading, coverage, novelty, or scientific correctness."
_SPACE_PATTERN = "[" + re.escape(_JS_SPACE) + "]"


def _text(value):
    return isinstance(value, str) and bool(value.strip(_JS_SPACE))


def _collapse(value):
    return re.sub(_SPACE_PATTERN + "+", " ", value).strip(_JS_SPACE)


def _json(body):
    def invalid_constant(value):
        raise ValueError("Non-standard JSON constant: " + value)
    return json.loads(body.decode("utf-8", errors="replace"), parse_constant=invalid_constant)


def _html_charset(label):
    label = label.strip(" \t\n\r\f").lower()
    if label in ("utf-16", "utf16", "utf-16le"):
        return "utf-16-le"
    if label == "utf-16be":
        return "utf-16-be"
    codec = codecs.lookup(label).name
    # Reject Python-specific transformations unsupported by TextDecoder.
    overrides = {"ascii": "cp1252", "iso8859-1": "cp1252", "iso8859-9": "cp1254",
                 "iso8859-11": "cp874", "gb2312": "gbk", "shift_jis": "cp932", "euc_kr": "cp949"}
    allowed = {"utf-8", "utf-16-le", "utf-16-be", "big5", "gbk", "gb18030", "euc_jp", "iso2022_jp",
               "koi8-r", "koi8-u", "mac-roman", "mac-cyrillic", "cp866", "cp874", "cp932", "cp949",
               *(f"cp{value}" for value in range(1250, 1259)),
               *(f"iso8859-{value}" for value in (2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16))}
    codec = overrides.get(codec, codec)
    if codec not in allowed:
        raise LookupError("Unsupported browser charset")
    return codec


def _hash(value):
    if isinstance(value, str):
        value = value.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace").encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _now(dependencies):
    callback = dependencies.get("now")
    return callback() if callback else datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _integer(value, name, fallback, maximum):
    value = fallback if value is None else value
    try:
        number = float(value)
    except (ValueError, TypeError):
        number = math.nan
    if not math.isfinite(number) or not number.is_integer() or not 1 <= number <= maximum:
        raise ValueError(f"{name} must be an integer from 1 to {maximum}")
    return int(number)


def _options(options):
    result = dict(options or {})
    for key in tuple(result):
        camel = re.sub(r"_([a-z])", lambda m: m[1].upper(), key)
        if camel != key and camel not in result:
            result[camel] = result[key]
    return result


def normalize_doi(value):
    if not _text(value):
        raise ValueError("DOI required")
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.strip(_JS_SPACE), flags=re.I)
    doi = re.sub("^doi:" + _SPACE_PATTERN + "*", "", doi, flags=re.I)
    if not re.fullmatch(r"10\.[0-9]{4,9}/.+", doi, flags=re.I) or any(v in _JS_SPACE for v in doi) or re.search(r"[\x00-\x20<>]", doi) or len(doi.encode("utf-16-le", "surrogatepass")) // 2 > 512:
        raise ValueError("Invalid DOI syntax")
    return doi.lower()


def normalize_arxiv(value):
    if not _text(value):
        raise ValueError("arXiv ID required")
    identity = re.sub(r"^https?://(?:www\.)?arxiv\.org/(?:abs|pdf|html)/", "", value.strip(_JS_SPACE), flags=re.I)
    identity = re.sub("^arxiv:" + _SPACE_PATTERN + "*", "", identity, flags=re.I)
    identity = re.sub(r"\.pdf$", "", identity, flags=re.I)
    if not re.fullmatch(r"(?:[0-9]{4}\.[0-9]{4,5}|[a-z][a-z.\-]+/[0-9]{7})(?:v[1-9][0-9]*)?", identity, flags=re.I):
        raise ValueError("Invalid arXiv ID syntax")
    return identity


def is_public_address(address):
    # Preserve Node's conservative address contract, including documentation,
    # transition, shared and benchmark ranges across Python stdlib versions.
    if not isinstance(address, str) or "%" in address:
        return False
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    if parsed.version == 4:
        a, b, c, _ = map(int, str(parsed).split("."))
        return not (a in (0, 10, 127) or a >= 224 or a == 100 and 64 <= b <= 127 or
                    a == 169 and b == 254 or a == 172 and 16 <= b <= 31 or
                    a == 192 and (b == 168 or b == 0 and c in (0, 2) or b == 88 and c == 99) or
                    a == 198 and (b in (18, 19) or b == 51 and c == 100) or a == 203 and b == 0 and c == 113)
    expanded = parsed.exploded.lower().split(":")
    return expanded[0][0] in ("2", "3") and expanded[0] not in ("2002", "3ffe") and not \
        (expanded[0] == "2001" and (int(expanded[1], 16) <= 0x1ff or int(expanded[1], 16) == 0xdb8))


def _fixed_api(parsed):
    return parsed.hostname == "api.crossref.org" and (parsed.path == "/works" or re.fullmatch(r"/works/10\.\d{4,9}%2f.+", parsed.path, re.I)) or \
        parsed.hostname == "export.arxiv.org" and parsed.path == "/api/query"


def _bounded_call(callback, deadline):
    completed = queue.Queue(maxsize=1)

    def observe():
        try:
            completed.put((True, callback()))
        except Exception as exc:
            completed.put((False, exc))

    threading.Thread(target=observe, daemon=True).start()
    try:
        ok, value = completed.get(timeout=max(0.001, deadline - time.monotonic()))
    except queue.Empty as exc:
        raise ValueError("Request timeout") from exc
    if time.monotonic() >= deadline:
        raise ValueError("Request timeout")
    if not ok:
        raise value
    return value


class _InjectedTransport:
    """Protocol fixture adapter; production networking stays in Transport."""
    def __init__(self, options, dependencies, *, timeout, max_bytes, byte_budget, request_budget):
        self.options, self.dependencies = options, dependencies
        self.timeout, self.max_bytes = timeout, max_bytes
        self.byte_budget, self.request_budget = byte_budget, request_budget
        self.requests, self.bytes_received = [], 0

    def get(self, value, *, allowed_hosts, trusted_provider=False, trusted_resource=None):
        parsed = checked_url(value)
        for redirect in range(4):
            if parsed.hostname not in allowed_hosts:
                raise ValueError("Redirect outside explicitly permitted source host")
            trusted = self.options.get("trustedProviderTransport", False)
            if trusted and not (parsed.geturl() == trusted_resource if trusted_resource else _fixed_api(parsed)):
                raise ValueError("Trusted-provider transport is limited to fixed official API/resource paths")
            if trusted and os.environ.get("NODE_TLS_REJECT_UNAUTHORIZED") == "0":
                raise ValueError("Trusted-provider transport requires TLS certificate verification")
            if len(self.requests) >= self.request_budget:
                raise ValueError("Request budget exhausted")
            mode = "trusted_provider_tls" if trusted else "public_dns_pinned_tls"
            record = {"url": parsed.geturl(), "status": None, "bytes": 0, "transport_mode": mode}
            self.requests.append(record)
            deadline = time.monotonic() + self.timeout
            try:
                address = None
                if not trusted:
                    lookup = self.dependencies.get("lookup")
                    if lookup is None:
                        raise ValueError("Injected fetch requires an explicit injected DNS observation")
                    addresses = _bounded_call(lambda: lookup(parsed.hostname, {"all": True, "verbatim": True}), deadline)
                    if not isinstance(addresses, list) or not addresses or any(not isinstance(v, dict) or not is_public_address(v.get("address", "")) for v in addresses):
                        raise ValueError("Source resolves to a non-public or unsupported address")
                    address = addresses[0]
                response = _bounded_call(lambda: self.dependencies["fetch"](parsed.geturl(), {
                    "redirect": "manual", "address": address,
                    "headers": {"user-agent": "ai-research-mentor/0.3 (bounded research acquisition)",
                                "accept-encoding": "identity", "accept": "*/*"}}), deadline)
                status = response.status if hasattr(response, "status") else response["status"]
                raw_headers = response.headers if hasattr(response, "headers") else response.get("headers", {})
                headers = {str(k).lower(): str(v) for k, v in raw_headers.items()}
                record["status"] = status
                if status in (301, 302, 303, 307, 308):
                    location = headers.get("location")
                    if not location or redirect == 3:
                        raise ValueError("Missing redirect location or redirect budget exhausted")
                    parsed = checked_url(urllib.parse.urljoin(parsed.geturl(), location))
                    continue
                if status == 429:
                    raise ValueError(f"Rate limited (HTTP 429; Retry-After={headers.get('retry-after', 'unknown')}); no automatic retries")
                if not 200 <= status < 300:
                    return Response(parsed.geturl(), status, headers, b"", mode)
                try:
                    declared = float(headers.get("content-length", "0"))
                except ValueError:
                    declared = 0
                if declared > self.max_bytes or declared > self.byte_budget - self.bytes_received:
                    raise ValueError("Response exceeds byte budget")
                if headers.get("content-encoding", "identity") != "identity":
                    raise ValueError("Unexpected compressed response; extraction not attempted")
                body = response.body if hasattr(response, "body") else response.get("body")
                if body is None:
                    raise ValueError("Response body missing")
                if isinstance(body, str):
                    body = body.encode("utf-8")
                chunks = []
                if isinstance(body, bytes):
                    iterator = iter([body])
                elif hasattr(body, "read"):
                    iterator = iter(lambda: body.read(65536), b"")
                else:
                    iterator = iter(body)
                sentinel = object()
                while True:
                    chunk = _bounded_call(lambda: next(iterator, sentinel), deadline)
                    if chunk is sentinel:
                        break
                    if not isinstance(chunk, (bytes, bytearray, memoryview)):
                        raise ValueError("Response body must yield bytes")
                    chunk = bytes(chunk)
                    record["bytes"] += len(chunk)
                    self.bytes_received += len(chunk)
                    if record["bytes"] > self.max_bytes or self.bytes_received > self.byte_budget:
                        raise ValueError("Response exceeds byte budget")
                    chunks.append(chunk)
                body = b"".join(chunks)
                record["response_sha256"] = _hash(body)
                return Response(parsed.geturl(), status, headers, body, mode)
            except Exception as exc:
                record["error"] = str(exc)
                raise
        raise ValueError("Redirect budget exhausted")


class _Network:
    def __init__(self, options, dependencies, resource=None):
        self.options, self.dependencies, self.resource = options, dependencies, resource
        timeout = _integer(options.get("timeout"), "timeout", 15000, 60000) / 1000
        self.max_bytes = _integer(options.get("maxBytes"), "maxBytes", 2 * 1024 * 1024, 20 * 1024 * 1024)
        self.byte_budget = _integer(options.get("byteBudget"), "byteBudget", 10 * 1024 * 1024, 100 * 1024 * 1024)
        self.request_budget = _integer(options.get("requestBudget"), "requestBudget", 8, 20)
        arguments = {"timeout": timeout, "max_bytes": min(self.max_bytes, self.byte_budget), "byte_budget": self.byte_budget,
                     "request_budget": self.request_budget}
        self.transport = dependencies.get("transport")
        if self.transport is None:
            self.transport = _InjectedTransport(options, dependencies, **arguments) if "fetch" in dependencies else \
                Transport(**arguments, trusted_provider_transport=bool(options.get("trustedProviderTransport")))

    def get(self, url, hosts):
        arguments = {"allowed_hosts": set(hosts), "trusted_provider": bool(self.options.get("trustedProviderTransport"))}
        if self.resource:
            arguments["trusted_resource"] = self.resource
        response = self.transport.get(url, **arguments)
        if response.status == 429:
            raise ValueError(f"Rate limited (HTTP 429; Retry-After={response.headers.get('retry-after', 'unknown')}); no automatic retries")
        if 200 <= response.status < 300 and response.headers.get("content-encoding", "identity") != "identity":
            raise ValueError("Unexpected compressed response; extraction not attempted")
        if self.transport.requests and 200 <= response.status < 300:
            self.transport.requests[-1]["response_sha256"] = _hash(response.body)
        return response

    def summary(self):
        return {"requests": self.transport.requests, "bytes_received": self.transport.bytes_received,
                "byte_budget": self.byte_budget, "request_budget": self.request_budget}


def _crossref_paper(item, at):
    if not isinstance(item, dict):
        raise ValueError("DOI required")
    doi = normalize_doi(item.get("DOI"))
    titles = item.get("title")
    title = titles[0] if isinstance(titles, list) and titles else None
    if not _text(title):
        raise ValueError(f"Missing deposited title for DOI {doi}")
    date = None
    for key in ("published", "issued"):
        record = item.get(key)
        parts = record.get("date-parts") if isinstance(record, dict) else None
        if isinstance(parts, list) and parts:
            date = parts[0]
            break
    authors = item.get("author", [])
    if not isinstance(authors, list):
        raise ValueError("Crossref authors must be an array")
    names = []
    for author in authors:
        if not isinstance(author, dict):
            raise ValueError("Crossref author must be an object")
        name = " ".join(author[key] for key in ("given", "family") if _text(author.get(key)))
        if _text(name):
            names.append(name)
    score = item.get("score")
    deposited = item.get("deposited")
    return {"id": "doi-" + _hash(doi)[:24], "title": title.strip(_JS_SPACE),
            "year": int(date[0]) if isinstance(date, list) and date and type(date[0]) in (int, float) and math.isfinite(date[0]) and int(date[0]) == date[0] else None,
            "url": "https://doi.org/" + "/".join(urllib.parse.quote(segment, safe="~!*'()") for segment in doi.split("/")),
            "identifiers": {"doi": doi}, "version": "unknown", "accessed_at": at, "authors": names,
            "source_metadata": {"provider": "crossref", "type": item.get("type"),
                                "deposited_at": deposited.get("date-time") if isinstance(deposited, dict) else None,
                                "provider_relevance_score": score if type(score) in (int, float) and math.isfinite(score) else None},
            "version_note": "Registration metadata does not establish the technical version actually read."}


def search_crossref(options=None, dependencies=None):
    options, dependencies = _options(options), dependencies or {}
    query = options.get("query")
    if not _text(query):
        raise ValueError("query required")
    if len(query.encode("utf-16-le", "surrogatepass")) // 2 > 2000:
        raise ValueError("query exceeds 2000 characters")
    if "searchId" in options and (not _text(options["searchId"]) or re.search(r"[\x00-\x1f]", options["searchId"])):
        raise ValueError("searchId must be a nonempty ID")
    rows = _integer(options.get("rows"), "rows", 10, 100)
    pages = _integer(options.get("pages"), "pages", 1, 5)
    if options.get("offline"):
        return {"status": "offline", "planned_query": query, "searches": [], "papers": [],
                "transport": {"requests": [], "bytes_received": 0}, "notice": NOTICE}
    check_outbound(query, sensitivity=options.get("sensitivity", "private"))
    at = _now(dependencies)
    search = {"id": options.get("searchId", "search-crossref-" + _hash(at + ":" + query)[:16]),
              "query": query.strip(_JS_SPACE), "provider": "crossref", "searched_at": at, "status": "failed",
              "scope": f"Crossref deposited work metadata; bibliographic query ordered by provider relevance score descending; at most {pages} page(s) of {rows} records",
              "limitations": ["Crossref coverage is not exhaustive for AI preprints; metadata search is not full-text reading."],
              "result_paper_ids": []}
    papers, cursor, fetched, exhausted, malformed = {}, "*", 0, False, False
    network = _Network(options, dependencies)
    try:
        for page in range(pages):
            parameters = {"query.bibliographic": search["query"], "rows": str(rows), "cursor": cursor, "sort": "score", "order": "desc"}
            if options.get("mailto"):
                parameters["mailto"] = options["mailto"]
            url = "https://api.crossref.org/works?" + urllib.parse.urlencode(parameters, safe="*").replace("~", "%7E")
            if page:
                dependencies.get("pause", time.sleep)(1)
            response = network.get(url, {"api.crossref.org"})
            if response.status != 200:
                raise ValueError(f"Crossref HTTP {response.status}")
            payload = _json(response.body)
            message = payload.get("message") if isinstance(payload, dict) else None
            if not isinstance(payload, dict) or payload.get("status") != "ok" or not isinstance(message, dict) or not isinstance(message.get("items"), list):
                raise ValueError("Unexpected Crossref response")
            total = message.get("total-results")
            search["total_results_reported"] = total if type(total) in (int, float) and math.isfinite(total) else None
            for item in message["items"]:
                try:
                    paper = _crossref_paper(item, at)
                    papers[paper["id"]] = paper
                except (ValueError, TypeError) as exc:
                    malformed = True
                    search["limitations"].append("Skipped unidentifiable result: " + str(exc))
            fetched += 1
            exhausted = len(message["items"]) < rows or search["total_results_reported"] is not None and len(papers) >= search["total_results_reported"]
            if exhausted:
                break
            if not _text(message.get("next-cursor")) or message["next-cursor"] == cursor:
                search["limitations"].append("Pagination cursor missing or unchanged before coverage was exhausted.")
                break
            cursor = message["next-cursor"]
        search["status"] = "complete" if exhausted and not malformed else "partial"
        if not exhausted:
            search["limitations"].append("Returned results truncated by page/request budget or pagination boundary.")
    except Exception as exc:
        search["status"] = "partial" if fetched else "failed"
        search["limitations"].append(str(exc))
    search["result_paper_ids"], search["pages_received"] = list(papers), fetched
    return {"searches": [search], "papers": list(papers.values()), "transport": network.summary(), "notice": NOTICE}


def _decode_entities(value):
    named = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": " "}

    def replace(match):
        key = match[1]
        if not key.startswith("#"):
            return named.get(key.lower(), match[0])
        number = int(key[2:], 16) if key[1].lower() == "x" else int(key[1:])
        return chr(number) if 0 < number <= 0x10ffff and not 0xd800 <= number <= 0xdfff else match[0]

    return re.sub(r"&(#x[0-9a-f]+|#[0-9]+|amp|lt|gt|quot|apos|nbsp);", replace, value, flags=re.I)


def _xml_text(xml, tag):
    match = re.search("<" + tag + "(?:" + _SPACE_PATTERN + r"[^>]*)?>([\s\S]*?)</" + tag + ">", xml, re.I)
    return _decode_entities(_collapse(re.sub(r"<[^>]*>", " ", match[1]))) if match else ""


def verify_identifier(options=None, dependencies=None):
    options, dependencies = _options(options), dependencies or {}
    if bool(options.get("doi")) == bool(options.get("arxiv")):
        raise ValueError("Provide exactly one DOI or arXiv ID")
    if "expectTitle" in options and not _text(options["expectTitle"]):
        raise ValueError("expectTitle must be a nonempty string")
    if "expectYear" in options:
        _integer(options["expectYear"], "expectYear", None, 9999)
    kind = "doi" if options.get("doi") else "arxiv"
    identifier = normalize_doi(options["doi"]) if kind == "doi" else normalize_arxiv(options["arxiv"])
    result = {"kind": kind, "identifier": identifier, "checked_at": _now(dependencies), "status": "unresolved",
              "reason": "", "paper": None, "comparison": None, "notice": NOTICE}
    if options.get("offline"):
        return {**result, "status": "offline", "reason": "No network verification requested."}
    network, acquired = _Network(options, dependencies), False
    try:
        url = "https://api.crossref.org/works/" + urllib.parse.quote(identifier, safe="~!*'()") if kind == "doi" else \
            "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(identifier, safe="~!*'()")
        response = network.get(url, {"api.crossref.org" if kind == "doi" else "export.arxiv.org"})
        acquired = response.status == 200
        if response.status == 404:
            result["reason"] = "DOI not found in Crossref; it may belong to another registration agency." if kind == "doi" else "arXiv endpoint returned HTTP 404."
        elif response.status != 200:
            raise ValueError(f"Identity endpoint HTTP {response.status}")
        elif kind == "doi":
            payload = _json(response.body)
            if not isinstance(payload, dict) or payload.get("status") != "ok" or not payload.get("message"):
                raise ValueError("Unexpected Crossref identity response")
            result["paper"] = _crossref_paper(payload["message"], result["checked_at"])
            if result["paper"]["identifiers"]["doi"] != identifier:
                raise ValueError("Returned DOI differs from requested DOI")
            result["status"] = "resolved"
        else:
            xml = response.body.decode("utf-8", errors="replace")
            if re.search(r"<!DOCTYPE|<!ENTITY", xml, re.I) or not re.search(r"<feed\b", xml, re.I):
                raise ValueError("Unsupported or malformed Atom response")
            entry = re.search(r"<entry\b[^>]*>([\s\S]*?)</entry>", xml, re.I)
            if not entry:
                result["reason"] = "No matching entry reported by arXiv."
            else:
                entry = entry[1]
                returned_url, title = _xml_text(entry, "id"), _xml_text(entry, "title")
                if not re.match(r"^https?://arxiv\.org/abs/", returned_url, re.I) or not _text(title):
                    raise ValueError("arXiv returned an error or unidentifiable entry")
                resolved = normalize_arxiv(returned_url)
                base = re.sub(r"v\d+$", "", resolved)
                if base != re.sub(r"v\d+$", "", identifier) or re.search(r"v\d+$", identifier) and resolved != identifier:
                    raise ValueError("Returned arXiv identity/version differs from request")
                published, version = _xml_text(entry, "published"), re.search(r"v\d+$", resolved)
                result["paper"] = {"id": "arxiv-" + _hash(base)[:24], "title": title,
                                   "year": int(published[:4]) if re.match(r"\d{4}-\d\d-\d\dT", published) else None,
                                   "url": "https://arxiv.org/abs/" + resolved, "identifiers": {"arxiv": resolved},
                                   "version": "arXiv " + version[0] if version else "unknown", "accessed_at": result["checked_at"]}
                result["status"] = "resolved"
        if result["paper"]:
            title_key = lambda value: _collapse(unicodedata.normalize("NFC", value).lower())
            result["comparison"] = {
                "title": "not_checked" if "expectTitle" not in options else "match" if title_key(options["expectTitle"]) == title_key(result["paper"]["title"]) else "different",
                "year": "not_checked" if "expectYear" not in options else "unknown" if result["paper"]["year"] is None else "match" if int(options["expectYear"]) == result["paper"]["year"] else "different"}
            result["reason"] = "Identifier resolved; metadata comparisons require human review and do not verify source claims."
    except Exception as exc:
        result["status"], result["reason"], result["paper"] = "failed" if acquired else "unresolved", str(exc), None
    return {**result, "transport": network.summary()}


def extract_html(html, source_url):
    blocks, stack, current = [], [], None
    block_tags = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "figcaption", "td", "th"}
    skipped = {"script", "style", "template", "noscript"}
    void = {"br", "img", "hr", "meta", "link", "input", "wbr", "source", "area", "base", "embed", "param", "track", "col"}
    # Offsets intentionally use UTF-16 units for existing dossier consumers.
    offsets, units = [0], 0
    for character in html:
        units += 2 if ord(character) > 0xffff else 1
        offsets.append(units)

    def flush(end):
        nonlocal current
        if current is None:
            return
        text = _collapse(_decode_entities(current["text"]))
        if text:
            blocks.append({"kind": current["kind"], "text": text,
                           "locator": {"source_url": source_url, "html_id": current["anchor"],
                                       "start_offset": current["start"], "end_offset": end, "offset_unit": "UTF-16 code units"}})
        current["text"] = ""
        current = None

    for token in re.finditer(r'''<!--[\s\S]*?-->|<(?:[^"'<>]|"[^"]*"|'[^']*')+>|[^<]+|<''', html):
        raw, offset = token[0], offsets[token.start()]
        if raw.startswith("<!--"):
            continue
        match = re.match("<" + _SPACE_PATTERN + "*(/?)" + _SPACE_PATTERN + r"*([a-z][a-z0-9_:\-]*)\b", raw, re.I)
        if not match:
            if not any(item["tag"] in skipped for item in stack) and current is not None:
                current["text"] += " " + raw
            continue
        closing, tag = bool(match[1]), match[2].lower()
        if closing:
            indices = [index for index, item in enumerate(stack) if item["tag"] == tag]
            index = indices[-1] if indices else -1
            closes_block = current is not None and index >= 0 and any(item["frame"] is current for item in stack[index:])
            if closes_block:
                flush(offsets[token.end()])
            if index >= 0:
                del stack[index:]
            if closes_block:
                current = next((item["frame"] for item in reversed(stack) if item["frame"] is not None), None)
                if current is not None:
                    current["start"] = offsets[token.end()]
            continue
        identity = re.search(r"\bid" + _SPACE_PATTERN + "*=" + _SPACE_PATTERN +
                             r'''*(?:"([^"]*)"|'([^']*)'|([^''' + re.escape(_JS_SPACE) + r'''>]+))''', raw, re.I)
        anchor = _decode_entities(next(value for value in identity.groups() if value is not None)) if identity else \
            next((item["id"] for item in reversed(stack) if item["id"]), None)
        starts_block = not any(item["tag"] in skipped for item in stack) and tag in block_tags
        if starts_block:
            flush(offset)
            current = {"kind": tag, "anchor": anchor, "start": offset, "text": ""}
        if not re.search("/" + _SPACE_PATTERN + "*>$", raw) and tag not in void:
            stack.append({"tag": tag, "id": anchor if identity else None, "frame": current if starts_block else None})
    flush(offsets[-1])
    return blocks


def _safe_directory(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
        raise ValueError("Root/output parent path contains a symlink")
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError("Root/output parent path contains a non-directory")


def save_source_bytes(root, output, data):
    if not _text(root) or not _text(output) or Path(output).is_absolute() or re.match(r"^[a-z]:", output, re.I) or \
       re.search(r"(^|[\\/])\.\.?([\\/]|$)", output) or re.search(r"[\x00-\x1f:]", output):
        raise ValueError("Output must be a safe relative file path under an explicit root")
    parts = re.split(r"[\\/]", output)
    if any(not part or re.search(r"[. ]$", part) or re.match(r"^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", part, re.I) for part in parts):
        raise ValueError("Output contains an ambiguous or reserved filename")
    absolute_root = Path(os.path.abspath(root))
    cursor = Path(absolute_root.anchor)
    for part in absolute_root.parts[1:]:
        cursor /= part
        _safe_directory(cursor)
    target = absolute_root.joinpath(*parts)
    cursor = absolute_root
    for part in parts[:-1]:
        cursor /= part
        _safe_directory(cursor)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(data)
    return str(target)


def acquire_fulltext(options=None, dependencies=None):
    options, dependencies = _options(options), dependencies or {}
    if "format" in options and options["format"] not in ("html", "pdf"):
        raise ValueError("format must be html or pdf")
    if options.get("trustedProviderTransport") and not options.get("arxiv"):
        raise ValueError("Trusted-provider transport is unavailable for arbitrary URL acquisition; use a fixed arXiv ID")
    if bool(options.get("url")) == bool(options.get("arxiv")):
        raise ValueError("Provide exactly one explicit URL or arXiv ID")
    if bool(options.get("out")) != bool(options.get("root")):
        raise ValueError("Saving requires both root and out")
    identity = normalize_arxiv(options["arxiv"]) if options.get("arxiv") else None
    input_url = "https://arxiv.org/" + ("pdf" if options.get("format") == "pdf" else "html") + "/" + identity if identity else options["url"]
    parsed = checked_url(input_url)
    result = {"requested_url": input_url, "retrieved_at": None if options.get("offline") else _now(dependencies),
              "status": "unresolved", "content_kind": "unknown", "reading_scope": "not_assigned",
              "saved_path": None, "blocks": [], "limitations": [], "notice": NOTICE}
    if options.get("offline"):
        return {**result, "status": "offline", "limitations": ["No acquisition requested; source availability and body content remain unknown."],
                "transport": {"requests": [], "bytes_received": 0}}
    network = _Network(options, dependencies, parsed.geturl() if options.get("trustedProviderTransport") else None)
    try:
        response = network.get(input_url, {parsed.hostname})
        result["source_url"] = response.url
        if response.status in (404, 410):
            return {**result, "status": "not_available",
                    "limitations": [f"Requested representation returned HTTP {response.status}; this does not establish that the paper does not exist."],
                    "transport": network.summary()}
        if response.status != 200:
            raise ValueError(f"Full-text source HTTP {response.status}; no fallback or access bypass attempted")
        result.update(byte_length=len(response.body), sha256=_hash(response.body), content_type=response.headers.get("content-type", "unknown"))
        if response.body.startswith(b"%PDF-"):
            result["status"] = "needs_host_extraction"
            result["limitations"].append("PDF bytes acquired only; no text, OCR, page, figure, or equation reading has occurred.")
        elif re.match(r"^(?:text/html|application/xhtml\+xml)(?:;|$)", result["content_type"], re.I):
            charset = re.search(r'''charset\s*=\s*["']?([^;\s"']+)''', result["content_type"], re.I)
            charset = charset[1] if charset else "utf-8"
            try:
                text = response.body.decode(_html_charset(charset), errors="strict")
                if text.startswith("\ufeff"):
                    text = text[1:]
            except (LookupError, UnicodeError) as exc:
                raise ValueError("Unsupported charset or invalid encoded HTML; use host extraction") from exc
            result["blocks"] = extract_html(text, response.url)
            result["extraction_status"] = "html_blocks_extracted" if result["blocks"] else "no_text_blocks"
            result["status"] = "needs_host_review" if result["blocks"] else "needs_host_extraction"
            result["limitations"].append("Lossy HTML blocks; host must confirm this is the paper body, verify equations/tables/figures, and assign actual reading scope. Unknown named entities are preserved.")
        else:
            raise ValueError("Unsupported content type or invalid PDF signature; no text extraction attempted")
        if options.get("out"):
            result["saved_path"] = save_source_bytes(options["root"], options["out"], response.body)
        else:
            result["limitations"].append("Original source bytes were not saved; provide root and a new out path when a durable source artifact is needed.")
        if identity and not re.search(r"v\d+$", identity):
            result["limitations"].append("Unversioned arXiv request; retrieved technical version must be confirmed before creating evidence.")
    except Exception as exc:
        result["status"] = "failed"
        result["limitations"].append(str(exc))
    return {**result, "transport": network.summary()}
