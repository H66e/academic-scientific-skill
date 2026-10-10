# Python evidence workflow

Use this reference for persistent AI/ML novelty checks and next-step decisions. Python 3.10+ and the standard library are sufficient. The CLI and importable API use one maintained runtime; no pip installation or model API is required.

## Boundaries

- A ledger records tool observations, model judgments and actual user statements separately. It is local sensitive research material, never a publication artifact by default.
- Acquisition does not imply parsing, delivery does not imply reading, an exact quote does not establish claim support, and provider completion does not mean literature completeness.
- A machine recommendation is `GO`, `HOLD` or typed `KILL`; `human_decision` remains null and `approval_status=pending_human` until an actual person decides. Commands never execute experiments, submit work or upload private material.
- Models must not invent `--human`, `--human-confirmed`, `--human-page-check` or a user's approval statement. These flags record existing human instructions; they do not authenticate identity.
- Native Python dossier tools use the current schema-3 contract and retain explicit v1/v2 migration; the Node entrypoints remain exercised compatibility oracles. Python is the default for both **new persistent evidence workflows** and existing dossier utilities, with separate data and approval semantics.

## Start and inspect

The evidence ledger and dossier auditor are separate supported workflows, both native Python. Use `research_mentor.py --project ...` for acquired-source receipts, exact anchors and append-only decisions; use `research_audit.py` directly on an existing dossier for legacy migration, dependency fingerprints, weighted ranking and actual independent receipts. Do not move approvals or hashes between them. `research_outputs.py` organizes supplied notes and references; `research_sources.py` returns independent acquisition JSON; `evolution_guard.py` checks read-only maintenance records. These helpers do not require `--project` or a Node installation.

```text
python -B <skill>/scripts/research_audit.py validate <private-project>/dossier.json
python -B <skill>/scripts/research_audit.py rank <private-project>/dossier.json --receipt-root <private-project>
python -B <skill>/scripts/research_sources.py search --query "public research terminology" --sensitivity public
python -B <skill>/scripts/research_outputs.py card <private-project>/notes.json
python -B <skill>/scripts/research_outputs.py bibtex <private-project>/source-records.json
python -B <skill>/scripts/evolution_guard.py snapshot <maintenance-directory>
```

Legacy `.mjs` entrypoints retain their old arguments and remain exercised compatibility oracles. Python standalone source-tool `--timeout` is milliseconds, matching its old interface; the ledger CLI's global `--timeout` is seconds. The standalone source query defaults to private and requires an explicit public/deidentified classification before an external request. The independent source adapter does not append ledger observations; choose the ledger workflow when automatic provenance recording is needed.

Use a project directory outside the formal source repository. Replace `<skill>` with the maintained/installed Skill path and `<private-project>` with a local private directory.

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> init --question "A concrete research question" --research-type empirical
python -B <skill>/scripts/research_mentor.py --project <private-project> doctor
python -B <skill>/scripts/research_mentor.py --project <private-project> status
```

The program name is `research-mentor`, not `rm` (which conflicts with deletion commands on Unix). `pip install -e .` optionally exposes that entry point for research code. Import `research_mentor.core.ResearchCore` and `research_mentor.judgment.Judgment` from the same source package. Copying a Skill folder provides its thin script, but does not register a Python package with pip.

`doctor` reports local capabilities. It does not probe the network, install software or infer the host model. Outputs use UTF-8 and a JSON envelope `{ok,status,data,warnings,errors,ledger_events,next}`. `--format markdown` is an optional human view. `ok`/exit code describe execution; inspect `status` for partial, offline, HOLD and pending-human states.

## Acquire without leaking a private idea

Search defaults to `private` and blocks external calls. Use public terminology or a deliberately de-identified query that the user has allowed; inspect the exact query before sending sensitive-derived terms. Paths, email addresses, common credential forms and credential-bearing URLs are also blocked. Heuristics cannot determine whether a technical idea is unpublished.

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> search "all:grouped AND all:query AND all:attention" --provider arxiv --family problem --sensitivity public
python -B <skill>/scripts/research_mentor.py --project <private-project> search "limitations grouped query attention" --provider crossref --family reverse --sensitivity deidentified
python -B <skill>/scripts/research_mentor.py --project <private-project> resolve arxiv:2305.13245v1
python -B <skill>/scripts/research_mentor.py --project <private-project> fetch --identifier arxiv:2305.13245v1 --paper-id <paper-id> --sensitivity public
python -B <skill>/scripts/research_mentor.py --project <private-project> fetch --local <local-public-or-private-source>
```

Use only IDs returned by the tools; do not type substitute IDs into a report. Failed executed searches can also return real ledger IDs, which record failure rather than usable evidence. Searches are arXiv or Crossref, one bounded result page per call; returned provider totals and truncation remain visible. A failed executed call remains in the ledger denominator; a blocked query is not an executed search. `--offline` never performs DNS/HTTP. An offline search can record local intent with `status=offline`, but never supports an external novelty claim. Local acquisition is available offline.

