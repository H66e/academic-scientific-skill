// Synthetic records only. These fixtures are not scientific or bibliographic evidence.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm, mkdir, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import {
  createInitialDossier, validateDossier, canonicalStringify,
  fingerprintIdea, rankingConfigHash, rankDossier, migrateDossier, initProject,
  DECISION_CONTRACT_VERSION, createReviewReceipt, verifyIndependentReceipts, effectiveResultState,
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
    evidence_links: [{ evidence_id: 'E1', role: 'motivation', target: 'problem',
      claim: 'A fictional condition warrants a bounded comparison', relation: 'supports', decision_relevant: true }],
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
    decision_contract_version: DECISION_CONTRACT_VERSION,
    review_basis_hash: fingerprintIdea(d, id), reviewed_at: when, kind: 'self', decision: 'GO',
    decision_scope: 'scientific_framing', recommended_stage: 'pilot',
    decision_basis: { type: 'advance', evidence_ids: ['E1'], pilot_ids: [], dependency_names: [],
      constraint_keys: [], explanation: 'Synthetic linked evidence warrants this bounded comparison' },
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
    r.review_basis_hash = fingerprintIdea(d, r.idea_id);
  }
}

async function sealReceipt(root, review, receipt = createReviewReceipt(review)) {
  const bytes = Buffer.from(`${JSON.stringify(receipt, null, 2)}\n`, 'utf8');
  await writeFile(path.join(root, review.artifact), bytes);
  review.artifact_sha256 = createHash('sha256').update(bytes).digest('hex');
}

function independentReview(d, options = {}) {
  return addReview(d, 'I1', { kind: 'independent', author_context: 'Synthetic author context',
    evaluator_context: 'Synthetic evaluator context', artifact: 'review.json', recommended_stage: 'full_validation',
    reviewed_at: '2026-10-05T09:00:00Z', ...options });
}

function decide(d, decision, type, basis = {}) {
  const r = d.reviews[0];
  r.decision = decision;
  r.decision_basis = { type, evidence_ids: [], pilot_ids: [], dependency_names: [], constraint_keys: [],
    explanation: 'Synthetic decision basis for software validation only', ...basis };
  refresh(d);
  return r;
}

function duplicate(d = fixture()) {
  d.ideas[0].novelty.status = 'duplicate';
  d.ideas[0].evidence_links[0] = { evidence_id: 'E1', role: 'nearest_work', target: 'nearest_work',
    claim: 'The synthetic contribution is covered by this nearest work', relation: 'supports', decision_relevant: true };
  decide(d, 'KILL', 'duplicate', { evidence_ids: ['E1'] });
  return d;
}

function addUnrelated(d) {
  const p = { ...structuredClone(d.papers[0]), id: 'P2', url: 'https://example.invalid/paper-2' };
  d.papers.push(p);
  d.searches.push({ ...structuredClone(d.searches[0]), id: 'S2', result_paper_ids: ['P2'] });
  d.evidence.push({ ...structuredClone(d.evidence[0]), id: 'E2', paper_id: 'P2' });
  const i = structuredClone(d.ideas[0]);
  Object.assign(i, { id: 'I2', evidence_ids: ['E2'], search_ids: ['S2'],
    evidence_links: [{ ...i.evidence_links[0], evidence_id: 'E2' }],
    nearest_work: [{ ...i.nearest_work[0], paper_id: 'P2', evidence_ids: ['E2'] }] });
  d.ideas.push(i);
  d.pilots.push({ id: 'X2', run_id: 'X2', affected_claims: [], idea_id: 'I2', idea_version: 1, kind: 'scientific', outcome: 'inconclusive',
    artifacts: ['synthetic-i2.csv'], summary: 'An unrelated synthetic result', limitations: [] });
  d.screening.push({ id: 'SC2', search_id: 'S2', paper_id: 'P2', idea_ids: ['I2'],
    stage: 'full_text', decision: 'include', reason: 'Synthetic relevance to I2', screened_at: when });
  return d;
}

function v1Fixture() {
  const d = fixture();
  d.schema_version = 1;
  delete d.decision_contract_version;
  delete d.screening;
  for (const idea of d.ideas) delete idea.evidence_links;
  for (const r of d.reviews) {
    for (const key of ['review_basis_hash', 'decision_scope', 'recommended_stage', 'decision_basis', 'decision_contract_version']) delete r[key];
    r.basis_hash = '0'.repeat(64);
  }
  for (const r of d.reviews) r.basis_hash = fingerprintIdea(d, r.idea_id);
  return d;
}

function result(d, id, options = {}) {
  const record = { id, run_id: id, idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'contradicted',
    artifacts: ['synthetic-observation.csv'], summary: 'SYNTHETIC lifecycle fixture, no actual experiment',
    limitations: ['No scientific evidence'], affected_claims: [], actor: 'model', trust: 'T2', ...options };
  d.pilots.push(record);
  return record;
}

function invalidate(d, record, options = {}) {
  const entry = { id: `INV-${d.result_invalidations.length + 1}`, run_id: record.run_id,
    idea_id: record.idea_id, idea_version: record.idea_version, result_id: record.id,
    reason: 'Synthetic control invalidity, not refutation', recorded_at: when, actor: 'user', trust: 'T1', ...options };
  d.result_invalidations.push(entry);
  return entry;
}

test('causal same-run correction removes a blocker but independent support does not', () => {
  const d = fixture(); result(d, 'A'); result(d, 'B', { outcome: 'supported' });
  assert.equal(effectiveResultState(d, 'I1').contradiction_blocker, true);
  refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
  const priorHash = d.reviews[0].review_basis_hash;
  result(d, 'A2', { run_id: 'A', supersedes: 'A', reason: 'Explicit changed classification', outcome: 'inconclusive' });
  assert.equal(effectiveResultState(d, 'I1').requires_hold, false);
  assert.notEqual(fingerprintIdea(d, 'I1'), priorHash);
  assert.match(rankDossier(d).held[0].reasons.join(' '), /stale/);
  refresh(d);
  assert.equal(rankDossier(d).ranked.length, 1);
});

test('multiple supported terminal heads warn and HOLD without contract invalidity', () => {
  const d = fixture(); result(d, 'A', { outcome: 'supported' });
  result(d, 'B', { run_id: 'A', outcome: 'supported' });
  assert.equal(validateDossier(d).valid, true);
  assert.match(validateDossier(d).warnings.join(' '), /ambiguous run A/);
  const state = effectiveResultState(d, 'I1');
  assert.equal(state.contradiction_blocker, false);
  assert.equal(state.ambiguity_blocker, true);
  refresh(d);
  assert.match(rankDossier(d).held[0].reasons.join(' '), /multiple effective/);
});

test('replacement ancestry never revives and effective state ignores record order and timestamps', () => {
  const d = fixture(); result(d, 'A', { recorded_at: '2026-10-07T00:00:00Z' });
  result(d, 'B', { run_id: 'A', supersedes: 'A', reason: 'First correction', outcome: 'supported', recorded_at: when });
  result(d, 'C', { run_id: 'A', supersedes: 'B', reason: 'Second correction', outcome: 'inconclusive' });
  const state = effectiveResultState(d, 'I1'), hash = fingerprintIdea(d, 'I1');
  assert.deepEqual(state.runs[0].head_ids, ['C']);
  assert.equal(state.requires_hold, false);
  for (const order of [[2, 0, 1], [1, 2, 0], [0, 2, 1]]) {
    const copy = structuredClone(d); copy.pilots = order.map(index => d.pilots[index]);
    assert.deepEqual(effectiveResultState(copy, 'I1'), state);
    assert.equal(fingerprintIdea(copy, 'I1'), hash);
  }
});

