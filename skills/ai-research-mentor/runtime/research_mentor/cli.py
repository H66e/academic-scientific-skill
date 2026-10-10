"""CLI adapter.  All output is UTF-8; --format json is a stable envelope."""
from __future__ import annotations
import argparse
import json
import platform
from pathlib import Path
import sqlite3
import sys

from .core import ResearchCore
from .contracts import Envelope
from .ledger import LedgerError
from .transport import Transport
from .judgment import Judgment, RESEARCH_TYPES

def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="research-mentor", description="Local research ledger and bounded evidence acquisition (Python 3.10+)")
    result.add_argument("--project", required=True, help="Local private project directory, outside the skill source tree")
    result.add_argument("--format", choices=["json", "markdown"], default="json")
    result.add_argument("--trusted-provider-transport", action="store_true", help="Use the system HTTPS proxy only for fixed official providers; TLS remains enabled")
    result.add_argument("--timeout", type=int, default=15)
    result.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024)
    result.add_argument("--byte-budget", type=int, default=10 * 1024 * 1024)
    result.add_argument("--request-budget", type=int, default=8)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--question", default="")
    init.add_argument("--research-type", choices=sorted(RESEARCH_TYPES), default="empirical")
    commands.add_parser("doctor")
    commands.add_parser("verify-ledger")
    commands.add_parser("verify-artifacts")
    commands.add_parser("anchor-ledger", help="Record the current ledger head and count so later tail truncation is detectable")
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--provider", choices=["arxiv", "crossref"], default="arxiv")
    search.add_argument("--sensitivity", choices=["public", "deidentified", "private"], default="private")
    search.add_argument("--family", default="unspecified")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--offline", action="store_true")
    resolve = commands.add_parser("resolve")
    resolve.add_argument("identifier")
    resolve.add_argument("--sensitivity", choices=["public", "deidentified", "private"], default="public")
    resolve.add_argument("--offline", action="store_true")
    fetch = commands.add_parser("fetch")
    origin = fetch.add_mutually_exclusive_group(required=True)
    origin.add_argument("--local", dest="local_path")
    origin.add_argument("--url")
    origin.add_argument("--identifier")
    fetch.add_argument("--paper-id")
    fetch.add_argument("--sensitivity", choices=["public", "deidentified", "private"], default="private")
    fetch.add_argument("--offline", action="store_true")
    quote = commands.add_parser("quote")
    quote.add_argument("source_id")
    quote.add_argument("excerpt")
    quote.add_argument("--locator", default="")
    quote.add_argument("--block-id")
    show = commands.add_parser("show-source")
    show.add_argument("source_id")
    identity = commands.add_parser("confirm-source", help="Record actual human verification of local or publisher source identity")
    identity.add_argument("source_id")
    identity.add_argument("paper_id")
    identity.add_argument("--version", required=True)
    identity.add_argument("--statement", required=True)
    identity.add_argument("--human-confirmed", action="store_true")
    candidate = commands.add_parser("candidate", help="Append a candidate from supplied JSON; updates create a new version")
    candidate.add_argument("file")
    claim = commands.add_parser("claim")
    claim.add_argument("candidate_id")
    claim.add_argument("text")
    claim.add_argument("--kind", default="hypothesis")
    claim.add_argument("--context-only", action="store_true")
    link = commands.add_parser("link")
    link.add_argument("claim_id")
    link.add_argument("evidence_id")
    link.add_argument("--relation", choices=["supports", "contradicts", "context"], default="supports")
    link.add_argument("--target", choices=["problem", "hypothesis", "nearest_work", "prerequisite", "validation"], default="hypothesis")
    link.add_argument("--context-only", action="store_true")
    reading = commands.add_parser("confirm-read", help="Record actual reading; acquisition or delivery cannot confirm it")
    reading.add_argument("evidence_id")
    reading.add_argument("--scope", choices=["abstract", "section", "full_text"], required=True)
    reading.add_argument("--context", required=True)
    reading.add_argument("--human-page-check", action="store_true")
    record = commands.add_parser("record-result", help="Record a declared result from JSON; does not run an experiment")
    record.add_argument("file")
    record.add_argument("--human-confirmed", action="store_true")
    correction = commands.add_parser("reclassify-result", help="Append an explicit same-run correction, preserving the prior record")
    correction.add_argument("target")
    correction.add_argument("--outcome", choices=["not_run", "execution_failed", "inconclusive", "supported", "contradicted"], required=True)
    correction.add_argument("--reason", required=True)
    correction.add_argument("--kind", choices=["smoke", "scientific"])
    correction.add_argument("--summary")
    correction.add_argument("--artifacts", nargs="*")
    correction.add_argument("--human-confirmed", action="store_true")
    invalidation = commands.add_parser("invalidate-result", help="Record an actual person's withdrawal of a whole run's eligibility")
    invalidation.add_argument("target")
    invalidation.add_argument("--reason", required=True)
    invalidation.add_argument("--human-confirmed", action="store_true")
    state = commands.add_parser("results", help="Inspect effective result heads and blockers without writing")
    state.add_argument("candidate_id")
    state.add_argument("--candidate-version", type=int)
    for name in ("coverage", "next", "finalize"):
        command = commands.add_parser(name)
        command.add_argument("candidate_id")
    assess = commands.add_parser("assess", help="Record a strict machine recommendation; no automatic human approval")
    assess.add_argument("candidate_id")
    assess.add_argument("--recommendation", choices=["GO", "HOLD", "KILL"], default="GO")
    assess.add_argument("--reason", required=True)
    assess.add_argument("--stage", choices=["information_test", "pilot", "full_validation"], default="pilot")
    assess.add_argument("--scope", choices=["scientific_framing", "current_constraints"], default="scientific_framing")
    assess.add_argument("--kill-type", choices=["duplicate", "scientific_refutation", "constraints"])
    decision = commands.add_parser("decision", help="Record an actual person's instruction; models must not invent this event")
    decision.add_argument("review_id")
    decision.add_argument("--decision", choices=["GO", "HOLD", "KILL"], required=True)
    decision.add_argument("--statement", required=True)
    decision.add_argument("--human-confirmed", action="store_true")
    decision.add_argument("--override-reason", default="")
    revoke = commands.add_parser("revoke")
    revoke.add_argument("candidate_id")
    revoke.add_argument("--statement", required=True)
    revoke.add_argument("--human-confirmed", action="store_true")
    commands.add_parser("export-dossier", help="Schema-3 projection preserving declared results; no migrated approval")
    commands.add_parser("status")
    lint = commands.add_parser("lint", help="Report unregistered DOI/arXiv references, without modifying prose")
    lint.add_argument("file")
    recheck = commands.add_parser("recheck", help="Repeat an explicitly selected public/de-identified recorded query")
    recheck.add_argument("search_id")
    recheck.add_argument("--sensitivity", choices=["public", "deidentified", "private"], default="private")
    return result


