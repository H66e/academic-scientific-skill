"""Draft contracts for user-facing research reports.

This is a structural and ledger-consistency checker, not a truth checker. It
enforces report tiers, section whitelists, citation forms, ledger-derived
reading status, quantitative-claim placement and user-facing label bans. It
cannot prove that a cited source supports a sentence, that numbers are correct,
or that a report is scientifically good.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
from typing import Any

TIERS = ("concept_memo", "evidence_review", "preregistration", "research_plan")
FRONT_TIER = re.compile(r"<!--\s*report-tier:\s*([a-z_]+)\s*-->")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CITATION = re.compile(r"\[(\d{1,3}(?:\s*[,，–-]\s*\d{1,3})*)\]")
CITATION_OTHER = [
    re.compile(r"\[\^[^\]]+\]"),
    re.compile(r"\[[^\]]*\]\([^)]+\)"),
    re.compile(r"\([A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?,?\s*\d{4}\)"),
    re.compile(r"\b10\.\d{4,9}/\S+"),
    re.compile(r"\barXiv:\s*\d", re.I),
    re.compile(r"https?://"),
    re.compile(r"［\d"),
]
LABEL = re.compile(r"(?:^|[^A-Za-z])(?:GO|HOLD|KILL)(?![A-Za-z])", re.M)
CJK_LABEL = re.compile(r"做\s*/\s*等\s*/\s*放弃")
LIGHT_LABEL = re.compile(r"[🟢🟡🔴✅❌]")
QUANT = re.compile(r"\d+(?:\.\d+)?\s*(?:%|pp|个百分点|倍)")
EFFECT_VERB = re.compile(r"提升|提高|优于|下降|降低|超过|改善|gain|improve|outperform|reduce", re.I)
COMPLETED_CLAIM = re.compile(r"已完成|已观察|观察到|结果表明|实验表明|we observed|results show|we found", re.I)

TIER_RULES: dict[str, dict[str, Any]] = {
    "concept_memo": {
        "required": [("当前判断", "当前判断与下一步"), ("待核验", "待核验清单", "问题")],
        "forbidden_headings": ["实验设计", "统计", "结果", "预算", "成本", "分工", "参考文献", "方法", "指标", "基线", "启动实验"],
        "forbidden_body": [re.compile(r"实验设计|统计检验|p\s*[<=]|α\s*=|置信区间|预算|GPU|样本量|n\s*=", re.I)],
        "allow_citations": False,
        "allow_references": False,
        "allow_quant": False,
    },
    "evidence_review": {
        "required": [("当前判断",), ("证据", "近邻", "相关工作"), ("覆盖", "待核验")],
        "forbidden_headings": ["实验设计", "统计", "结果", "计划", "分工", "预算", "启动实验", "预注册"],
        "forbidden_body": [re.compile(r"实验设计|统计检验|p\s*[<=]|置信区间|样本量|n\s*=", re.I)],
        "allow_citations": True,
        "allow_references": True,
        "allow_quant": False,
    },
    "preregistration": {
        "required": [("当前判断",), ("假设", "问题"), ("判据", "分析计划"), ("数据",)],
        "forbidden_headings": ["结果", "已观察", "已完成"],
        "forbidden_body": [],
        "allow_citations": True,
        "allow_references": True,
        "allow_quant": False,
    },
    "research_plan": {
        "required": [("当前判断",), ("假设", "问题"), ("实验设计", "方法"), ("风险", "停止")],
        "forbidden_headings": ["结果", "已观察", "已完成"],
        "forbidden_body": [],
        "allow_citations": True,
        "allow_references": True,
        "allow_quant": True,
    },
}
PLAN_SECTION = re.compile(r"分析计划|规模|成本|预算|实验设计|方法|计划|风险")


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return re.sub(r"[ \t]+", " ", text)


def _strip_comments(text: str) -> str:
    return HTML_COMMENT.sub("", text)


def _split_references(lines: list[str]) -> tuple[list[str], list[str], int | None]:
    for index, line in enumerate(lines):
        if re.match(r"^(#{1,4})\s+(参考文献|References?)\s*$", line.strip(), re.I):
            return lines[:index], lines[index:], index
    return lines, [], None


def _headings(lines: list[str]) -> list[tuple[int, str, int]]:
    result: list[tuple[int, str, int]] = []
    for index, raw in enumerate(lines):
        line = raw.strip()
        atx = re.match(r"^(#{1,6})\s+(.+)$", line)
        if atx:
            result.append((len(atx.group(1)), _norm(atx.group(2)), index))
            continue
        html = re.match(r"^<h([1-6])[^>]*>(.*?)</h\1>$", line, re.I)
        if html:
            result.append((int(html.group(1)), _norm(re.sub(r"<[^>]+>", "", html.group(2))), index))
            continue
        bold = re.fullmatch(r"\*\*(.+?)\*\*", line)
        if bold and len(bold.group(1)) <= 40:
            result.append((2, _norm(bold.group(1)), index))
            continue
        if index + 1 < len(lines) and re.fullmatch(r"=+|-+", lines[index + 1].strip()) and line:
            result.append((1 if "=" in lines[index + 1] else 2, _norm(line), index))
    return result


def _ref_entries(lines: list[str]) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in lines:
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        match = re.fullmatch(r"\[(\d{1,3})\]", cells[0])
        if match:
            entries[match.group(1)] = cells[-1] if len(cells) >= 3 else ""
    for raw in lines:
        match = re.match(r"^[-*]\s*\[(\d{1,3})\]\s*(.+)$", raw.strip())
        if match and match.group(1) not in entries:
            entries[match.group(1)] = raw.strip()
    return entries


def _ledger_verified(project: pathlib.Path) -> tuple[set[str], set[str]]:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from research_mentor.ledger import Ledger
    from research_mentor.readings import effective_readings

    events = Ledger(project).read()
    anchors = {}
    for event in events:
        if event.get("type") == "evidence.anchor":
            data = event.get("data", {})
            key = data.get("id", event["id"])
            anchors[key] = data
    verified_anchors: set[str] = set()
    verified_sources: set[str] = set()
    for anchor_id, data in anchors.items():
        confirmations = effective_readings(events, anchor_id)
        if any(c.get("actor") == "user" and c.get("trust") == "T1"
               and c.get("data", {}).get("scope") in {"section", "full_text"}
               for c in confirmations):
            verified_anchors.add(anchor_id)
            if isinstance(data.get("source"), str):
                verified_sources.add(data["source"])
    return verified_anchors, verified_sources


def check_draft(path: str | pathlib.Path, ledger: str | pathlib.Path | None = None) -> dict[str, Any]:
    target = pathlib.Path(path)
    raw = target.read_text(encoding="utf-8")
    text = _norm(raw)
    visible = _strip_comments(text)
    front = FRONT_TIER.search(raw)
    tier = front.group(1) if front else ""
    lines = visible.splitlines()
    body, references, ref_index = _split_references(lines)
    body_text = "\n".join(body)
    entries = _ref_entries(references)
    headings = _headings(body)
    headings_all = [title for _, title, _ in headings]
    errors: list[str] = []
    warnings: list[str] = []

    if not tier:
        errors.append("missing <!-- report-tier: ... -->")
    elif tier not in TIERS:
        errors.append(f"unknown report-tier: {tier!r}")
        tier = ""

    rules = TIER_RULES.get(tier, {})
    if rules:
        for alternatives in rules["required"]:
            if not any(any(alt in title for alt in alternatives) for title in headings_all):
                errors.append("missing required section: " + " / ".join(alternatives))
        for title in headings_all:
            if any(word in title for word in rules["forbidden_headings"]):
                errors.append(f"forbidden section for {tier}: {title}")
        for pattern in rules["forbidden_body"]:
            match = pattern.search(body_text)
            if match:
                errors.append(f"forbidden content for {tier}: {match.group(0)}")

    if ref_index is not None:
        for line in references[1:]:
            if re.match(r"^(#{1,6})\s+", line.strip()):
                errors.append("content heading appears after the reference section; references must be last")
                break

    used: list[str] = []
    for match in CITATION.finditer(body_text):
        for part in re.split(r"[,，–-]", match.group(1)):
            if part.strip():
                used.append(part.strip())
    used = sorted(set(used), key=int)
    if rules and not rules.get("allow_citations", True):
        if used:
            errors.append("concept_memo must not contain numbered citations; list unverified leads without [n]")
        if ref_index is not None:
            errors.append("concept_memo must not contain a reference section")
    for pattern in CITATION_OTHER:
        hit = pattern.search(body_text)
        if hit:
            errors.append(f"unsupported citation form: {hit.group(0)[:40]}; use [n] + ledger IDs")

    if rules and rules.get("allow_citations", True) and used:
        missing = [key for key in used if key not in entries]
        if missing:
            errors.append("inline citations without entries: " + ", ".join(f"[{key}]" for key in missing))
        if ledger is None:
            errors.append("this tier requires --ledger <project>; self-declared verification is not accepted")
        else:
            try:
                anchors, sources = _ledger_verified(pathlib.Path(ledger))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"ledger verification failed: {exc}")
                anchors, sources = set(), set()
            for key in used:
                status = entries.get(key, "")
                match = re.fullmatch(r"ledger:(\S+)", status)
                if not match:
                    errors.append(f"reference [{key}] must use ledger:<source-or-evidence-id>, got {status!r}")
                elif match.group(1) not in anchors and match.group(1) not in sources:
                    errors.append(f"reference [{key}] not verified by a user/T1 section/full_text reading in the ledger")
        if not entries:
            errors.append("reference section exists but no [n] entries were parsed")
        uncited = [key for key in entries if key not in used]
        if uncited:
            warnings.append("reference entries not used: " + ", ".join(f"[{key}]" for key in uncited))
    elif rules and rules.get("allow_citations", True) and not used:
        warnings.append("no citations; evidence_review/preregistration/research_plan should cite verified sources")

    if LABEL.search(text):
        errors.append("user-facing label GO/HOLD/KILL present; answer the three questions instead")
    if CJK_LABEL.search(text):
        errors.append("user-facing phrase 做/等/放弃 present; answer the three questions instead")
    if LIGHT_LABEL.search(text):
        errors.append("traffic-light/checkmark decision labels present")

    if rules:
        current = ""
        for line in body:
            heading = re.match(r"^#{1,6}\s+(.+)$", line.strip())
            if heading:
                current = _norm(heading.group(1))
            if QUANT.search(line) and EFFECT_VERB.search(line) and not PLAN_SECTION.search(current):
                if not rules.get("allow_quant", False) and "[PLANNED:" not in line:
                    errors.append("quantitative effect claim outside a plan/scaling section needs [PLANNED:] or a verified citation")
                elif not CITATION.search(line):
                    warnings.append("quantitative effect claim without a citation or plan marker")
            if COMPLETED_CLAIM.search(line) and tier != "research_plan":
                errors.append(f"completed/observed claim is not allowed in {tier}")

    if tier == "concept_memo":
        head = visible[:4000]
        if "概念备忘录" not in head or not any(marker in head for marker in ("未核验", "待核验", "未读全文")):
            errors.append("concept_memo needs a visible 概念备忘录 + 未核验/待核验 banner")
        if len(raw) > 12000:
            errors.append("concept_memo is too long for a decision memo (>12000 characters); shorten or choose a higher tier")

    if "当前判断与下一步" not in body_text:
        warnings.append("missing '当前判断与下一步' section")

    current = ""
    for line in body:
        heading = re.match(r"^#{1,6}\s+(.+)$", line.strip())
        if heading:
            current = _norm(heading.group(1))
        if "[PLANNED:" in line and re.search(r"摘要|Abstract|结果|Results|结论|Conclusion", current, re.I):
            errors.append("planned material appears in a result/abstract/conclusion section")

    todo = body_text.count("TODO(需来源)")
    if todo:
        warnings.append(f"{todo} TODO(需来源) placeholders remain")
    return {
        "valid": not errors,
        "delivery_ready": not errors and todo == 0,
        "tier": tier,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "citations_used": len(used),
            "reference_entries": len(entries),
            "todo_placeholders": todo,
            "verified_by_ledger": ledger is not None and bool(rules.get("allow_citations")),
            "sections": headings_all,
        },
        "note": "Structural/ledger-consistency checks only; not a truth check. It cannot prove source support, numbers, novelty or writing quality.",
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check a research report draft (structural, not truth).")
    parser.add_argument("file")
    parser.add_argument("--ledger", help="project directory containing a ledger; required for non-concept tiers")
    args = parser.parse_args(argv)
    result = check_draft(args.file, ledger=args.ledger)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
