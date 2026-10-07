# Workspace and Release Governance

This repository is the single source of truth for the project. The parent directory may contain installed copies, historical snapshots, development candidates, and evaluation artifacts; those paths are not additional source trees.

## Version state

The current released and installed version is **0.3.0**. The release baseline is the `main` branch at commit `7e3de66`. The formal working tree may contain unreleased governance or documentation changes; the Codex installation remains the last synchronized release until an explicit promotion and sync.

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

The `feat/python-evidence-workflow` branch develops the Python runtime from the formal source tree. Its baseline is `5f8e0ac`, which preserves a concurrent result-interpretation prompt change; Python changes remain a separate, uncommitted concern. It retains the v0.3 Node compatibility path, adds a separate versioned local ledger, and does not change the released/installed version. Its source, tests, ADR and [validation report](../evaluation/validation-python-core.md) are maintained in this repository; private ledgers and raw source artifacts are kept outside it. New Python ledger hashes do not replace old Node review fingerprints.

## Version and compatibility rules

- `VERSION`, README release text, CHANGELOG entries, package contents, and validation reports must agree.
- A candidate version may be used in a development directory, but the repository version remains unchanged until promotion is complete.
- v0.4 work must preserve the v0.3 JSON contracts and Node.js tools by default. Any incompatible schema or artifact change requires an explicit migration and compatibility note.
- Python-first is a migration strategy for new research-core capabilities. It is not permission to remove working Node.js behavior before an equivalent path and tests exist.

## Responsibility boundary

The software records sources, evidence, uncertainty, and bounded recommendations. A person remains responsible for the final research decision. `GO`, `HOLD`, and `KILL` are scoped decisions under the recorded evidence and constraints; they are not claims that a project will succeed or that a research direction has scientific value in all settings.

## External data and privacy boundary

The source tools may contact public providers, but external requests are not a private channel. Queries can reveal the research direction being investigated, and request logs can preserve query text, identifiers, URLs, response hashes, and source locations. Keep project records and source artifacts local and private.

Use public, deliberately de-identified query terms and public identifiers by default. Do not send unpublished ideas, private paper text, private code, credentials, or local paths to a provider. `--offline` performs no DNS or HTTP request and saves no remotely acquired source files; Python local acquisition can still save a local source copy in the private project. Fixed-provider transport does not provide anonymity or a private network. Any future model-assisted interpretation should receive public metadata or explicitly redacted excerpts by default; private full text and code require an explicit user choice.
