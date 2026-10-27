# ADR 0012: Direction-to-report workflow and clarification intake

## Context

The 0.5.0 refocus made writing a first-class task, but the shipped outputs were still short decision cards, gap cards and paper/proposal scaffolds. A real user request exposed a gap: after a researcher proposes a direction, they want a complete, discussable research report — one that formalizes the problem, locates the nearest work, states falsifiable hypotheses and criteria, designs the experiments and statistics, plans the pilot and go/no-go, and states risks and failure paths. Several ablation answers looked like competent Q&A but did not meet that bar.

The same request also showed that the skill asked too little before writing. A direction is one sentence; the goal, hard constraints, evidence status, success criteria and delivery format change the problem definition and the experiment design. Without an intake step the model either invents resources or writes a generic proposal that does not match the user's real decision.

## Decision

- Add `templates/report.md`, a full research-report scaffold with sections for input assumptions and scope, abstract, introduction, related work and nearest-work positioning, problem definition and falsifiable hypotheses with criteria, method, experiment design (data/splits, scale and cost, metrics, baselines, statistics, pilot and go/no-go), expected results and failure analysis, plan and roles, risks, conclusion and references.
- Add `references/clarification.md`, a one-round intake protocol: ask 3–5 high-leverage questions covering goal and use, hard constraints, evidence status, success criteria and risk preference, and delivery format; give defaults; restate intent in 3–5 bullets; proceed with explicit assumptions when the user asks for speed.
- Route “user proposes a direction and wants a complete report/proposal/decision report” to clarification first, then the report template. Short decision cards and simple requests keep the existing lighter path.
- Keep the fail-closed source boundary: the report may state expected contributions and plans, but must not write unexecuted experiments as observations, must not fabricate citations/numbers/results, and must mark unverified references as pending.
- Add the new reference and template to the fixed self-evolution whitelist, the skill structure check, the template-guardrail check and CI. A report-template change therefore also requires the `writing_template_guardrails` receipt.

## Alternatives

- Reuse the proposal template unchanged: it covers a proposal but not the full report decisions (nearest-work positioning table, statistics, pilot go/no-go, roles, risks), and users would keep getting incomplete reports. Rejected.
- Write a report immediately without clarification: faster, but would encode invented constraints and miss the user's real decision. Rejected.
- Ask a long questionnaire: increases burden and invites boilerplate answers; 3–5 high-leverage questions with defaults preserves momentum. Rejected.
- Let the model fill missing constraints with plausible values: violates the evidence boundary and produces confident but false reports. Rejected.

## Rationale

A report is a decision artifact, not a longer answer. Its value comes from making the decision problem explicit, separating evidence from plans, and showing what would change the conclusion. The intake step is the cheapest way to avoid a well-written report for the wrong question. Keeping both surfaces inside the existing fixed whitelist means they can improve through the controlled maintenance loop without weakening the guards.

## Consequences

- The skill can now turn a human-proposed direction into a structured research report and can ask focused clarifying questions first.
- The new template and reference change the shipped file set, package size and required checks; old package hashes and installed copies from 0.6.0 no longer describe the current tree.
- A report is still a draft for human verification. The template check verifies structural guardrails only; it does not prove citation truth, novelty, feasibility or scientific quality.
- No runtime, ledger, dossier or decision-policy behavior changes; the new surfaces are prompt/reference/template layer.
