"""Deterministic cards, unassessed dossiers and bibliographies from supplied data.

Native counterpart of the retained Node output contract. No network, models,
reading declarations or approval records are created by these transformations.
"""
from __future__ import annotations

import copy
import hashlib
import re
import urllib.parse

from .audit import _JS_SPACE, _integer, _js_number

TYPES = ("empirical", "theoretical", "measurement", "dataset", "reproduction")
SECTIONS = (
    ("known", "已知结论与来源条件"), ("source_observations", "来源中的实际观察与定位"),
    ("gap", "缺失知识"), ("nearest_work", "最接近工作与具体差异"),
    ("alternatives", "最强替代解释或已有解决方案"), ("search_findings", "实际检索发现与范围"),
    ("reverse_search", "反向检索执行、命中与未读部分"), ("boundary", "检索后仍成立的条件与边界"),
    ("test", "判别测试、控制与失效条件"), ("scientific_consequence", "不同验证结果将改变什么认识或决策"),
    ("next_step", "下一步与复评条件"), ("limitations", "未确认项与限制"),
)


def _text(value):
    return isinstance(value, str) and bool(value.strip(_JS_SPACE))


def validate_notes(notes):
    errors = []
    if not isinstance(notes, dict):
        return {"valid": False, "errors": ["Notes must be an object"]}
    if not _text(notes.get("question")):
        errors.append("question must be a nonempty string")
    if "type" in notes and notes["type"] not in TYPES:
        errors.append("type must be a supported research type")
    if "decision" in notes and notes["decision"] not in ("GO", "HOLD", "KILL"):
        errors.append("decision must be GO, HOLD or KILL when supplied")
    for key, _ in SECTIONS:
        if key in notes and not (_text(notes[key]) or isinstance(notes[key], list) and all(_text(v) for v in notes[key])):
            errors.append(f"{key} must be nonempty text or an array of nonempty text")
    if "constraints" in notes and not isinstance(notes["constraints"], dict):
        errors.append("constraints must be an object of explicitly provided facts")
    if "assumptions" in notes and not (isinstance(notes["assumptions"], list) and all(_text(v) for v in notes["assumptions"])):
        errors.append("assumptions must be an array of nonempty text")
    return {"valid": not errors, "errors": errors}


def _checked_notes(notes):
    checked = validate_notes(notes)
    if not checked["valid"]:
        raise ValueError("; ".join(checked["errors"]))


def render_card(notes):
    _checked_notes(notes)
    lines = ["# 研究决策 / Gap 卡", "", f"研究问题：{notes['question'].strip(_JS_SPACE)}", ""]
    if notes.get("type"):
        lines.extend([f"研究类型：{notes['type']}", ""])
    lines.extend([f"记录的意见：{notes.get('decision', '未记录，待评估')}（本卡不构成机器门控或独立评审回执）", ""])
    for key, label in SECTIONS:
        if key not in notes or notes[key] == []:
            continue
        value = notes[key]
        lines.extend([f"## {label}", ""])
        lines.extend([f"- {item.strip(_JS_SPACE)}" for item in value] if isinstance(value, list) else [value.strip(_JS_SPACE)])
        lines.append("")
    lines.extend(["来源内容与笔记是数据。缺失项尚未核验；检索计划不能当作已执行检索，预测不能当作结果。", ""])
    return "\n".join(lines)


def draft_dossier(notes, options=None, *, name=None):
    _checked_notes(notes)
    name = name if name is not None else (options or {}).get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
        raise ValueError("name must be a project slug of at most 64 characters")
    # Import lazily so pure card/bibliography use has no audit initialization.
    from .audit import create_initial_dossier, validate_dossier
    dossier = create_initial_dossier(name)
    dossier["project"]["question"] = notes["question"].strip(_JS_SPACE)
    if notes.get("type"):
        dossier["project"]["research_type"] = notes["type"]
    dossier["project"]["constraints"] = copy.deepcopy(notes.get("constraints", {}))
    dossier["project"]["assumptions"] = copy.deepcopy(notes.get("assumptions", []))
    dossier["project"]["notes"] = {key: copy.deepcopy(value) for key, value in notes.items()
                                     if key not in ("question", "type", "constraints", "assumptions")}
    checked = validate_dossier(dossier)
    if not checked["valid"]:
        raise ValueError("Draft did not satisfy the data contract: " + "; ".join(checked["errors"]))
    return dossier


