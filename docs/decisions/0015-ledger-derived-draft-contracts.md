# ADR 0015: Ledger-derived verification and tier contracts

## Context

The v0.9.0 re-review found that `check-draft` was still a self-report checker: a reference entry containing the string “已核验” passed, `unverified` was accidentally treated as verified by substring matching, `concept_memo` had no content contract, section checks could be evaded by renaming headings, and planned results could be written as ordinary prose. The reviewers also found residual client-facing conflicts (question counts, venue rules, a `"decision": "HOLD"` example, an outdated README link, and a repo-relative script path that breaks installed users).

A red-team review of the proposed fix added: `concept_memo` can leak citations through author-year/DOI/URL/footnote forms; a ledger ID proves existence, not support; heading whitelists need setext/HTML/bold parsing; quantitative claims need separate detection; label variants and exception clauses can bypass literal checks.

## Decision

- `check-draft` becomes a **tier contract checker**:
  - `concept_memo`: no numbered citations, no reference section, no experiment/statistics/budget/result sections; must carry a visible concept-memo/unverified banner; length limited.
  - `evidence_review`, `preregistration`, `research_plan`: require their own section whitelists; forbidden sections are errors.
- Verification is **derived from the ledger**, not self-declared. Reference entries must use `ledger:<source-or-evidence-id>`. `check-draft --ledger <project>` reads `evidence.anchor` and effective `reading.confirm` events; only **user/T1** confirmations with scope `section` or `full_text` count. Without `--ledger`, non-concept tiers fail.
- Reject unsupported citation forms (author-year, DOI, URL, footnote, fullwidth brackets) and content headings after the reference section.
- Detect quantitative effect claims outside plan/scaling sections, completed/observed claims in non-plan tiers, labels after NFKC/zero-width normalization, emoji traffic lights, and plan markers in result/abstract sections.
- Rewrite `templates/report.md` as four tier outlines with explicit delete-inapplicable instructions; remove pre-written “author verified” statements; document the ledger reference format.
- Fix residual conflicts: one question count (2–3 blocking, max 4), venue rules may not be assumed but content may proceed with format marked pending, remove the `"decision": "HOLD"` example, fix the installed-script path, update README links.
- Add adversarial tests: `unverified` substring, `[2,3]`, Chinese-adjacent labels, concept memo with experiment design, missing `--ledger`, self-declared verification, unknown ledger IDs.
- Keep the effect protocol as unexecuted; make its primary metrics co-primary (no composite score).

## Alternatives

- Keep self-declared status and add more regexes: rejected; the red-team showed the status is the root of the bypass.
- Require a full dossier/ledger for every report: too heavy for a concept memo; tiers plus no citations in concept_memo keep the light path honest.
- Use a model as checker: not deterministic, not reproducible, and still cannot prove citation support.
- Remove `check-draft`: loses the one mechanism that can catch honest omissions.

## Consequences

- Users must maintain a ledger and record user/T1 reading confirmations before a non-concept report can pass. This is intentionally stricter; reports without it stay concept memos.
- A ledger ID still does not prove the citation supports the sentence; the checker says so and cannot replace human verification.
- The report template is now four contracts rather than one full skeleton; models must choose and delete.
- Old drafts without tier or with unverified citations fail; the legacy demonstration is downgraded and moved aside.
- Effect claims remain unproven; the protocol is still a plan, not evidence.