TLS, DNS public-address validation, redirects, timeouts, request/response budgets and URL credential checks remain active. `--trusted-provider-transport` is an explicit proxy mode for internally constructed official-provider URLs only. It does not authorize arbitrary proxy URLs or make a query private. Arbitrary public HTTPS URLs are supported when authorized by the task and classified public/de-identified; redirects cannot silently add a new host.

Raw bytes and Document IR are stored in project `sources/` using content hashes; receipt events bind request, provider, response, hash, status and result IDs. They identify locally acquired observations, not provider honesty. Do not publish ledger/query/source artifacts merely because they contain public paper IDs.

## Anchor, then record actual reading

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> show-source <source-id>
python -B <skill>/scripts/research_mentor.py --project <private-project> quote <source-id> "An exact passage actually present in the source" --block-id <block-id>
python -B <skill>/scripts/research_mentor.py --project <private-project> confirm-read <evidence-id> --scope section --context "Actual reader/context and inspected section"
```

Anchoring preserves case, mathematical symbols and scientific units; NFC/whitespace normalization is versioned. Quote offsets apply to the normalized block/document, not raw PDF bytes. Ambiguous occurrences require a narrower block. A miss creates no anchor; no fuzzy match is promoted to exact. Quote text, offsets, block, source/IR hashes and extractor are rechecked against retained bytes.

PDF is acquired but **not extracted** by this runtime. HTML extraction is conservatively lossy; source pages must be checked for critical equations, tables, figures or omissions. A human records an actual page check with `confirm-read ... --human-page-check`; a model must not add that flag on its own behalf, and — as in Boundaries above — the flag records the instruction rather than authenticating who issued it. Until parsing/page requirements are met, strict assessments hold the affected claim.

Publication identity is separate from a caller-supplied `paper_id`. A fixed-version arXiv resource can bind to matching resolved metadata. Local/publisher files require a person's actual identity/version check:

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> confirm-source <source-id> <resolved-paper-id> --version <actual-version> --statement "Actual user's source/version confirmation" --human-confirmed
```

This is T1 user confirmation, not automatic authentication. Never upgrade old free-text metadata or source associations to tool-observed identity.

### Supplementary reading and explicit withdrawal

`confirm-read` adds one observation of actual reading. Effective confirmations accumulate: deep reading followed by a supplementary abstract-only observation retains deep qualification. Abstract followed by an actual section observation can remove a reading blocker. Supplementation never adds a reading blocker, but every addition changes the scientific snapshot, stales the review and returns the human decision to pending. Reassess; do not exclude supposedly redundant readings from the snapshot.

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> retract-read <reading-confirm-event-id> --reason "Actual mistaken reading statement withdrawn"
python -B <skill>/scripts/research_mentor.py --project <private-project> retract-read <reading-confirm-event-id> --reason "Actual person's withdrawal instruction" --human
```

Withdrawal is a separate appended `reading.retract` event with exactly `{target,reason}`. It permanently retires that existing effective confirmation; no replacement reading is required for complete error withdrawal. For partial error, retract the false statement and then separately confirm the actual scope. The old event stays unchanged. A missing, unrelated, retraction or already retired target is rejected; a nonempty reason is required. Model/T2 may withdraw T2 confirmations only; actual user/T1 instructions may withdraw either T1 or T2. `confirm-read --human` records a person's reading statement without implying a page check; `--human-page-check` additionally records an actual visual check.

Deep qualification means at least one effective section/full_text confirmation; required visual qualification means at least one effective user/T1 visual_checked confirmation. Ordinary evidence reading, visual checks and duplicate-KILL use the same effective set. There is no latest-record or timestamp winner. Withdrawal is the only path that can lower reading qualification, and always requires reassessment. Legacy histories without withdrawals retain all confirmations; the policy upgrade makes old reviews stale without rewriting ledger bytes.

## Claims and scoped decisions

Append a candidate JSON with `id,title,question,research_type,hypothesis,contribution,search_ids,nearest_work,novelty,feasibility,validation`. The last three reuse the v2 field concepts; Ledger judgment policy is separate from dossier decision rules. `nearest_work` entries contain `paper_id,evidence_ids,delta,decisive`. Updates automatically create a new candidate version; prior claims do not silently transfer to it. Include the actual, candidate-relevant search IDs and the nearest comparisons that might change the decision.

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> candidate <candidate-json>
python -B <skill>/scripts/research_mentor.py --project <private-project> claim <candidate-id> "A source-grounded atomic claim" --kind nearest_delta
python -B <skill>/scripts/research_mentor.py --project <private-project> link <claim-event-id> <evidence-id> --relation supports --target nearest_work
python -B <skill>/scripts/research_mentor.py --project <private-project> coverage <candidate-id>
python -B <skill>/scripts/research_mentor.py --project <private-project> assess <candidate-id> --reason "Actual reasoning and limitations" --stage pilot
```

