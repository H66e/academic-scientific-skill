# Effect-pilot task bank and per-task metadata template

> **NOT EXECUTED — no effect evidence.** This file is a pre-registration artifact. No task provider has been recruited, no task has been answered, and no result exists.

**Status:** candidate task bank `EP-TB-01` for protocol v2, created 2026-10-30. The per-task field schema is frozen; the 12 task seeds below are the pre-registered minimum matrix. Provider slots `TP-01`–`TP-05` are **unbound**. The bank becomes sealed only after at least four distinct non-author providers confirm their tasks and the local gold key is locked. No run may start from an unsealed bank.

**Scope:** 12 tasks, 5 non-author provider slots (minimum 4), 4 known-duplicate tasks, 4 task types. This is a pilot matrix, not a benchmark, and not evidence of effectiveness.

---

## 1. Frozen per-task field schema

Every task record must contain all of the following fields. A record with a missing or placeholder field fails the sealing check.

| Field | Required content | Validation rule |
| --- | --- | --- |
| `task_id` | Stable ID such as `EP-01` | Unique; immutable after sealing |
| `provider_id_expertise` | Pseudonymous provider ID plus domain expertise | Must bind to a real non-author human in the local register; no names in this repository |
| `task_type` | `direction_choice`, `novelty_check`, `evidence_review`, or `proposal_draft` | One value only |
| `user_prompt` | Verbatim prompt given to the model | Same text in every arm; no gold title, arm label, or evaluation hint |
| `constraints_resources` | Data access, language, output, interaction rule | Public sources only; no private material; no operator clarification |
| `allowed_tools` | Tool envelope available to the model | Identical across arms; arm materials differ, permissions do not |
| `caps` | Wall-clock, output-token, and retrieval-call limits | Identical across arms for the task |
| `gold.id` | Sealed gold ID | `G-EP-NN`, unique |
| `gold.title` | Nearest work title | Exact published title |
| `gold.identifier` | DOI/arXiv/URL identifier | Resolvable public identifier |
| `gold.why_decisive` | Why this work is the nearest decisive comparison | Specific mechanism/condition, not a generic "related work" note |
| `gold.sealed_sha256` | Integrity commitment to the gold identity | 64 lowercase hex characters; rule in section 2 |
| `known_duplicate` | `yes` or `no` | Pre-registered before any run; `yes` means the proposed mechanism is already covered |
| `expected_acceptable_outcome` | What a correct artifact must establish | Written before any run; no post-hoc gold changes |
| `notes` | Provider-confirmation and scoring cautions | Operator-only; never shown to the model |

**Common tool envelope (all tasks, all arms):** public web search; public URL fetch; local file read/write; local Python sandbox whose network egress is limited to the provided retrieval tools. No private or unpublished material, no external model calls, no access to the evaluation directory, task bank, gold keys, or another arm's materials.

**Common caps (all tasks, all arms):** 30 minutes wall-clock; 5,000 output tokens; 12 retrieval calls. The model must stop at a cap and submit what it has.

**Common deliverable rule:** one self-contained Markdown artifact in English; no operator interaction (state assumptions instead); end with a recommended next step, a cost/time bound, a stop condition, and the observation that would change the judgment; include a reference table with an identifier for every cited work.

**Language:** frozen to English for this pilot. A Chinese-language replication is a separate pre-registration; it is not pooled with this one.

---

## 2. Sealed-gold hash rule

The identity commitment for each gold record is:

```text
canonical = UTF-8 JSON object with exactly the keys id, title, identifier;
            keys sorted; separators "," and ":"; no trailing newline
sealed_sha256 = SHA-256(canonical) as 64 lowercase hex characters
```

The hash fixes the gold work's identity. The `why_decisive` and `expected_acceptable_outcome` text is fixed by the SHA-256 of this file recorded in [README.md](README.md) before the first run. The full gold key (including reviewer-specific notes and any additional evidence locators) is held in the local key store, outside the repository; the summary fields above are operator material and must not be shown to the model or to blind reviewers except through the scoring form.

The titles and identifiers were checked against public arXiv records on 2026-10-30. Re-check them against the publisher record before sealing; a metadata change requires a new bank version and a recomputed hash.