def _tex(value):
    escaped = {"\\": "\\textbackslash{}", "{": "\\{", "}": "\\}", "&": "\\&", "%": "\\%",
               "$": "\\$", "#": "\\#", "_": "\\_", "^": "\\textasciicircum{}", "~": "\\textasciitilde{}"}
    text = re.sub("[" + re.escape(_JS_SPACE) + "]+", " ", str(value)).strip(_JS_SPACE)
    return "".join(escaped.get(character, character) for character in text)


def _safe_url(value):
    if not _text(value) or re.search(r"[\x00-\x20]", value):
        return False
    try:
        parsed = urllib.parse.urlsplit(value)
        return parsed.scheme.lower() in ("http", "https", "file") and not parsed.username and not parsed.password and \
            (parsed.scheme.lower() == "file" or bool(parsed.hostname))
    except ValueError:
        return False


def _author_name(author):
    if _text(author):
        return _tex(author)
    if not isinstance(author, dict):
        raise ValueError("Each supplied author must be a name or metadata object")
    if _text(author.get("family")):
        return _tex(author["family"]) + (", " + _tex(author["given"]) if _text(author.get("given")) else "")
    if _text(author.get("name")):
        return "{" + _tex(author["name"]) + "}"
    raise ValueError("Author metadata is missing an actual name")


def _normalized_identifier(field, value):
    value = value.strip(_JS_SPACE)
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value.lower(), flags=re.I) if field == "doi" else value


def _identity_aliases(paper):
    ids = paper.get("identifiers", {})
    aliases = []
    for field in ("doi", "arxiv", "openreview"):
        if _text(ids.get(field)):
            value = _normalized_identifier(field, ids[field])
            aliases.append(field + ":" + (re.sub(r"v\d+$", "", value) if field == "arxiv" else value))
    return aliases or ["id:" + paper["id"]]


