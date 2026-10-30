# ADR 0019: Nearest-set, claim and provisional contract before release

## Context

The 0.13.0 audit by the two external reviewers accepted several real fixes
(A/B projection dead code, NFKC C headings, C-only blocking, URL slicing,
template columns) but rejected release: both called for major revision again.
They showed that a report which copies the template, only changing the date,
could still pass `check-draft`; that A/B claims could bind `abstract`/`unseen`
candidates with self-answered kill questions; that the claim grade column was no
longer validated; that C IDs could be avoided by rewriting prose; that the
current-judgment directive only scanned Markdown bullets; that reference cells
with backticks were misparsed and the declared reading scope was not checked;
and that JSON type errors crashed the checker instead of reporting errors.

The common request was to make the report contract bind candidates, claims,
readings and provisional claims to one another, and to make the template itself
pass the checker end to end.

## Decision

- `nearest-set-json` becomes v2 with `schema`, `created_at`, at least two
  distinct non-placeholder queries, at least two candidates, and `uncovered`.
  Each candidate has a unique `P#` id and unique `ledger:` binding, a title,
  rationale, status (`full_text`/`section`/`abstract`/`unseen`), reader
  (`model`/`user`), a real locator, and at least two kill questions whose
  answers are exactly 是/否/未读到 and whose locators are real section/table
  references. Every candidate ledger must resolve in the verified projection;
  a `section`/`full_text` status cannot exceed the ledger reading scope.
- The claim table becomes six columns: 编号, 主张, 等级, 近邻, 依据, 翻转条件.
  A/B rows must reference existing nearest candidates, bind a `ledger:` id that
  is one of those candidates' ledgers, and require at least two answered
  (是/否) kill questions per bound candidate. An A claim must cover all read
  nearest candidates and mention unread candidates in `uncovered`; absolute
  novelty wording is rejected for A claims.
- The current-judgment section is parsed into claim units (paragraphs and list
  items); every unit needs a `[C#]` ID except plan units that start with
  下一步/行动/核验动作/获取路径. C IDs may appear there only in the qualified
  form `倾向……（见 [C#]）`; elsewhere they are rejected. All referenced IDs must
  exist in the claim table. Hard judgment terms outside the claim-bearing
  sections without an ID are errors.
- `provisional-json` (schema `provisional-v1`) becomes the machine contract for
  C claims: one entry per C claim with tendency, flip condition, access path,
  and a `check` that names an existing candidate and repeats one of that
  candidate's kill questions. Missing, unknown or paraphrased entries fail.
- Reference rows are backtick-stripped before checks, and the declared reading
  scope must be exactly `full_text` or `section:<locator>`; identity and
  scope-does-not-exceed-reading checks stay.
- The checker validates JSON types before use so malformed author input becomes
  an error list, never a traceback. A stale (>180 day) nearest set remains a
  warning but now also makes `delivery_ready` false. Candidate ledger ids are
  normalized to one source before uniqueness and coverage checks; read
  candidate locators must overlap a ledger reading locator, and `section:`
  reference scopes are checked the same way. Unread candidates and
  `未读到` answers may use locator 无 instead of inventing a section.
- After the second review round: blockquotes and the document title are
  scanned, plan blocks may not carry judgment terms, duplicate machine blocks
  fail, provisional checks must bind a candidate of the same C claim and a
  still-unread kill question, and bold subtitles are not headings.
- After the third review round: answered (是/否) kill-question locators must
  match a ledger reading locator by type and numeric prefix; a read candidate
  without a real reading locator fails; C claims must bind at least one
  nearest candidate and the provisional candidate must belong to that set;
  H1 also rejects absolute novelty wording; tests pin the checker date and a
  real-ledger end-to-end report passes `check_draft`.
- The report template keeps one canonical machine-readable appendix for the
  nearest set and provisional block instead of three divergent copies, and the
  reference/gate documentation is updated to the same contract.

## Alternatives

- Add a model-based semantic reviewer: rejected as non-deterministic and unable
  to prove support; the checker stays structural and says so.
- Keep the Markdown table for kill questions: rejected; the previous reviews
  showed arbitrary cells pass.
- Validate only JSON shape without binding to the ledger: rejected; it still
  allows fabricated candidates.
- Keep a soft stale warning only: rejected after review; a stale nearest set
  also makes `delivery_ready` false, while automatic re-search stays out of
  scope.
- Store nearest sets/readers as ledger events: deferred; `ledger-json-v1` is
  frozen in this release, so the report contract binds to the existing
  projection instead.
- Make a stale nearest set a hard `valid` error instead of a delivery block:
  rejected; the warning stays visible and `delivery_ready` is false.

## Consequences

- This is a breaking report-contract change: 0.13.0 `nearest-set-json`,
  five-column claim tables, bullet-only claim IDs and prose C sections fail.
  Old reports need migration; no automatic migration is provided because the
  missing bindings cannot be inferred.
- `reader: model` remains a declaration: only user/T1 ledger readings are
  verified, and model-first reading is still not authenticated. The checker
  cannot prove nearest-set completeness, kill-answer honesty, citation support,
  or scientific quality.
- The template, gate reference, SKILL summary, validation record and tests are
  one contract and must change together; `check-templates` keeps the
  anti-fabrication markers in place.
- No effect evidence is claimed. This release fixes a checkable contract, not
  the scientific effectiveness of the skill.
