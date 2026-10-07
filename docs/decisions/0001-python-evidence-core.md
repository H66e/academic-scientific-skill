# ADR 0001: Python evidence core with explicit compatibility

## Context

The v0.3 Node tools validate researcher-supplied records. They do not authenticate source content or prove literature coverage. Hand-written source IDs, quotations, reading claims and receipts make the reliable path unnecessarily difficult. The project needs a Python API for research use while preserving existing commands and dossiers.

## Decision

Add a standard-library Python runtime inside the maintained skill tree. One implementation serves the CLI and importable API. Acquisition tools write source receipts and exact text anchors to a project-local append-only ledger; model judgments reference those IDs. Raw sources and project records remain outside the source repository. Public/de-identified queries require an explicit classification before transport; private/unknown queries do not leave the machine.

Retain the v0.3 Node commands and schema-2 behavior as a compatibility path. The new ledger is not a replacement implementation of every Node audit rule. A v2 dossier projection is an initial record without fabricated reviews: export cannot resurrect an old GO. Python strict assessments and human decisions are separate from legacy ranking.

Bind human decisions to a candidate and evidence snapshot. Missing or stale decisions remain pending. No identity authentication or cryptographic signatures are introduced. The threat model is accidental errors, model hallucination, omission, stale state and hostile source instructions, not a deliberately dishonest owner. Hashes identify content and detect mistakes; they do not prove honesty, scientific truth or human identity.

Judgment policy `python-credibility-v2` consumes current-version load-bearing claim links for core support/refutation. Duplicate KILL requires an explicit mechanism-equivalence or duplicate claim supporting each decisive nearest comparison; labels and context-only claims do not suffice. Policy changes invalidate prior assessments through the snapshot without altering their historical records. Experimental result registration/classification is deferred; the host's result-interpretation prompt is not an implemented Python results layer.

## Alternatives

- Rewrite all Node tools immediately: rejected because language migration and changed decision semantics would be difficult to disentangle.
- Continue adding checks to hand-written receipts: rejected as the primary workflow because it leaves the most error-prone acquisition fields with the model.
- Require signed identities and a remote service: rejected as unnecessary for the current local research assistant.

## Rationale

Tool-created records reduce avoidable transcription errors. Exact anchors prove text presence only. Acquisition, parsing, delivery, reading confirmation and claim support remain distinct; fetching a document cannot claim it has been read. GO is a machine recommendation for a bounded next step, and never executes experiments or replaces a person's final decision.

## Consequences

Two runtimes remain intentionally supported during migration. Python has independent unit and workflow checks; Node regressions remain required. Existing fingerprints retain their existing canonicalization, including floats and JavaScript UTF-16 key ordering. New event hashes use a separate, versioned canonical contract. A deterministic package includes Python source and excludes bytecode. New provider, PDF/OCR, experiment and library capabilities can be added after failures in the initial evidence workflow are measured. No scientific-effectiveness claim follows from software tests.
