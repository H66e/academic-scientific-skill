"""Native adapters for the retained dossier, source, output and maintenance contracts.

These tools operate on existing JSON/files, not the append-only evidence ledger.
They share the importable implementations and never launch Node or experiments.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

INPUT_LIMIT = 8 * 1024 * 1024


def read_json(file: str):
    """Bounded UTF-8 JSON input, including '-' for piped research material."""
    if file == "-":
        stream = getattr(sys.stdin, "buffer", None)
        if stream is None:
            content = sys.stdin.read(INPUT_LIMIT + 1).encode("utf-8")
        else:
            content = stream.read(INPUT_LIMIT + 1)
    else:
        path = Path(file)
        if not path.is_file() or path.stat().st_size > INPUT_LIMIT:
            raise ValueError("Input must be a JSON file of at most 8 MiB")
        with path.open("rb") as stream:
            content = stream.read(INPUT_LIMIT + 1)
    if len(content) > INPUT_LIMIT:
        raise ValueError("Input must be JSON of at most 8 MiB")
    def nonfinite(value):
        raise ValueError(f"Non-finite JSON number: {value}")
    return json.loads(content.decode("utf-8-sig"), parse_constant=nonfinite)


class ToolParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("allow_abbrev", False)
        super().__init__(*args, **kwargs)

    def parse_args(self, args=None, namespace=None):
        arguments = list(sys.argv[1:] if args is None else args)
        seen = set()
        for token in arguments:
            if token.startswith("--") and token != "--":
                flag = token.split("=", 1)[0]
                if flag in seen:
                    self.error(f"Repeated option: {flag}")
                seen.add(flag)
        return super().parse_args(arguments, namespace)


def audit_parser():
    parser = ToolParser(prog="research_audit.py", description="Native dossier contract audit; no research execution")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--name", required=True)
    for name in ("validate", "fingerprint", "rank", "migrate", "verify-receipts"):
        command = commands.add_parser(name)
        command.add_argument("file")
        if name == "fingerprint":
            command.add_argument("idea_id")
        elif name == "rank":
            command.add_argument("--receipt-root")
        elif name == "verify-receipts":
            command.add_argument("--root", required=True)
    return parser


def audit_run(args):
    from . import audit
    if args.command == "init":
        return {"ok": True, **audit.init_project(args.root, args.name)}, 0
    dossier = read_json(args.file)
    if args.command == "validate":
        result = audit.validate_dossier(dossier)
        return result, 0 if result["valid"] else 1
    if args.command == "fingerprint":
        fingerprint = audit.fingerprint_idea(dossier, args.idea_id)
        field = "review_basis_hash" if dossier.get("schema_version", 0) >= 2 else "basis_hash"
        return {"idea_id": args.idea_id, field: fingerprint, "notice": audit.NOTICE}, 0
    if args.command == "migrate":
        return audit.migrate_dossier(dossier), 0
    if args.command == "verify-receipts":
        return audit.verify_independent_receipts(dossier, root=args.root), 0
    receipts = audit.verify_independent_receipts(dossier, root=args.receipt_root) if args.receipt_root else None
    result = audit.rank_dossier(dossier, receipt_verification=receipts)
    if receipts is not None:
        result["receipt_verification"] = receipts
    return result, 0


def sources_parser():
    parser = ToolParser(prog="research_sources.py", description="Bounded Crossref/arXiv acquisition; no automatic reading")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("search", "verify", "fulltext"):
        command = commands.add_parser(name)
        for flag in ("timeout", "max-bytes", "byte-budget", "request-budget"):
            command.add_argument("--" + flag)
        command.add_argument("--offline", action="store_true")
        command.add_argument("--trusted-provider-transport", action="store_true")
        command.add_argument("--sensitivity", choices=("public", "deidentified", "private"), default="private" if name == "search" else "public")
        if name == "search":
            command.add_argument("--query", required=True)
            for flag in ("rows", "pages", "mailto", "search-id"):
                command.add_argument("--" + flag)
        elif name == "verify":
            identifier = command.add_mutually_exclusive_group(required=True)
            identifier.add_argument("--doi")
            identifier.add_argument("--arxiv")
            command.add_argument("--expect-title")
            command.add_argument("--expect-year")
        else:
            origin = command.add_mutually_exclusive_group(required=True)
            origin.add_argument("--arxiv")
            origin.add_argument("--url")
            command.add_argument("--format", choices=("html", "pdf"))
            command.add_argument("--root")
            command.add_argument("--out")
    return parser


def sources_run(args):
    from . import sources
    options = {key: value for key, value in vars(args).items() if key != "command" and value is not None}
    function = {"search": sources.search_crossref, "verify": sources.verify_identifier, "fulltext": sources.acquire_fulltext}[args.command]
    result = function(options)
    searches = result.get("searches") or []
    failed = bool(searches and searches[0].get("status") == "failed") if args.command == "search" else result.get("status") in {"failed", "unresolved", "not_available"}
    return result, 1 if failed else 0


def outputs_parser():
    parser = ToolParser(prog="research_outputs.py", description="Organize supplied research notes and metadata")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("card", "draft", "bibtex"):
        command = commands.add_parser(name)
        command.add_argument("file", help="JSON file or '-' for standard input")
        if name == "draft":
            command.add_argument("--name", required=True)
    return parser


def outputs_run(args):
    from . import outputs
    record = read_json(args.file)
    if args.command == "card":
        return outputs.render_card(record), 0
    if args.command == "draft":
        return outputs.draft_dossier(record, name=args.name), 0
    result = outputs.export_bibtex(record)
    sys.stderr.write(json.dumps({key: result[key] for key in ("exported_count", "keys", "warnings")}, ensure_ascii=False) + "\n")
    return result["bibtex"], 0


def evolution_parser():
    parser = ToolParser(prog="evolution_guard.py", description="Read-only skill maintenance receipts and version checks")
    parser.add_argument("command", choices=("snapshot", "hash", "checks-hash", "check"))
    parser.add_argument("input")
    return parser


def evolution_run(args):
    from . import evolution
    if args.command == "snapshot":
        result = evolution.snapshot_skill(args.input)
    elif args.command == "hash":
        result = {"hash": evolution.hash_file(args.input)}
    else:
        run, file = evolution.read_run(args.input)
        result = {"hash": evolution.hash_checks(run.get("checks"))} if args.command == "checks-hash" else evolution.check_evolution(run, str(file.parent))
    return {**result, "notice": evolution.NOTICE}, 0


def main(tool: str, argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parsers = {"audit": audit_parser, "sources": sources_parser, "outputs": outputs_parser, "evolution": evolution_parser}
    runners = {"audit": audit_run, "sources": sources_run, "outputs": outputs_run, "evolution": evolution_run}
    args = parsers[tool]().parse_args(argv)
    try:
        result, status = runners[tool](args)
        sys.stdout.write(result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        return status
    except (ValueError, OSError, TypeError, KeyError) as error:
        if tool == "audit":
            from .audit import NOTICE
            result = {"ok": False, "error": str(error), "notice": NOTICE}
        elif tool == "evolution":
            from .evolution import NOTICE
            result = {"decision": "HOLD", "reasons": [str(error)], "changed_paths": [], "notice": NOTICE}
        else:
            sys.stderr.write(str(error) + "\n")
            return 1
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return 1
