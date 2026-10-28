# ADR 0018: Structured nearest-set and claim-ID binding

## Context

The 0.12.0 deep-read gate review found that the gate was still a shape check: the nearest table could be filled with placeholders, the A/B ledger check was dead code before projection derivation, C-only reports could not pass, and claim-table rows could be disconnected from the prose. The reviewers asked for structured nearest-selection data, claim IDs in the prose, real ledger verification, and template/checker alignment.

## Decision

- Replace the free-form nearest table with a structured `nearest-set-json` block inside the "近邻选择与深读记录" section: `created_at`, at least two distinct queries, and at least two candidates. Each candidate has id, rationale, status (`full_text`/`section`/`abstract`/`unseen`), reader (`model`/`user`), ledger binding, locator, and at least two kill questions with q/answer/locator.
- `check-draft` parses that block and rejects missing/placeholder/malformed data; a nearest set older than 180 days emits a stale warning.
- Require claim IDs in the current-judgment prose: every bullet in "当前判断与下一步" must carry `[C#]`; C-grade IDs may not appear there. A/B claims must bind a candidate ledger from the nearest set and a user/T1 section/full_text reading.
- Require C claims to appear in the "暂定判断（C 级）" section with `[C#]`, flip condition, minimal check and access path; C IDs outside that section are rejected.
- Fix the review findings: derive projections before A/B checks, strip backticks from evidence, normalize provisional headings after NFKC, allow C-only reports with a warning, fix the URL prefix slice, align template reference columns, and add tests for bad ledger IDs and C-only reports.
- Model-first reading and cache expiry remain specification-level: reader is recorded in the nearest set (model/user) but not authenticated; stale warning is structural, not a full invalidation engine.

## Alternatives

- Keep the Markdown table: rejected; placeholders and arbitrary rows passed.
- Require only claim-table presence: rejected; prose could still state a different conclusion.
- Block C-only reports: rejected; it would force authors to upgrade grades dishonestly.
- Change ledger events to store nearest sets/readers: deferred; `ledger-json-v1` is frozen.

## Consequences

- Reports need a JSON nearest-set block and `[C#]` claim IDs in prose; old reports fail.
- The checker is stricter but still structural: it cannot verify that a kill question was answered honestly, that the nearest selection is complete, or that a claim is supported.
- C-only reports are allowed with a warning; they must stay in the provisional section.
- Template and tests must stay in sync; the JSON block is the authoritative nearest record, not the prose table.
- No effect evidence is claimed; this is a discipline/mechanism improvement only.
