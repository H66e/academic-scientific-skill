import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { renderCard, draftDossier, exportBibtex, validateNotes } from '../scripts/research_outputs.mjs';
import { rankDossier, validateDossier } from '../scripts/research_audit.mjs';

test('minimal notes produce a card without fabricating evidence or a GO', () => {
  const card = renderCard({ question: 'Why does the observed effect change across conditions?' });
  assert.match(card, /未记录，待评估/);
  assert.doesNotMatch(card, /已知结论与来源条件|GO/);
});
test('a recorded opinion is explicitly not a machine approval or an independent receipt', () => {
  assert.match(renderCard({ question: 'Q', decision: 'GO' }), /GO（本卡不构成机器门控或独立评审回执）/);
});
test('gap cards preserve the actual observation, reverse search, surviving boundary and decision test as notes', () => {
  const notes = { question: 'Which condition explains the discrepancy?',
    source_observations: 'Source version 1, section 3: observation under condition A.',
    gap: 'Condition B was not established in this source; a field-wide gap is not yet claimed.',
    alternatives: ['A simpler existing method may already resolve condition B.'],
    reverse_search: 'Not executed: checking that alternative is the next step.',
    boundary: 'Provisional condition B; unresolved until the reverse search.',
    test: 'Planned matched-condition test; a failed intervention is inconclusive.',
    scientific_consequence: 'A valid refutation would narrow the claimed mechanism.', decision: 'HOLD' };
  const card = renderCard(notes);
  for (const value of Object.values(notes).filter(value => typeof value === 'string')) assert.ok(card.includes(value));
  const draft = draftDossier(notes, { name: 'bounded-gap' });
  assert.equal(draft.project.notes.reverse_search, notes.reverse_search);
  assert.deepEqual(draft.searches, []);
  assert.deepEqual(draft.evidence, []);
  assert.deepEqual(draft.reviews, []);
});
test('a draft preserves provided notes and constraints but generates no searches, evidence, candidates or reviews', () => {
  const notes = { question: '  A real question  ', type: 'theoretical', known: ['Source A, theorem 2'],
    decision: 'GO', constraints: { time: { status: 'unknown', value: 'not yet confirmed' } }, assumptions: ['Assumption still untested'] };
  const before = structuredClone(notes);
  const draft = draftDossier(notes, { name: 'my-question' });
  assert.deepEqual(notes, before);
  assert.equal(draft.project.question, 'A real question');
  assert.equal(draft.project.research_type, 'theoretical');
  assert.deepEqual(draft.project.constraints, notes.constraints);
  assert.deepEqual(draft.project.notes.known, notes.known);
  for (const name of ['searches', 'papers', 'evidence', 'ideas', 'reviews', 'pilots']) assert.deepEqual(draft[name], []);
  assert.equal(validateDossier(draft).valid, true);
  assert.deepEqual(rankDossier(draft).ranked, []);
});
test('malformed or unconfirmed inputs are not repaired into invented facts', () => {
  assert.equal(validateNotes({ question: '', type: 'magic', alternatives: [null] }).valid, false);
  assert.throws(() => draftDossier({ question: 'Q' }, { name: '../other' }), /slug/);
  assert.throws(() => renderCard({ question: 'Q', decision: 'PIVOT' }), /decision/);
  assert.throws(() => draftDossier({ question: 'Q', constraints: 'guess a GPU' }, { name: 'topic' }), /constraints/);
});
const paper = { id: 'P-real-metadata', title: 'A title supplied by a source', year: 2024,
  url: 'https://example.org/paper', identifiers: { doi: '10.1234/example' }, authors: [{ given: 'Jane', family: 'Doe' }] };
