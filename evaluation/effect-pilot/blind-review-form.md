# Blind artifact review form (de-formatted)

**Form version:** `EP-BRF-01` for pilot protocol v2.
**Use:** one form per reviewer per artifact. Each artifact is scored independently by **two non-author reviewers**; disagreements go to a **third non-author arbiter**.

> Read the task prompt and the sealed gold key before reading the artifact. Score only what the de-formatted artifact says. Do not try to identify the preparation that produced it, do not search for the arm mapping, and do not discuss scores with the other reviewer before both forms are locked. The authors of the method under study may not review.

**Reviewer instructions**

1. Check the de-formatting integrity box in section 1. If it fails, stop and report a blinding breach; do not score.
2. Read the sealed gold key in section 2, then the artifact.
3. Score M1 first and quote the decisive sentence. Then score S1–S3. Do not revise M1 after seeing S2/S3.
4. Use `0` or `1` exactly; do not use half points. For M1 there is no N/A: an incomplete or unreadable artifact scores `0`.
5. Confidence is about how certain you are of your score, not about whether you like the conclusion.
6. Lock and submit the form before the analyst unblinds the run. Do not edit after locking.

---

## 1. Review and artifact identifiers

| Field | Value |
| --- | --- |
| Review ID | `R-______` |
| Artifact blind ID | `A-______` |
| Task ID | `EP-____` |
| Reviewer ID | `RV-____` |
| Review date | `YYYY-MM-DD` |
| Review role | `reviewer` / `arbiter` |
| Review round | `1` (independent) / `2` (arbiter) |

**De-formatting integrity check** (all must be checked):

- [ ] The artifact contains no `nearest-set-json` or `provisional-json` block and no fence for either.
- [ ] The artifact contains no HTML comment (`<!-- ... -->`).
- [ ] The artifact contains no `report-tier` marker.
- [ ] The artifact contains no `[C#]`-style claim ID.
- [ ] The artifact contains no arm, condition, model, operator, or file-path label.
- [ ] The task prompt and sealed gold key are present below.
- [ ] I have not seen the arm map, the raw output, or another reviewer's scores.

If any box is unchecked, **stop**: record the item and notify the operator. A surviving machine block, claim ID, or arm cue is a blinding breach, not a scoring problem.

---

## 2. Task and sealed gold key (operator-filled before review)

**Task type:** `direction_choice` / `novelty_check` / `evidence_review` / `proposal_draft`

**Task prompt (verbatim):**

```text
[operator inserts the frozen prompt]
```

**Sealed gold nearest work**

| Field | Value |
| --- | --- |
| Gold ID | `G-EP-____` |
| Title | [exact title] |
| Identifier | [DOI / arXiv / URL] |
| Common name / method label | [e.g. LoRA, GQA, Chinchilla; copy the name used in the expected outcome] |
| Why decisive | [operator inserts the frozen reason] |
| Known duplicate? | `yes` / `no` |
| Expected acceptable outcome | [operator inserts the frozen expected outcome] |

Reviewer confirmation: [ ] I read the gold key before scoring the artifact.

---

## 3. M1 — Primary metric: sealed-gold nearest recall (binary)

**Definition.** `M1 = 1` only if the artifact (a) identifies the sealed gold work by an unambiguous title, the model/method name given in the gold key, or a bibliographic identifier, and (b) gives the pre-registered correct difference judgment:

- **Non-duplicate task:** states a specific mechanism or condition difference that is consistent with the sealed gold key. A generic "related work" mention, a difference that the gold key says is absent, or a difference with no condition is `0`.
- **Known-duplicate task:** states that the proposed mechanism is already covered and that no material mechanism difference remains; a recommendation to stop or narrow is expected. Claiming novelty where the gold already covers the mechanism is `0`.

Naming a different, merely adjacent work is `0`. Naming the gold but giving no difference/equivalence statement is `0`. If the artifact is incomplete, unreadable, or the relevant section is missing, score `0`.

**Score:**

- [ ] `M1 = 0`
- [ ] `M1 = 1`

| Audit field | Value |
| --- | --- |
| Gold named? | `yes` / `no` |
| Decisive quotation | "[quote the sentence that names the gold and states the difference/equivalence]" |
| Difference/equivalence stated? | `yes` / `no` |
| Reason for `0` (if applicable) | [specific missing or incorrect element] |

---

## 4. S1 — Secondary: fabricated citations (script-checkable count)

**Definition.** A citation is **fabricated** when the cited work does not exist: its identifier (DOI/arXiv/URL) does not resolve, and an exact title/author/year search finds no matching source. A real work cited for a claim it does not support is **not** fabricated; it is S2 unsupported. An identifier typo is not fabricated if the title/author/year identifies the real work; record it as an identifier error.