test('whole-run user invalidation survives later classification and always stales reviews', () => {
  const d = fixture(), first = result(d, 'A'); refresh(d);
  const hash = fingerprintIdea(d, 'I1');
  invalidate(d, first);
  assert.notEqual(fingerprintIdea(d, 'I1'), hash);
  assert.equal(effectiveResultState(d, 'I1').requires_hold, false);
  assert.match(rankDossier(d).held[0].reasons.join(' '), /stale/);
  result(d, 'B', { run_id: 'A', supersedes: 'A', reason: 'New interpretation of retired run' });
  assert.equal(effectiveResultState(d, 'I1').runs[0].eligible, false);
  assert.deepEqual(effectiveResultState(d, 'I1').scientific_refutation_ids, []);
  refresh(d); assert.equal(rankDossier(d).ranked.length, 1);
  result(d, 'NEW-ATTEMPT'); refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
});

test('scientific KILL and GO share effective result state and reject retired or ambiguous basis', () => {
  for (const scenario of ['superseded', 'invalidated', 'ambiguous']) {
    const d = fixture(), first = result(d, 'A');
    if (scenario === 'superseded') result(d, 'B', { run_id: 'A', supersedes: 'A', reason: 'Changed interpretation', outcome: 'supported' });
    if (scenario === 'invalidated') invalidate(d, first);
    if (scenario === 'ambiguous') result(d, 'B', { run_id: 'A', outcome: 'supported' });
    decide(d, 'KILL', 'scientific_refutation', { pilot_ids: ['A'] });
    assert.equal(rankDossier(d).killed.length, 0, scenario);
    assert.equal(rankDossier(d).held.length, 1, scenario);
  }
  const d = fixture(); result(d, 'A');
  decide(d, 'KILL', 'scientific_refutation', { pilot_ids: ['A'] });
  assert.equal(rankDossier(d).killed.length, 1);
});

test('transition references, cycles, provenance and run identity are contract-invalid', () => {
  for (const modify of [
    d => result(d, 'B', { run_id: 'A', supersedes: 'missing', reason: 'Correction' }),
    d => result(d, 'B', { run_id: 'B', supersedes: 'A', reason: 'Cross-run' }),
    d => result(d, 'B', { run_id: 'A', supersedes: 'B', reason: 'Self-reference' }),
    d => { d.pilots[0].supersedes = 'B'; d.pilots[0].reason = 'Cycle'; result(d, 'B', { run_id: 'A', supersedes: 'A', reason: 'Cycle' }); },
    d => result(d, 'B', { run_id: 'A', idea_version: 2 }),
    d => { const other = structuredClone(d.ideas[0]); other.id = 'I2'; d.ideas.push(other); result(d, 'B', { run_id: 'A', idea_id: 'I2', supersedes: 'A', reason: 'Cross-candidate' }); },
    d => result(d, 'B', { run_id: 'A', supersedes: 'A', reason: ' ' }),
    d => invalidate(d, d.pilots[0], { actor: 'model', trust: 'T2' }),
    d => invalidate(d, d.pilots[0], { result_id: 'missing' }),
    d => invalidate(d, d.pilots[0], { run_id: 'wrong-run' }),
    d => invalidate(d, d.pilots[0], { id: 'A' }),
    d => result(d, 'B', { actor: 'model', trust: 'T1' }),
  ]) {
    const d = fixture(); result(d, 'A'); modify(d);
    assert.equal(validateDossier(d).valid, false);
    assert.throws(() => effectiveResultState(d, 'I1'), /Invalid dossier/);
  }
});

test('explanatory claim references can degrade visibly without weakening the result gate', () => {
  const d = fixture();
  d.ideas[0].claims = [{ id: 'H1', candidate_version: 1 }, { id: 'H2', candidate_version: 1 }];
  const observed = result(d, 'A');
  for (const claim_id of ['H1', 'H2', 'H3']) {
    observed.affected_claims = [{ claim_id, reason: 'Declared explanation only' }];
    const checked = validateDossier(d), state = effectiveResultState(d, 'I1');
    assert.equal(checked.valid, true);
    assert.equal(state.contradiction_blocker, true);
    assert.equal(state.affected_claims_degraded, claim_id === 'H3');
    refresh(d); assert.equal(rankDossier(d).held.length, 1);
  }
  for (const affected_claims of ['H1', [null], [{ claim_id: 'H1' }], [{ claim_id: 'H1', reason: ' ' }], [{ claim_id: 'H1', reason: 'Extra key', extra: true }]]) {
    observed.affected_claims = affected_claims;
    assert.equal(validateDossier(d).valid, false);
  }
});

test('v2 migration materializes independent run IDs, preserves observations and archives reviews', () => {
  const d = fixture(); result(d, 'A'); result(d, 'B', { outcome: 'supported' });
  d.schema_version = 2; d.decision_contract_version = 2; delete d.result_invalidations;
  for (const pilot of d.pilots) { delete pilot.run_id; delete pilot.affected_claims; }
  for (const review of d.reviews) review.decision_contract_version = 2;
  refresh(d);
  const before = structuredClone(d), migrated = migrateDossier(d);
  assert.deepEqual(d, before);
  assert.equal(validateDossier(d).valid, true); assert.equal(rankDossier(d).ranked.length, 0);
  assert.equal(migrated.schema_version, 3); assert.deepEqual(migrated.result_invalidations, []);
  assert.deepEqual(migrated.pilots, before.pilots.map(pilot => ({ ...pilot, run_id: pilot.id, affected_claims: [] })));
  assert.deepEqual(migrated.history[0].original_review, before.reviews[0]);
  assert.deepEqual(migrated.reviews, []);
  assert.equal(effectiveResultState(migrated, 'I1').contradiction_blocker, true);
  addReview(migrated, 'I1');
  assert.equal(rankDossier(migrated).held.length, 1);
});

test('migration rejects ignored legacy withdrawals instead of silently activating or deleting them', () => {
  for (const legacyVersion of [1, 2]) {
    for (const withdrawals of [
      [{ id: 'INV', run_id: 'A', idea_id: 'I1', idea_version: 1, result_id: 'A', reason: 'Previously ignored extra data',
        recorded_at: when, actor: 'user', trust: 'T1' }],
      'Previously ignored extra field', null,
    ]) {
      const d = legacyVersion === 1 ? v1Fixture() : fixture();
      result(d, 'A'); delete d.pilots[0].run_id; delete d.pilots[0].affected_claims;
      d.schema_version = legacyVersion;
      if (legacyVersion === 2) d.decision_contract_version = 2;
      d.result_invalidations = withdrawals;
      const original = structuredClone(d);
      assert.equal(validateDossier(d).valid, true);
      assert.throws(() => migrateDossier(d), /uninterpreted result_invalidations/);
      assert.deepEqual(d, original);
    }
  }
});

test('classification history and invalidations enter only their candidate review closure', () => {
  const d = fixture(); addUnrelated(d); refresh(d);
  const unchanged = fingerprintIdea(d, 'I1');
  invalidate(d, d.pilots[0]);
  assert.equal(fingerprintIdea(d, 'I1'), unchanged);
  const first = result(d, 'A');
  result(d, 'B', { run_id: 'A', supersedes: 'A', reason: 'Corrected classification', outcome: 'supported' });
  refresh(d);
  const before = fingerprintIdea(d, 'I1');
  first.summary += ' Additional historical scientific context';
  assert.notEqual(fingerprintIdea(d, 'I1'), before);
  refresh(d); invalidate(d, first);
  assert.match(rankDossier(d).held[0].reasons.join(' '), /stale/);
});