**Gold-bank commitment:** `sha256("\n".join(sorted canonical gold records by task_id))` = `ceabe71b1da3944d05ad9c1aa02ebf0fe3800feb205a04b3f7360213a884ac47`.

If any gold title or identifier is edited, the per-task hash and this bank commitment must both be recomputed before sealing. After the first scored run, no recomputation is allowed.

---

## 3. Bank summary

| Task | Type | Provider slot | Known duplicate | Sealed gold |
| --- | --- | --- | --- | --- |
| EP-01 | `direction_choice` | TP-01 NLP evaluation | yes | G-EP-01 LoRA |
| EP-02 | `novelty_check` | TP-01 NLP evaluation | yes | G-EP-02 GQA |
| EP-03 | `direction_choice` | TP-02 ML systems | no | G-EP-03 Chinchilla |
| EP-04 | `novelty_check` | TP-02 ML systems | yes | G-EP-04 FlashAttention |
| EP-05 | `direction_choice` | TP-05 human-AI interaction | no | G-EP-05 Chain-of-Thought |
| EP-06 | `evidence_review` | TP-03 retrieval/evidence | no | G-EP-06 RAG |
| EP-07 | `proposal_draft` | TP-04 biomedical NLP | no | G-EP-07 PubMedQA |
| EP-08 | `proposal_draft` | TP-04 biomedical NLP | no | G-EP-08 DPO |
| EP-09 | `evidence_review` | TP-03 retrieval/evidence | no | G-EP-09 DPR |
| EP-10 | `novelty_check` | TP-05 human-AI interaction | yes | G-EP-10 InstructGPT |
| EP-11 | `evidence_review` | TP-03 retrieval/evidence | no | G-EP-11 Lost in the Middle |
| EP-12 | `direction_choice` | TP-02 ML systems | no | G-EP-12 speculative decoding |

Task-type counts: direction choice 4, novelty check 3, evidence review 3, proposal draft 2. Provider load: TP-01 2, TP-02 3, TP-03 3, TP-04 2, TP-05 2.

**Provider slots are not people.** `TP-01`–`TP-05` are reservation IDs for real, distinct, non-author domain experts. Bind them in the local register; do not put personal names, affiliations, or contact details in this repository. At least four slots must be bound before sealing; the intended design uses five. The skill's authors may not fill a provider slot or a reviewer slot.

---

## 4. Task records

### EP-01 — Low-rank adaptation for a legal-domain model

- **Task ID:** `EP-01`
- **Provider slot / expertise:** `TP-01` — NLP evaluation (non-author; **unbound**)
- **Task type:** `direction_choice`
- **User prompt (verbatim):**

```text
I have a frozen 7B instruction-tuned language model and a small legal-domain corpus (about 30k unlabeled documents plus 2k labeled question-answer pairs). Full fine-tuning is too expensive on our hardware. I am considering adapting the model by learning low-rank updates to the attention projection matrices while keeping the base weights frozen. Before we invest, tell me whether this direction is worth pursuing, what the nearest prior work is, and what, if anything, would make it distinct from that work.
```

