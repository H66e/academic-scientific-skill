# Effect evaluation protocol (pre-registration draft)

Status: **NOT EXECUTED**. This file defines how to test whether the skill helps; until it is run with real tasks and independent raters, the repository must not claim that it improves research decisions or writing quality.

## Question

Does `ai-research-mentor` produce better research-decision artifacts than a bare strong model with the same tools and token budget, at acceptable cost?

## Design

- **Arms**: (A) skill loaded; (B) bare model with a neutral "help with this research decision" prompt. Same model, same tools, same token budget, same time budget.
- **Tasks**: 24 real, pre-specified tasks from at least 8 researchers, balanced across direction choice, novelty check, and report/proposal writing. At least 8 tasks should have a publicly known nearest work (a “gold” nearest); at least 4 should be deliberately weak/duplicated directions to test whether the system says “stop”.
- **Sampling**: 3 independent runs per task per arm; fixed decoding settings where the host exposes them; record model identifier, date and tool availability.
- **Blinding**: anonymize arm labels, randomize order, strip file metadata; raters do not know the hypothesis.
- **Raters**: at least 2 independent researchers per task, not authors of the skill; disagreements adjudicated by a third. Report inter-rater agreement.
- **No composite score**: the three primary metrics are analyzed separately (co-primary), with Holm correction; do not hide a regression in one metric behind a weighted average.

## Metrics (co-primary)

1. **Fabricated citation rate**, split into two separately reported rates:
   - *nonexistent*: citation does not resolve to a real source;
   - *unsupported*: source exists but does not support the attached sentence (checked against retrieved full text by a rater).
2. **Nearest-work recall**: for tasks with a known nearest work, whether the artifact identifies it and states a mechanism/condition difference.
3. **Actionability**: pre-registered 1–5 rubric on whether the next step names a concrete check, cost bound, stopping rule and what observation would change the judgment.

## Secondary

- Calibration of “未确认/待补证” claims: share that are indeed unverified, and share of verified claims that are supported.
- Time and token cost per accepted artifact; human editing time; rounds to a usable draft.
- “Stop/continue” correctness on known-weak directions.
- Whether `check-draft` changes outcomes: same artifacts with/without the checker, measured by fabricated-citation and unsupported-claim rates; report failures the checker missed.

## Decision rule

- Claim superiority only if **all three co-primary metrics** improve in the pre-registered direction and none worsens, with task-level clustered bootstrap 95% CI excluding zero after Holm correction.
- Otherwise report mixed/null/negative results; do not choose a favorable subset after seeing data.
- Sample size is a pilot (24 tasks); it cannot establish small effects. A larger study is required before general claims.

## Data and ethics

- Use only public papers or user-provided materials with permission; no private drafts or unpublished results in the evaluation set unless the provider consents.
- Store raw outputs, retrieval logs and rater forms outside the source repository; publish only anonymized summaries.
- Do not use the evaluation set to tune prompts during the run; if a defect is found, record it and fix it in a new version after the run.

## Known limitations before execution

- No external raters or task providers are currently committed; the protocol is a plan, not evidence.
- The skill's own authors cannot serve as the only raters.
- Model and tool versions drift; the protocol must record them, and re-running later is a new evaluation, not a replication of the same claim.
- The protocol cannot prove citation support automatically; it relies on rater verification.