test('v3 lifecycle fields are mandatory without blocking readable v2 inputs', () => {
  const d = fixture(); result(d, 'A'); delete d.pilots[0].run_id;
  assert.equal(validateDossier(d).valid, false);
  d.schema_version = 2; delete d.result_invalidations; d.decision_contract_version = 2;
  d.ideas[0].claims = 'An arbitrary old extra field';
  assert.equal(validateDossier(d).valid, true);
  assert.throws(() => effectiveResultState(d, 'I1'), /schema v3 migration/);
  const malformed = fixture(); malformed.result_invalidations = [null, { id: 'bad' }];
  assert.doesNotThrow(() => validateDossier(malformed));
  assert.equal(validateDossier(malformed).valid, false);
});

test('empty initialization is valid and yields zero survivors', () => {
  const d = createInitialDossier('empty-test');
  assert.equal(d.schema_version, 3);
  assert.deepEqual(d.result_invalidations, []);
  assert.deepEqual(d.screening, []);
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

test('an evidence-backed current KILL cannot be outweighed by a perfect score', () => {
  const d = duplicate();
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.killed[0].idea_id, 'I1');
});

test('explicit HOLD is retained despite perfect scores', () => {
  const d = fixture(); decide(d, 'HOLD', 'insufficient');
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

test('unknown or failed prerequisite needs reassessment rather than automatic KILL', () => {
  const d = fixture(); d.ideas[0].feasibility.dependencies[0].status = 'unknown'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
  d.ideas[0].feasibility.dependencies[0].status = 'failed'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
});

test('pilot-only status is not permission for the full scientific validation', () => {
  const d = fixture(); d.ideas[0].feasibility.status = 'pilot_only'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
});

test('a duplicate label with a current GO review calls for HOLD', () => {
  const d = fixture(); d.ideas[0].novelty.status = 'duplicate'; refresh(d);
  assert.equal(rankDossier(d).held.length, 1);
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
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'supported',
    artifacts: ['synthetic-results.csv'], summary: 'Fictional result', limitations: ['Synthetic only'] });
  assert.equal(validateDossier(d).valid, true);
  assert.equal(rankDossier(d).held.length, 1);
});

test('failed execution is retained separately from a contradicted hypothesis', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'smoke', outcome: 'execution_failed',
    artifacts: ['synthetic-error.log'], summary: 'Synthetic import error', limitations: [] });
  assert.equal(validateDossier(d).valid, true);
  assert.equal(d.pilots[0].outcome, 'execution_failed');
  assert.equal(rankDossier(d).held.length, 1);
});

test('not-run is valid without fabricated artifacts', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'not_run',
    artifacts: [], summary: 'No execution took place', limitations: [] });
  assert.equal(validateDossier(d).valid, true);
});

test('old pilot versions can remain in history', () => {
  const d = fixture(); d.ideas[0].version = 2;
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'smoke', outcome: 'supported',
    artifacts: ['synthetic-smoke.log'], summary: 'Old fixture environment check', limitations: [] });
  refresh(d);
  assert.equal(validateDossier(d).valid, true);
});

test('a latest stale review does not fall back to an earlier favorable review', () => {
  const d = fixture();
  addReview(d, 'I1', { reviewed_at: '2026-10-05T09:00:00Z', review_basis_hash: '0'.repeat(64), decision: 'KILL',
    decision_basis: { type: 'insufficient', evidence_ids: [], pilot_ids: [], dependency_names: [], constraint_keys: [],
      explanation: 'Synthetic stale review, not a valid reason to kill' } });
  const r = rankDossier(d);
  assert.equal(r.ranked.length, 0); assert.equal(r.held.length, 1);
});

