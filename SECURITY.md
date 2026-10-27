# Security policy

This repository is a local research-evidence tool. It runs on the user's machine,
uses the Python standard library, and stores project records in private project
directories. This policy describes the security properties the code actually
claims, what is out of scope, and how to report a problem.

## Supported versions

The current release is **0.5.0**. Security fixes are considered for the 0.5.x
line only. Version 0.4.x remains available for users who still need result
logging, but it is no longer the supported security line.

Version 0.3.0 is the last Node.js implementation and was retired under
[ADR 0007](docs/decisions/0007-python-only-toolchain.md); it is not supported.
The Codex installation directory is a runtime copy, not a source tree. A fix in
this repository does not reach an installed copy until an explicit
synchronization step runs, so a report should state whether it was reproduced
from the repository tree or from an installed copy.

## In scope

The code makes the following security-relevant claims; a defect that breaks one
of them is a security issue.

- **Ledger integrity for accidental and partial changes.** The append-only
  ledger uses a SHA-256 hash chain, a registered event vocabulary, payload
  admission for all 17 event types, and an external anchor recording the expected
  head and event count. Verification must report a torn line, edited chain,
  unregistered type, malformed payload or anchor mismatch instead of repairing,
  skipping or silently accepting it.
- **Outbound privacy boundary.** External calls are gated by
  `privacy.check_outbound` before transport. A `private` classification must
  block with zero network requests, and obvious credential forms, e-mail
  addresses and local paths must be blocked for `public`/`deidentified` material.
  The gate must be applied to the ledger `search`/`fetch`/`resolve` commands and
  to the standalone `search`/`verify`/`fulltext` commands.
- **Path and artifact handling.** Project outputs must not be written inside the
  published skill tree or an unignored Git path; source artifacts, IR files and
  receipt paths must stay inside the project even through symlinks; release
  packaging must reject traversal and unsupported paths rather than silently
  excluding them.
- **Fail-closed behavior.** Unexpected runtime failures return the standard JSON
  envelope with `ok: false` and a non-zero exit code instead of a traceback, so
  a caller can detect the failure.

The threat model and its limits are recorded in
[ADR 0009](docs/decisions/0009-acquisition-direction-and-payload-admission.md).
The privacy boundary is also summarized in
[docs/WORKSPACE_GOVERNANCE.md](docs/WORKSPACE_GOVERNANCE.md).

## Out of scope

These are known limits, not vulnerabilities:

- **Scientific correctness, novelty and research quality.** The tool records
  sources, evidence, uncertainty and bounded recommendations. It does not prove
  that a paper exists, that a quote supports a claim, that a search was complete,
  or that a GO/HOLD/KILL decision is scientifically right.
- **Provider truth.** A receipt proves what this machine observed and retained;
  it does not make Crossref, arXiv, a publisher page or any response honest.
- **Identity authentication.** `--human`, `--human-confirmed` and similar flags
  record an existing instruction; they do not authenticate who issued it. Hashes
  and flags are not signatures.
- **An owner who deliberately rewrites everything.** The chain and anchor detect
  accident, loss, partial writes and tail truncation. They do not defend against
  a person who rewrites the ledger, anchor and artifacts together.
- **Model or host behavior.** Prompt-level scientific rules, model output quality
  and host integrations are not security boundaries of this runtime.
- **The 0.3.0 Node implementation and third-party provider/GitHub
  infrastructure.** Report those to their own maintainers.

## Reporting a vulnerability

Use GitHub private vulnerability reporting: open the repository's **Security**
tab and choose **Report a vulnerability** (Security advisory), or go to
<https://github.com/H66e/academic-scientific-skill/security/advisories/new>.
If private reporting is unavailable, open a minimal public issue that asks for a
private channel and contains no exploit details, then continue there.

A useful report contains:

- the affected version or commit, and whether it is an installed copy;
- operating system and Python version;
- the exact command and inputs;
- expected and actual behavior, including the JSON envelope or exit code;
- a minimal reproduction using **synthetic** material;
- the security impact and whether any private material may have been exposed.

Do **not** include private research material, unpublished ideas, personal
data, credentials, tokens, local absolute paths, or copied real project ledgers
and source artifacts. Reproduce with synthetic data; if a leak is the issue,
describe the category without pasting the leaked content.

There is no response-time promise in this policy. This is a small
maintainer-run project without on-call staff or a paid security team. There is
**no bug bounty**. Reports are handled on a best-effort basis; coordinated
disclosure is preferred, so please allow time for a fix before publishing
details.

## Related documents

- [CONTRIBUTING.md](CONTRIBUTING.md) — contribution and review rules.
- [ADR 0009](docs/decisions/0009-acquisition-direction-and-payload-admission.md) — acquisition direction, payload admission and threat model.
- [docs/WORKSPACE_GOVERNANCE.md](docs/WORKSPACE_GOVERNANCE.md) — release and private-material boundaries.
- [skills/ai-research-mentor/references/python-core.md](skills/ai-research-mentor/references/python-core.md) — workflow behavior and honest guarantees.
