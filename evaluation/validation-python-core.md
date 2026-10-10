# Python evidence core validation

Date: 2026-10-07. Branch: `feat/python-evidence-workflow`, based on `5f8e0ac` (the concurrent result-interpretation prompt change is retained). This is an unreleased working-tree validation record; the installed Skill and `main` remain v0.3.0.

**2026-10-09 supersession:** the branch named above was merged into `main` and deleted; the Python runtime is now released source on `main`. The sentence above described the working tree on 2026-10-07 and is preserved as written. It no longer describes the current state: the installed Codex Skill is still v0.3.0, but `main` now carries the Python core. See [ADR 0003](../docs/decisions/0003-ledger-tail-anchor.md) for the ledger anchor added on this date and [validation-v030.md](validation-v030.md) for the v0.3 line.

## Scope

The initial Python slice uses only the standard library. It provides a project-local append-only ledger, bounded arXiv/Crossref search and resolution, content-addressed source receipts, exact text anchors, explicit reading records, source identity confirmation, conservative candidate assessments, human decision/revocation records, query recheck and an initial schema-2 dossier projection. Existing Node commands remain the compatibility path for the older contract.

The Python ledger hash contract (`ledger-json-v1`) and `python-credibility-v2` judgment policy are separate from Node fingerprints and decision rules. Export is a conservative projection: it does not migrate evidence associations or approvals and cannot resurrect an old GO. Private projects, ledgers, raw sources, caches and logs remain outside the repository.

## Checks run

| Check | Result | Boundary |
|---|---:|---|
| Python workflow and contract suite, cached CPython 3.12.14 | 59 passed, 0 failed | Standard-library behavior and compatibility cases; all provider responses are synthetic except the noted smoke below |
| Python workflow and contract suite, Blender Python 3.13.9 | 59 passed, 0 failed | Second local interpreter; not a platform matrix proof |
| Existing Node regression suite | 184 passed, 1 skipped, 0 failed | The skip is the Windows symbolic-link receipt case; no symlink privilege was available |
| `check-skill` | Passed; 41 local links, 111 Skill lines | Repository metadata/reference checks, not scientific quality |
| `check-examples` | Passed | Three examples are explicitly synthetic and are not findings |
| `git diff --check` | Passed | No whitespace errors |
| Python 3.10 syntax and package-version consistency | Passed; 11 modules | `VERSION`, `pyproject.toml`, and `research_mentor.__version__` all report 0.3.0 |
| Deterministic package check | Passed after the final rebuild; 38 files, 512059 bytes, SHA-256 `c1e8c8aa7de7b10a29fbc03edc7c4f2fc5678877d352bdb16e5b9f852883dd85` | ZIP file set and bytes are checked against the Skill source |

**2026-10-09 supersession:** the release archive was rebuilt to carry the repository `LICENSE` as `ai-research-mentor/LICENSE` (MIT, ADR 0002), so the hash above describes a superseded artifact. It was rebuilt once more the same day, after the ledger-anchor change described below; only the resulting archive is recorded, because the intermediate one was never published. Archive as of this note: 39 files, 522930 bytes, SHA-256 `f6bdaf914031bdb0bc9e76315328a24f94d63be62b5378155c4379874d0423ac`, re-checked with `check-package.mjs`.

The Python suite now runs 65 tests rather than 59. `evaluation/tests/test_version_consistency.py` automates the package-version half of the `Python 3.10 syntax and package-version consistency` row above, which was a manual comparison of `VERSION`, `pyproject.toml` and `research_mentor.__version__` and would not have caught a later drift. Four further tests cover ledger tail truncation, which the content chain alone does not detect; a controlled experiment first deleted the final ledger line and confirmed the previous code reported `valid: true`, then confirmed the anchor reports `mismatch`. The 2026-10-07 measurements in this record are preserved unmodified and were not re-run.

**Anchor boundary:** the anchor file sits beside the ledger and cannot distinguish a truncated ledger from a genuinely short one, so a project whose events were already lost before the anchor existed is anchored in its damaged state without warning. `verify-ledger` reports `absent` rather than `matched` until a person runs `anchor-ledger`, which is the honest signal available; it is not proof that an adopted ledger was never truncated.

The final package was extracted to a temporary directory and its thin CLI `doctor` command completed successfully; the temporary project and extracted files were removed afterward.

The Python suite includes ledger tamper/concurrency checks, privacy and credential/path blocking, offline behavior, failed-search accounting, provider replay, exact-anchor ambiguity and tamper checks, source identity, current-version claim links, stale/revoked decisions, conservative export, and slow-body/blocked-header deadline and byte-budget transport fixtures. The fixtures do not measure literature recall or research usefulness.

## Bounded external smoke

An explicit trusted official-provider transport mode resolved public arXiv `2305.13245v1` in a fake-IP environment and replayed one raw receipt successfully. The normal public-DNS path correctly rejected the environment's non-public fake address. The temporary project and source artifact were deleted after the smoke. No private idea, paper, code or local path was sent.

## What this does not establish

These checks do not establish search recall, field-wide literature coverage, novelty, faithful interpretation, scientific decision quality, or reduction of hallucination. No expert gold set, private-topic paired evaluation, or long-running calibration study has been run. PDF bytes can be acquired but are not extracted; HTML extraction is conservatively lossy and critical pages, equations, tables and figures need human review. Only one bounded provider page is queried per call. OpenAlex/Semantic Scholar/OpenReview/DBLP adapters, citation expansion, multi-page/date-window saturation, a full independent-review importer, personal library, and the experiment plan/run/classification/calibration layer remain deferred.

The result-classification section added to `SKILL.md` is a host interpretation workflow. Python does not yet register experiment plans or runs, import logs, classify outcomes, or automatically invalidate a candidate after a result. Existing result records retain separate `kind` and `outcome` axes (`smoke` is a kind).

