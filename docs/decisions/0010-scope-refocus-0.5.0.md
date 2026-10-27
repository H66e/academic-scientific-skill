# ADR 0010: Scope refocus for 0.5.0 — retire result interpretation, promote writing

## Context

The 0.4.0 skill combined two purposes: deciding what is worth researching, and interpreting experimental results afterwards. Result interpretation had grown into a large surface: a six-state classification in `SKILL.md`, `feedback.md`, four ledger CLI commands (`record-result`, `reclassify-result`, `invalidate-result`, `results`), result events in the ledger vocabulary, result-derived assessment blockers and KILL branches, snapshot inputs, a policy version (`python-credibility-v4`), frozen conformance cases and 41 lifecycle fixtures. It also coupled the decision gates to information the skill cannot verify: a recorded result is a declaration, not evidence that an experiment ran or that its interpretation is right.

The owner has narrowed the intended scope to four things: finding directions, novelty checking (查新), judging whether a direction is worth doing, and writing papers, surveys and proposals. Other capabilities are to be added later only as the owner's research requires them. Keeping the result surface would keep the skill large, keep an unpromoted declaration workflow in the decision path, and dilute the four target tasks.

## Decision

- Remove result interpretation from the user-facing skill: the result classification section, its routing row, `feedback.md`, and all result command references are removed. Reading lifecycle (`confirm-read`/`retract-read`), evidence acquisition, anchors, claims, nearest work, GO/HOLD/KILL and human decision binding are unchanged.
- Promote writing to a first-class task. Full drafts of papers, surveys and proposals may be produced from real supplied or acquired sources, with templates, claims-to-evidence mapping and citation discipline. Fabricated citations, numbers, experiments, results or venue rules remain prohibited; unrun experiments stay clearly marked as plans; human review before submission is mandatory.
- Retire result interpretation at the runtime boundary. `Judgment` no longer records, corrects, invalidates or exposes results; assessments no longer consume result state; result-based scientific-refutation KILL is removed while literature-evidence contradiction, duplicate/mechanism-equivalence and confirmed-constraint KILL remain; the snapshot digest excludes `result.record`/`result.invalidate`; policy becomes `python-credibility-v5`.
- Keep legacy compatibility. The 17-type ledger vocabulary, `event_payloads` admission rules and `results.py` validators stay so old ledgers still verify and malformed legacy events are still reported. The four CLI commands are removed, so old result events are readable only by inspecting the JSONL and no new result records are produced by the skill.
- The dossier/reference stack keeps its frozen schema-3 result fields for maintenance compatibility ([ADR 0009](0009-acquisition-direction-and-payload-admission.md)); that stack does not gain new result features either.
- Existing reviews become stale once because the policy identifier and snapshot inputs change; reassessment is required. Old ledgers and their result events are not rewritten or deleted. Users who still need result logging stay on 0.4.x or keep that record outside this skill.

## Alternatives

- Keep result interpretation and only demote it in documentation: leaves the unpromoted workflow and its gates in the code, and keeps four CLI commands the owner does not want. Rejected.
- Hard-delete result events and dossier result fields: would make old ledgers fail verification and require a new ledger/dossier protocol plus migration, contradicting the repository's rule to preserve old research records. Rejected.
- Replace result interpretation with an external experiment tracker: a separate integration is a future capability (ADR 0009 defers new providers/integrations) and not needed to narrow the scope now. Deferred.

## Rationale

A narrow skill is easier to use, review and extend: the four retained tasks share one evidence discipline, while result interpretation required a different one (execution artifacts, experimental design, calibration) that the runtime cannot verify. Retiring it at the runtime boundary prevents future assessments from depending on unverifiable declarations, and keeping the vocabulary/validators avoids breaking historical ledgers. Promoting writing addresses the owner's actual next need without turning the skill into an autonomous paper generator: the honest boundaries from the existing references carry over.

## Consequences

- The four result commands disappear; scripts using them must switch to 0.4.x or record results elsewhere. A ledger containing result events still verifies, but those events no longer affect decisions.
- Old reviews/decisions are stale after the policy change and need at least one reassessment; the skill does not migrate or reinterpret them.
- Writing output is larger and more useful, but the skill still cannot guarantee novelty, correctness, acceptance or any experimental result; citations must trace to real sources and reading scope.
- `docs/decisions/0004` and `0005` remain as historical records with a supersession note; the validation records for 0.3.0–0.4.0 are not rewritten.
- The result fixture file remains as historical evidence; tests that exercised the retired semantics are removed rather than rewritten to look like new evidence.

## Implementation status (2026-10-27)

- The runtime change is implemented: policy `python-credibility-v5`, no result consumption in assessment/snapshot/KILL, and no result CLI/API. Old ledgers still pass `verify-ledger`/`verify-artifacts`; `assess` on a ledger containing retired result events returns a visible `legacy_result_events_ignored` count and warning (not a blocker), and reassessment neither restores an old GO nor revives a direction rejected after a result-based KILL. `export-dossier` keeps projecting legacy result history but labels it as a historical declaration, not a current verdict.
- Structural validation is not weakened: `results.py` validators and the 17-type payload admission remain for legacy events; only the retired result *semantics* (effective heads, invalidation eligibility, result-derived gates) are no longer interpreted. The covered reverse tests and compatibility tests live in `evaluation/tests/test_python_contract.py` and `test_ledger_payloads.py`.
- Removed tests (behavior retired, not evidence deleted): `skills/ai-research-mentor/tests/python/test_results.py` (13 cases), `evaluation/tests/test_result_cli.py` (2 cases), `evaluation/tests/test_result_conformance.py` (7 cases). They remain available at the `v0.4.0` tag. Frozen fixtures were not edited; the evolution baseline batch 2 is preserved and only its renamed editable-whitelist path (`references/feedback.md` → `references/research-outputs.md`) is migrated for comparison after the file-set change recorded in ADR 0007.
- Interoperability: 0.4.x can still read a ledger structurally, but a v5 review appears stale there and must not be treated as a current decision; upgrading or downgrading both require reassessment. The installed Codex copy is synchronized only after release, and its version is checked against the release package.
