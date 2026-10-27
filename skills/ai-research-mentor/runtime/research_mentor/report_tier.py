"""Derive the highest allowed report tier from a verified local ledger.

Only user/T1 reading confirmations with section/full_text scope count. The
ledger records declarations, not authenticated identity or claim support.
"""
from __future__ import annotations

import pathlib
import re
from typing import Any

TIERS = ("concept_memo", "evidence_review", "preregistration", "research_plan")
RANK = {tier: index for index, tier in enumerate(TIERS)}


def _canonical(resolve: dict | None, source: dict) -> str:
    identifiers = (resolve or {}).get("identifiers", {}) if isinstance(resolve, dict) else {}
    doi = identifiers.get("doi")
    arxiv = identifiers.get("arxiv")
    if isinstance(doi, str) and doi.strip():
        return "doi:" + doi.strip().lower()
    if isinstance(arxiv, str) and arxiv.strip():
        return "arxiv:" + re.sub(r"v[1-9]\d*$", "", arxiv.strip().lower())
    title = (resolve or {}).get("title") if isinstance(resolve, dict) else None
    if isinstance(title, str) and title.strip():
        return "title:" + re.sub(r"\W+", "", title.lower())
    return "source:" + str(source.get("id", ""))


def derive_tier(project: str | pathlib.Path) -> dict[str, Any]:
    sys_path = pathlib.Path(project)
    from research_mentor.core import ResearchCore
    from research_mentor.ledger import Ledger
    from research_mentor.readings import effective_readings

    ledger = Ledger(project)
    verification = ledger.verify()
    artifacts = ResearchCore(project).verify_artifacts()
    result: dict[str, Any] = {
        "derived_tier": "concept_memo",
        "chain_ok": bool(verification.get("valid")),
        "artifacts_ok": bool(artifacts.get("valid")),
        "unmet": [],
        "sources": {},
        "anchor_to_source": {},
        "verified_anchors": [],
    }
    if not result["chain_ok"]:
        result["unmet"] = ["LEDGER_CHAIN"]
        return result
    if not result["artifacts_ok"]:
        result["unmet"] = ["ARTIFACT_REPLAY"]
        return result

    events = ledger.read()
    resolves = {event.get("data", {}).get("id"): event.get("data", {})
                for event in events if event.get("type") == "paper.resolve"}
    sources: dict[str, dict[str, Any]] = {}
    for event in events:
        if event.get("type") != "source.fetch":
            continue
        data = event.get("data", {})
        source_id = data.get("id", event["id"])
        resolve = resolves.get(data.get("paper_id"))
        identities = (resolve or {}).get("identifiers", {}) if isinstance(resolve, dict) else {}
        version = (resolve or {}).get("version") if isinstance(resolve, dict) else None
        sources[source_id] = {
            "source_id": source_id,
            "canonical": _canonical(resolve, data),
            "title": (resolve or {}).get("title") if isinstance(resolve, dict) else None,
            "doi": identities.get("doi"),
            "arxiv": identities.get("arxiv"),
            "version": version,
            "url": data.get("source_url"),
            "readings": [],
        }

    anchors = {}
    for event in events:
        if event.get("type") == "evidence.anchor":
            data = event.get("data", {})
            anchor_id = data.get("id", event["id"])
            anchors[anchor_id] = data

    for anchor_id, data in anchors.items():
        source_id = data.get("source")
        if source_id not in sources:
            continue
        result["anchor_to_source"][anchor_id] = source_id
        confirmations = effective_readings(events, anchor_id)
        scopes = sorted({c.get("data", {}).get("scope") for c in confirmations
                         if c.get("actor") == "user" and c.get("trust") == "T1"
                         and c.get("data", {}).get("scope") in {"section", "full_text"}})
        if scopes:
            sources[source_id]["readings"].append({"anchor": anchor_id, "scopes": scopes,
                                                   "locator": data.get("locator")})
            result["verified_anchors"].append(anchor_id)

    result["sources"] = sources
    read_canonicals = {view["canonical"] for view in sources.values() if view["readings"]}
    if len(read_canonicals) >= 2:
        result["derived_tier"] = "evidence_review"
    else:
        result["unmet"] = ["TWO_DISTINCT_VERIFIED_SOURCES"]
    # preregistration/research_plan need dedicated ledger events that do not
    # exist in ledger-json-v1; cap rather than fabricate them.
    result["capped"] = "evidence_review"
    return result