test('changing a previously killed framing calls for reassessment rather than a permanent ban', () => {
  const d = duplicate();
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

test('unrelated papers, retrievals, evidence, pilots and screenings do not stale another idea', () => {
  const d = fixture(); const hash = fingerprintIdea(d, 'I1');
  addUnrelated(d);
  assert.equal(validateDossier(d).valid, true);
  assert.equal(fingerprintIdea(d, 'I1'), hash);
  assert.equal(rankDossier(d).ranked[0].idea_id, 'I1');
  d.evidence[1].observation = 'Revised observation for I2';
  d.searches[1].limitations.push('Different coverage boundary for I2');
  d.papers[1].version = 'fixture v3';
  d.pilots[0].summary = 'Updated unrelated scientific result';
  d.screening[0].decision = 'uncertain';
  assert.equal(fingerprintIdea(d, 'I1'), hash);
});

test('ranking preferences change ordering without staling scientific reviews', () => {
  const d = fixture(); addUnrelated(d);
  addReview(d, 'I2', { decision_basis: { type: 'advance', evidence_ids: ['E2'], pilot_ids: [],
    dependency_names: [], constraint_keys: [], explanation: 'Synthetic I2 basis' } });
  d.reviews[0].scores = { scientific_value: 4, differentiation: 1, testability: 1 };
  d.reviews[1].scores = { scientific_value: 1, differentiation: 4, testability: 4 };
  const scientific = fingerprintIdea(d, 'I1'); const ranking = rankingConfigHash(d);
  d.config.ranking_weights = { scientific_value: 80, differentiation: 10, testability: 10 };
  assert.equal(fingerprintIdea(d, 'I1'), scientific);
  assert.notEqual(rankingConfigHash(d), ranking);
  assert.equal(rankDossier(d).ranked[0].idea_id, 'I1');
  d.config.ranking_weights = { scientific_value: 10, differentiation: 80, testability: 10 };
  const output = rankDossier(d);
  assert.equal(output.ranked[0].idea_id, 'I2');
  assert.equal(output.held.length, 0);
  assert.equal(output.ranking_config_hash, rankingConfigHash(d));
});

test('access and screening record timestamps do not change the scientific basis', () => {
  const d = fixture();
  d.screening.push({ id: 'SC1', search_id: 'S1', paper_id: 'P1', idea_ids: ['I1'],
    stage: 'full_text', decision: 'include', reason: 'Synthetic candidate relevance', screened_at: when });
  refresh(d); const hash = fingerprintIdea(d, 'I1');
  d.papers[0].accessed_at = '2026-10-06T08:00:00Z';
  d.screening[0].screened_at = '2026-10-06T08:00:00Z';
  assert.equal(fingerprintIdea(d, 'I1'), hash);
  assert.equal(rankDossier(d).ranked.length, 1);
});

test('retrieval execution dates remain part of the scientific coverage boundary', () => {
  const d = fixture(); const hash = fingerprintIdea(d, 'I1');
  d.searches[0].searched_at = '2026-10-06T08:00:00Z';
  assert.notEqual(fingerprintIdea(d, 'I1'), hash);
  assert.equal(rankDossier(d).held.length, 1);
});

test('linked search results include paper versions even when not marked nearest work', () => {
  const d = fixture(); addUnrelated(d);
  d.searches[0].result_paper_ids.push('P2'); refresh(d);
  d.papers[1].version = 'fixture v2';
  assert.equal(rankDossier(d).held.find(r => r.idea_id === 'I1').decision, 'HOLD');
});

test('evidence-linked papers enter the closure without a search or nearest-work link', () => {
  const d = fixture(); addUnrelated(d);
  d.ideas[0].evidence_ids.push('E2');
  d.ideas[0].evidence_links.push({ evidence_id: 'E2', role: 'context', target: 'problem',
    claim: 'Additional synthetic problem context', relation: 'context', decision_relevant: false });
  refresh(d); const hash = fingerprintIdea(d, 'I1');
  d.papers[1].version = 'fixture v2';
  assert.notEqual(fingerprintIdea(d, 'I1'), hash);
});

test('screening-linked retrieval and papers enter only the associated candidate closure', () => {
  const d = fixture(); addUnrelated(d);
  const before = fingerprintIdea(d, 'I1');
  d.screening[0].idea_ids.push('I1');
  assert.notEqual(fingerprintIdea(d, 'I1'), before);
  refresh(d); const linked = fingerprintIdea(d, 'I1');
  d.searches[1].query = 'A changed screening-associated retrieval';
  assert.notEqual(fingerprintIdea(d, 'I1'), linked);
});

test('collection ordering does not alter the scoped fingerprint', () => {
  const d = fixture(); addUnrelated(d);
  const before = fingerprintIdea(d, 'I1');
  for (const name of ['papers', 'searches', 'evidence', 'ideas', 'screening', 'pilots']) d[name].reverse();
  assert.equal(fingerprintIdea(d, 'I1'), before);
});

test('project labels do not replace scientific inputs as a reason for reassessment', () => {
  const d = fixture(); const hash = fingerprintIdea(d, 'I1');
  d.project.id = 'renamed-synthetic-project';
  assert.equal(fingerprintIdea(d, 'I1'), hash);
  assert.equal(rankDossier(d).ranked.length, 1);
});

test('candidate-associated screening decisions stale reviews while preserving actual search results', () => {
  const d = fixture();
  d.screening.push({ id: 'SC1', search_id: 'S1', paper_id: 'P1', idea_ids: ['I1'], stage: 'title_abstract',
    decision: 'include', reason: 'Synthetic initial relevance', screened_at: when });
  refresh(d); const results = structuredClone(d.searches[0].result_paper_ids);
  d.screening[0].decision = 'uncertain'; d.screening[0].reason = 'Synthetic unresolved inclusion condition';
  assert.deepEqual(d.searches[0].result_paper_ids, results);
  assert.equal(rankDossier(d).held.length, 1);
});

test('sharing an unchanged screening record with another candidate does not stale its original candidate', () => {
  const d = fixture(); addUnrelated(d);
  d.screening.push({ id: 'SC1', search_id: 'S1', paper_id: 'P1', idea_ids: ['I1'], stage: 'full_text',
    decision: 'include', reason: 'Synthetic relevance shared between candidates', screened_at: when });
  refresh(d); const hash = fingerprintIdea(d, 'I1');
  d.screening.find(s => s.id === 'SC1').idea_ids.push('I2');
  assert.equal(fingerprintIdea(d, 'I1'), hash);
  assert.equal(rankDossier(d).ranked.find(r => r.idea_id === 'I1').decision, 'GO');
});

test('nearest-work differences and candidate evidence-link meaning stale prior reviews', () => {
  for (const update of [
    d => d.ideas[0].nearest_work[0].delta = 'A new technical difference',
    d => d.ideas[0].evidence_links[0].claim = 'A different claim from the same source',
    d => d.evidence[0].observation = 'An updated source observation',
  ]) {
    const d = fixture(); update(d);
    assert.equal(rankDossier(d).held.length, 1);
  }
});

test('duplicate or blocked labels without a current review cannot KILL', () => {
  for (const modify of [
    d => d.ideas[0].novelty.status = 'duplicate',
    d => d.ideas[0].feasibility.status = 'blocked',
    d => d.ideas[0].feasibility.dependencies[0].status = 'failed',
  ]) {
    const d = fixture(); d.reviews = []; modify(d);
    const result = rankDossier(d);
    assert.equal(result.killed.length, 0);
    assert.equal(result.held.length, 1);
  }
});

test('a bare current KILL without a matching decision basis remains HOLD', () => {
  const d = fixture(); decide(d, 'KILL', 'insufficient');
  assert.equal(rankDossier(d).killed.length, 0);
  assert.equal(rankDossier(d).held.length, 1);
});

test('duplicate KILL needs deep decisive evidence, not an abstract or unchecked nearest claim', () => {
  for (const modify of [
    d => d.evidence[0].read_scope = 'abstract',
    d => d.ideas[0].nearest_work[0].decisive = false,
    d => d.reviews[0].decision_basis.evidence_ids = [],
  ]) {
    const d = duplicate(); modify(d); refresh(d);
    assert.equal(rankDossier(d).killed.length, 0);
    assert.equal(rankDossier(d).held.length, 1);
  }
});

test('constraints KILL is scoped and requires confirmed facts plus an actual failed prerequisite', () => {
  const d = fixture();
  d.project.constraints.compute = { status: 'confirmed', value: 'No synthetic device available', source: 'Synthetic user confirmation, fixture only' };
  d.ideas[0].feasibility.status = 'blocked';
  d.ideas[0].feasibility.dependencies[0].status = 'failed';
  d.ideas[0].feasibility.dependencies[0].constraint_keys = ['compute'];
  const r = decide(d, 'KILL', 'constraints', { constraint_keys: ['compute'], dependency_names: ['Synthetic resource'] });
  r.decision_scope = 'current_constraints';
  const result = rankDossier(d);
  assert.equal(result.killed.length, 1);
  assert.equal(result.killed[0].decision_scope, 'current_constraints');
  assert.equal(result.ranked.length, 0);
  r.decision_scope = 'scientific_framing';
  assert.equal(rankDossier(d).held.length, 1);
});

test('unconfirmed resource claims or an unfailed dependency cannot justify constraints KILL', () => {
  for (const modify of [
    d => d.project.constraints.compute = 'An unconfirmed resource claim',
    d => d.ideas[0].feasibility.dependencies[0].status = 'met',
    d => d.ideas[0].feasibility.dependencies[0].mandatory = false,
    d => d.reviews[0].decision_basis.constraint_keys = [],
  ]) {
    const d = fixture();
    d.project.constraints.compute = { status: 'confirmed', value: 'Synthetic unavailable resource', source: 'Synthetic user record' };
    d.ideas[0].feasibility.dependencies[0].status = 'failed';
    d.ideas[0].feasibility.dependencies[0].constraint_keys = ['compute'];
    decide(d, 'KILL', 'constraints', { constraint_keys: ['compute'], dependency_names: ['Synthetic resource'] }).decision_scope = 'current_constraints';
    modify(d);
    if (validateDossier(d).valid) {
      refresh(d); assert.equal(rankDossier(d).killed.length, 0);
    } else {
      assert.equal(validateDossier(d).valid, false);
    }
  }
});

test('constraints KILL rejects empty facts while retaining meaningful zero and false values', () => {
  for (const value of [{}, [], [''], { resource: null }, { resource: { devices: [] } }, 0, false]) {
    const d = fixture();
    d.project.constraints.compute = { status: 'confirmed', value, source: 'Synthetic user resource record' };
    d.ideas[0].feasibility.status = 'blocked';
    d.ideas[0].feasibility.dependencies[0].status = 'failed';
    d.ideas[0].feasibility.dependencies[0].constraint_keys = ['compute'];
    decide(d, 'KILL', 'constraints', { constraint_keys: ['compute'], dependency_names: ['Synthetic resource'] }).decision_scope = 'current_constraints';
    const meaningful = value === 0 || value === false;
    const output = rankDossier(d);
    assert.equal(output.killed.length, meaningful ? 1 : 0);
    assert.equal(output.held.length, meaningful ? 0 : 1);
  }
});

test('a scientific contradiction can KILL this framing while smoke or failed execution cannot', () => {
  for (const [kind, outcome, expected] of [
    ['scientific', 'contradicted', 'KILL'],
    ['smoke', 'contradicted', 'HOLD'],
    ['scientific', 'execution_failed', 'HOLD'],
    ['scientific', 'inconclusive', 'HOLD'],
  ]) {
    const d = fixture();
    d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind, outcome,
      artifacts: ['synthetic-result.log'], summary: 'Synthetic attempted falsification', limitations: ['No scientific experiment performed'] });
    decide(d, 'KILL', 'scientific_refutation', { pilot_ids: ['X1'] });
    const output = rankDossier(d);
    assert.equal(output.killed.length, expected === 'KILL' ? 1 : 0);
    assert.equal(output.held.length, expected === 'HOLD' ? 1 : 0);
  }
});