def read_input(file: str) -> str:
    path = Path(file)
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("input exceeds 8 MiB budget")
    return path.read_text(encoding="utf-8-sig")

def doctor(core: ResearchCore) -> Envelope:
    # Capability observations are explicit; this command never silently requests
    # network permission or installs a parser.
    data = {"python": platform.python_version(), "python_supported": sys.version_info >= (3, 10),
            "stdout_encoding": sys.stdout.encoding, "network": "not_tested", "pdf_extraction": "not_available",
            "sqlite": sqlite3.sqlite_version, "project": str(core.ledger.project),
            "ledger": core.ledger.verify(), "protocol": "ledger-json-v1"}
    return Envelope.success(data, status="capabilities", warnings=["Network availability and source coverage were not tested."])

def run(args) -> Envelope:
    core = ResearchCore(args.project, transport=Transport(timeout=args.timeout, max_bytes=args.max_bytes,
            byte_budget=args.byte_budget, request_budget=args.request_budget,
            trusted_provider_transport=args.trusted_provider_transport))
    if args.command == "init":
        output = core.init()
        if output.ok and args.question:
            project = core.ledger.append("project.update", {"id": core.ledger.project.name,
                "question": args.question, "research_type": args.research_type,
                "constraints": {}, "assumptions": []}, actor="user", trust="T1")
            output.ledger_events.append(project["id"])
        return output
    if args.command == "doctor":
        return doctor(core)
    if args.command == "verify-ledger":
        data = core.ledger.verify()
        warnings = [] if data["anchor"] != "absent" else [
            "No anchor file: the chain is intact but a deleted tail cannot be detected. Run anchor-ledger to record the current head."]
        return Envelope(data["valid"], "valid" if data["valid"] else "invalid", data,
                        errors=data["errors"], warnings=warnings)
    if args.command == "anchor-ledger":
        data = core.ledger.anchor()
        return Envelope.success(data, status="anchored", warnings=[
            "Anchoring adopts the ledger exactly as it stands. A truncated or edited ledger would be anchored as-is."])
    if args.command == "verify-artifacts":
        data = core.verify_artifacts()
        return Envelope(data["valid"], "valid" if data["valid"] else "invalid", data, errors=data["errors"])
    if args.command == "search":
        return core.search(args.query, provider=args.provider, sensitivity=args.sensitivity,
                           limit=args.limit, family=args.family, offline=args.offline)
    if args.command == "resolve":
        return core.resolve(args.identifier, sensitivity=args.sensitivity, offline=args.offline)
    if args.command == "fetch":
        return core.fetch(local_path=args.local_path, url=args.url, identifier=args.identifier,
                          paper_id=args.paper_id, sensitivity=args.sensitivity, offline=args.offline)
    if args.command == "quote":
        return core.quote(args.source_id, args.excerpt, locator=args.locator, block_id=args.block_id)
    if args.command == "show-source":
        return core.inspect_source(args.source_id)
    if args.command == "confirm-source":
        return core.confirm_source_identity(args.source_id, args.paper_id, version=args.version,
            statement=args.statement, human=args.human_confirmed)
    judgment = Judgment(core.ledger)
    if args.command == "candidate":
        event = judgment.upsert_candidate(json.loads(read_input(args.file)))
        return Envelope.success(event["data"], status="recorded", ledger_events=[event["id"]])
    if args.command == "claim":
        event = judgment.add_claim(args.text, args.candidate_id, args.kind, load_bearing=not args.context_only)
        return Envelope.success(event["data"], status="recorded", ledger_events=[event["id"]])
    if args.command == "link":
        event = judgment.link_claim(args.claim_id, args.evidence_id, args.relation,
            target=args.target, decision_relevant=not args.context_only)
        return Envelope.success(event["data"], status="recorded", ledger_events=[event["id"]])
    if args.command == "confirm-read":
        event = judgment.confirm_read(args.evidence_id, args.scope, args.context,
            human=args.human_page_check, visual_checked=args.human_page_check)
        return Envelope.success(event["data"], status="recorded", ledger_events=[event["id"]],
            warnings=["This records the reader's statement; it cannot prove reading or scientific understanding."])
    if args.command in {"record-result", "reclassify-result", "invalidate-result"}:
        if args.command == "record-result":
            event = judgment.record_result(json.loads(read_input(args.file)), human=args.human_confirmed)
        elif args.command == "reclassify-result":
            event = judgment.reclassify_result(args.target, args.outcome, reason=args.reason,
                human=args.human_confirmed, kind=args.kind, summary=args.summary, artifacts=args.artifacts)
        else:
            event = judgment.invalidate_result(args.target, args.reason, human=args.human_confirmed)
        return Envelope.success(event["data"], status="recorded", ledger_events=[event["id"]], warnings=[
            "A declaration preserves history and requires reassessment; it does not verify scientific truth or grant execution authority."])
    if args.command == "results":
        data = judgment.results(args.candidate_id, candidate_version=args.candidate_version)
        return Envelope.success(data, status="effective_results", warnings=data.get("warnings", []))
    if args.command in {"coverage", "next"}:
        data = judgment.coverage(args.candidate_id)
        return Envelope.success(data, status="bounded", next=data["missing"][:5])
    if args.command == "assess":
        data = judgment.assess(args.candidate_id, args.recommendation, reason=args.reason,
            stage=args.stage, scope=args.scope, kill_type=args.kill_type)
        return Envelope.success(data, status=data["machine_recommendation"], ledger_events=[data["review_id"]],
            next=data["missing"][:5])
    if args.command == "decision":
        event = judgment.record_decision(args.review_id, args.decision, args.statement,
            human=args.human_confirmed, override_reason=args.override_reason)
        return Envelope.success(event["data"], status="human_recorded", ledger_events=[event["id"]],
            warnings=["No identity authentication; an operator must ensure this is an actual person's instruction."])
    if args.command == "finalize":
        data = judgment.finalize(args.candidate_id)
        return Envelope.success(data, status=data["approval_status"])
    if args.command == "revoke":
        event = judgment.revoke_decision(args.candidate_id, args.statement, human=args.human_confirmed)
        return Envelope.success(event["data"], status="revoked", ledger_events=[event["id"]])
    if args.command == "export-dossier":
        return Envelope.success(judgment.export_dossier(), status="initial_projection",
            warnings=["Projection preserves result history but omits evidence associations and reviews; Node ranking requires its own current v3 assessment and applicable receipt checks."])
    if args.command == "status":
        events = judgment._events()
        candidates = {}
        project = {}
        for event in events:
            if event["type"] in {"project.init", "project.update"}:
                project = event["data"]
            if event["type"] == "candidate.upsert":
                candidates[event["data"]["id"]] = event["data"]
        return Envelope.success({"project": project, "event_count": len(events),
            "candidates": [{**judgment.finalize(cid), "next": judgment.coverage(cid)["missing"][:5]} for cid in candidates]}, status="current")
    if args.command == "lint":
        import re
        text = read_input(args.file)
        registered = set()
        for event in judgment._events():
            papers = [event["data"]] if event["type"] == "paper.resolve" else event["data"].get("papers", [])
            for paper in papers:
                registered.update(str(v).lower() for v in paper.get("identifiers", {}).values())
        found = set(re.findall(r"10\.\d{4,9}/[^\s<>\[\]]+|\b\d{4}\.\d{4,5}(?:v\d+)?\b", text))
        unknown = sorted(value for value in found if value.rstrip(".,;)").lower() not in registered)
        return Envelope.success({"unregistered_identifiers": unknown,
            "notice": "Lexical DOI/arXiv check only; prose entailment, authors and titles still need source review."},
            status="unverified_references" if unknown else "references_registered", warnings=unknown)
    if args.command == "recheck":
        previous = judgment._record(args.search_id, "search.result")["data"]
        output = core.search(previous["query"], provider=previous["provider"], sensitivity=args.sensitivity,
            limit=previous["limit"], family=previous.get("family", "unspecified"))
        if output.data:
            output.data["new_paper_ids"] = sorted(set(output.data.get("result_paper_ids", [])) - set(previous["result_paper_ids"]))
        return output
    return Envelope.failure("unknown command")

def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        output = run(args)
    except (LedgerError, OSError, ValueError) as exc:
        output = Envelope.failure(str(exc))
    if args.format == "json":
        print(json.dumps(output.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"{output.status}: {'ok' if output.ok else 'failed'}")
        if output.data is not None:
            print(json.dumps(output.data, ensure_ascii=False, indent=2))
        for item in output.warnings:
            print(f"- Warning: {item}")
        for item in output.errors:
            print(f"- Error: {item}")
        for item in output.next:
            print(f"- Next: {item}")
    if not output.ok:
        return 2 if output.status == "blocked" else 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
