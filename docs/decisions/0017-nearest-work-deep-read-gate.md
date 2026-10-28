# ADR 0017: Nearest-work deep-read gate (claim-level, not hard chat block)

## Context

The reviewers agreed that judging novelty/value from abstracts is the highest-cost failure mode, but rejected a blanket "read full text before answering" gate: it would block users who lack access or need a fast provisional view, and it would create false safety ("read two papers = completed search"). Their six recommendations were: claim-level A/B/C grades; kill-question-driven reading; an auditable nearest-selection step; model-first reading; a falsification-style C template; and cache/staleness rules.

## Decision

- Add `references/deep-read-gate.md` and route novelty/gap/equivalence/investment claims through it. Chat is not hard-blocked; high-cost claims are graded and downgraded.
- Grades:
  - A: required nearest-work reading with locator + flip condition; formal but scoped conclusion.
  - B: at least one relevant section read; conclusion plus remaining risk.
  - C: abstract-only/unread/no access; only "provisional conclusion + flip condition + minimal check + access path".
- Require two kill questions per key nearest work, with answer and locator. "Read full text" without a targeted question/answer/locator does not count.
- Require an auditable nearest-selection section: at least two query phrasings, a candidate table with rationale, and possible missed clusters.
- Prefer model-first reading of open full text; hand only inaccessible items to the user. Distinguish `reader:model` and `reader:user`; confirmation is not proof of understanding.
- Report template and `check-draft`:
  - evidence_review+ reports require "近邻选择与深读记录" (two queries + table) and "主张—证据等级" table.
  - A/B claims must bind `ledger:<id>` with effective user/T1 section/full_text reading; C claims need a flip condition and a "暂定判断（C 级）" section containing flip condition and minimal check.
  - C claims may not appear in "当前判断与下一步".
- Cache/staleness is documented (same paper/version/scope reuse; nearest set expires after 6 months or new direct nearest/version; scope expansion retriggers).
- No hard chat block; no new ledger event types; no claim that reading is authenticated.

## Alternatives

- Blanket hard block before every answer: rejected by both reviewers; blocks fast exploration and users without access.
- Global "read N papers" count: rejected; it creates false safety and does not bind evidence to specific claims.
- Require full_text for everything: rejected; section-level reading suffices for gap/condition claims and reduces cost.
- Only prompt guidance without checker: rejected; the report-level claim table and C-section enforcement are the hard part.

## Consequences

- Reports become longer (nearest-selection table, claim table, C section); the template must be trimmed by tier.
- `check-draft` can enforce structure/binding but cannot verify whether a claim is truly supported, whether the nearest selection is complete, or whether the reading was understood.
- Chat answers may still be provisional; C-level answers must visibly say so and give flip conditions.
- Ledger schema is unchanged; kill questions live in the report/reading notes, not in a new event type.
- Effect evidence remains absent; the gate improves discipline, not proven research quality.