`quick_validate.py` was not run because the available cached Python did not include PyYAML; no dependency was installed solely for that check. The repository's own metadata, schema-pointer, workflow and package checks passed. No general JSON Schema validator was run.

## 2026-10-09: Step 1 vocabulary closure and specification freeze

This is a new validation entry; the earlier measurements, policy labels and package hashes above are preserved. [ADR 0004](../docs/decisions/0004-result-lifecycle-semantics.md) freezes future result/reading lifecycle requirements. Only the existing event vocabulary is closed in this implementation; result events, reading retraction, predicate changes and Node v3 remain unimplemented. Package version 0.3.0, Python policy `python-credibility-v2` and Node contract 2 remain unchanged.

| Check | Actual result | Boundary |
| --- | --- | --- |
| Native Windows, CPython 3.14.5 | Baseline 65 passed; modified suite 68 passed, 0 failed | Three new tests cover unknown-type rejection, correctly hashed legacy events and malformed types; existing workflow tests still pass |
| Native Windows, Node.js 24.18.0 | Baseline and modified suites: 188 tests, 187 passed, 1 skipped, 0 failed | Existing Windows file-symlink receipt test skips without symlink privilege; no new skips |
| Differential supported-event check | 15 allowed type/role combinations retain identical ledger and anchor bytes; old and new verification pass | Synthetic deterministic events; not evidence of scientific judgment quality |
| Differential legacy unknown-type check | Five formerly accepted types now fail verification despite matched anchors; rejection preserves history and anchor bytes | Includes unimplemented result/reading names; no silent cleanup or migration |
| JSON Schema, installed `jsonschema` Draft 2020-12 validator | Schema self-validation passed; 168 declared type/actor/trust combinations match runtime roles; five unknown types rejected | Uses an already installed validation tool; no runtime dependency added; does not validate source truth |
| Skill Creator `quick_validate.py` | Passed using installed PyYAML and UTF-8 mode | Metadata validation only; supersedes neither earlier environment facts nor scientific limitations |
| Repository skill/example checks | Passed; 41 local links, 111 Skill lines, three synthetic examples | Synthetic examples are not research findings |
| Independent code/contract review | No required correction found | Static review of production guards, regression mechanisms and current/future documentation boundaries |
| Package/source comparison | Passed; 39 files, 528024 bytes; SHA-256 `986b35836bab3fbf1ab050599c4eb386629bab4dae562b5f679e836f0e89746a` | Rebuilt local archive matches packaged source bytes; no release or installation sync performed |

Initial sandbox runs hit interpreter/temporary-directory and Windows directory-link restrictions. Native runs completed all required checks without changing the tests to suppress those failures. Private run logs and the bounded differential probe remain outside the repository; no papers, user ledgers, request logs or caches were added to release source.

Compatibility is deliberately narrower: supported existing events retain their hashes and interpretation, while a legacy ledger containing unknown types is now rejected and needs explicit inspection/migration. Replacing old `claim.record`/`test` fixtures with supported types and asserting the intended hash, torn-line and lock errors prevents the new admission guard from making old negative tests pass for the wrong reason.

Future lifecycle tests in ADR 0004 are frozen acceptance requirements, not checks executed by this step. No result API, effective-reading predicate or policy migration is claimed as implemented, and no topic-selection, gap-discovery or scientific-effectiveness improvement has been measured.

## 2026-10-10 result lifecycle implementation

This dated record supersedes the Step 1 implementation boundary for results. Python policy `python-credibility-v3` implements classifications, causal corrections, user-only whole-run invalidations and shared effective GO/refutation-KILL state. Node schema/decision contract 3 implements the same facts, explicit legacy migration, complete result review inputs and Python result-preserving projection. Reading withdrawal remains a separate next concern in this record. See [ADR 0005](../docs/decisions/0005-policy-bound-lifecycle-rollout.md).

Native local verification used CPython 3.14.5 and Node 24.18.0 on Windows:

| Check | Result | Boundary |
| --- | --- | --- |
| Python full suite | 89 passed, 0 failed | Includes 13 result tests, 2 CLI integration tests and 6 conformance tests |
| Node full suite | 199 tests; 198 passed, 1 skipped, 0 failed | Existing host file-symlink limitation; no test weakened to hide failure |
| Independent conformance | 41 fixed synthetic cases: 18 valid, 23 invalid; 36 Python and 28 Node order permutations | Actual assess/export/rank/migrate paths; facts and gates, not hash equality |
| Skill / examples / generic validator | Passed; 44 internal links, 111 entrypoint lines, three synthetic examples | Metadata, structural compatibility and intended example gates only |
| Rebuilt archive / source bytes | Passed; 41 files, 596132 bytes; SHA-256 `184d8e748bbc9366420499e2a0cd94c3184b6074bbacad05ed17fe846dcefd1d` | Local unreleased package; no install synchronization |

Independent review caught and verified fixes for malformed locators/provenance/time fields, ambiguous Python target aliases, cross-lifecycle ID collisions, and migration that could activate previously ignored legacy invalidations. Legacy `EV-*` pilot IDs remain legal. Nonempty or malformed ignored withdrawals now require explicit investigation rather than automatic activation or silent deletion. Unresolvable explanatory claims warn and degrade without changing blockers.

Old finalized reviews and bound human decisions become stale when only the policy digest input changes; ledger and anchor bytes and event counts remain unchanged. Pure policy changes preserve the scientific missing list. Reclassification or invalidation can clear eligibility blockers but always changes review inputs; fresh human instructions are still needed after reassessment. No research effectiveness or truthful scientific interpretation was measured.
