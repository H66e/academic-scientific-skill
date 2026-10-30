# Effect evaluation protocol v2 (pre-registration)

> **NOT EXECUTED — no effect evidence.**
>
> This is a pre-registered plan. No model evaluation has been run for this protocol, no task provider or independent reviewer has been recruited, and no result exists. Passing repository tests, CI, or API review scores is not evidence that the skill improves research decisions.

**Status:** protocol v2, 2026-10-30. It supersedes the earlier draft. Executable materials, the task bank, arm prompts, blind form, manifest example, and de-formatting script are in [effect-pilot/](effect-pilot/README.md).

---

## 1. Claim boundary

The pilot asks a narrow question: **on a frozen set of 12–24 real research-decision tasks, with the same model, tools, time, and day, does the full v0.14.0 skill produce better sealed-gold nearest-work judgments and more actionable recommendations than a bare model, without increasing fabricated or unsupported citations, at acceptable cost?**

What the pilot can support:

- A paired, descriptive estimate on these tasks with this model and tool configuration.
- A decision about whether a larger, better-powered study is worth running.
- Safety signals from the citation checks, even when the effect estimates are null.

What the pilot cannot support:

- General effectiveness, general superiority, or a claim that the skill "works".
- A claim that the skill improves scientific quality, publication outcomes, or research decisions outside these tasks.
- A claim that the sealed gold set is exhaustive or that a missed nearest work does not exist.
- A claim that sampled citation checks establish the truth of all citations.

Even a favorable pilot result is a **signal for a larger study**, not an effectiveness claim.

---

## 2. Frozen baseline

| Field | Frozen value |
| --- | --- |
| Version | `0.14.0` (frozen commit) |
| Commit | `efc6a0f9fbc20e83f4fe17a515653b0760613673` (`efc6a0f`) |
| Package | `dist/ai-research-mentor.zip` built from that commit |
| Package SHA-256 | `21db3bca28ee4b27c086e69092f8444d8c653df864269fd29281c06c291a7195` |
| Task-bank file SHA-256 | `841ffa362b79a6568c94afdb5bd9078b34f97e4cc28cc4d5d23f458b27c87b86` |
| Gold-bank commitment | `ceabe71b1da3944d05ad9c1aa02ebf0fe3800feb205a04b3f7360213a884ac47` |

The package and commit are verified before the first run and after the last. A mismatch, a dirty skill tree, or an unreviewed post-freeze skill commit means the treatment is not the frozen baseline; stop and do not run.

The repository may contain a later documentation patch that carries this pack; that does not change the treatment. Build and verify the package from a clean worktree at tag `v0.14.0` / commit `efc6a0f`. A package built from a later commit has a different hash and is not the frozen baseline. Keep the pilot instruments from the pack tree, but give arm A only the v0.14.0 skill/package.

---

## 3. Design

### 3.1 Arms

All arms use the same model, model snapshot, retrieval tools, tool permissions, caps, task prompt, output requirements, and run window. Only the provided method material differs.

| Arm | Material | Neutral prompt |
| --- | --- | --- |
| A — full skill | The complete `ai-research-mentor` v0.14.0 package, including its instructions and templates | [arms/skill.md](effect-pilot/arms/skill.md) |
| B — bare | No method package and no report template; the model's own judgment with the same retrieval tools | [arms/bare.md](effect-pilot/arms/bare.md) |
| C — template only | The same report template as the skill, but no skill guidance or runtime instructions | [arms/template.md](effect-pilot/arms/template.md) |

C controls for the report format: if A beats B but not C, the gain may come from formatting rather than the skill's method. The B and C prompts must not be weakened, padded with extra warnings, or given fewer tools; the only intended difference is the material listed above.

### 3.2 Tasks and providers

- **12–24 tasks**, frozen before the first run. The current candidate bank has 12; it may be expanded only before sealing.
- **At least 4 distinct non-author task providers.** The current bank plans 5 provider slots. Providers confirm that each task reflects a real decision, check the gold record and duplicate flag, and do not see outputs or scores. A provider may not review a task they provided.
- At least some tasks are **known duplicates** of existing work (the current bank has 4 of 12). These test whether the artifact identifies the nearest work and recommends stopping or narrowing instead of claiming novelty.
- Every task has a **sealed gold nearest work** (ID, title/identifier, why decisive, sealed SHA-256) and a pre-registered **expected acceptable outcome**. The full task schema is in [task-template.md](effect-pilot/task-template.md).
- Task prompts contain no gold title, no arm label, and no evaluation hint. The current pilot is English-language; a Chinese-language replication is a separate pre-registration.
- The task bank becomes `EP-TB-01-FROZEN` only after provider confirmation and hash locking. After the first scored run, no task, gold, cap, or prompt changes.

### 3.3 Runs

