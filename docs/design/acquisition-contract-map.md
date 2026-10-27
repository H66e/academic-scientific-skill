# Acquisition contract map

Status: implemented documentation for 0.5.0, 2026-10-27. This map records the two
supported acquisition/audit surfaces in the Python runtime, the data contracts
each one is bound to, and who may change what. It does not change any contract;
the direction is decided in [ADR 0009](../decisions/0009-acquisition-direction-and-payload-admission.md).
Result interpretation was retired from the ledger workflow in 0.5.0
([ADR 0010](../decisions/0010-scope-refocus-0.5.0.md)); result events and payload
rules remain only so historical ledgers keep verifying.

## Why two surfaces exist

[ADR 0007](../decisions/0007-python-only-toolchain.md) retired the JavaScript
implementation and described "one implementation". That statement is true of the
toolchain language, not of the acquisition surfaces: the Python runtime still
contains two of them with separate data and approval semantics, and reviewers
must currently audit both. [ADR 0009](../decisions/0009-acquisition-direction-and-payload-admission.md)
names the ledger stack as the owner of new work and keeps the dossier/reference
stack maintenance-only until a reviewed refactor. The user-facing split is also
stated in [python-core.md](../../skills/ai-research-mentor/references/python-core.md)
("Start and inspect").

## Surface map

### Ledger stack (owner of new features)

| Item | Value |
| --- | --- |
| Entry point | `python -B skills/ai-research-mentor/scripts/research_mentor.py --project <private-project> ...` |
| Entry functions | `research_mentor/cli.py` → `ResearchCore` (`core.py`), `Judgment` (`judgment.py`) |
| Modules | `core.py`, `providers.py`, `transport.py`, `ledger.py`, `judgment.py`, `results.py`, `readings.py`, `anchors.py`, `event_payloads.py`, `privacy.py` |
| Writes | Append-only ledger `<private-project>/ledger.jsonl` plus `<private-project>/ledger.anchor.json`, `sources/` artifacts and IR files |
| Commands | `init`, `doctor`, `status`, `search`, `resolve`, `fetch`, `quote`, `show-source`, `confirm-source`, `candidate`, `claim`, `link`, `confirm-read`, `retract-read`, `coverage`, `next`, `assess`, `decision`, `finalize`, `revoke`, `export-dossier`, `verify-ledger`, `anchor-ledger`, `verify-artifacts`, `lint`, `recheck` |
| Contracts | `ledger-json-v1`, `ledger-anchor-v1`, `text-normalized-v1` anchors, `python-credibility-v5` policy, 17-type closed event vocabulary with payload admission (legacy `result.record`/`result.invalidate` readable, not interpreted) |
| Change policy | New acquisition, evidence, reading and decision features land here. Result interpretation is retired (policy v5, ADR 0010); legacy result events are read-only compatibility. A change to a frozen protocol identifier needs an explicit new protocol/policy version, an ADR, migration notes for existing ledgers and regression tests. |

### Dossier/reference stack (maintenance-only)

| Item | Value |
| --- | --- |
| Entry points | `python -B skills/ai-research-mentor/scripts/research_audit.py ...`, `research_sources.py ...`, `research_outputs.py ...`, `evolution_guard.py ...` |
| Entry functions | `research_mentor/tool_cli.py` → `audit.py`, `sources.py`, `outputs.py`, `evolution.py` |
| Writes | `research_audit.py init` creates a private dossier tree; `research_sources.py fulltext` can save an artifact only with both an explicit `--root` and `--out`; the other commands print JSON to standard output and do not append to a ledger |
| Commands | `research_audit.py init/validate/fingerprint/rank/migrate/verify-receipts`; `research_sources.py search/verify/fulltext`; `research_outputs.py card/draft/bibtex`; `evolution_guard.py snapshot/hash/checks-hash/check` |
| Contracts | dossier schema 3 / decision contract 3 and its canonical-JSON fingerprint; frozen standalone acquisition/output JSON shapes |
| Change policy | Maintenance-only: security and correctness fixes, contract compatibility, and frozen regression evidence. No new providers and no new scientific capabilities. Every change must keep existing canonical bytes and the frozen fixtures unchanged. |

## Frozen contracts

