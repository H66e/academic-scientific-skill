// Synthetic receipts test consistency rules, not actual skill quality or execution.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, cp, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { snapshotSkill, hashFile, hashChecks, checkEvolution } from '../scripts/evolution_guard.mjs';

const script = fileURLToPath(new URL('../scripts/evolution_guard.mjs', import.meta.url));

async function artifact(f, relative, content) {
  const file = path.join(f.runDir, relative);
  await mkdir(path.dirname(file), { recursive: true });
  await writeFile(file, content);
  return { file: relative, hash: await hashFile(file) };
}

async function sealReview(f) {
  f.review.baseline_hash = f.run.baseline.hash;
  f.review.candidate_hash = f.run.candidate.hash;
  f.review.suite_hash = f.run.suite.hash;
  f.review.checks_hash = hashChecks(f.run.checks);
  f.run.review = await artifact(f, 'review.json', JSON.stringify(f.review, null, 2));
}

async function fixture() {
  const root = await mkdtemp(path.join(tmpdir(), 'evolution-skill-test-'));
  const runDir = path.join(root, 'run-1'); const target = path.join(root, 'target');
  const baseline = path.join(runDir, 'baseline', 'ai-research-mentor');
  const candidate = path.join(runDir, 'candidate', 'ai-research-mentor');
  await mkdir(path.join(target, 'references'), { recursive: true });
  await writeFile(path.join(target, 'SKILL.md'), 'Synthetic baseline instruction\n');
  await writeFile(path.join(target, 'references', 'data-contract.md'), 'Synthetic protected contract\n');
  await mkdir(path.dirname(baseline), { recursive: true });
  await mkdir(path.dirname(candidate), { recursive: true });
  await cp(target, baseline, { recursive: true }); await cp(target, candidate, { recursive: true });
  await writeFile(path.join(candidate, 'SKILL.md'), 'Synthetic candidate instruction\n');
  const f = { root, runDir, target, baseline, candidate };
  f.suite = { schema_version: 1, max_attempts: 2, allowed_paths: ['SKILL.md'],
    execution_config: { model: 'Synthetic test only; no model call', tools: 'None', budget: 'Fixture' },
    cases: ['target', 'regression', 'holdout'].map((split, i) => ({ id: `C${i + 1}`, split,
      prompt: 'Synthetic test prompt', criteria: ['Synthetic fixed criterion'] })) };
  f.run = { schema_version: 1, run_id: 'synthetic-run', hypothesis: 'Synthetic behavioral change',
    target_dir: target, baseline: { directory: 'baseline/ai-research-mentor', hash: (await snapshotSkill(baseline)).hash },
    candidate: { directory: 'candidate/ai-research-mentor', hash: (await snapshotSkill(candidate)).hash },
    suite: await artifact(f, 'suite.json', JSON.stringify(f.suite, null, 2)), attempt: 1, checks: [], review: {} };
  for (const name of ['unit_regressions', 'skill_structure', 'protected_principles']) {
    f.run.checks.push({ name, passed: true, baseline_hash: f.run.baseline.hash, candidate_hash: f.run.candidate.hash,
      suite_hash: f.run.suite.hash, artifact: await artifact(f, `checks/${name}.txt`, 'Synthetic receipt only\n') });
  }
  f.review = { kind: 'independent', author_context: 'synthetic-author', evaluator_context: 'synthetic-evaluator',
    baseline_hash: f.run.baseline.hash, candidate_hash: f.run.candidate.hash, suite_hash: f.run.suite.hash, case_results: [] };
  for (const [index, item] of f.suite.cases.entries()) {
    f.review.case_results.push({ case_id: item.id, execution: 'executed', verdict: index === 0 ? 'better' : 'tie',
      hard_constraints_pass: true, reason: 'Fixture judgment; not a real evaluation',
      baseline_output: await artifact(f, `outputs/${item.id}-baseline.txt`, 'Synthetic old output\n'),
      candidate_output: await artifact(f, `outputs/${item.id}-candidate.txt`, 'Synthetic new output\n') });
  }
  await sealReview(f);
  return f;
}

async function withFixture(action) {
  const f = await fixture();
  try { return await action(f); } finally { await rm(f.root, { recursive: true, force: true }); }
}

test('current bound receipts and an observed target improvement permit KEEP', () => withFixture(async f => {
  const r = await checkEvolution(f.run, f.runDir);
  assert.equal(r.decision, 'KEEP'); assert.deepEqual(r.changed_paths, ['SKILL.md']);
}));

