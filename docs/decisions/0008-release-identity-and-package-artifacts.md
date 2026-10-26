# ADR 0008: Release identity and package artifacts

## Context

Until 0.4.0 the repository had a version number but no release identity. `VERSION` said `0.3.0` while the working tree carried the complete Python-only migration; the tracked `dist/ai-research-mentor.zip` was rebuilt from current source, so it contained unreleased code while being presented as the 0.3.0 package; the Codex installation was the byte-identical 0.3.0 Node archive (23 files, no `VERSION`). The same version label therefore named two different implementations, and no tag or GitHub Release distinguished them. `check-package` compared the tracked archive to the source, which proved consistency but not release identity, and 646 KB binaries accumulated in Git history.

`README.md` and `docs/WORKSPACE_GOVERNANCE.md` encoded the old arrangement ("release and installed copy are still 0.3.0" next to a Python tree), so the prose itself was stale.

## Decision

- Version 0.4.0 is the first release of the Python-only implementation. Tag `v0.4.0` identifies the immutable commit whose package was published; tag `v0.3.0` is retroactively placed on the last Node implementation commit. The two tags are different trees and different packages.
- The release package is a build product, not source. `dist/` is ignored by Git; `python -B evaluation/skill_tools.py package` builds the deterministic archive, `check-package` recomputes a fresh build and compares it byte-for-byte with any local artifact, and CI builds and stores the archive as a run artifact. The GitHub Release attaches the build from the tagged commit.
- `VERSION` remains the truth for the tree. A commit that changes behavior after a tag must bump `VERSION` and add its CHANGELOG section in the same commit; a tag is not extended with unreleased content.
- The Codex installation under the user's skills directory is a runtime copy, synchronized only by an explicit post-release action; it may lag and is never described as the source.
- README, CONTRIBUTING and governance prose describe this flow and no longer claim that a release/install lags the source version.

## Alternatives

- Keep committing the archive: preserves offline download from the tree, but keeps the release identity ambiguous and adds an unreviewable binary to every change. Rejected; a Release asset serves the same need.
- Keep the version label and only add a tag: the tag would still cover a tree whose CHANGELOG and package describe different things. Rejected.
- Split the skill into a separate repository: would change distribution and provenance more than this release needs. Deferred.
- Publish to PyPI: the package is documented as an optional editable development install without package data; publishing would require a different packaging decision. Not adopted.

## Rationale

A version number is only meaningful if it resolves to one immutable artifact. Removing the archive from Git makes the build reproducible from the tag, lets CI attach the artifact, and removes the failure mode where source and committed package silently diverge. Keeping the install manual preserves the existing safeguard against overwriting a concurrently changed runtime copy.

## Consequences

- A user who wants a standalone archive takes it from the GitHub Release or builds it locally; a fresh clone has no `dist/` file.
- `check-package` no longer requires a tracked artifact; with a local artifact present it additionally proves build determinism.
- Historical tags and validation records keep their original hashes; they are not rewritten.
- Installation update remains a separate, manual, reviewable step; the released package and the installed copy can still differ until synchronization.