- **Constraints / resources:** Public literature only; do not use or reveal private corpus content. Single turn; state assumptions instead of asking. English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope (public search/fetch, local file read/write, local Python sandbox; no private data, no external model calls, no evaluation/gold access).
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-01` — "LoRA: Low-Rank Adaptation of Large Language Models" (`arXiv:2106.09685`); sealed SHA-256 `39519c4592ddcb38d563a02a315eb4343cc3002914f9cbfe03f334e138a849df`.
  - **Why decisive:** Proposes low-rank updates to frozen pretrained weights as the adaptation mechanism; that is the same mechanism as this seed, so the remaining question is only whether the legal-domain data or constraint creates a genuinely new test.
- **Known duplicate:** `yes`
- **Expected acceptable outcome:** Names LoRA (or the unambiguous gold record) and states that the low-rank adaptation mechanism is already established; recommends stopping or narrows to a specific new condition and test. A novelty claim for the mechanism itself fails.
- **Notes:** Do not accept "low-rank adaptation" as a generic phrase without the gold identification and the equivalence statement. A domain-specific data contribution may be a legitimate difference only if it is stated as a condition and paired with a test.

### EP-02 — Sharing key/value heads in a pretrained decoder

- **Task ID:** `EP-02`
- **Provider slot / expertise:** `TP-01` — NLP evaluation (non-author; **unbound**)
- **Task type:** `novelty_check`
- **User prompt (verbatim):**

```text
We want to cut KV-cache memory during inference for a pretrained decoder-only model. Our plan is to let several query heads share one key/value head, initialize the shared heads from a trained multi-head checkpoint, and continue training briefly to recover quality. Is this novel enough to pursue, and what is the closest prior work? If it is already covered, say what remains open.
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-02` — "GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints" (`arXiv:2305.13245`); sealed SHA-256 `44ec89c707b3b8c3c8b913bb27caa7d5c6aaaf8bac04262d8424c59801661cc6`.
  - **Why decisive:** Shares key/value heads across query heads and uptrains from a multi-head checkpoint; this directly covers the proposed KV-cache reduction and initialization.
- **Known duplicate:** `yes`
- **Expected acceptable outcome:** Names GQA (or the unambiguous gold record) and states that sharing KV heads plus uptraining already covers the plan; recommends stopping or a narrow open question. Naming only multi-query attention is not sufficient.
- **Notes:** Multi-query attention is an ancestor, but the prompt includes uptraining from a multi-head checkpoint, so the sealed gold is GQA. Score M1 against GQA, not against a generic "share KV heads" idea.

### EP-03 — Parameter count versus training tokens at fixed compute

- **Task ID:** `EP-03`
- **Provider slot / expertise:** `TP-02` — ML systems and training efficiency (non-author; **unbound**)
- **Task type:** `direction_choice`
- **User prompt (verbatim):**

```text
We have a fixed pretraining compute budget and are choosing between a larger model trained on fewer tokens and a smaller model trained on more tokens. Our goal is the best downstream performance at that budget, and inference cost is excluded from this decision. What is the nearest work that studies this trade-off, and what does it imply for how we set the split? State the conditions under which the implication changes.
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-03` — "Training Compute-Optimal Large Language Models" (`arXiv:2203.15556`); sealed SHA-256 `e79c4ff58b2828cbf80e146ae2e00dce41e3b686a24f0ea1b01babc077730edd`.
  - **Why decisive:** Derives a compute-optimal parameter/data allocation for fixed training compute; it is the nearest work that decides the proposed larger-model-versus-more-data trade-off.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names Chinchilla (or the unambiguous gold record), states the compute-optimal scaling result and a condition under which the recommended allocation changes (for example data quality, inference budget, or architecture). A bare "more data is better" answer fails.
- **Notes:** Do not require an exact numeric split; the decision is about the allocation logic and its conditions. A generic scaling-law citation without the gold identification is insufficient.

### EP-04 — Exact attention with tiling and recomputation

- **Task ID:** `EP-04`
- **Provider slot / expertise:** `TP-02` — ML systems and efficient inference (non-author; **unbound**)
- **Task type:** `novelty_check`
- **User prompt (verbatim):**

```text
We want to make exact self-attention faster on long sequences by tiling the computation, keeping intermediate tiles in on-chip memory, and recomputing some intermediates during the backward pass instead of storing them. Is this a new idea, and what is the nearest prior work? If it is already established, what would a genuinely different contribution look like?
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-04` — "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness" (`arXiv:2205.14135`); sealed SHA-256 `63db80c9debc2e410fa7d930cb00d1a7eb23638d6f67f75447d894dff38930aa`.
  - **Why decisive:** Uses tiling, on-chip intermediate storage, and recomputation to compute exact attention with fewer HBM reads; that is the proposed mechanism.
- **Known duplicate:** `yes`
- **Expected acceptable outcome:** Names FlashAttention (or the unambiguous gold record) and states that tiling, recomputation, and IO-awareness are already the mechanism; recommends stopping or narrowing. A generic "efficient attention" answer fails.
- **Notes:** The prompt deliberately describes the mechanism, not the paper. M1 requires the gold identification and the equivalence statement, not merely a description of IO-aware attention.

### EP-05 — Step-by-step prompting for a mathematics tutor

- **Task ID:** `EP-05`
- **Provider slot / expertise:** `TP-05` — human-AI interaction and learning sciences (non-author; **unbound**)
- **Task type:** `direction_choice`
- **User prompt (verbatim):**

```text
We are building a tutoring assistant for middle-school mathematics. We plan to improve explanation quality by prompting the model to write step-by-step reasoning before giving the final answer, and we will evaluate whether students' revision quality improves. Is this direction novel, what is the nearest prior work, and what condition would make our study different from it?
```

- **Constraints / resources:** Public literature only; no student data; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-05` — "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (`arXiv:2201.11903`); sealed SHA-256 `bfb0113764f1004c1a81f963e24802db19357aea4d21f908d33cdf0f3d8bd422`.
  - **Why decisive:** Establishes step-by-step prompting as a reasoning intervention; the educational revision outcome is a different condition/outcome, not a new prompting mechanism.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names Chain-of-Thought (or the unambiguous gold record) and states that step-by-step prompting is established; identifies the educational outcome or population as the condition that could make the study different. A claim that the prompting mechanism is new fails.
