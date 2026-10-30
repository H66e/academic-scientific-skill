# Effect pilot — pre-registration pack

> **NOT EXECUTED — no effect evidence.**
>
> This folder contains a pre-registered plan and review instruments only. No model evaluation has been run for this pilot, no task provider or blind reviewer has been recruited, and no result exists. Do not cite this folder, its tests, or the repository's CI as evidence that the skill improves research decisions.

| Item | State |
| --- | --- |
| Protocol | [effect-protocol.md](../effect-protocol.md) v2 (pre-registration) |
| Frozen baseline | v0.14.0, commit `efc6a0f`, package SHA-256 `21db3bca…` |
| Task bank | `EP-TB-01` candidate: 12 tasks, 5 non-author provider slots, 4 known duplicates; **unbound** |
| Execution | **Not started** |
| Results | **None** |
| Pack date | 2026-10-30 |

---

## 1. Purpose

The pilot asks one bounded question: **on 12–24 frozen tasks, with the same model and tools, does the full `ai-research-mentor` skill produce better nearest-work judgments and more actionable recommendations than a bare model, without increasing fabricated or unsupported citations, at acceptable cost?**

It is a screening pilot to decide whether a larger study is worth running. It is not a benchmark, not a product-effectiveness claim, and not a substitute for peer review. The detailed claim boundary and stopping rules are in the [protocol](../effect-protocol.md).

This pack contains the runnable *instruments*: the task bank, three neutral arm prompts, a blind review form, a de-formatting script, a manifest example, and this runbook. It deliberately contains no results file.

---

## 2. Frozen baseline

The treatment is the v0.14.0 skill package as released at:

| Field | Frozen value |
| --- | --- |
| Version | `0.14.0` (`VERSION` at the frozen commit) |
| Commit (short) | `efc6a0f` |
| Commit (full) | `efc6a0f9fbc20e83f4fe17a515653b0760613673` |
| Package | `dist/ai-research-mentor.zip` built at `efc6a0f` (build product, not committed; not the artifact of a later docs branch) |
| Package size | 809,089 bytes, 58 files |
| Package SHA-256 | `21db3bca28ee4b27c086e69092f8444d8c653df864269fd29281c06c291a7195` |
| Task-bank file SHA-256 | `841ffa362b79a6568c94afdb5bd9078b34f97e4cc28cc4d5d23f458b27c87b86` |
| Gold-bank commitment | `ceabe71b1da3944d05ad9c1aa02ebf0fe3800feb205a04b3f7360213a884ac47` |

**Working-tree note.** This pack may be committed on a later documentation branch (for example, the 0.14.1 docs patch). That does not change the treatment. The pilot must use a clean worktree at tag `v0.14.0` / commit `efc6a0f`, not the later docs tree:

```powershell
git worktree add ..\effect-pilot-v0140 v0.14.0
cd ..\effect-pilot-v0140
git status --porcelain
# must be empty

python -B evaluation/skill_tools.py package
Get-FileHash dist/ai-research-mentor.zip -Algorithm SHA256
# must print 21DB3BCA28EE4B27C086E69092F8444D8C653DF864269FD29281C06C291A7195
```

A fresh clone checked out at the tag is equivalent. Keep the pilot instruments from the pack tree, but give arm A only the v0.14.0 skill/package. A package built from a later commit has a different hash and is not the frozen baseline; do not use it.

Verify before and after the run:

```powershell
# in the clean v0.14.0 worktree
git rev-parse HEAD
# must print efc6a0f9fbc20e83f4fe17a515653b0760613673

git status --porcelain
# must be empty; the skill tree is unchanged

python -B evaluation/skill_tools.py check-package
Get-FileHash dist/ai-research-mentor.zip -Algorithm SHA256
# must print 21DB3BCA28EE4B27C086E69092F8444D8C653DF864269FD29281C06C291A7195
```

`dist/` is ignored; if the package is missing, build it from the frozen commit. A hash mismatch means the baseline is not the frozen baseline: stop and do not run. `check-package` run in a later docs tree verifies that tree's package, not the pilot's baseline.

`run-python-tests.py` and `check-python-only` are repository-integrity checks. Passing them is **not** effect evidence.