test('a refreshed GO review cannot erase a current-version scientific pilot contradiction', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'contradicted',
    artifacts: ['synthetic-refutation.csv'], summary: 'Synthetic current hypothesis failed its stated test',
    limitations: ['A software fixture, not scientific evidence'] });
  refresh(d);
  assert.equal(validateDossier(d).valid, true);
  assert.equal(d.reviews[0].decision, 'GO');
  const output = rankDossier(d);
  assert.equal(output.ranked.length, 0);
  assert.equal(output.held.length, 1);
  assert.equal(output.killed.length, 0);
});

test('an old scientific contradiction does not permanently ban a freshly reviewed revised framing', () => {
  const d = fixture();
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'contradicted',
    artifacts: ['synthetic-old-refutation.csv'], summary: 'Synthetic historical framing was contradicted',
    limitations: ['Historical fixture, not a test of the revised question'] });
  d.ideas[0].version = 2;
  d.ideas[0].question = 'A revised synthetic question whose framing addresses the historical limitation';
  d.ideas[0].hypothesis = 'A different conditional prediction for the revised synthetic question';
  refresh(d);
  assert.equal(validateDossier(d).valid, true);
  const output = rankDossier(d);
  assert.equal(output.ranked.length, 1);
  assert.equal(output.held.length, 0);
  assert.equal(output.killed.length, 0);
  assert.equal(d.pilots[0].outcome, 'contradicted');
});

test('a contradictory old-version pilot cannot be cited as a current refutation', () => {
  const d = fixture(); d.ideas[0].version = 2;
  d.pilots.push({ id: 'X1', run_id: 'X1', affected_claims: [], idea_id: 'I1', idea_version: 1, kind: 'scientific', outcome: 'contradicted',
    artifacts: ['synthetic-old.csv'], summary: 'A different historical framing', limitations: [] });
  d.reviews[0].idea_version = 2;
  d.reviews[0].review_basis_hash = fingerprintIdea(d, 'I1');
  d.reviews[0].decision = 'KILL';
  d.reviews[0].decision_basis.type = 'scientific_refutation';
  d.reviews[0].decision_basis.pilot_ids = ['X1'];
  assert.equal(validateDossier(d).valid, false);
});

test('theory, measurement and reproduction can advance on deep non-support problem evidence', () => {
  for (const research_type of ['theoretical', 'measurement', 'reproduction']) {
    const d = fixture(); d.ideas[0].research_type = research_type;
    d.evidence[0].polarity = 'contradicts';
    Object.assign(d.ideas[0].evidence_links[0], { role: 'contradiction', target: 'problem', relation: 'contradicts',
      claim: 'A flaw in the existing formulation motivates this distinct research question' });
    refresh(d);
    assert.equal(rankDossier(d).ranked.length, 1);
  }
  const d = fixture(); d.ideas[0].research_type = 'theoretical';
  d.evidence[0].polarity = 'context'; d.ideas[0].evidence_links[0].relation = 'context'; refresh(d);
  assert.equal(rankDossier(d).ranked.length, 1);
});

test('metadata-only decision evidence and a deep but irrelevant source cannot establish GO', () => {
  for (const modify of [
    d => d.evidence[0].read_scope = 'metadata',
    d => d.ideas[0].evidence_links[0].decision_relevant = false,
    d => d.ideas[0].evidence_links = [],
  ]) {
    const d = fixture(); modify(d); refresh(d);
    assert.equal(rankDossier(d).held.length, 1);
  }
});

test('a decision-relevant contradiction of this hypothesis, prerequisite or design blocks GO', () => {
  for (const target of ['hypothesis', 'prerequisite', 'validation']) {
    const d = fixture(); d.evidence[0].polarity = 'contradicts';
    Object.assign(d.ideas[0].evidence_links[0], { role: 'contradiction', target, relation: 'contradicts' });
    refresh(d);
    assert.equal(rankDossier(d).ranked.length, 0);
    assert.equal(rankDossier(d).held.length, 1);
  }
});

test('candidate-specific evidence links cannot refer outside that candidate evidence set', () => {
  const d = fixture(); addUnrelated(d);
  d.ideas[0].evidence_links[0].evidence_id = 'E2';
  assert.equal(validateDossier(d).valid, false);
});

test('decision-basis evidence, pilots, dependency names and constraints must resolve in candidate scope', () => {
  const modifications = [
    d => d.reviews[0].decision_basis.evidence_ids = ['E2'],
    d => d.reviews[0].decision_basis.pilot_ids = ['X2'],
    d => d.reviews[0].decision_basis.dependency_names = ['Missing dependency'],
    d => d.reviews[0].decision_basis.constraint_keys = ['Missing resource'],
  ];
  for (const modify of modifications) {
    const d = fixture(); addUnrelated(d); modify(d);
    assert.equal(validateDossier(d).valid, false);
  }
});

test('historical review bases remain readable after candidate links change but cannot authorize GO', () => {
  const d = fixture(); addUnrelated(d);
  Object.assign(d.ideas[0], { evidence_ids: ['E2'], search_ids: ['S2'],
    evidence_links: [{ ...d.ideas[0].evidence_links[0], evidence_id: 'E2' }],
    nearest_work: [{ ...d.ideas[0].nearest_work[0], paper_id: 'P2', evidence_ids: ['E2'] }] });
  assert.equal(validateDossier(d).valid, true);
  assert.equal(rankDossier(d).ranked.length, 0);
  assert.equal(rankDossier(d).held.find(r => r.idea_id === 'I1').decision, 'HOLD');
  assert.deepEqual(d.reviews[0].decision_basis.evidence_ids, ['E1']);
});

test('new contract fields require valid enums, complete references and a decision explanation', () => {
  const updates = [
    d => delete d.reviews[0].review_basis_hash,
    d => d.reviews[0].decision_scope = 'whole_field',
    d => d.reviews[0].recommended_stage = 'publication',
    d => d.reviews[0].decision_basis.type = 'auto_scientific_truth',
    d => d.reviews[0].decision_basis.explanation = '',
    d => delete d.reviews[0].decision_basis.constraint_keys,
    d => d.ideas[0].evidence_links[0].target = 'entire_field',
    d => d.ideas[0].evidence_links[0].role = 'ground_truth',
    d => d.ideas[0].evidence_links[0].relation = 'proves',
    d => d.ideas[0].evidence_links[0].decision_relevant = 'yes',
  ];
  for (const change of updates) { const d = fixture(); change(d); assert.equal(validateDossier(d).valid, false); }
});

test('screening rejects missing references, invalid enums and papers absent from search results', () => {
  const updates = [
    s => s.search_id = 'missing', s => s.paper_id = 'missing', s => s.idea_ids = ['missing'],
    s => s.stage = 'imagined_reading', s => s.decision = 'possibly',
    s => s.paper_id = 'P2',
  ];
  for (const update of updates) {
    const d = fixture(); addUnrelated(d);
    const s = { id: 'SC1', search_id: 'S1', paper_id: 'P1', idea_ids: ['I1'], stage: 'metadata',
      decision: 'uncertain', reason: 'Synthetic uncertainty', screened_at: when };
    update(s); d.screening.push(s);
    assert.equal(validateDossier(d).valid, false);
  }
});

test('warnings preserve structural validity and never replace decision gates', () => {
  const d = fixture(); d.evidence[0].read_scope = 'full_text'; d.evidence[0].locator = 'paper'; refresh(d);
  const validation = validateDossier(d);
  assert.equal(validation.valid, true); assert.deepEqual(validation.errors, []);
  assert.ok(validation.warnings.length > 0);
});

