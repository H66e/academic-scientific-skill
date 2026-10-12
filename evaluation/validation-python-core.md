# Python evidence core validation

**2026-10-12 supersession:** the maintained source, test runners, CI and release archive now use Python only, under [ADR 0007](../docs/decisions/0007-python-only-toolchain.md). Earlier statements below about retaining active Node entrypoints or live cross-language checks describe historical stages, not current requirements. Their actual results remain unchanged. Current completion evidence is recorded in the final entry below; the installed copy has not been synchronized.

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

## 2026-10-10 effective reading and final lifecycle validation

This entry supersedes the result-stage statement that reading withdrawal remained future work. Current Python policy is `python-credibility-v4`; Node schema/decision contract stays 3 and the ledger encoding stays `ledger-json-v1`. Supplementary reading is cumulative, explicit withdrawal is irreversible, and deep/visual/duplicate-KILL consumers use one effective set. Current guides and dated ADR supersessions distinguish implemented behavior from earlier Step 1 history.

Native local checks on CPython 3.14.5 / Node 24.18.0 / Windows:

| Check | Result | Boundary |
| --- | --- | --- |
| Final Python suite | 116 passed, 0 failed | Includes 12 reading runtime tests, 12 independent reading acceptance tests, 3 reading CLI tests and the existing result/compatibility suites; Node conformance was required to run |
| Final Node suite | 199 tests; 198 passed, 1 skipped, 0 failed | Existing file-symlink host limitation; reading-only change does not change Node contract |
| Shared result conformance | 41 fixed cases and production paths still pass | Declared facts/eligibility/KILL agreement, not numerical hash equivalence |
| Full editor Schema checks | All 3 schemas self-valid; 204 actor/trust combinations and 3 examples pass | Local installed jsonschema used only for supplementary checks; no runtime dependency added |
| Skill / examples / generic validator | Passed; 44 internal links, 111 entrypoint lines, GO/GO/HOLD synthetic examples | No real-topic quality claim |
| Final archive / source bytes | Passed; 43 files, 619145 bytes; SHA-256 `7a686c70b47847df70ff983b583477c51217454378ee6f68cf7a534f8885dd1a` | Unreleased local archive; installed copy untouched |

An actual prior committed v3 implementation and the new v4 implementation were compared on identical private synthetic ledger/anchor bytes. Deep reading followed by a supplementary abstract observation changed the machine assessment from HOLD to GO; the old human decision stayed stale/pending, and recording a new decision required explicit reassessment and instruction. Independent migration tests also covered two prior GO candidates whose reviews and decisions globally expired on policy change without any ledger rewrite. Isolated policy changes preserved scientific missing reasons and source integrity.

Negative controls covered missing/wrong-type/retired/unauthorized withdrawal targets, extra payload fields, correctly hashed invalid scientific transitions, six reading-order permutations across three anchor aliases, and backdated timestamps. Retraction does not invent replacement reading. The prior narrow-reading correction fixture now uses explicit withdrawal plus a separate actual abstract observation; its HOLD expectation is retained. Identical repeated exact anchors remain usable; the result-specific ambiguous-alias guard does not reject legitimate repeat acquisitions.

Independent core review found no remaining required correction. Low-level ledger verification validates structure and chain; Judgment consumers additionally validate scientific references and transitions, and its write APIs enforce existing effective targets. All source/runtime changes, tests and private evidence retain these boundaries. PDF extraction, automatic experiment-log interpretation, fine-grained review dependencies and measured scientific usefulness remain outside this completed lifecycle scope.

Independent forward use loaded the current Skill with only an offline synthetic request and raw project artifacts, without test expectations. It appended exactly a reading withdrawal, user run invalidation and new HOLD assessment (15 to 18 events), preserving the original prefix, abstract observation and both prior result classifications. It did not invent replacement reading or a new human research decision. Chain/anchor and four acquisition receipts remained valid. The final answer correctly distinguished completed reassessment from pending human decision, identified missing result-log artifacts, and recommended actual relevant-section reading rather than adding a label. No critical workflow defect was observed; private outputs remain outside source. This bounded simulation does not measure real literature coverage, gap finding or research value.

## 2026-10-10 native Python toolchain migration