| Contract | Defined in | Frozen because |
| --- | --- | --- |
| dossier schema 3 / decision contract 3 | `audit.py:21` (`DECISION_CONTRACT_VERSION = 3`), `audit.py:266-281` accepts legacy 1/2 as readable but not authoritative; semantic requirements in [data-contract.md](../../skills/ai-research-mentor/references/data-contract.md) | Released users already hold dossiers; changing the field set or decision semantics would silently invalidate or fabricate approvals. Legacy migration is explicit and archived, and old reviews never regain authority. |
| dossier canonical JSON fingerprint | `audit.py:51-52` (`_utf16` key bytes), `audit.py:84-131` (UTF-16 key order, index-first keys, binary64 number spelling) | The fingerprint is the evidence-of-consistency link between a dossier and its reviews. Byte drift makes every existing review stale or unrecognisable. |
| `ledger-json-v1` | `ledger.py:25`, `ledger.py:44-62` (sorted-key JSON, no floats, SHA-256 chain) | Every existing ledger hash and every cross-check of a chain depends on the exact bytes. It is deliberately separate from the dossier fingerprint (`audit.py:88`). |
| `ledger-anchor-v1` | `ledger.py:26`, `ledger.py:241-255` | The external anchor records the expected head and count; silently changing its shape weakens tail-truncation detection. |
| `text-normalized-v1` anchors | `anchors.py:10-12` (NFC, NBSP and whitespace normalization), `anchors.py:31-43` | Quote offsets, quote hashes and source-text hashes must be reproducible from retained bytes across platforms. |
| `python-credibility-v5` | `judgment.py:22` (`POLICY_VERSION`), recorded in `review.record` (`judgment.py:340`) and bound into the snapshot digest (`judgment.py:74`) | The policy decides when a machine recommendation and a human decision are current. v5 retires result-derived inputs and excludes `result.record`/`result.invalidate` from the snapshot; a new policy intentionally stales prior reviews and must be a deliberate, recorded change rather than an edit in place. |
| 17-event closed vocabulary and payload admission | `ledger.py:27-39` (`EVENT_ACTORS`), `event_payloads.py:15-51` (documented table), `event_payloads.py:138-143` (`REQUIRED_FIELDS`), admission used by `append`/`verify` (`ledger.py:205-216`, `269-271`) | Verification must report malformed data instead of repairing it or crashing later. Adding an event type requires registering its actor/trust pair, payload rule and consumer together. The result event types remain registered only for old-ledger compatibility. |

Dossier semantics and gate rules are documented in
[data-contract.md](../../skills/ai-research-mentor/references/data-contract.md);
the ledger workflow and its limits are in
[python-core.md](../../skills/ai-research-mentor/references/python-core.md).

## Who may change which

The rule is about change classes, not individuals; a repository owner who wants a
new contract revision still has to follow the same path.

| Change class | Ledger stack | Dossier/reference stack |
| --- | --- | --- |
| New provider, parser, acquisition or evidence feature | Allowed; add tests and update the reference docs. | **Prohibited.** The stack stays maintenance-only; new capabilities go to the ledger. |
| New or changed scientific gate, reading semantics, policy | Allowed only with an ADR, a policy-version change (`python-credibility-v5` → new id), regression cases and a compatibility note. Result interpretation is retired and must not be reintroduced without a new scope ADR. | **Prohibited.** The dossier decision contract is frozen; release hardening may fix defects, not add gates. |
| Security or correctness fix | Allowed; must not change the hash/anchor protocols silently. | Allowed; must not change canonical dossier bytes, frozen fixture expectations or migrated-record semantics. |
| Change to a frozen contract identifier or shape | Requires a separate reviewed contract revision: new protocol id or schema/decision-contract version, ADR, migration note, new regression evidence. | Same. Editing fixtures or hashes to make a change pass is not a contract revision. |
| Command-surface change | Keep one contract per command and document it in the README command table and [python-core.md](../../skills/ai-research-mentor/references/python-core.md). | Same; maintenance commands must keep their current output shapes or add a versioned replacement. |

Cross-stack rules:

- Approvals and hashes never move between the stacks. `export-dossier` is a
  schema-3 projection that intentionally omits evidence associations and
  reviews; it is not a lossless round trip and does not transfer an approval
  (`core.py` `export-dossier`, [python-core.md](../../skills/ai-research-mentor/references/python-core.md)).