test('screening exclusion of recorded nearest work is a consistency warning, not invalid JSON', () => {
  const d = fixture();
  d.screening.push({ id: 'SC1', search_id: 'S1', paper_id: 'P1', idea_ids: ['I1'], stage: 'full_text',
    decision: 'exclude', reason: 'Synthetic exclusion needs reconciliation', screened_at: when });
  const validation = validateDossier(d);
  assert.equal(validation.valid, true);
  assert.ok(validation.warnings.length > 0);
});

test('malformed candidate records with exclusions return aggregate validation errors without throwing', () => {
  const d = fixture();
  d.ideas = [null];
  d.screening.push({ id: 'SC1', search_id: 'S1', paper_id: 'P1', idea_ids: ['I1'], stage: 'full_text',
    decision: 'exclude', reason: 'Synthetic excluded work', screened_at: when });
  let validation;
  assert.doesNotThrow(() => { validation = validateDossier(d); });
  assert.equal(validation.valid, false);
  assert.ok(validation.errors.length >= 2);
});

test('low confidence retains score and requires explicit reasons for every dimension', () => {
  const d = fixture();
  d.reviews[0].confidence = { scientific_value: 'low', differentiation: 'medium', testability: 'high' };
  d.reviews[0].confidence_reasons = { scientific_value: 'Only synthetic motivation', differentiation: 'Only one fixture neighbor',
    testability: 'Synthetic design is fully specified' };
  assert.equal(validateDossier(d).valid, true);
  assert.equal(rankDossier(d).ranked[0].score, 100);
  assert.ok(validateDossier(d).warnings.length > 0);
  delete d.reviews[0].confidence_reasons;
  assert.equal(validateDossier(d).valid, false);
});

test('partial or invalid confidence is rejected instead of becoming a hidden score multiplier', () => {
  for (const confidence of [
    { scientific_value: 'certain', differentiation: 'medium', testability: 'high' },
    { scientific_value: 'low', differentiation: 'medium' },
  ]) {
    const d = fixture(); d.reviews[0].confidence = confidence;
    d.reviews[0].confidence_reasons = { scientific_value: 'Fixture', differentiation: 'Fixture', testability: 'Fixture' };
    assert.equal(validateDossier(d).valid, false);
  }
});