The remaining existing research utilities now have native Python implementations: dossier validation, fingerprints, weighted ranking, v1/v2 migration, actual independent receipts, source acquisition, note cards/drafts/BibTeX and read-only evolution checks. Thin standalone adapters and APIs share `runtime/research_mentor`; no runtime command launches Node. Python repository checks and stored ZIP packaging also run without Node. [ADR 0006](../docs/decisions/0006-native-python-toolchain.md) defines the compatibility boundaries.

The old Node interfaces remain actively tested compatibility oracles. Dossier schema and decision contract remain 3, ledger encoding remains `ledger-json-v1`, ledger policy remains `python-credibility-v4`, and the release/installed version remains 0.3.0. Native dossier hashes preserve the original canonical-JSON contract; they do not replace ledger hashes or transfer approvals. Independent-receipt gating now runs in the Python dossier auditor, while ledger Judgment still has no T3 event or experiment authorization.

Final local execution on Windows / CPython 3.14.5 / Node 24.18.0:

| Check | Actual result | Boundary |
| --- | --- | --- |
| Complete Python suite | 241 tests; 240 passed, 1 skipped, 0 failed | File symlink privilege unavailable; directory junction checks executed. Required Node conformance was enabled. |
| Complete retained Node suite | 199 tests; 198 passed, 1 skipped, 0 failed | Existing file-symlink host limitation; original scientific tests and examples retained. |
| Independent native/Node comparison | 11 test methods, 164 complete fixed outputs agree | Audit, gates, migration, current/forged/copied/stale receipts, metadata outputs, acquisition states, UTF-16 and numeric/whitespace edges. Additional module-specific cases and the 41 frozen lifecycle fixtures passed. |
| Python-only commands | Passed with Node absent from the command environment | Existing dossier validation/fingerprint/rank, same-call full-stage receipt consumption and tamper rejection, init, UTF-8 stdin outputs, source offline paths, read-only maintenance and repository checks. |
| Fresh-context forward use | Completed using only current Skill, request and raw synthetic inputs | Restored v2 to v3, archived old review exactly, generated gap card/BibTeX and unassessed notes draft, recorded two unexecuted offline plans; originals unchanged and full validation stayed HOLD. |
| Skill / examples / generic validator | Passed in native and compatibility checks; 44 links, 111 entrypoint lines, GO/GO/HOLD examples | Generic validator used explicit UTF-8 mode on Windows. Structural checks do not establish scientific truth. |
| Deterministic package and source-byte checks | 56 files, 864693 bytes; SHA-256 `65ad235c46221eb38f4cb5a9bfc7b6c2386d47c873da75274141d0d46a879378` | Python build checked independently by Python and Node against all source bytes plus LICENSE. No installation synchronization or release promotion. |
| Bounded actual public-source checks | 0 successful HTTP responses; 2 attempts blocked at DNS; 0 bytes and 0 paper metadata | Fixed Crossref DOI and arXiv ID, 5-second/one-request budgets. Both returned unresolved because DNS resolved to non-public addresses. No configured proxy was detected; no proxy fallback or network-setting change was attempted. This is not evidence of successful live retrieval. |

Independent review exposed and verified fixes for URL cursor escaping, ECMAScript whitespace, Windows Python 3.10 junction handling, malformed fingerprint input errors, empty ZIP path segments, retained test resources and array JSON pointers. An earlier Windows package fixture accidentally used native CRLF while expecting LF; it now writes explicitly fixed bytes. Source and fixture comparisons were not weakened to obtain passes.

Raw suites, blocked source observations and fresh forward outputs are private development evidence outside the formal repository, under `.skill-development/python-toolchain-migration-20261010/`. They are not distributed in the package. No researcher inputs, source caches, credentials or generated scientific findings were added to release source.

This completes migration of the existing toolchain, not new PDF/OCR extraction, automatic experiment-log interpretation, fine-grained ledger dependencies, lossless ledger/dossier round trips or real research-effectiveness evaluation. The configured Python Windows/Linux version matrix has not been executed locally; these results cover the versions named above. Source retrieval remains constrained by this host's network environment, and scientific selection/brainstorm/gap quality remains unmeasured.

## 2026-10-12 Python-only completion and implementation retirement

The owner requested removal of residual JavaScript, including test-only compatibility implementations. Fifteen superseded executable and test files were removed: four research/evolution scripts, four Skill test files, five repository maintenance/runners and two repository integration test files. Python implements all existing runtime and maintenance responsibilities; no Python adapter, regression test or CI job invokes Node or embeds an executable replacement-language bridge. Current README, Skill references and all four example READMEs use the native Python interfaces. [ADR 0007](../docs/decisions/0007-python-only-toolchain.md) defines the interface retirement and historical-record boundaries.

