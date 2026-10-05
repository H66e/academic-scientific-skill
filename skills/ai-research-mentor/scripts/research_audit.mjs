#!/usr/bin/env node
// Structural checks and bounded ranking; never a proof of scientific merit.
// Public APIs: createInitialDossier, validateDossier, canonicalStringify,
// fingerprintIdea, rankingConfigHash, migrateDossier, rankDossier, initProject.
// Importing this file has no effects.
import { createHash } from 'node:crypto';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIMENSIONS = ['scientific_value', 'differentiation', 'testability'];
const TYPES = ['empirical', 'theoretical', 'measurement', 'dataset', 'reproduction'];
const READ_SCOPES = ['metadata', 'abstract', 'section', 'full_text'];
const ROLES = ['motivation', 'nearest_work', 'contradiction', 'assumption', 'feasibility', 'validation', 'context'];
const TARGETS = ['problem', 'hypothesis', 'nearest_work', 'prerequisite', 'validation'];
const NOTICE = 'Structural checks only: passing does not establish source authenticity, literature coverage, novelty, or scientific correctness.';
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const positiveInteger = value => Number.isInteger(value) && value > 0;
const hasFact = (value, seen = new Set()) => {
  if (typeof value === 'string') return nonempty(value);
  if (typeof value === 'number') return Number.isFinite(value);
  if (typeof value === 'boolean') return true;
  if (!Array.isArray(value) && !object(value)) return false;
  if (seen.has(value)) return false;
  seen.add(value);
  return Object.values(value).some(child => hasFact(child, seen));
};

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
  const warnings = [];
  const fail = (where, message) => errors.push(`${where}: ${message}`);
  const warn = (where, message) => warnings.push(`${where}: ${message}`);
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
  if (!keys(dossier, 'dossier', ['schema_version', 'project', 'config', 'searches', 'papers', 'evidence', 'ideas', 'reviews', 'pilots', 'history'])) return { valid: false, errors, warnings, notice: NOTICE };
  if (![1, 2].includes(dossier.schema_version)) fail('schema_version', 'must equal 1 or 2');
  const v2 = dossier.schema_version === 2;
  if (v2 && !own(dossier, 'screening')) fail('screening', 'required');
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
  for (const name of ['searches', 'papers', 'evidence', 'ideas', 'reviews', 'pilots', 'history', ...(v2 ? ['screening'] : [])]) {
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
    if (['section', 'full_text'].includes(item.read_scope) && typeof item.locator === 'string' &&
        (/^(?:paper|article|full[ _-]?text|全文|整篇论文)$/i.test(item.locator.trim()) || /^https?:\/\/\S+$/i.test(item.locator.trim()))) {
      warn(`${where}.locator`, 'Deep evidence needs a precise section, page, figure, equation, or searchable passage');
    }
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
    if (v2) {
      if (!Array.isArray(item.evidence_links)) fail(`${where}.evidence_links`, 'must be an array');
      else item.evidence_links.forEach((link, index) => {
        const location = `${where}.evidence_links[${index}]`;
        if (!keys(link, location, ['evidence_id', 'role', 'target', 'claim', 'relation', 'decision_relevant'])) return;
        reference(link.evidence_id, `${location}.evidence_id`, 'evidence');
        choice(link.role, `${location}.role`, ROLES);
        choice(link.target, `${location}.target`, TARGETS);
        choice(link.relation, `${location}.relation`, ['supports', 'contradicts', 'context']);
        text(link.claim, `${location}.claim`);
        boolean(link.decision_relevant, `${location}.decision_relevant`);
        const attached = new Set([...(Array.isArray(item.evidence_ids) ? item.evidence_ids : []),
          ...(Array.isArray(item.nearest_work) ? item.nearest_work.flatMap(nearest => Array.isArray(nearest?.evidence_ids) ? nearest.evidence_ids : []) : [])]);
        if (!attached.has(link.evidence_id)) fail(location, 'Evidence link must belong to this candidate or its nearest work');
      });
    }
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
      if (item.novelty.status === 'distinct' && Array.isArray(item.search_ids) && !item.search_ids.length) warn(`${where}.novelty`, 'Distinct label has no candidate search; ranking will HOLD');
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
  visit('reviews', ['id', 'idea_id', 'idea_version', v2 ? 'review_basis_hash' : 'basis_hash', 'reviewed_at', 'kind', 'decision', 'reason', 'scores', 'score_reasons', 'penalties', 'limitations',
    ...(v2 ? ['decision_scope', 'recommended_stage', 'decision_basis'] : [])], (item, where) => {
    reference(item.idea_id, `${where}.idea_id`, 'ideas');
    positive(item.idea_version, `${where}.idea_version`);
    const hashKey = v2 ? 'review_basis_hash' : 'basis_hash';
    if (typeof item[hashKey] !== 'string' || !/^[a-f\d]{64}$/.test(item[hashKey])) fail(`${where}.${hashKey}`, 'must be a lowercase SHA-256 hex digest');
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
    if (v2) {
      choice(item.decision_scope, `${where}.decision_scope`, ['scientific_framing', 'current_constraints']);
      choice(item.recommended_stage, `${where}.recommended_stage`, ['information_test', 'pilot', 'full_validation']);
      const basis = item.decision_basis;
      if (keys(basis, `${where}.decision_basis`, ['type', 'evidence_ids', 'pilot_ids', 'dependency_names', 'constraint_keys', 'explanation'])) {
        choice(basis.type, `${where}.decision_basis.type`, ['advance', 'insufficient', 'duplicate', 'scientific_refutation', 'constraints']);
        references(basis.evidence_ids, `${where}.decision_basis.evidence_ids`, 'evidence');
        references(basis.pilot_ids, `${where}.decision_basis.pilot_ids`, 'pilots');
        strings(basis.dependency_names, `${where}.decision_basis.dependency_names`);
        strings(basis.constraint_keys, `${where}.decision_basis.constraint_keys`);
        text(basis.explanation, `${where}.decision_basis.explanation`);
      }
      if (item.kind === 'independent') {
        for (const field of ['author_context', 'evaluator_context']) text(item[field], `${where}.${field}`);
        if (nonempty(item.author_context) && item.author_context === item.evaluator_context) fail(`${where}.evaluator_context`, 'Must be different from the author context');
        if (!artifact(item.artifact)) fail(`${where}.artifact`, 'Independent review needs its actual receipt path or URL');
      }
      if (own(item, 'confidence')) {
        if (keys(item.confidence, `${where}.confidence`, DIMENSIONS)) {
          if (Object.keys(item.confidence).length !== DIMENSIONS.length) fail(`${where}.confidence`, 'Must contain exactly the three scoring dimensions');
          for (const field of DIMENSIONS) {
            choice(item.confidence[field], `${where}.confidence.${field}`, ['low', 'medium', 'high']);
            if (item.decision === 'GO' && item.confidence[field] === 'low') warn(`${where}.confidence.${field}`, 'Low-confidence GO needs explicit missing evidence and a bounded next step; confidence does not change scores');
          }
        }
        if (keys(item.confidence_reasons, `${where}.confidence_reasons`, DIMENSIONS)) {
          if (Object.keys(item.confidence_reasons).length !== DIMENSIONS.length) fail(`${where}.confidence_reasons`, 'Must contain exactly the three scoring dimensions');
          for (const field of DIMENSIONS) text(item.confidence_reasons[field], `${where}.confidence_reasons.${field}`);
        }
      }
    }
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
  if (v2) {
    const searches = new Map(collections.searches.filter(object).map(item => [item.id, item]));
    visit('screening', ['id', 'search_id', 'paper_id', 'idea_ids', 'stage', 'decision', 'reason', 'screened_at'], (item, where) => {
      reference(item.search_id, `${where}.search_id`, 'searches');
      reference(item.paper_id, `${where}.paper_id`, 'papers');
      references(item.idea_ids, `${where}.idea_ids`, 'ideas');
      choice(item.stage, `${where}.stage`, ['metadata', 'title_abstract', 'full_text']);
      choice(item.decision, `${where}.decision`, ['include', 'exclude', 'uncertain']);
      text(item.reason, `${where}.reason`);
      date(item.screened_at, `${where}.screened_at`);
      const search = searches.get(item.search_id);
      if (Array.isArray(search?.result_paper_ids) && !search.result_paper_ids.includes(item.paper_id)) fail(`${where}.paper_id`, 'Paper must have been recorded in this search result');
      if (item.decision === 'uncertain' && item.idea_ids?.length) warn(where, 'Candidate-related screening is unresolved; do not claim complete coverage');
      if (item.decision === 'exclude' && Array.isArray(item.idea_ids)) {
        for (const ideaId of item.idea_ids) {
          const idea = collections.ideas.find(idea => idea?.id === ideaId);
          if (Array.isArray(idea?.nearest_work) && idea.nearest_work.some(nearest => nearest.paper_id === item.paper_id)) warn(where, `Excluded paper is also nearest work for ${ideaId}; explain the screening scope`);
        }
      }
    });
  }
  // Old reviews may refer to superseded candidate links. Check the cross-references
  // only for an actually current review, so editing an idea does not corrupt history.
  if (v2 && errors.length === 0) dossier.reviews.forEach((review, index) => {
    const idea = dossier.ideas.find(idea => idea.id === review.idea_id);
    if (review.idea_version !== idea.version || review.review_basis_hash !== basisHash(dossier, idea)) return;
    const where = `reviews[${index}].decision_basis`;
    const basis = review.decision_basis;
    const attached = new Set([...idea.evidence_ids, ...idea.nearest_work.flatMap(nearest => nearest.evidence_ids)]);
    for (const id of basis.evidence_ids) if (!attached.has(id)) fail(`${where}.evidence_ids`, `Evidence ${id} is not attached to this candidate`);
    for (const id of basis.pilot_ids) {
      const pilot = dossier.pilots.find(pilot => pilot.id === id);
      if (pilot.idea_id !== idea.id || pilot.idea_version !== idea.version) fail(`${where}.pilot_ids`, `Pilot ${id} is not from this candidate version`);
    }
    for (const name of basis.dependency_names) if (!idea.feasibility.dependencies.some(dependency => dependency.name === name)) fail(`${where}.dependency_names`, `Unknown current dependency ${name}`);
    for (const key of basis.constraint_keys) if (!own(dossier.project.constraints, key)) fail(`${where}.constraint_keys`, `Unknown current constraint ${key}`);
  });
  return { valid: errors.length === 0, errors, warnings, notice: NOTICE };
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
  if (dossier.schema_version === 2) return reviewBasisHash(dossier, idea);
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

const digest = value => createHash('sha256').update(canonicalStringify(value), 'utf8').digest('hex');
const without = (record, excluded) => Object.fromEntries(Object.entries(record).filter(([key]) => !excluded.includes(key)));
const byId = records => [...records].sort((a, b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
const canonicalOrder = (a, b) => {
  const left = canonicalStringify(a), right = canonicalStringify(b);
  return left < right ? -1 : left > right ? 1 : 0;
};

function reviewBasisHash(dossier, idea) {
  const screening = dossier.screening.filter(record => record.idea_ids.includes(idea.id));
  const searchIds = new Set([...idea.search_ids, ...screening.map(record => record.search_id)]);
  const searches = dossier.searches.filter(record => searchIds.has(record.id));
  const evidenceIds = new Set([...idea.evidence_ids, ...idea.nearest_work.flatMap(record => record.evidence_ids),
    ...idea.evidence_links.map(link => link.evidence_id)]);
  const evidence = dossier.evidence.filter(record => evidenceIds.has(record.id));
  const paperIds = new Set([...searches.flatMap(record => record.result_paper_ids), ...evidence.map(record => record.paper_id),
    ...idea.nearest_work.map(record => record.paper_id), ...screening.map(record => record.paper_id)]);
  const semanticIdea = without(idea, ['created_at', 'updated_at', 'formatting']);
  semanticIdea.evidence_ids = [...idea.evidence_ids].sort();
  semanticIdea.search_ids = [...idea.search_ids].sort();
  semanticIdea.nearest_work = idea.nearest_work.map(record => ({ ...record, evidence_ids: [...record.evidence_ids].sort() }))
    .sort(canonicalOrder);
  semanticIdea.evidence_links = [...idea.evidence_links].sort(canonicalOrder);
  return digest({
    schema_version: 2,
    project: without(dossier.project, ['id', 'created_at', 'updated_at', 'formatting']),
    idea: semanticIdea,
    searches: byId(searches).map(record => ({ ...record, result_paper_ids: [...record.result_paper_ids].sort() })),
    papers: byId(dossier.papers.filter(record => paperIds.has(record.id))).map(record => without(record, ['accessed_at', 'created_at', 'updated_at', 'formatting'])),
    evidence: byId(evidence),
    screening: byId(screening).map(record => ({ ...without(record, ['screened_at']), idea_ids: [idea.id] })),
    pilots: byId(dossier.pilots.filter(record => record.idea_id === idea.id)),
  });
}

/** Preferences have their own digest; they do not invalidate scientific reviews. */
export function rankingConfigHash(dossier) {
  requireValid(dossier);
  return digest(dossier.config.ranking_weights);
}

/** Migration is pure and does not manufacture new evidence or a current review. */
export function migrateDossier(dossier) {
  requireValid(dossier);
  const migrated = JSON.parse(JSON.stringify(dossier));
  if (migrated.schema_version === 2) return migrated;
  migrated.schema_version = 2;
  migrated.screening ??= [];
  for (const idea of migrated.ideas) idea.evidence_links ??= [];
  for (const review of migrated.reviews) migrated.history.push({
    event: 'schema_v1_review_archived', idea_id: review.idea_id, idea_version: review.idea_version,
    reason: 'Schema v1 review retained as history; new evidence links and a v2 review require reassessment.',
    original_review: review, requires_reassessment: true,
  });
  migrated.reviews = [];
  requireValid(migrated);
  return migrated;
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

/** Rank current eligible GO records; labels alone cannot justify KILL. */
export function rankDossier(dossier) {
  requireValid(dossier);
  const output = { ranked: [], held: [], killed: [], ranking_config_hash: rankingConfigHash(dossier), notice: NOTICE };
  if (dossier.schema_version === 1) {
    output.held = dossier.ideas.map(idea => ({ idea_id: idea.id, title: idea.title, decision: 'HOLD', score: null,
      reasons: ['Schema v1 needs migration and reassessment; legacy hashes are not current v2 reviews'] }));
    return output;
  }
  const evidence = new Map(dossier.evidence.map(record => [record.id, record]));
  const searches = new Map(dossier.searches.map(record => [record.id, record]));
  const pilots = new Map(dossier.pilots.map(record => [record.id, record]));
  const deep = record => record && ['section', 'full_text'].includes(record.read_scope);
  const weights = dossier.config.ranking_weights;
  const weightSum = DIMENSIONS.reduce((sum, key) => sum + weights[key], 0);
  for (const idea of dossier.ideas) {
    // Iterating in record order and replacing equal times implements the tie rule.
    let review;
    for (const candidate of dossier.reviews) if (candidate.idea_id === idea.id && (!review || notEarlier(candidate.reviewed_at, review.reviewed_at))) review = candidate;
    const hash = basisHash(dossier, idea);
    const current = review && review.idea_version === idea.version && review.review_basis_hash === hash;
    const row = { idea_id: idea.id, title: idea.title, decision: 'HOLD', score: null, reasons: [], ...(review ? { review_id: review.id } : {}) };
    // A changed framing may invalidate both favorable and unfavorable judgments.
    // Do not carry an old duplicate/block label across an outdated review.
    if (review && !current) {
      row.reasons = ['Latest review is stale: idea version or basis hash changed; all decisions need reassessment'];
      output.held.push(row);
      continue;
    }
    const mandatory = idea.feasibility.dependencies.filter(dependency => dependency.mandatory);
    const basis = current ? review.decision_basis : null;
    if (current && review.decision === 'KILL') {
      let justified = false;
      if (basis.type === 'duplicate' && review.decision_scope === 'scientific_framing' && idea.novelty.status === 'duplicate') {
        const decisive = idea.nearest_work.filter(nearest => nearest.decisive);
        justified = decisive.length > 0 && decisive.every(nearest => nearest.evidence_ids.some(id => basis.evidence_ids.includes(id) && deep(evidence.get(id))));
      } else if (basis.type === 'scientific_refutation' && review.decision_scope === 'scientific_framing') {
        justified = idea.evidence_links.some(link => link.decision_relevant && link.target === 'hypothesis' && link.relation === 'contradicts' &&
          basis.evidence_ids.includes(link.evidence_id) && deep(evidence.get(link.evidence_id))) ||
          basis.pilot_ids.some(id => {
            const pilot = pilots.get(id);
            return pilot.idea_id === idea.id && pilot.idea_version === idea.version && pilot.kind === 'scientific' &&
              pilot.outcome === 'contradicted' && pilot.artifacts.length > 0;
          });
      } else if (basis.type === 'constraints' && review.decision_scope === 'current_constraints') {
        const failed = mandatory.filter(dependency => dependency.status === 'failed');
        const confirmed = basis.constraint_keys.some(key => {
          const constraint = dossier.project.constraints[key];
          return object(constraint) && constraint.status === 'confirmed' && nonempty(constraint.source) &&
            own(constraint, 'value') && hasFact(constraint.value);
        });
        justified = confirmed && (idea.feasibility.status === 'blocked' || failed.some(dependency => basis.dependency_names.includes(dependency.name)));
      }
      if (justified) {
        row.decision = 'KILL'; row.decision_scope = review.decision_scope;
        row.reasons = [`Current ${basis.type} KILL (${review.decision_scope}): ${review.reason}`, basis.explanation,
          'Recorded necessary conditions only; host must verify the cited evidence and constraints'];
        output.killed.push(row); continue;
      }
      row.reasons = ['Current KILL lacks reason-specific decisive evidence or confirmed constraints; labels alone do not justify rejection'];
      output.held.push(row); continue;
    }
    const reasons = [];
    if (!review) reasons.push('No review recorded');
    else if (!current) reasons.push('Latest review is stale: idea version or basis hash changed; earlier reviews are not reused');
    else {
      if (review.decision === 'HOLD') reasons.push(`Current review HOLD: ${review.reason}`);
      for (const key of DIMENSIONS) if (review.scores[key] === null) reasons.push(`Unknown score: ${key}`);
      if (basis.type !== 'advance') reasons.push('GO needs an explicit advance decision basis');
      if (review.recommended_stage === 'information_test') reasons.push('Information gathering remains HOLD; GO requires a bounded scientific pilot or validation');
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
    const relevant = idea.evidence_links.filter(link => link.decision_relevant &&
      ['motivation', 'nearest_work', 'contradiction', 'assumption', 'validation'].includes(link.role) && deep(evidence.get(link.evidence_id)));
    if (!relevant.length) reasons.push('No decision-relevant section/full_text evidence linked to this candidate');
    if (current && !relevant.some(link => basis.evidence_ids.includes(link.evidence_id))) reasons.push('Review decision basis must cite decision-relevant deep candidate evidence');
    if (idea.evidence_links.some(link => link.decision_relevant && link.relation === 'contradicts' && ['hypothesis', 'prerequisite', 'validation'].includes(link.target))) {
      reasons.push('Decision-relevant contradiction to the current hypothesis, prerequisite, or validation needs reassessment');
    }
    if (dossier.pilots.some(pilot => pilot.idea_id === idea.id && pilot.idea_version === idea.version &&
      pilot.kind === 'scientific' && pilot.outcome === 'contradicted')) {
      reasons.push('A scientific pilot contradicts this candidate version; a fresh GO label cannot erase the refutation');
    }
    if (idea.feasibility.status !== 'ready') reasons.push(`Feasibility is ${idea.feasibility.status}: ${idea.feasibility.reason}`);
    for (const dependency of mandatory) if (dependency.status !== 'met') reasons.push(`Mandatory dependency not verified: ${dependency.name}`);
    if (idea.validation.status !== 'specified') reasons.push('Validation is not specified');
    if (current && review.recommended_stage === 'full_validation' && !dossier.reviews.some(peer => peer.idea_id === idea.id &&
      peer.idea_version === idea.version && peer.review_basis_hash === hash && peer.kind === 'independent' && peer.decision === 'GO' &&
      peer.decision_basis.type === 'advance' && peer.recommended_stage !== 'information_test' &&
      DIMENSIONS.every(key => peer.scores[key] !== null) && relevant.some(link => peer.decision_basis.evidence_ids.includes(link.evidence_id)))) {
      reasons.push('Full validation needs a current independent GO receipt; consider a bounded pilot instead');
    }
    if (reasons.length) { row.reasons = reasons; output.held.push(row); continue; }
    const total = DIMENSIONS.reduce((sum, key) => sum + (review.scores[key] / 4) * (weights[key] / weightSum) * 100, 0);
    const penalty = review.penalties.reduce((sum, item) => sum + item.points, 0);
    row.decision = 'GO';
    row.recommended_stage = review.recommended_stage;
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
    schema_version: 2,
    project: { id: name, question: '', research_type: 'empirical', constraints: {}, assumptions: [] },
    config: { ranking_weights: { scientific_value: 40, differentiation: 35, testability: 25 } },
    searches: [], papers: [], screening: [], evidence: [], ideas: [], reviews: [], pilots: [], history: [],
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
  if (!['validate', 'fingerprint', 'rank', 'migrate'].includes(command) || rest.length !== (command === 'fingerprint' ? 2 : 1)) throw new Error('Usage: validate <dossier.json> | fingerprint <dossier.json> <idea_id> | rank <dossier.json> | migrate <dossier.json>');
  const dossier = JSON.parse(await fs.readFile(rest[0], 'utf8'));
  if (command === 'validate') {
    const result = validateDossier(dossier);
    if (!result.valid) process.exitCode = 1;
    return result;
  }
  if (command === 'fingerprint') return { idea_id: rest[1], [dossier.schema_version === 2 ? 'review_basis_hash' : 'basis_hash']: fingerprintIdea(dossier, rest[1]), notice: NOTICE };
  if (command === 'migrate') return migrateDossier(dossier);
  return rankDossier(dossier);
}

const entryPath = process.argv[1] ? path.resolve(process.argv[1]) : '';
if (entryPath && entryPath === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then(result => process.stdout.write(`${JSON.stringify(result, null, 2)}\n`)).catch(error => {
    process.exitCode = 1;
    process.stdout.write(`${JSON.stringify({ ok: false, error: error.message, notice: NOTICE }, null, 2)}\n`);
  });
}