- **Notes:** The gold is the prompting mechanism, not an education paper. Accept a genuine educational-condition difference; do not accept a generic "AI tutor" citation that never reaches the mechanism.

### EP-06 — What retrieval-augmented generation establishes

- **Task ID:** `EP-06`
- **Provider slot / expertise:** `TP-03` — information retrieval and evidence synthesis (non-author; **unbound**)
- **Task type:** `evidence_review`
- **User prompt (verbatim):**

```text
We are reviewing whether retrieval-augmented generation actually improves factual accuracy for knowledge-intensive questions compared with a strong parametric model. Summarize what the nearest prior work establishes, under what conditions, and what it does not establish. We care about the mechanism, not a leaderboard number.
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-06` — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (`arXiv:2005.11401`); sealed SHA-256 `12834e9cb8ca066d01cdbddb30c3537885ce0cb826d65b68816684d6d9368e09`.
  - **Why decisive:** Introduces retrieval-augmented generation with a parametric model plus a non-parametric retrieval index; it is the canonical nearest work for the proposed factual-question-answering mechanism.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names RAG (or the unambiguous gold record), states the parametric-plus-retrieval mechanism and its conditions and limits, and does not claim that it eliminates hallucination. A generic "RAG helps" answer fails the difference/limits requirement.
- **Notes:** The review must distinguish what the work establishes from what it does not. A claim that retrieval guarantees factual support is an unsupported-citation risk, not a correct summary.

### EP-07 — A minimal clinical question-answering evaluation

- **Task ID:** `EP-07`
- **Provider slot / expertise:** `TP-04` — biomedical NLP and clinical evaluation (non-author; **unbound**)
- **Task type:** `proposal_draft`
- **User prompt (verbatim):**

```text
Draft a minimal evaluation plan for a clinical question-answering assistant that uses a frozen general-purpose LLM plus retrieval over PubMed abstracts. We need a defensible benchmark and a nearest-work comparison. Identify the closest prior work, state how our evaluation should differ, and give the next concrete step with a cost bound and a stop condition.
```

