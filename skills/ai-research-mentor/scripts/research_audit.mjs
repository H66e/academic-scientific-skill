#!/usr/bin/env node
// Structural checks and bounded ranking; never a proof of scientific merit.
// Public APIs: createInitialDossier, validateDossier, canonicalStringify,
// fingerprintIdea, rankDossier, initProject. Importing this file has no effects.
import { createHash } from 'node:crypto';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIMENSIONS = ['scientific_value', 'differentiation', 'testability'];
const TYPES = ['empirical', 'theoretical', 'measurement', 'dataset', 'reproduction'];
const READ_SCOPES = ['metadata', 'abstract', 'section', 'full_text'];
const NOTICE = 'Structural checks only: passing does not establish source authenticity, literature coverage, novelty, or scientific correctness.';
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const positiveInteger = value => Number.isInteger(value) && value > 0;

function timestamp(value) {
  if (typeof value !== 'string') return false;
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.\d+)?)?(Z|[+-]\d{2}:?\d{2})$/.exec(value);
  if (!match || !Number.isFinite(Date.parse(value))) return false;
  const [, y, m, d, h, minute, second = '0', zone] = match;
  const year = Number(y), month = Number(m), day = Number(d);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (month < 1 || month > 12 || day < 1 || day > days[month - 1]) return false;
  if (Number(h) > 23 || Number(minute) > 59 || Number(second) > 59) return false;
  return zone === 'Z' || (Number(zone.slice(1, 3)) <= 23 && Number(zone.replace(':', '').slice(3)) <= 59);
}

function sourceUrl(value) {
  if (!nonempty(value) || /[\x00-\x20]/.test(value) || !/^(https?:\/\/|file:\/\/)/i.test(value)) return false;
  try {
    const url = new URL(value);
    if (url.username || url.password) return false;
    if (url.protocol === 'file:') return url.pathname.length > 1;
    return ['https:', 'http:'].includes(url.protocol) && Boolean(url.hostname);
  } catch { return false; }
}

function artifact(value) {
  if (!nonempty(value) || /[\x00-\x1f]/.test(value)) return false;
  if (/^[a-z][a-z\d+.-]*:/i.test(value) && !/^[a-z]:[\\/]/i.test(value)) return sourceUrl(value);
  return true; // Actual paths are recorded, never followed by this audit tool.
}

