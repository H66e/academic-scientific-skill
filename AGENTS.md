# Project Management Rules

This repository follows the project governance requirements adopted from the attached Codex Project Governance Prompt. These rules apply to every maintenance task.

## Order of priorities

Prefer correctness, scientific rigor, maintainability, testability, traceability, and extensibility in that order. Development speed never justifies fabricated evidence, weaker evaluation, duplicate implementations, or an unclear source of truth.

## Required workflow

Before editing, inspect the repository structure and relevant existing files, including `README.md`, `SKILL.md`, `CHANGELOG.md`, `VERSION`, `CONTRIBUTING.md`, `evaluation/`, and `tests/`. Search for existing or obsolete implementations and decide whether an existing file can carry the change. State the affected layer: runtime, prompt, reference, schema, script, evaluation, example, documentation, or packaging.

Use the smallest architecture change that solves one clearly scoped problem:

```text
Issue → Design → Branch → Implementation → Tests → Evaluation → Cleanup → Review → Merge → Release
```

Do not make large experimental changes directly on `main`. Use a branch named for one concern (`feat/`, `fix/`, `refactor/`, `eval/`, `docs/`, `chore/`, `build/`, or `ci/`). Use a precise commit prefix from the same set.

## Repository boundaries

- `skills/ai-research-mentor/` is the user-facing Skill and its deterministic runtime.
- `evaluation/` is for benchmark cases, runners, methodology, and regression evaluation. Generated reports and temporary run logs are not source by default.
- `examples/` contains only stable, documented examples.
- `docs/` contains architecture, methodology, roadmap, design decisions, and contributor documentation.
- `tools/` is reserved for repository-level maintenance, packaging, validation, and migration tooling; do not mix it with Skill runtime scripts.

Git stores history. Do not create `*-old`, `*-copy`, `*-backup`, `*-v2`, `*-final`, or similar versioned source files. Keep two implementations only while they are genuinely being run or evaluated side by side; merge the winner and remove the temporary implementation.

Classify files as source, generated, runtime output, or temporary. Keep user dossiers, private research material, caches, and ordinary run output outside the source repository. Preserve an evaluation artifact only when it has documented long-term value and provenance.

## Scientific and evaluation requirements

Every scientific behavior change must consider evidence, traceability, reproducibility, uncertainty, falsifiability, source quality, and methodology. Never invent papers, results, citations, reading, or source support; never present a hypothesis as a conclusion.

Important changes require structural checks, schema validation, unit tests, relevant benchmark or regression cases, real-world or bounded source checks when applicable, and comparison with the previous behavior. Fixed benchmark cases must not be edited merely to improve scores. Prompt changes are behavior changes and require the same review.

For important design decisions, create an ADR under `docs/decisions/` with Context, Decision, Alternatives, Rationale, and Consequences. Before adding a dependency, check whether the standard library or an existing dependency is sufficient and record the maintenance and packaging impact.

## Cleanup and completion report

After every task, perform a cleanup pass for duplicate implementations, obsolete files, unused code or dependencies, temporary artifacts, debug output, stale documentation, and unnecessary compatibility layers. A task is complete only when the behavior, tests, evaluation, documentation, changelog, packaging, and repository structure are consistent.

The final report must state: Summary, Added, Modified, Removed, Architecture Impact, Behavior Impact, Evaluation, Regression Risk, Remaining Issues, and Repository Hygiene.

The formal source of truth and release boundaries are documented in [docs/WORKSPACE_GOVERNANCE.md](docs/WORKSPACE_GOVERNANCE.md). Contributor commands and compatibility rules are in [CONTRIBUTING.md](CONTRIBUTING.md).
