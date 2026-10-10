"""Read-only, byte-bound skill maintenance receipts; not scientific evaluation.

This is the native Python equivalent of ``scripts/evolution_guard.mjs``.  It
never applies a candidate, launches a process, invokes Git, or makes requests.
The fixed editable whitelist cannot be expanded by a submitted suite.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any

from .audit import canonical_stringify

NOTICE = "Structural and recorded-evidence checks only: KEEP does not establish scientific quality, novelty, or correctness."
EDITABLE = frozenset({"SKILL.md", *(f"references/{name}.md" for name in
                                  ("literature", "ideation", "evaluation", "feedback"))})
REQUIRED_CHECKS = ("unit_regressions", "skill_structure", "protected_principles")
SPLITS = ("target", "regression", "holdout")
_MISSING = object()
_TRIM = "\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip(_TRIM))


def _digest(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[a-f\d]{64}", value, re.ASCII) is not None


def _positive(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and (not isinstance(value, float) or math.isfinite(value))
            and value > 0 and value == int(value))


def _version_one(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == 1


def _display(value: Any) -> str:
    """JavaScript interpolation for invalid fields that occur in diagnostics."""
    if value is _MISSING:
        return "undefined"
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, dict):
        return "[object Object]"
    if isinstance(value, list):
        return ",".join("" if item is None or item is _MISSING else _display(item) for item in value)
    return str(value)


def _identity(value: Any) -> Any:
    # JS Set/Map can store malformed object IDs without throwing or conflating
    # them with structurally equal values. Validation will still hold the run.
    if isinstance(value, (dict, list)):
        return ("object", id(value))
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, float)):
        return ("number", "NaN" if isinstance(value, float) and math.isnan(value) else value)
    return (type(value), value)


def _sort_key(value: str) -> bytes:
    return value.encode("utf-16-be", "surrogatepass")


def _inside(root: str, file: str) -> bool:
    try:
        return os.path.normcase(os.path.commonpath((root, file))) == os.path.normcase(root)
    except ValueError:
        return False


def _resolve_path(base: str, value: Any, contained: bool = True) -> str:
    if not _text(value) or re.search(r"[\x00-\x1f]", value):
        raise ValueError("must be a nonempty filesystem path")
    if re.match(r"^[a-z][a-z\d+.-]*:", value, re.I) and not re.match(r"^[a-z]:[\\/]", value, re.I):
        raise ValueError("URLs and drive-relative paths are forbidden")
    if os.name != "nt" and (re.match(r"^[a-z]:", value, re.I) or "\\" in value):
        raise ValueError("foreign-platform paths are forbidden")
    result = os.path.abspath(os.path.join(base, value))
    if contained and not _inside(base, result):
        raise ValueError("path must stay inside runDir")
    return result


def _linked(info: os.stat_result) -> bool:
    # Python 3.10 lacks Path.is_junction(). A Windows junction is a reparse
    # point even when its st_mode is a directory; lstat must not miss it.
    return (stat.S_ISLNK(info.st_mode)
            or bool(getattr(info, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _no_links(file: str | os.PathLike[str], kind: str) -> str:
    """Inspect the root and every ancestor without resolving directory links."""
    absolute = os.path.abspath(os.fspath(file))
    parts = Path(absolute).parts
    current = parts[0]
    root_info = os.lstat(current)
    if _linked(root_info) or not stat.S_ISDIR(root_info.st_mode):
        raise ValueError("linked or invalid filesystem root")
    for index, name in enumerate(parts[1:], 1):
        current = os.path.join(current, name)
        info = os.lstat(current)
        if _linked(info):
            raise ValueError("symbolic links and junctions are forbidden")
        expected = kind if index == len(parts) - 1 else "directory"
        if not (stat.S_ISDIR(info.st_mode) if expected == "directory" else stat.S_ISREG(info.st_mode)):
            raise ValueError(f"expected a regular {expected}")
    if len(parts) == 1 and kind != "directory":
        raise ValueError("expected a regular file")
    return absolute


def _read_bytes(file: str | os.PathLike[str]) -> bytes:
    absolute = _no_links(file, "file")
    with open(absolute, "rb") as stream:
        value = stream.read()
    _no_links(absolute, "file")
    return value


def hash_file(file: str | os.PathLike[str]) -> str:
    """Hash exact file bytes; reject links and linked ancestors.

    Streaming avoids retaining large files in memory. Like the compatibility
    guard, this imposes no newly invented file-size acceptance limit.
    """
    absolute = _no_links(file, "file")
    digest = hashlib.sha256()
    with open(absolute, "rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    _no_links(absolute, "file")
    return digest.hexdigest()


def hash_checks(checks: Any) -> str:
    """Bind checks using the existing Node fingerprint serialization protocol."""
    return hashlib.sha256(canonical_stringify(checks).encode("utf-8")).hexdigest()


def snapshot_skill(directory: str | os.PathLike[str]) -> dict[str, Any]:
    """Hash every regular file, including tests; never ignore or follow links."""
    root = _no_links(directory, "directory")
    files: dict[str, str] = {}

    def walk(current: str) -> None:
        with os.scandir(current) as entries:
            names = sorted((entry.name for entry in entries), key=_sort_key)
        for name in names:
            absolute = os.path.join(current, name)
            info = os.lstat(absolute)
            if _linked(info):
                raise ValueError("snapshot contains a symbolic link or junction")
            if stat.S_ISDIR(info.st_mode):
                walk(absolute)
            elif stat.S_ISREG(info.st_mode):
                files[os.path.relpath(absolute, root).replace(os.sep, "/")] = hash_file(absolute)
            else:
                raise ValueError("snapshot contains a non-regular file")

    walk(root)
    _no_links(root, "directory")
    ordered = dict(sorted(files.items(), key=lambda item: _sort_key(item[0])))
    return {"hash": hash_checks(ordered), "files": ordered}


def _parse_json(data: bytes) -> Any:
    def invalid_constant(value: str) -> None:
        raise ValueError(f"invalid JSON constant: {value}")
    # Node converts buffer bytes to UTF-8 with replacement before JSON.parse.
    return json.loads(data.decode("utf-8", errors="replace"), parse_constant=invalid_constant)


def read_run(file: str | os.PathLike[str]) -> tuple[Any, Path]:
    """Read a JSON run without links; return the absolute run-file path."""
    absolute = _no_links(file, "file")
    return _parse_json(_read_bytes(absolute)), Path(absolute)


def _validate_suite(suite: Any, hold) -> list[Any]:
    if not isinstance(suite, dict):
        hold("suite must be a JSON object")
        return []
    if not _version_one(suite.get("schema_version")):
        hold("suite.schema_version must equal 1")
    if not _positive(suite.get("max_attempts")):
        hold("suite.max_attempts must be a positive integer")
    if not isinstance(suite.get("execution_config"), dict):
        hold("suite.execution_config must be an object")
    else:
        try:
            canonical_stringify(suite["execution_config"])
        except (ValueError, TypeError, OverflowError):
            hold("suite.execution_config must contain finite JSON values")
    allowed = suite.get("allowed_paths")
    if (not isinstance(allowed, list) or any(not isinstance(value, str) or value not in EDITABLE for value in allowed)
            or len({_identity(value) for value in allowed}) != len(allowed)):
        hold("suite.allowed_paths must be a unique subset of the fixed editable whitelist")
    cases = suite.get("cases") if isinstance(suite.get("cases"), list) else []
    if not isinstance(suite.get("cases"), list):
        hold("suite.cases must be an array")
    ids: set[Any] = set()
    counts = dict.fromkeys(SPLITS, 0)
    for item in cases:
        if not isinstance(item, dict):
            hold("suite case must be an object")
            continue
        identifier = item.get("id", _MISSING)
        if not _text(identifier) or _identity(identifier) in ids:
            hold("suite case IDs must be nonempty and unique")
        ids.add(_identity(identifier))
        split = item.get("split")
        if split not in SPLITS:
            hold("suite case split must be target, regression, or holdout")
        else:
            counts[split] += 1
        if not _text(item.get("prompt")):
            hold("suite case prompt must be nonempty")
        criteria = item.get("criteria")
        if not isinstance(criteria, list) or not criteria or any(not _text(value) for value in criteria):
            hold("suite case criteria must contain nonempty strings")
    for split in SPLITS:
        if counts[split] == 0:
            hold(f"suite requires at least one {split} case")
    return cases


def check_evolution(run: Any, run_dir: str | os.PathLike[str]) -> dict[str, Any]:
    """Validate current bytes and bound receipts. Rejection wins over holds."""
    holds: list[str] = []
    rejects: list[str] = []
    changed_paths: list[str] = []
    hold, reject = holds.append, rejects.append

    def finish() -> dict[str, Any]:
        return {"decision": "REJECT" if rejects else "HOLD" if holds else "KEEP",
                "reasons": list(dict.fromkeys([*rejects, *holds])), "changed_paths": changed_paths}

    try:
        if not isinstance(run, dict):
            hold("run must be an object")
            return finish()
        root = _no_links(run_dir, "directory")
        if not _version_one(run.get("schema_version")):
            hold("run.schema_version must equal 1")
        for key in ("run_id", "hypothesis"):
            if not _text(run.get(key)):
                hold(f"run.{key} must be nonempty")
        if not _positive(run.get("attempt")):
            hold("run.attempt must be a positive integer")

        def artifact(record: Any, label: str, parse: bool = False) -> tuple[bool, Any]:
            try:
                if not isinstance(record, dict) or not _digest(record.get("hash")):
                    raise ValueError("requires file and lowercase SHA-256 hash")
                data = _read_bytes(_resolve_path(root, record.get("file")))
                if hashlib.sha256(data).hexdigest() != record["hash"]:
                    raise ValueError("artifact hash does not match current bytes")
                return True, _parse_json(data) if parse else None
            except (ValueError, TypeError, OSError) as error:
                hold(f"{label}: {error}")
                return False, None

        def snapshot(record: Any, label: str) -> dict[str, Any] | None:
            try:
                if not isinstance(record, dict) or not _digest(record.get("hash")):
                    raise ValueError("requires directory and lowercase SHA-256 hash")
                result = snapshot_skill(_resolve_path(root, record.get("directory")))
                if result["hash"] != record["hash"]:
                    hold(f"{label}: snapshot hash does not match current files")
                return result
            except (ValueError, TypeError, OSError) as error:
                hold(f"{label}: {error}")
                return None

        baseline = snapshot(run.get("baseline"), "baseline")
        candidate = snapshot(run.get("candidate"), "candidate")
        if baseline and candidate:
            changed_paths = [file for file in sorted(set(baseline["files"]) | set(candidate["files"]), key=_sort_key)
                             if baseline["files"].get(file) != candidate["files"].get(file)]
            if not changed_paths:
                hold("candidate has no file changes")
            for file in changed_paths:
                if file not in EDITABLE:
                    reject(f"protected file changed: {file}")
        try:
            target = snapshot_skill(_resolve_path(root, run.get("target_dir"), False))
            if (not baseline or target["hash"] != (run.get("baseline") or {}).get("hash")
                    or target["hash"] != baseline["hash"]):
                hold("target no longer matches the baseline snapshot")
        except (ValueError, TypeError, OSError) as error:
            hold(f"target_dir: {error}")

        suite_ok, suite = artifact(run.get("suite"), "suite", True)
        cases = _validate_suite(suite, hold) if suite_ok else []
        if isinstance(suite, dict):
            if (_positive(suite.get("max_attempts")) and _positive(run.get("attempt"))
                    and run["attempt"] > suite["max_attempts"]):
                hold("attempt exceeds the frozen suite budget")
            allowed = suite.get("allowed_paths")
            if isinstance(allowed, list) and all(isinstance(value, str) and value in EDITABLE for value in allowed):
                for file in changed_paths:
                    if file in EDITABLE and file not in allowed:
                        reject(f"change outside suite.allowed_paths: {file}")

        checks = run.get("checks") if isinstance(run.get("checks"), list) else []
        if not isinstance(run.get("checks"), list):
            hold("run.checks must be an array")
        names: set[Any] = set()
        for check in checks:
            if not isinstance(check, dict):
                hold("check must be an object")
                continue
            name = check.get("name", _MISSING)
            if not _text(name) or _identity(name) in names:
                hold("check names must be nonempty and unique")
            names.add(_identity(name))
            if check.get("passed") is False:
                reject(f"check failed: {_display(name)}")
            elif check.get("passed") is not True:
                hold(f"check.passed must be boolean: {_display(name)}")
            for key, expected_hash in (("baseline_hash", baseline["hash"] if baseline else None),
                                       ("candidate_hash", candidate["hash"] if candidate else None),
                                       ("suite_hash", (run.get("suite") or {}).get("hash") if isinstance(run.get("suite"), dict) else None)):
                if not _digest(check.get(key)) or check[key] != expected_hash:
                    hold(f"check is stale or unbound: {_display(name)}.{key}")
            artifact(check.get("artifact"), f"check artifact {_display(name)}")
        for name in REQUIRED_CHECKS:
            if _identity(name) not in names:
                hold(f"missing required check: {name}")

        receipt_ok, review = artifact(run.get("review"), "review", True)
        if not receipt_ok:
            return finish()
        if not isinstance(review, dict):
            hold("review must be a JSON object")
            return finish()
        if review.get("kind") not in ("independent", "self"):
            hold("review.kind must be independent or self")
        if review.get("kind") != "independent":
            hold("review must be independent to KEEP")
        if not _digest(review.get("checks_hash")) or review["checks_hash"] != hash_checks(checks):
            hold("review does not bind the current check statuses and artifacts")
        if (not _text(review.get("author_context")) or not _text(review.get("evaluator_context"))
                or review["author_context"].strip(_TRIM) == review["evaluator_context"].strip(_TRIM)):
            hold("review requires different nonempty author and evaluator contexts")
        bound = bool(baseline and candidate and suite_ok
                     and baseline["hash"] == run["baseline"].get("hash")
                     and candidate["hash"] == run["candidate"].get("hash")
                     and _digest(review.get("baseline_hash")) and review["baseline_hash"] == baseline["hash"]
                     and _digest(review.get("candidate_hash")) and review["candidate_hash"] == candidate["hash"]
                     and _digest(review.get("suite_hash")) and review["suite_hash"] == run["suite"].get("hash"))
        if not bound:
            hold("review is not bound to the current baseline, candidate, and suite hashes")
        rows = review.get("case_results") if isinstance(review.get("case_results"), list) else []
        if not isinstance(review.get("case_results"), list):
            hold("review.case_results must be an array")
        expected = {_identity(item.get("id", _MISSING)): item for item in cases if isinstance(item, dict)}
        seen: set[Any] = set()
        target_better = False
        for row in rows:
            if not isinstance(row, dict):
                hold("review case result must be an object")
                continue
            identifier = row.get("case_id", _MISSING)
            known = _text(identifier) and _identity(identifier) in expected
            unique = _identity(identifier) not in seen
            if not known:
                hold("review contains an unknown or invalid case ID")
            if not unique:
                hold(f"duplicate review case: {_display(identifier)}")
            seen.add(_identity(identifier))
            if row.get("execution") != "executed":
                hold(f"case was not executed: {_display(identifier)}")
            if row.get("execution") not in ("executed", "dry_run"):
                hold(f"invalid execution mode: {_display(identifier)}")
            if row.get("verdict") not in ("better", "tie", "worse", "unclear"):
                hold(f"invalid verdict: {_display(identifier)}")
            if row.get("verdict") == "unclear":
                hold(f"unclear verdict: {_display(identifier)}")
            if not isinstance(row.get("hard_constraints_pass"), bool):
                hold(f"hard_constraints_pass must be boolean: {_display(identifier)}")
            if not _text(row.get("reason")):
                hold(f"case reason must be nonempty: {_display(identifier)}")
            before_ok, _ = artifact(row.get("baseline_output"), f"baseline output {_display(identifier)}")
            after_ok, _ = artifact(row.get("candidate_output"), f"candidate output {_display(identifier)}")
            supported = bound and known and unique and row.get("execution") == "executed" and before_ok and after_ok
            if supported and row.get("hard_constraints_pass") is False:
                reject(f"hard constraint failed: {_display(identifier)}")
            if supported and row.get("verdict") == "worse":
                reject(f"case regressed: {_display(identifier)}")
            if (supported and row.get("hard_constraints_pass") is True and row.get("verdict") == "better"
                    and expected[_identity(identifier)].get("split") == "target"):
                target_better = True
        for key, item in expected.items():
            if key not in seen:
                hold(f"missing review case: {_display(item.get('id', _MISSING))}")
        if not target_better:
            hold("no executed target case demonstrates improvement")
        return finish()
    except (ValueError, TypeError, OSError, OverflowError, RecursionError) as error:
        hold(f"invalid run or filesystem: {error}")
        return finish()
