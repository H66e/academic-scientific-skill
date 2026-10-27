# ADR 0013: Answer the three decision questions without GO/HOLD/KILL labels

## Context

Earlier versions summarized a research decision with a `GO`, `HOLD` or `KILL` label, and the 0.7.0 report workflow inherited a "decision summary" section that used `HOLD`/`GO` language. A user reviewing a real report objected that the label compresses the argument and biases the human: a reader sees `HOLD` and stops at the label instead of weighing whether the direction is worth doing, how it differs from the nearest work, and whether it can be validated under the real constraints. The label also invites treating a machine recommendation as the decision.

The runtime still needs typed states. `python-credibility-v5`, the dossier contracts, `assess`, ranking and human-decision binding use `GO`, `HOLD` and `KILL` as recorded machine statuses, and removing them would be a contract change unrelated to the reported problem.

## Decision

- User-facing reports, decision cards and chat answers answer three questions instead of emitting a label:
  1. Is this problem worth researching?
  2. What is the difference from the nearest work, at the level of mechanism, conditions or testable predictions?
  3. Under the real time, compute, data and evaluation constraints, can a meaningful validation be done now?
- They then give the decisive evidence and strongest counterargument, the unknowns, the next executable step (information test, bounded pilot, more evidence, narrower scope) and what observation would change the judgment.
- `GO`/`HOLD`/`KILL` remain **internal ledger states** for the Python CLI, dossier contracts, ranking and human-decision binding. They are not the default report output. They may be used only when the user explicitly asks for ledger/contract fields, and must be labelled as a recorded machine state, not as the research conclusion.
- Update `SKILL.md`, `research-outputs.md`, `evaluation.md`, the report template and README to state this distinction. The report template gains a "current judgment and next step" section without labels.
- No runtime, schema, policy or decision-gate behavior changes.

## Alternatives

- Remove `GO`/`HOLD`/`KILL` from the runtime entirely: would break the ledger, dossier contracts, ranking, receipt binding and existing fixtures, and does not solve the user-facing bias. Rejected.
- Keep labels in reports: directly contradicts the user's observation that labels interfere with human judgment. Rejected.
- Replace labels with "do/wait/abandon": still a compressed verdict that can shortcut the argument. Rejected in favor of answering the three questions in plain language.
- Hide the labels but keep a decision summary table: the table still anchors the reader on a verdict; the report should carry the reasoning instead. Rejected.

## Rationale

The three questions are the actual decision content; the label is a compression that loses the evidence, the nearest-work delta and the feasibility boundary. Keeping the labels only as an internal contract preserves compatibility while making the human-facing artifact more honest and less coercive. A report that answers the three questions and states what would change the judgment is more useful than a report that says `HOLD`.

## Consequences

- Reports become more argumentative and longer in the judgment section; readers must form their own decision, which is the intended effect.
- Internal runtime documentation and tool output still use `GO`/`HOLD`/`KILL`; docs must call them machine states so the two surfaces are not confused.
- Existing frozen examples and dossier fixtures keep their labels; the change is prompt/reference/template layer only.
- The report template and skill instructions change behavior, so a version bump and prompt-level regression checks are required.