- **One scored run per task per arm.** This is a pilot; it does not estimate decoding variance. A larger study should add repeated runs.
- All runs for a task use the same model snapshot, tools, caps, and day/window. The full bank should be completed in one contiguous run window; if it must span days, the model/tool snapshot and configuration remain identical, and any drift stops the pilot. Arm order is randomized with a recorded seed; each run uses a fresh session and no cross-arm context.
- Fixed decoding settings are recorded where the host exposes them. If the host does not expose them, record that fact; do not pretend they were fixed.
- The operator may not help with content, clarify the task, or retry because an output is weak. An infrastructure failure may be retried once with the same configuration; the retry is logged.
- Missing output, request log, manifest, or hash for any task/arm is a logistics stop, not a missing-data convenience.

### 3.4 Blinding and review

- Raw artifacts are de-formatted with [strip_artifact.py](effect-pilot/strip_artifact.py) before review. The script removes `nearest-set-json`/`provisional-json` blocks and fences, HTML comments, `report-tier` markers, and `[C#]` claim IDs. It preserves prose, case, language, ordinary code fences, and citation markers such as `[1]`.
- Blind IDs replace arm/task/file identifiers. The blind map and gold keys are held separately from reviewers.
- **At least two independent non-author reviewers per artifact**, plus a **third non-author arbiter** for disagreements. The authors of the skill are excluded from scoring. Reviewers do not know the arm and do not discuss scores before both forms are locked.
- Reviewers use [blind-review-form.md](effect-pilot/blind-review-form.md). They see the de-formatted artifact, the task prompt, and the sealed gold key — not the raw output, arm map, or operator notes.
- Inter-rater reporting: raw agreement and Cohen's kappa for binary metrics; exact agreement and ICC(2,1) (or a reported mean difference) for counts. If M1 kappa is below 0.4, the primary result is reported as inconclusive; do not re-score to force agreement.

---

## 4. Metrics

Four outcomes are pre-specified and reported. The form uses "primary" for M1 and "secondary" for S1–S3; the protocol keeps that hierarchy.

| ID | Outcome | Role | Definition |
| --- | --- | --- | --- |
| **M1** | Sealed-gold nearest recall (binary) | **Co-primary (1 of the allowed maximum 3)** | `1` iff the artifact identifies the sealed gold work (by title, the model/method name given in the gold key, or a bibliographic identifier) and gives the pre-registered correct judgment: a specific mechanism/condition difference for a non-duplicate task, or an explicit "already covered / no material difference" plus stop-or-narrow for a known-duplicate task. `0` otherwise; no N/A. |
| **S1** | Fabricated-citation count/rate | Secondary / safety | Distinct cited works that cannot be resolved to a real source. Rate = fabricated / total distinct cited works; `NA` if total = 0. The reference table is the machine-readable source; the extraction and resolution record is retained. |
| **S2** | Unsupported citations among 5 sampled claims | Secondary / safety | Of 5 pre-sampled cited claims (all if fewer), the count whose source exists but does not support the claim as stated; rate = unsupported / sampled denominator. `Unverifiable` is reported separately and is not counted as unsupported. |
| **S3** | Actionability (binary) | Secondary | `1` iff all four components are present: concrete action, cost boundary, stop condition, and an observation that would change the judgment. Components are recorded separately. |

**Why only one co-primary?** A 12–24 task pilot cannot support three or four simultaneous superiority claims. M1 is the effect the pilot is designed to screen; S1–S3 remain mandatory safety/secondary outcomes and feed the stopping rules. This deliberately uses one of the allowed maximum of three co-primary outcomes. A larger pre-registered study may promote actionability and citation safety to co-primary.

**No composite score.** Do not average M1, S1, S2, and S3 into a single "quality" number, and do not hide a safety regression behind an effect gain.

---

## 5. Analysis

- **Unit of analysis:** the task, paired across arms. Report per-arm and per-task descriptive statistics first: counts, proportions, medians, interquartile ranges, and exact numerators/denominators.
- **Binary outcomes (M1, S3 overall, any-fabricated):** paired McNemar exact test; report discordant pairs, risk difference, and a task-level bootstrap 95% CI (10,000 resamples, recorded seed). With 12–24 tasks, treat p-values as descriptive, not as proof.
- **Counts/rates (S1, S2):** report paired mean and median differences with task-level bootstrap 95% CIs; report the exact count and denominator for every arm. Do not impute zero for missing or unverifiable data.
- **Comparisons:** A vs B is the primary contrast; A vs C is the format-control contrast; B vs C is context only. Report all three.
- **Multiplicity:** one co-primary means no multiplicity correction for M1. S1–S3 are secondary/safety and are labeled exploratory; if a later version designates 2–3 co-primary, apply Holm correction to that pre-registered family.
- **Mixed and null results are allowed and must be reported.** Do not select a favorable subset, change the metric after unblinding, or run unregistered subgroup analyses. No "success" claim if one outcome improves and another worsens.
- **Cost:** wall-clock from logs plus token/tool cost at a price table fixed at run start. Report median cost per artifact and the A/B and A/C ratios; report cost per successful M1 artifact. Cost is not a substitute for quality.
- **Inter-rater:** compute agreement on locked pre-arbitration scores; use the arbiter's final score for the analysis. Report kappa/ICC and the disagreement log. Low agreement is a finding, not a reason to re-score.