Dossier schema and decision contract remain 3, dossier canonical bytes and fingerprints remain compatible, and `ledger-json-v1` and `python-credibility-v4` are unchanged. Retiring command/import paths does not change scientific interpretation or rewrite stored research material. Script callers must switch to Python; old-contract reviews still require explicit migration and reassessment. Ledger approvals are not transferred to dossier reviews, and the ledger still does not authorize experiment execution. Old maintenance snapshots require a new baseline because the maintained file set changed.

The historical implementations actually produced the frozen responses before removal; expected values were not regenerated from the Python code under test. The fixed synthetic inputs, source commit/blob digests, response counts, complete fixture hashes and capture limitations are documented in [the fixture provenance](fixtures/README.md). Whole-byte integrity checks and response-length assertions prevent accidentally shortening coverage. The old 199 named test responsibilities were mapped to 113 existing Python test methods; all referenced methods were checked against the actual AST. That mapping is private development evidence, not a claim of identical line coverage or equivalent test counts.

Completion checks on Windows / CPython 3.14.5:

| Check | Actual result | Boundary |
| --- | --- | --- |
| Complete Python suite, executed during the 2026-10-10 implementation | 275 tests; 274 passed, 1 skipped, 0 failed | Run with only Windows system utilities in PATH and the absolute Python interpreter, with no Node available. The sole skip was existing file-symbolic-link privilege; directory-junction cases ran. The source/package hashes and frozen response hashes were confirmed again at completion. |
| Frozen historical toolchain observations | 11 groups, 164 complete responses passed | Full validation, ranking, migrations, fingerprints, receipt binding/forgery/staleness, source protocols and outputs; these are software contracts on synthetic inputs. |
| Frozen historical module observations | 14 batches, 321 complete responses passed | 245 audit, 28 source, 20 output, four evolution hashes, two file/snapshot responses and 22 maintenance decisions. Some responsibilities overlap the other fixture groups. |
| Language-neutral result lifecycle | Original 41 cases preserved and passed | Native ledger and dossier consumers agree on declared facts, explicit causal heads, invalidation, review staleness and scoped refutation; no hash-protocol equivalence is claimed. |
| Native behavioral and integration checks | Passed | Added missing legacy score/gate/fingerprint/peer-precedence cases, actual read-only evolution CLI KEEP/REJECT, source-to-output workflow, required-license omission/collision and missing Skill entrypoint checks. Production TLS certificate and hostname verification remain required. |
| Python-only boundary and packaging negative controls | Passed | Forbidden scripts and dependency manifests are rejected, including inside `build`, `.venv`, `venv` and `*.egg-info` directories; nothing that will be packaged is silently exempted. No runtime dependency or new scientific event vocabulary was added. |
| Independent offline forward use | 14 workflow commands and two help checks completed with an empty executable PATH | Actual cards, notes draft, legacy migration and receipt-aware ranking; original inputs unchanged, no invented reading, sources or approvals, and complete validation remained HOLD. Two restricted-host receipt-root failures were retained before successful authorized local retries. |
| Current example instructions, executed at completion | All eight documented commands passed with empty PATH and absolute Python | Three synthetic dossiers validate/rank as GO/GO/HOLD; note card and unreviewed draft work. This validates the interface and existing example behavior, not scientific value. |
| Skill and documentation checks | Passed: 44 internal Skill links, 111 entrypoint lines, generic Skill validator and 133 repository-local Markdown links | All 43 Python files were parsed using the Python 3.10 syntax grammar; this is not execution on Python 3.10. |
| Release archive checked against all source bytes and LICENSE | 48 files, 644330 bytes; SHA-256 `1f549e742adab0b1c9e576f0702d5fb545eeff3a09c99b9544388ab013776535` | Project package verifier and independent standard-library ZIP reading agreed on the complete file set and bytes; no JavaScript/TypeScript entries. Stored fixed-time archive behavior also matches the independently captured 479-byte historical synthetic ZIP. |
| Independent direct import from the release ZIP | Passed | Old and migrated dossier fingerprints match the actual forward records; old GO remains HOLD, reviews are preserved in history rather than manufactured, and notes drafts retain empty scientific collections. No extraction or installation mutation was performed. |