/** Validate the data contract without changing the dossier or following URLs. */
export function validateDossier(dossier) {
  const errors = [];
  const fail = (where, message) => errors.push(`${where}: ${message}`);
  const keys = (value, where, required) => {
    if (!object(value)) { fail(where, 'must be an object'); return false; }
    for (const key of required) if (!own(value, key)) fail(`${where}.${key}`, 'required');
    return true;
  };
  const text = (value, where, allowEmpty = false) => {
    if (typeof value !== 'string' || (!allowEmpty && !nonempty(value))) fail(where, allowEmpty ? 'must be a string' : 'must be a nonempty string');
  };
  const choice = (value, where, allowed) => {
    if (!allowed.includes(value)) fail(where, `must be one of ${allowed.join(', ')}`);
  };
  const boolean = (value, where) => { if (typeof value !== 'boolean') fail(where, 'must be a boolean'); };
  const strings = (value, where) => {
    if (!Array.isArray(value)) { fail(where, 'must be an array of strings'); return; }
    value.forEach((item, index) => text(item, `${where}[${index}]`));
  };
  const date = (value, where) => { if (!timestamp(value)) fail(where, 'must be an ISO 8601 timestamp with a timezone'); };
  const positive = (value, where) => { if (!positiveInteger(value)) fail(where, 'must be a positive integer'); };
  if (!keys(dossier, 'dossier', ['schema_version', 'project', 'config', 'searches', 'papers', 'evidence', 'ideas', 'reviews', 'pilots', 'history'])) return { valid: false, errors, notice: NOTICE };
  if (dossier.schema_version !== 1) fail('schema_version', 'must equal 1');
  if (keys(dossier.project, 'project', ['id', 'question', 'research_type', 'constraints', 'assumptions'])) {
    text(dossier.project.id, 'project.id');
    text(dossier.project.question, 'project.question', true);
    choice(dossier.project.research_type, 'project.research_type', TYPES);
    if (!object(dossier.project.constraints)) fail('project.constraints', 'must be an object');
    strings(dossier.project.assumptions, 'project.assumptions');
  }
  if (keys(dossier.config, 'config', ['ranking_weights'])) {
    const weights = dossier.config.ranking_weights;
    if (keys(weights, 'config.ranking_weights', DIMENSIONS)) {
      if (Object.keys(weights).length !== DIMENSIONS.length) fail('config.ranking_weights', 'must contain exactly the three scoring dimensions');
      for (const key of DIMENSIONS) {
        if (typeof weights[key] !== 'number' || !Number.isFinite(weights[key]) || weights[key] < 0) fail(`config.ranking_weights.${key}`, 'must be a finite nonnegative number');
      }
      const total = DIMENSIONS.reduce((sum, key) => sum + weights[key], 0);
      if (!Number.isFinite(total) || total <= 0) fail('config.ranking_weights', 'sum must be finite and greater than zero');
    }
  }
  const collections = {};
  const ids = {};
  for (const name of ['searches', 'papers', 'evidence', 'ideas', 'reviews', 'pilots', 'history']) {
    if (!Array.isArray(dossier[name])) fail(name, 'must be an array');
    collections[name] = Array.isArray(dossier[name]) ? dossier[name] : [];
    ids[name] = new Set();
    collections[name].forEach((item, index) => {
      if (!object(item)) { fail(`${name}[${index}]`, 'must be an object'); return; }
      if (name !== 'history' || own(item, 'id')) {
        text(item.id, `${name}[${index}].id`);
        if (nonempty(item.id)) {
          if (ids[name].has(item.id)) fail(`${name}[${index}].id`, 'duplicate ID');
          ids[name].add(item.id);
        }
      }
    });
  }
  const reference = (value, where, collection) => {
    text(value, where);
    if (nonempty(value) && !ids[collection].has(value)) fail(where, `unknown ${collection} ID ${value}`);
  };
  const references = (value, where, collection) => {
    strings(value, where);
    if (Array.isArray(value)) value.forEach((id, index) => reference(id, `${where}[${index}]`, collection));
  };
  const visit = (name, required, check) => collections[name].forEach((item, index) => {
    const where = `${name}[${index}]`;
    if (keys(item, where, required)) check(item, where);
  });
  visit('searches', ['id', 'query', 'provider', 'searched_at', 'status', 'scope', 'limitations', 'result_paper_ids'], (item, where) => {
    for (const field of ['query', 'provider', 'scope']) text(item[field], `${where}.${field}`);
    date(item.searched_at, `${where}.searched_at`);
    choice(item.status, `${where}.status`, ['complete', 'partial', 'failed']);
    strings(item.limitations, `${where}.limitations`);
    references(item.result_paper_ids, `${where}.result_paper_ids`, 'papers');
  });
  visit('papers', ['id', 'title', 'year', 'url', 'identifiers', 'version', 'accessed_at'], (item, where) => {
    text(item.title, `${where}.title`);
    text(item.version, `${where}.version`);
    if (item.year !== null && !Number.isInteger(item.year)) fail(`${where}.year`, 'must be an integer or null');
    if (!sourceUrl(item.url)) fail(`${where}.url`, 'must be a valid http, https, or file URL without credentials');
    if (!object(item.identifiers)) fail(`${where}.identifiers`, 'must be an object');
    else for (const [key, value] of Object.entries(item.identifiers)) text(value, `${where}.identifiers.${key}`);
    date(item.accessed_at, `${where}.accessed_at`);
  });
  visit('evidence', ['id', 'paper_id', 'source_version', 'read_scope', 'locator', 'observation', 'polarity'], (item, where) => {
    reference(item.paper_id, `${where}.paper_id`, 'papers');
    text(item.source_version, `${where}.source_version`);
    choice(item.read_scope, `${where}.read_scope`, READ_SCOPES);
    text(item.locator, `${where}.locator`);
    text(item.observation, `${where}.observation`);
    choice(item.polarity, `${where}.polarity`, ['supports', 'contradicts', 'context']);
    if (own(item, 'excerpt')) text(item.excerpt, `${where}.excerpt`);
    if (own(item, 'limitation_origin')) choice(item.limitation_origin, `${where}.limitation_origin`, ['author_stated', 'reader_inferred']);
    if (own(item, 'uncertainty')) text(item.uncertainty, `${where}.uncertainty`, true);
  });
  const evidenceById = new Map(collections.evidence.filter(object).map(item => [item.id, item]));
  visit('ideas', ['id', 'version', 'title', 'question', 'research_type', 'hypothesis', 'contribution', 'evidence_ids', 'search_ids', 'nearest_work', 'novelty', 'feasibility', 'validation'], (item, where) => {
    positive(item.version, `${where}.version`);
    for (const field of ['title', 'question', 'hypothesis', 'contribution']) text(item[field], `${where}.${field}`);
    choice(item.research_type, `${where}.research_type`, TYPES);
    references(item.evidence_ids, `${where}.evidence_ids`, 'evidence');
    references(item.search_ids, `${where}.search_ids`, 'searches');
    if (!Array.isArray(item.nearest_work)) fail(`${where}.nearest_work`, 'must be an array');
    else item.nearest_work.forEach((nearest, index) => {
      const location = `${where}.nearest_work[${index}]`;
      if (!keys(nearest, location, ['paper_id', 'evidence_ids', 'delta', 'decisive'])) return;
      reference(nearest.paper_id, `${location}.paper_id`, 'papers');
      references(nearest.evidence_ids, `${location}.evidence_ids`, 'evidence');
      text(nearest.delta, `${location}.delta`);
      boolean(nearest.decisive, `${location}.decisive`);
      for (const id of Array.isArray(nearest.evidence_ids) ? nearest.evidence_ids : []) {
        const record = evidenceById.get(id);
        if (record && record.paper_id !== nearest.paper_id) fail(`${location}.evidence_ids`, `evidence ${id} belongs to a different paper`);
      }
    });
    if (keys(item.novelty, `${where}.novelty`, ['status', 'reason', 'coverage'])) {
      choice(item.novelty.status, `${where}.novelty.status`, ['distinct', 'incremental', 'duplicate', 'unclear']);
      for (const field of ['reason', 'coverage']) text(item.novelty[field], `${where}.novelty.${field}`);
    }
    if (keys(item.feasibility, `${where}.feasibility`, ['status', 'reason', 'dependencies'])) {
      choice(item.feasibility.status, `${where}.feasibility.status`, ['ready', 'pilot_only', 'blocked', 'unknown']);
      text(item.feasibility.reason, `${where}.feasibility.reason`);
      if (!Array.isArray(item.feasibility.dependencies)) fail(`${where}.feasibility.dependencies`, 'must be an array');
      else item.feasibility.dependencies.forEach((dependency, index) => {
        const location = `${where}.feasibility.dependencies[${index}]`;
        if (!keys(dependency, location, ['name', 'mandatory', 'status', 'basis'])) return;
        text(dependency.name, `${location}.name`);
        boolean(dependency.mandatory, `${location}.mandatory`);
        choice(dependency.status, `${location}.status`, ['met', 'failed', 'unknown']);
        text(dependency.basis, `${location}.basis`);
      });
    }
    const fields = ['prediction', 'falsifier', 'design', 'metric', 'resource_estimate', 'stop_rule'];
    if (keys(item.validation, `${where}.validation`, ['status', ...fields])) {
      choice(item.validation.status, `${where}.validation.status`, ['specified', 'missing']);
      for (const field of fields) text(item.validation[field], `${where}.validation.${field}`, item.validation.status === 'missing');
    }
  });
  visit('reviews', ['id', 'idea_id', 'idea_version', 'basis_hash', 'reviewed_at', 'kind', 'decision', 'reason', 'scores', 'score_reasons', 'penalties', 'limitations'], (item, where) => {
    reference(item.idea_id, `${where}.idea_id`, 'ideas');
    positive(item.idea_version, `${where}.idea_version`);
    if (typeof item.basis_hash !== 'string' || !/^[a-f\d]{64}$/.test(item.basis_hash)) fail(`${where}.basis_hash`, 'must be a lowercase SHA-256 hex digest');
    date(item.reviewed_at, `${where}.reviewed_at`);
    choice(item.kind, `${where}.kind`, ['self', 'independent']);
    choice(item.decision, `${where}.decision`, ['GO', 'HOLD', 'KILL']);
    text(item.reason, `${where}.reason`);
    if (keys(item.scores, `${where}.scores`, DIMENSIONS)) {
      if (Object.keys(item.scores).length !== DIMENSIONS.length) fail(`${where}.scores`, 'must contain exactly the three scoring dimensions');
      for (const field of DIMENSIONS) if (item.scores[field] !== null && (!Number.isInteger(item.scores[field]) || item.scores[field] < 0 || item.scores[field] > 4)) fail(`${where}.scores.${field}`, 'must be an integer from 0 to 4, or null');
    }
    if (keys(item.score_reasons, `${where}.score_reasons`, DIMENSIONS)) {
      if (Object.keys(item.score_reasons).length !== DIMENSIONS.length) fail(`${where}.score_reasons`, 'must contain exactly the three scoring dimensions');
      for (const field of DIMENSIONS) text(item.score_reasons[field], `${where}.score_reasons.${field}`);
    }
    if (!Array.isArray(item.penalties)) fail(`${where}.penalties`, 'must be an array');
    else item.penalties.forEach((penalty, index) => {
      const location = `${where}.penalties[${index}]`;
      if (!keys(penalty, location, ['reason', 'points'])) return;
      text(penalty.reason, `${location}.reason`);
      if (typeof penalty.points !== 'number' || !Number.isFinite(penalty.points) || penalty.points < 0) fail(`${location}.points`, 'must be finite and nonnegative');
    });
    strings(item.limitations, `${where}.limitations`);
  });
  visit('pilots', ['id', 'idea_id', 'idea_version', 'kind', 'outcome', 'artifacts', 'summary', 'limitations'], (item, where) => {
    reference(item.idea_id, `${where}.idea_id`, 'ideas');
    positive(item.idea_version, `${where}.idea_version`);
    choice(item.kind, `${where}.kind`, ['smoke', 'scientific']);
    choice(item.outcome, `${where}.outcome`, ['supported', 'contradicted', 'inconclusive', 'execution_failed', 'not_run']);
    strings(item.artifacts, `${where}.artifacts`);
    if (Array.isArray(item.artifacts)) {
      item.artifacts.forEach((value, index) => { if (!artifact(value)) fail(`${where}.artifacts[${index}]`, 'must be a file path or valid http, https, or file URL'); });
      if (item.outcome !== 'not_run' && item.artifacts.length === 0) fail(`${where}.artifacts`, 'executed attempts need an artifact or log reference');
    }
    text(item.summary, `${where}.summary`);
    strings(item.limitations, `${where}.limitations`);
  });
  visit('history', [], (item, where) => {
    if (own(item, 'idea_id')) reference(item.idea_id, `${where}.idea_id`, 'ideas');
    if (own(item, 'idea_version')) positive(item.idea_version, `${where}.idea_version`);
    if (own(item, 'at')) date(item.at, `${where}.at`);
    if (own(item, 'evidence_ids')) references(item.evidence_ids, `${where}.evidence_ids`, 'evidence');
    for (const field of ['event', 'reason']) if (own(item, field)) text(item[field], `${where}.${field}`);
  });
  return { valid: errors.length === 0, errors, notice: NOTICE };
}

