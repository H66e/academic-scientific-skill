# ADR 0003: External anchor for ledger tail truncation

## Context

The Python ledger is a hash chain: each event records the previous event's `sha256`. Verification recomputes every hash and checks each link. That detects edits to any surviving event and a torn final line, because every later event depends on the changed one.

It does not detect the loss of events from the end. Removing the last line leaves a shorter chain in which every remaining link is still intact, so `verify-ledger` returned `valid: true` on a ledger whose most recent observations, decisions or reviews had been removed. The surviving `expected_head` checks in `ledger.append` read the head **from the same ledger** that is being appended to, so they only guard against a concurrent writer, not against earlier loss.

This is not a hypothetical for the intended workflow. Research projects are directories a person may move, sync, partially copy, restore from backup, or trim by hand, and the events most likely to be lost that way are the most recent and most consequential ones — the human `decision.record` and the review it binds to. A ledger that reports "valid" after losing them actively misleads, which is worse than reporting nothing.

ADR 0001 already fixes the threat model: accidental errors, model hallucination, omission, stale state and hostile source instructions — not a deliberately dishonest owner. Any fix has to be judged against that boundary and must not overstate what it covers.

## Decision

Write a second file beside the ledger, `ledger.anchor.json`, recording the expected event count and head hash from **outside** the chain:

```json
{"protocol": "ledger-anchor-v1", "event_count": 4, "head": "<sha256 of the last event>"}
```

- `append` rewrites the anchor after the ledger line is fsynced, inside the writer lock. `_write_anchor` writes a temporary file, fsyncs it and calls `os.replace`, so a half-written anchor can never survive as a valid-looking shorter one.
- `verify` compares the anchor against the ledger and reports an `anchor` field: `matched`, `mismatch`, `absent`, or `unchecked` when the caller explicitly disables the check.
- A mismatch is a hard failure, not a warning. `verify-ledger` reports `valid: false` with the specific mismatch, and `append` refuses to extend the ledger until a person investigates — extending a truncated ledger would bury the loss under new events.
- A missing anchor is reported as `absent`, never as `matched`. Projects created before this change are not silently credited with protection they never had; `verify-ledger` emits a warning naming the `anchor-ledger` command.
- `anchor-ledger` records the current head and count. It refuses to anchor an already-invalid ledger, so it cannot bless a chain that fails its own hashes. It accepts a structurally valid but truncated ledger, which is unavoidable: nothing inside the directory can distinguish "truncated" from "this is what it always was". The command's output and `python-core.md` both say so plainly.

## Alternatives

- **Sign the head with a key held outside the project.** Rejected as out of scope: no identity or key management exists in this runtime, and ADR 0001 explicitly declines to introduce signatures. It also does not help the actual failure modes, which are accidents, not adversaries.
- **Append the expected head to a second append-only file.** Rejected because that file has the same vulnerability as the ledger: removing its last line removes exactly the record of the newest state, and nothing would notice.
- **Store the anchor outside the project directory** (user config, a registry, a remote service). Rejected as a larger architecture change than the problem warrants, and it breaks the property that a project directory is self-contained and portable. It would also create a new failure mode — a project moved to another machine loses its anchor and reports `absent`.
- **Refuse to read any unanchored ledger.** Rejected because it would make every existing project unusable until a person runs a migration command, for a protection most of them never needed.
- **Report a mismatch as a warning instead of a failure.** Rejected: a truncated ledger is not a lesser state than a malformed one, and a warning is exactly the "green forever" outcome this fix exists to remove.

## Rationale

Anchoring works because the expected state is stored somewhere the truncation does not touch. The chain's blind spot is that it can only reason about events that are still present; the anchor is the one record that knows how many there should be.

The `absent` state is deliberate. Trust-on-first-use is inherent here — an existing ledger can only be protected by adopting its current contents, and a truncation that happened before the upgrade cannot be detected afterwards. Reporting `absent` rather than `matched` keeps the tool honest about that gap instead of papering over it.

The anchor shares the ledger's directory and therefore its threat model. A person who deliberately deletes a ledger line and rewrites the anchor defeats it. That is consistent with ADR 0001 and is stated in the module docstring, `python-core.md`, and the CLI warning rather than left for a reader to infer.

## Consequences

`ledger.anchor.json` becomes a second file that must travel with `ledger.jsonl`. Copying a ledger without its anchor yields `absent`, which is a warning, not a failure — degraded but not broken. Copying a *stale* anchor alongside a newer ledger yields `mismatch` and blocks appends until a person resolves it, which is the correct outcome but does mean a careless partial copy can require manual intervention.

`verify` gained a keyword-only `check_anchor` parameter and an `anchor` field in its result. The field is additive; existing callers that only read `valid`, `errors` and `event_count` are unaffected. `ledger.anchor()` and the `anchor-ledger` command are new surface.

Four regression tests cover the original reproduction and its neighbours: tail truncation is now detected, an anchorless ledger is readable but reports `absent`, `anchor-ledger` adopts the current state and then matches, and `append` refuses a ledger whose anchor mismatches. Without them the fix could regress to `valid: true` on a truncated ledger and every other test would still pass — the failure is invisible in a healthy project.

No new dependency. Anchor writes reuse the existing lock, the existing `canonical_json` contract and the standard library's atomic replace.
