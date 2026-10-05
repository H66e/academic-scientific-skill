// Synthetic records only. These fixtures are not scientific or bibliographic evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm, mkdir, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import {
  createInitialDossier, validateDossier, canonicalStringify,
  fingerprintIdea, rankDossier, initProject,
} from '../scripts/research_audit.mjs';

const when = '2026-10-05T08:00:00Z';
const script = fileURLToPath(new URL('../scripts/research_audit.mjs', import.meta.url));

function fixture() {
  const d = createInitialDossier('synthetic-test');
  d.project.question = 'A synthetic question used to exercise record validation';
  d.project.constraints = { compute: 'Synthetic bounded resource; not a user commitment' };
  d.papers.push({ id: 'P1', title: 'Synthetic fixture, not a real paper', year: 2024,
    url: 'https://example.invalid/paper-1', identifiers: {}, version: 'fixture v1', accessed_at: when });
  d.searches.push({ id: 'S1', query: 'synthetic query', provider: 'fixture', searched_at: when,
    status: 'complete', scope: 'One fictional document', limitations: ['No real search performed'], result_paper_ids: ['P1'] });
  d.evidence.push({ id: 'E1', paper_id: 'P1', source_version: 'fixture v1', read_scope: 'section', locator: 'Synthetic section 3',
    observation: 'A fictional condition of a fictional method', polarity: 'supports' });
  d.ideas.push({ id: 'I1', version: 1, title: 'Synthetic candidate', question: 'Fictional boundary question',
    research_type: 'empirical', hypothesis: 'A fictional condition changes a fictional response',
    contribution: 'A conditional extension; this is not a real scientific claim', evidence_ids: ['E1'], search_ids: ['S1'],
    nearest_work: [{ paper_id: 'P1', evidence_ids: ['E1'], delta: 'Synthetic condition differs', decisive: true }],
    novelty: { status: 'distinct', reason: 'Fixture assertion only', coverage: 'One fictional document' },
    feasibility: { status: 'ready', reason: 'Fixture prerequisite met',
      dependencies: [{ name: 'Synthetic resource', mandatory: true, status: 'met', basis: 'Fixture observation' }] },
    validation: { status: 'specified', prediction: 'Synthetic response changes', falsifier: 'Response does not change',
      design: 'A synthetic paired comparison', metric: 'Synthetic response', resource_estimate: 'One fictional unit',
      stop_rule: 'Stop after one synthetic comparison' } });
  addReview(d, 'I1');
  return d;
}

function addReview(d, id, options = {}) {
  const idea = d.ideas.find(i => i.id === id);
  const r = { id: `R${d.reviews.length + 1}`, idea_id: id, idea_version: idea.version,
    basis_hash: fingerprintIdea(d, id), reviewed_at: when, kind: 'self', decision: 'GO',
    reason: 'Synthetic review for software tests only',
    scores: { scientific_value: 4, differentiation: 4, testability: 4 },
    score_reasons: { scientific_value: 'Fixture reason', differentiation: 'Fixture reason', testability: 'Fixture reason' },
    penalties: [], limitations: ['Fictional input; no scientific validation'], ...options };
  d.reviews.push(r);
  return r;
}

function refresh(d) {
  for (const r of d.reviews) {
    r.idea_version = d.ideas.find(i => i.id === r.idea_id).version;
    r.basis_hash = fingerprintIdea(d, r.idea_id);
  }
}

test('empty initialization is valid and yields zero survivors', () => {
  const d = createInitialDossier('empty-test');
  assert.equal(validateDossier(d).valid, true);
  const r = rankDossier(d);
  assert.deepEqual(r.ranked, []);
  assert.deepEqual(r.held, []);
  assert.deepEqual(r.killed, []);
});

test('a structurally supported current GO can be ranked', () => {
  const d = fixture();
  assert.deepEqual(validateDossier(d).errors, []);
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 1);
  assert.equal(r.ranked[0].idea_id, 'I1');
  assert.equal(r.ranked[0].score, 100);
});

test('configured weights alter the ordering and actual score', () => {
  const d = fixture();
  const other = structuredClone(d.ideas[0]); other.id = 'I2'; other.title = 'Second synthetic candidate';
  d.ideas.push(other); addReview(d, 'I2');
  d.reviews[0].scores = { scientific_value: 4, differentiation: 1, testability: 1 };
  d.reviews[1].scores = { scientific_value: 1, differentiation: 4, testability: 4 };
  d.config.ranking_weights = { scientific_value: 80, differentiation: 10, testability: 10 }; refresh(d);
  let r = rankDossier(d);
  assert.equal(r.ranked[0].idea_id, 'I1'); assert.equal(r.ranked[0].score, 85);
  d.config.ranking_weights = { scientific_value: 10, differentiation: 80, testability: 10 }; refresh(d);
  r = rankDossier(d);
  assert.equal(r.ranked[0].idea_id, 'I2'); assert.equal(r.ranked[0].score, 92.5);
});

