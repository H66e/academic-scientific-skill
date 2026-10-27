# Effect evaluation protocol (pre-registration draft)

Status: **NOT EXECUTED**. This file defines how to test whether the skill helps; until it is run with real tasks and independent raters, the repository must not claim that it improves research decisions or writing quality.

## Question

Does `ai-research-mentor` produce better research-decision artifacts than a bare strong model with the same tools and token budget, at acceptable cost?

## Design

- **Arms**: (A) skill loaded; (B) bare model with a neutral "help with this research decision" prompt. Same model, same tools, same token budget, same time budget.
- **Tasks**: 24 real, pre-specified tasks from at least 8 researchers, balanced across direction choice, novelty check, and report/proposal writing. At least 8 tasks should have a publicly known nearest work (a “gold” nearest) to measure novel-work recall; at least 4 should be deliberately weak/duplicated directions to test whether the system says “stop”.
- **Sampling**: 3 independent runs per task per arm; fixed decoding settings where the host exposes them; record model identifier, date and tool availability.
- **Blinding**: anonymize arm labels, randomize order, strip file metadata; raters do not know the hypothesis.
- **Raters**: at least 2 independent researchers per task, not authors of the skill; disagreements adjudicated by a third. Report inter-rater agreement.

## Metrics (primary)

1. **Fabricated citation rate**: share of inline citations that do not exist or do not support the attached claim, checked against retrieved full text by a rater.
2. **Nearest-work recall**: for tasks with a known nearest work, whether the artifact identifies it and states a mechanism/condition difference.
3. **Actionability**: pre-registered 1–5 rubric on whether the next step names a concrete check, cost bound, stopping rule and what observation would change the judgment.
4. **Calibration of confidence**: share of claims marked “未确认/待补证” that are indeed unverified, and share of verified claims that are supported.

## Secondary

- Time and token cost per accepted artifact; human editing time; number of rounds to a usable draft.
- “Stop/continue” correctness on known-weak directions (avoiding false GO and false KILL).
- Failure taxonomy: invented number, invented citation, overclaim, plan-as-result, missing nearest, unusable next step.

## Analysis and decision rule

- Pre-register the primary comparison: skill vs bare model on a composite of fabricated-citation rate (lower is better), nearest recall (higher), actionability (higher), with task-level clustering bootstrap 95% CI.
- Do **not** claim superiority if any primary metric fails to improve or if fabrication/overclaim increases.
- Report negative and mixed results; a null result is a valid outcome and should change the README claims, not be hidden.
- Sample size is a pilot (24 tasks); it cannot establish small effects. A larger study is required before general claims.

## Data and ethics

- Use only public papers or user-provided materials with permission; no private drafts or unpublished results in the evaluation set unless the provider consents.
- Store raw outputs, retrieval logs and rater forms outside the source repository; publish only anonymized summaries.
- Do not use the evaluation set to tune prompts during the run; if a defect is found, record it and fix it in a new version after the run.

## Known limitations before execution

- No external raters or task providers are currently committed; the protocol is a plan, not evidence.
- The skill's own authors cannot serve as the only raters.
- Model and tool versions drift; the protocol must record them, and re-running later is a new evaluation, not a replication of the same claim.