function requireValid(dossier) {
  const result = validateDossier(dossier);
  if (!result.valid) throw new Error(`Invalid dossier:\n${result.errors.join('\n')}`);
}

/** Canonical JSON sorts object keys recursively and preserves array order. */
export function canonicalStringify(value) {
  const seen = new Set();
  const normalize = item => {
    if (item === null || typeof item === 'string' || typeof item === 'boolean') return item;
    if (typeof item === 'number' && Number.isFinite(item)) return item;
    if (!Array.isArray(item) && !object(item)) throw new Error('Only finite JSON values can be fingerprinted');
    if (seen.has(item)) throw new Error('Circular values cannot be fingerprinted');
    seen.add(item);
    const output = Array.isArray(item) ? item.map(normalize) : Object.fromEntries(Object.keys(item).sort().map(key => [key, normalize(item[key])]));
    seen.delete(item);
    return output;
  };
  return JSON.stringify(normalize(value));
}

function basisHash(dossier, idea) {
  return createHash('sha256').update(canonicalStringify({
    project: dossier.project,
    config: dossier.config,
    searches: dossier.searches,
    papers: dossier.papers,
    evidence: dossier.evidence,
    idea,
    pilots: dossier.pilots.filter(pilot => pilot.idea_id === idea.id),
  }), 'utf8').digest('hex');
}