---

## 6. Pre-registered stopping rules

A stop means **stop the pilot/analysis and do not patch it into a continuing run**. Record the rule, the evidence, and the artifacts; if the issue is fixable, create a new version and re-measure under a new pilot ID. The old outputs are not reused.

| Rule | Trigger | When checked |
| --- | --- | --- |
| **STOP-1 — no recall gain** | Arm A's M1 recall is not greater than **both** B and C on the paired task set (A ≤ B or A ≤ C by point estimate), or A is worse than either. | After unblinding |
| **STOP-2 — cost >3× with no metric gain** | Median cost per artifact for A is more than 3× the lower-cost control, **and** A has no favorable point estimate on any of M1, S1, S2, or S3 relative to both controls. If cost is >3× but a gain exists, report cost-effectiveness and apply the progression criteria; do not automatically stop. | After unblinding |
| **STOP-3 — severe unsupported-citation finding** | Any fabricated citation in arm A; or any **load-bearing** unsupported or contradicted citation in arm A (a claim the recommendation, GO/HOLD/KILL label, or next step depends on); or a finding that the citation audit itself is unreliable. Stop immediately and audit. Fabricated/unsupported citations in B or C are recorded; if they reveal a task or gold defect, treat as STOP-4. | During review or analysis |
| **STOP-4 — task/reviewer logistics fail** | Fewer than 12 valid tasks or fewer than 4 distinct non-author providers; any task missing an arm, output, request log, manifest, or hash; any de-formatting or blinding breach; fewer than 2 independent pre-arbitration reviews for any artifact; an author scored; model/tool version drift within the run window; a post-freeze task/gold/prompt edit; provider withdrawal below 4. | Any time |

If none of the stopping rules fires, the pilot may report a **progression signal** only if A's M1 recall is higher than both B and C and no safety outcome shows a clear harm signal. That signal justifies planning a larger study; it does not justify an effectiveness claim.

---

## 7. Freeze and no-tuning rule

- No skill changes, prompt changes, task edits, gold edits, cap changes, tool changes, model switches, or review-form changes during the pilot. The treatment is the frozen v0.14.0 package.
- No prompt tuning, task cherry-picking, selective re-runs, or post-unblinding metric changes. Infrastructure retries are allowed once and logged; content-driven retries are not.
- Defects are recorded in the local defect log. A defect that could affect validity triggers the relevant stop rule; fix it in a new version, then run a new pilot ID. Do not patch mid-run and continue.
- The author(s) may not score and may not change tasks, gold, or prompts after the first run. Any author involvement in design or operation is disclosed.
- The task-bank file SHA-256, gold-bank commitment, package hash, model snapshot, tool versions, and analysis plan are recorded before the first run and checked after the last.

---

## 8. Artifacts to retain

Keep run material outside the repository, access-controlled, and hashed. Retain for at least 24 months after the decision report or longer if consent requires it.

- **Freeze record:** commit, package SHA-256, model name/version/snapshot, decoding settings, tool versions, retrieval provider/index, arm prompts, task bank, gold key, caps, review form, de-format script, analysis plan.
- **Per run:** raw output, request log, manifest, stdout/stderr, token usage, timestamps, output SHA-256, request-log SHA-256, operator ID, retry record.
- **Blind material:** de-formatted artifacts, blind map, both reviewer forms, arbiter form, inter-rater tables.
- **Analysis:** code/notebook, sample seeds, summary tables, stopping-rule checks, all deviations, the decision report.
- **Administration:** conflict-of-interest declarations, provider/reviewer consent, defect log, decision log.

Publish only anonymized aggregate summaries with consent. Do not publish raw outputs, request logs, task prompts containing private material, reviewer/provider identities, blind maps, or gold keys.

---

## 9. Explicit non-claims

- This protocol and pack are **not executed**; they provide **no effect evidence**.
- A completed pilot is **not** a benchmark, a product endorsement, or proof of scientific quality.
- The pilot does **not** establish general effectiveness, superiority, or reproducibility across models, tools, dates, languages, or domains.
- The pilot does **not** establish that the sealed gold set is exhaustive, that a missed nearest work does not exist, or that sampled citation checks prove all citations are supported.
- The pilot does **not** establish that a favorable recommendation leads to a successful research project, publication, or grant.
- Passing repository tests, CI, packaging checks, or API reviews is **not** effect evidence and must never be reported as such.
- The author(s) may design and operate the pilot, but are excluded from scoring; their involvement is a limitation, not a substitute for independent review.

---

## 10. Execution materials

Start with the [pilot README](effect-pilot/README.md). It contains the frozen baseline verification, required roles, step-by-step run order, storage rules, freeze rule, file index, and pre-run checklist. The task bank, three arm prompts, blind review form, manifest example, and de-formatting script are linked there.

If the pilot cannot satisfy the role, sealing, blinding, or logging requirements, it must not run. A smaller valid pilot is preferable to a larger invalid one; a null or mixed result is preferable to an unregistered claim.
