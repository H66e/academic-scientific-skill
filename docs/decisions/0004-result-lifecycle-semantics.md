# ADR 0004: Result lifecycle and effective reading semantics

## Context

The existing [Node contract](../../skills/ai-research-mentor/references/data-contract.md) blocks GO for a current-version scientific contradiction; the [feedback workflow](../../skills/ai-research-mentor/references/feedback.md) distinguishes failed execution, inconclusive tests and scientific outcomes. Python records evidence but has no result lifecycle. Classification correction, run invalidation and reading correction need explicit meanings before either runtime changes its judgments.

This ADR is the single language-neutral specification for that future work. It freezes semantics, not scientific-effectiveness claims. The current Node contract and Python judgment behavior remain authoritative until their corresponding implementation and migration steps ship.

**2026-10-10 implementation note:** the Step 1 boundaries below are historical. Subsequent implementation registers validated `result.record`, `result.invalidate` and `reading.retract`, adds effective-state gates, cumulative reading with explicit withdrawal, Node v3 migration and result-preserving projection. Rollout and policy boundaries are recorded in [ADR 0005](0005-policy-bound-lifecycle-rollout.md); the frozen normative clauses remain unchanged.

## Decision

### Implementation boundary

- Step 1 implements only closure of the existing Python event vocabulary in append, verification and its schema, with matching regression tests. Known event actor/trust pairs remain unchanged.
- `result.record`, `result.invalidate` and `reading.retract` remain unregistered and unimplemented in Step 1; empty or arbitrary payloads must not acquire legitimacy by reserving their names early.
- Step 1 does not change `judgment.py`, `POLICY_VERSION`, Node decision/schema versions, result projections or reading predicates. The following lifecycle and acceptance clauses are requirements for later implementation.
- Closing admission does not reinterpret a ledger containing only supported events, so Step 1 does not bump judgment policy. It does tighten compatibility: old implementations accepted unknown event types; ledgers containing them will now fail verification and require explicit investigation/migration. Do not silently discard or rename those events, or claim every old ledger remains compatible.
- Register each future event together with its complete payload validation, actor/trust rules, consumers and tests. The current Python envelope is closed, but its formerly open type vocabulary was a separate issue; Node permits many extra object keys while its declared enums are already closed.

### Result identity and records

- A run identifies an actual attempt or explicitly not-yet-run plan, bound to one candidate and one candidate version. New classifications of the same attempt retain its `run_id`; a genuinely new attempt receives a new run identity. Relabeling an old attempt is not a new experiment.
- A classification has a unique record ID and `run_id`, `candidate_id`, `candidate_version`, `kind`, `outcome`, `artifacts`, `summary`, `limitations`, `affected_claims`, plus an optional `supersedes` reference to a classification of that same run and candidate version.
- Reclassification includes a nonempty reason and preserves the prior record. `supersedes` is the causal replacement relation; timestamps, array order, ledger sequence or actor seniority cannot select the winning classification.
- `kind` remains `smoke` or `scientific`; `outcome` remains `not_run`, `execution_failed`, `inconclusive`, `supported` or `contradicted`. A smoke pass is not scientific support, a process failure is not refutation, and a null effect is not automatically a contradiction.
- `not_run` permits an empty artifacts array; reported executed/scientific results require locatable artifacts. The host must assess control validity, applicability, uncertainty and whether the observation meets the predeclared falsifier. Structure and hashes do not establish those facts.
- `affected_claims` contains structured claim references for explanation. It does not make the result gate claim-specific. Changing a resolvable claim reference to another or to a dangling reference cannot change the result blocker.
- `result.record`, including reclassification, accepts model/T2 and user/T1 declarations. A model may visibly correct a prior classification, including one that blocked progress; this is not an increase in trust or permission to rewrite history.
- `result.invalidate` accepts user/T1 only and identifies the run, its candidate/version, a referenced classification, a nonempty reason and recording time. It withdraws that run's scientific eligibility, rather than changing its outcome.
- Invalidation applies to the entire identified run in that candidate version, not just one classification head. Appending a different classification cannot revive it. Resuming execution requires a genuinely new run; there is no implicit uninvalidate operation.

### Effective result state

For each structurally valid, non-invalidated run, `effective_heads(run)` is every classification not superseded by another valid classification of that run. Retain all records when computing this relation; superseding a replacement does not revive its ancestors.

```text
contradiction_blocker(candidate_version) =
  exists eligible run, exists head in effective_heads(run):
    head.kind == scientific and head.outcome == contradicted
ambiguity_blocker(candidate_version) =
  exists eligible run: count(effective_heads(run)) > 1
result_requires_hold = contradiction_blocker or ambiguity_blocker
```