test('full validation needs a byte-verified current independent full-stage GO receipt; pilot does not', async () => {
  const d = fixture();
  assert.equal(rankDossier(d).ranked.length, 1);
  d.reviews[0].recommended_stage = 'full_validation';
  assert.equal(rankDossier(d).held.length, 1);
  const review = addReview(d, 'I1', { kind: 'independent', author_context: 'Synthetic author context A',
    evaluator_context: 'Synthetic independent context B', artifact: 'synthetic-review.json',
    recommended_stage: 'full_validation', reviewed_at: '2026-10-05T09:00:00Z' });
  assert.equal(rankDossier(d).held.length, 1);
  const root = await mkdtemp(path.join(tmpdir(), 'research-receipt-'));
  try {
    await sealReceipt(root, review);
    const receiptVerification = await verifyIndependentReceipts(d, { root });
    assert.deepEqual(receiptVerification.failed, []);
    assert.equal(rankDossier(d, { receiptVerification }).ranked.length, 1);
    assert.equal(rankDossier(d, { receiptVerification }).ranked[0].recommended_stage, 'full_validation');
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('a stale independent receipt cannot authorize a latest self full-validation recommendation', () => {
  const d = fixture();
  addReview(d, 'I1', { kind: 'independent', author_context: 'Synthetic author A', evaluator_context: 'Synthetic evaluator B',
    artifact: 'synthetic-review.md', reviewed_at: '2026-10-05T09:00:00Z' });
  d.ideas[0].question = 'A revised synthetic target';
  addReview(d, 'I1', { recommended_stage: 'full_validation', reviewed_at: '2026-10-05T10:00:00Z' });
  assert.equal(rankDossier(d).held.length, 1);
});

test('a verified independent pilot cannot authorize a later self full-validation GO', async () => {
  const d = fixture(); const peer = independentReview(d, { recommended_stage: 'pilot' });
  addReview(d, 'I1', { recommended_stage: 'full_validation', reviewed_at: '2026-10-05T10:00:00Z' });
  const root = await mkdtemp(path.join(tmpdir(), 'research-stage-'));
  try {
    await sealReceipt(root, peer);
    const receiptVerification = await verifyIndependentReceipts(d, { root });
    assert.equal(receiptVerification.verified.length, 1);
    const output = rankDossier(d, { receiptVerification });
    assert.equal(output.ranked.length, 0);
    assert.match(output.held[0].reasons.join(' '), /pilot approval cannot authorize escalation/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('a verified full-validation independent GO can cover a later matching self review', async () => {
  const d = fixture(); const peer = independentReview(d);
  addReview(d, 'I1', { recommended_stage: 'full_validation', reviewed_at: '2026-10-05T10:00:00Z' });
  const root = await mkdtemp(path.join(tmpdir(), 'research-full-'));
  try {
    await sealReceipt(root, peer);
    const receiptVerification = await verifyIndependentReceipts(d, { root });
    assert.equal(rankDossier(d, { receiptVerification }).ranked.length, 1);
    assert.equal(rankDossier(d, { receiptVerification: structuredClone(receiptVerification) }).ranked.length, 0);
    assert.equal(rankDossier(d, { receiptVerification: { verified: [{ review_id: peer.id }] } }).ranked.length, 0);
    d.reviews.at(-1).reason = 'A changed recommendation after verification';
    assert.equal(rankDossier(d, { receiptVerification }).ranked.length, 0);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('receipt verification compares actual bytes and complete review bindings', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-binding-'));
  try {
    for (const mutate of [
      receipt => receipt.review.idea_version++,
      receipt => receipt.review.review_basis_hash = '0'.repeat(64),
      receipt => receipt.review.recommended_stage = 'pilot',
      receipt => receipt.review.decision = 'HOLD',
      receipt => receipt.review.evaluator_context = 'Another evaluator',
      receipt => receipt.review.decision_basis.evidence_ids = [],
      receipt => receipt.review.scores.scientific_value = 0,
      receipt => receipt.review.decision_contract_version = 1,
    ]) {
      const d = fixture(); const peer = independentReview(d); const receipt = createReviewReceipt(peer); mutate(receipt);
      await sealReceipt(root, peer, receipt);
      const report = await verifyIndependentReceipts(d, { root });
      assert.equal(report.verified.length, 0);
      assert.match(report.failed[0].reason, /fields do not match/);
    }
    const d = fixture(); const peer = independentReview(d); await sealReceipt(root, peer);
    await writeFile(path.join(root, peer.artifact), `${JSON.stringify(createReviewReceipt(peer))} `);
    const report = await verifyIndependentReceipts(d, { root });
    assert.equal(report.verified.length, 0);
    assert.match(report.failed[0].reason, /SHA-256/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('later independent HOLD supersedes an older verified full-validation approval', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-new-peer-'));
  try {
    const d = fixture(); const first = independentReview(d); await sealReceipt(root, first);
    const later = independentReview(d, { artifact: 'hold.json', decision: 'HOLD', reviewed_at: '2026-10-05T10:00:00Z',
      decision_basis: { type: 'insufficient', evidence_ids: ['E1'], pilot_ids: [], dependency_names: [], constraint_keys: [], explanation: 'Synthetic remaining doubt' } });
    await sealReceipt(root, later);
    addReview(d, 'I1', { recommended_stage: 'full_validation', reviewed_at: '2026-10-05T11:00:00Z' });
    const receiptVerification = await verifyIndependentReceipts(d, { root });
    assert.equal(receiptVerification.verified.length, 2);
    assert.equal(rankDossier(d, { receiptVerification }).ranked.length, 0);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('later independent pilot approval supersedes an older full approval even at the same timestamp', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-peer-stage-'));
  try {
    const d = fixture(); const first = independentReview(d); await sealReceipt(root, first);
    const later = independentReview(d, { artifact: 'pilot.json', recommended_stage: 'pilot' });
    await sealReceipt(root, later);
    addReview(d, 'I1', { recommended_stage: 'full_validation', reviewed_at: '2026-10-05T11:00:00Z' });
    const receiptVerification = await verifyIndependentReceipts(d, { root });
    assert.equal(receiptVerification.verified.length, 2);
    assert.equal(rankDossier(d, { receiptVerification }).ranked.length, 0);
    assert.match(rankDossier(d, { receiptVerification }).held[0].reasons.join(' '), /pilot approval cannot authorize escalation/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('receipt claims and paths do not replace explicit local-root file verification', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-path-'));
  try {
    for (const artifact of ['literally anything', '../outside-review.json', 'https://example.invalid/receipt.json', 'file:///receipt.json']) {
      const d = fixture(); const peer = independentReview(d, { artifact, artifact_sha256: '0'.repeat(64) });
      peer.verified = true;
      const report = await verifyIndependentReceipts(d, { root });
      assert.equal(report.verified.length, 0);
      assert.equal(rankDossier(d, { receiptVerification: report }).ranked.length, 0);
    }
    const d = fixture(); independentReview(d);
    await assert.rejects(verifyIndependentReceipts(d), /explicit existing local root/);
    assert.equal((await verifyIndependentReceipts(d, { root })).verified.length, 0);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('receipt verification rejects symbolic links instead of following them', async t => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-link-'));
  try {
    const d = fixture(); const peer = independentReview(d, { artifact: 'actual.json' }); await sealReceipt(root, peer);
    try { await symlink(path.join(root, 'actual.json'), path.join(root, 'review.json'), 'file'); }
    catch (error) { if (['EPERM', 'EACCES', 'ENOTSUP'].includes(error.code)) { t.skip('File symlink creation unavailable on this host'); return; } throw error; }
    peer.artifact = 'review.json';
    const report = await verifyIndependentReceipts(d, { root });
    assert.equal(report.verified.length, 0);
    assert.match(report.failed[0].reason, /symbolic links/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('receipt verification accepts local spaces and absolute paths inside the root, and bounds reads', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-space-'));
  try {
    const d = fixture(); const peer = independentReview(d, { artifact: 'a real receipt.json' });
    await sealReceipt(root, peer);
    assert.equal((await verifyIndependentReceipts(d, { root })).verified.length, 1);
    peer.artifact = path.join(root, peer.artifact);
    assert.equal((await verifyIndependentReceipts(d, { root })).verified.length, 1);
    await writeFile(peer.artifact, Buffer.alloc(1024 * 1024 + 1));
    const report = await verifyIndependentReceipts(d, { root });
    assert.equal(report.verified.length, 0);
    assert.match(report.failed[0].reason, /1 MiB/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('a changed receipt is rechecked by the explicit CLI rank rather than a persisted verified flag', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-cli-receipt-'));
  try {
    const d = fixture(); const peer = independentReview(d); await sealReceipt(root, peer);
    const file = path.join(root, 'dossier.json'); await writeFile(file, JSON.stringify(d));
    let run = spawnSync(process.execPath, [script, 'rank', file, '--receipt-root', root], { encoding: 'utf8' });
    assert.equal(run.status, 0, run.stdout); assert.equal(JSON.parse(run.stdout).ranked.length, 1);
    await writeFile(path.join(root, peer.artifact), '{}');
    run = spawnSync(process.execPath, [script, 'rank', file, '--receipt-root', root], { encoding: 'utf8' });
    assert.equal(run.status, 0, run.stdout); assert.equal(JSON.parse(run.stdout).held.length, 1);
    const verify = spawnSync(process.execPath, [script, 'verify-receipts', file, '--root', root], { encoding: 'utf8' });
    assert.equal(verify.status, 0, verify.stdout); assert.equal(JSON.parse(verify.stdout).failed.length, 1);
    assert.deepEqual(JSON.parse(await readFile(file, 'utf8')), d);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('unrelated confirmed preferences or a blocked label cannot justify constraints KILL', () => {
  for (const modify of [
    d => d.ideas[0].feasibility.dependencies[0].status = 'met',
    d => d.ideas[0].feasibility.dependencies[0].constraint_keys = [],
    d => delete d.ideas[0].feasibility.dependencies[0].constraint_keys,
    d => d.reviews[0].decision_basis.constraint_keys = ['format'],
  ]) {
    const d = fixture();
    d.project.constraints.compute = { status: 'confirmed', value: 0, source: 'Synthetic resource observation' };
    d.project.constraints.format = { status: 'confirmed', value: 'Markdown', source: 'Synthetic user preference' };
    d.ideas[0].feasibility.status = 'blocked';
    Object.assign(d.ideas[0].feasibility.dependencies[0], { status: 'failed', constraint_keys: ['compute'] });
    decide(d, 'KILL', 'constraints', { constraint_keys: ['compute'], dependency_names: ['Synthetic resource'] }).decision_scope = 'current_constraints';
    modify(d); refresh(d);
    assert.equal(rankDossier(d).killed.length, 0);
    assert.equal(rankDossier(d).held.length, 1);
  }
});

test('unrelated validation errors do not hide current decision-basis scope errors', () => {
  const d = addUnrelated(fixture());
  d.reviews[0].decision_basis.evidence_ids = ['E2'];
  d.history.push({ evidence_ids: ['ghost'] });
  const errors = validateDossier(d).errors.join('\n');
  assert.match(errors, /history\[0\].evidence_ids/);
  assert.match(errors, /Evidence E2 is not attached to this candidate/);
  assert.throws(() => rankDossier(d), /Invalid dossier/);
});

test('malformed unrelated hash collections do not hide a valid candidate decision-basis error', () => {
  for (const modify of [
    d => d.screening[0].idea_ids = null,
    d => d.screening.push(null),
    d => d.searches.push(null),
    d => d.papers.push(null),
    d => d.evidence.push(null),
    d => d.pilots.push(null),
  ]) {
    const d = addUnrelated(fixture());
    d.reviews[0].decision_basis.evidence_ids = ['E2'];
    modify(d);
    const result = validateDossier(d);
    assert.equal(result.valid, false);
    assert.match(result.errors.join('\n'), /Evidence E2 is not attached to this candidate/);
    assert.throws(() => rankDossier(d), /Invalid dossier/);
  }
});

test('source notes must be an object and their type errors aggregate with other record errors', () => {
  for (const notes of ['unstructured string', [], null, 3]) {
    const d = fixture(); d.project.notes = notes;
    d.history.push({ evidence_ids: ['ghost'] });
    const errors = validateDossier(d).errors.join('\n');
    assert.match(errors, /project.notes: must be an object/);
    assert.match(errors, /history\[0\].evidence_ids/);
  }
  const d = fixture(); d.project.notes = { gap: 'A supplied hypothesis still awaiting verification' }; refresh(d);
  assert.equal(validateDossier(d).valid, true);
});

test('legacy v2 decisions remain readable but cannot become current through relabelling a review', () => {
  const d = fixture(); d.schema_version = 2; delete d.result_invalidations; delete d.decision_contract_version; delete d.reviews[0].decision_contract_version; refresh(d);
  const legacyHash = d.reviews[0].review_basis_hash;
  assert.equal(validateDossier(d).valid, true);
  for (const decision of ['GO', 'HOLD', 'KILL']) {
    d.reviews[0].decision = decision;
    assert.equal(rankDossier(d).held.length, 1);
  }
  d.reviews[0].decision_contract_version = DECISION_CONTRACT_VERSION;
  assert.equal(rankDossier(d).held.length, 1);
  d.decision_contract_version = DECISION_CONTRACT_VERSION;
  assert.notEqual(fingerprintIdea(d, 'I1'), legacyHash);
  assert.equal(rankDossier(d).held.length, 1);
});

test('contract migration archives legacy v2 reviews unchanged without making replacement approvals', () => {
  const d = fixture(); d.schema_version = 2; delete d.result_invalidations; d.decision_contract_version = 1; d.reviews[0].decision_contract_version = 1; refresh(d);
  const original = structuredClone(d); const migrated = migrateDossier(d);
  assert.deepEqual(d, original);
  assert.equal(migrated.schema_version, 3);
  assert.equal(migrated.decision_contract_version, DECISION_CONTRACT_VERSION);
  assert.deepEqual(migrated.reviews, []);
  assert.deepEqual(migrated.history.at(-1).original_review, original.reviews[0]);
  assert.equal(migrated.history.at(-1).requires_reassessment, true);
  assert.equal(rankDossier(migrated).held.length, 1);
});

test('contract migration cannot expose an older GO after archiving the latest legacy review', () => {
  for (const reviewed_at of [when, '2026-10-05T10:00:00Z']) {
    const d = fixture();
    addReview(d, 'I1', { decision_contract_version: 1, decision: 'HOLD', reviewed_at });
    const original = structuredClone(d);
    assert.equal(rankDossier(d).held.length, 1);
    const migrated = migrateDossier(d);
    assert.equal(rankDossier(migrated).ranked.length, 0);
    assert.equal(rankDossier(migrated).held.length, 1);
    assert.deepEqual(migrated.reviews, []);
    assert.deepEqual(migrated.history.map(item => item.original_review), original.reviews);
    assert.deepEqual(d, original);
    assert.deepEqual(migrateDossier(migrated), migrated);
  }
});

test('contract migration cannot restore an older independent full approval hidden by a legacy peer', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-migration-peer-'));
  try {
    const d = fixture(); const first = independentReview(d); await sealReceipt(root, first);
    const blocker = independentReview(d, { artifact: 'legacy-hold.json', decision: 'HOLD',
      decision_contract_version: 1, reviewed_at: '2026-10-05T10:00:00Z' });
    const latest = addReview(d, 'I1', { recommended_stage: 'full_validation', reviewed_at: '2026-10-05T11:00:00Z' });
    const before = await verifyIndependentReceipts(d, { root });
    assert.equal(rankDossier(d, { receiptVerification: before }).held.length, 1);
    const migrated = migrateDossier(d);
    const after = await verifyIndependentReceipts(migrated, { root });
    assert.equal(rankDossier(migrated, { receiptVerification: after }).ranked.length, 0);
    assert.equal(rankDossier(migrated, { receiptVerification: after }).held.length, 1);
    assert.deepEqual(migrated.reviews, [d.reviews[0], latest]);
    assert.deepEqual(migrated.history.map(item => item.original_review), [first, blocker]);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('contract migration retains a genuinely newer current review after an older legacy review', () => {
  const d = fixture(); d.reviews[0].decision_contract_version = 1;
  const latest = addReview(d, 'I1', { reviewed_at: '2026-10-05T10:00:00Z' });
  const migrated = migrateDossier(d);
  assert.deepEqual(migrated.reviews, [latest]);
  assert.equal(rankDossier(migrated).ranked.length, 1);
  assert.deepEqual(migrated.history[0].original_review, d.reviews[0]);
});

test('unsupported future contracts are preserved and cannot be migrated into an older meaning', () => {
  const d = fixture(); d.decision_contract_version = DECISION_CONTRACT_VERSION + 1;
  d.reviews[0].decision_contract_version = DECISION_CONTRACT_VERSION + 1; refresh(d);
  const original = structuredClone(d);
  assert.equal(validateDossier(d).valid, true);
  assert.equal(rankDossier(d).held.length, 1);
  assert.throws(() => migrateDossier(d), /unsupported future decision contract/);
  assert.deepEqual(d, original);
  d.decision_contract_version = DECISION_CONTRACT_VERSION;
  assert.throws(() => migrateDossier(d), /unsupported future decision contract/);
});

test('independent labeling needs distinct context identifiers and a review artifact', () => {
  for (const options of [
    { author_context: 'same', evaluator_context: 'same', artifact: 'synthetic-review.md' },
    { author_context: 'author', evaluator_context: 'evaluator' },
  ]) {
    const d = fixture(); Object.assign(d.reviews[0], { kind: 'independent' }, options);
    assert.equal(validateDossier(d).valid, false);
  }
});

test('v1 remains readable with its original hash but its old decisions require reassessment', () => {
  const d = v1Fixture();
  assert.equal(validateDossier(d).valid, true);
  const expected = createHash('sha256').update(canonicalStringify({ project: d.project, config: d.config,
    searches: d.searches, papers: d.papers, evidence: d.evidence, idea: d.ideas[0],
    pilots: d.pilots.filter(pilot => pilot.idea_id === 'I1') }), 'utf8').digest('hex');
  assert.equal(fingerprintIdea(d, 'I1'), expected);
  for (const decision of ['GO', 'HOLD', 'KILL']) {
    d.reviews[0].decision = decision;
    const output = rankDossier(d);
    assert.equal(output.ranked.length, 0); assert.equal(output.killed.length, 0); assert.equal(output.held.length, 1);
  }
});

test('migration archives full v1 reviews without fabricating reassessment or mutating input', () => {
  const d = v1Fixture(); const before = JSON.stringify(d); const oldReview = structuredClone(d.reviews[0]);
  const migrated = migrateDossier(d);
  assert.equal(JSON.stringify(d), before);
  assert.equal(migrated.schema_version, 3);
  assert.equal(validateDossier(migrated).valid, true);
  assert.deepEqual(migrated.reviews, []);
  assert.deepEqual(migrated.ideas[0].evidence_links, []);
  const archived = migrated.history.find(entry => entry.original_review?.id === oldReview.id);
  assert.deepEqual(archived.original_review, oldReview);
  assert.equal(archived.requires_reassessment, true);
  assert.equal(rankDossier(migrated).held.length, 1);
  assert.equal(rankDossier(migrated).ranked.length, 0);
});

test('migrating a current v3 dossier preserves its records without rewriting hashes', () => {
  const d = fixture(); const before = structuredClone(d);
  assert.deepEqual(migrateDossier(d), before);
  assert.deepEqual(d, before);
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
    for (const command of ['validate', 'rank', 'fingerprint', 'migrate']) {
      const args = command === 'fingerprint' ? [command, file, 'I1'] : [command, file];
      const r = spawnSync(process.execPath, [script, ...args], { encoding: 'utf8' });
      assert.equal(r.status, 0, r.stderr);
      if (command !== 'fingerprint') JSON.parse(r.stdout);
      assert.equal(await readFile(file, 'utf8'), content);
    }
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('CLI migration emits a valid reassessment dossier without overwriting the v1 file', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'research-skill-test-'));
  try {
    const file = path.join(root, 'old-dossier.json');
    const content = JSON.stringify(v1Fixture(), null, 2); await writeFile(file, content);
    const result = spawnSync(process.execPath, [script, 'migrate', file], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr);
    const output = JSON.parse(result.stdout);
    assert.equal(output.schema_version, 3);
    assert.equal(validateDossier(output).valid, true);
    assert.deepEqual(output.reviews, []);
    assert.equal(await readFile(file, 'utf8'), content);
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
