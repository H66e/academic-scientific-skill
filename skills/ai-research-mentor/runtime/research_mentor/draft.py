"""Tier-contract checks for research reports.

The checker parses the document, derives the highest allowed tier from a
verified local ledger, binds claim rows to nearest-set candidates, ledger
readings and a structured provisional block, and rejects result-like claims
without a plan marker or verified citation.

It is a structural and recorded-evidence checker. It cannot prove that a
source supports a sentence, that a nearest set is complete, that the
kill-question answers are honest, or that the report is scientifically good.
"""
from __future__ import annotations

import datetime as dt
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

NEAREST_SCHEMA = "nearest-set-v2"
PROVISIONAL_SCHEMA = "provisional-v1"
NEAREST_BLOCK = re.compile(r"```nearest-set-json\s*(.*?)```", re.S)
PROVISIONAL_BLOCK = re.compile(r"```provisional-json\s*(.*?)```", re.S)
CODE_FENCE = re.compile(r"```.*?```", re.S)
CLAIM_REF = re.compile(r"\[(C\d+)\]")
CLAIM_ID = re.compile(r"^C[1-9][0-9]*$")
CANDIDATE_ID = re.compile(r"^P[1-9][0-9]*$")
PLAN_PREFIX = re.compile(r"^(?:[-*]\s*)?(?:下一步|行动|核验动作|获取路径|成本与停止)")
JUDGMENT_TERMS = re.compile(
    r"新颖|首次提出|首次实现|研究空白|尚无工作|没有相关工作|机制等价|值得投入|值得做|不建议投入")
ABSOLUTE_NOVELTY = re.compile(r"首次|第一个|全新|史无前例")
LOCATOR_PATTERN = re.compile(
    r"(?:§\s*\d+(?:\.\d+)*"
    r"|(?:Table|Tab\.)\s*\d+[A-Za-z]?"
    r"|(?:Figure|Fig\.?)\s*\d+[A-Za-z]?"
    r"|[Pp]\.\s*\d+"
    r"|(?:第\s*)?\d+(?:\.\d+)*\s*(?:节|章|页)"
    r"|(?:表|图)\s*\d+"
    r"|Appendix\s+[A-Z0-9]+"
    r"|附录\s*[A-Z0-9一二三四五六七八九十]+)")
LOCATOR_SPLIT = re.compile(r"[,，、;；/]")
LOCATOR_SPECIAL = {"无", "未读", "未读到", "未获取", "未找到", "n/a", "notread", "摘要"}
LOCATOR_TOKEN = re.compile(r"\d+(?:\.\d+)*")
ANSWER_ALLOWED = {"是", "否", "未读到"}
PLACEHOLDER_TERMS = (
    "新颖", "首次提出", "首次实现", "研究空白", "尚无工作", "没有相关工作",
    "机制等价", "值得投入", "值得做", "不建议投入",
)
STATUS_ALLOWED = {"full_text", "section", "abstract", "unseen"}
READER_ALLOWED = {"model", "user"}
CANDIDATE_FIELDS = ("title", "rationale", "status", "reader", "ledger", "locator")
PLACEHOLDER_FRAGMENTS = (
    "检索式 1", "检索式1", "检索式 2", "检索式2", "术语/数据库", "为什么最接近",
    "可能漏掉什么", "第二个致命问题", "第二个候选", "第二篇候选", "若答案是 Y",
    "若答案是Y", "什么发现会推翻", "是/否/未读到", "哪个主张不成立",
    "第二个候选的致命问题",
)
FILLER = {"x", "xx", "xxx", "...", "……", "示例", "待填", "todo"}
CLAIM_BEARING = {"当前判断与下一步", "主张—证据等级", "暂定判断（C 级）", "参考文献"}

