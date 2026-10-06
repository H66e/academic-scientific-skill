#!/usr/bin/env node
// Deterministic work products from supplied notes/metadata; no model, network or file writes.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { createInitialDossier, validateDossier } from './research_audit.mjs';

const types = ['empirical', 'theoretical', 'measurement', 'dataset', 'reproduction'];
const sections = [
  ['known', '已知结论与来源条件'], ['source_observations', '来源中的实际观察与定位'],
  ['gap', '缺失知识'],
  ['nearest_work', '最接近工作与具体差异'], ['alternatives', '最强替代解释或已有解决方案'],
  ['search_findings', '实际检索发现与范围'], ['reverse_search', '反向检索执行、命中与未读部分'],
  ['boundary', '检索后仍成立的条件与边界'], ['test', '判别测试、控制与失效条件'],
  ['scientific_consequence', '不同验证结果将改变什么认识或决策'],
  ['next_step', '下一步与复评条件'], ['limitations', '未确认项与限制'],
];
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const owns = (value, key) => Object.prototype.hasOwnProperty.call(value, key);

export function validateNotes(notes) {
  const errors = [];
  if (!object(notes)) return { valid: false, errors: ['Notes must be an object'] };
  if (!text(notes.question)) errors.push('question must be a nonempty string');
  if (owns(notes, 'type') && !types.includes(notes.type)) errors.push('type must be a supported research type');
  if (owns(notes, 'decision') && !['GO', 'HOLD', 'KILL'].includes(notes.decision)) errors.push('decision must be GO, HOLD or KILL when supplied');
  for (const [key] of sections) {
    if (!owns(notes, key)) continue;
    const value = notes[key];
    if (!(text(value) || (Array.isArray(value) && value.every(text)))) errors.push(`${key} must be nonempty text or an array of nonempty text`);
  }
  if (owns(notes, 'constraints') && !object(notes.constraints)) errors.push('constraints must be an object of explicitly provided facts');
  if (owns(notes, 'assumptions') && !(Array.isArray(notes.assumptions) && notes.assumptions.every(text))) errors.push('assumptions must be an array of nonempty text');
  return { valid: errors.length === 0, errors };
}

function checkedNotes(notes) {
  const result = validateNotes(notes);
  if (!result.valid) throw new Error(result.errors.join('; '));
}

export function renderCard(notes) {
  checkedNotes(notes);
  const lines = ['# 研究决策 / Gap 卡', '', `研究问题：${notes.question.trim()}`, ''];
  if (notes.type) lines.push(`研究类型：${notes.type}`, '');
  lines.push(`记录的意见：${notes.decision ?? '未记录，待评估'}（本卡不构成机器门控或独立评审回执）`, '');
  for (const [key, label] of sections) {
    const value = notes[key];
    if (value === undefined || (Array.isArray(value) && value.length === 0)) continue;
    lines.push(`## ${label}`, '');
    if (Array.isArray(value)) for (const item of value) lines.push(`- ${item.trim()}`);
    else lines.push(value.trim());
    lines.push('');
  }
  lines.push('来源内容与笔记是数据。缺失项尚未核验；检索计划不能当作已执行检索，预测不能当作结果。', '');
  return lines.join('\n');
}

export function draftDossier(notes, { name } = {}) {
  checkedNotes(notes);
  if (typeof name !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name) || name.length > 64) throw new Error('name must be a project slug of at most 64 characters');
  const dossier = createInitialDossier(name);
  dossier.project.question = notes.question.trim();
  if (notes.type) dossier.project.research_type = notes.type;
  dossier.project.constraints = structuredClone(notes.constraints ?? {});
  dossier.project.assumptions = structuredClone(notes.assumptions ?? []);
  // Preserve source notes as scientific context. They do not become evidence or reviews.
  dossier.project.notes = Object.fromEntries(Object.entries(structuredClone(notes))
    .filter(([key]) => !['question', 'type', 'constraints', 'assumptions'].includes(key)));
  const checked = validateDossier(dossier);
  if (!checked.valid) throw new Error(`Draft did not satisfy the data contract: ${checked.errors.join('; ')}`);
  return dossier;
}