- A command belongs to exactly one contract. The README table and
  [python-core.md](../../skills/ai-research-mentor/references/python-core.md)
  are the user-facing statement of that assignment.
- Do not add a third surface. Fixes belong to an existing stack.

## Known divergences (accepted debt)

The two surfaces still parse the same providers and HTML differently. Each
divergence is a boundary, not a bug to paper over in documentation.

### 1. Paper ID schemes

| Stack | Scheme | Evidence |
| --- | --- | --- |
| Ledger | Provider-derived `P-<sha256(kind:identity)[:16]>`; source events `SRC-<raw_sha256[:16]>`; anchor events `E-<digest[:16]>` | `providers.py:30-31` (`paper_id`), `core.py:249` (`SRC-`), `core.py:310` (`E-`) |
| Dossier/reference | Standalone acquisition uses `doi-<hash[:24]>` and `arxiv-<hash[:24]>`; dossier papers are caller-supplied free-form `id` values whose provider identity lives in the `identifiers` object | `sources.py:316`, `sources.py:459`, [data-contract.md](../../skills/ai-research-mentor/references/data-contract.md) papers section |

Consequence: the same DOI or arXiv version has different IDs in the two stacks.
There is no automatic cross-walk, so an ID must not be copied between them; use
each stack's own `resolve`/`verify` result.

### 2. Block and offset models

| Stack | Model | Evidence |
| --- | --- | --- |
| Ledger | IR blocks have sequential IDs (`B-0001`, ...) and no character offsets; quote anchors are Python code-point offsets into NFC/whitespace-normalized text, versioned as `text-normalized-v1`; PDF is acquired but not extracted | `core.py:34-35`, `core.py:55-74`, `anchors.py:10-12`, `anchors.py:31-43` |
| Dossier/reference | HTML blocks report UTF-16 code-unit offsets into the raw decoded HTML; dossier canonical JSON also orders and compares strings by UTF-16 code units | `sources.py:480-494` (`offset_unit: "UTF-16 code units"`), [source-tools.md](../../skills/ai-research-mentor/references/source-tools.md), `audit.py:51-52`, `audit.py:84-127` |

Consequence: a stored offset is only valid inside the stack and normalization
that produced it. Code-point offsets, UTF-16 offsets and raw-byte offsets are not
interchangeable, and UTF-16 ordering can differ from Python's default string
ordering for non-BMP text.

### 3. Privacy handling

Both stacks share one policy module ([privacy.py](../../skills/ai-research-mentor/runtime/research_mentor/privacy.py)),
which blocks credentials, e-mail addresses, local paths and `private`
classification before any network request, and rejects full-width variants used
to slip past the credential checks.

They differ in defaults:

| Entry point | Default classification | Evidence |
| --- | --- | --- |
| Ledger `search`, `fetch` | `private` (blocked) | `cli.py:37`, `cli.py:51` |
| Ledger `resolve` | `public` | `cli.py:43` |
| Standalone `search` | `private` | `tool_cli.py:88` |
| Standalone `verify`, `fulltext` | `public` | `tool_cli.py:88` |

Consequence: the same string can be blocked by one command and sent by another
unless `--sensitivity` is passed explicitly. The heuristics only catch obvious
paths and credentials; they cannot decide whether a technical idea is
unpublished ([privacy.py](../../skills/ai-research-mentor/runtime/research_mentor/privacy.py) docstring,
[python-core.md](../../skills/ai-research-mentor/references/python-core.md)).

### 4. Duplicated HTML extraction

The ledger IR parser (`core.py:55-74`, `html-stdlib-v1`) and the standalone HTML
block extractor (`sources.py:475-532`) are two implementations of a similar
lossy parse. ADR 0009 accepts this as documented debt until the deferred merge;
it does not mean the outputs are equivalent.

## Verification

From the repository root, the contracts above are exercised by:

```text
python -B evaluation/run-python-tests.py
python -B evaluation/skill_tools.py check-skill
python -B evaluation/skill_tools.py check-examples
python -B evaluation/skill_tools.py check-python-only
```

The frozen protocol and toolchain expectations are described in
[fixtures/README.md](../../evaluation/fixtures/README.md). Passing them shows
recorded software contracts still hold; it does not measure literature recall,
scientific value or research effectiveness.