COMMON_HEADINGS = {"报告等级与范围"}
ALLOWED: dict[str, set[str]] = {
    "concept_memo": {"当前判断与下一步", "问题与未知", "待核验线索", "下一步", "暂定判断（C 级）"},
    "evidence_review": {"当前判断与下一步", "近邻选择与深读记录", "主张—证据等级", "暂定判断（C 级）",
                        "证据、近邻与差异", "反例、冲突与替代解释",
                        "覆盖边界与待核验清单", "参考文献", "附录：机器可读块"},
    "preregistration": {"当前判断与下一步", "近邻选择与深读记录", "主张—证据等级", "暂定判断（C 级）",
                        "研究问题、假设与判据", "数据与划分", "分析计划与停止判据",
                        "风险与替代解释", "参考文献", "附录：机器可读块"},
    "research_plan": {"当前判断与下一步", "近邻选择与深读记录", "主张—证据等级", "暂定判断（C 级）",
                      "研究问题、假设与判据", "方法与实验设计", "规模、成本与资源",
                      "计划与分工", "风险与继续/停止判据", "参考文献", "附录：机器可读块"},
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


def _clean(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("`", "").strip()


def _norm_cell(value: Any) -> str:
    return re.sub(r"\s+", "", _norm(_clean(value))).casefold()


def _placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    text = _norm(value).replace("`", "").strip()
    if not text:
        return True
    lowered = text.casefold()
    if lowered in FILLER:
        return True
    if re.fullmatch(r"\[.*\]", text):
        return True
    return any(fragment in text for fragment in PLACEHOLDER_FRAGMENTS)


def _substantive(value: Any, minimum: int) -> bool:
    if _placeholder(value):
        return False
    text = _norm(_clean(value))
    return len(re.sub(r"\s", "", text)) >= minimum


def _locator_ok(value: Any, *, allow_special: bool = False) -> bool:
    text = _clean(value)
    if _placeholder(text):
        return False
    parts = [part.strip() for part in LOCATOR_SPLIT.split(_norm(text)) if part.strip()]
    if not parts:
        return False
    for part in parts:
        if LOCATOR_PATTERN.fullmatch(part):
            continue
        if allow_special and _norm_cell(part) in LOCATOR_SPECIAL:
            continue
        return False
    return True


LOCATOR_TYPED = (
    (re.compile(r"§\s*(\d+(?:\.\d+)*)"), "section"),
    (re.compile(r"(?:Table|Tab\.)\s*(\d+[A-Za-z]?)"), "table"),
    (re.compile(r"(?:Figure|Fig\.?)\s*(\d+[A-Za-z]?)"), "figure"),
    (re.compile(r"[Pp]\.\s*(\d+)"), "page"),
    (re.compile(r"(?:第\s*)?(\d+(?:\.\d+)*)\s*(?:节|章|页)"), "section-cn"),
    (re.compile(r"(?:表|图)\s*(\d+)"), "table-cn"),
    (re.compile(r"Appendix\s+([A-Z0-9]+)"), "appendix"),
    (re.compile(r"附录\s*([A-Z0-9一二三四五六七八九十]+)"), "appendix-cn"),
)


LOCATOR_KIND_ALIAS = {"section-cn": "section", "table-cn": "table", "appendix-cn": "appendix"}


def _locator_tokens(value: Any) -> set[tuple[str, str]]:
    tokens: set[tuple[str, str]] = set()
    for part in LOCATOR_SPLIT.split(_norm(_clean(value))):
        part = part.strip()
        if not part:
            continue
        for pattern, kind in LOCATOR_TYPED:
            match = pattern.fullmatch(part)
            if match:
                tokens.add((LOCATOR_KIND_ALIAS.get(kind, kind), match.group(1)))
                break
    return tokens


def _locator_matches(left: Any, right: Any) -> bool:
    """Compare locators by type and numeric prefix; §2 never matches Table 2."""
    left_tokens, right_tokens = _locator_tokens(left), _locator_tokens(right)
    for left_kind, left_number in left_tokens:
        for right_kind, right_number in right_tokens:
            if left_kind != right_kind:
                continue
            if (left_number == right_number
                    or left_number.startswith(right_number + ".")
                    or right_number.startswith(left_number + ".")):
                return True
    return False


def _reading_locators(view: dict) -> list[str]:
    locators: list[str] = []
    for reading in view.get("readings") or []:
        if not isinstance(reading, dict):
            continue
        locator = reading.get("locator")
        if isinstance(locator, str) and _locator_ok(locator):
            locators.append(locator.strip())
    return locators


def _today() -> dt.date:
    return dt.date.today()


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
        if bold and len(bold.group(1)) <= 40 and "：" not in bold.group(1) and ":" not in bold.group(1):
            found.append((_title(bold.group(1)), index))
            continue
        if index + 1 < len(lines) and re.fullmatch(r"=+|-+", lines[index + 1].strip()) and line:
            found.append((_title(line), index))
    return found


def _sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    titles = {index: title for title, index in _headings(lines)}
    result: list[tuple[str, list[str]]] = []
    current_title = ""
    current: list[str] = []
    for index, line in enumerate(lines):
        if index in titles:
            result.append((current_title, current))
            current_title = titles[index]
            current = []
        else:
            current.append(line)
    result.append((current_title, current))
    return result


def _section_text(lines: list[str], title: str) -> str:
    start = next((i for i, line in enumerate(lines)
                  if _title(re.sub(r"^#+\s*", "", line.strip())) == _title(title)), None)
    if start is None:
        return ""
    out = []
    for line in lines[start + 1:]:
        if re.match(r"^#{1,6}\s+", line.strip()):
            break
        out.append(line)
    return "\n".join(out)


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
        cells = [_clean(cell) for cell in line.strip("|").split("|")]
        match = re.fullmatch(r"\[(\d{1,3})\]", cells[0]) if cells else None
        if match and len(cells) == 5:
            rows[match.group(1)] = cells[1:]
    return rows


def _claim_rows(text: str) -> tuple[list[list[str]], list[str]]:
    rows: list[list[str]] = []
    errors: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] in {"编号", "---"} or re.fullmatch(r":?-{3,}:?", cells[0]):
            continue
        if len(cells) != 6:
            errors.append("CLAIM_TABLE_COLUMNS")
            continue
        rows.append(cells)
    return rows, errors


def _token_jaccard(left: str, right: str) -> float:
    a = set(re.findall(r"[\w\u4e00-\u9fff]+", unicodedata.normalize("NFKC", left).lower()))
    b = set(re.findall(r"[\w\u4e00-\u9fff]+", unicodedata.normalize("NFKC", right).lower()))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _projection_view(projections: dict | None, ledger_id: str) -> dict | None:
    if not projections or not ledger_id:
        return None
    sources = projections.get("sources") or {}
    source = ledger_id if ledger_id in sources else (projections.get("anchor_to_source") or {}).get(ledger_id)
    return sources.get(source) if source else None


def _projection_source_id(projections: dict | None, ledger_id: str) -> str | None:
    if not projections or not ledger_id:
        return None
    if ledger_id in (projections.get("sources") or {}):
        return ledger_id
    return (projections.get("anchor_to_source") or {}).get(ledger_id)


def _view_scopes(view: dict) -> set[str]:
    scopes: set[str] = set()
    for reading in view.get("readings") or []:
        if not isinstance(reading, dict):
            continue
        for scope in reading.get("scopes") or []:
            if isinstance(scope, str):
                scopes.add(scope)
    return scopes


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
    scopes = _view_scopes(view)
    if scope == "full_text" and "full_text" not in scopes:
        errors.append("CITATION_SCOPE_EXCEEDS_READING (full_text)")
    if scope.startswith("section") and not ({"section", "full_text"} & scopes):
        errors.append("CITATION_SCOPE_EXCEEDS_READING (section)")
    return errors


def _nearest_contract(body: list[str], projections: dict | None) -> tuple[dict[str, dict], list[str], bool, list[str], list[str]]:
    """Validate the nearest-set JSON block.

    Returns (candidates by id, uncovered entries, stale flag, errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []
    candidates: dict[str, dict] = {}
    uncovered: list[str] = []
    stale = False
    section = _section_text(body, "近邻选择与深读记录")
    match = NEAREST_BLOCK.search(section)
    if not match:
        return candidates, uncovered, stale, ["NEAREST_SET_BLOCK_MISSING"], warnings
    try:
        payload = json.loads(match.group(1))
    except Exception:  # noqa: BLE001 - malformed author input must be an error, not a crash
        return candidates, uncovered, stale, ["NEAREST_SET_JSON_INVALID"], warnings
    if not isinstance(payload, dict):
        return candidates, uncovered, stale, ["NEAREST_SET_JSON_INVALID"], warnings
    if payload.get("schema") != NEAREST_SCHEMA:
        errors.append("NEAREST_SET_SCHEMA_INVALID")

    queries = payload.get("queries")
    distinct: list[str] = []
    if not isinstance(queries, list):
        errors.append("NEAREST_SET_REQUIRES_TWO_DISTINCT_QUERIES")
    else:
        for query in queries:
            if not _substantive(query, 4):
                errors.append("NEAREST_SET_QUERY_INVALID")
                continue
            distinct.append(_norm_cell(query))
    if len(set(distinct)) < 2:
        errors.append("NEAREST_SET_REQUIRES_TWO_DISTINCT_QUERIES")

    created = payload.get("created_at")
    if not isinstance(created, str) or not created.strip():
        errors.append("NEAREST_SET_CREATED_AT_REQUIRED")
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", created.strip()):
        errors.append("NEAREST_SET_CREATED_AT_INVALID")
    else:
        try:
            created_date = dt.date.fromisoformat(created.strip())
        except ValueError:
            errors.append("NEAREST_SET_CREATED_AT_INVALID")
        else:
            today = _today()
            if created_date > today:
                errors.append("NEAREST_SET_CREATED_AT_IN_FUTURE")
            elif (today - created_date).days > 180:
                stale = True
                warnings.append(f"NEAREST_SET_STALE {(today - created_date).days} days")

    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) < 2:
        errors.append("NEAREST_SET_REQUIRES_TWO_CANDIDATES")
        raw_candidates = raw_candidates if isinstance(raw_candidates, list) else []

    seen_ids: set[str] = set()
    seen_ledgers: set[str] = set()
    seen_sources: set[str] = set()
    for candidate in raw_candidates:
        if not isinstance(candidate, dict):
            errors.append("NEAREST_CANDIDATE_INVALID")
            continue
        cid = _clean(candidate.get("id"))
        if not CANDIDATE_ID.fullmatch(cid):
            errors.append("NEAREST_CANDIDATE_ID_INVALID")
            cid = ""
        elif cid in seen_ids:
            errors.append("NEAREST_CANDIDATE_DUPLICATE_ID")
            cid = ""
        else:
            seen_ids.add(cid)

        for field in CANDIDATE_FIELDS:
            value = candidate.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"NEAREST_CANDIDATE_MISSING_{field.upper()}")

        title = _clean(candidate.get("title"))
        rationale = _clean(candidate.get("rationale"))
        if not _substantive(title, 4):
            errors.append("NEAREST_CANDIDATE_PLACEHOLDER_TITLE")
        if not _substantive(rationale, 6):
            errors.append("NEAREST_CANDIDATE_PLACEHOLDER_RATIONALE")

        status = _clean(candidate.get("status"))
        if status not in STATUS_ALLOWED:
            errors.append("NEAREST_CANDIDATE_INVALID_STATUS")
        reader = _clean(candidate.get("reader"))
        if reader not in READER_ALLOWED:
            errors.append("NEAREST_CANDIDATE_INVALID_READER")

        ledger_raw = candidate.get("ledger")
        ledger_id = ""
        if isinstance(ledger_raw, str) and ledger_raw.strip():
            ledger_text = _clean(ledger_raw)
            if not ledger_text.startswith("ledger:") or not ledger_text[7:].strip():
                errors.append("NEAREST_CANDIDATE_LEDGER_FORMAT")
            else:
                ledger_id = ledger_text[7:].strip()
                if ledger_id in seen_ledgers:
                    errors.append("NEAREST_CANDIDATE_DUPLICATE_LEDGER")
                    ledger_id = ""
                else:
                    seen_ledgers.add(ledger_id)

        locator = _clean(candidate.get("locator"))
        if status in {"full_text", "section"}:
            if not _locator_ok(locator):
                errors.append("NEAREST_CANDIDATE_LOCATOR_INVALID")
        elif not _locator_ok(locator, allow_special=True):
            errors.append("NEAREST_CANDIDATE_LOCATOR_INVALID")

        view = None
        if ledger_id and projections is not None:
            view = _projection_view(projections, ledger_id)
            if view is None:
                errors.append("NEAREST_CANDIDATE_LEDGER_UNBOUND")
            else:
                scopes = _view_scopes(view)
                if status == "full_text" and "full_text" not in scopes:
                    errors.append("NEAREST_CANDIDATE_STATUS_EXCEEDS_LEDGER_SCOPE")
                elif status == "section" and not ({"section", "full_text"} & scopes):
                    errors.append("NEAREST_CANDIDATE_STATUS_EXCEEDS_LEDGER_SCOPE")
                source_key = str(_projection_source_id(projections, ledger_id) or ledger_id)
                if source_key in seen_sources:
                    errors.append("NEAREST_CANDIDATE_DUPLICATE_SOURCE")
                else:
                    seen_sources.add(source_key)
                if status in {"full_text", "section"}:
                    reading_locators = _reading_locators(view)
                    if not reading_locators:
                        errors.append("NEAREST_CANDIDATE_READING_LOCATOR_MISSING")
                    elif not any(_locator_matches(locator, item) for item in reading_locators):
                        errors.append("NEAREST_CANDIDATE_LOCATOR_NOT_IN_READING")

        kill_questions: list[str] = []
        answers: dict[str, str] = {}
        kill_locators: dict[str, str] = {}
        answered = 0
        raw_kill = candidate.get("kill_questions")
        if not isinstance(raw_kill, list) or len(raw_kill) < 2:
            errors.append("NEAREST_CANDIDATE_NEEDS_TWO_KILL_QUESTIONS")
        else:
            for question in raw_kill:
                if not isinstance(question, dict):
                    errors.append("NEAREST_KILL_QUESTION_INCOMPLETE")
                    continue
                question_text = _clean(question.get("q"))
                answer = _clean(question.get("answer"))
                question_locator = _clean(question.get("locator"))
                text_ok = _substantive(question_text, 6)
                answer_ok = answer in ANSWER_ALLOWED
                if not text_ok:
                    errors.append("NEAREST_KILL_QUESTION_INCOMPLETE")
                if not answer_ok:
                    errors.append("NEAREST_KILL_QUESTION_ANSWER_INVALID")
                if answer == "未读到":
                    locator_ok = _locator_ok(question_locator, allow_special=True)
                else:
                    locator_ok = _locator_ok(question_locator)
                if not locator_ok:
                    errors.append("NEAREST_KILL_QUESTION_LOCATOR_INVALID")
                if text_ok and answer_ok and locator_ok:
                    if answer in {"是", "否"} and view is not None and status in {"full_text", "section"}:
                        reading_locators = _reading_locators(view)
                        if not reading_locators:
                            locator_ok = False
                            errors.append("NEAREST_KILL_QUESTION_LOCATOR_NOT_IN_READING")
                        elif not any(_locator_matches(question_locator, item) for item in reading_locators):
                            locator_ok = False
                            errors.append("NEAREST_KILL_QUESTION_LOCATOR_NOT_IN_READING")
                    if locator_ok:
                        key = _norm_cell(question_text)
                        kill_questions.append(key)
                        answers[key] = answer
                        kill_locators[key] = _norm_cell(question_locator)
                        if answer in {"是", "否"}:
                            answered += 1

        if cid:
            candidates[cid] = {"id": cid, "title": title, "status": status, "reader": reader,
                               "ledger": ledger_id, "answered": answered,
                               "kill_questions": kill_questions, "answers": answers,
                               "kill_locators": kill_locators}

    raw_uncovered = payload.get("uncovered")
    if raw_uncovered is not None:
        if not isinstance(raw_uncovered, list):
            errors.append("NEAREST_UNCOVERED_INVALID")
        else:
            for entry in raw_uncovered:
                if not _substantive(entry, 4):
                    errors.append("NEAREST_UNCOVERED_INVALID")
                else:
                    uncovered.append(_clean(entry))
    return candidates, uncovered, stale, errors, warnings

def _claims_contract(body: list[str], candidates: dict[str, dict], uncovered: list[str],
                     projections: dict | None) -> tuple[dict[str, dict], set[str], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    rows, row_errors = _claim_rows(_section_text(body, "主张—证据等级"))
    errors.extend(row_errors)
    if not rows:
        errors.append("CLAIM_EVIDENCE_TABLE_MISSING")
        return {}, set(), errors, warnings
    claims: dict[str, dict] = {}
    c_ids: set[str] = set()
    for row in rows:
        cid, claim, grade, candidate_cell, evidence, flip = (cell.strip() for cell in row)
        cid = _clean(cid)
        claim = _clean(claim)
        grade = _clean(grade)
        evidence = _clean(evidence)
        flip = _clean(flip)
        valid_id = bool(CLAIM_ID.fullmatch(cid))
        if not valid_id:
            errors.append("CLAIM_ID_INVALID")
        elif cid in claims:
            errors.append("CLAIM_ID_DUPLICATE")
        if not _substantive(claim, 6):
            errors.append("CLAIM_TEXT_PLACEHOLDER")
        if grade not in {"A", "B", "C"}:
            errors.append("CLAIM_GRADE_INVALID")
        if not _substantive(flip, 6):
            errors.append("CLAIM_NEEDS_FLIP_CONDITION")

        tokens = [token.strip() for token in re.split(r"[,，、;；\s]+", _clean(candidate_cell)) if token.strip()]
        bound: list[str] = []
        if grade in {"A", "B"}:
            if not tokens:
                errors.append("CLAIM_CANDIDATE_ID_INVALID")
            for token in tokens:
                if not CANDIDATE_ID.fullmatch(token):
                    errors.append("CLAIM_CANDIDATE_ID_INVALID")
                elif token not in candidates:
                    errors.append("CLAIM_CANDIDATE_NOT_IN_NEAREST_SET")
                else:
                    bound.append(token)
            if not evidence.startswith("ledger:"):
                errors.append("A_B_CLAIM_NOT_LEDGER_BOUND")
            else:
                ledger_id = evidence[7:].strip()
                claim_ledgers = {candidates[item]["ledger"] for item in bound if item in candidates}
                if ledger_id not in claim_ledgers:
                    errors.append("A_B_CLAIM_NOT_IN_NEAREST_SET")
                view = _projection_view(projections, ledger_id)
                if not view or not view.get("readings"):
                    errors.append("A_B_CLAIM_NOT_VERIFIED")
            for item in bound:
                candidate = candidates.get(item)
                if not candidate:
                    continue
                if candidate["status"] not in {"section", "full_text"}:
                    errors.append("CLAIM_CANDIDATE_UNREAD")
                if candidate["answered"] < 2:
                    errors.append("CLAIM_CANDIDATE_KILL_QUESTIONS_UNANSWERED")
            if grade == "A":
                read_ids = {item for item, candidate in candidates.items()
                            if candidate["status"] in {"section", "full_text"}}
                if read_ids - set(bound):
                    errors.append("A_CLAIM_MUST_COVER_READ_NEAREST")
                for item, candidate in candidates.items():
                    if candidate["status"] not in {"abstract", "unseen"}:
                        continue
                    title = _norm_cell(candidate["title"])
                    mentioned = any(item in entry or (title and title in _norm_cell(entry))
                                    for entry in uncovered)
                    if not mentioned:
                        errors.append("A_GRADE_UNCOVERED_NEAREST_MISSING")
                if ABSOLUTE_NOVELTY.search(claim):
                    errors.append("A_CLAIM_ABSOLUTE_NOVELTY_WORDING")
        elif grade == "C":
            if not tokens:
                errors.append("C_CLAIM_CANDIDATE_ID_REQUIRED")
            for token in tokens:
                if not CANDIDATE_ID.fullmatch(token):
                    errors.append("CLAIM_CANDIDATE_ID_INVALID")
                elif token not in candidates:
                    errors.append("CLAIM_CANDIDATE_NOT_IN_NEAREST_SET")
                else:
                    bound.append(token)
        if valid_id and cid not in claims:
            claims[cid] = {"grade": grade, "claim": claim, "candidates": bound}
        if grade == "C" and valid_id:
            c_ids.add(cid)
    return claims, c_ids, errors, warnings

def _provisional_contract(body: list[str], c_ids: set[str], candidates: dict[str, dict],
                           claims: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    section = _section_text(body, "暂定判断（C 级）")
    match = PROVISIONAL_BLOCK.search(section)
    if not match:
        if c_ids:
            errors.append("PROVISIONAL_BLOCK_MISSING")
        return errors
    try:
        payload = json.loads(match.group(1))
    except Exception:  # noqa: BLE001
        return ["PROVISIONAL_JSON_INVALID"]
    if not isinstance(payload, dict):
        return ["PROVISIONAL_JSON_INVALID"]
    if payload.get("schema") != PROVISIONAL_SCHEMA:
        errors.append("PROVISIONAL_SCHEMA_INVALID")
    raw_claims = payload.get("claims")
    if not isinstance(raw_claims, list):
        errors.append("PROVISIONAL_JSON_INVALID")
        return errors
    entries: dict[str, dict] = {}
    for entry in raw_claims:
        if not isinstance(entry, dict):
            errors.append("PROVISIONAL_CLAIM_INCOMPLETE")
            continue
        cid = _clean(entry.get("id"))
        if not CLAIM_ID.fullmatch(cid):
            errors.append("PROVISIONAL_CLAIM_ID_INVALID")
            continue
        if cid in entries:
            errors.append("PROVISIONAL_CLAIM_DUPLICATE_ID")
            continue
        entries[cid] = entry
    for cid in sorted(c_ids - set(entries)):
        errors.append(f"PROVISIONAL_CLAIM_ID_MISSING {cid}")
    for cid in sorted(set(entries) - c_ids):
        errors.append(f"PROVISIONAL_CLAIM_UNKNOWN_ID {cid}")
    for cid, entry in entries.items():
        if not _substantive(entry.get("tendency"), 4) or not _substantive(entry.get("flip"), 6) \
                or not _substantive(entry.get("access"), 4):
            errors.append("PROVISIONAL_CLAIM_INCOMPLETE")
        check = entry.get("check")
        if not isinstance(check, dict):
            errors.append("PROVISIONAL_CHECK_INCOMPLETE")
            continue
        candidate_id = _clean(check.get("candidate"))
        if candidate_id not in candidates:
            errors.append("PROVISIONAL_CHECK_CANDIDATE_UNKNOWN")
        bound = set((claims.get(cid) or {}).get("candidates") or [])
        if candidate_id not in bound:
            errors.append("PROVISIONAL_CHECK_CANDIDATE_NOT_BOUND")
        question = _clean(check.get("question"))
        if not _substantive(question, 6):
            errors.append("PROVISIONAL_CHECK_INCOMPLETE")
            continue
        if candidate_id not in candidates:
            continue
        key = _norm_cell(question)
        answers = candidates[candidate_id]["answers"]
        if key not in answers:
            errors.append("PROVISIONAL_CHECK_QUESTION_NOT_IN_NEAREST")
            continue
        if answers[key] != "未读到":
            errors.append("PROVISIONAL_CHECK_QUESTION_ALREADY_ANSWERED")
        expected_locator = candidates[candidate_id]["kill_locators"].get(key, "")
        if _norm_cell(_clean(check.get("locator"))) != expected_locator:
            errors.append("PROVISIONAL_CHECK_LOCATOR_MISMATCH")
    return errors

def _claim_id_contract(body: list[str], claims: dict[str, dict], c_ids: set[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    known = set(claims)
    headings = _headings(body)
    if headings and (JUDGMENT_TERMS.search(headings[0][0]) or ABSOLUTE_NOVELTY.search(headings[0][0])):
        errors.append("JUDGMENT_OUTSIDE_CLAIM_CONTRACT")
    skip_titles = {_title("主张—证据等级"), _title("暂定判断（C 级）"), _title("参考文献")}
    current_title = _title("当前判断与下一步")
    sections = _sections(body)
    referenced_current: set[str] = set()
    for title, lines in sections:
        normalized = _title(title)
        text = "\n".join(lines)
        prose = CODE_FENCE.sub("", text)
        if normalized == current_title:
            blocks: list[list[str]] = []
            buffer: list[str] = []

            def flush() -> None:
                nonlocal buffer
                if buffer:
                    blocks.append(buffer)
                    buffer = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    flush()
                    continue
                if re.match(r"^#{1,6}\s", stripped):
                    flush()
                    continue
                if re.match(r"^(?:[-*+]|\d+[.)])\s+", stripped):
                    flush()
                    buffer = [stripped]
                else:
                    if stripped.startswith(">"):
                        stripped = stripped.lstrip("> ").strip()
                        if not stripped:
                            continue
                    buffer.append(stripped)
            flush()
            for block in blocks:
                block_text = "\n".join(block)
                block_refs = CLAIM_REF.findall(block_text)
                referenced_current.update(block_refs)
                for ref in block_refs:
                    if ref not in known:
                        errors.append(f"CLAIM_ID_UNKNOWN {ref}")
                if not block_refs:
                    if PLAN_PREFIX.match(block[0]):
                        if JUDGMENT_TERMS.search(block_text) or ABSOLUTE_NOVELTY.search(block_text):
                            errors.append("PLAN_UNIT_CONTAINS_JUDGMENT")
                        continue
                    errors.append("CURRENT_JUDGMENT_CLAIM_ID_MISSING")
                    continue
                if any(ref in c_ids for ref in block_refs):
                    qualified = "倾向" in block_text and ("见" in block_text or "暂定" in block_text)
                    if not qualified:
                        errors.append("C_CLAIM_STATED_IN_CURRENT_JUDGMENT")
            continue
        if normalized in skip_titles:
            continue
        for line in prose.splitlines():
            refs = CLAIM_REF.findall(line)
            for ref in refs:
                if ref not in known:
                    errors.append(f"CLAIM_ID_UNKNOWN {ref}")
                if ref in c_ids:
                    errors.append("C_CLAIM_STATED_OUTSIDE_PROVISIONAL_SECTION")
            if JUDGMENT_TERMS.search(line):
                if not refs or all(ref in c_ids for ref in refs):
                    errors.append("JUDGMENT_OUTSIDE_CLAIM_CONTRACT")
    for cid, claim in claims.items():
        if claim["grade"] in {"A", "B"} and cid not in referenced_current:
            warnings.append(f"A_B_CLAIM_NOT_REFERENCED_IN_CURRENT {cid}")
    return errors, warnings

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
    stale = False
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
    sections = _sections(body)
    headings = _headings(body)
    if headings:
        headings = headings[1:]  # first heading is the document title
    titles = [title for title, _ in headings]
    if tier in {"evidence_review", "preregistration", "research_plan"} and ledger is not None:
        try:
            projections = derive_tier(pathlib.Path(ledger))
        except Exception:  # noqa: BLE001
            projections = None

    if tier in {"evidence_review", "preregistration", "research_plan"}:
        joined = "\n".join(body)
        if len(NEAREST_BLOCK.findall(joined)) > 1:
            errors.append("NEAREST_SET_BLOCK_DUPLICATE")
        if len(PROVISIONAL_BLOCK.findall(joined)) > 1:
            errors.append("PROVISIONAL_BLOCK_DUPLICATE")
        candidates, uncovered, stale, nearest_errors, nearest_warnings = _nearest_contract(body, projections)
        errors.extend(nearest_errors)
        warnings.extend(nearest_warnings)
        claims, c_ids, claim_errors, claim_warnings = _claims_contract(body, candidates, uncovered, projections)
        errors.extend(claim_errors)
        warnings.extend(claim_warnings)
        errors.extend(_provisional_contract(body, c_ids, candidates, claims))
        id_errors, id_warnings = _claim_id_contract(body, claims, c_ids)
        errors.extend(id_errors)
        warnings.extend(id_warnings)
        stats_claims = len(claims)
        stats_candidates = len(candidates)
    else:
        stats_claims = 0
        stats_candidates = 0

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

    prose_text = CODE_FENCE.sub("", body_text)
    used: list[str] = []
    for match in CITATION.finditer(prose_text):
        for part in re.split(r"[,，–-]", match.group(1)):
            if part.strip():
                used.append(part.strip())
    used = sorted(set(used), key=int)
    for pattern in OTHER_CITATIONS:
        hit = pattern.search(prose_text)
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
            if not _substantive(title, 4):
                errors.append(f"CITATION_ENTRY_INVALID [{key}]")
            if not (scope == "full_text" or (scope.startswith("section:") and _locator_ok(scope[8:]))):
                errors.append(f"CITATION_SCOPE_INVALID [{key}]")
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
                if scope.startswith("section:"):
                    reading_locators = _reading_locators(view)
                    if not reading_locators or not any(_locator_matches(scope[8:], item) for item in reading_locators):
                        errors.append(f"CITATION_SCOPE_LOCATOR_NOT_IN_READING [{key}]")
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
    for line in prose_text.splitlines():
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
    delivery_ready = (not errors and todo == 0 and not stale
                      and not any("UNUSED_REFERENCE" in warning for warning in warnings))
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
            "claims": stats_claims,
            "nearest_candidates": stats_candidates,
        },
        "attestation": "user-attested readings; not authenticated",
        "note": "Structure/ledger-consistency only; not a truth check. It cannot prove source support, numbers, "
                "nearest-set completeness, kill-answer honesty, novelty or writing quality.",
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