---

## 3. Required human roles

No role may be filled by a fabricated identity. Identities, affiliations, and conflict-of-interest declarations stay in the local pilot register, not in this repository.

| Role | Minimum | May be an author? | Duties and restrictions |
| --- | --- | --- | --- |
| Pilot lead / operator | 1 | Yes, but cannot score | Holds the freeze, runs sessions, captures manifests, verifies hashes, enforces no-content-help. Does not alter tasks, prompts, or gold after sealing. |
| Task providers | **4 distinct non-author humans** (5 slots planned) | **No** | Real domain experts who confirm that each task reflects a real decision, check the gold record and duplicate flag, and do not see outputs or scores. A provider may not review a task they provided. |
| Blind reviewers | **2 independent non-author reviewers per artifact** | **No** | Score de-formatted artifacts independently, without arm knowledge, discussion, or author input. Submit the form before unblinding. |
| Arbiter | **1 non-author arbiter** | **No** | Resolves reviewer disagreements using the de-formatted artifact and both locked forms, without arm knowledge. The arbiter's decision and rationale are recorded. |
| Author(s) of the skill | — | **Excluded from scoring** | May design or operate only with disclosed conflict of interest; may not be a provider, reviewer, or arbiter, and may not change tasks or gold after the first run. |
| Data steward (optional) | 1 | Yes | Holds the blind map and gold keys separately from the reviewers and operator; may be the pilot lead if access is logged. |

The task bank currently names **provider slots `TP-01`–`TP-05`**, not people. They are reservation IDs for real, distinct, non-author experts. The pilot cannot start until at least four are bound in the local register.

---

## 4. Run order

Follow the steps in order. Each step has a stop condition; do not skip a failed check.

### Step 0 — Verify the freeze

- In the clean v0.14.0 worktree, confirm the commit, clean skill tree, package size/hash, and section 2 baseline values.
- In the pack tree, confirm the task-bank file SHA-256 and gold-bank commitment. Run `python -B evaluation/run-python-tests.py` (including `test_effect_pilot.py`) and `python -B evaluation/skill_tools.py check-python-only`; record the output. These are integrity checks, not results.
- Record the verification output in the local run log.

**Stop if:** the baseline commit or package hash differs, the skill tree has unreviewed changes, the docs-tree package is being used as the baseline, or a check fails.

### Step 1 — Bind roles and declare conflicts

- Recruit at least four distinct non-author providers, at least two non-author reviewers, and one non-author arbiter.
- Collect conflict-of-interest declarations in the local register. The skill's authors may not score.
- Assign local pseudonymous IDs (`TP-01`, `RV-01`, `AR-01`, `OP-01`). Do not put names in the repository.

**Stop if:** fewer than four providers or fewer than two reviewers can be bound independently.

### Step 2 — Seal the task bank

- Providers read their prompts and confirm that each one describes a real decision. Replace any rejected task **before** sealing; a replacement changes the bank version, the task-bank SHA-256, and the gold-bank commitment, so update the frozen record and re-freeze before the first run. Never silently use a different bank.
- Verify every gold title and identifier resolves to the intended public source. Recompute the per-task hashes and the gold-bank commitment.
- Record the task-bank file SHA-256 and mark the bank `EP-TB-01-FROZEN` in the local log.
- Lock the full gold key in the local key store. Reviewers receive only the per-task scoring key in the blind form.

**Stop if:** fewer than 12 complete tasks, fewer than four distinct non-author providers, a gold record does not resolve, or any field remains a placeholder.

### Step 3 — Freeze the environment

- Record the model provider, model name, version/snapshot, decoding settings, tool versions, retrieval provider/index, run date window, and caps.
- Render the three arm prompts with the same task fields, caps, and neutral output paths. The only differences are the materials provided: full skill (A), no method material (B), or report template only (C).
- Verify that no prompt contains an arm label, hypothesis, gold title, or evaluation hint.
- Run one dry run on a **synthetic task not in the bank** to test logs, manifests, and de-formatting. Do not score it or add it to the analysis.

**Stop if:** the same task fields cannot be rendered identically across arms, or the dry run cannot produce a complete manifest/log/hash set.

### Step 4 — Run the three arms