- One terminal head is the normal case, not a requirement that makes every fork contract-invalid. Multiple lawful heads are `ambiguous`, emit a warning and require HOLD even if none says `contradicted`.
- Forks are detected conservatively; this specification does not promise automatic branch resolution or merging. A later workflow must resolve them explicitly without erasing conflicting classifications.
- HOLD and scientific-refutation KILL must consume this same effective state. A superseded or invalidated contradiction cannot serve as current KILL evidence; a current contradiction does not automatically issue KILL. An ambiguous run cannot alone supply a conclusive scientific KILL basis.
- An unrelated supported run cannot cancel an effective contradiction from another run. A reclassification can remove a result blocker within the same version, but never restores an old GO review.
- Gate scope is the candidate version. Old-version results retain their historical scope; carrying their relevance into a revised candidate requires explicit reasoning, not rewriting their original version.

### Two validation tiers

| Condition | Required handling |
| --- | --- |
| Missing candidate, invalid candidate version or required field/type | Contract-invalid |
| Missing `supersedes` target; cross-run/candidate/version replacement | Contract-invalid |
| Self-reference or replacement cycle | Contract-invalid |
| Invalidation target absent, mismatched run/version or unauthorized actor | Contract-invalid |
| Multiple lawful terminal heads | Run-level ambiguous + warning + HOLD |
| Malformed `affected_claims` structure | Contract-invalid |
| Well-formed but unresolved `affected_claims` reference | Warning + `affected_claims_degraded`; result state unchanged |
| Nonempty but scientifically unhelpful reason | Structurally valid; host quality failure |

A reference that determines identity, scope or a transition must resolve. Explanatory references that do not participate in the gate may degrade visibly. Do not turn either class into the other merely to improve a score.

### Effective reading facts

- `reading.confirm` adds a historical observation; it does not replace another reader's scope. Multiple confirmations may coexist and are not ambiguous result branches.
- Future `reading.retract` has payload exactly `target` and a nonempty `reason`, with actor/trust in the event envelope. The target resolves unambiguously to an existing, currently effective `reading.confirm`; no `scope` or `evidence_id` is accepted in the retraction payload.
- The target already binds the observation to its exact acquired evidence/source version. Retraction cannot transfer reading to a different anchor, paper or version, and cannot target a retraction or an unrelated event.
- A missing or wrong-type target is contract-invalid. Retracting an already retired confirmation is rejected by the judgment write precondition; the ledger layer validates structure rather than inventing a second lifecycle authority. Effective-set consumers must resolve and validate transitions before applying them.
- Model/T2 may retract T2 confirmations only; user/T1 may retract T1 or T2 confirmations. A host may record the human flag only on an actual person's explicit instruction, never on inferred approval. These classifications do not authenticate identity.
- A retraction retires its target permanently from the effective set, preserving both events. Complete withdrawal requires no invented replacement scope. Partial correction is retract then confirm with the actual corrected facts; it does not edit the old event.
- `effective_readings(evidence)` is the confirmations for that immutable anchor minus validly retracted confirmations. Deep-read qualification is existence of an effective `section` or `full_text` observation; required visual qualification is existence of an effective user/T1 observation with `visual_checked=true`.
- Deep reading, lossy-source visual checks and duplicate-KILL reading checks must share this effective set. Retracted confirmations cannot survive in a separate consumer's historical `any()` scan.
- Plain confirmation is monotone only for reading qualification: it cannot add a reading-related blocker. It still changes the project snapshot, makes previous reviews stale and returns human decisions to pending. It does not guarantee GO or freeze other blockers.
- Legacy confirmations have no invented retractions: all are effective under the future predicate unless explicitly retired. Therefore this interpretation change requires a policy upgrade even when no ledger bytes change.

### Reviews, policy and authorization

- Every relevant result classification, reclassification or invalidation is scientific review input. Removing a result blocker does not remove the requirement for a new assessment and, where applicable, a newly recorded human decision.
- Node v3 must explicitly include the candidate's complete result classification history and relevant `result_invalidations` in `reviewBasisHash`; hashing only surviving heads loses causal input. New fields do not enter this explicit projection automatically.
- Python retains its current whole-project snapshot: all scientific events participate except `decision.record`, `decision.revoke` and `review.record`. New result and reading events enter through this existing deny-list; confirm this with tests rather than create another fingerprint. Unrelated scientific additions may still stale reviews.
- Changes to accepted evidence interpretation or effective-state predicates must ship with a `POLICY_VERSION` change in the same implementation. The policy is an actual digest input, not merely a returned label; do not change stored historical snapshots or repair their version fields to revive approval.
- A policy upgrade globally stales all candidate reviews and bound human decisions, including unrelated candidates. Prefer conservative over-invalidation to falsely current approval; defer finer version axes with the dependency model. The upgrade itself does not change scientific predicates or create GO.
- When isolated in a migration test, changing only the policy identifier must not alter evidence integrity, acquisition artifacts, effective facts or scientific `missing` reasons. It invalidates derived review/decision currency. After reassessment, old human decisions remain pending until newly recorded for the current review.
- Vocabulary closure alone does not imply every future admission change is policy-neutral. If a change reinterprets admissible facts or their eligibility, reassess the judgment-policy boundary even when implemented inside a validator.
- GO is a bounded research recommendation. Result classification, invalidation and human decision recording grant no experimental execution, publication or external-write authority. Node independent-review gating remains its existing separate-context responsibility; this ADR creates no Python T3 mechanism.

