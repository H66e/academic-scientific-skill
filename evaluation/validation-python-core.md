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