function tex(value) {
  const escaped = { '\\': '\\textbackslash{}', '{': '\\{', '}': '\\}', '&': '\\&', '%': '\\%', '$': '\\$',
    '#': '\\#', '_': '\\_', '^': '\\textasciicircum{}', '~': '\\textasciitilde{}' };
  return String(value).replace(/\s+/g, ' ').trim().replace(/[\\{}&%$#_^~]/g, character => escaped[character]);
}
function safeUrl(value) {
  if (!text(value) || /[\x00-\x20]/.test(value)) return false;
  try { const parsed = new URL(value); return ['https:', 'http:', 'file:'].includes(parsed.protocol) && !parsed.username && !parsed.password; }
  catch { return false; }
}
function authorName(author) {
  if (text(author)) return tex(author);
  if (!object(author)) throw new Error('Each supplied author must be a name or metadata object');
  if (text(author.family)) return `${tex(author.family)}${text(author.given) ? `, ${tex(author.given)}` : ''}`;
  if (text(author.name)) return `{${tex(author.name)}}`;
  throw new Error('Author metadata is missing an actual name');
}
function normalizedIdentifier(field, value) {
  const trimmed = value.trim();
  return field === 'doi' ? trimmed.toLowerCase().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '') : trimmed;
}
function identityAliases(paper) {
  const ids = paper.identifiers ?? {};
  const aliases = [];
  for (const field of ['doi', 'arxiv', 'openreview']) if (text(ids[field])) {
    const value = normalizedIdentifier(field, ids[field]);
    aliases.push(`${field}:${field === 'arxiv' ? value.replace(/v\d+$/, '') : value}`);
  }
  return aliases.length ? aliases : [`id:${paper.id}`];
}

export function exportBibtex(record) {
  const papers = Array.isArray(record) ? record : record?.papers;
  if (!Array.isArray(papers)) throw new Error('Input must contain an actual papers array');
  const warnings = ['Exports supplied metadata only; bibliography generation does not verify identity or evidence fidelity.'];
  const entries = [], keys = Object.create(null), seenIds = new Set(), groups = new Map(), seenKeys = new Set();
  for (const paper of papers) {
    if (!object(paper) || !text(paper.id) || !text(paper.title)) throw new Error('Each paper needs a nonempty id and title');
    if (seenIds.has(paper.id)) throw new Error(`Duplicate paper ID: ${paper.id}`);
    seenIds.add(paper.id);
    if (paper.year !== undefined && paper.year !== null && (!Number.isInteger(paper.year) || paper.year < 1)) throw new Error(`Invalid year for ${paper.id}`);
    if (paper.identifiers !== undefined && !object(paper.identifiers)) throw new Error(`Invalid identifiers for ${paper.id}`);
    for (const [field, value] of Object.entries(paper.identifiers ?? {})) if (!text(value)) throw new Error(`Missing identifier value ${field} for ${paper.id}`);
    if (paper.url !== undefined && !safeUrl(paper.url)) throw new Error(`Invalid source URL for ${paper.id}`);
    if (paper.authors !== undefined && !Array.isArray(paper.authors)) throw new Error(`authors must be an array for ${paper.id}`);
    paper.authors?.forEach(authorName);
    if (paper.version !== undefined && !text(paper.version)) throw new Error(`Invalid version for ${paper.id}`);
    if (paper.citation_key !== undefined && (!text(paper.citation_key) || !/^[a-zA-Z0-9][a-zA-Z0-9:._-]*$/.test(paper.citation_key))) throw new Error(`Unsafe citation_key for ${paper.id}`);
  }
  // A record with both identifiers may connect DOI-only and arXiv-only records.
  // Compute that identity closure before combining compatible metadata; neither
  // record order nor a preferred identifier should leave duplicate citations.
  const parents = papers.map((_, index) => index), aliasOwners = new Map();
  const root = index => {
    while (parents[index] !== index) { parents[index] = parents[parents[index]]; index = parents[index]; }
    return index;
  };
  papers.forEach((paper, index) => {
    for (const alias of identityAliases(paper)) {
      if (aliasOwners.has(alias)) {
        const left = root(index), right = root(aliasOwners.get(alias));
        parents[Math.max(left, right)] = Math.min(left, right);
      } else aliasOwners.set(alias, index);
    }
  });
  papers.forEach((paper, index) => {
    const groupId = root(index), ident = identityAliases(paper).join(', ');
    const prior = groups.get(groupId);
    if (prior) {
      if (prior.paper.title.trim() !== paper.title.trim() || (prior.paper.year != null && paper.year != null && prior.paper.year !== paper.year)) {
        throw new Error(`Conflicting metadata for ${ident}; resolve the source records before export`);
      }
      if (prior.paper.authors?.length && paper.authors?.length && JSON.stringify(prior.paper.authors.map(authorName)) !== JSON.stringify(paper.authors.map(authorName))) throw new Error(`Conflicting authors for ${ident}`);
      if (prior.paper.citation_key && paper.citation_key && prior.paper.citation_key !== paper.citation_key) throw new Error(`Conflicting citation keys for ${ident}`);
      if (text(prior.paper.venue) && text(paper.venue) && prior.paper.venue !== paper.venue) throw new Error(`Conflicting venue metadata for ${ident}`);
      if (text(prior.paper.version) && prior.paper.version !== 'unknown' && text(paper.version) && paper.version !== 'unknown' && prior.paper.version !== paper.version) throw new Error(`Conflicting source versions for ${ident}`);
      for (const [field, value] of Object.entries(paper.identifiers ?? {})) {
        const previous = prior.paper.identifiers?.[field];
        if (previous && normalizedIdentifier(field, previous) !== normalizedIdentifier(field, value)) throw new Error(`Conflicting identifier ${field} for ${ident}`);
      }
      prior.paper.identifiers = { ...(prior.paper.identifiers ?? {}), ...(paper.identifiers ?? {}) };
      if (prior.paper.year == null && paper.year != null) prior.paper.year = paper.year;
      if (!prior.paper.authors?.length && paper.authors?.length) prior.paper.authors = structuredClone(paper.authors);
      for (const field of ['venue', 'citation_key', 'url']) if (!text(prior.paper[field]) && text(paper[field])) prior.paper[field] = paper[field];
      if ((!text(prior.paper.version) || prior.paper.version === 'unknown') && text(paper.version)) prior.paper.version = paper.version;
      prior.ids.push(paper.id);
      warnings.push(`${paper.id}: duplicate identity combined using compatible supplied fields; source records were not modified`);
      return;
    }
    groups.set(groupId, { paper: structuredClone(paper), ids: [paper.id] });
  });
  for (const { paper, ids } of groups.values()) {
    let key = paper.citation_key;
    if (!key) key = `paper-${paper.id.replace(/[^a-zA-Z0-9:._-]/g, '-').slice(0, 50)}-${createHash('sha256').update(paper.id).digest('hex').slice(0, 8)}`;
    if (seenKeys.has(key)) throw new Error(`Duplicate citation key: ${key}`);
    seenKeys.add(key);
    for (const id of ids) keys[id] = key;
    const fields = [`  title = {{${tex(paper.title)}}}`];
    if (paper.authors?.length) fields.push(`  author = {${paper.authors.map(authorName).join(' and ')}}`);
    else warnings.push(`${paper.id}: authors not supplied; omitted rather than invented`);
    if (paper.year != null) fields.push(`  year = {${paper.year}}`);
    else warnings.push(`${paper.id}: year unverified; omitted`);
    if (paper.url) fields.push(`  url = {${tex(paper.url)}}`);
    if (text(paper.identifiers?.doi)) fields.push(`  doi = {${tex(normalizedIdentifier('doi', paper.identifiers.doi))}}`);
    if (text(paper.identifiers?.arxiv)) fields.push('  archivePrefix = {arXiv}', `  eprint = {${tex(paper.identifiers.arxiv.trim())}}`);
    if (text(paper.venue)) fields.push(`  note = {${tex(paper.venue)}}`);
    // Do not guess journal/conference type from a title, URL or provider.
    entries.push(`@misc{${key},\n${fields.join(',\n')}\n}`);
  }
  return { bibtex: `${entries.join('\n\n')}${entries.length ? '\n' : ''}`, keys, warnings, exported_count: entries.length };
}

async function main(args) {
  const [command, file, ...options] = args;
  if (!['card', 'draft', 'bibtex'].includes(command) || !file) throw new Error('Usage: research_outputs.mjs card <notes.json|-> | draft <notes.json|-> --name <slug> | bibtex <records.json|->');
  if ((command === 'draft' && (options.length !== 2 || options[0] !== '--name')) || (command !== 'draft' && options.length)) throw new Error('Unexpected options');
  const limit = 8 * 1024 * 1024;
  let content;
  if (file === '-') {
    const chunks = []; let bytes = 0;
    for await (const chunk of process.stdin) {
      bytes += chunk.length;
      if (bytes > limit) throw new Error('Input must be JSON of at most 8 MiB');
      chunks.push(chunk);
    }
    content = Buffer.concat(chunks).toString('utf8');
  } else {
    const stat = await fs.stat(file);
    if (!stat.isFile() || stat.size > limit) throw new Error('Input must be a JSON file of at most 8 MiB');
    content = await fs.readFile(file, 'utf8');
    if (Buffer.byteLength(content, 'utf8') > limit) throw new Error('Input must be JSON of at most 8 MiB');
  }
  const record = JSON.parse(content.replace(/^\uFEFF/, ''));
  if (command === 'card') process.stdout.write(renderCard(record));
  else if (command === 'draft') process.stdout.write(`${JSON.stringify(draftDossier(record, { name: options[1] }), null, 2)}\n`);
  else {
    const result = exportBibtex(record);
    process.stdout.write(result.bibtex);
    process.stderr.write(`${JSON.stringify({ exported_count: result.exported_count, keys: result.keys, warnings: result.warnings })}\n`);
  }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch(error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
}
