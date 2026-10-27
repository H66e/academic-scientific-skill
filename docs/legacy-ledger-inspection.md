# Inspecting a legacy ledger that fails payload admission

Status: read-only inspection procedure for 0.4.0, 2026-10-27. This document adds
no migration tool; none exists.

Since 0.4.0, `verify-ledger` checks the required `data` fields of all 17
registered event types, and `append` shares the same admission rule. A ledger
written by an older producer that omitted a now-required field still has a valid
hash chain, but it fails verification. The runtime never repairs or rewrites such
a ledger, and neither should an automatic tool: the file is local research
material, and changing it changes what the recorded evidence claims.

Related references:
[python-core.md](../skills/ai-research-mentor/references/python-core.md)
("Reliability and evaluation"), [ADR 0009](decisions/0009-acquisition-direction-and-payload-admission.md)
(Consequences), and the payload table in
[event_payloads.py](../skills/ai-research-mentor/runtime/research_mentor/event_payloads.py).

## What the failure means

`verify-ledger` reports `ok: false`, `status: "invalid"` and exits non-zero. Each
malformed event appears in `errors`, for example:

```text
invalid event payload at line 4: candidate.upsert: missing required field 'title'
```

Three variants exist:

- `invalid event payload at line N: <type>: ...` for most event types
  (`ledger.py` verify branch).
- `invalid result payload at line N: ...` for `result.record` / `result.invalidate`.
- `invalid reading retraction payload at line N: ...` for `reading.retract`.

Other errors such as `event hash mismatch`, `hash chain mismatch`,
`unregistered event type` or `invalid ledger JSON` describe a different problem:
reference corruption, an unsupported old vocabulary, or an edited chain. They are
outside this procedure and need their own inspection; do not assume a payload fix
addresses them.

The ledger becomes read-only until a person resolves it: `append` refuses to
extend an invalid ledger, and `anchor-ledger` refuses to anchor one. In
particular, do **not** use `anchor-ledger` to "adopt" a failing ledger as the
expected state; it refuses, and adopting malformed bytes would defeat the point
of the anchor.

## Procedure (read-only)

Work on a copy of the project, or run only commands that read. Replace
`<private-project>` with a project directory outside this source repository and
ignored by Git (the runtime rejects project paths inside the published skill tree
or an unignored Git path). These commands make no network request and write
nothing.

1. Record the current bytes so you can prove the original was not modified:

   ```text
   Get-FileHash -Algorithm SHA256 -LiteralPath '<private-project>\ledger.jsonl'
   Get-FileHash -Algorithm SHA256 -LiteralPath '<private-project>\ledger.anchor.json'
   ```

   On Linux/macOS use `sha256sum <private-project>/ledger.jsonl` for both files.
   Keep the hashes in your own working note, outside the repository.

2. Capture the verification report:

   ```text
   python -B skills/ai-research-mentor/scripts/research_mentor.py --project <private-project> verify-ledger
   ```

   Save the JSON output. Note the line numbers and event types in `errors`.

3. Inspect the reported line without editing it. For line 4:

   ```text
   python -B -c "import json; line=open(r'<private-project>/ledger.jsonl', encoding='utf-8').read().splitlines()[3]; print(json.dumps(json.loads(line), ensure_ascii=False, indent=2))"
   ```

4. Compare the event `data` keys with the runtime's required fields:

   ```text
   python -B -c "import json,sys; sys.path.insert(0, 'skills/ai-research-mentor/runtime'); from research_mentor.event_payloads import REQUIRED_FIELDS; event=json.loads(open(sys.argv[1], encoding='utf-8').read().splitlines()[int(sys.argv[2])-1]); print(event['type']); print('missing:', sorted(set(REQUIRED_FIELDS[event['type']]) - set(event['data'])))" "<private-project>/ledger.jsonl" 4
   ```

   `REQUIRED_FIELDS` is the documented table in `event_payloads.py`. Extra keys
   are allowed and are not a failure; only missing fields (or wrong primitive
   types) are.

5. Classify what you found before deciding anything:

   - **Old producer.** The field is absent because the version that wrote the
     event did not set it. The chain and anchor may still match. This is the
     legacy case this document covers.
   - **Hand-edited or corrupted.** The event no longer matches its recorded
     `sha256`, or the chain/anchor does not match. Payload admission reports many
     such cases, but a deliberate edit that recomputed the hash would not be
     detected by admission; do not treat a clean chain as proof that the
     content is authentic.
   - **Unsupported vocabulary.** An unregistered type is a different failure and
     may predate the closed vocabulary. It is not repaired by adding fields.

6. Decide **archive or repair**, explicitly, and write the decision down in your
   own local note (not in the published repository):

   - **Archive (recommended default).** Keep the failing project exactly as it
     is, as evidence of the earlier run. Start new work in a new private project
     directory so new events get a fresh `ledger.jsonl` and anchor. Do not move,
     truncate or edit the old file. Re-run the hash command from step 1 at the
     end and confirm it is unchanged.
   - **Repair (explicit, separate maintenance action).** There is no migration
     command for ledger events, and `verify-ledger`/`append` will not rewrite
     them. Repairing means producing a new ledger file by hand or with a
     reviewed one-off script and recomputing every affected hash, the chain and
     the anchor. That changes the record's provenance: the original chain no
     longer authenticates the repaired file, and fields must not be invented to
     make a consumer pass. Keep the original bytes as evidence, document every
     changed event and the reason, and treat it as a reviewed maintenance task,
     not a routine fix. If you only need to continue research, archive instead.

7. Never auto-rewrite. Do not delete lines, reorder events, recompute hashes in
   place, drop the final line, or delete `ledger.anchor.json` to make the error
   disappear. Any of these silently destroys evidence and is worse than a
   reported failure.

## Minimal example

A synthetic legacy ledger line (shown as the event object; the real file has one
compact JSON object per line) contains a `candidate.upsert` event whose `data`
has `id`, `version`, `question`, `hypothesis`, `contribution`, `research_type`,
`search_ids`, `nearest_work`, `novelty`, `feasibility` and `validation` but no
`title`:

```json
{
  "seq": 4,
  "id": "EV-000004",
  "type": "candidate.upsert",
  "data": {
    "id": "C-1",
    "version": 1,
    "question": "A concrete question",
    "hypothesis": "A falsifiable hypothesis",
    "contribution": "A conditional comparison",
    "research_type": "empirical",
    "search_ids": [],
    "nearest_work": [],
    "novelty": {"status": "incremental"},
    "feasibility": {"status": "ready"},
    "validation": {"status": "specified"}
  }
}
```

`verify-ledger` then reports:

```text
invalid event payload at line 4: candidate.upsert: missing required field 'title'
```

The correct response is not to add a `title` value chosen to pass. First decide
whether the old event should be archived as-is, or whether a repairable record
with the original retained as evidence is warranted; then follow the chosen path.

## No migration tool exists yet

There is no command, function or documented script that upgrades ledger event
payloads. `research_audit.py migrate` migrates **dossiers** between schema
versions; it does not touch `ledger.jsonl`, and it must not be used as a ledger
migration. Until a reviewed migration exists, inspect manually and choose
archive or repair explicitly.
