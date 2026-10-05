#!/usr/bin/env node
// Read-only receipts and version checks. No shell, Git, writes, or auto-application.
import { createHash } from 'node:crypto';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { canonicalStringify } from './research_audit.mjs';

export const NOTICE = 'Structural and recorded-evidence checks only: KEEP does not establish scientific quality, novelty, or correctness.';
const EDITABLE = new Set(['SKILL.md', ...['literature', 'ideation', 'evaluation', 'feedback'].map(name => `references/${name}.md`)]);
const REQUIRED_CHECKS = ['unit_regressions', 'skill_structure', 'protected_principles'];
const SPLITS = ['target', 'regression', 'holdout'];
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const digest = value => typeof value === 'string' && /^[a-f\d]{64}$/.test(value);
const positive = value => Number.isInteger(value) && value > 0;
const sha256 = value => createHash('sha256').update(value).digest('hex');
const inside = (root, file) => {
  const relative = path.relative(root, file);
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
};

function resolvePath(base, value, contained = true) {
  if (!text(value) || /[\x00-\x1f]/.test(value)) throw new Error('must be a nonempty filesystem path');
  // Reject URL/drive-relative spellings rather than interpreting them as files.
  if (/^[a-z][a-z\d+.-]*:/i.test(value) && !/^[a-z]:[\\/]/i.test(value)) throw new Error('URLs and drive-relative paths are forbidden');
  if (process.platform !== 'win32' && (/^[a-z]:/i.test(value) || value.includes('\\'))) throw new Error('foreign-platform paths are forbidden');
  const result = path.resolve(base, value);
  if (contained && !inside(base, result)) throw new Error('path must stay inside runDir');
  return result;
}

/** Inspect every ancestor: lstat on the leaf alone would miss directory links. */
async function noLinks(file, kind) {
  const absolute = path.resolve(file), root = path.parse(absolute).root;
  const parts = path.relative(root, absolute).split(path.sep).filter(Boolean);
  let current = root;
  const rootStat = await fs.lstat(root);
  if (rootStat.isSymbolicLink() || !rootStat.isDirectory()) throw new Error('linked or invalid filesystem root');
  for (let index = 0; index < parts.length; index += 1) {
    current = path.join(current, parts[index]);
    const stat = await fs.lstat(current);
    if (stat.isSymbolicLink()) throw new Error('symbolic links and junctions are forbidden');
    const expected = index === parts.length - 1 ? kind : 'directory';
    if (expected === 'directory' ? !stat.isDirectory() : !stat.isFile()) throw new Error(`expected a regular ${expected}`);
  }
  if (parts.length === 0 && kind !== 'directory') throw new Error('expected a regular file');
  return absolute;
}

async function readBytes(file) {
  const absolute = await noLinks(file, 'file');
  const bytes = await fs.readFile(absolute);
  await noLinks(absolute, 'file');
  return bytes;
}

/** SHA-256 of the exact file bytes; rejects linked files and linked ancestors. */
export async function hashFile(file) { return sha256(await readBytes(file)); }

/** Bind the exact check statuses and log hashes to the independent review. */
export function hashChecks(checks) { return sha256(canonicalStringify(checks)); }

