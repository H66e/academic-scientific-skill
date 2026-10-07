"""Scoped machine recommendations, explicit reading and human decisions.

No function authenticates a person, establishes novelty, or executes research.
New evidence invalidates the conservative project snapshot used by decisions.
The v2 export deliberately has no machine-generated legacy GO reviews.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .ledger import Ledger, LedgerError, digest

RESEARCH_TYPES = {"empirical", "theoretical", "measurement", "dataset", "reproduction"}
TARGETS = {"problem", "hypothesis", "nearest_work", "prerequisite", "validation"}
NOTICE = ("Structural acquisition and anchor checks do not prove source truth, "
          "literature completeness, faithful interpretation, novelty or human identity.")
POLICY_VERSION = "python-credibility-v2"
DUPLICATION_CLAIM_KINDS = {"mechanism_equivalence", "duplicate"}


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")
    return value


class Judgment:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    def _events(self) -> list[dict]:
        report = self.ledger.verify()
        if not report["valid"]:
            raise LedgerError("invalid ledger: " + "; ".join(report["errors"]))
        return self.ledger.read()

    def _candidate(self, candidate_id: str) -> dict:
        matches = [e for e in self._events() if e["type"] == "candidate.upsert"
                   and e["data"].get("id") == candidate_id]
        if not matches:
            raise ValueError("unknown candidate ID")
        return matches[-1]["data"]

    def _record(self, record_id: str, event_type: str) -> dict:
        matches = [e for e in self._events() if e["type"] == event_type
                   and (e["id"] == record_id or e["data"].get("id") == record_id)]
        if not matches:
            raise ValueError(f"unknown {event_type} ID: {record_id}")
        return matches[-1]

    def snapshot(self, candidate_id: str) -> str:
        # Decisions/reviews are outcomes, not their own input. All scientific
        # changes are included until a narrower dependency model is evaluated.
        events = self._events()
        candidates = [e["data"] for e in events if e["type"] == "candidate.upsert" and e["data"].get("id") == candidate_id]
        if not candidates:
            raise ValueError("unknown candidate ID")
        return self._snapshot(candidates[-1], events)

    @staticmethod
    def _snapshot(candidate: dict, events: list[dict]) -> str:
        science = [e["sha256"] for e in events
                   if e["type"] not in {"decision.record", "decision.revoke", "review.record"}]
        return digest({"policy": POLICY_VERSION, "candidate": candidate, "science": science})

    def _source_identity(self, source: dict, events: list[dict]) -> dict:
        confirmations = [e for e in events if e["type"] == "source.identity.confirm"
            and e["actor"] == "user" and e["trust"] == "T1"
            and e["data"].get("source_event") == source["id"]
            and e["data"].get("source_snapshot") == digest(source["data"])]
        if confirmations:
            latest = confirmations[-1]["data"]
            resolved = self._record(latest.get("resolve_event", ""), "paper.resolve")
            if resolved["data"].get("id") == latest.get("paper_id"):
                return latest
        return source["data"].get("source_identity", {})

    def upsert_candidate(self, candidate: dict) -> dict:
        if not isinstance(candidate, dict):
            raise ValueError("candidate must be an object")
        events = self._events()
        data = deepcopy(candidate)
        for key in ("id", "title", "question", "hypothesis", "contribution"):
            _text(data.get(key), key)
        if data.get("research_type") not in RESEARCH_TYPES:
            raise ValueError("unsupported research_type")
        for key in ("search_ids", "nearest_work"):
            if not isinstance(data.get(key, []), list):
                raise ValueError(f"{key} must be an array")
            data.setdefault(key, [])
        novelty = data.get("novelty", {})
        if not isinstance(novelty, dict) or novelty.get("status", "unclear") not in {"distinct", "incremental", "duplicate", "unclear"}:
            raise ValueError("invalid novelty status")
        feasibility = data.get("feasibility", {})
        if not isinstance(feasibility, dict) or feasibility.get("status", "unknown") not in {"ready", "pilot_only", "blocked", "unknown"}:
            raise ValueError("invalid feasibility status")
        if not isinstance(feasibility.get("dependencies", []), list):
            raise ValueError("dependencies must be an array")
        for dependency in feasibility.get("dependencies", []):
            if not isinstance(dependency, dict) or type(dependency.get("mandatory")) is not bool or dependency.get("status") not in {"met", "unknown", "failed"}:
                raise ValueError("invalid dependency")
            _text(dependency.get("name"), "dependency.name")
            _text(dependency.get("basis"), "dependency.basis")
        if not isinstance(data.get("validation", {}), dict):
            raise ValueError("validation must be an object")
        for search_id in data["search_ids"]:
            self._record(search_id, "search.result")
        for nearest in data["nearest_work"]:
            if not isinstance(nearest, dict) or type(nearest.get("decisive")) is not bool:
                raise ValueError("nearest_work needs paper_id, evidence_ids, delta and decisive")
            _text(nearest.get("paper_id"), "nearest_work.paper_id")
            _text(nearest.get("delta"), "nearest_work.delta")
            if not isinstance(nearest.get("evidence_ids"), list):
                raise ValueError("nearest_work.evidence_ids must be an array")
            for evidence_id in nearest["evidence_ids"]:
                self._record(evidence_id, "evidence.anchor")
        previous = [e["data"] for e in events if e["type"] == "candidate.upsert"
                    and e["data"].get("id") == data["id"]]
        data["version"] = previous[-1]["version"] + 1 if previous else 1
        data.setdefault("novelty", {"status": "unclear", "reason": "Unassessed"})
        data.setdefault("feasibility", {"status": "unknown", "reason": "Unconfirmed", "dependencies": []})
        data.setdefault("validation", {"status": "missing"})
        return self.ledger.append("candidate.upsert", data, actor="model", trust="T2",
            expected_head=events[-1]["sha256"] if events else "")

    def add_claim(self, text: str, candidate_id: str, kind: str = "hypothesis", *,
                  load_bearing: bool = True) -> dict:
        candidate = self._candidate(candidate_id)
        if type(load_bearing) is not bool:
            raise ValueError("load_bearing must be boolean")
        return self.ledger.append("claim.add", {"text": _text(text, "claim"),
            "candidate_id": candidate_id, "candidate_version": candidate["version"],
            "kind": _text(kind, "kind"), "load_bearing": load_bearing}, actor="model", trust="T2")

    def link_claim(self, claim_id: str, evidence_id: str, relation: str = "supports", *,
                   target: str = "hypothesis", decision_relevant: bool = True) -> dict:
        self._record(claim_id, "claim.add")
        self._record(evidence_id, "evidence.anchor")
        if relation not in {"supports", "contradicts", "context"} or target not in TARGETS:
            raise ValueError("unsupported evidence relation/target")
        if type(decision_relevant) is not bool:
            raise ValueError("decision_relevant must be boolean")
        return self.ledger.append("claim.link", {"claim_id": claim_id, "evidence_id": evidence_id,
            "relation": relation, "target": target, "decision_relevant": decision_relevant},
            actor="model", trust="T2")

    def confirm_read(self, evidence_id: str, scope: str, context: str, *,
                     human: bool = False, visual_checked: bool = False) -> dict:
        self._record(evidence_id, "evidence.anchor")
        if scope not in {"abstract", "section", "full_text"}:
            raise ValueError("scope must describe actual reading")
        if visual_checked and not human:
            raise ValueError("visual confirmation requires an actual human page check")
        return self.ledger.append("reading.confirm", {"evidence_id": evidence_id,
            "scope": scope, "context": _text(context, "reader context"),
            "visual_checked": visual_checked}, actor="user" if human else "model",
            trust="T1" if human else "T2")

    def _links(self, candidate: dict, events: list[dict]) -> tuple[list[dict], list[dict]]:
        claims = [e for e in events if e["type"] == "claim.add"
                  and e["data"].get("candidate_id") == candidate["id"]
                  and e["data"].get("candidate_version") == candidate["version"]]
        ids = {e["id"] for e in claims}
        links = [e["data"] for e in events if e["type"] == "claim.link"
                 and e["data"].get("claim_id") in ids]
        return claims, links

    def coverage(self, candidate_id: str) -> dict:
        candidate = self._candidate(candidate_id)
        events = self._events()
        searches = [self._record(sid, "search.result") for sid in candidate["search_ids"]]
        rows = [{"id": e["data"].get("id", e["id"]), "provider": e["data"].get("provider"),
                 "status": e["data"].get("status"), "family": e["data"].get("family", "unspecified"),
                 "hits_returned": len(e["data"].get("result_paper_ids", [])),
                 "limitations": e["data"].get("limitations", [])} for e in searches]
        claims, links = self._links(candidate, events)
        missing = []
        if not searches:
            missing.append("No candidate-linked executed search")
        if not any(r["family"] == "reverse" and r["status"] in {"complete", "partial"} for r in rows):
            missing.append("No executed reverse query")
        if not candidate["nearest_work"]:
            missing.append("No nearest-work comparison")
        for claim in claims:
            if claim["data"]["load_bearing"] and not any(link["claim_id"] == claim["id"] for link in links):
                missing.append(f"Unanchored load-bearing claim {claim['id']}")
        return {"searches": rows, "claims": len(claims), "links": len(links),
                "missing": missing, "coverage_complete": False,
                "notice": "Provider completion is not literature completeness. " + NOTICE}

    def assess(self, candidate_id: str, recommendation: str = "GO", *,
               reason: str, stage: str = "pilot", scope: str = "scientific_framing",
               kill_type: str | None = None, record: bool = True) -> dict:
        events = self._events()
        candidates = [e["data"] for e in events if e["type"] == "candidate.upsert" and e["data"].get("id") == candidate_id]
        if not candidates:
            raise ValueError("unknown candidate ID")
        candidate = candidates[-1]
        input_snapshot = self._snapshot(candidate, events)
        if recommendation not in {"GO", "HOLD", "KILL"}:
            raise ValueError("unsupported recommendation")
        if stage not in {"information_test", "pilot", "full_validation"}:
            raise ValueError("unsupported stage")
        if scope not in {"scientific_framing", "current_constraints"}:
            raise ValueError("unsupported scope")
        _text(reason, "assessment reason")
        from .core import ResearchCore
        artifacts = ResearchCore(self.ledger.project).verify_artifacts()
        missing = [] if artifacts.get("valid") else ["Acquisition artifact integrity check failed"]
        coverage = self.coverage(candidate_id)
        missing.extend(coverage["missing"])
        candidate_searches = [self._record(sid, "search.result") for sid in candidate["search_ids"]]
        if not any(e["trust"] == "T0" and e["data"].get("status") == "complete"
                   and e["data"].get("result_paper_ids") for e in candidate_searches):
            missing.append("No complete, nonempty acquired search boundary; partial-only searches remain HOLD")
        claims, links = self._links(candidate, events)
        load_bearing_ids = {c["id"] for c in claims if c["data"].get("load_bearing")}
        core_links = [l for l in links if l["claim_id"] in load_bearing_ids
                      and l["decision_relevant"] and l["relation"] in {"supports", "contradicts"}]
        if not load_bearing_ids:
            missing.append("No explicit load-bearing claim")
        evidence_ids = {l["evidence_id"] for l in core_links}
        decisive = [n for n in candidate["nearest_work"] if n["decisive"]]
        required_nearest = decisive or candidate["nearest_work"][:1]
        for nearest in required_nearest:
            if not nearest["evidence_ids"]:
                missing.append("Decisive nearest work has no anchor")
            evidence_ids.update(nearest["evidence_ids"])
            for eid in nearest["evidence_ids"]:
                anchor = self._record(eid, "evidence.anchor")
                source = self._record(anchor["data"]["source_event"], "source.fetch")
                if self._source_identity(source, events).get("paper_id") != nearest["paper_id"]:
                    missing.append(f"Nearest-work anchor {eid} is bound to a different/unresolved paper")
        if not core_links:
            missing.append("No decision-relevant claim-to-anchor link")
        for claim in claims:
            if claim["data"]["load_bearing"] and not any(l["claim_id"] == claim["id"]
                    and l["decision_relevant"] and l["relation"] == "supports" for l in links):
                missing.append(f"Load-bearing claim {claim['id']} only has contextual/non-decisive links")
        for evidence_id in evidence_ids:
            anchor = self._record(evidence_id, "evidence.anchor")
            reads = [e for e in events if e["type"] == "reading.confirm"
                     and e["data"].get("evidence_id") == evidence_id]
            if anchor["trust"] != "T0" or anchor["data"].get("match") != "exact":
                missing.append(f"Evidence {evidence_id} is not an exact tool anchor")
            if not reads or reads[-1]["data"]["scope"] not in {"section", "full_text"}:
                missing.append(f"Evidence {evidence_id} lacks explicit relevant-section reading")
            if anchor["data"].get("lossy") and not any(e["actor"] == "user" and e["trust"] == "T1"
                    and e["data"].get("visual_checked") for e in reads):
                missing.append(f"Evidence {evidence_id} requires an actual page/visual check")
            source = self._record(anchor["data"]["source_event"], "source.fetch")
            identity = self._source_identity(source, events)
            if identity.get("status") not in {"provider_url_bound", "human_confirmed"}:
                missing.append(f"Evidence {evidence_id} has no provider-bound or human-confirmed source identity")
        contradictions = [l for l in core_links if l["relation"] == "contradicts"
                          and l["target"] in {"hypothesis", "prerequisite", "validation"}]
        if contradictions:
            missing.append("Decision-relevant evidence contradicts a core condition")
        feasibility = candidate.get("feasibility", {})
        dependencies = feasibility.get("dependencies", [])
        if feasibility.get("status") != "ready" or any(d.get("mandatory") and d.get("status") != "met" for d in dependencies):
            missing.append("Required resources or prerequisites are not ready")
        validation = candidate.get("validation", {})
        fields = ("prediction", "falsifier", "design", "metric", "resource_estimate", "stop_rule")
        if validation.get("status") != "specified" or any(not isinstance(validation.get(f), str) or not validation[f].strip() for f in fields):
            missing.append("Bounded falsifiable validation design is incomplete")
        if candidate.get("novelty", {}).get("status") not in {"distinct", "incremental"}:
            missing.append("Novelty remains unclear or duplicate")
        if stage == "information_test":
            missing.append("Information gathering is a HOLD next step")
        if stage == "full_validation":
            missing.append("Independent full-validation import is not implemented; full validation remains HOLD")
        decision = "GO" if recommendation == "GO" and not missing else "HOLD"
        # Typed KILL is intentionally conservative; no label or failed network
        # call can by itself eliminate a scientific framing.
        if recommendation == "KILL":
            if kill_type == "scientific_refutation" and contradictions and evidence_ids and artifacts.get("valid"):
                evidence_failures = [m for m in missing if m.startswith("Evidence ") or "different/unresolved paper" in m]
                if not evidence_failures and scope == "scientific_framing":
                    decision = "KILL"
            elif kill_type == "duplicate" and scope == "scientific_framing" and candidate.get("novelty", {}).get("status") == "duplicate":
                decisive = [n for n in candidate["nearest_work"] if n["decisive"]]
                duplication_claim_ids = {c["id"] for c in claims if c["id"] in load_bearing_ids
                                         and c["data"].get("kind") in DUPLICATION_CLAIM_KINDS}
                duplication_links = [l for l in core_links if l["claim_id"] in duplication_claim_ids
                                     and l["relation"] == "supports" and l["target"] == "nearest_work"]
                # A novelty label and a nearby paper are not an equivalence
                # argument. Require an explicit current-version assertion whose
                # support is bound to each decisive comparison's actual source.
                duplicate_basis = bool(decisive and duplication_claim_ids and all(
                    any(l["evidence_id"] in n["evidence_ids"] for l in duplication_links) for n in decisive))
                if not duplicate_basis:
                    missing.append("Duplicate KILL lacks a current load-bearing equivalence/duplicate claim supported by decisive nearest-work anchors")
                if duplicate_basis and artifacts.get("valid") and all(n["evidence_ids"] and all(
                    any(e["type"] == "reading.confirm" and e["data"].get("evidence_id") == eid
                        and e["data"].get("scope") in {"section", "full_text"} for e in events)
                    for eid in n["evidence_ids"]) for n in decisive) and not any(
                    "different/unresolved paper" in m or m.startswith("Evidence ") for m in missing):
                    decision = "KILL"
            elif kill_type == "constraints" and scope == "current_constraints":
                projects = [e["data"] for e in events if e["type"] == "project.update"
                            and e["actor"] == "user" and e["trust"] == "T1"]
                constraints = projects[-1].get("constraints", {}) if projects else {}
                if any(d.get("mandatory") and d.get("status") == "failed" and any(
                    isinstance(constraints.get(k), dict) and constraints[k].get("status") == "confirmed"
                    and constraints[k].get("value") is not None and constraints[k].get("value") != ""
                    and constraints[k].get("source")
                    for k in d.get("constraint_keys", [])) for d in dependencies):
                    decision = "KILL"
            if decision != "KILL":
                missing.append("No verified, typed KILL basis; keep HOLD")
        result = {"candidate_id": candidate_id, "candidate_version": candidate["version"],
                  "snapshot": input_snapshot, "policy_version": POLICY_VERSION,
                  "machine_recommendation": decision, "requested_recommendation": recommendation,
                  "stage": stage, "scope": scope, "kill_type": kill_type, "reason": reason,
                  "missing": list(dict.fromkeys(missing)), "coverage": coverage,
                  "artifact_verification": artifacts, "human_decision": None,
                  "approval_status": "pending_human", "notice": NOTICE}
        if self.snapshot(candidate_id) != input_snapshot:
            raise ValueError("scientific inputs changed during assessment; retry a stable snapshot")
        if record:
            event = self.ledger.append("review.record", result, actor="model", trust="T2",
                expected_head=events[-1]["sha256"] if events else "")
            result = {**result, "review_id": event["id"]}
        return result

    def record_decision(self, review_id: str, decision: str, statement: str, *,
                        human: bool = False, override_reason: str = "") -> dict:
        if human is not True:
            raise ValueError("an actual human instruction is required; a model cannot approve itself")
        events = self._events()
        review = self._record(review_id, "review.record")
        if review["actor"] != "model" or review["trust"] != "T2":
            raise ValueError("review has an invalid origin")
        data = review["data"]
        latest = [e for e in self._events() if e["type"] == "review.record"
                  and e["data"].get("candidate_id") == data["candidate_id"]][-1]
        if latest["id"] != review["id"] or data["snapshot"] != self.snapshot(data["candidate_id"]):
            raise ValueError("review is stale; reassess before recording a human decision")
        if decision not in {"GO", "HOLD", "KILL"}:
            raise ValueError("unsupported human decision")
        if decision != data["machine_recommendation"]:
            _text(override_reason, "override_reason")
        return self.ledger.append("decision.record", {"candidate_id": data["candidate_id"],
            "candidate_version": data["candidate_version"], "review_id": review_id,
            "snapshot": data["snapshot"], "machine_recommendation": data["machine_recommendation"],
            "human_decision": decision, "statement": _text(statement, "actual human statement"),
            "override_reason": override_reason, "stage": data["stage"], "scope": data["scope"]},
            actor="user", trust="T1", expected_head=events[-1]["sha256"] if events else "")

    def revoke_decision(self, candidate_id: str, statement: str, *, human: bool = False) -> dict:
        if human is not True:
            raise ValueError("revocation requires an actual person's instruction")
        self._candidate(candidate_id)
        return self.ledger.append("decision.revoke", {"candidate_id": candidate_id,
            "statement": _text(statement, "actual human revocation")}, actor="user", trust="T1")

    def finalize(self, candidate_id: str) -> dict:
        events = self._events()
        snapshot = self.snapshot(candidate_id)
        reviews = [e for e in events if e["type"] == "review.record"
                   and e["data"].get("candidate_id") == candidate_id]
        decisions = [e for e in events if e["type"] == "decision.record"
                     and e["data"].get("candidate_id") == candidate_id]
        revocations = [e for e in events if e["type"] == "decision.revoke"
                       and e["data"].get("candidate_id") == candidate_id]
        review_current = bool(reviews and reviews[-1]["data"]["snapshot"] == snapshot)
        current = bool(reviews and decisions and decisions[-1]["data"]["snapshot"] == snapshot
                       and decisions[-1]["data"]["review_id"] == reviews[-1]["id"]
                       and decisions[-1]["actor"] == "user" and decisions[-1]["trust"] == "T1"
                       and reviews[-1]["actor"] == "model" and reviews[-1]["trust"] == "T2"
                       and not (revocations and revocations[-1]["seq"] > decisions[-1]["seq"]))
        from .core import ResearchCore
        artifacts_valid = ResearchCore(self.ledger.project).verify_artifacts().get("valid", False)
        current = current and artifacts_valid
        review_current = review_current and artifacts_valid
        return {"candidate_id": candidate_id, "snapshot": snapshot,
                "machine_recommendation": reviews[-1]["data"]["machine_recommendation"] if review_current else "HOLD",
                "previous_recommendation": reviews[-1]["data"]["machine_recommendation"] if reviews and not review_current else None,
                "assessment_required": not review_current,
                "human_decision": decisions[-1]["data"]["human_decision"] if current else None,
                "approval_status": "human_recorded" if current else "pending_human",
                "execution_authorized": False,
                "notice": "A recorded research decision does not execute experiments, publish or upload material. " + NOTICE}

    def export_dossier(self) -> dict:
        events = self._events()
        projects = [e["data"] for e in events if e["type"] in {"project.init", "project.update"}]
        project = projects[-1] if projects else {}
        dossier = {"schema_version": 2, "decision_contract_version": 2,
            "project": {"id": project.get("id", self.ledger.project.name), "question": project.get("question", ""),
                        "research_type": project.get("research_type", "empirical"),
                        "constraints": project.get("constraints", {}), "assumptions": project.get("assumptions", [])},
            "config": {"ranking_weights": {"scientific_value": 40, "differentiation": 35, "testability": 25}},
            "searches": [], "papers": [], "screening": [], "evidence": [], "ideas": [],
            "reviews": [], "pilots": [], "history": [{"type": "python_ledger_projection",
                "protocol": "ledger-json-v1", "requires_reassessment": True,
                "note": "Initial v2 projection; does not transfer Python reviews, approvals or new hash semantics."}]}
        papers = {}
        for event in events:
            if event["type"] == "paper.resolve":
                paper = event["data"]
                url = paper.get("url") or paper.get("source_url")
                if paper.get("title") and url:
                    papers[paper["id"]] = {"id": paper["id"], "title": paper["title"], "year": paper.get("year"),
                        "url": url, "identifiers": paper.get("identifiers", {}),
                        "version": paper.get("version") or "unknown", "accessed_at": event["ts"]}
            elif event["type"] == "search.result" and event["data"].get("status") in {"complete", "partial", "failed"}:
                data = event["data"]
                for paper in data.get("papers", []):
                    url = paper.get("url") or paper.get("source_url")
                    if paper.get("title") and url:
                        papers[paper["id"]] = {"id": paper["id"], "title": paper["title"], "year": paper.get("year"),
                            "url": url, "identifiers": paper.get("identifiers", {}),
                            "version": paper.get("version") or "unknown", "accessed_at": event["ts"]}
                dossier["searches"].append({"id": data["id"], "query": data["query"], "provider": data["provider"],
                    "searched_at": event["ts"], "status": data["status"], "scope": "Bounded Python acquisition",
                    "limitations": data.get("limitations", []), "result_paper_ids": data.get("result_paper_ids", [])})
        dossier["papers"] = list(papers.values())
        for search in dossier["searches"]:
            search["result_paper_ids"] = [p for p in search["result_paper_ids"] if p in papers]
        current_candidates = {}
        for event in events:
            if event["type"] == "candidate.upsert":
                current_candidates[event["data"]["id"]] = event["data"]
        for candidate in current_candidates.values():
            # No reading/claim is manufactured by a projection. Preserve user
            # fields, leave evidence associations pending explicit v2 reassessment.
            item = {k: deepcopy(candidate[k]) for k in ("id", "version", "title", "question", "research_type", "hypothesis", "contribution")}
            item.update({"evidence_ids": [], "evidence_links": [], "nearest_work": [],
                         "search_ids": [sid for sid in candidate["search_ids"] if any(s["id"] == sid for s in dossier["searches"])],
                         "novelty": {"status": "unclear", "reason": "Projection requires v2 reassessment", "coverage": "See local ledger"},
                         "feasibility": {"status": "unknown", "reason": "Projection is not a v2 approval", "dependencies": []},
                         "validation": {"status": "missing", **{k: "" for k in ("prediction", "falsifier", "design", "metric", "resource_estimate", "stop_rule")}}})
            dossier["ideas"].append(item)
        return dossier