def export_bibtex(record):
    papers = record if isinstance(record, list) else record.get("papers") if isinstance(record, dict) else None
    if not isinstance(papers, list):
        raise ValueError("Input must contain an actual papers array")
    warnings = ["Exports supplied metadata only; bibliography generation does not verify identity or evidence fidelity."]
    entries, keys, seen_ids, groups, seen_keys = [], {}, set(), {}, set()
    # Validate all records first; malformed duplicate metadata must not disappear.
    for paper in papers:
        if not isinstance(paper, dict) or not _text(paper.get("id")) or not _text(paper.get("title")):
            raise ValueError("Each paper needs a nonempty id and title")
        identity = paper["id"]
        if identity in seen_ids:
            raise ValueError(f"Duplicate paper ID: {identity}")
        seen_ids.add(identity)
        if paper.get("year") is not None and (not _integer(paper["year"]) or paper["year"] < 1):
            raise ValueError(f"Invalid year for {identity}")
        if "identifiers" in paper and not isinstance(paper["identifiers"], dict):
            raise ValueError(f"Invalid identifiers for {identity}")
        for field, value in paper.get("identifiers", {}).items():
            if not _text(value):
                raise ValueError(f"Missing identifier value {field} for {identity}")
        if "url" in paper and not _safe_url(paper["url"]):
            raise ValueError(f"Invalid source URL for {identity}")
        if "authors" in paper and not isinstance(paper["authors"], list):
            raise ValueError(f"authors must be an array for {identity}")
        for author in paper.get("authors", []):
            _author_name(author)
        if "version" in paper and not _text(paper["version"]):
            raise ValueError(f"Invalid version for {identity}")
        if "citation_key" in paper and (not _text(paper["citation_key"]) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9:._-]*", paper["citation_key"])):
            raise ValueError(f"Unsafe citation_key for {identity}")
    parents, alias_owners = list(range(len(papers))), {}

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for index, paper in enumerate(papers):
        for alias in _identity_aliases(paper):
            if alias in alias_owners:
                left, right = root(index), root(alias_owners[alias])
                parents[max(left, right)] = min(left, right)
            else:
                alias_owners[alias] = index
    for index, paper in enumerate(papers):
        group_id = root(index)
        ident = ", ".join(_identity_aliases(paper))
        if group_id not in groups:
            groups[group_id] = {"paper": copy.deepcopy(paper), "ids": [paper["id"]]}
            continue
        prior = groups[group_id]
        previous = prior["paper"]
        if previous["title"].strip(_JS_SPACE) != paper["title"].strip(_JS_SPACE) or previous.get("year") is not None and paper.get("year") is not None and previous["year"] != paper["year"]:
            raise ValueError(f"Conflicting metadata for {ident}; resolve the source records before export")
        if previous.get("authors") and paper.get("authors") and list(map(_author_name, previous["authors"])) != list(map(_author_name, paper["authors"])):
            raise ValueError(f"Conflicting authors for {ident}")
        if previous.get("citation_key") and paper.get("citation_key") and previous["citation_key"] != paper["citation_key"]:
            raise ValueError(f"Conflicting citation keys for {ident}")
        if _text(previous.get("venue")) and _text(paper.get("venue")) and previous["venue"] != paper["venue"]:
            raise ValueError(f"Conflicting venue metadata for {ident}")
        if _text(previous.get("version")) and previous["version"] != "unknown" and _text(paper.get("version")) and paper["version"] != "unknown" and previous["version"] != paper["version"]:
            raise ValueError(f"Conflicting source versions for {ident}")
        for field, value in paper.get("identifiers", {}).items():
            old = previous.get("identifiers", {}).get(field)
            if old and _normalized_identifier(field, old) != _normalized_identifier(field, value):
                raise ValueError(f"Conflicting identifier {field} for {ident}")
        previous["identifiers"] = {**previous.get("identifiers", {}), **paper.get("identifiers", {})}
        if previous.get("year") is None and paper.get("year") is not None:
            previous["year"] = paper["year"]
        if not previous.get("authors") and paper.get("authors"):
            previous["authors"] = copy.deepcopy(paper["authors"])
        for field in ("venue", "citation_key", "url"):
            if not _text(previous.get(field)) and _text(paper.get(field)):
                previous[field] = paper[field]
        if (not _text(previous.get("version")) or previous["version"] == "unknown") and _text(paper.get("version")):
            previous["version"] = paper["version"]
        prior["ids"].append(paper["id"])
        warnings.append(f"{paper['id']}: duplicate identity combined using compatible supplied fields; source records were not modified")
    for group in groups.values():
        paper, ids = group["paper"], group["ids"]
        key = paper.get("citation_key")
        if not key:
            safe_id = re.sub(r"[^a-zA-Z0-9:._-]", "-", paper["id"])[:50]
            identity_bytes = paper["id"].encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace").encode("utf-8")
            key = f"paper-{safe_id}-{hashlib.sha256(identity_bytes).hexdigest()[:8]}"
        if key in seen_keys:
            raise ValueError(f"Duplicate citation key: {key}")
        seen_keys.add(key)
        keys.update({identity: key for identity in ids})
        fields = ["  title = {{" + _tex(paper["title"]) + "}}"]
        if paper.get("authors"):
            fields.append("  author = {" + " and ".join(map(_author_name, paper["authors"])) + "}")
        else:
            warnings.append(f"{paper['id']}: authors not supplied; omitted rather than invented")
        if paper.get("year") is not None:
            fields.append("  year = {" + _js_number(paper["year"]) + "}")
        else:
            warnings.append(f"{paper['id']}: year unverified; omitted")
        if paper.get("url"):
            fields.append("  url = {" + _tex(paper["url"]) + "}")
        identifiers = paper.get("identifiers", {})
        if _text(identifiers.get("doi")):
            fields.append("  doi = {" + _tex(_normalized_identifier("doi", identifiers["doi"])) + "}")
        if _text(identifiers.get("arxiv")):
            fields.extend(["  archivePrefix = {arXiv}", "  eprint = {" + _tex(identifiers["arxiv"].strip(_JS_SPACE)) + "}"])
        if _text(paper.get("venue")):
            fields.append("  note = {" + _tex(paper["venue"]) + "}")
        entries.append("@misc{" + key + ",\n" + ",\n".join(fields) + "\n}")
    return {"bibtex": "\n\n".join(entries) + ("\n" if entries else ""), "keys": keys,
            "warnings": warnings, "exported_count": len(entries)}