- Pre-generate the arm order per task with a recorded random seed; use a separate fresh session for each run and do not reuse context across arms.
- Run all arms for a task on the same day/window, with the same model snapshot and tools. Keep the same frozen model/tool configuration across the whole bank; any drift stops the pilot.
- The operator may not help with content or clarify the task. If the model asks, it must state an assumption and continue.
- On an infrastructure failure only, retry once with the same configuration and model; log the retry. Do not retry because the content is weak.
- Immediately capture the raw output, request log, manifest, token usage, timestamps, and SHA-256 hashes.

**Stop if:** the model/tool version drifts, a run has no output/log/manifest, or the operator has to intervene on content.

### Step 5 — De-format and blind

- Run the de-formatting script on every raw artifact:

```powershell
python -B evaluation/effect-pilot/strip_artifact.py <raw-output.md> --out <blind-artifact.md>
```

- Verify the blind artifact contains no `nearest-set-json` or `provisional-json` block/fence, no HTML comments, no `report-tier` marker, no `[C#]` claim ID, and no arm/model/operator label.
- Assign a random blind ID, store the map in the local key store, and remove arm-specific file names and metadata from what reviewers see.
- If a machine block or arm cue survives, treat it as a **blinding breach**: stop, do not score, and log it.

### Step 6 — Blind review

- Calibrate reviewers on two synthetic artifacts not from the pilot. If agreement on the primary binary is below kappa 0.6, recalibrate before scoring the pilot; do not change the form anchors.
- Two reviewers score each artifact independently, using [blind-review-form.md](blind-review-form.md). They may not discuss scores before both forms are locked.
- The analyst locks both forms, then sends only disagreements to the arbiter. The arbiter sees the de-formatted artifact and both forms, not the arm.
- Record confidence, notes, and the exact evidence quotation for the primary metric.

**Stop if:** any artifact has fewer than two independent pre-arbitration reviews, an author scored, or a reviewer knows the arm.

### Step 7 — Analyze and apply the stopping rules

- Verify every output/log/manifest hash before analysis.
- Unblind only after all review forms are locked. Compute the metrics in the [protocol](../effect-protocol.md): sealed-gold recall, fabricated-citation count/rate, unsupported-citation count among five sampled claims, and actionability components/overall.
- Report paired task-level descriptive statistics and confidence intervals; report mixed and null results. Do not use a composite score or a favorable subgroup.
- Apply the pre-registered stopping rules. A stop is a finding, not a failure to hide.

**Stop if:** any pre-registered stopping rule fires. Do not patch the skill or prompts and continue.

### Step 8 — Report, decide, archive

- Write an internal report containing every pre-specified outcome, the stopping-rule check, inter-rater results, all deviations, and the raw artifact inventory.
- State the claim boundary explicitly: this pilot cannot establish general effectiveness. A favorable signal can justify a larger study; it is not an effectiveness claim.
- If a skill or protocol defect is found, open a new version and re-measure under a new pilot ID. Do not reuse the old outputs.
- Archive per section 5. Publish only anonymized aggregate summaries with consent.

---

## 5. Artifact and log storage

Keep all run material **outside this repository**, for example:

```text
%USERPROFILE%\effect-pilot-runs\EP-PILOT-2026-01\
  config\                 frozen task bank, arm prompts, model/tool record
  runs\<task>\<arm>\<run-id>\
    output.raw.md
    request.log.jsonl
    manifest.json
    hashes.txt
  blind\<blind-id>\       de-formatted artifacts and locked review forms
  keys\                   blind map and sealed gold keys (access-controlled)
  analysis\               code, seeds, tables, stopping-rule checks
  admin\                  COI declarations, consent, defects, decision log
```

Rules:

