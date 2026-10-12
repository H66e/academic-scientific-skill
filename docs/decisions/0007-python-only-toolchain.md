# ADR 0007: Python-only maintained toolchain

## Context

[ADR 0006](0006-native-python-toolchain.md) introduced native Python equivalents while retaining a second implementation as a live differential oracle. That stage established compatibility checks and a working Python workflow. The project owner now requires the formal repository and release archive to contain no residual JavaScript implementation. Keeping duplicate entrypoints, tests, CI jobs and packaging logic would leave an unnecessary maintenance obligation after the port.

Historical evaluation observations remain evidence of what actually ran. Removing a superseded implementation must not rewrite those observations, transfer approvals, alter the dossier fingerprint contract or turn a prior dual-runtime check into a claimed Python-only check.

## Decision

- Maintain one standard-library Python 3.10+ implementation under `skills/ai-research-mentor/runtime/research_mentor/`, shared by thin CLI adapters and importable APIs. Repository validation, test discovery, CI and deterministic ZIP packaging also use Python.
- Remove superseded language source, its test runners, entrypoints and CI dependencies. Do not retain subprocess bridges, embedded replacement-language programs or a second installed compatibility implementation.
- Preserve existing frozen input/output observations with their provenance as regression data; execute current tests against native Python. Supplement fixed observations with direct behavioral, safety, mutation, migration and packaging checks rather than deriving expected answers from the implementation under test.
- Add `python -B evaluation/skill_tools.py check-python-only` as a maintenance and CI check. It rejects JavaScript/TypeScript source and obsolete manifests or dependency directories. Skill structure and package source collection reject unsupported source rather than silently omitting it from the archive.
- Keep dossier `schema_version=3`, `decision_contract_version=3`, canonical-JSON byte spelling and fingerprints unchanged. UTF-16 key ordering and the existing floating-point spelling are data-contract requirements implemented in Python, not a runtime dependency. Continue reading v1/v2 through the documented explicit migration and reassessment path.
- Keep `ledger-json-v1` and `python-credibility-v4` unchanged. Dossier fingerprints and ledger hashes remain separate protocols; the ledger does not acquire independent-review trust or execution authority from this refactor.
- Retire old command and import interfaces. Callers must switch to the Python adapters or `research_mentor` APIs. CLI flags and native source privacy rules remain documented in the current references; a source query must explicitly be public or deidentified before an external request.
- Do not rewrite research data, historic ledgers, review records or source artifacts merely to retire code. Old contract reviews still require explicit migration and reassessment; old maintenance snapshots and receipts must be replaced with a new frozen baseline because the maintained file set has changed.
- Retain ADR 0001–0006, prior validation reports and release history as historical records with a retirement note. This decision supersedes their continuing dual-runtime obligation, not their past observations. The released and installed version remains 0.3.0 until explicit promotion and synchronization.

## Alternatives

- Keep the second runtime only for tests: this still leaves residual source and CI dependencies and conflicts with the owner’s requested boundary.
- Delete the previous tests and retain only the newly ported happy paths: this discards important invalid-input, stale-review, receipt, privacy, lifecycle and packaging regression coverage.
- Rewrite canonical JSON to use default Python serialization: this changes established fingerprints and can make existing review bindings appear stale despite unchanged scientific input.
- Call the old programs from Python wrappers or ship them only in the archive: this keeps the dependency and duplicate implementation while making their location less visible.
- Rewrite historical reports into Python-only reports: this misstates which implementation was observed and destroys traceability.

## Rationale

One implementation makes scientific gates, receipt binding, source safety and release packaging easier to review consistently. Frozen observations preserve independent migration evidence without requiring the superseded runtime at execution time. Direct native regressions exercise the transitions and failures that observations alone cannot prove. Structural rejection prevents the removed language from quietly returning through future source or package changes.

## Consequences

Users and CI need only Python for the maintained toolchain. Existing script/import callers must change their invocation, but stored dossier and ledger data need no language-driven rewrite. Historical reports may still name the removed tools because they record real past executions; Git remains the source for the old implementation. Changes to fingerprints, judgment interpretation or receipt contracts still require their own reviewed migration and policy/contract decisions.

The deterministic archive changes when source files are removed; this is an intentional file-set change, not a promise to reproduce the earlier archive hash. Current archive checks compare the complete current source set, file bytes and license. Installed copies are not modified automatically. PDF extraction, experiment-log interpretation, lossless ledger/dossier conversion and measured topic-selection quality remain outside this refactor.