function notEarlier(left, right) {
  const seconds = value => Math.floor(Date.parse(value) / 1000);
  if (seconds(left) !== seconds(right)) return seconds(left) > seconds(right);
  const fraction = value => /\.(\d+)(?:Z|[+-]\d{2}:?\d{2})$/.exec(value)?.[1] ?? '';
  const a = fraction(left), b = fraction(right);
  const width = Math.max(a.length, b.length);
  return a.padEnd(width, '0') >= b.padEnd(width, '0');
}

/** Reviews/history are deliberately excluded; associated pilots are included. */
export function fingerprintIdea(dossier, ideaId) {
  requireValid(dossier);
  const idea = dossier.ideas.find(candidate => candidate.id === ideaId);
  if (!idea) throw new Error(`Unknown idea ID: ${ideaId}`);
  return basisHash(dossier, idea);
}

/** Rank current eligible GO records; unknowns stay HOLD, confirmed blocks KILL. */
export function rankDossier(dossier) {
  requireValid(dossier);
  const output = { ranked: [], held: [], killed: [], notice: NOTICE };
  const evidence = new Map(dossier.evidence.map(record => [record.id, record]));
  const searches = new Map(dossier.searches.map(record => [record.id, record]));
  const deep = record => record && ['section', 'full_text'].includes(record.read_scope);
  const weights = dossier.config.ranking_weights;
  const weightSum = DIMENSIONS.reduce((sum, key) => sum + weights[key], 0);
  for (const idea of dossier.ideas) {
    // Iterating in record order and replacing equal times implements the tie rule.
    let review;
    for (const candidate of dossier.reviews) if (candidate.idea_id === idea.id && (!review || notEarlier(candidate.reviewed_at, review.reviewed_at))) review = candidate;
    const current = review && review.idea_version === idea.version && review.basis_hash === basisHash(dossier, idea);
    const row = { idea_id: idea.id, title: idea.title, decision: 'HOLD', score: null, reasons: [], ...(review ? { review_id: review.id } : {}) };
    // A changed framing may invalidate both favorable and unfavorable judgments.
    // Do not carry an old duplicate/block label across an outdated review.
    if (review && !current) {
      row.reasons = ['Latest review is stale: idea version or basis hash changed; all decisions need reassessment'];
      output.held.push(row);
      continue;
    }
    const mandatory = idea.feasibility.dependencies.filter(dependency => dependency.mandatory);
    const killReasons = [];
    if (idea.novelty.status === 'duplicate') killReasons.push(`Confirmed duplicate: ${idea.novelty.reason}`);
    if (idea.feasibility.status === 'blocked') killReasons.push(`Feasibility blocked: ${idea.feasibility.reason}`);
    for (const dependency of mandatory) if (dependency.status === 'failed') killReasons.push(`Mandatory dependency failed: ${dependency.name}; ${dependency.basis}`);
    if (current && review.decision === 'KILL') killReasons.push(`Current review KILL: ${review.reason}`);
    if (killReasons.length) {
      row.decision = 'KILL'; row.reasons = killReasons; output.killed.push(row); continue;
    }
    const reasons = [];
    if (!review) reasons.push('No review recorded');
    else if (!current) reasons.push('Latest review is stale: idea version or basis hash changed; earlier reviews are not reused');
    else {
      if (review.decision === 'HOLD') reasons.push(`Current review HOLD: ${review.reason}`);
      for (const key of DIMENSIONS) if (review.scores[key] === null) reasons.push(`Unknown score: ${key}`);
    }
    if (!['distinct', 'incremental'].includes(idea.novelty.status)) reasons.push(`Novelty needs evidence: ${idea.novelty.status}`);
    const searched = idea.search_ids.map(id => searches.get(id));
    if (!searched.some(search => ['complete', 'partial'].includes(search.status) && search.result_paper_ids.length > 0)) reasons.push('No completed/partial candidate search with a paper result');
    if (!idea.nearest_work.length) reasons.push('No nearest-work comparison');
    const decisive = idea.nearest_work.filter(nearest => nearest.decisive);
    const hasDeepNearest = nearest => nearest.evidence_ids.some(id => deep(evidence.get(id)));
    if (decisive.length) {
      for (const nearest of decisive) if (!hasDeepNearest(nearest)) reasons.push(`Decisive nearest work lacks section/full_text evidence: ${nearest.paper_id}`);
    } else if (idea.nearest_work.length && !idea.nearest_work.some(hasDeepNearest)) reasons.push('At least one nearest work needs section/full_text evidence');
    if (!idea.evidence_ids.some(id => deep(evidence.get(id)) && evidence.get(id).polarity === 'supports')) reasons.push('No supporting section/full_text evidence for the candidate question or difference');
    if (idea.feasibility.status !== 'ready') reasons.push(`Feasibility is ${idea.feasibility.status}: ${idea.feasibility.reason}`);
    for (const dependency of mandatory) if (dependency.status !== 'met') reasons.push(`Mandatory dependency not verified: ${dependency.name}`);
    if (idea.validation.status !== 'specified') reasons.push('Validation is not specified');
    if (reasons.length) { row.reasons = reasons; output.held.push(row); continue; }
    const total = DIMENSIONS.reduce((sum, key) => sum + (review.scores[key] / 4) * (weights[key] / weightSum) * 100, 0);
    const penalty = review.penalties.reduce((sum, item) => sum + item.points, 0);
    row.decision = 'GO';
    row.score = Math.round(Math.max(0, Math.min(100, total - penalty)) * 100) / 100;
    row.reasons = [review.reason, 'Recorded machine-checkable necessary conditions met; host evidence review is still required'];
    output.ranked.push(row);
  }
  output.ranked.sort((a, b) => b.score - a.score || (a.idea_id < b.idea_id ? -1 : a.idea_id > b.idea_id ? 1 : 0));
  return output;
}