**Procedure.** Use the artifact's reference table as the machine-readable source. Extract every distinct cited work and its identifier. Resolve each identifier; if it fails, check the exact title/author/year. Attach the extraction/resolution output or record the command and date. Inspect every distinct cited work, not a sample. The analyst's extraction/resolution script and output are retained with the analysis; this form records the result.

| # | Citation as written | Identifier | Resolution | Fabricated? | Note |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  | resolved / failed / not-checkable | yes / no |  |
| 2 |  |  |  |  |  |
| 3 |  |  |  |  |  |
| … |  |  |  |  |  |

**Counts:**

| Field | Value |
| --- | --- |
| Total distinct cited works | `____` |
| Fabricated citations | `____` |
| Fabricated rate | `____ / ____` (write `NA` if total = 0) |
| Any fabricated citation? | `yes` / `no` |
| Citation extraction/resolution record attached? | `yes` / `no` |

Do not count private or user-provided sources as fabricated; mark them `out of scope` and report them separately. The pilot's frozen tasks allow public sources only.

---

## 5. S2 — Secondary: unsupported citations among 5 sampled claims

**Sampling rule.** The analyst pre-selects 5 claims with citations using a recorded seed and the artifact's blind ID; if the artifact has fewer than 5, use all of them. **Do not choose the claims yourself.** Use the sample IDs provided below.

**Sample record (operator-filled):** seed `________`; sampled claim IDs `________`; denominator `____`.

**Definitions.**

- **Supported (`S`):** the cited source, as available, supports the claim as stated.
- **Unsupported (`U`):** the source exists but does not support the claim as stated (including a source that supports only a weaker or different claim).
- **Unverifiable (`V`):** the source exists but no accessible text is available to check support. Report separately; do not count as unsupported.
- **Fabricated (`F`):** the source does not exist. Count it here for completeness and also count it in S1.

| # | Claim (quote) | Cited source | Verdict | Load-bearing? | Evidence / locator |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  | S / U / V / F | yes / no |  |
| 2 |  |  | S / U / V / F | yes / no |  |
| 3 |  |  | S / U / V / F | yes / no |  |
| 4 |  |  | S / U / V / F | yes / no |  |
| 5 |  |  | S / U / V / F | yes / no |  |

**Counts:**

| Field | Value |
| --- | --- |
| Unsupported count | `____` |
| Denominator (5, or fewer if the artifact has fewer) | `____` |
| Unsupported rate | `____ / ____` |
| Unverifiable count | `____` |
| Load-bearing unsupported count | `____` |
| Severe finding? (see protocol: fabricated or load-bearing/contradicted citation) | `yes` / `no` / `not assessable` |

A **load-bearing** claim is one the recommendation, GO/HOLD/KILL label, or "next step" depends on. A minor unsupported citation is still counted; severity is recorded separately.

---

## 6. S3 — Secondary: actionability (four binary components)

Score the artifact's recommended next step, not whether the task prompt asked for these components. Each component is `0` or `1`; **overall actionability = 1 only if all four are 1**.

| Component | `1` anchor | `0` anchor | Score |
| --- | --- | --- | --- |
| **A1. Concrete action** | Names a specific check, read, query, or experiment and its object (for example, "read P1 §3.2 and Table 2" or "run a 200-example test on corpus X"). | "Do more research", "explore further", or a direction with no object. | `0` / `1` |
| **A2. Cost boundary** | States a time, token, money, or opportunity-cost bound for the next step (for example, "at most 2 hours / 5k tokens / $0"). | No bound, or only "soon" / "cheap". | `0` / `1` |
| **A3. Stop condition** | States when to stop, abandon, or not continue (for example, "stop if P1 §3 shows the same mechanism"). | No stopping condition, or only "if it doesn't work". | `0` / `1` |
| **A4. Observation that would change the judgment** | Names a specific observation or result that would flip the recommendation (for example, "if P1 reports the same action set at equal cost, abandon the difference claim"). | Generic "if results differ", "if new evidence appears", or no observation. | `0` / `1` |

| Field | Value |
| --- | --- |
| A1 | `0` / `1` |
| A2 | `0` / `1` |
| A3 | `0` / `1` |
| A4 | `0` / `1` |
| **Overall actionability** | `0` / `1` (1 iff A1 = A2 = A3 = A4 = 1) |
| Decisive quotation | "[quote the next-step paragraph]" |

If the artifact has no next-step paragraph, score all four components `0`.

---

## 7. Confidence

