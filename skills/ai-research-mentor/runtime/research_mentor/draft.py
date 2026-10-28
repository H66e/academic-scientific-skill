"""Tier-contract checks for research reports.

The checker parses the document, derives the highest allowed tier from a
verified local ledger, binds each citation to source identity/version/scope,
and rejects result-like claims without a plan marker or verified citation. It
cannot prove that a source supports a sentence, that numbers are correct, or
that the report is scientifically good.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
from typing import Any

from .report_tier import RANK, TIERS, derive_tier

FRONT_TIER = re.compile(r"<!--\s*report-tier:\s*([a-z_]+)\s*-->")
DOC_KIND = re.compile(r"<!--\s*doc-kind:\s*([a-z_]+)\s*-->")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CITATION = re.compile(r"\[(\d{1,3}(?:\s*[,，–-]\s*\d{1,3})*)\]")
OTHER_CITATIONS = [
    re.compile(r"\[\^[^\]]+\]"),
    re.compile(r"\[[A-Za-z][A-Za-z\-]+\s+\d{4}\]"),
    re.compile(r"\([A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?\s*,?\s*\d{4}\)"),
    re.compile(r"[A-Z][A-Za-z\-]+\s*\(\s*\d{4}\s*\)"),
    re.compile(r"\b10\.\d{4,9}/\S+"),
    re.compile(r"\barXiv\s*:?\s*\d", re.I),
    re.compile(r"https?://"),
    re.compile(r"arxiv\.org/abs/\S+", re.I),
    re.compile(r"［\d"),
]
LABEL = re.compile(r"(?:^|[^A-Za-z])(?:GO|HOLD|KILL)(?![A-Za-z])", re.M)
CJK_LABEL = re.compile(r"做\s*/\s*等\s*/\s*放弃")
LIGHT_LABEL = re.compile(r"[🟢🟡🔴✅❌]")
QUANT = re.compile(r"\d+(?:\.\d+)?\s*(?:%|pp|个百分点|倍)")
EFFECT = re.compile(r"提升|提高|优于|下降|降低|超过|改善|gain|improve|outperform|reduce", re.I)
COMPLETED = re.compile(r"实验表明|结果表明|我们观察到|we observed|results show|已完成(?:实验|训练|评测|测试|主实验)", re.I)
PLANNED = re.compile(r"\[PLANNED:[^\]]*\]")
TODO = "TODO(需来源)"
PLAN_HEADING = re.compile(r"计划|预注册|实验设计|方法|规模|成本|风险|分析")

COMMON_HEADINGS = {"报告等级与范围"}
ALLOWED: dict[str, set[str]] = {
    "concept_memo": {"当前判断与下一步", "问题与未知", "待核验线索", "下一步", "暂定判断（C 级）"},
    "evidence_review": {"当前判断与下一步", "近邻选择与深读记录", "主张—证据等级", "暂定判断（C 级）",
                        "证据、近邻与差异", "反例、冲突与替代解释",
                        "覆盖边界与待核验清单", "参考文献"},
    "preregistration": {"当前判断与下一步", "近邻选择与深读记录", "主张—证据等级", "暂定判断（C 级）",
                        "研究问题、假设与判据", "数据与划分", "分析计划与停止判据",
                        "风险与替代解释", "参考文献"},
    "research_plan": {"当前判断与下一步", "近邻选择与深读记录", "主张—证据等级", "暂定判断（C 级）",
                      "研究问题、假设与判据", "方法与实验设计", "规模、成本与资源",
                      "计划与分工", "风险与继续/停止判据", "参考文献"},
}
REQUIRED: dict[str, list[str]] = {
    "concept_memo": ["当前判断与下一步", "待核验线索", "下一步"],
    "evidence_review": ["当前判断与下一步", "近邻选择与深读记录", "主张—证据等级",
                        "证据、近邻与差异", "覆盖边界与待核验清单"],
    "preregistration": ["当前判断与下一步", "近邻选择与深读记录", "主张—证据等级",
                        "研究问题、假设与判据", "分析计划与停止判据"],
    "research_plan": ["当前判断与下一步", "近邻选择与深读记录", "主张—证据等级",
                      "研究问题、假设与判据", "方法与实验设计", "风险与继续/停止判据"],
}
CONCEPT_MAX = 4000


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Cf")


def _visible(text: str) -> str:
    return HTML_COMMENT.sub("", text)


def _title(text: str) -> str:
    text = _norm(text).strip()
    return re.sub(r"^\d+(?:\.\d+)*\s+", "", text)


def _headings(lines: list[str]) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for index, raw in enumerate(lines):
        line = raw.strip()
        atx = re.match(r"^(#{1,6})\s+(.+)$", line)
        if atx:
            found.append((_title(atx.group(2)), index))
            continue
        html = re.match(r"^<h([1-6])[^>]*>(.*?)</h\1>$", line, re.I)
        if html:
            found.append((_title(re.sub(r"<[^>]+>", "", html.group(2))), index))
            continue
        bold = re.fullmatch(r"\*\*(.+?)\*\*", line)
        if bold and len(bold.group(1)) <= 40:
            found.append((_title(bold.group(1)), index))
            continue
        if index + 1 < len(lines) and re.fullmatch(r"=+|-+", lines[index + 1].strip()) and line:
            found.append((_title(line), index))
    return found


def _ref_section(lines: list[str]) -> tuple[list[str], list[str], int | None]:
    for index, line in enumerate(lines):
        if _title(re.sub(r"^#+\s*", "", line.strip())) in {"参考文献", "References"}:
            return lines[:index], lines[index:], index
    return lines, [], None


def _ref_rows(lines: list[str]) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for raw in lines:
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        match = re.fullmatch(r"\[(\d{1,3})\]", cells[0]) if cells else None
        if match and len(cells) == 5:
            rows[match.group(1)] = cells[1:]
    return rows


def _token_jaccard(left: str, right: str) -> float:
    a = set(re.findall(r"[\w\u4e00-\u9fff]+", unicodedata.normalize("NFKC", left).lower()))
    b = set(re.findall(r"[\w\u4e00-\u9fff]+", unicodedata.normalize("NFKC", right).lower()))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _check_identity(identifier: str, title: str, view: dict, scope: str) -> list[str]:
    errors = []
    expected_doi = (view.get("doi") or "").lower() if isinstance(view.get("doi"), str) else ""
    expected_arxiv = (view.get("arxiv") or "").lower() if isinstance(view.get("arxiv"), str) else ""
    expected_title = view.get("title") or ""
    ident = identifier.strip()
    if ident.lower().startswith("doi:"):
        if not expected_doi or ident[4:].strip().lower() != expected_doi:
            errors.append("CITATION_IDENTITY_MISMATCH (DOI)")
    elif ident.lower().startswith("arxiv:"):
        actual = ident[6:].strip().lower()
        if not expected_arxiv or actual != expected_arxiv:
            errors.append("CITATION_IDENTITY_MISMATCH (arXiv/version)")
    elif ident.lower().startswith("url:"):
        if not view.get("url") or ident[4:].strip() != view["url"]:
            errors.append("CITATION_IDENTITY_MISMATCH (URL)")
    else:
        errors.append("UNIDENTIFIABLE_CITATION (use doi:, arXiv: or url:)")
    if expected_title and _token_jaccard(title, expected_title) < 0.8:
        errors.append("CITATION_TITLE_MISMATCH")
    scopes = [item for reading in view.get("readings", []) for item in reading.get("scopes", [])]
    if scope == "full_text" and "full_text" not in scopes:
        errors.append("CITATION_SCOPE_EXCEEDS_READING (full_text)")
    if scope.startswith("section") and not ({"section", "full_text"} & set(scopes)):
        errors.append("CITATION_SCOPE_EXCEEDS_READING (section)")
    return errors




def _section_text(lines: list[str], title: str) -> str:
    start = next((i for i, line in enumerate(lines) if _title(re.sub(r"^#+\s*", "", line.strip())) == _title(title)), None)
    if start is None:
        return ""
    out = []
    for line in lines[start + 1:]:
        if re.match(r"^#{1,6}\s+", line.strip()):
            break
        out.append(line)
    return "\n".join(out)


def _claim_rows(text: str) -> list[list[str]]:
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 5 and cells[0] not in {"编号", "---"} and not cells[0].startswith("---"):
            rows.append(cells[:5])
    return rows


def check_draft(path: str | pathlib.Path, ledger: str | pathlib.Path | None = None) -> dict[str, Any]:
    target = pathlib.Path(path)
    raw = target.read_text(encoding="utf-8")
    text = _norm(raw)
    visible = _visible(text)
    tiers = FRONT_TIER.findall(raw)
    kind = DOC_KIND.search(raw)
    errors: list[str] = []
    warnings: list[str] = []
    projections = None
    if len(tiers) != 1:
        errors.append("REPORT_TIER_MARKER must appear exactly once")
        tier = ""
    else:
        tier = tiers[0]
        if tier not in TIERS:
            errors.append(f"UNKNOWN_REPORT_TIER {tier!r}")
            tier = ""
    if kind and kind.group(1) != "report":
        errors.append(f"UNSUPPORTED_DOC_KIND {kind.group(1)!r}; draft checker only supports reports")

    lines = visible.splitlines()
    body, refs, ref_index = _ref_section(lines)
    body_text = "\n".join(body)
    headings = _headings(body)
    if headings:
        headings = headings[1:]  # first heading is the document title
    titles = [title for title, _ in headings]
    if tier in {"evidence_review", "preregistration", "research_plan"} and ledger is not None and projections is None:
        try:
            projections = derive_tier(pathlib.Path(ledger))
        except Exception:  # noqa: BLE001
            projections = None
    if tier in {"evidence_review", "preregistration", "research_plan"}:
        nearest = _section_text(body, "近邻选择与深读记录")
        query_values = []
        for line in nearest.splitlines():
            if re.search(r"检索式|query", line, re.I):
                value = re.split(r"[:：]", line, maxsplit=1)[-1].strip() if re.search(r"[:：]", line) else ""
                if value and "[" not in value:
                    query_values.append(value)
        if len(set(query_values)) < 2:
            errors.append("NEAREST_SELECTION_REQUIRES_TWO_DISTINCT_QUERIES")
        data_rows = []
        for line in nearest.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")] if line.strip().startswith("|") else []
            if len(cells) >= 6 and cells[0] not in {"近邻", "---"} and not cells[0].startswith("---"):
                data_rows.append(cells)
        if not data_rows:
            errors.append("NEAREST_SELECTION_TABLE_MISSING")
        for row in data_rows:
            if any("[" in cell for cell in row[2:]):
                errors.append("NEAREST_SELECTION_PLACEHOLDERS_REMAIN")
            if not row[3] or not row[4] or not row[5]:
                errors.append("KILL_QUESTION_ANSWER_LOCATOR_REQUIRED")
        claims = _claim_rows(_section_text(body, "主张—证据等级"))
        if not claims:
            errors.append("CLAIM_EVIDENCE_TABLE_MISSING")
        else:
            graded = [row for row in claims if row[2] in {"A", "B"}]
            if not graded:
                warnings.append("NO_A_OR_B_GRADE_CLAIM (C-only report)")
            current = _section_text(body, "当前判断与下一步")
            has_c = False
            for row in claims:
                grade = row[2]
                if grade not in {"A", "B", "C"}:
                    errors.append(f"INVALID_CLAIM_GRADE {grade!r}")
                    continue
                if not row[4].strip():
                    errors.append("CLAIM_NEEDS_FLIP_CONDITION")
                if grade == "C":
                    has_c = True
                    outside = body_text.replace(_section_text(body, "暂定判断（C 级）"), "").replace(_section_text(body, "主张—证据等级"), "")
                    if row[1][:20] and row[1][:20] in outside:
                        errors.append("C_CLAIM_STATED_OUTSIDE_PROVISIONAL_SECTION")
                else:
                    if not row[3].strip("`").startswith("ledger:"):
                        errors.append("A_B_CLAIM_NOT_LEDGER_BOUND")
                    elif projections:
                        link = row[3].strip("`")[7:].strip()
                        source = link if link in projections["sources"] else projections["anchor_to_source"].get(link)
                        view = projections["sources"].get(source) if source else None
                        if not view or not view.get("readings"):
                            errors.append("A_B_CLAIM_NOT_VERIFIED")
            if has_c:
                c_text = _section_text(body, "暂定判断（C 级）")
                if not c_text or "翻转条件" not in c_text or "最小核验" not in c_text or "获取路径" not in c_text:
                    errors.append("C_CLAIM_SECTION_INCOMPLETE")
                for row in claims:
                    if row[2] == "C" and row[0] not in c_text:
                        errors.append(f"C_CLAIM_ID_MISSING_FROM_PROVISIONAL_SECTION {row[0]}")

    if ref_index is not None:
        for line in refs[1:]:
            if line.strip() and not line.strip().startswith("|"):
                errors.append("CONTENT_AFTER_REFERENCES")
                break
        extra = _headings(refs[1:])
        if extra:
            errors.append("CONTENT_AFTER_REFERENCES")

    allowed = {_title(item) for item in (COMMON_HEADINGS | ALLOWED.get(tier, set()))}
    for title in titles:
        if _title(title) not in allowed:
            errors.append(f"HEADING_NOT_ALLOWED {title!r}")
    for needed in REQUIRED.get(tier, []):
        if _title(needed) not in titles:
            errors.append(f"MISSING_SECTION {needed!r}")

    body_text = "\n".join(body)
    used: list[str] = []
    for match in CITATION.finditer(body_text):
        for part in re.split(r"[,，–-]", match.group(1)):
            if part.strip():
                used.append(part.strip())
    used = sorted(set(used), key=int)
    for pattern in OTHER_CITATIONS:
        hit = pattern.search(body_text)
        if hit:
            errors.append(f"UNSUPPORTED_CITATION_FORM {hit.group(0)[:40]!r}")

    if tier == "concept_memo":
        if used:
            errors.append("CONCEPT_MEMO_CITATIONS_FORBIDDEN")
        if ref_index is not None:
            errors.append("CONCEPT_MEMO_REFERENCES_FORBIDDEN")
        if len(re.sub(r"\s", "", visible)) > CONCEPT_MAX:
            errors.append("CONCEPT_MEMO_TOO_LONG")
    elif tier:
        if ledger is None:
            errors.append("LEDGER_REQUIRED")
        else:
            if projections is None:
                try:
                    projections = derive_tier(pathlib.Path(ledger))
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"LEDGER_VERIFICATION_FAILED {exc}")
                    projections = None
            if projections:
                if not projections["chain_ok"]:
                    errors.append("LEDGER_CHAIN")
                if not projections["artifacts_ok"]:
                    errors.append("ARTIFACT_REPLAY")
                if projections["chain_ok"] and projections["artifacts_ok"]:
                    if RANK.get(tier, 99) > RANK.get(projections["derived_tier"], 0):
                        errors.append(f"TIER_EXCEEDS_EVIDENCE declared={tier} derived={projections['derived_tier']}")
                    elif RANK.get(tier, 99) < RANK.get(projections["derived_tier"], 0):
                        warnings.append(f"DOWNGRADED declared={tier} derived={projections['derived_tier']}")
        if not used:
            errors.append("NO_VERIFIED_CITATIONS")
        rows = _ref_rows(refs)
        if len(rows) < 2:
            errors.append("TOO_FEW_REFERENCE_ENTRIES")
        seen_canonical = set()
        for key in used:
            row = rows.get(key)
            if not row:
                errors.append(f"CITATION_WITHOUT_ENTRY [{key}]")
                continue
            title, identifier, binding, scope = row
            if not binding.startswith("ledger:"):
                errors.append(f"CITATION_NOT_LEDGER_BOUND [{key}]")
                continue
            source_id = binding[7:].strip()
            if projections:
                source = source_id if source_id in projections["sources"] else projections["anchor_to_source"].get(source_id)
                view = projections["sources"].get(source) if source else None
                if not view or not view.get("readings"):
                    errors.append(f"CITATION_NOT_VERIFIED [{key}]")
                    continue
                if view["canonical"] in seen_canonical:
                    errors.append("DUPLICATE_SOURCE")
                seen_canonical.add(view["canonical"])
                errors.extend(f"{code} [{key}]" for code in _check_identity(identifier, title, view, scope))
            else:
                errors.append(f"CITATION_UNCHECKED [{key}]")

    # Labels (GO term/Gene Ontology are not decision labels).
    label_text = re.sub(r"\bGO\s+(?:term|terms|enrichment|annotation|ontology|analysis)\b", "", text, flags=re.I)
    label_text = re.sub(r"Gene Ontology", "", label_text, flags=re.I)
    if LABEL.search(label_text):
        errors.append("USER_FACING_LABEL")
    if CJK_LABEL.search(label_text):
        errors.append("USER_FACING_LABEL")
    if LIGHT_LABEL.search(label_text):
        errors.append("USER_FACING_LABEL")

    # Effect/completed claims are line-local; no whole-section exemption.
    for line in body:
        if QUANT.search(line) and EFFECT.search(line):
            if tier == "concept_memo":
                errors.append("EFFECT_CLAIM_IN_CONCEPT_MEMO")
            elif not PLANNED.search(line) and not CITATION.search(line):
                errors.append("UNSUPPORTED_EFFECT_CLAIM")
        if COMPLETED.search(line) and not CITATION.search(line):
            errors.append("COMPLETED_CLAIM_WITHOUT_CITATION")

    todo = body_text.count(TODO)
    if todo:
        warnings.append(f"{todo} TODO(需来源) placeholders remain")
    if ref_index is not None and tier != "concept_memo":
        unused = [key for key in _ref_rows(refs) if key not in used]
        if unused:
            warnings.append("UNUSED_REFERENCE_ENTRIES " + ",".join(unused))
    delivery_ready = not errors and todo == 0 and not any("UNUSED_REFERENCE" in warning for warning in warnings)
    return {
        "valid": not errors,
        "delivery_ready": delivery_ready,
        "declared_tier": tier,
        "derived_tier": projections["derived_tier"] if projections else None,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "citations_used": len(used),
            "reference_entries": len(_ref_rows(refs)),
            "verified_citations": len(used) if projections and not errors else 0,
            "distinct_sources": len({row[2] for row in _ref_rows(refs).values()}),
            "chain_ok": projections["chain_ok"] if projections else None,
            "artifacts_ok": projections["artifacts_ok"] if projections else None,
            "todo_placeholders": todo,
        },
        "attestation": "user-attested readings; not authenticated",
        "note": "Structure/ledger-consistency only; not a truth check. It cannot prove source support, numbers, novelty or writing quality.",
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
