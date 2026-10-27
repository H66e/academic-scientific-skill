# ADR 0014: Major revision after external-style review

## Context

Two harsh reviews of v0.8.0 (Claude Fable 5.1 and Claude Opus 5.5, invoked through the user-provided API) reached the same verdict: major revision. The main findings were:

- no effect evidence; the only ablation was four rounds with one sample per condition and summary-level material, and the user judged the output insufficient;
- "fail-closed" writing guardrails were prompt-level only; there was no draft checker, and the demonstration report itself put 30 unverified citations into the body;
- 0.8.0's removal of GO/HOLD/KILL labels was incomplete (a decision summary still said “做/等/放弃”; go/no-go wording remained);
- the clarification protocol supplied default resources (24GB, 2 weeks) that contradicted `SKILL.md`'s prohibition on inventing GPU/time constraints, and venue-rule precedence was ambiguous;
- the report template encouraged filling every section for any research type, producing form-complete but evidence-empty reports;
- README install instructions and checksum examples still pointed at v0.5.0 while the current version was 0.8.0;
- self-evolution proved only file/record consistency, not scientific improvement, and could be over-read as “self-improvement”.

## Decision

1. **Add `check-draft`** (`runtime/research_mentor/draft.py`, `scripts/research_draft.py`): a deterministic structural checker for report tiers, citation keys, verified/unverified status, user-facing labels, planned material in result/abstract sections, and remaining `TODO(需来源)`. It is explicitly not a truth checker.
2. **Add report tiers** to `templates/report.md` and the checker: `concept_memo`, `evidence_review`, `preregistration`, `research_plan`. A concept memo must carry a visible “概念备忘录 / 引用未核验” banner; non-concept tiers must use verified reference entries. Add research-type variants (empirical, theory, measurement, dataset, reproduction) and instruct deleting inapplicable sections rather than filling them.
3. **Remove invented defaults and fix label remnants**: clarification asks 2–3 blocking questions, resources stay unknown unless the user supplies them; remove the 24GB/2-week default; make venue rules never defaulted; replace “做/等/放弃” and go/no-go wording with “继续/停止判据”.
4. **Trim `SKILL.md` CLI detail**: keep the evidence workflow pointer and the human-decision rule; move command flags and receipt mechanics to `python-core.md`.
5. **Rename and bound self-evolution**: describe it as prompt/template change audit, not self-improvement; it proves record/structure consistency, not scientific quality. Add an explicit effect-evaluation protocol (`evaluation/effect-protocol.md`) that is **not executed** and must be run before any effect claim.
6. **Fix version delivery**: update README install instructions, checksum examples and current-release statements; add a version-consistency test that checks the install block names the current version, not just the top line.
7. **Downgrade the demonstration report** to a `concept_memo`, with a visible unverified banner, no GO/HOLD/KILL labels, and a recorded `check-draft` result. It must not be presented as an evidence review or a validated plan.

## Alternatives

- Only rewrite prompts/README without a checker: cheap, but leaves the central “fail-closed” claim as rhetoric. Rejected.
- Make `check-draft` a semantic reviewer: needs a model, is not deterministic, and cannot prove citation support; keep it structural and say so. Rejected as a false guarantee.
- Remove report tiers and keep one template: keeps the form-filling failure mode. Rejected.
- Execute the full effect study now: requires external raters and real tasks that are not available in this session; pretending to run it would repeat the original problem. Keep it as a protocol and do not claim results. Rejected as premature.

## Rationale

The reviews are right that mechanism beats prose. A deterministic checker cannot prove research quality, but it can stop the specific failures the skill claims to prevent (unverified citations in the body, labels, plans written as observations) and it can be tested. Tiers let the skill deliver less when evidence is weak instead of filling a template. Removing invented defaults and stale versions removes direct user harm.

## Consequences

- Drafts now need a `report-tier` marker and, above concept-memo, verified reference entries; a draft without them fails `check-draft`.
- The demo report is explicitly a concept memo with warnings; it no longer serves as evidence that the skill produces publishable reports.
- Effect claims remain unproven. The README and skill must say so; the effect protocol is a plan, not a result.
- Version 0.9.0 changes prompt/reference/template behavior and adds a shipped script; package size and installed copy change.
- Self-evolution is renamed in user-facing docs and bounded; internal `KEEP/HOLD/REJECT` terms remain for the audit tool.
