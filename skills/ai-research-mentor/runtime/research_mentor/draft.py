"""Deterministic draft checks for user-facing research reports.

This is a structural and bookkeeping check, not a truth check. It verifies that
a draft declares its evidence tier, that inline citations resolve to reference
entries, that non-concept tiers do not cite unverified entries, that user-facing
labels (GO/HOLD/KILL) are absent, and that planned material does not appear in
result sections. It cannot verify that a cited source supports a claim, that a
number is correct, or that the research is good.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TIERS = ("concept_memo", "evidence_review", "preregistration", "research_plan")
VERIFIED_MARKERS = ("已核验", "已读全文", "verified")
UNVERIFIED_MARKERS = ("待核验", "未读", "未核验", "unverified")
FRONT_TIER = re.compile(r"<!--\s*report-tier:\s*([a-z_]+)\s*-->")
CITATION = re.compile(r"\[(\d{1,3})\]")
LABEL = re.compile(r"\b(?:GO|HOLD|KILL)\b")
CJK_LABEL = re.compile(r"做/等/放弃")
REF_HEADING = re.compile(r"^(#{1,4})\s+(参考文献|References?)\s*$", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,4})\s+(.+)$")


def _split_references(lines: list[str]) -> tuple[list[str], list[str], int | None]:
    for index, line in enumerate(lines):
        if REF_HEADING.match(line.strip()):
            return lines[:index], lines[index:], index
    return lines, [], None


def _reference_entries(lines: list[str]) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for raw in lines:
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key = re.fullmatch(r"\[(\d{1,3})\]", cells[0])
        if not key:
            continue
        body = " | ".join(cells[1:])
        entries[key.group(1)] = {"text": body, "status": cells[-1]}
    # Also accept list-style entries: [1] Title. ... 已读全文
    for raw in lines:
        line = raw.strip()
        match = re.match(r"^[-*]\s*\[(\d{1,3})\]\s*(.+)$", line)
        if match and match.group(1) not in entries:
            entries[match.group(1)] = {"text": match.group(2), "status": line}
    return entries


def _section_titles(body_lines: list[str]) -> list[str]:
    return [match.group(2).strip() for line in body_lines for match in [HEADING.match(line.strip())] if match]


def check_draft(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    front = FRONT_TIER.search(text)
    tier = front.group(1) if front else ""
    lines = text.splitlines()
    body, references, ref_index = _split_references(lines)
    body_text = "\n".join(body)
    entries = _reference_entries(references)
    sections = _section_titles(body)

    errors: list[str] = []
    warnings: list[str] = []

    if not tier:
        errors.append("missing <!-- report-tier: ... --> (choose concept_memo, evidence_review, preregistration or research_plan)")
    elif tier not in TIERS:
        errors.append(f"unknown report-tier: {tier!r}")

    used = sorted({match.group(1) for match in CITATION.finditer(body_text)}, key=int)
    if used and ref_index is None:
        errors.append("inline citations are used but no 参考文献/References section exists")
    if ref_index is not None and not entries:
        errors.append("reference section exists but no [n] entries could be parsed")

    missing = [key for key in used if key not in entries]
    for key in missing:
        errors.append(f"inline citation [{key}] has no reference entry")
    uncited = [key for key in entries if key not in used]
    if uncited:
        warnings.append("reference entries not used in the body: " + ", ".join(f"[{key}]" for key in sorted(uncited, key=int)))

    unverified_used = [key for key in used if key in entries and not any(marker in entries[key]["status"].lower() for marker in VERIFIED_MARKERS)]
    verified_count = sum(1 for key in used if key in entries and any(marker in entries[key]["status"].lower() for marker in VERIFIED_MARKERS))
    if tier and tier != "concept_memo":
        if unverified_used:
            errors.append("non-concept report cites unverified entries: " + ", ".join(f"[{key}]" for key in unverified_used))
        if not verified_count:
            errors.append("non-concept report has no citation marked 已核验/已读全文/verified")

    if LABEL.search(text):
        errors.append("user-facing labels GO/HOLD/KILL are present; answer the three questions instead")
    if CJK_LABEL.search(text):
        errors.append("user-facing phrase 做/等/放弃 is present; answer the three questions instead")

    if "当前判断与下一步" not in body_text:
        warnings.append("missing '当前判断与下一步' section")

    if tier == "concept_memo":
        head = text[:4000]
        if "概念备忘录" not in head or not any(marker in head for marker in ("未核验", "待核验", "未读全文")):
            errors.append("concept_memo must carry a visible 概念备忘录 + 未核验/待核验 banner in the opening")

    # Planned markers must not appear under result/outcome/abstract headings.
    current = ""
    for line in body:
        heading = HEADING.match(line.strip())
        if heading:
            current = heading.group(2).strip()
        if re.search(r"\[PLANNED:", line) and re.search(r"摘要|Abstract|结果|Results|结论|Conclusion", current, re.IGNORECASE):
            errors.append(f"planned material appears in a result/abstract section: {current or line.strip()[:40]}")

    todo_count = body_text.count("TODO(需来源)")
    if todo_count:
        warnings.append(f"{todo_count} TODO(需来源) placeholders remain; list them before delivery")

    return {
        "valid": not errors,
        "tier": tier,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "citations_used": len(used),
            "reference_entries": len(entries),
            "verified_citations": verified_count,
            "unverified_citations": len(unverified_used),
            "todo_placeholders": todo_count,
            "sections": sections,
        },
        "note": "Structural/bookkeeping checks only; not a truth check. It cannot verify source support, numbers, or research quality.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Check a user-facing research report draft (structural, not truth).")
    parser.add_argument("file")
    parser.add_argument("--json", action="store_true", help="print JSON (default)")
    args = parser.parse_args(argv)
    result = check_draft(args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