test('nonnegative penalties reduce the score and excessive ones clamp at zero', () => {
  const d = fixture();
  d.reviews[0].penalties = [{ reason: 'Synthetic limitation', points: 10 }];
  assert.equal(rankDossier(d).ranked[0].score, 90);
  d.reviews[0].penalties[0].points = 150;
  assert.equal(rankDossier(d).ranked[0].score, 0);
});

test('negative penalties are invalid rather than increasing scores', () => {
  const d = fixture(); d.reviews[0].penalties = [{ reason: 'Bad sign', points: -10 }];
  assert.equal(validateDossier(d).valid, false);
});

test('explicit KILL cannot be outweighed by a perfect score', () => {
  const d = fixture(); d.reviews[0].decision = 'KILL';
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.killed[0].idea_id, 'I1');
});

test('explicit HOLD is retained despite perfect scores', () => {
  const d = fixture(); d.reviews[0].decision = 'HOLD';
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('unknown scoring information is not silently converted to zero', () => {
  const d = fixture(); d.reviews[0].scores.scientific_value = null;
  assert.equal(validateDossier(d).valid, true);
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('abstract-only decisive evidence does not establish GO', () => {
  const d = fixture(); d.evidence[0].read_scope = 'abstract'; refresh(d);
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('zero search hits do not establish novelty', () => {
  const d = fixture(); d.searches[0].result_paper_ids = []; refresh(d);
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('failed retrieval does not establish novelty', () => {
  const d = fixture(); d.searches[0].status = 'failed'; refresh(d);
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('unmarked nearest work is conservatively checked at section depth', () => {
  const d = fixture(); d.ideas[0].nearest_work[0].decisive = false;
  d.evidence[0].read_scope = 'abstract'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
});

test('unknown prerequisite calls for HOLD while failed prerequisite kills this framing', () => {
  const d = fixture(); d.ideas[0].feasibility.dependencies[0].status = 'unknown'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
  d.ideas[0].feasibility.dependencies[0].status = 'failed'; refresh(d);
  assert.equal(rankDossier(d).killed.length, 1);
});

test('pilot-only status is not permission for the full scientific validation', () => {
  const d = fixture(); d.ideas[0].feasibility.status = 'pilot_only'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
});

test('confirmed duplicate overrides a GO review', () => {
  const d = fixture(); d.ideas[0].novelty.status = 'duplicate'; refresh(d);
  assert.equal(rankDossier(d).killed.length, 1);
});

test('missing evaluation design prevents ranking', () => {
  const d = fixture(); d.ideas[0].validation.status = 'missing';
  d.ideas[0].validation.design = ''; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
});

test('an edited question invalidates the review without changing a manual version', () => {
  const d = fixture(); d.ideas[0].question = 'A substantively changed synthetic question';
  assert.equal(rankDossier(d).held.length, 1);
});

test('changed compute constraints invalidate the review', () => {
  const d = fixture(); d.project.constraints.compute = 'A different resource envelope';
  assert.equal(rankDossier(d).held.length, 1);
});

test('a new retrieval result invalidates the review', () => {
  const d = fixture(); d.searches[0].limitations.push('Newly discovered coverage limit');
  assert.equal(rankDossier(d).held.length, 1);
});

test('a changed source version invalidates the review', () => {
  const d = fixture(); d.papers[0].version = 'fixture v2';
  assert.equal(rankDossier(d).held.length, 1);
});

test('actual evidence version is retained and version corrections invalidate review', () => {
  const d = fixture(); d.papers[0].version = 'fixture v2';
  assert.equal(d.evidence[0].source_version, 'fixture v1');
  refresh(d); d.evidence[0].source_version = 'fixture v2';
  assert.equal(rankDossier(d).held.length, 1);
  delete d.evidence[0].source_version;
  assert.equal(validateDossier(d).valid, false);
});

test('new pilot evidence requires reassessment and is not automatically promoted', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'supported',
    artifacts: ['synthetic-results.csv'], summary: 'Fictional result', limitations: ['Synthetic only'] });
  assert.equal(validateDossier(d).valid, true);
  assert.equal(rankDossier(d).held.length, 1);
});

test('failed execution is retained separately from a contradicted hypothesis', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', idea_id: 'I1', idea_version: 1, kind: 'smoke', outcome: 'execution_failed',
    artifacts: ['synthetic-error.log'], summary: 'Synthetic import error', limitations: [] });
  assert.equal(validateDossier(d).valid, true);
  assert.equal(d.pilots[0].outcome, 'execution_failed');
  assert.equal(rankDossier(d).held.length, 1);
});

test('not-run is valid without fabricated artifacts', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'not_run',
    artifacts: [], summary: 'No execution took place', limitations: [] });
  assert.equal(validateDossier(d).valid, true);
});

test('old pilot versions can remain in history', () => {
  const d = fixture(); d.ideas[0].version = 2;
  d.pilots.push({ id: 'X1', idea_id: 'I1', idea_version: 1, kind: 'smoke', outcome: 'supported',
    artifacts: ['synthetic-smoke.log'], summary: 'Old fixture environment check', limitations: [] });
  refresh(d);
  assert.equal(validateDossier(d).valid, true);
});

test('a latest stale review does not fall back to an earlier favorable review', () => {
  const d = fixture();
  addReview(d, 'I1', { reviewed_at: '2026-10-05T09:00:00Z', basis_hash: '0'.repeat(64), decision: 'KILL' });
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('changing a previously killed framing calls for reassessment rather than a permanent ban', () => {
  const d = fixture(); d.ideas[0].novelty.status = 'duplicate';
  d.reviews[0].decision = 'KILL'; refresh(d);
  assert.equal(rankDossier(d).killed.length, 1);
  d.ideas[0].question = 'A revised question with a different scientific target';
  const r = rankDossier(d);
  assert.equal(r.killed.length, 0);
  assert.equal(r.held.length, 1);
});

test('JSON key order and history logging do not alter the fingerprint', () => {
  const d = fixture(); const h = fingerprintIdea(d, 'I1');
  d.history.push({ event: 'Synthetic archival note', applies_when: 'Synthetic only' });
  assert.equal(fingerprintIdea(d, 'I1'), h);
  assert.equal(canonicalStringify({ b: 2, a: 1 }), canonicalStringify({ a: 1, b: 2 }));
});

test('invalid references, scores, dates and weights are rejected', () => {
  const modifications = [
    d => d.evidence[0].paper_id = 'missing',
    d => d.ideas[0].nearest_work[0].evidence_ids = ['missing'],
    d => d.reviews[0].scores.testability = 5,
    d => d.reviews[0].scores.testability = 1.5,
    d => d.reviews[0].reviewed_at = '2026-10-05',
    d => d.config.ranking_weights = { scientific_value: 0, differentiation: 0, testability: 0 },
    d => d.config.ranking_weights.testability = -1,
    d => d.papers.push(structuredClone(d.papers[0])),
    d => d.papers[0].url = 'javascript:alert(1)',
    d => d.evidence[0].read_scope = 'pretended_full_read',
  ];
  for (const change of modifications) { const d = fixture(); change(d); assert.equal(validateDossier(d).valid, false); }
});

test('theoretical validation does not require an empirical benchmark or GPU', () => {
  const d = fixture(); d.project.research_type = 'theoretical'; d.project.constraints = {};
  d.ideas[0].research_type = 'theoretical';
  d.ideas[0].validation.metric = 'Discharge the proof obligation or produce a counterexample'; refresh(d);
  assert.equal(rankDossier(d).ranked.length, 1);
});

test('init rejects traversal and existing targets, and never overwrites a dossier', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-skill-test-'));
  try {
    for (const name of ['../escape', '..', '.', 'a/b', 'a\\b', 'C:\\escape', '-bad', 'a'.repeat(65)]) {
      await assert.rejects(() => initProject(root, name));
    }
    const result = await initProject(root, 'valid-project');
    assert.equal(path.dirname(result.project_dir), root);
    const before = await readFile(result.dossier_path, 'utf8');
    await assert.rejects(() => initProject(root, 'valid-project'));
    assert.equal(await readFile(result.dossier_path, 'utf8'), before);
    assert.equal(validateDossier(JSON.parse(before)).valid, true);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('init requires an existing root directory', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-skill-test-'));
  try { await assert.rejects(() => initProject(path.join(root, 'not-created'), 'new-project')); }
  finally { await rm(root, { recursive: true, force: true }); }
});

test('init refuses a directory junction or symbolic link as its root', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-skill-test-'));
  try {
    const real = path.join(root, 'real'); const link = path.join(root, 'link');
    await mkdir(real); await symlink(real, link, process.platform === 'win32' ? 'junction' : 'dir');
    await assert.rejects(() => initProject(link, 'new-project'));
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('CLI validates and ranks a dossier without changing it', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-skill-test-'));
  try {
    const file = path.join(root, 'dossier.json');
    const content = JSON.stringify(fixture(), null, 2); await writeFile(file, content);
    for (const command of ['validate', 'rank', 'fingerprint']) {
      const args = command === 'fingerprint' ? [command, file, 'I1'] : [command, file];
      const r = spawnSync(process.execPath, [script, ...args], { encoding: 'utf8' });
      assert.equal(r.status, 0, r.stderr);
      if (command !== 'fingerprint') JSON.parse(r.stdout);
      assert.equal(await readFile(file, 'utf8'), content);
    }
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('invalid CLI input produces a nonzero exit code', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-skill-test-'));
  try {
    const file = path.join(root, 'dossier.json'); await writeFile(file, '{invalid JSON');
    const r = spawnSync(process.execPath, [script, 'validate', file], { encoding: 'utf8' });
    assert.notEqual(r.status, 0);
  } finally { await rm(root, { recursive: true, force: true }); }
});