- **Constraints / resources:** Public literature only; no patient data; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-07` — "PubMedQA: A Dataset for Biomedical Research Question Answering" (`arXiv:1909.06146`); sealed SHA-256 `54375c9f33969f56bd32b550e80307074b6287702a7a14cd0943ddf98e61bb31`.
  - **Why decisive:** Provides a biomedical question-answering benchmark built from PubMed abstracts with expert annotations; it is the nearest public evaluation for the proposed PubMed-retrieval clinical assistant.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names PubMedQA (or the unambiguous gold record) as the nearest benchmark, states how the proposed evaluation differs (assistant task, retrieval setup, clinical safety), and gives a concrete next step with a bound and stop condition. A fabricated benchmark identifier fails.
- **Notes:** PubMedQA is the nearest benchmark, not a clinical deployment study. The acceptable difference is the assistant/evaluation/safety setting. Check that the identifier resolves before sealing.

### EP-08 — Direct preference optimization in a clinical setting

- **Task ID:** `EP-08`
- **Provider slot / expertise:** `TP-04` — biomedical NLP and clinical evaluation (non-author; **unbound**)
- **Task type:** `proposal_draft`
- **User prompt (verbatim):**

```text
We want to adapt a biomedical LLM to clinician preferences using pairwise rankings of two candidate answers. We plan to optimize the policy directly on the preference pairs without training a separate reward model. Is this method appropriate, what is the nearest prior work, and what condition or safety check would make our use different from that work?
```

- **Constraints / resources:** Public literature only; no patient data; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-08` — "Direct Preference Optimization: Your Language Model is Secretly a Reward Model" (`arXiv:2305.18290`); sealed SHA-256 `21c868b66c7021b7cf23b309814bf746ec7737c46b8145e8cb46b27a2a8abebd`.
  - **Why decisive:** Optimizes a policy directly on pairwise preferences without a separate reward model; the proposed clinical use must differ by data, safety condition, or evaluation, not by the base algorithm.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names DPO (or the unambiguous gold record) and states that direct preference optimization is established; identifies clinical preference data, safety evaluation, or deployment conditions as the difference and gives a test. A claim that the base algorithm is new fails.
- **Notes:** DPO is the base algorithm. The acceptable difference is clinical data/safety/evaluation, not a renamed optimizer. A proposal that ignores safety review fails the condition requirement.

### EP-09 — BM25 versus dense retrieval for a new scientific corpus

- **Task ID:** `EP-09`
- **Provider slot / expertise:** `TP-03` — information retrieval and evidence synthesis (non-author; **unbound**)
- **Task type:** `evidence_review`
- **User prompt (verbatim):**

```text
We are building a literature-review assistant and need to choose between BM25 and a dense dual-encoder retriever for a new scientific corpus. Review the nearest evidence comparing these retrieval approaches. What does it establish, under what conditions, and what would we still need to test on our corpus?
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-09` — "Dense Passage Retrieval for Open-Domain Question Answering" (`arXiv:2004.04906`); sealed SHA-256 `c243d0f226e374bf25708bc3ce35263a41c85eb5b80c77e2d8ea233d9dc56bca`.
  - **Why decisive:** Compares dense dual-encoder retrieval with sparse BM25 on open-domain question answering; it is the nearest evidence for the proposed retrieval choice and its conditions.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names DPR (or the unambiguous gold record), states the dense-versus-sparse comparison and its condition dependence (training data, domain, corpus), and proposes a corpus-specific test. A universal "dense beats BM25" claim fails.
- **Notes:** The review should not turn a benchmark result into a universal rule. A condition-specific recommendation is the acceptable outcome; a universal claim is an overreach.

### EP-10 — A comparison-reward-model and PPO alignment recipe

- **Task ID:** `EP-10`
- **Provider slot / expertise:** `TP-05` — human-AI interaction and alignment evaluation (non-author; **unbound**)
- **Task type:** `novelty_check`
- **User prompt (verbatim):**

```text
We want to improve instruction following by collecting human comparisons between model outputs, training a reward model on those comparisons, and optimizing the policy with PPO against that reward model. Is this a novel alignment recipe, and what is the nearest prior work? If it is already established, what remains open?
```