Only a current, bounded pilot can receive machine GO when recorded necessities pass: verified acquired sources/anchors, reverse query, nonempty completed provider boundary, nearest comparison, relevant-section reading, load-bearing evidence links, ready prerequisites and a falsifiable budgeted design. Partial-only searches, contextual-only links, unconfirmed identities, core contradictory evidence and missing required reading remain HOLD. These conditions prevent obvious omissions; they do not prove search quality or a claim's truth.

**Independent review is a division of labour, not a missing piece.** The T3 trust level (independent review) does not exist in the ledger runtime, and that is deliberate rather than a deferred gap: independent-review gating belongs to the dossier audit path, now available through native Python `scripts/research_audit.py` as well as the retained Node entrypoint, where a `kind === 'independent'` receipt bound to a version and review basis can authorize `full_validation`. The ledger core acquires and anchors evidence, records reading statements and machine judgments, and reports `execution_authorized: false` — it never authorizes execution, so no ledger command consumes an independent review and no trust level is reserved for one. Inventing a T3 pair with no consumer would be untested vocabulary that reads as a stronger guarantee than the code provides. If that ever changes, three things are required together, and nothing less: register the event type in `ledger.EVENT_ACTORS`, register the actor/trust pair in `schemas/ledger-event.schema.json`, and note that "independent" throughout this project means a **separate context**, not a separate person — the dossier auditor realizes it as `author_context` and `evaluator_context` values that `research_audit.py` and its Node counterpart require to differ, so it is context isolation and never identity isolation. Both append and verification reject event types absent from `EVENT_ACTORS`; the schema enumerates the same types. Register any new type together with its payload validation and consumers, so admission never implies an implemented capability.

Typed `KILL` requires `--recommendation KILL --kill-type duplicate|scientific_refutation|constraints` and the matching scope. Literature-based duplicate/refutation requires verified, correctly linked, read evidence for current-version load-bearing claims; an effective unambiguous scientific contradiction with locatable artifacts can also supply explicit result-based refutation. Duplicate KILL requires an explicit `--kind mechanism_equivalence` or `--kind duplicate` claim with `supports` links targeting `nearest_work` for every decisive nearest comparison; a duplicate label alone is insufficient. Context-only claims cannot refute the core hypothesis. A constraints KILL requires confirmed user constraints linked to failed mandatory dependencies. An execution failure, label, empty search or abstract similarity never becomes a scientific KILL. Current policy `python-credibility-v4` binds result and effective-reading semantics to snapshots, superseding v3 without rewriting history.

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> decision <review-event-id> --decision HOLD --statement "Actual person's instruction" --human-confirmed
python -B <skill>/scripts/research_mentor.py --project <private-project> finalize <candidate-id>
python -B <skill>/scripts/research_mentor.py --project <private-project> revoke <candidate-id> --statement "Actual person's withdrawal" --human-confirmed
```

An override also requires `--override-reason`. Human decisions bind to the latest review and a scientific-input snapshot; changed evidence, artifacts, candidate or project records returns `pending_human`. The initial snapshot is deliberately conservative and covers the project's scientific ledger, so unrelated new science may also require reassessment. Hashes and flags do not prove identity or authorization; a host must preserve actual user instructions. Recording GO never grants arbitrary external mutations or experiments.

## Revisit and export

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> recheck <search-id> --sensitivity public
python -B <skill>/scripts/research_mentor.py --project <private-project> next <candidate-id>
python -B <skill>/scripts/research_mentor.py --project <private-project> lint <answer-markdown>
python -B <skill>/scripts/research_mentor.py --project <private-project> verify-ledger
python -B <skill>/scripts/research_mentor.py --project <private-project> anchor-ledger
python -B <skill>/scripts/research_mentor.py --project <private-project> verify-artifacts
python -B <skill>/scripts/research_mentor.py --project <private-project> export-dossier
```

`recheck` repeats the selected query and reports newly returned IDs, not every newly published work. `next` reports limited coverage gaps, not an autonomous planner or all judgment prerequisites. An empty `next` list does not mean GO; use the current `assess` result's `missing` list for decision blockers, including reading, identity, feasibility and validation gates. `lint` only checks lexical DOI/arXiv identifiers against acquired metadata, not citation entailment or all reference styles. Full output is local; show the user the decision, decisive sources, nearest deltas, remaining gaps and cheapest bounded next check instead of raw command logs.