Independent review found and corrected the generated-directory packaging bypass, a stale schema tool description, legacy receipt API prose, four example command blocks and missing license/evolution CLI regression responsibilities. Source-file admission was made stricter without weakening the scientific gates. The obsolete process-specific TLS environment check existed only in the injected protocol fixture adapter; production Python HTTPS continues to create a verified TLS context and check the host name.

No new live provider or model calls were made for this retirement task. The prior two bounded real-source attempts remain failures at the DNS safety boundary (zero HTTP responses, zero bytes, zero paper metadata), not successful retrieval evidence. Existing historical validation reports, source observations and ADRs retain their original implementation names and results. The current Python Linux/Windows version matrix is configured but has not been executed locally; only the environment named above has an actual complete-suite result.

Private raw test logs, the historical test-responsibility map, forward-use outputs and current command observations remain under `.skill-development/python-only-20261010/` outside the formal source tree. Temporary executable oracle copies and one-time capture/rewrite scripts were removed after the fixtures and provenance were verified. Only justified synthetic regression resources enter Git; no private research inputs, caches, acquisition logs or generated research reports are distributed.

This completes the existing project's Python-only implementation scope. The released/installed version is still 0.3.0; source changes and the rebuilt archive do not automatically promote a release, push a repository or synchronize an installation. PDF/OCR extraction, automatic experiment-log interpretation, lossless ledger/dossier round trips, finer review dependencies and measured real-topic/brainstorm/gap effectiveness remain outside this refactor.

## 2026-10-12 Remote cleanup and portable audit regressions

The owner authorized pushing the source and deleting confirmed obsolete remote files. A fresh remote fetch found only `main`, with no extra work branches. The Python-only migration removes the fifteen obsolete JavaScript files from that branch. A separate source/artifact audit found no additional maintained files to delete: historical reports, public-paper trial inputs/outputs, ADRs and frozen fixtures retain documented purposes and provenance. The untracked local pytest cache was removed and explicitly ignored. Three absolute machine paths in the historical public call log were replaced by `<PRIVATE_RUN_ROOT>` with a publication note; JSON comparison confirmed every other original observation unchanged. Private raw source files remain outside the repository, and no history rewrite or installation synchronization occurred.

The [initial remote Python matrix](https://github.com/H66e/academic-scientific-skill/actions/runs/38259227207) provided new execution evidence: Ubuntu Python 3.12 and 3.14 passed, Ubuntu 3.10 failed on parsing an arbitrary-precision fractional timestamp, and all three Windows jobs failed on a root-contained absolute receipt path. Windows exposed the temporary root as `RUNNER~1` while canonical resolution expanded it to `runneradmin`; the initial lexical containment comparison treated those spellings as different directories. These were failures, not successful matrix coverage.

The date fix removes fractional seconds only from the whole-second parser input and normalizes an uncolonized numeric offset for Python 3.10. Latest-review ordering still compares the original fractional digits exactly, including year zero and equivalent offsets; timestamp validation and stored inputs are unchanged. The receipt fix accepts the already-checked root's original or canonical spelling at the initial lexical boundary, while retaining the original target for link checks. Parent/leaf links and reparse points, the final resolved containment check, file identity, read bounds, byte hash, complete review binding and snapshot guards remain required. No dossier, ledger or scientific policy version changed.

Local completion on Windows / CPython 3.14.5: **276 tests, 275 passed, one existing file-symbolic-link privilege skip, zero failures**, using the absolute interpreter with only Windows system utilities in PATH. The additional test includes nine exact latest-review date-order scenarios; the existing absolute-receipt test now checks both original and canonical root spellings and reports failed verification reasons. All frozen expected values remain unchanged. Independent review found no weakened scientific or filesystem gate. Native source, Skill, example, version and package checks passed. The rebuilt archive has **48 files, 646673 bytes**, SHA-256 `7266fab9cf60bc4b724d1659574d28bb067a3ce03ca608527a5b10e5d35ed063`; it supersedes the earlier archive in this report. This section records actual local verification and the initial CI failure; follow-up matrix status must be read from its actual GitHub Actions run.

Raw initial CI logs and the local complete-suite log remain private development evidence in `.skill-development/remote-hygiene-20261012/`. This push does not promote a release or establish research effectiveness.
