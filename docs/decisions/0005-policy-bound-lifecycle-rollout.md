# ADR 0005: Policy-bound lifecycle rollout

**2026-10-27 scope retirement:** ledger policy v4 is superseded by `python-credibility-v5`, which excludes result records from assessment and snapshots; result interpretation is out of scope for the skill from 0.5.0. The dossier contract-3 projection and its policy-bound review semantics remain unchanged in the maintenance stack. See [ADR 0010](0010-scope-refocus-0.5.0.md).

**2026-10-10 runtime retirement:** [ADR 0007](0007-python-only-toolchain.md) retires the second implementation described below. Native Python keeps both the dossier contract-3 dependency projection and the ledger policy-v4 snapshot semantics. Their distinct hashing mechanisms and historical rollout observations remain unchanged.

## Context

[ADR 0004](0004-result-lifecycle-semantics.md) froze the common semantics while Step 1 only closed admission. Result gates and cumulative reading reinterpret scientific inputs, including existing histories with unchanged ledger bytes. Old reviews must not remain current under changed rules.

## Decision

Implement result lifecycle and reading withdrawal as separately reviewed concerns. Result gates initially use Python `python-credibility-v3` and Node schema/decision contract 3. The subsequent reading predicate switch uses current policy `python-credibility-v4` in the same change; Node's decision contract remains 3. Each new event ships with its payload checks, authorization rules, consumers and tests. `ledger-json-v1` remains unchanged.

`POLICY_VERSION` participates in the snapshot digest. A returned `policy_version` label alone cannot invalidate anything. Preserve stored events and snapshots; old machine recommendations become historical, old human decisions become pending, and old reviews reject new decisions. Reassessment creates a new policy-bound review; a new human instruction is required to record a new decision.

This is deliberately global and conservative: a policy change stales all candidates, including those unaffected by the particular rule. Isolated policy changes must leave scientific facts and `missing` reasons unchanged. The policy is a currency boundary, not a gate shortcut. Do not introduce a narrower dependency model during this rollout.

Python includes scientific ledger events by default, excluding review/decision outputs. Node explicitly projects review dependencies and must include result invalidations and complete classification history. These opposite defaults need separate regression coverage; changing only one runtime leaves stale-approval holes.

## Alternatives

- Relabel historical reviews: rejected because it silently claims review under rules that were never applied.
- Change only the reading predicate: rejected because identical ledger bytes otherwise preserve the old digest.
- Build per-feature policy axes or special-case redundant readings: deferred with the dependency model.

## Rationale

Explicit causality and withdrawal repair errors without rewriting history. Conservative freshness checks keep corrected eligibility distinct from reviewed approval.

## Consequences

Existing valid histories remain readable and verifiable; interpretation upgrades require reassessment, not ledger rewriting. Node v1/v2 records require explicit v3 migration and cannot regain old approval. No third-party runtime dependency, Python T3 mechanism, experiment execution or publication authority is introduced. Synthetic regression checks establish contract behavior, not research quality.