The schema-3 projection contains acquired metadata, searches, candidates, declared claims, complete result classification history and run invalidations. It intentionally omits evidence associations and reviews rather than guessing fingerprints or approvals; native Python and Node dossier validation succeeds while ranking remains HOLD. It is an initial interoperable export, not lossless round-trip migration. The authoritative local ledger retains the new information. Native Python `validate/fingerprint/rank/migrate/card/draft/bibtex`, independent receipts and evolution checks are available; Node retains the matching compatibility entrypoints; consult [data-contract.md](data-contract.md) for current contracts and legacy migration.

## Record, correct and withdraw results

Result interpretation in [feedback.md](feedback.md) remains the host's scientific responsibility. The runtime records explicit declarations; it does not execute experiments, import arbitrary logs, authenticate artifacts or calculate scientific calibration. Keep separate `kind` and `outcome` fields: `smoke` is a kind, not an outcome.

```text
python -B <skill>/scripts/research_mentor.py --project <private-project> record-result <result-json>
python -B <skill>/scripts/research_mentor.py --project <private-project> reclassify-result <result-id> --outcome inconclusive --reason "Actual interpretation correction and its basis"
python -B <skill>/scripts/research_mentor.py --project <private-project> invalidate-result <result-id> --reason "Actual person's finding that the test is invalid" --human-confirmed
python -B <skill>/scripts/research_mentor.py --project <private-project> results <candidate-id>
```

Result JSON requires `run_id,candidate_id,candidate_version,kind,outcome,artifacts,summary,limitations,affected_claims`; an ID may be supplied or generated. `affected_claims` is an array of `{claim_id,reason}` explanations. `not_run` may have empty artifacts; executed declarations need locatable nonempty artifact references. Record real locations and uncertainties, never fabricated measurements. `--human-confirmed` records an actual human instruction, without authenticating identity.

Reclassification appends a same-run causal `supersedes` record and a reason; independent runs cannot cancel each other's contradictions. Effective heads use references, not record order. Multiple lawful heads force HOLD, including all-supported forks. Only actual user/T1 invalidation can withdraw whole-run eligibility; a later classification cannot revive that run. Both changes are review inputs. Removing a result blocker requires reassessment and a new human decision, never reuses old GO. Superseded, invalidated or ambiguous run results cannot alone justify scientific-refutation KILL. See [data-contract.md](data-contract.md) for the corresponding dossier lifecycle and validation tiers.

## Reliability and evaluation

The ledger uses exclusive writer locks, fsynced appends, sequential IDs, timezone timestamps and a content chain. It rejects a torn final line or edited chain instead of repairing silently.

The event vocabulary is closed. Older implementations accepted unknown types; these ledgers now fail verification and require explicit inspection and migration, without silently deleting or ignoring events. Result events are registered with payload checks and effective-state consumers. Initial vocabulary closure did not reinterpret supported facts; later interpretation changes require a policy change in the snapshot digest, while retaining historical ledger bytes and hashes. Policy changes conservatively stale all project reviews and human decisions; a policy identifier itself never creates GO or changes scientific facts.

`verify-ledger` checks the chain, envelope, registered roles and new-event payload shapes. `Judgment` consumers additionally resolve scientific references and transitions. Direct `Ledger.append` is a low-level structural interface, not the research workflow API; use `confirm_read/retract_read` and result methods for existing-target and current-eligibility write preconditions. A structurally valid ledger is not proof that every scientific transition is semantically valid.

A chain cannot detect its own tail being removed: every surviving event still points at its predecessor, so a shorter ledger verifies clean. `ledger.anchor.json` therefore records the expected head and event count from outside the chain, and `verify-ledger` reports `anchor` as `matched`, `mismatch` or `absent`. A mismatch is a hard failure: `verify-ledger` reports invalid and `append` refuses to extend the ledger until a person investigates. `anchor-ledger` records the current state; run it on a project created before anchoring, and only once you are satisfied that the contents are the ones you mean to keep, because anchoring adopts whatever is there. The anchor shares the ledger's directory and threat model, so it detects accident, loss and partial writes — not a deliberate owner who rewrites both.

Do not delete a lock until verifying its writer stopped. Use separate projects for concurrent independent evaluations. Hash protocol `ledger-json-v1` accepts integer/string values, not floats; it is not Node canonical JSON and is not a cross-language fingerprint claim.

Run `python -B evaluation/run-python-tests.py` and `python -B evaluation/skill_tools.py` with `check-skill`, `check-examples`, `package` and `check-package` from the repository root. Development acceptance also runs the retained Node regressions and requires cross-language checks with `RESEARCH_MENTOR_REQUIRE_NODE_CONFORMANCE=1`. Protocol fixtures are synthetic. Tests measure program behavior and compatibility, not recall, scientific usefulness or honesty. Preserve real failures and unknowns; public/source-grounded examples and actual human adjudication are still needed before scientific-effectiveness claims.
