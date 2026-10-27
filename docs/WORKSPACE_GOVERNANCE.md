# Workspace and Release Governance

This repository is the single source of truth for the project. The parent directory may contain installed copies, historical snapshots, development candidates, and evaluation artifacts; those paths are not additional source trees.

## Version and release state

The current released version is **0.8.0** (tag `v0.8.0`), the scope-refocus release described in [ADR 0010](decisions/0010-scope-refocus-0.5.0.md). Version 0.7.0 (tag `v0.7.0`) is the report-workflow release; 0.6.0 (tag `v0.6.0`) is the self-evolution template release; 0.5.0 (tag `v0.5.0`) is the scope-refocus release; 0.4.0 (tag `v0.4.0`) is the first Python-only release; version 0.3.0 (tag `v0.3.0`) is the last Node implementation. The tags point at different trees and different release packages, and the same version number must never be used to describe two of them. `VERSION` is the version truth for the working tree, and `evaluation/tests/test_version_consistency.py` keeps `pyproject.toml`, `research_mentor.__version__`, the README version line and the CHANGELOG section equal to it.

The release rule is that a tag identifies the immutable commit whose package was published: `python -B evaluation/skill_tools.py package` builds the deterministic archive from that commit, `check-package` recomputes it, and the GitHub Release attaches that same build. The archive is not committed; `dist/` is ignored and CI stores the build as a run artifact. A commit that changes behavior after a tag must bump `VERSION` and record the change in `CHANGELOG.md` in the same commit; it must not extend a tag with unreleased content. See [ADR 0008](decisions/0008-release-identity-and-package-artifacts.md).

The Codex installation under the user's skills directory is a runtime copy, not a source tree. It is updated only after a release is accepted and an explicit synchronization step confirms that the installed copy was not changed concurrently. It may lag the repository, and README/governance statements about the installation describe that copy, not the working tree.

The directory `.skill-development/research-v040-20261006-153948/candidate` is an obsolete pre-release candidate. Its old `VERSION` label `0.4.0` recorded a candidate target at that time; it is not the released 0.4.0 tree and is unrelated to the 0.5.0 release. It must not be described as the current version, and its checks and benchmark template are development evidence rather than evidence of scientific effectiveness. Version 0.4.x remains the place for workflows that still need result logging.

## What belongs where

- Formal source, schemas, scripts, tests, documentation and release configuration belong in this Git repository.
- Release archives are build products, published as GitHub Release assets and CI run artifacts. They are not committed, and `dist/` is ignored.
- A Codex installation is a runtime copy, updated only by an explicit synchronization after a release.
- `.skill-development/` stores frozen baselines, candidates, test logs, source checks, and forward-evaluation records. These are development evidence and must retain their timestamps and provenance.
- Strict-review files are audit inputs. They may identify weaknesses in the formal checks, but they do not themselves change the data contract or release status.

## Candidate promotion rules

A candidate may be promoted only after all of the following are true:

1. It does not delete files from the released baseline unless a separately reviewed migration says so.
2. Every README, CHANGELOG, and documentation link resolves inside the candidate or to an intentional external source.
3. The candidate has a matching validation report, package manifest, version, and release notes.
4. Existing released behavior, schemas, artifacts, and synchronization safeguards remain compatible or have an explicit migration path.
5. New retrieval or graph checks are reported with their actual coverage and failure boundaries; templates, null gold labels, and smoke checks are not called benchmark results.
6. The candidate is reviewed for evidence anchoring and fabricated-record resistance before any acquisition change is treated as a priority release task.

## Version and compatibility rules

- `VERSION`, README release text, CHANGELOG entries, package contents, and validation reports must agree at a tagged commit.
- A release tag is immutable; further work belongs to a new version with its own CHANGELOG section.
- Preserve the dossier JSON contracts (schema 3, decision contract 3) and the documented legacy-dossier migration. Any incompatible schema or artifact change requires an explicit migration and compatibility note.
- The maintained source, tests, CI and release packaging use Python only. Superseded entrypoints were removed under [ADR 0007](decisions/0007-python-only-toolchain.md); historical checks retain their original observations and provenance.

The formal source implements dossier, source, output and evolution utilities, repository validation and packaging natively in Python. Ledger hashes and approvals remain a separate protocol from dossier fingerprints; migration of the toolchain implies neither lossless ledger/dossier conversion nor measured scientific effectiveness. The two acquisition surfaces and the payload admission rule are recorded in [ADR 0009](decisions/0009-acquisition-direction-and-payload-admission.md).

## Responsibility boundary

The software records sources, evidence, uncertainty, and bounded recommendations. A person remains responsible for the final research decision. `GO`, `HOLD`, and `KILL` are scoped decisions under the recorded evidence and constraints; they are not claims that a project will succeed or that a research direction has scientific value in all settings.

## External data and privacy boundary

The source tools may contact public providers, but external requests are not a private channel. Queries can reveal the research direction being investigated, and request logs can preserve query text, identifiers, URLs, response hashes, and source locations. Keep project records and source artifacts local and private.

Use public, deliberately de-identified query terms and public identifiers by default. Do not send unpublished ideas, private paper text, private code, credentials, or local paths to a provider. `--offline` performs no DNS or HTTP request and saves no remotely acquired source files; Python local acquisition can still save a local source copy in the private project. The outbound classification gate applies to the ledger search/fetch commands and to the standalone `search`, `verify` and `fulltext` commands; a `private` classification blocks before any network request. Fixed-provider transport does not provide anonymity or a private network. Any future model-assisted interpretation should receive public metadata or explicitly redacted excerpts by default; private full text and code require an explicit user choice.
