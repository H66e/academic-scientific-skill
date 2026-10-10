# Workspace and Release Governance

This repository is the single source of truth for the project. The parent directory may contain installed copies, historical snapshots, development candidates, and evaluation artifacts; those paths are not additional source trees.

## Version state

The current released and installed version is **0.3.0**. The release baseline is the `main` branch. Individual commit hashes and the names of in-flight branches are deliberately **not** recorded anywhere in this repository's prose: `git log` and `git branch` are authoritative, while a hash or branch name written into a document goes stale on the next commit and is then read as current fact. The formal working tree may contain unreleased governance or documentation changes; the Codex installation remains the last synchronized release until an explicit promotion and sync.

The directory `.skill-development/research-v040-20261006-153948/candidate` is an unreleased development snapshot. Its `VERSION` says `0.4.0`, but that label means “candidate target”, not “published release”. It must not be described as the current version, and its checks and benchmark template must not be presented as evidence of scientific effectiveness.

The former parent-directory copy `ai-research-mentor/` was an obsolete, truncated duplicate. It was verified not to be the active Codex installation and has been removed. The Codex installation under `C:/Users/16273/.codex/skills/` is a runtime copy and is governed separately below.

## What belongs where

- Formal source, schemas, scripts, tests, documentation, and release packages belong in this Git repository.
- A Codex installation is a runtime copy. It is updated only after a release candidate is accepted and the synchronization guard confirms that the installed copy has not been changed concurrently.
- `.skill-development/` stores frozen baselines, candidates, test logs, source checks, and forward-evaluation records. These are development evidence and must retain their timestamps and provenance.
- Strict-review files are audit inputs. They may identify weaknesses in the formal checks, but they do not themselves change the data contract or release status.

## Candidate promotion rules

A candidate may be promoted only after all of the following are true:

1. It does not delete files from the formal v0.3 release baseline unless a separately reviewed migration says so.
2. Every README, CHANGELOG, and documentation link resolves inside the candidate or to an intentional external source.
3. The candidate has a matching validation report, package manifest, version, and release notes.
4. Existing v0.3 behavior, schemas, artifacts, and synchronization safeguards remain compatible or have an explicit migration path.
5. New retrieval or graph checks are reported with their actual coverage and failure boundaries; templates, null gold labels, and smoke checks are not called benchmark results.
6. The candidate is reviewed for evidence anchoring and fabricated-record resistance before any Python migration is treated as a priority release task.

The current v0.4 candidate has structural provenance and human-decision experiments, but remains unpromoted: tool-generated acquisition provenance and scientific-effectiveness evaluation are incomplete. Its results are not the validation report for this formal branch's separate Python implementation. Do not copy candidate files back into the repository.

The Python runtime is developed from the formal source tree and lives on `main`; a per-concern branch (`feat/`, `fix/`, `docs/`, `ci/`, …) exists only while a change is in review and is deleted after the merge. It retains the v0.3 Node compatibility path, adds a separate versioned local ledger, and does not change the released/installed version. Its source, tests, ADRs and [validation report](../evaluation/validation-python-core.md) are maintained in this repository; private ledgers and raw source artifacts are kept outside it. New Python ledger hashes do not replace old Node review fingerprints. The ledger's content chain cannot detect its own tail being truncated, so an external anchor file records the expected head and count; see [ADR 0003](decisions/0003-ledger-tail-anchor.md) for what that does and does not cover.

## Version and compatibility rules

- `VERSION`, README release text, CHANGELOG entries, package contents, and validation reports must agree.
- A candidate version may be used in a development directory, but the repository version remains unchanged until promotion is complete.
- v0.4 work must preserve the v0.3 JSON contracts and Node.js tools by default. Any incompatible schema or artifact change requires an explicit migration and compatibility note.
- Python-first is a migration strategy for new research-core capabilities. It is not permission to remove working Node.js behavior before an equivalent path and tests exist.

The formal Python source now also implements the existing dossier, source, output and evolution utilities natively; it does not dispatch to Node. Node tools remain actively exercised as compatibility entrypoints and differential oracles. Shared dossier fingerprints preserve their original contract, while ledger hashes and approvals remain a different protocol. Migration of the toolchain does not imply release promotion, installed synchronization, lossless ledger/dossier conversion or measured scientific effectiveness; see [ADR 0006](decisions/0006-native-python-toolchain.md).

## Responsibility boundary

The software records sources, evidence, uncertainty, and bounded recommendations. A person remains responsible for the final research decision. `GO`, `HOLD`, and `KILL` are scoped decisions under the recorded evidence and constraints; they are not claims that a project will succeed or that a research direction has scientific value in all settings.

## External data and privacy boundary

The source tools may contact public providers, but external requests are not a private channel. Queries can reveal the research direction being investigated, and request logs can preserve query text, identifiers, URLs, response hashes, and source locations. Keep project records and source artifacts local and private.

Use public, deliberately de-identified query terms and public identifiers by default. Do not send unpublished ideas, private paper text, private code, credentials, or local paths to a provider. `--offline` performs no DNS or HTTP request and saves no remotely acquired source files; Python local acquisition can still save a local source copy in the private project. Fixed-provider transport does not provide anonymity or a private network. Any future model-assisted interpretation should receive public metadata or explicitly redacted excerpts by default; private full text and code require an explicit user choice.