test('bibliography preserves actual names and identifiers without guessing venue or publication type', () => {
  const result = exportBibtex({ papers: [paper] });
  assert.match(result.bibtex, /author = \{Doe, Jane\}/);
  assert.match(result.bibtex, /doi = \{10\.1234\/example\}/);
  assert.match(result.bibtex, /^@misc/);
  assert.doesNotMatch(result.bibtex, /journal =|booktitle =/);
  const normalized = exportBibtex([{ ...paper, identifiers: { doi: '  https://doi.org/10.1234/EXAMPLE  ' } }]);
  assert.match(normalized.bibtex, /doi = \{10\.1234\/example\}/);
});
test('unknown authors and year remain missing and produce warnings', () => {
  const result = exportBibtex({ papers: [{ id: 'P1', title: 'Known title', year: null, identifiers: {} }] });
  assert.doesNotMatch(result.bibtex, /author =|year =/);
  assert.ok(result.warnings.some(warning => warning.includes('authors not supplied')));
  assert.ok(result.warnings.some(warning => warning.includes('year unverified')));
});
test('TeX control text in a source title is escaped as data', () => {
  const result = exportBibtex({ papers: [{ ...paper, title: 'A } \\input{private} & 50% $x_1$' }] });
  assert.doesNotMatch(result.bibtex, /\\input\{/);
  assert.ok(result.bibtex.includes('\\textbackslash{}input\\{private\\}'));
  assert.ok(result.bibtex.includes('\\& 50\\% \\$x\\_1\\$'));
});
test('duplicate identities export once and conflicting metadata are rejected visibly', () => {
  const second = { ...paper, id: 'P2' };
  const result = exportBibtex({ papers: [paper, second] });
  assert.equal(result.exported_count, 1);
  assert.equal(result.keys.P2, result.keys[paper.id]);
  assert.ok(result.warnings.some(warning => warning.includes('duplicate identity')));
  assert.throws(() => exportBibtex({ papers: [paper, { ...second, title: 'Conflicting title' }] }), /Conflicting metadata/);
});
test('unsafe citation keys, URL credentials and repeated IDs do not enter bibliography output', () => {
  assert.throws(() => exportBibtex({ papers: [{ ...paper, citation_key: 'a}\n\\input{x}' }] }), /Unsafe/);
  assert.throws(() => exportBibtex({ papers: [{ ...paper, url: 'https://name:secret@example.org/' }] }), /Invalid source URL/);
  assert.throws(() => exportBibtex({ papers: [paper, paper] }), /Duplicate paper ID/);
});
test('all duplicate records are validated before identity consolidation', () => {
  assert.throws(() => exportBibtex({ papers: [paper, { ...paper, id: 'P2', authors: 2 }] }), /authors must be an array/);
  assert.throws(() => exportBibtex({ papers: [paper, { ...paper, id: 'P2', citation_key: 'bad}\\input{x}' }] }), /Unsafe citation_key/);
});
test('compatible supplied metadata fills unknown fields without changing source records', () => {
  const first = { ...paper, year: null, authors: [] };
  const input = { papers: [first, { ...paper, id: 'P2' }] };
  const original = structuredClone(input);
  const result = exportBibtex(input);
  assert.equal(result.exported_count, 1);
  assert.match(result.bibtex, /year = \{2024\}/);
  assert.match(result.bibtex, /author = \{Doe, Jane\}/);
  assert.deepEqual(input, original);
});
test('conflicting authors or identifiers require source resolution before export', () => {
  assert.throws(() => exportBibtex({ papers: [paper, { ...paper, id: 'P2', authors: ['Another Person'] }] }), /Conflicting authors/);
  const first = { ...paper, identifiers: { ...paper.identifiers, arxiv: '2401.00001v1' } };
  const second = { ...paper, id: 'P2', identifiers: { ...paper.identifiers, arxiv: '2401.00001v2' } };
  assert.throws(() => exportBibtex({ papers: [first, second] }), /Conflicting identifier/);
});
test('shared identifier aliases combine DOI-only and arXiv-only records, including a later bridge', () => {
  const records = [
    { ...paper, id: 'DOI-only' },
    { ...paper, id: 'arXiv-only', identifiers: { arxiv: '2401.00001v1' } },
    { ...paper, id: 'bridge', identifiers: { doi: 'https://doi.org/10.1234/EXAMPLE', arxiv: '2401.00001v1' } },
  ];
  const original = structuredClone(records);
  const result = exportBibtex(records);
  assert.equal(result.exported_count, 1);
  assert.equal(result.keys['DOI-only'], result.keys['arXiv-only']);
  assert.equal(result.keys.bridge, result.keys['DOI-only']);
  assert.match(result.bibtex, /eprint = \{2401\.00001v1\}/);
  assert.deepEqual(records, original);
  assert.equal(exportBibtex([records[2], records[1], records[0]]).exported_count, 1);
});
test('identity bridges cannot conceal conflicting DOI, title or source version records', () => {
  const arxiv = '2401.00001v1';
  assert.throws(() => exportBibtex([
    { ...paper, id: 'left', identifiers: { ...paper.identifiers, arxiv } },
    { ...paper, id: 'right', identifiers: { doi: '10.1234/another', arxiv } },
  ]), /Conflicting identifier doi/);
  assert.throws(() => exportBibtex([
    { ...paper, id: 'left', version: 'v1' },
    { ...paper, id: 'right', version: 'v2' },
  ]), /Conflicting source versions/);
  assert.throws(() => exportBibtex([
    { ...paper, id: 'left' },
    { ...paper, id: 'right', title: 'Another title', identifiers: { arxiv } },
    { ...paper, id: 'bridge', identifiers: { ...paper.identifiers, arxiv } },
  ]), /Conflicting metadata/);
});
test('OpenReview identity is case-sensitive and a known version can fill an unknown source version', () => {
  const records = [
    { ...paper, id: 'first', identifiers: { openreview: 'CaseSensitive' }, version: 'unknown' },
    { ...paper, id: 'same', identifiers: { openreview: 'CaseSensitive' }, version: 'revision-2' },
    { ...paper, id: 'other', identifiers: { openreview: 'casesensitive' }, version: 'revision-2' },
  ];
  const result = exportBibtex(records);
  assert.equal(result.exported_count, 2);
  assert.equal(result.keys.first, result.keys.same);
  assert.notEqual(result.keys.first, result.keys.other);
  assert.throws(() => exportBibtex([{ ...paper, version: 2 }]), /Invalid version/);
});
test('special valid paper IDs retain their citation key mapping', () => {
  const result = exportBibtex({ papers: [{ ...paper, id: '__proto__' }] });
  assert.ok(Object.hasOwn(result.keys, '__proto__'));
  assert.ok(JSON.parse(JSON.stringify(result.keys)).__proto__.startsWith('paper-'));
});
const script = fileURLToPath(new URL('../scripts/research_outputs.mjs', import.meta.url));
test('CLI accepts bounded UTF-8 notes from stdin and drafts a contract-valid unassessed record', () => {
  const notes = { question: 'A supplied question', decision: 'GO', reverse_search: 'Not executed.' };
  const result = spawnSync(process.execPath, [script, 'draft', '-', '--name', 'stdin-question'],
    { input: `\uFEFF${JSON.stringify(notes)}`, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  const dossier = JSON.parse(result.stdout);
  assert.equal(validateDossier(dossier).valid, true);
  assert.equal(dossier.project.notes.decision, 'GO');
  assert.deepEqual(dossier.searches, []);
  assert.deepEqual(dossier.reviews, []);
  assert.deepEqual(rankDossier(dossier).ranked, []);
});
test('CLI renders supplied notes, and bibliography stdout remains separate from warnings', () => {
  const card = spawnSync(process.execPath, [script, 'card', '-'],
    { input: JSON.stringify({ question: 'SYNTHETIC EXAMPLE: a supplied question.' }), encoding: 'utf8' });
  assert.equal(card.status, 0, card.stderr);
  assert.match(card.stdout, /SYNTHETIC EXAMPLE/);
  assert.equal(card.stderr, '');
  const result = spawnSync(process.execPath, [script, 'bibtex', '-'],
    { input: JSON.stringify({ papers: [paper] }), encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /^@misc/);
  assert.equal(JSON.parse(result.stderr).exported_count, 1);
  assert.doesNotMatch(result.stdout, /Exports supplied metadata/);
});
test('CLI rejects malformed or oversized input without emitting a partial dossier', () => {
  for (const input of ['{', 'x'.repeat(8 * 1024 * 1024 + 1)]) {
    const result = spawnSync(process.execPath, [script, 'draft', '-', '--name', 'bad-input'],
      { input, encoding: 'utf8' });
    assert.equal(result.status, 1);
    assert.equal(result.stdout, '');
    assert.ok(result.stderr.length > 0);
  }
});