- **Constraints / resources:** Public literature only; no human-subject data; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-10` — "Training language models to follow instructions with human feedback" (`arXiv:2203.02155`); sealed SHA-256 `998429fce6baca86a2889bb3306f5ee5d59f1dbc54403318d75805a0bbd32382`.
  - **Why decisive:** Establishes the comparison-reward-model plus PPO pipeline for instruction following; the proposed alignment recipe is the same mechanism.
- **Known duplicate:** `yes`
- **Expected acceptable outcome:** Names InstructGPT (or the unambiguous gold record) and states that the comparison-reward-model plus PPO pipeline is established; recommends stopping or narrowing to an open condition. A claim that the recipe is new fails.
- **Notes:** Naming only "RLHF" without the gold identification may be insufficient. The prompt describes the InstructGPT pipeline; M1 requires the gold work and the equivalence statement.

### EP-11 — Document order in long-context question answering

- **Task ID:** `EP-11`
- **Provider slot / expertise:** `TP-03` — information retrieval and evidence synthesis (non-author; **unbound**)
- **Task type:** `evidence_review`
- **User prompt (verbatim):**

```text
We are testing whether the position of the most relevant document in a long context changes question-answering accuracy. We plan to compare relevant documents placed at the beginning, middle, and end of the context. What is the nearest prior work, what did it find, and what condition would make our test informative rather than a repeat?
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-11` — "Lost in the Middle: How Language Models Use Long Contexts" (`arXiv:2307.03172`); sealed SHA-256 `1de92a3d8d24a7d8de9f76a4aa048d40bd6ae5c3fdc7e23a1e1802b1a3e20212`.
  - **Why decisive:** Documents position-dependent long-context question-answering performance, including the middle-context drop; it is the nearest work for the proposed document-order test.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names Lost in the Middle (or the unambiguous gold record), states the position effect, and identifies a new domain, model, or test condition that would make the study informative. An unaware "we will test order" answer fails.
- **Notes:** The gold documents a position effect; the acceptable difference is a condition and a test that could change the finding. A repeat without a condition fails.

### EP-12 — Adaptive draft length for speculative decoding

- **Task ID:** `EP-12`
- **Provider slot / expertise:** `TP-02` — ML systems and efficient inference (non-author; **unbound**)
- **Task type:** `direction_choice`
- **User prompt (verbatim):**

```text
We want to speed up autoregressive inference by using a small draft model to propose several tokens and a large model to verify them in one pass, accepting a token when the verification distribution supports it. Unlike a fixed draft length, we want to adapt the number of proposed tokens online based on recent acceptance. Is this direction novel, what is the nearest prior work, and what condition would make our adaptive variant a real contribution?
```

- **Constraints / resources:** Public literature only; single turn; state assumptions; English output; one Markdown artifact.
- **Allowed tools:** Common tool envelope.
- **Caps:** 30 min wall-clock; 5,000 output tokens; 12 retrieval calls. Same in all arms.
- **Sealed gold nearest work:** `G-EP-12` — "Fast Inference from Transformers via Speculative Decoding" (`arXiv:2211.17192`); sealed SHA-256 `b9021da2cb44b1cbf5380124fc22326b13d7c5deff07f6010687c83452c4741c`.
  - **Why decisive:** Establishes draft-then-verify speculative decoding with an acceptance rule; the proposed adaptive draft length differs only in scheduling and condition.
- **Known duplicate:** `no`
- **Expected acceptable outcome:** Names speculative decoding (or the unambiguous gold record), states that draft-then-verify is established, and identifies adaptive draft length or scheduling as the condition and a test for it. A claim that draft-then-verify is new fails.
- **Notes:** The gold is the fixed-length framework; adaptive length is a variant, not a new base mechanism. The acceptable difference must be stated as a scheduling condition plus a test.

---

## 5. Sealing, provider binding, and freeze checklist

Before the first run, the pilot lead must complete all items and record the result in the local run log:

- [ ] At least 12 task records are complete; no field is a placeholder.
- [ ] At least four **distinct real non-author humans** are bound to `TP-01`–`TP-05`; the local register maps slots to identities and conflict-of-interest declarations. No names are committed.
- [ ] Each bound provider has read their task prompt and confirmed it reflects a real decision they would face; any rejected task is replaced **before** sealing.
- [ ] Each gold title and identifier resolves to the intended public source; the per-task hashes and the gold-bank commitment match the recomputation.
- [ ] The task bank file SHA-256 and the gold-bank commitment are recorded; the local gold key is locked.
- [ ] The author(s) are excluded from provider and reviewer slots.
- [ ] The arm prompts, caps, and tool envelope are rendered with the same task fields for all three arms.
- [ ] No private, unpublished, or provider-identifying material is in the prompts, this file, or the repository.
- [ ] The bank is marked `EP-TB-01-FROZEN` in the local log with the timestamp; the first run starts only after that.

After the first scored run, **no field in this file, no gold record, and no task prompt may change**. If a defect is found, record it, stop if the protocol requires it, fix it in a new version, and re-measure with a new pilot ID. Do not reuse the old outputs.
