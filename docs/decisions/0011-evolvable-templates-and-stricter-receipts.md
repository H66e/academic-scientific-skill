# ADR 0011: Evolvable writing templates and stricter self-evolution receipts

## Context

Version 0.5.0 added three writing templates (`templates/paper.md`, `survey.md`, `proposal.md`) with anti-fabrication guardrails: a do-not-fabricate header, `TODO(需来源)` placeholders, and a planned-vs-observed or fact/hypothesis/plan/risk separation. The self-evolution whitelist still covered only `SKILL.md` and four reference documents, so the new writing surface could not be improved through the controlled maintenance loop while every other prompt layer could. That made the template guards effectively frozen at their first draft.

Reviewing the guard also exposed two acceptance gaps:

- A candidate could change a template without any check that its guardrails survived; the required checks were only `unit_regressions`, `skill_structure` and `protected_principles`.
- A target or regression case could be marked `better` or `worse` while its baseline and candidate output files were byte-identical, so the verdict was not supported by any observable difference.

## Decision

- Extend the fixed editable whitelist with exactly the three writing templates. It remains a fixed set; a submitted suite cannot expand it. Runtime code, scripts, schemas, tests, evaluation rules and the self-improvement protocol stay protected.
- When any `templates/` file changes, the run must also carry a passing `writing_template_guardrails` check bound to the current baseline, candidate and suite hashes. The check is produced by `python -B evaluation/skill_tools.py check-templates`, which verifies the structural markers in each template and is also run in CI.
- Require an observable difference for `better` and `worse` verdicts: the baseline and candidate output artifacts for that case must have different hashes. Identical outputs force `tie` or a re-run and cannot support a KEEP.
- Keep every existing protection: one behavior hypothesis per attempt, frozen baseline/suite, independent-context receipt, no test or contract edits to pass, all cases executed (dry runs hold), hard constraints, no regression, and the tool remains read-only.

## Alternatives

- Keep templates protected: leaves the writing surface unable to learn from actual failures and contradicts the 0.5.0 decision that writing is a first-class task. Rejected.
- Make templates editable without a required guardrail check: a candidate could remove the do-not-fabricate header, the source placeholder, or the planned/observed separation while still passing the existing checks. Rejected.
- Replace the structural template check with a model review: not reproducible, not byte-bound, and impossible for the guard to inspect. Rejected.
- Allow arbitrary `better`/`worse` verdicts regardless of output: permits a receipt to claim an improvement with no observed change. Rejected.

## Rationale

The maintenance loop should be able to improve what the skill actually asks a host to write, but only with a guardrail check that makes the safety rails part of the acceptance surface. Byte-bound outputs are the smallest observable evidence that a verdict is about behavior rather than a preference; requiring them removes a cheap way to produce an unsupported KEEP without pretending to judge scientific quality.

## Consequences

- Self-evolution can now propose and retain template changes; a template change without `writing_template_guardrails` holds, and a failing guardrail check rejects.
- The new required check and the template whitelist change the frozen file set and receipt contract. Previous maintenance rounds cannot be reused; a new baseline and suite are required, consistent with the repository's rule for changed file sets.
- The structural check proves only that guardrail markers exist. It does not prove citation truth, scientific quality or that a template change improved writing; the independent review and the non-claims in the receipt still apply.
- No automation, installation sync or repository push is introduced by this decision.