- **Raw outputs and request logs are sensitive.** They may contain provider material, unpublished ideas, query text, URLs, and timestamps. Do not commit them, attach them to public issues, or upload them to a public service.
- **Hash everything.** Every raw output, request log, manifest, blind artifact, review form, and analysis table gets a SHA-256 recorded in the manifest or a `hashes.txt`. Verify hashes before review and before analysis.
- **Separate keys from scores.** The blind map and gold keys live in `keys/`; reviewers see only the blind artifact and the per-task scoring key. Do not put the arm mapping in a filename, header, or metadata field.
- **No publishing private material.** Publish only anonymized aggregate counts/tables with provider and reviewer consent. Do not publish raw artifacts, request logs, task prompts with private content, reviewer identities, provider identities, or gold keys.
- **Retention.** Retain the run material for at least 24 months after the decision report, or longer if a provider/reviewer consent requires it. Destroy it according to the local data policy after that.
- **The repository stays clean.** Do not rely on `.gitignore`; keep run material outside the tree. `git status --porcelain` must show only the frozen pack (and later, no uncommitted run material).

The example manifest in [run-manifest.example.json](run-manifest.example.json) shows the minimum per-run record.

---

## 6. Freeze and no-tuning rule

- **No skill changes during the pilot.** The treatment is the frozen v0.14.0 package. A post-freeze skill commit is a different treatment; do not mix it into the run.
- **No changes to the task bank, gold, arm prompts, caps, tool envelope, review form, de-format script, or analysis plan after the first scored run.** A change requires a new bank/protocol version and a new pilot ID.
- **No prompt tuning, task cherry-picking, or selective re-runs.** Infrastructure retries are allowed once and logged; content-driven retries are not.
- **Defects go to a new version.** Log the defect, stop if a stopping rule applies, fix it in a new version (new commit/tag), and re-measure. Do not patch mid-run and continue.
- **No post-unblinding changes** to metrics, stopping rules, or exclusions. Report all pre-specified outcomes, including null and mixed results.
- **Author separation.** Authors may not score, and may not change the task/gold/prompt after the first run. Any author involvement in design or operation is disclosed in the report.

---

## 7. File index

| Path | Role | Execution state |
| --- | --- | --- |
| [README.md](README.md) | This runbook and index | Not executed |
| [task-template.md](task-template.md) | Frozen per-task metadata schema and 12-task candidate bank; 5 provider slots; 4 known duplicates; sealed gold hashes | Candidate; providers unbound |
| [arms/skill.md](arms/skill.md) | Arm A prompt: full skill package | Ready for dry run |
| [arms/bare.md](arms/bare.md) | Arm B prompt: bare model with the same retrieval tools | Ready for dry run |
| [arms/template.md](arms/template.md) | Arm C prompt: bare model with the same report template, no skill guidance | Ready for dry run |
| [blind-review-form.md](blind-review-form.md) | De-formatted blind review form, anchors, two reviewers plus arbiter, inter-rater section | Ready for calibration |
| [run-manifest.example.json](run-manifest.example.json) | Example per-run manifest (illustrative values only; not a real run) | Example |
| [strip_artifact.py](strip_artifact.py) | Standard-library de-formatting script used before blind review | Tested |
| [../effect-protocol.md](../effect-protocol.md) | v2 protocol: claim boundary, design, metrics, stopping rules, non-claims | Pre-registered |
| [../tests/test_effect_pilot.py](../tests/test_effect_pilot.py) | Unit tests for the de-formatting script | Tested |

There is no results file in this folder. A completed pilot adds a local report outside the repository; only an anonymized aggregate summary may be added later if the protocol and consent allow it.

---

## 8. Pre-run checklist

- [ ] Baseline commit, package hash, task-bank hash, and gold-bank commitment verified.
- [ ] At least four distinct non-author providers bound; authors excluded.
- [ ] At least two non-author reviewers and one non-author arbiter bound; COI declarations recorded.
- [ ] All 12 tasks provider-confirmed; gold identifiers resolve; hashes recomputed; bank marked frozen.
- [ ] Model, tools, caps, and date window frozen; all three arm prompts rendered identically.
- [ ] Dry run on a synthetic non-bank task completed; manifest, log, and hash pipeline verified.
- [ ] De-formatting script run on the dry-run artifact; no machine blocks, claim IDs, tier markers, or arm cues.
- [ ] Review form, sampling rule, analysis code, and stopping-rule checks frozen.
- [ ] Local storage tree and access controls ready; no run material inside the repository.
- [ ] Team has read the [protocol](../effect-protocol.md) and accepts the no-effectiveness-claim boundary.

If any item cannot be checked, the pilot does not start.
