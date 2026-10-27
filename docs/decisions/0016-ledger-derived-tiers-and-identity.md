# ADR 0016: Ledger-derived report tiers and citation identity binding

## Context

The independent review of v0.10.0 and the follow-up implementation guidance found that `check-draft` still trusted self-declared tier and reference status: a citation could bind any verified ledger ID, a research plan without citations could claim results, content after the reference section escaped checks, and concept memos could use synonym headings to hide experiment design. The reviewers' common instruction was: derive the tier from the ledger, bind citation identity/version/scope, parse the whole document first, and test with a real ledger to avoid mock-only validation.

## Decision

- Add `runtime/research_mentor/report_tier.py`: derive the highest allowed report tier from a verified local ledger. Only effective user/T1 `reading.confirm` events with `section` or `full_text` scope count; at least two distinct canonical sources are required for `evidence_review`. The ledger schema has no preregistration/plan event types, so `preregistration` and `research_plan` are **capped**: they cannot be derived or delivered in this version. This is deliberate: do not fabricate evidence tiers.
- `check-draft --ledger <project>` now:
  - verifies the ledger chain and artifacts;
  - compares declared tier against derived tier (`declared > derived` fails; lower declared gets a warning);
  - parses the whole document (ATX, setext, HTML and single-line bold headings) and requires references to be the last section with no content after them;
  - enforces closed heading sets per tier (no synonym headings);
  - requires five-column reference rows: number, title, identifier (`doi:`, `arXiv:` with version, or `url:`), `ledger:<id>`, reading scope;
  - binds each citation to source identity/version/scope from the ledger, rejects duplicate canonical sources and untrusted/missing readings;
  - rejects effect claims outside a same-line `[PLANNED: ...]` span or a verified citation, and completed claims without a citation;
  - fixes false positives for `GO term`/`Gene Ontology` and keeps “completed retrieval” out of completed-result detection;
  - limits concept memos to 4000 visible characters and forbids citations/references/design sections.
- Add a real-ledger test: build local sources via `ResearchCore.fetch`, `quote`, and human `confirm_read`, then assert `derive_tier` returns `evidence_review`; no mock of `effective_readings` or `_ledger_verified`.
- Update the report template to four tier outlines, five-column references, the tier cap, and no prewritten verification claims.
- Keep `effect-protocol.md` unexecuted and co-primary; no effect claim is made.

## Alternatives

- Keep self-declared tiers: rejected; the reviewer showed the model can select a tier and bypass checks.
- Add new ledger event types for preregistration/plan: rejected for this version; `ledger-json-v1` is frozen and adding event types requires a separate contract change.
- Expand checker to papers/surveys: rejected; Results, author-year citations and user-provided results need a separate design and would multiply false positives.
- Keep mock tests: rejected; they hid the self-report hole.

## Consequences

- Non-concept reports require a real ledger with user/T1 section/full_text reading confirmations and identity-bearing sources. Without it they stay concept memos.
- `preregistration` and `research_plan` are unreachable until the ledger has dedicated events; the skill must not imply otherwise.
- Citation identity still proves only that the bound source has the claimed identity/version/scope, not that it supports the sentence. This limitation is in code, template and validation.
- The checker remains report-only; paper/survey drafts are not mechanically checked.
- Version 0.11.0 changes the shipped file set (new module), package hash and installer copy.