Circle one overall confidence: `1` / `2` / `3` / `4` / `5`

| Score | Anchor |
| --- | --- |
| `1` | Guess; the artifact or gold key is too unclear to judge. |
| `2` | Low; important evidence is missing or ambiguous. |
| `3` | Moderate; the main judgment is clear but some details are uncertain. |
| `4` | High; the evidence is clear and the anchors fit. |
| `5` | Certain; the artifact directly matches one anchor and the gold key is unambiguous. |

Optional per-metric confidence (same scale): M1 `___`; S2 `___`; S3 `___`.

Confidence is not a prediction of whether the hypothesis is true. Do not reward or punish an artifact for agreeing with your prior.

---

## 8. Reviewer notes

Use this space for exact quotations, ambiguities in the gold key, missing sections, and any reason a score could be contested. Do not speculate about the preparation or arm.

```text
[notes]
```

---

## 9. Reviewer attestation

- [ ] I reviewed the de-formatted artifact independently.
- [ ] I did not know the arm/condition mapping when I scored.
- [ ] I am not an author of the method under study and have no conflict of interest beyond the declared one.
- [ ] I did not discuss scores with the other reviewer before locking this form.
- [ ] I did not use private material or contact the task provider about the artifact.
- [ ] The scores above are my own and are based only on the artifact, task prompt, and sealed gold key.

Reviewer local ID: `RV-____`  Date: `YYYY-MM-DD`  Signature/hash: `________`

---

## 10. Arbiter section (only if the two independent reviews disagree)

The analyst sends the de-formatted artifact and both locked forms to the arbiter. The arbiter does not see the arm mapping, the raw outputs, or the operator's notes.

| Field | Value |
| --- | --- |
| Arbiter ID | `AR-____` |
| Date | `YYYY-MM-DD` |
| Artifact blind ID | `A-______` |
| Disagreement items | M1 / S1 count / S2 verdict(s) / S3 component(s) |

**Arbiter decision**

| Item | Reviewer 1 | Reviewer 2 | Arbiter score | Final | Rationale |
| --- | --- | --- | --- | --- | --- |
| M1 | `0/1` | `0/1` | `0/1` | `0/1` |  |
| S1 fabricated count | `__` | `__` | `__` | `__` |  |
| S2 unsupported count | `__` | `__` | `__` | `__` |  |
| S3 A1–A4 | `____` | `____` | `____` | `____` |  |
| S3 overall | `0/1` | `0/1` | `0/1` | `0/1` |  |

**Finalization rule (pre-registered):** for M1 and each S3 component, the arbiter's independent score is final if the two reviewers disagree. For S1 and S2 counts, the arbiter re-checks each disputed citation/claim; the final count is the arbiter's adjudicated count after applying the same definitions. The arbiter does not see the reviewers' arm guesses (none should exist). Record every change from the reviewer scores.

- [ ] I re-read the artifact and the sealed gold key before deciding.
- [ ] I did not know the arm/condition mapping.
- [ ] I applied the same anchors and definitions as the reviewers.

Arbiter local ID: `AR-____`  Date: `YYYY-MM-DD`

---

## 11. Inter-rater reporting (analysis use only)

Complete after both independent forms are locked and after arbitration. Do not change reviewer scores; report them as submitted.

| Field | Value |
| --- | --- |
| Artifacts with two independent reviews | `____` |
| Artifacts sent to arbitration | `____` |
| Reviewers | `RV-__`, `RV-__`, `RV-__` |
| M1 raw agreement | `____%` |
| M1 Cohen's kappa | `____` |
| M1 prevalence (positive) | `____%` |
| M1 PABAK (if prevalence < 10% or > 90%) | `____` |
| S3 overall raw agreement / kappa | `____%` / `____` |
| S3 component agreement (A1–A4) | `____%`, `____%`, `____%`, `____%` |
| S1 exact agreement / ICC(2,1) or mean difference | `____` |
| S2 unsupported-count agreement / ICC(2,1) or mean difference | `____` |
| Reviewer confidence distribution | `____` |

**Disagreement log:** list every disagreement, the arbiter's final decision, and whether it changed the primary result.

```text
[list]
```

**Interpretation guardrails**

- Report raw agreement and kappa together; kappa is unstable with small N and extreme prevalence. PABAK is descriptive only.
- If M1 kappa is below `0.4`, treat the primary result as **inconclusive** and say so; do not re-score artifacts to force agreement.
- Do not average away a disagreement without recording it. Do not use reviewer confidence to weight scores.
- Do not unblind or compare arms until every form in this section is locked.

Analyst ID: `AN-____`  Date: `YYYY-MM-DD`
