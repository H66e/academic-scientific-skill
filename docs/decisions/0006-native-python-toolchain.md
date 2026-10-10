# Native Python toolchain with retained dossier compatibility

## Context

The evidence ledger already runs on Python, but dossier audit, independent review receipts, source utilities, note outputs and controlled-maintenance checks still require Node. Users cannot finish the existing research workflow in a Python-only environment. A language migration must not silently change fingerprints, revive archived approval, invent missing metadata or lower scientific gates.

## Decision

Provide native standard-library Python implementations under the existing `runtime/research_mentor` package, with thin standalone `research_audit.py`, `research_sources.py`, `research_outputs.py` and `evolution_guard.py` adapters. Preserve the existing command responsibilities and dossier schema/decision contract 3. Provide Python repository validation and deterministic packaging through `evaluation/skill_tools.py`.

Keep Node entrypoints as an exercised compatibility path and differential oracle. Neither native runtime dispatches to the other language. Python dossier fingerprints use the ECMAScript canonical-JSON algorithm required by existing dossiers; the ledger continues to use its separate `ledger-json-v1` protocol. Do not rewrite either history or hashes to unify the formats.

The ledger `Judgment` still never authorizes experiment execution and does not import independent approvals. The native Python dossier auditor consumes actual same-process verified independent receipts for `full_validation`, preserving that separate responsibility. Receipt verification means file/contract checks and context separation, not authenticated personal identity or scientific truth.

Python source queries require public/deidentified classification before external requests. The retained Node compatibility entrypoint does not add that classification mechanism; hosts must enforce the privacy reference when using it. Fixed arXiv resource transport binds the original version and format, including redirects. Downloading a PDF remains acquisition, not extraction or reading.

## Alternatives

- Invoke Node from Python wrappers: this leaves the runtime dependency and does not constitute migration.
- Remove Node immediately: this loses a functioning compatibility path before differential checks establish equivalence.
- Replace dossier hashes with ledger hashes or import old reviews into the ledger: this breaks old contracts and manufactures currency under a different decision model.
- Add PDF/OCR or automatic experiment-log interpretation during the port: these are new capabilities with separate evidence and dependency requirements.

## Rationale

Shared native implementations keep CLI and API behavior aligned. Differential checks against maintained Node algorithms and existing fixed synthetic cases expose accidental changes in rejection, ordering, score gates, receipt binding and canonicalization. Python-only forward checks establish that operational commands work without Node. These checks demonstrate compatibility, not topic-selection quality or literature completeness.

## Consequences

Python 3.10+ and the standard library suffice for the existing research utilities and local packaging/validation. Node remains necessary only when users choose its compatibility entrypoints or run cross-language development checks. Two implementations have maintenance cost while both are actively exercised; changes to the shared dossier contract must update both and their differential cases. The release version and installed skill are unchanged until explicit promotion and synchronization. Ledger-to-dossier projection remains partial, and reverse conversion does not create trusted ledger observations.

Native JSON CLI input is explicitly bounded to 8 MiB and accepts UTF-8 BOM/stdin; this is an operational admission difference from the legacy unbounded dossier file reader, not a new scientific interpretation. Oversize input fails without truncation or mutation; callers with a separately budgeted large dataset may use the same importable audit API. Receipt reads retain their existing 1 MiB bound.