### Node v3 migration and Python projection

- Future Node `schema_version=3` and `decision_contract_version=3` require `pilot.run_id` and top-level `result_invalidations`. Version-gate these requirements so a valid v2 input can still reach migration.
- Migration is validate v2, clone, set both versions to 3, initialize `result_invalidations=[]`, materialize each legacy `pilot.run_id=pilot.id`, preserve missing `supersedes` as no replacement, archive old reviews with reassessment required, then validate v3. Do not permanently maintain a second implicit `run_id := id` reading rule.
- Each old pilot initially remains an independent run; migration preserves its artifacts, outcome and contradiction effect. It fabricates neither invalidation nor supersession. Old v2 reviews/receipts cannot become current by relabeling versions or hashes.
- Future Python export maps candidate identity to Node `idea_id/idea_version`, classification IDs to pilot IDs, and supersession references consistently; it projects all classification history and valid invalidations, preserving run identity and provenance declarations. It must not retain an empty `pilots` stub once claiming result support.
- Node invalidation snapshots retain `id,run_id,idea_id,idea_version,result_id,reason,recorded_at` and declared user provenance; the referenced result must belong to that run/version. Node validates relationships in the supplied snapshot, not that nobody removed history before supplying it.
- Python's append-only ledger and Node's mutable dossier are intentionally different persistence guarantees. Export must not fabricate reading, source verification, independent receipts, historical events or transferable review approval; incompatible hashes remain incompatible.

### Acceptance requirements for later implementation

Step 1 runs vocabulary-closure checks only. Freeze the following future regression requirements; do not implement result/reading predicates just to make their tests executable now.

1. An earlier same-version contradiction survives a later independent supported run; a valid same-run superseding correction may remove that result blocker while still making the review stale.
2. Cross-run/version replacements, missing targets, cycles and invalid authorization fail; lawful forks warn and HOLD, including all-supported forks. HOLD and KILL agree on effective result state.
3. User invalidation removes a run's eligibility, changes review basis and cannot revive old GO; model invalidation fails, and a later classification cannot reactivate the invalidated run.
4. `affected_claims` H1/H2/dangling H3 leave blockers equal, while malformed structure fails. Migration materializes run IDs, preserves existing contradictions and archives old reviews; projection does not drop results or invalidations.
5. Supplemental abstract reading preserves earlier effective deep/visual qualification, yet stales reviews; targeted retraction removes only its confirmation. T2-to-T1 retraction, retired/missing/wrong-type targets and extra retraction fields fail; all reading consumers agree.
6. With identical ledger bytes, an implementation switching reading predicates must change the policy-bound snapshot: old review is stale, old human decision is pending, the previous recommendation is retained and the old review cannot receive a new decision. Ledger verification remains valid with the same event count; freshly assessed reviews carry the new policy and can receive a newly instructed human decision.
7. Isolating only the policy upgrade leaves artifact integrity and scientific `missing` reasons unchanged; subsequent reassessment does not inherit human approval. Fresh explicit decision recording restores currency without rewriting old events, hashes or reading facts.
8. Cross-runtime fixtures compare declared scientific facts and gate outcomes through explicit adapters, not numerical fingerprint equality; retain negative controls and run actual production ranking paths.

## Alternatives

- Latest timestamp/array entry wins: rejected because it can silently erase a conflicting result or another reader's observation.
- Every contradiction blocks forever: rejected because visible reclassification and user-controlled run invalidation have different legitimate purposes.
- Implement a full result engine, migration and new reading policy in Step 1: rejected because admission closure is independently reviewable and must not legalize unvalidated future events.

## Rationale

Explicit run causality separates changed interpretation from changed evidence eligibility. Effective reading facts model cumulative observation with accountable withdrawal. Both retain scientific uncertainty and make changed inputs trigger reassessment rather than resurrect approval. The two validation tiers preserve usable evidence without pretending ambiguous states are resolved.

## Consequences

Step 1 has one runtime impact: unsupported event types are rejected instead of silently admitted. Result storage, reading retraction, Node v3 migration, projection and policy upgrades remain future work requiring their own behavior checks. Local histories stay private by default. Tests establish contract behavior, not faithful interpretation, complete search, human identity or improved research outcomes.