/** Hash every regular file, including tests; never follows links or ignores files. */
export async function snapshotSkill(directory) {
  const root = await noLinks(directory, 'directory');
  const files = Object.create(null);
  async function walk(current) {
    for (const name of (await fs.readdir(current)).sort()) {
      const absolute = path.join(current, name), stat = await fs.lstat(absolute);
      if (stat.isSymbolicLink()) throw new Error('snapshot contains a symbolic link or junction');
      if (stat.isDirectory()) await walk(absolute);
      else if (stat.isFile()) files[path.relative(root, absolute).split(path.sep).join('/')] = await hashFile(absolute);
      else throw new Error('snapshot contains a non-regular file');
    }
  }
  await walk(root);
  await noLinks(root, 'directory');
  const sorted = Object.fromEntries(Object.entries(files).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
  return { hash: sha256(canonicalStringify(sorted)), files: sorted };
}

function validateSuite(suite, hold) {
  if (!object(suite)) { hold('suite must be a JSON object'); return []; }
  if (suite.schema_version !== 1) hold('suite.schema_version must equal 1');
  if (!positive(suite.max_attempts)) hold('suite.max_attempts must be a positive integer');
  if (!object(suite.execution_config)) hold('suite.execution_config must be an object');
  else { try { canonicalStringify(suite.execution_config); } catch { hold('suite.execution_config must contain finite JSON values'); } }
  if (!Array.isArray(suite.allowed_paths) || suite.allowed_paths.some(value => !EDITABLE.has(value)) || new Set(suite.allowed_paths).size !== suite.allowed_paths.length) {
    hold('suite.allowed_paths must be a unique subset of the fixed editable whitelist');
  }
  const cases = Array.isArray(suite.cases) ? suite.cases : [];
  if (!Array.isArray(suite.cases)) hold('suite.cases must be an array');
  const ids = new Set(), counts = Object.fromEntries(SPLITS.map(split => [split, 0]));
  for (const item of cases) {
    if (!object(item)) { hold('suite case must be an object'); continue; }
    if (!text(item.id) || ids.has(item.id)) hold('suite case IDs must be nonempty and unique');
    ids.add(item.id);
    if (!SPLITS.includes(item.split)) hold('suite case split must be target, regression, or holdout');
    else counts[item.split] += 1;
    if (!text(item.prompt)) hold('suite case prompt must be nonempty');
    if (!Array.isArray(item.criteria) || item.criteria.length === 0 || item.criteria.some(value => !text(value))) hold('suite case criteria must contain nonempty strings');
  }
  for (const split of SPLITS) if (counts[split] === 0) hold(`suite requires at least one ${split} case`);
  return cases;
}

/** Validate a run against current bytes. Rejection wins over incomplete evidence. */
export async function checkEvolution(run, runDir) {
  const holds = [], rejects = [];
  let changed_paths = [];
  const hold = reason => holds.push(reason), reject = reason => rejects.push(reason);
  const finish = () => ({ decision: rejects.length ? 'REJECT' : holds.length ? 'HOLD' : 'KEEP', reasons: [...new Set([...rejects, ...holds])], changed_paths });
  try {
    if (!object(run)) { hold('run must be an object'); return finish(); }
    const root = await noLinks(path.resolve(runDir), 'directory');
    if (run.schema_version !== 1) hold('run.schema_version must equal 1');
    for (const key of ['run_id', 'hypothesis']) if (!text(run[key])) hold(`run.${key} must be nonempty`);
    if (!positive(run.attempt)) hold('run.attempt must be a positive integer');

    async function artifact(record, label, json = false) {
      try {
        if (!object(record) || !digest(record.hash)) throw new Error('requires file and lowercase SHA-256 hash');
        const absolute = resolvePath(root, record.file), bytes = await readBytes(absolute);
        if (sha256(bytes) !== record.hash) throw new Error('artifact hash does not match current bytes');
        return { ok: true, value: json ? JSON.parse(bytes.toString('utf8')) : null };
      } catch (error) { hold(`${label}: ${error.message}`); return { ok: false, value: null }; }
    }

    async function snapshot(record, label) {
      try {
        if (!object(record) || !digest(record.hash)) throw new Error('requires directory and lowercase SHA-256 hash');
        const result = await snapshotSkill(resolvePath(root, record.directory));
        if (result.hash !== record.hash) hold(`${label}: snapshot hash does not match current files`);
        return result;
      } catch (error) { hold(`${label}: ${error.message}`); return null; }
    }

    const baseline = await snapshot(run.baseline, 'baseline');
    const candidate = await snapshot(run.candidate, 'candidate');
    if (baseline && candidate) {
      changed_paths = [...new Set([...Object.keys(baseline.files), ...Object.keys(candidate.files)])].sort().filter(file => baseline.files[file] !== candidate.files[file]);
      if (changed_paths.length === 0) hold('candidate has no file changes');
      for (const file of changed_paths) if (!EDITABLE.has(file)) reject(`protected file changed: ${file}`);
    }
    try {
      const target = await snapshotSkill(resolvePath(root, run.target_dir, false));
      if (!baseline || target.hash !== run.baseline?.hash || target.hash !== baseline.hash) hold('target no longer matches the baseline snapshot');
    } catch (error) { hold(`target_dir: ${error.message}`); }

    const suiteArtifact = await artifact(run.suite, 'suite', true);
    const suite = suiteArtifact.value, cases = suiteArtifact.ok ? validateSuite(suite, hold) : [];
    if (object(suite)) {
      if (positive(suite.max_attempts) && positive(run.attempt) && run.attempt > suite.max_attempts) hold('attempt exceeds the frozen suite budget');
      if (Array.isArray(suite.allowed_paths) && suite.allowed_paths.every(value => EDITABLE.has(value))) {
        for (const file of changed_paths) if (EDITABLE.has(file) && !suite.allowed_paths.includes(file)) reject(`change outside suite.allowed_paths: ${file}`);
      }
    }

    const checks = Array.isArray(run.checks) ? run.checks : [];
    if (!Array.isArray(run.checks)) hold('run.checks must be an array');
    const names = new Set();
    for (const check of checks) {
      if (!object(check)) { hold('check must be an object'); continue; }
      if (!text(check.name) || names.has(check.name)) hold('check names must be nonempty and unique');
      names.add(check.name);
      if (check.passed === false) reject(`check failed: ${check.name}`);
      else if (check.passed !== true) hold(`check.passed must be boolean: ${check.name}`);
      for (const [key, expectedHash] of [['baseline_hash', baseline?.hash], ['candidate_hash', candidate?.hash], ['suite_hash', run.suite?.hash]]) {
        if (!digest(check[key]) || check[key] !== expectedHash) hold(`check is stale or unbound: ${check.name}.${key}`);
      }
      await artifact(check.artifact, `check artifact ${check.name}`);
    }
    for (const name of REQUIRED_CHECKS) if (!names.has(name)) hold(`missing required check: ${name}`);

    const receipt = await artifact(run.review, 'review', true);
    if (!receipt.ok) return finish();
    const review = receipt.value;
    if (!object(review)) { hold('review must be a JSON object'); return finish(); }
    if (!['independent', 'self'].includes(review.kind)) hold('review.kind must be independent or self');
    if (review.kind !== 'independent') hold('review must be independent to KEEP');
    if (!digest(review.checks_hash) || review.checks_hash !== hashChecks(checks)) hold('review does not bind the current check statuses and artifacts');
    if (!text(review.author_context) || !text(review.evaluator_context) || review.author_context.trim() === review.evaluator_context.trim()) hold('review requires different nonempty author and evaluator contexts');
    const bound = baseline && candidate && suiteArtifact.ok &&
      baseline.hash === run.baseline?.hash && candidate.hash === run.candidate?.hash &&
      digest(review.baseline_hash) && review.baseline_hash === baseline.hash &&
      digest(review.candidate_hash) && review.candidate_hash === candidate.hash &&
      digest(review.suite_hash) && review.suite_hash === run.suite?.hash;
    if (!bound) hold('review is not bound to the current baseline, candidate, and suite hashes');
    const rows = Array.isArray(review.case_results) ? review.case_results : [];
    if (!Array.isArray(review.case_results)) hold('review.case_results must be an array');
    const expected = new Map(cases.filter(object).map(item => [item.id, item]));
    const seen = new Set();
    let targetBetter = false;
    for (const row of rows) {
      if (!object(row)) { hold('review case result must be an object'); continue; }
      const known = text(row.case_id) && expected.has(row.case_id), unique = !seen.has(row.case_id);
      if (!known) hold('review contains an unknown or invalid case ID');
      if (!unique) hold(`duplicate review case: ${row.case_id}`);
      seen.add(row.case_id);
      if (row.execution !== 'executed') hold(`case was not executed: ${row.case_id}`);
      if (!['executed', 'dry_run'].includes(row.execution)) hold(`invalid execution mode: ${row.case_id}`);
      if (!['better', 'tie', 'worse', 'unclear'].includes(row.verdict)) hold(`invalid verdict: ${row.case_id}`);
      if (row.verdict === 'unclear') hold(`unclear verdict: ${row.case_id}`);
      if (typeof row.hard_constraints_pass !== 'boolean') hold(`hard_constraints_pass must be boolean: ${row.case_id}`);
      if (!text(row.reason)) hold(`case reason must be nonempty: ${row.case_id}`);
      const before = await artifact(row.baseline_output, `baseline output ${row.case_id}`);
      const after = await artifact(row.candidate_output, `candidate output ${row.case_id}`);
      const supported = bound && known && unique && row.execution === 'executed' && before.ok && after.ok;
      if (supported && row.hard_constraints_pass === false) reject(`hard constraint failed: ${row.case_id}`);
      if (supported && row.verdict === 'worse') reject(`case regressed: ${row.case_id}`);
      if (supported && row.hard_constraints_pass === true && row.verdict === 'better' && expected.get(row.case_id).split === 'target') targetBetter = true;
    }
    for (const id of expected.keys()) if (!seen.has(id)) hold(`missing review case: ${id}`);
    if (!targetBetter) hold('no executed target case demonstrates improvement');
    return finish();
  } catch (error) { hold(`invalid run or filesystem: ${error.message}`); return finish(); }
}

async function main(args) {
  if (args.length !== 2 || !['snapshot', 'hash', 'checks-hash', 'check'].includes(args[0])) throw new Error('Usage: evolution_guard.mjs snapshot <dir> | hash <file> | checks-hash <run.json> | check <run.json>');
  const [command, input] = args;
  if (command === 'snapshot') return { ...await snapshotSkill(input), notice: NOTICE };
  if (command === 'hash') return { hash: await hashFile(input), notice: NOTICE };
  const runFile = await noLinks(path.resolve(input), 'file');
  const run = JSON.parse((await readBytes(runFile)).toString('utf8'));
  if (command === 'checks-hash') return { hash: hashChecks(run.checks), notice: NOTICE };
  return { ...await checkEvolution(run, path.dirname(runFile)), notice: NOTICE };
}

const entry = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (entry && entry === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(result => process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)).catch(error => {
    process.exitCode = 1;
    process.stdout.write(`${JSON.stringify({ decision: 'HOLD', reasons: [error.message], changed_paths: [], notice: NOTICE }, null, 2)}\n`);
  });
}
