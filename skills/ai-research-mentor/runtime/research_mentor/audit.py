"""Native dossier audit compatibility with the existing decision contract.

This module preserves dossier fingerprints, not Python ledger fingerprints.
Structural acceptance and receipt checks do not establish scientific truth.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit
import weakref

DECISION_CONTRACT_VERSION = 3
DIMENSIONS = ("scientific_value", "differentiation", "testability")
TYPES = ("empirical", "theoretical", "measurement", "dataset", "reproduction")
READ_SCOPES = ("metadata", "abstract", "section", "full_text")
ROLES = ("motivation", "nearest_work", "contradiction", "assumption", "feasibility", "validation", "context")
TARGETS = ("problem", "hypothesis", "nearest_work", "prerequisite", "validation")
NOTICE = "Structural checks only: passing does not establish source authenticity, literature coverage, novelty, or scientific correctness."
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_JS_SPACE = " \t\v\f\r\n\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def _text(value):
    return isinstance(value, str) and bool(value.strip(_JS_SPACE))


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _integer(value):
    return _number(value) and int(value) == value


def _positive(value):
    return _integer(value) and value > 0


def _utf16(value):
    return value.encode("utf-16-be", "surrogatepass")


def _js_number(value):
    """ECMAScript JSON number spelling for the binary64 input domain."""
    try:
        number = float(value)
    except (OverflowError, ValueError):
        raise ValueError("Only finite JSON values can be fingerprinted") from None
    if not math.isfinite(number):
        raise ValueError("Only finite JSON values can be fingerprinted")
    if number == 0:
        return "0"
    negative = number < 0
    number = abs(number)
    # CPython and ECMAScript choose the shortest round-tripping decimal. Their
    # display thresholds differ; Decimal expands that decimal without rounding.
    shortest = repr(number).lower()
    if 1e-6 <= number < 1e21:
        result = format(Decimal(shortest), "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
    else:
        if "e" not in shortest:
            shortest = format(number, ".16e")
        mantissa, exponent = shortest.split("e")
        mantissa = mantissa.rstrip("0").rstrip(".") if "." in mantissa else mantissa
        exponent = int(exponent)
        result = f"{mantissa}e{'+' if exponent >= 0 else '-'}{abs(exponent)}"
    return ("-" if negative else "") + result


def canonical_stringify(value):
    """Node canonical JSON: UTF-16 keys, index ordering, finite binary64 numbers.

    Arrays retain order. Lone UTF-16 surrogates are escaped as JSON.stringify
    does; this protocol remains distinct from ledger-json-v1.
    """
    seen = set()

    def string(item):
        # A native Python string may explicitly contain a UTF-16 pair. Node
        # treats that pair and the corresponding Unicode scalar identically.
        item = item.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "surrogatepass")
        encoded = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        return "".join(f"\\u{ord(char):04x}" if 0xD800 <= ord(char) <= 0xDFFF else char for char in encoded)

    def encode(item):
        if item is None:
            return "null"
        if isinstance(item, str):
            return string(item)
        if type(item) is bool:
            return "true" if item else "false"
        if type(item) in (int, float):
            return _js_number(item)
        if not isinstance(item, (list, dict)):
            raise ValueError("Only finite JSON values can be fingerprinted")
        if id(item) in seen:
            raise ValueError("Circular values cannot be fingerprinted")
        seen.add(id(item))
        try:
            if isinstance(item, list):
                return "[" + ",".join(encode(child) for child in item) + "]"
            if any(not isinstance(key, str) for key in item):
                raise ValueError("Only string JSON object keys can be fingerprinted")
            keys = sorted(item, key=_utf16)
            # JSON.stringify enumerates uint32 index properties ahead of other
            # properties even when Object.fromEntries received lexically sorted keys.
            indexed = [key for key in keys if re.fullmatch(r"0|[1-9][0-9]*", key) and int(key) < 4294967295]
            keys = sorted(indexed, key=int) + [key for key in keys if key not in indexed]
            return "{" + ",".join(string(key) + ":" + encode(item[key]) for key in keys) + "}"
        finally:
            seen.remove(id(item))

    return encode(value)


def _digest(value):
    return hashlib.sha256(canonical_stringify(value).encode("utf-8")).hexdigest()


def _without(record, excluded):
    return {key: value for key, value in record.items() if key not in excluded}


def _by_id(records):
    return sorted(records, key=lambda row: _utf16(row["id"]))


def _timestamp(value):
    if not isinstance(value, str):
        return False
    match = re.fullmatch(r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]+))?)?(Z|[+-][0-9]{2}:?[0-9]{2})", value)
    if not match:
        return False
    year, month, day, hour, minute, second, _, zone = match.groups()
    y, m, d, h, mi, se = map(int, (year, month, day, hour, minute, second or "0"))
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    days = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return (1 <= m <= 12 and 1 <= d <= days[m - 1] and h <= 23 and mi <= 59 and se <= 59
            and (zone == "Z" or (int(zone[1:3]) <= 23 and int(zone.replace(":", "")[3:]) <= 59)))


def _date_seconds(value):
    # datetime has no year zero; the contract does. Shift year zero into an
    # equivalent leap year then subtract the whole 400-year Gregorian cycle.
    zero = value.startswith("0000-")
    safe = "0400" + value[4:] if zero else value
    parsed = datetime.fromisoformat(safe.replace("Z", "+00:00"))
    whole = parsed.replace(microsecond=0)
    seconds = (whole - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
    return int(seconds) - (146097 * 86400 if zero else 0)


def _not_earlier(left, right):
    a, b = _date_seconds(left), _date_seconds(right)
    if a != b:
        return a > b
    fraction = lambda value: (re.search(r"\.([0-9]+)(?:Z|[+-][0-9]{2}:?[0-9]{2})$", value).group(1)
                              if re.search(r"\.([0-9]+)(?:Z|[+-][0-9]{2}:?[0-9]{2})$", value) else "")
    x, y = fraction(left), fraction(right)
    width = max(len(x), len(y))
    return x.ljust(width, "0") >= y.ljust(width, "0")


def _source_url(value):
    if not _text(value) or re.search(r"[\x00-\x20]", value) or not re.match(r"^(https?://|file://)", value, re.I):
        return False
    try:
        url = urlsplit(value)
        url.port
        if url.username or url.password:
            return False
        return len(url.path) > 1 if url.scheme == "file" else bool(url.hostname)
    except ValueError:
        return False


def _artifact(value):
    if not _text(value) or re.search(r"[\x00-\x1f]", value):
        return False
    if re.match(r"^[a-z][a-z0-9+.-]*:", value, re.I) and not re.match(r"^[a-z]:[\\/]", value, re.I):
        return _source_url(value)
    return True


def _fact(value, seen=None):
    if isinstance(value, str):
        return _text(value)
    if type(value) is bool:
        return True
    if type(value) in (int, float):
        return _number(value)
    if not isinstance(value, (dict, list)):
        return False
    seen = set() if seen is None else seen
    if id(value) in seen:
        return False
    seen.add(id(value))
    return any(_fact(child, seen) for child in (value.values() if isinstance(value, dict) else value))


def validate_dossier(dossier):
    """Validate contracts 1/2/3 without editing records or following locators."""
    errors, warnings = [], []
    fail = lambda where, message: errors.append(f"{where}: {message}")
    warn = lambda where, message: warnings.append(f"{where}: {message}")

    def keys(value, where, required):
        if not isinstance(value, dict):
            fail(where, "must be an object")
            return False
        for key in required:
            if key not in value:
                fail(f"{where}.{key}", "required")
        return True

    def text(value, where, allow_empty=False):
        if not isinstance(value, str) or (not allow_empty and not _text(value)):
            fail(where, "must be a string" if allow_empty else "must be a nonempty string")

    def choice(value, where, allowed):
        if type(value) not in (str, int, float) or value not in allowed:
            fail(where, "must be one of " + ", ".join(map(str, allowed)))

    def boolean(value, where):
        if type(value) is not bool:
            fail(where, "must be a boolean")

    def strings(value, where):
        if not isinstance(value, list):
            fail(where, "must be an array of strings")
        else:
            for index, item in enumerate(value):
                text(item, f"{where}[{index}]")

    def date(value, where):
        if not _timestamp(value):
            fail(where, "must be an ISO 8601 timestamp with a timezone")

    def positive(value, where):
        if not _positive(value):
            fail(where, "must be a positive integer")

    def report():
        return {"valid": not errors, "errors": errors, "warnings": warnings, "notice": NOTICE}

    if not keys(dossier, "dossier", ("schema_version", "project", "config", "searches", "papers", "evidence", "ideas", "reviews", "pilots", "history")):
        return report()
    version = dossier.get("schema_version")
    if type(version) not in (int, float) or version not in (1, 2, 3):
        fail("schema_version", "must equal 1, 2 or 3")
    modern, v3 = type(version) in (int, float) and version in (2, 3), type(version) in (int, float) and version == 3
    if modern and "screening" not in dossier:
        fail("screening", "required")
    if v3:
        for key in ("decision_contract_version", "result_invalidations"):
            if key not in dossier:
                fail(key, "required")
    if modern and "decision_contract_version" in dossier:
        positive(dossier["decision_contract_version"], "decision_contract_version")
    if modern and dossier.get("decision_contract_version") != DECISION_CONTRACT_VERSION:
        warn("decision_contract_version", "Legacy or unsupported decision contract; decisions remain HOLD until migration and reassessment")
    project = dossier.get("project")
    if keys(project, "project", ("id", "question", "research_type", "constraints", "assumptions")):
        text(project.get("id"), "project.id")
        text(project.get("question"), "project.question", True)
        choice(project.get("research_type"), "project.research_type", TYPES)
        if not isinstance(project.get("constraints"), dict):
            fail("project.constraints", "must be an object")
        if "notes" in project and not isinstance(project["notes"], dict):
            fail("project.notes", "must be an object of supplied source notes")
        strings(project.get("assumptions"), "project.assumptions")
    config = dossier.get("config")
    if keys(config, "config", ("ranking_weights",)):
        weights = config.get("ranking_weights")
        if keys(weights, "config.ranking_weights", DIMENSIONS):
            if len(weights) != 3:
                fail("config.ranking_weights", "must contain exactly the three scoring dimensions")
            for key in DIMENSIONS:
                if not _number(weights.get(key)) or weights[key] < 0:
                    fail(f"config.ranking_weights.{key}", "must be a finite nonnegative number")
            if not all(_number(weights.get(key)) for key in DIMENSIONS) or not _number(sum(weights.get(key, 0) for key in DIMENSIONS)) or sum(weights.get(key, 0) for key in DIMENSIONS) <= 0:
                fail("config.ranking_weights", "sum must be finite and greater than zero")
    collections, ids = {}, {}
    names = ["searches", "papers", "evidence", "ideas", "reviews", "pilots", "history"] + (["screening"] if modern else []) + (["result_invalidations"] if v3 else [])
    for name in names:
        raw = dossier.get(name)
        if not isinstance(raw, list):
            fail(name, "must be an array")
        collections[name], ids[name] = raw if isinstance(raw, list) else [], set()
        for index, item in enumerate(collections[name]):
            if not isinstance(item, dict):
                fail(f"{name}[{index}]", "must be an object")
                continue
            if name != "history" or "id" in item:
                text(item.get("id"), f"{name}[{index}].id")
                if _text(item.get("id")):
                    if item["id"] in ids[name]:
                        fail(f"{name}[{index}].id", "duplicate ID")
                    ids[name].add(item["id"])

    def reference(value, where, collection):
        text(value, where)
        if _text(value) and value not in ids[collection]:
            fail(where, f"unknown {collection} ID {value}")

    def references(value, where, collection):
        strings(value, where)
        if isinstance(value, list):
            for index, item in enumerate(value):
                reference(item, f"{where}[{index}]", collection)

    def visit(name, required):
        for index, item in enumerate(collections[name]):
            where = f"{name}[{index}]"
            if keys(item, where, required):
                yield item, where

    def array(value):
        return value if isinstance(value, list) else []

    def records(name):
        return [item for item in collections[name] if isinstance(item, dict)]

    def find(name, value):
        return next((item for item in records(name) if item.get("id") == value), None)

    for item, where in visit("searches", ("id", "query", "provider", "searched_at", "status", "scope", "limitations", "result_paper_ids")):
        for field in ("query", "provider", "scope"):
            text(item.get(field), f"{where}.{field}")
        date(item.get("searched_at"), f"{where}.searched_at")
        choice(item.get("status"), f"{where}.status", ("complete", "partial", "failed"))
        strings(item.get("limitations"), f"{where}.limitations")
        references(item.get("result_paper_ids"), f"{where}.result_paper_ids", "papers")
    for item, where in visit("papers", ("id", "title", "year", "url", "identifiers", "version", "accessed_at")):
        text(item.get("title"), f"{where}.title")
        text(item.get("version"), f"{where}.version")
        if "year" not in item or (item["year"] is not None and not _integer(item["year"])):
            fail(f"{where}.year", "must be an integer or null")
        if not _source_url(item.get("url")):
            fail(f"{where}.url", "must be a valid http, https, or file URL without credentials")
        if not isinstance(item.get("identifiers"), dict):
            fail(f"{where}.identifiers", "must be an object")
        else:
            for key, value in item["identifiers"].items():
                text(value, f"{where}.identifiers.{key}")
        date(item.get("accessed_at"), f"{where}.accessed_at")
    for item, where in visit("evidence", ("id", "paper_id", "source_version", "read_scope", "locator", "observation", "polarity")):
        reference(item.get("paper_id"), f"{where}.paper_id", "papers")
        text(item.get("source_version"), f"{where}.source_version")
        choice(item.get("read_scope"), f"{where}.read_scope", READ_SCOPES)
        text(item.get("locator"), f"{where}.locator")
        locator = item.get("locator")
        if item.get("read_scope") in ("section", "full_text") and isinstance(locator, str) and (re.fullmatch(r"paper|article|full[ _-]?text|全文|整篇论文", locator.strip(_JS_SPACE), re.I) or re.fullmatch(r"https?://\S+", locator.strip(_JS_SPACE), re.I)):
            warn(f"{where}.locator", "Deep evidence needs a precise section, page, figure, equation, or searchable passage")
        text(item.get("observation"), f"{where}.observation")
        choice(item.get("polarity"), f"{where}.polarity", ("supports", "contradicts", "context"))
        if "excerpt" in item:
            text(item["excerpt"], f"{where}.excerpt")
        if "limitation_origin" in item:
            choice(item["limitation_origin"], f"{where}.limitation_origin", ("author_stated", "reader_inferred"))
        if "uncertainty" in item:
            text(item["uncertainty"], f"{where}.uncertainty", True)
    evidence_by_id = {item.get("id"): item for item in records("evidence") if isinstance(item.get("id"), str)}
    for item, where in visit("ideas", ("id", "version", "title", "question", "research_type", "hypothesis", "contribution", "evidence_ids", "search_ids", "nearest_work", "novelty", "feasibility", "validation")):
        positive(item.get("version"), f"{where}.version")
        for field in ("title", "question", "hypothesis", "contribution"):
            text(item.get(field), f"{where}.{field}")
        choice(item.get("research_type"), f"{where}.research_type", TYPES)
        references(item.get("evidence_ids"), f"{where}.evidence_ids", "evidence")
        references(item.get("search_ids"), f"{where}.search_ids", "searches")
        if v3 and "claims" in item:
            if not isinstance(item["claims"], list):
                fail(f"{where}.claims", "must be an array of supplied claim records")
            else:
                claim_ids = set()
                for index, claim in enumerate(item["claims"]):
                    location = f"{where}.claims[{index}]"
                    if not keys(claim, location, ("id",)):
                        continue
                    text(claim.get("id"), f"{location}.id")
                    if _text(claim.get("id")):
                        if claim["id"] in claim_ids:
                            fail(f"{location}.id", "duplicate claim ID")
                        claim_ids.add(claim["id"])
                    if "candidate_version" in claim:
                        positive(claim["candidate_version"], f"{location}.candidate_version")
        nearest_work = array(item.get("nearest_work"))
        attached = [*array(item.get("evidence_ids")), *(identifier for nearest in nearest_work if isinstance(nearest, dict) for identifier in array(nearest.get("evidence_ids")))]
        if modern:
            if not isinstance(item.get("evidence_links"), list):
                fail(f"{where}.evidence_links", "must be an array")
            else:
                for index, link in enumerate(item["evidence_links"]):
                    location = f"{where}.evidence_links[{index}]"
                    if not keys(link, location, ("evidence_id", "role", "target", "claim", "relation", "decision_relevant")):
                        continue
                    reference(link.get("evidence_id"), f"{location}.evidence_id", "evidence")
                    choice(link.get("role"), f"{location}.role", ROLES)
                    choice(link.get("target"), f"{location}.target", TARGETS)
                    choice(link.get("relation"), f"{location}.relation", ("supports", "contradicts", "context"))
                    text(link.get("claim"), f"{location}.claim")
                    boolean(link.get("decision_relevant"), f"{location}.decision_relevant")
                    if link.get("evidence_id") not in attached:
                        fail(location, "Evidence link must belong to this candidate or its nearest work")
        if not isinstance(item.get("nearest_work"), list):
            fail(f"{where}.nearest_work", "must be an array")
        else:
            for index, nearest in enumerate(nearest_work):
                location = f"{where}.nearest_work[{index}]"
                if not keys(nearest, location, ("paper_id", "evidence_ids", "delta", "decisive")):
                    continue
                reference(nearest.get("paper_id"), f"{location}.paper_id", "papers")
                references(nearest.get("evidence_ids"), f"{location}.evidence_ids", "evidence")
                text(nearest.get("delta"), f"{location}.delta")
                boolean(nearest.get("decisive"), f"{location}.decisive")
                for identifier in array(nearest.get("evidence_ids")):
                    record = evidence_by_id.get(identifier) if isinstance(identifier, str) else None
                    if record and record.get("paper_id") != nearest.get("paper_id"):
                        fail(f"{location}.evidence_ids", f"evidence {identifier} belongs to a different paper")
        novelty = item.get("novelty")
        if keys(novelty, f"{where}.novelty", ("status", "reason", "coverage")):
            choice(novelty.get("status"), f"{where}.novelty.status", ("distinct", "incremental", "duplicate", "unclear"))
            for field in ("reason", "coverage"):
                text(novelty.get(field), f"{where}.novelty.{field}")
            if novelty.get("status") == "distinct" and isinstance(item.get("search_ids"), list) and not item["search_ids"]:
                warn(f"{where}.novelty", "Distinct label has no candidate search; ranking will HOLD")
        feasibility = item.get("feasibility")
        if keys(feasibility, f"{where}.feasibility", ("status", "reason", "dependencies")):
            choice(feasibility.get("status"), f"{where}.feasibility.status", ("ready", "pilot_only", "blocked", "unknown"))
            text(feasibility.get("reason"), f"{where}.feasibility.reason")
            if not isinstance(feasibility.get("dependencies"), list):
                fail(f"{where}.feasibility.dependencies", "must be an array")
            else:
                for index, dependency in enumerate(feasibility["dependencies"]):
                    location = f"{where}.feasibility.dependencies[{index}]"
                    if not keys(dependency, location, ("name", "mandatory", "status", "basis")):
                        continue
                    text(dependency.get("name"), f"{location}.name")
                    boolean(dependency.get("mandatory"), f"{location}.mandatory")
                    choice(dependency.get("status"), f"{location}.status", ("met", "failed", "unknown"))
                    text(dependency.get("basis"), f"{location}.basis")
                    if "constraint_keys" in dependency:
                        strings(dependency["constraint_keys"], f"{location}.constraint_keys")
                        constraints = project.get("constraints") if isinstance(project, dict) else None
                        if isinstance(dependency["constraint_keys"], list) and isinstance(constraints, dict):
                            for key in dependency["constraint_keys"]:
                                if not isinstance(key, str) or key not in constraints:
                                    fail(f"{location}.constraint_keys", f"Unknown current constraint {key}")
        validation = item.get("validation")
        fields = ("prediction", "falsifier", "design", "metric", "resource_estimate", "stop_rule")
        if keys(validation, f"{where}.validation", ("status", *fields)):
            choice(validation.get("status"), f"{where}.validation.status", ("specified", "missing"))
            for field in fields:
                text(validation.get(field), f"{where}.validation.{field}", validation.get("status") == "missing")
    required = ("id", "idea_id", "idea_version", "review_basis_hash" if modern else "basis_hash", "reviewed_at", "kind", "decision", "reason", "scores", "score_reasons", "penalties", "limitations") + (("decision_scope", "recommended_stage", "decision_basis") if modern else ())
    for item, where in visit("reviews", required):
        reference(item.get("idea_id"), f"{where}.idea_id", "ideas")
        positive(item.get("idea_version"), f"{where}.idea_version")
        hash_key = "review_basis_hash" if modern else "basis_hash"
        if not isinstance(item.get(hash_key), str) or not _HEX.fullmatch(item[hash_key]):
            fail(f"{where}.{hash_key}", "must be a lowercase SHA-256 hex digest")
        date(item.get("reviewed_at"), f"{where}.reviewed_at")
        choice(item.get("kind"), f"{where}.kind", ("self", "independent"))
        choice(item.get("decision"), f"{where}.decision", ("GO", "HOLD", "KILL"))
        text(item.get("reason"), f"{where}.reason")
        scores = item.get("scores")
        if keys(scores, f"{where}.scores", DIMENSIONS):
            if len(scores) != 3:
                fail(f"{where}.scores", "must contain exactly the three scoring dimensions")
            for field in DIMENSIONS:
                if field not in scores or (scores[field] is not None and (not _integer(scores[field]) or not 0 <= scores[field] <= 4)):
                    fail(f"{where}.scores.{field}", "must be an integer from 0 to 4, or null")
        reasons = item.get("score_reasons")
        if keys(reasons, f"{where}.score_reasons", DIMENSIONS):
            if len(reasons) != 3:
                fail(f"{where}.score_reasons", "must contain exactly the three scoring dimensions")
            for field in DIMENSIONS:
                text(reasons.get(field), f"{where}.score_reasons.{field}")
        if not isinstance(item.get("penalties"), list):
            fail(f"{where}.penalties", "must be an array")
        else:
            for index, penalty in enumerate(item["penalties"]):
                location = f"{where}.penalties[{index}]"
                if keys(penalty, location, ("reason", "points")):
                    text(penalty.get("reason"), f"{location}.reason")
                    if not _number(penalty.get("points")) or penalty["points"] < 0:
                        fail(f"{location}.points", "must be finite and nonnegative")
        strings(item.get("limitations"), f"{where}.limitations")
        if not modern:
            continue
        if "decision_contract_version" in item:
            positive(item["decision_contract_version"], f"{where}.decision_contract_version")
        if item.get("decision_contract_version") != DECISION_CONTRACT_VERSION:
            warn(f"{where}.decision_contract_version", "Legacy or unsupported review contract; reassessment is required")
        choice(item.get("decision_scope"), f"{where}.decision_scope", ("scientific_framing", "current_constraints"))
        choice(item.get("recommended_stage"), f"{where}.recommended_stage", ("information_test", "pilot", "full_validation"))
        basis = item.get("decision_basis")
        if keys(basis, f"{where}.decision_basis", ("type", "evidence_ids", "pilot_ids", "dependency_names", "constraint_keys", "explanation")):
            choice(basis.get("type"), f"{where}.decision_basis.type", ("advance", "insufficient", "duplicate", "scientific_refutation", "constraints"))
            references(basis.get("evidence_ids"), f"{where}.decision_basis.evidence_ids", "evidence")
            references(basis.get("pilot_ids"), f"{where}.decision_basis.pilot_ids", "pilots")
            strings(basis.get("dependency_names"), f"{where}.decision_basis.dependency_names")
            strings(basis.get("constraint_keys"), f"{where}.decision_basis.constraint_keys")
            text(basis.get("explanation"), f"{where}.decision_basis.explanation")
        if item.get("kind") == "independent":
            for field in ("author_context", "evaluator_context"):
                text(item.get(field), f"{where}.{field}")
            if _text(item.get("author_context")) and item.get("author_context") == item.get("evaluator_context"):
                fail(f"{where}.evaluator_context", "Must be different from the author context")
            if not _artifact(item.get("artifact")):
                fail(f"{where}.artifact", "Independent review needs its actual receipt path or URL")
            if "artifact_sha256" in item and (not isinstance(item["artifact_sha256"], str) or not _HEX.fullmatch(item["artifact_sha256"])):
                fail(f"{where}.artifact_sha256", "must be a lowercase SHA-256 hex digest")
            if "artifact_sha256" not in item:
                warn(f"{where}.artifact_sha256", "Receipt bytes have not been bound; full validation remains HOLD without explicit verification")
        if "confidence" in item:
            confidence = item["confidence"]
            if keys(confidence, f"{where}.confidence", DIMENSIONS):
                if len(confidence) != 3:
                    fail(f"{where}.confidence", "Must contain exactly the three scoring dimensions")
                for field in DIMENSIONS:
                    choice(confidence.get(field), f"{where}.confidence.{field}", ("low", "medium", "high"))
                    if item.get("decision") == "GO" and confidence.get(field) == "low":
                        warn(f"{where}.confidence.{field}", "Low-confidence GO needs explicit missing evidence and a bounded next step; confidence does not change scores")
            confidence_reasons = item.get("confidence_reasons")
            if keys(confidence_reasons, f"{where}.confidence_reasons", DIMENSIONS):
                if len(confidence_reasons) != 3:
                    fail(f"{where}.confidence_reasons", "Must contain exactly the three scoring dimensions")
                for field in DIMENSIONS:
                    text(confidence_reasons.get(field), f"{where}.confidence_reasons.{field}")
    for item, where in visit("pilots", ("id", "idea_id", "idea_version", "kind", "outcome", "artifacts", "summary", "limitations") + (("run_id", "affected_claims") if v3 else ())):
        reference(item.get("idea_id"), f"{where}.idea_id", "ideas")
        positive(item.get("idea_version"), f"{where}.idea_version")
        choice(item.get("kind"), f"{where}.kind", ("smoke", "scientific"))
        choice(item.get("outcome"), f"{where}.outcome", ("supported", "contradicted", "inconclusive", "execution_failed", "not_run"))
        strings(item.get("artifacts"), f"{where}.artifacts")
        if isinstance(item.get("artifacts"), list):
            for index, value in enumerate(item["artifacts"]):
                if not _artifact(value):
                    fail(f"{where}.artifacts[{index}]", "must be a file path or valid http, https, or file URL")
            if item.get("outcome") != "not_run" and not item["artifacts"]:
                fail(f"{where}.artifacts", "executed attempts need an artifact or log reference")
        text(item.get("summary"), f"{where}.summary")
        strings(item.get("limitations"), f"{where}.limitations")
        if v3:
            text(item.get("run_id"), f"{where}.run_id")
            if ("actor" in item or "trust" in item) and (item.get("actor"), item.get("trust")) not in (("model", "T2"), ("user", "T1")):
                fail(where, "result provenance must be model/T2 or user/T1")
            if "recorded_at" in item:
                date(item["recorded_at"], f"{where}.recorded_at")
            if "supersedes" in item:
                reference(item["supersedes"], f"{where}.supersedes", "pilots")
                text(item.get("reason"), f"{where}.reason")
            elif "reason" in item:
                fail(f"{where}.reason", "correction reason requires supersedes")
            if not isinstance(item.get("affected_claims"), list):
                fail(f"{where}.affected_claims", "must be an array of claim references")
            else:
                for index, claim in enumerate(item["affected_claims"]):
                    location = f"{where}.affected_claims[{index}]"
                    if keys(claim, location, ("claim_id", "reason")):
                        if any(key not in ("claim_id", "reason") for key in claim):
                            fail(location, "only claim_id and reason are allowed")
                        text(claim.get("claim_id"), f"{location}.claim_id")
                        text(claim.get("reason"), f"{location}.reason")
    if v3:
        result_by_id = {item.get("id"): item for item in records("pilots") if isinstance(item.get("id"), str)}
        run_scopes = {}
        for index, item in enumerate(collections["pilots"]):
            if not isinstance(item, dict):
                continue
            where, scope = f"pilots[{index}]", (item.get("idea_id"), item.get("idea_version"))
            run_id = item.get("run_id")
            if isinstance(run_id, str):
                if run_id in run_scopes and run_scopes[run_id] != scope:
                    fail(f"{where}.run_id", "run identity cannot cross candidates or candidate versions")
                run_scopes[run_id] = scope
            target = result_by_id.get(item.get("supersedes")) if isinstance(item.get("supersedes"), str) else None
            if target and (target.get("run_id"), target.get("idea_id"), target.get("idea_version")) != (run_id, *scope):
                fail(f"{where}.supersedes", "replacement must stay in the same run, candidate and version")
            seen, ancestor = [item.get("id")], target
            while ancestor:
                if ancestor.get("id") in seen:
                    fail(f"{where}.supersedes", "self-reference or replacement cycle")
                    break
                seen.append(ancestor.get("id"))
                parent = ancestor.get("supersedes")
                ancestor = result_by_id.get(parent) if isinstance(parent, str) else None
            idea = find("ideas", item.get("idea_id"))
            if idea and _positive(item.get("idea_version")) and _number(idea.get("version")) and item["idea_version"] > idea["version"]:
                fail(f"{where}.idea_version", "result version cannot exceed its candidate version")
            claim_ids = [claim.get("id") for claim in array(idea.get("claims") if idea else None) if isinstance(claim, dict) and ("candidate_version" not in claim or claim["candidate_version"] == item.get("idea_version"))]
            for claim in array(item.get("affected_claims")):
                if isinstance(claim, dict) and _text(claim.get("claim_id")) and claim["claim_id"] not in claim_ids:
                    warn(f"{where}.affected_claims", f"affected_claims_degraded: unresolved claim {claim['claim_id']}")
        for item, where in visit("result_invalidations", ("id", "run_id", "idea_id", "idea_version", "result_id", "reason", "recorded_at", "actor", "trust")):
            if isinstance(item.get("id"), str) and item["id"] in ids["pilots"]:
                fail(f"{where}.id", "classification and invalidation IDs must be distinct")
            reference(item.get("idea_id"), f"{where}.idea_id", "ideas")
            positive(item.get("idea_version"), f"{where}.idea_version")
            text(item.get("run_id"), f"{where}.run_id")
            text(item.get("reason"), f"{where}.reason")
            date(item.get("recorded_at"), f"{where}.recorded_at")
            reference(item.get("result_id"), f"{where}.result_id", "pilots")
            if item.get("actor") != "user" or item.get("trust") != "T1":
                fail(where, "run invalidation requires declared user/T1 provenance")
            target = result_by_id.get(item.get("result_id")) if isinstance(item.get("result_id"), str) else None
            if target and (target.get("run_id"), target.get("idea_id"), target.get("idea_version")) != (item.get("run_id"), item.get("idea_id"), item.get("idea_version")):
                fail(f"{where}.result_id", "invalidation target must match its run, candidate and version")
        if not errors:
            for idea in collections["ideas"]:
                state = _fold_results(dossier, idea["id"], idea["version"])
                for run in state["runs"]:
                    if run["eligible"] and run["ambiguous"]:
                        warn("pilots", f"ambiguous run {run['run_id']}: multiple effective classification heads require HOLD")
    for item, where in visit("history", ()):
        if "idea_id" in item:
            reference(item["idea_id"], f"{where}.idea_id", "ideas")
        if "idea_version" in item:
            positive(item["idea_version"], f"{where}.idea_version")
        if "at" in item:
            date(item["at"], f"{where}.at")
        if "evidence_ids" in item:
            references(item["evidence_ids"], f"{where}.evidence_ids", "evidence")
        for field in ("event", "reason"):
            if field in item:
                text(item[field], f"{where}.{field}")
    if modern:
        for item, where in visit("screening", ("id", "search_id", "paper_id", "idea_ids", "stage", "decision", "reason", "screened_at")):
            reference(item.get("search_id"), f"{where}.search_id", "searches")
            reference(item.get("paper_id"), f"{where}.paper_id", "papers")
            references(item.get("idea_ids"), f"{where}.idea_ids", "ideas")
            choice(item.get("stage"), f"{where}.stage", ("metadata", "title_abstract", "full_text"))
            choice(item.get("decision"), f"{where}.decision", ("include", "exclude", "uncertain"))
            text(item.get("reason"), f"{where}.reason")
            date(item.get("screened_at"), f"{where}.screened_at")
            search = find("searches", item.get("search_id"))
            if search and isinstance(search.get("result_paper_ids"), list) and item.get("paper_id") not in search["result_paper_ids"]:
                fail(f"{where}.paper_id", "Paper must have been recorded in this search result")
            if item.get("decision") == "uncertain" and item.get("idea_ids"):
                warn(where, "Candidate-related screening is unresolved; do not claim complete coverage")
            if item.get("decision") == "exclude":
                for identifier in array(item.get("idea_ids")):
                    idea = find("ideas", identifier)
                    if idea and any(isinstance(nearest, dict) and nearest.get("paper_id") == item.get("paper_id") for nearest in array(idea.get("nearest_work"))):
                        warn(where, f"Excluded paper is also nearest work for {identifier}; explain the screening scope")
        for index, review in enumerate(collections["reviews"]):
            if not isinstance(review, dict):
                continue
            idea = find("ideas", review.get("idea_id"))
            if not idea or review.get("idea_version") != idea.get("version") or not isinstance(review.get("decision_basis"), dict):
                continue
            try:
                hash_value = _basis_hash(dossier, idea)
            except (ValueError, KeyError, TypeError, AttributeError):
                continue
            if review.get("review_basis_hash") != hash_value:
                continue
            where, basis = f"reviews[{index}].decision_basis", review["decision_basis"]
            attached = [*array(idea.get("evidence_ids")), *(identifier for nearest in array(idea.get("nearest_work")) if isinstance(nearest, dict) for identifier in array(nearest.get("evidence_ids")))]
            for identifier in array(basis.get("evidence_ids")):
                if identifier not in attached:
                    fail(f"{where}.evidence_ids", f"Evidence {identifier} is not attached to this candidate")
            for identifier in array(basis.get("pilot_ids")):
                pilot = find("pilots", identifier)
                if pilot and (pilot.get("idea_id"), pilot.get("idea_version")) != (idea.get("id"), idea.get("version")):
                    fail(f"{where}.pilot_ids", f"Pilot {identifier} is not from this candidate version")
            feasibility = idea.get("feasibility")
            if isinstance(feasibility, dict) and isinstance(feasibility.get("dependencies"), list):
                for name in array(basis.get("dependency_names")):
                    if not any(isinstance(dep, dict) and dep.get("name") == name for dep in feasibility["dependencies"]):
                        fail(f"{where}.dependency_names", f"Unknown current dependency {name}")
            constraints = project.get("constraints") if isinstance(project, dict) else None
            if isinstance(constraints, dict):
                for key in array(basis.get("constraint_keys")):
                    if not isinstance(key, str) or key not in constraints:
                        fail(f"{where}.constraint_keys", f"Unknown current constraint {key}")
    return report()


def _require_valid(dossier):
    result = validate_dossier(dossier)
    if not result["valid"]:
        raise ValueError("Invalid dossier:\n" + "\n".join(result["errors"]))


def _fold_results(dossier, idea_id, version):
    records = [row for row in dossier["pilots"] if row["idea_id"] == idea_id and row["idea_version"] == version]
    invalidated = {row["run_id"] for row in dossier["result_invalidations"] if row["idea_id"] == idea_id and row["idea_version"] == version}
    superseded = {row["supersedes"] for row in records if "supersedes" in row}
    runs = []
    for run_id in sorted({row["run_id"] for row in records}, key=_utf16):
        heads = _by_id([row for row in records if row["run_id"] == run_id and row["id"] not in superseded])
        eligible = run_id not in invalidated
        runs.append({"run_id": run_id, "eligible": eligible, "head_ids": [row["id"] for row in heads],
                     "ambiguous": len(heads) > 1, "contradiction": eligible and any(row["kind"] == "scientific" and row["outcome"] == "contradicted" for row in heads)})
    contradiction = any(run["contradiction"] for run in runs)
    ambiguity = any(run["eligible"] and run["ambiguous"] for run in runs)
    decisive_ids = {identifier for run in runs if run["eligible"] and not run["ambiguous"] for identifier in run["head_ids"]}
    refutations = sorted([row["id"] for row in records if row["id"] in decisive_ids and row["kind"] == "scientific" and row["outcome"] == "contradicted"], key=_utf16)
    idea = next(row for row in dossier["ideas"] if row["id"] == idea_id)
    claim_ids = {claim["id"] for claim in idea.get("claims", []) if "candidate_version" not in claim or claim["candidate_version"] == version}
    degraded = [{"result_id": row["id"], "claim_id": claim["claim_id"]} for row in records for claim in row["affected_claims"] if claim["claim_id"] not in claim_ids]
    warnings = [f"ambiguous run {run['run_id']}: multiple effective classification heads require HOLD" for run in runs if run["eligible"] and run["ambiguous"]]
    warnings.extend(f"affected_claims_degraded: unresolved claim {row['claim_id']} in result {row['result_id']}" for row in degraded)
    return {"runs": runs, "contradiction_blocker": contradiction, "ambiguity_blocker": ambiguity,
            "requires_hold": contradiction or ambiguity, "scientific_refutation_ids": refutations,
            "affected_claims_degraded": bool(degraded), "warnings": sorted(warnings, key=_utf16)}


def effective_result_state(dossier, idea_id, idea_version=None):
    _require_valid(dossier)
    if dossier["schema_version"] != 3:
        raise ValueError("Result lifecycle requires explicit schema v3 migration")
    idea = next((row for row in dossier["ideas"] if row["id"] == idea_id), None)
    if idea is None:
        raise ValueError(f"Unknown idea ID: {idea_id}")
    version = idea["version"] if idea_version is None else idea_version
    if not _positive(version) or version > idea["version"]:
        raise ValueError("Invalid candidate version")
    return _fold_results(dossier, idea_id, version)


def _basis_hash(dossier, idea):
    if dossier["schema_version"] not in (2, 3):
        return _digest({"project": dossier["project"], "config": dossier["config"], "searches": dossier["searches"],
                        "papers": dossier["papers"], "evidence": dossier["evidence"], "idea": idea,
                        "pilots": [row for row in dossier["pilots"] if row["idea_id"] == idea["id"]]})
    screening = [row for row in dossier["screening"] if isinstance(row, dict) and isinstance(row.get("idea_ids"), list) and idea["id"] in row["idea_ids"]]
    search_ids = set(idea["search_ids"]) | {row["search_id"] for row in screening}
    searches = [row for row in dossier["searches"] if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"] in search_ids]
    evidence_ids = set(idea["evidence_ids"]) | {identifier for row in idea["nearest_work"] for identifier in row["evidence_ids"]} | {row["evidence_id"] for row in idea["evidence_links"]}
    evidence = [row for row in dossier["evidence"] if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"] in evidence_ids]
    paper_ids = {identifier for row in searches for identifier in row["result_paper_ids"]} | {row["paper_id"] for row in evidence} | {row["paper_id"] for row in idea["nearest_work"]} | {row["paper_id"] for row in screening}
    semantic = _without(idea, ("created_at", "updated_at", "formatting"))
    semantic["evidence_ids"] = sorted(idea["evidence_ids"], key=_utf16)
    semantic["search_ids"] = sorted(idea["search_ids"], key=_utf16)
    semantic["nearest_work"] = sorted([{**row, "evidence_ids": sorted(row["evidence_ids"], key=_utf16)} for row in idea["nearest_work"]], key=lambda row: _utf16(canonical_stringify(row)))
    semantic["evidence_links"] = sorted(idea["evidence_links"], key=lambda row: _utf16(canonical_stringify(row)))
    payload = {"schema_version": dossier["schema_version"],
               "project": _without(dossier["project"], ("id", "created_at", "updated_at", "formatting")),
               "idea": semantic,
               "searches": [{**row, "result_paper_ids": sorted(row["result_paper_ids"], key=_utf16)} for row in _by_id(searches)],
               "papers": [_without(row, ("accessed_at", "created_at", "updated_at", "formatting")) for row in _by_id([row for row in dossier["papers"] if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"] in paper_ids])],
               "evidence": _by_id(evidence),
               "screening": [{**_without(row, ("screened_at",)), "idea_ids": [idea["id"]]} for row in _by_id(screening)],
               "pilots": _by_id([row for row in dossier["pilots"] if isinstance(row, dict) and row.get("idea_id") == idea["id"]])}
    if "decision_contract_version" in dossier:
        payload["decision_contract_version"] = dossier["decision_contract_version"]
    if dossier["schema_version"] == 3:
        payload["result_invalidations"] = _by_id([row for row in dossier["result_invalidations"] if isinstance(row, dict) and row.get("idea_id") == idea["id"]])
    return _digest(payload)


def fingerprint_idea(dossier, idea_id):
    _require_valid(dossier)
    idea = next((row for row in dossier["ideas"] if row["id"] == idea_id), None)
    if idea is None:
        raise ValueError(f"Unknown idea ID: {idea_id}")
    return _basis_hash(dossier, idea)


def ranking_config_hash(dossier):
    _require_valid(dossier)
    return _digest(dossier["config"]["ranking_weights"])


def migrate_dossier(dossier):
    """Pure migration; preserve old declarations and archive old authority."""
    _require_valid(dossier)
    if dossier["schema_version"] in (2, 3) and (dossier.get("decision_contract_version", 0) > DECISION_CONTRACT_VERSION or any(row.get("decision_contract_version", 0) > DECISION_CONTRACT_VERSION for row in dossier["reviews"])):
        raise ValueError("Cannot migrate an unsupported future decision contract; use a compatible tool and preserve the original record")
    if dossier["schema_version"] != 3 and "result_invalidations" in dossier and (not isinstance(dossier["result_invalidations"], list) or dossier["result_invalidations"]):
        raise ValueError("Legacy schema contains uninterpreted result_invalidations; explicitly inspect and migrate this material before converting, rather than activating or discarding withdrawals")
    migrated = deepcopy(dossier)
    from_v1, legacy, old_contract = migrated["schema_version"] == 1, migrated["schema_version"] != 3, migrated.get("decision_contract_version")
    migrated["schema_version"], migrated["decision_contract_version"] = 3, DECISION_CONTRACT_VERSION
    if migrated.get("screening") is None:
        migrated["screening"] = []
    if legacy:
        migrated["result_invalidations"] = []
        for pilot in migrated["pilots"]:
            pilot["run_id"] = pilot["id"]
            if pilot.get("affected_claims") is None:
                pilot["affected_claims"] = []
    for idea in migrated["ideas"]:
        if idea.get("evidence_links") is None:
            idea["evidence_links"] = []
    latest, peers = {}, {}
    for review in migrated["reviews"]:
        for mapping in (latest, peers) if review["kind"] == "independent" else (latest,):
            previous = mapping.get(review["idea_id"])
            if previous is None or _not_earlier(review["reviewed_at"], previous["reviewed_at"]):
                mapping[review["idea_id"]] = review
    retained = []
    for review in migrated["reviews"]:
        blocked = latest[review["idea_id"]].get("decision_contract_version") != DECISION_CONTRACT_VERSION or (review["kind"] == "independent" and peers[review["idea_id"]].get("decision_contract_version") != DECISION_CONTRACT_VERSION)
        if not legacy and old_contract == DECISION_CONTRACT_VERSION and review.get("decision_contract_version") == DECISION_CONTRACT_VERSION and not blocked:
            retained.append(review)
        else:
            migrated["history"].append({"event": "schema_v1_review_archived" if from_v1 else "decision_contract_review_archived",
                                        "idea_id": review["idea_id"], "idea_version": review["idea_version"],
                                        "reason": "Original review archived unchanged because a newer legacy review blocked its authority; migration must not revive an older approval." if blocked and review.get("decision_contract_version") == DECISION_CONTRACT_VERSION else "Original review archived unchanged; decision contract 3 requires explicit reassessment, not a rehashed old decision.",
                                        "original_review": review, "requires_reassessment": True})
    migrated["reviews"] = retained
    _require_valid(migrated)
    return migrated


def create_initial_dossier(name):
    if not isinstance(name, str) or len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError("Project name must use lowercase letters and digits separated by single hyphens (1–64 characters)")
    return {"schema_version": 3, "decision_contract_version": DECISION_CONTRACT_VERSION,
            "project": {"id": name, "question": "", "research_type": "empirical", "constraints": {}, "assumptions": []},
            "config": {"ranking_weights": {"scientific_value": 40, "differentiation": 35, "testability": 25}},
            **{name: [] for name in ("searches", "papers", "screening", "evidence", "ideas", "reviews", "pilots", "result_invalidations", "history")}}


class _ReceiptReport(dict):
    """Public JSON report; authority lives exclusively in the private registry."""


_verified_receipts = {}


def _remember_receipt(report, snapshot, bindings):
    identity = id(report)
    reference = weakref.ref(report, lambda _: _verified_receipts.pop(identity, None))
    _verified_receipts[identity] = (reference, snapshot, bindings)


def rank_dossier(dossier, *, receipt_verification=None):
    _require_valid(dossier)
    proof = _verified_receipts.get(id(receipt_verification))
    bindings = proof[2] if proof and proof[0]() is receipt_verification and proof[1] == _digest(dossier) else {}
    output = {"ranked": [], "held": [], "killed": [], "ranking_config_hash": ranking_config_hash(dossier), "notice": NOTICE}
    if dossier["schema_version"] != 3:
        output["held"] = [{"idea_id": idea["id"], "title": idea["title"], "decision": "HOLD", "score": None,
                           "reasons": [f"Schema v{dossier['schema_version']} needs explicit migration and reassessment; legacy reviews are not current v3 approvals"]} for idea in dossier["ideas"]]
        return output
    evidence = {row["id"]: row for row in dossier["evidence"]}
    searches = {row["id"]: row for row in dossier["searches"]}
    deep = lambda row: row is not None and row["read_scope"] in ("section", "full_text")
    weights = dossier["config"]["ranking_weights"]
    weight_sum = sum(weights[key] for key in DIMENSIONS)
    for idea in dossier["ideas"]:
        state = _fold_results(dossier, idea["id"], idea["version"])
        review, peer = None, None
        for candidate in dossier["reviews"]:
            if candidate["idea_id"] == idea["id"]:
                if review is None or _not_earlier(candidate["reviewed_at"], review["reviewed_at"]):
                    review = candidate
                if candidate["kind"] == "independent" and (peer is None or _not_earlier(candidate["reviewed_at"], peer["reviewed_at"])):
                    peer = candidate
        basis_hash = _basis_hash(dossier, idea)
        contract = dossier.get("decision_contract_version") == DECISION_CONTRACT_VERSION and review is not None and review.get("decision_contract_version") == DECISION_CONTRACT_VERSION
        current = review is not None and contract and review["idea_version"] == idea["version"] and review["review_basis_hash"] == basis_hash
        row = {"idea_id": idea["id"], "title": idea["title"], "decision": "HOLD", "score": None, "reasons": []}
        if review:
            row["review_id"] = review["id"]
        if review and not current:
            row["reasons"] = ["Latest review uses a legacy or unsupported decision contract; explicit migration and reassessment are required" if not contract else "Latest review is stale: idea version or basis hash changed; all decisions need reassessment"]
            output["held"].append(row)
            continue
        mandatory = [dep for dep in idea["feasibility"]["dependencies"] if dep["mandatory"]]
        basis = review["decision_basis"] if current else None
        if current and review["decision"] == "KILL":
            justified = False
            if basis["type"] == "duplicate" and review["decision_scope"] == "scientific_framing" and idea["novelty"]["status"] == "duplicate":
                decisive = [nearest for nearest in idea["nearest_work"] if nearest["decisive"]]
                justified = bool(decisive) and all(any(identifier in basis["evidence_ids"] and deep(evidence.get(identifier)) for identifier in nearest["evidence_ids"]) for nearest in decisive)
            elif basis["type"] == "scientific_refutation" and review["decision_scope"] == "scientific_framing":
                justified = any(link["decision_relevant"] and link["target"] == "hypothesis" and link["relation"] == "contradicts" and link["evidence_id"] in basis["evidence_ids"] and deep(evidence.get(link["evidence_id"])) for link in idea["evidence_links"]) or any(identifier in state["scientific_refutation_ids"] for identifier in basis["pilot_ids"])
            elif basis["type"] == "constraints" and review["decision_scope"] == "current_constraints":
                def confirmed(key):
                    constraint = dossier["project"]["constraints"].get(key)
                    return isinstance(constraint, dict) and constraint.get("status") == "confirmed" and _text(constraint.get("source")) and "value" in constraint and _fact(constraint["value"])
                justified = any(dep["status"] == "failed" and dep["name"] in basis["dependency_names"] and isinstance(dep.get("constraint_keys"), list) and any(key in basis["constraint_keys"] and confirmed(key) for key in dep["constraint_keys"]) for dep in mandatory)
            if justified:
                row.update(decision="KILL", decision_scope=review["decision_scope"], reasons=[f"Current {basis['type']} KILL ({review['decision_scope']}): {review['reason']}", basis["explanation"], "Recorded necessary conditions only; host must verify the cited evidence and constraints"])
                output["killed"].append(row)
            else:
                row["reasons"] = ["Current KILL lacks reason-specific decisive evidence or confirmed constraints; labels alone do not justify rejection"]
                output["held"].append(row)
            continue
        reasons = []
        if review is None:
            reasons.append("No review recorded")
        elif not current:
            reasons.append("Latest review is stale: idea version or basis hash changed; earlier reviews are not reused")
        else:
            if review["decision"] == "HOLD":
                reasons.append(f"Current review HOLD: {review['reason']}")
            for key in DIMENSIONS:
                if review["scores"][key] is None:
                    reasons.append(f"Unknown score: {key}")
            if basis["type"] != "advance":
                reasons.append("GO needs an explicit advance decision basis")
            if review["recommended_stage"] == "information_test":
                reasons.append("Information gathering remains HOLD; GO requires a bounded scientific pilot or validation")
        if idea["novelty"]["status"] not in ("distinct", "incremental"):
            reasons.append(f"Novelty needs evidence: {idea['novelty']['status']}")
        searched = [searches[identifier] for identifier in idea["search_ids"]]
        if not any(search["status"] in ("complete", "partial") and search["result_paper_ids"] for search in searched):
            reasons.append("No completed/partial candidate search with a paper result")
        if not idea["nearest_work"]:
            reasons.append("No nearest-work comparison")
        decisive = [nearest for nearest in idea["nearest_work"] if nearest["decisive"]]
        deep_nearest = lambda nearest: any(deep(evidence.get(identifier)) for identifier in nearest["evidence_ids"])
        if decisive:
            for nearest in decisive:
                if not deep_nearest(nearest):
                    reasons.append(f"Decisive nearest work lacks section/full_text evidence: {nearest['paper_id']}")
        elif idea["nearest_work"] and not any(deep_nearest(nearest) for nearest in idea["nearest_work"]):
            reasons.append("At least one nearest work needs section/full_text evidence")
        relevant = [link for link in idea["evidence_links"] if link["decision_relevant"] and link["role"] in ("motivation", "nearest_work", "contradiction", "assumption", "validation") and deep(evidence.get(link["evidence_id"]))]
        if not relevant:
            reasons.append("No decision-relevant section/full_text evidence linked to this candidate")
        if current and not any(link["evidence_id"] in basis["evidence_ids"] for link in relevant):
            reasons.append("Review decision basis must cite decision-relevant deep candidate evidence")
        if any(link["decision_relevant"] and link["relation"] == "contradicts" and link["target"] in ("hypothesis", "prerequisite", "validation") for link in idea["evidence_links"]):
            reasons.append("Decision-relevant contradiction to the current hypothesis, prerequisite, or validation needs reassessment")
        if state["contradiction_blocker"]:
            reasons.append("An effective scientific result contradicts this candidate version; a fresh GO label cannot erase the refutation")
        if state["ambiguity_blocker"]:
            reasons.append("An eligible run has multiple effective classification heads; ambiguous results require HOLD")
        if idea["feasibility"]["status"] != "ready":
            reasons.append(f"Feasibility is {idea['feasibility']['status']}: {idea['feasibility']['reason']}")
        for dependency in mandatory:
            if dependency["status"] != "met":
                reasons.append(f"Mandatory dependency not verified: {dependency['name']}")
        if idea["validation"]["status"] != "specified":
            reasons.append("Validation is not specified")
        peer_current = peer is not None and peer["idea_version"] == idea["version"] and peer["review_basis_hash"] == basis_hash and peer.get("decision_contract_version") == DECISION_CONTRACT_VERSION and peer["decision"] == "GO" and peer["decision_basis"]["type"] == "advance" and peer["recommended_stage"] == "full_validation" and bindings.get(peer["id"]) == _digest(peer) and all(peer["scores"][key] is not None for key in DIMENSIONS) and any(link["evidence_id"] in peer["decision_basis"]["evidence_ids"] for link in relevant)
        if current and review["recommended_stage"] == "full_validation" and not peer_current:
            reasons.append("Full validation needs an explicitly verified current independent GO full_validation receipt; a pilot approval cannot authorize escalation")
        if reasons:
            row["reasons"] = reasons
            output["held"].append(row)
            continue
        total = sum((review["scores"][key] / 4) * (weights[key] / weight_sum) * 100 for key in DIMENSIONS)
        penalty = sum(item["points"] for item in review["penalties"])
        score = math.floor(max(0, min(100, total - penalty)) * 100 + 0.5) / 100
        row.update(decision="GO", recommended_stage=review["recommended_stage"], score=score,
                   reasons=[review["reason"], "Recorded machine-checkable necessary conditions met; host evidence review is still required"])
        output["ranked"].append(row)
    output["ranked"].sort(key=lambda row: (-row["score"], _utf16(row["idea_id"])))
    return output


def _inside(root, target):
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def _directory_links(directory):
    cursor = Path(os.path.abspath(directory))
    while True:
        info = cursor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ValueError(f"Directory links are not allowed: {cursor}")
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"Root must be an existing directory: {cursor}")
        if cursor.parent == cursor:
            return
        cursor = cursor.parent


def create_review_receipt(review):
    if not isinstance(review, dict) or review.get("kind") != "independent" or review.get("decision_contract_version") != DECISION_CONTRACT_VERSION:
        raise ValueError("Receipt needs a contract-3 independent review")
    return {"receipt_version": 1, "review": json.loads(canonical_stringify(_without(review, ("artifact", "artifact_sha256"))))}


def verify_independent_receipts(dossier, *, root=None):
    """Verify bounded local bytes and retain private snapshot-bound authority."""
    _require_valid(dossier)
    if not _text(root):
        raise ValueError("Receipt verification requires an explicit existing local root")
    resolved_root = Path(os.path.abspath(root))
    _directory_links(resolved_root)
    real_root = resolved_root.resolve(strict=True)
    snapshot = _digest(dossier)
    report = _ReceiptReport(verified=[], failed=[], notice="Verifies receipt bytes and bindings at this read only; cannot prove honest evidence, real model independence, or later file immutability.")
    bindings = {}
    for review in (row for row in dossier["reviews"] if row["kind"] == "independent"):
        try:
            if dossier.get("decision_contract_version") != DECISION_CONTRACT_VERSION or review.get("decision_contract_version") != DECISION_CONTRACT_VERSION:
                raise ValueError("Legacy or unsupported decision contract")
            idea = next(row for row in dossier["ideas"] if row["id"] == review["idea_id"])
            if review["idea_version"] != idea["version"] or review["review_basis_hash"] != _basis_hash(dossier, idea):
                raise ValueError("Receipt belongs to stale candidate inputs")
            if not isinstance(review.get("artifact_sha256"), str) or not _HEX.fullmatch(review["artifact_sha256"]):
                raise ValueError("An expected artifact_sha256 is required before verification")
            artifact = review["artifact"]
            if re.match(r"^[a-z][a-z0-9+.-]*:", artifact, re.I) and not re.match(r"^[a-z]:[\\/]", artifact, re.I):
                raise ValueError("Only local file paths below the explicit root can be verified; URLs are not followed")
            target = Path(os.path.abspath(real_root / artifact))
            if target == real_root or not _inside(real_root, target):
                raise ValueError("Receipt path escapes the explicit root")
            _directory_links(target.parent)
            before = target.lstat()
            if stat.S_ISLNK(before.st_mode) or getattr(before, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or not stat.S_ISREG(before.st_mode):
                raise ValueError("Receipt must be a regular file, without symbolic links")
            if before.st_size > 1024 * 1024:
                raise ValueError("Receipt exceeds the 1 MiB read limit")
            if not _inside(real_root, target.resolve(strict=True)):
                raise ValueError("Receipt real path escapes the root")
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(target, flags)
            try:
                opened = os.fstat(descriptor)
                identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
                if not stat.S_ISREG(opened.st_mode) or identity(opened) != identity(before):
                    raise ValueError("Receipt changed before reading")
                chunks, remaining = [], before.st_size + 1
                while remaining:
                    chunk = os.read(descriptor, remaining)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                contents = b"".join(chunks)
                after, current = os.fstat(descriptor), target.lstat()
                if len(contents) != before.st_size or identity(after) != identity(before) or stat.S_ISLNK(current.st_mode) or getattr(current, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400) or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):
                    raise ValueError("Receipt changed while reading")
            finally:
                os.close(descriptor)
            sha = hashlib.sha256(contents).hexdigest()
            if sha != review["artifact_sha256"]:
                raise ValueError("Receipt SHA-256 does not match actual bytes")
            receipt = json.loads(contents.decode("utf-8", "replace"))
            if canonical_stringify(receipt) != canonical_stringify(create_review_receipt(review)):
                raise ValueError("Receipt review fields do not match the recorded candidate, decision, stage, inputs, or contexts")
            bindings[review["id"]] = _digest(review)
            report["verified"].append({"review_id": review["id"], "artifact_sha256": sha, "idea_id": review["idea_id"], "idea_version": review["idea_version"], "review_basis_hash": review["review_basis_hash"]})
        except (OSError, ValueError, StopIteration) as error:
            report["failed"].append({"review_id": review["id"], "reason": str(error)})
    if _digest(dossier) != snapshot:
        raise ValueError("Dossier changed during receipt verification; repeat with a stable snapshot")
    _remember_receipt(report, snapshot, bindings)
    return report


def init_project(root, name):
    """Create only a fresh directory below an existing non-linked user root."""
    dossier = create_initial_dossier(name)
    if not _text(root):
        raise ValueError("An existing root directory is required")
    resolved_root = Path(os.path.abspath(root))
    _directory_links(resolved_root)
    real_root = resolved_root.resolve(strict=True)
    target = real_root / name
    if target == real_root or not _inside(real_root, target):
        raise ValueError("Project path escapes the root")
    skill_root = Path(__file__).resolve().parents[2]
    if _inside(skill_root, target):
        raise ValueError("Projects must be created in a user workspace, outside the installed skill directory")
    if target.exists() or target.is_symlink():
        raise ValueError(f"Project path already exists: {target}")
    target.mkdir()
    try:
        _directory_links(target)
        destination = target / "dossier.json"
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(dossier, ensure_ascii=False, indent=2) + "\n")
        return {"project_dir": str(target), "dossier_path": str(destination)}
    except BaseException:
        try:
            target.rmdir()
        except OSError:
            pass
        raise