export function createInitialDossier(name) {
  if (typeof name !== 'string' || name.length > 64 || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) throw new Error('Project name must use lowercase letters and digits separated by single hyphens (1–64 characters)');
  return {
    schema_version: 1,
    project: { id: name, question: '', research_type: 'empirical', constraints: {}, assumptions: [] },
    config: { ranking_weights: { scientific_value: 40, differentiation: 35, testability: 25 } },
    searches: [], papers: [], evidence: [], ideas: [], reviews: [], pilots: [], history: [],
  };
}

function inside(root, target) {
  const relative = path.relative(root, target);
  return relative === '' || (!path.isAbsolute(relative) && relative !== '..' && !relative.startsWith(`..${path.sep}`));
}

async function rejectDirectoryLinks(directory) {
  let cursor = path.resolve(directory);
  while (true) {
    const stat = await fs.lstat(cursor);
    if (stat.isSymbolicLink()) throw new Error(`Directory links are not allowed: ${cursor}`);
    if (!stat.isDirectory()) throw new Error(`Root must be an existing directory: ${cursor}`);
    const parent = path.dirname(cursor);
    if (parent === cursor) break;
    cursor = parent;
  }
}

/** The only writing API: create a fresh project below an existing real root. */
export async function initProject(root, name) {
  const dossier = createInitialDossier(name);
  if (!nonempty(root)) throw new Error('An existing root directory is required');
  const resolvedRoot = path.resolve(root);
  await rejectDirectoryLinks(resolvedRoot);
  const realRoot = await fs.realpath(resolvedRoot);
  const target = path.resolve(realRoot, name);
  if (!inside(realRoot, target) || target === realRoot) throw new Error('Project path escapes the root');
  const skillRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  if (inside(skillRoot, target)) throw new Error('Projects must be created in a user workspace, outside the installed skill directory');
  try { await fs.lstat(target); throw new Error(`Project path already exists: ${target}`); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  await fs.mkdir(target); // No recursive creation, and EEXIST remains an error.
  try {
    await rejectDirectoryLinks(target);
    const dossierPath = path.join(target, 'dossier.json');
    await fs.writeFile(dossierPath, `${JSON.stringify(dossier, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
    return { project_dir: target, dossier_path: dossierPath };
  } catch (error) {
    // Only remove our new empty directory; never recurse or remove user contents.
    await fs.rmdir(target).catch(() => {});
    throw error;
  }
}

async function main(args) {
  const [command, ...rest] = args;
  if (command === 'init') {
    const options = {};
    if (rest.length !== 4) throw new Error('Usage: init --root <existing-directory> --name <slug>');
    for (let index = 0; index < rest.length; index += 2) {
      const flag = rest[index];
      if (!['--root', '--name'].includes(flag) || own(options, flag)) throw new Error('Expected one --root and one --name');
      options[flag] = rest[index + 1];
    }
    return { ok: true, ...await initProject(options['--root'], options['--name']) };
  }
  if (!['validate', 'fingerprint', 'rank'].includes(command) || rest.length !== (command === 'fingerprint' ? 2 : 1)) throw new Error('Usage: validate <dossier.json> | fingerprint <dossier.json> <idea_id> | rank <dossier.json>');
  const dossier = JSON.parse(await fs.readFile(rest[0], 'utf8'));
  if (command === 'validate') {
    const result = validateDossier(dossier);
    if (!result.valid) process.exitCode = 1;
    return result;
  }
  if (command === 'fingerprint') return { idea_id: rest[1], basis_hash: fingerprintIdea(dossier, rest[1]), notice: NOTICE };
  return rankDossier(dossier);
}

const entryPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (entryPath && entryPath === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(result => process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)).catch(error => {
    process.exitCode = 1;
    process.stdout.write(`${JSON.stringify({ ok: false, error: error.message, notice: NOTICE }, null, 2)}\n`);
  });
}
