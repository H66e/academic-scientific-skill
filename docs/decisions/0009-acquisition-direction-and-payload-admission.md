# ADR 0009: Acquisition direction and ledger payload admission

## Context

The Python runtime contains two supported acquisition surfaces. The ledger workflow (`core.py`, `providers.py`, `transport.py`, `ledger.py`, `judgment.py`, `results.py`, `readings.py`) records acquired sources, anchors, claims, results and decisions in an append-only ledger. The older dossier/reference utilities (`audit.py`, `sources.py`, `outputs.py`, `evolution.py`) serve the released dossier contract and standalone source commands. Both parse arXiv/Crossref metadata and HTML, and they diverge in paper IDs, block/offset models, and privacy handling. ADR 0007 removed the JavaScript implementation but described "one implementation" as the rationale; that statement is not true of the two Python surfaces, and reviewers must currently audit both.

Separately, `Ledger.verify` validated payload shapes only for `result.record`, `result.invalidate` and `reading.retract`. The other 14 registered event types accepted any object, so a structurally valid ledger could pass `verify-ledger` and then crash the CLI (`status` raised `KeyError` on a `candidate.upsert` event without `id`). The low-level `Ledger.append` is documented as structural, but it is exported and callers can reach it.

## Decision

- The ledger stack owns new acquisition, evidence, reading, result and decision features. The dossier/reference stack is maintenance-only: security and correctness fixes, contract compatibility, and frozen regression evidence, but no new providers or new scientific capabilities. New work must not add a third surface.
- Until a reviewed refactor (not in this release), the two surfaces remain and the duplicated acquisition/HTML extraction code is accepted as documented debt. Every command must be attributable to one contract, and documentation must state which workflow a command belongs to.
- All 17 registered ledger event types get explicit payload admission validation, shared by `Ledger.append` and `Ledger.verify`. Required fields are the fields the runtime's own producers set and its consumers dereference unconditionally; extra keys remain allowed for forward compatibility; the existing result/reading validators are reused rather than duplicated. The JSON schema remains editor assistance and is not the runtime authority.
- The threat model is recorded here: the ledger chain and external anchor detect accidental edits, partial writes and tail truncation; payload admission rejects malformed events; the outbound classification gate blocks `private` material before network access; `verify-artifacts` re-derives provider metadata from retained bytes. They do **not** defend against an owner who deliberately rewrites ledger, anchor and artifacts together, do not authenticate human identity, do not prove an HTTP response was truthful, and do not establish scientific correctness or reading fidelity.

## Alternatives

- Merge the two acquisition stacks now: removes the duplication but is a large, test-heavy refactor that would compete with the release-hardening scope and risk the dossier contract. Deferred.
- Keep only the dossier stack: loses the ledger's receipt, anchor, lifecycle and reading guarantees. Rejected.
- Validate only the event types that currently have JSON schema definitions: leaves the demonstrated `KeyError` reachable through half the vocabulary. Rejected.
- Keep `Ledger.append` permissive and make every consumer defensive: hides malformed records instead of reporting them. Rejected; consumers still fail closed, but admission is the primary gate.

## Rationale

Naming one owning surface stops the duplication from growing while keeping the release scope small. Payload admission converts a class of consumer crashes into a clear verification error, and it matches the existing policy that verification reports invalid data instead of repairing or ignoring it. Recording the limits keeps the guarantee honest: these checks are consistency and admission controls, not authentication.

## Consequences

- Existing private ledgers whose events lack a required field will fail `verify-ledger` and need explicit inspection; the tool does not rewrite them. This is the same trade-off already taken for unknown event types.
- `Ledger.append` is still a low-level API, but no longer accepts payloads that consumers cannot read.
- Reviewers have a documented direction for future acquisition work; the duplication stays a known cost until the deferred refactor.
- Parser and CLI failures now surface as structured envelopes rather than tracebacks, but a structural pass still never proves scientific or provenance truth.