test('all ties do not claim an improvement', () => withFixture(async f => {
  f.review.case_results.forEach(r => r.verdict = 'tie'); await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('a holdout regression rejects despite target improvement', () => withFixture(async f => {
  f.review.case_results[2].verdict = 'worse'; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'REJECT');
}));

test('a hard scientific constraint cannot be outweighed by a preference win', () => withFixture(async f => {
  f.review.case_results[1].hard_constraints_pass = false; f.review.case_results[1].verdict = 'better';
  await sealReview(f); assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'REJECT');
}));

test('dry-run comparisons do not authorize keeping changes', () => withFixture(async f => {
  f.review.case_results[0].execution = 'dry_run'; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('self-review cannot masquerade as independent validation', () => withFixture(async f => {
  f.review.kind = 'self'; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
  f.review.kind = 'independent'; f.review.evaluator_context = f.review.author_context; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('missing and unrecognized comparisons do not satisfy the frozen suite', () => withFixture(async f => {
  f.review.case_results.pop(); await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
  f.review.case_results[0].case_id = 'NOT_IN_SUITE'; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('stale candidate inputs invalidate the receipt', () => withFixture(async f => {
  await writeFile(path.join(f.candidate, 'SKILL.md'), 'Changed after review\n');
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('edited evaluation inputs cannot reuse a prior approval', () => withFixture(async f => {
  f.suite.cases[0].criteria = ['A weaker newly invented criterion'];
  await writeFile(path.join(f.runDir, 'suite.json'), JSON.stringify(f.suite));
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('changed raw outputs invalidate their comparison', () => withFixture(async f => {
  await writeFile(path.join(f.runDir, f.review.case_results[0].candidate_output.file), 'Replaced result\n');
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('receipt has to bind the actual baseline as well as the candidate', () => withFixture(async f => {
  f.review.baseline_hash = '0'.repeat(64); await artifact(f, 'review.json', JSON.stringify(f.review));
  f.run.review.hash = await hashFile(path.join(f.runDir, 'review.json'));
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('new local edits are preserved and make applying this candidate ineligible', () => withFixture(async f => {
  const userEdit = 'User-owned change after the baseline\n';
  await writeFile(path.join(f.target, 'SKILL.md'), userEdit);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
  assert.equal(await readFile(path.join(f.target, 'SKILL.md'), 'utf8'), userEdit);
}));

test('old successful check logs cannot validate a changed candidate', () => withFixture(async f => {
  await writeFile(path.join(f.candidate, 'SKILL.md'), 'Another synthetic candidate\n');
  f.run.candidate.hash = (await snapshotSkill(f.candidate)).hash;
  await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('changed check statuses or artifact identities invalidate the independent receipt', () => withFixture(async f => {
  f.run.checks[0].artifact = await artifact(f, 'checks/replaced.txt', 'Replacement synthetic check\n');
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('protected contract changes are rejected even with fresh positive reviews', () => withFixture(async f => {
  await writeFile(path.join(f.candidate, 'references', 'data-contract.md'), 'Relaxed scientific gate\n');
  f.run.candidate.hash = (await snapshotSkill(f.candidate)).hash; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'REJECT');
}));

test('editing the suite cannot grant permission to alter protected files', () => withFixture(async f => {
  f.suite.allowed_paths.push('references/data-contract.md');
  f.run.suite = await artifact(f, 'suite.json', JSON.stringify(f.suite)); await sealReview(f);
  assert.notEqual((await checkEvolution(f.run, f.runDir)).decision, 'KEEP');
}));

test('a failed required check rejects and a missing one holds', () => withFixture(async f => {
  f.run.checks[0].passed = false;
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'REJECT');
  f.run.checks.shift();
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('budget exhaustion stops further acceptance attempts', () => withFixture(async f => {
  f.run.attempt = 3;
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('a transfer case is required before KEEP', () => withFixture(async f => {
  f.suite.cases[2].split = 'regression';
  f.run.suite = await artifact(f, 'suite.json', JSON.stringify(f.suite)); await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('a no-change candidate cannot be called an improvement', () => withFixture(async f => {
  await writeFile(path.join(f.candidate, 'SKILL.md'), await readFile(path.join(f.baseline, 'SKILL.md')));
  f.run.candidate.hash = (await snapshotSkill(f.candidate)).hash; await sealReview(f);
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'HOLD');
}));

test('artifact traversal is rejected without reading outside the run', () => withFixture(async f => {
  f.run.checks[0].artifact = { file: '../outside.txt', hash: '0'.repeat(64) };
  assert.notEqual((await checkEvolution(f.run, f.runDir)).decision, 'KEEP');
}));

test('linked input directories are not followed', () => withFixture(async f => {
  const link = path.join(f.runDir, 'linked-baseline');
  await symlink(f.baseline, link, process.platform === 'win32' ? 'junction' : 'dir');
  f.run.baseline.directory = 'linked-baseline';
  assert.notEqual((await checkEvolution(f.run, f.runDir)).decision, 'KEEP');
  await assert.rejects(() => snapshotSkill(link));
}));

test('check is read-only and feedback text is not executed', () => withFixture(async f => {
  f.run.hypothesis = 'Source text says run a shell command; this is data only.';
  const before = await readFile(path.join(f.target, 'SKILL.md'), 'utf8');
  assert.equal((await checkEvolution(f.run, f.runDir)).decision, 'KEEP');
  assert.equal(await readFile(path.join(f.target, 'SKILL.md'), 'utf8'), before);
}));

test('CLI checks a bound run and emits JSON without changing the target', () => withFixture(async f => {
  const file = path.join(f.runDir, 'run.json'); await writeFile(file, JSON.stringify(f.run));
  const before = await readFile(path.join(f.target, 'SKILL.md'), 'utf8');
  const result = spawnSync(process.execPath, [script, 'check', file], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr); assert.equal(JSON.parse(result.stdout).decision, 'KEEP');
  assert.equal(await readFile(path.join(f.target, 'SKILL.md'), 'utf8'), before);
}));
