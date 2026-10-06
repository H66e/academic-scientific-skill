#!/usr/bin/env node
// Explicit, bounded source acquisition. No dossier writes, models, or GO decisions.
import { createHash } from 'node:crypto';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';
import https from 'node:https';
import { Readable } from 'node:stream';

const NOTICE = 'Acquisition and identity checks only; source existence does not prove faithful reading, coverage, novelty, or scientific correctness.';
const hash = value => createHash('sha256').update(value).digest('hex');
const integer = (value, name, fallback, max) => {
  const n = value === undefined ? fallback : Number(value);
  if (!Number.isInteger(n) || n < 1 || n > max) throw new Error(`${name} must be an integer from 1 to ${max}`);
  return n;
};
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
// Whitespace/case normalization must preserve meaningful title symbols (e.g. < vs >).
const titleKey = value => value.normalize('NFC').toLowerCase().replace(/\s+/gu, ' ').trim();

export function normalizeDoi(value) {
  if (!nonempty(value)) throw new Error('DOI required');
  const doi = value.trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '').replace(/^doi:\s*/i, '');
  if (!/^10\.\d{4,9}\/\S+$/i.test(doi) || /[\x00-\x20<>]/.test(doi) || doi.length > 512) throw new Error('Invalid DOI syntax');
  return doi.toLowerCase();
}

export function normalizeArxiv(value) {
  if (!nonempty(value)) throw new Error('arXiv ID required');
  const id = value.trim().replace(/^https?:\/\/(?:www\.)?arxiv\.org\/(?:abs|pdf|html)\//i, '').replace(/^arxiv:\s*/i, '').replace(/\.pdf$/i, '');
  if (!/^(?:\d{4}\.\d{4,5}|[a-z][a-z.\-]+\/\d{7})(?:v[1-9]\d*)?$/i.test(id)) throw new Error('Invalid arXiv ID syntax');
  return id;
}

export function isPublicAddress(address) {
  const family = isIP(address);
  if (family === 4) {
    const [a, b, c] = address.split('.').map(Number);
    return !(a === 0 || a === 10 || a === 127 || a >= 224 || (a === 100 && b >= 64 && b <= 127) ||
      (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) ||
      (a === 192 && (b === 168 || (b === 0 && (c === 0 || c === 2)) || (b === 88 && c === 99))) ||
      (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) || (a === 203 && b === 0 && c === 113));
  }
  // Global unicast only; conservatively exclude transition and documentation ranges.
  if (family !== 6 || !/^[23]/i.test(address) || /^(?:2002:|3ffe:)/i.test(address)) return false;
  const parts = address.toLowerCase().split(':');
  return !(parts[0] === '2001' && (parseInt(parts[1] || '0', 16) <= 0x1ff || parseInt(parts[1], 16) === 0xdb8));
}

function publicUrl(value) {
  const url = new URL(value);
  const host = url.hostname.toLowerCase();
  if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443') ||
      isIP(host.replace(/^\[|\]$/g, '')) || !host.includes('.') || /(?:^|\.)(?:localhost|local|internal)$/.test(host)) {
    throw new Error('Only public HTTPS domain URLs without credentials or custom ports are accepted');
  }
  url.hash = '';
  return url;
}

// DNS resolution is checked once and pinned to the TLS request, avoiding a second lookup.
function pinnedFetch(url, { signal, address, headers }) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, {
      signal, headers, rejectUnauthorized: true,
      lookup(_host, options, callback) {
        callback(null, options?.all ? [address] : address.address, address.family);
      }
    }, response => {
      const mapped = new Headers();
      for (const [key, value] of Object.entries(response.headers)) if (value !== undefined) mapped.set(key, Array.isArray(value) ? value.join(', ') : value);
      resolve({ status: response.statusCode, headers: mapped, body: Readable.toWeb(response) });
    });
    request.on('error', reject);
  });
}

function fixedApiUrl(url) {
  return (url.hostname === 'api.crossref.org' && (url.pathname === '/works' || /^\/works\/10\.\d{4,9}%2f.+$/i.test(url.pathname))) ||
    (url.hostname === 'export.arxiv.org' && url.pathname === '/api/query');
}

function aborted(signal) {
  if (signal.aborted) throw new Error('Request timeout');
}

async function abortable(promise, signal) {
  aborted(signal);
  let onAbort;
  const stop = new Promise((_, reject) => {
    onAbort = () => reject(new Error('Request timeout'));
    signal.addEventListener('abort', onAbort, { once: true });
  });
  try { return await Promise.race([promise, stop]); }
  finally { signal.removeEventListener('abort', onAbort); }
}

function transport(options, dependencies, trustedResource = null) {
  const timeout = integer(options.timeout, 'timeout', 15000, 60000);
  const maxBytes = integer(options.maxBytes, 'maxBytes', 2 * 1024 * 1024, 20 * 1024 * 1024);
  const budget = integer(options.byteBudget, 'byteBudget', 10 * 1024 * 1024, 100 * 1024 * 1024);
  const maxRequests = integer(options.requestBudget, 'requestBudget', 8, 20);
  const requests = [];
  let totalBytes = 0;
  return {
    summary: () => ({ requests, bytes_received: totalBytes, byte_budget: budget, request_budget: maxRequests }),
    async get(input, allowedHosts) {
      let url = publicUrl(input);
      for (let redirect = 0; redirect <= 3; redirect++) {
        if (!allowedHosts.has(url.hostname.toLowerCase())) throw new Error('Redirect outside explicitly permitted source host');
        if (options.trustedProviderTransport && !(trustedResource ? url.href === trustedResource : fixedApiUrl(url))) throw new Error('Trusted-provider transport is limited to fixed official API/resource paths');
        if (options.trustedProviderTransport && process.env.NODE_TLS_REJECT_UNAUTHORIZED === '0') throw new Error('Trusted-provider transport requires TLS certificate verification');
        if (requests.length >= maxRequests) throw new Error('Request budget exhausted');
        const record = { url: url.href, status: null, bytes: 0, transport_mode: options.trustedProviderTransport ? 'trusted_provider_tls' : 'public_dns_pinned_tls' };
        requests.push(record);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeout);
        let reader;
        try {
          let addresses;
          if (!options.trustedProviderTransport) {
            addresses = await abortable((dependencies.lookup ?? lookup)(url.hostname, { all: true, verbatim: true }), controller.signal);
            if (!Array.isArray(addresses) || addresses.length === 0 || addresses.some(item => !isPublicAddress(item.address))) throw new Error('Source resolves to a non-public or unsupported address');
          }
          aborted(controller.signal);
          const response = await abortable((dependencies.fetch ?? (options.trustedProviderTransport ? fetch : pinnedFetch))(url.href, {
            signal: controller.signal, redirect: 'manual', address: addresses?.[0],
            headers: { 'user-agent': 'ai-research-mentor/0.3 (bounded research acquisition)', 'accept-encoding': 'identity', accept: '*/*' }
          }), controller.signal);
          record.status = response.status;
          if ([301, 302, 303, 307, 308].includes(response.status)) {
            await response.body?.cancel();
            const location = response.headers.get('location');
            if (!location || redirect === 3) throw new Error('Missing redirect location or redirect budget exhausted');
            url = publicUrl(new URL(location, url).href);
            continue;
          }
          if (response.status === 429) throw new Error(`Rate limited (HTTP 429; Retry-After=${response.headers.get('retry-after') ?? 'unknown'}); no automatic retries`);
          if (response.status < 200 || response.status >= 300) {
            await response.body?.cancel();
            return { status: response.status, url: url.href, bytes: Buffer.alloc(0), headers: response.headers };
          }
          const declared = Number(response.headers.get('content-length'));
          if (declared > maxBytes || declared > budget - totalBytes) throw new Error('Response exceeds byte budget');
          if ((response.headers.get('content-encoding') ?? 'identity') !== 'identity') throw new Error('Unexpected compressed response; extraction not attempted');
          if (!response.body) throw new Error('Response body missing');
          reader = response.body.getReader();
          const chunks = [];
          while (true) {
            const next = await abortable(reader.read(), controller.signal);
            if (next.done) break;
            const bytes = Buffer.from(next.value);
            totalBytes += bytes.length;
            record.bytes += bytes.length;
            if (record.bytes > maxBytes || totalBytes > budget) throw new Error('Response exceeds byte budget');
            chunks.push(bytes);
          }
          const bytes = Buffer.concat(chunks);
          record.response_sha256 = hash(bytes);
          return { status: response.status, url: url.href, bytes, headers: response.headers };
        } catch (error) {
          record.error = controller.signal.aborted ? 'Request timeout' : error.message;
          controller.abort();
          if (reader) await reader.cancel().catch(() => {});
          throw new Error(record.error);
        } finally { clearTimeout(timer); }
      }
      throw new Error('Redirect budget exhausted');
    }
  };
}

function crossrefPaper(item, at) {
  const doi = normalizeDoi(item.DOI);
  const title = Array.isArray(item.title) ? item.title[0] : null;
  if (!nonempty(title)) throw new Error(`Missing deposited title for DOI ${doi}`);
  const date = item.published?.['date-parts']?.[0] ?? item.issued?.['date-parts']?.[0];
  return {
    id: `doi-${hash(doi).slice(0, 24)}`, title: title.trim(), year: Number.isInteger(date?.[0]) ? date[0] : null,
    url: `https://doi.org/${doi.split('/').map(encodeURIComponent).join('/')}`, identifiers: { doi }, version: 'unknown', accessed_at: at,
    authors: (item.author ?? []).map(author => [author.given, author.family].filter(nonempty).join(' ')).filter(nonempty),
    source_metadata: { provider: 'crossref', type: item.type ?? null, deposited_at: item.deposited?.['date-time'] ?? null,
      provider_relevance_score: Number.isFinite(item.score) ? item.score : null },
    version_note: 'Registration metadata does not establish the technical version actually read.'
  };
}

/** Return contract-compatible searches/papers. Records are never merged or written automatically. */
export async function searchCrossref(options = {}, dependencies = {}) {
  if (!nonempty(options.query)) throw new Error('query required');
  if (options.query.length > 2000) throw new Error('query exceeds 2000 characters');
  if (options.searchId !== undefined && (!nonempty(options.searchId) || /[\x00-\x1f]/.test(options.searchId))) throw new Error('searchId must be a nonempty ID');
  const rows = integer(options.rows, 'rows', 10, 100);
  const pages = integer(options.pages, 'pages', 1, 5);
  if (options.offline) return { status: 'offline', planned_query: options.query, searches: [], papers: [], transport: { requests: [], bytes_received: 0 }, notice: NOTICE };
  const at = new Date().toISOString();
  const search = {
    id: options.searchId ?? `search-crossref-${hash(`${at}:${options.query}`).slice(0, 16)}`,
    query: options.query.trim(), provider: 'crossref', searched_at: at, status: 'failed',
    scope: `Crossref deposited work metadata; bibliographic query ordered by provider relevance score descending; at most ${pages} page(s) of ${rows} records`,
    limitations: ['Crossref coverage is not exhaustive for AI preprints; metadata search is not full-text reading.'], result_paper_ids: []
  };
  const papers = new Map();
  const network = transport(options, dependencies);
  let cursor = '*', fetchedPages = 0, exhausted = false, malformed = false;
  try {
    for (let page = 0; page < pages; page++) {
      const url = new URL('https://api.crossref.org/works');
      url.searchParams.set('query.bibliographic', search.query);
      url.searchParams.set('rows', String(rows));
      url.searchParams.set('cursor', cursor);
      // Cursor defaults are not necessarily relevance ordered; make discovery ordering explicit.
      url.searchParams.set('sort', 'score');
      url.searchParams.set('order', 'desc');
      if (options.mailto) url.searchParams.set('mailto', options.mailto);
      if (page) await (dependencies.pause ?? (ms => new Promise(resolve => setTimeout(resolve, ms))))(1000);
      const response = await network.get(url.href, new Set(['api.crossref.org']));
      if (response.status !== 200) throw new Error(`Crossref HTTP ${response.status}`);
      const payload = JSON.parse(response.bytes.toString('utf8'));
      if (payload.status !== 'ok' || !Array.isArray(payload.message?.items)) throw new Error('Unexpected Crossref response');
      const message = payload.message;
      search.total_results_reported = Number.isFinite(message['total-results']) ? message['total-results'] : null;
      for (const item of message.items) {
        try { const paper = crossrefPaper(item, at); papers.set(paper.id, paper); }
        catch (error) { malformed = true; search.limitations.push(`Skipped unidentifiable result: ${error.message}`); }
      }
      fetchedPages++;
      exhausted = message.items.length < rows || (search.total_results_reported !== null && papers.size >= search.total_results_reported);
      if (exhausted) break;
      if (!nonempty(message['next-cursor']) || message['next-cursor'] === cursor) {
        search.limitations.push('Pagination cursor missing or unchanged before coverage was exhausted.');
        break;
      }
      cursor = message['next-cursor'];
    }
    search.status = exhausted && !malformed ? 'complete' : 'partial';
    if (!exhausted) search.limitations.push('Returned results truncated by page/request budget or pagination boundary.');
  } catch (error) {
    search.status = fetchedPages ? 'partial' : 'failed';
    search.limitations.push(error.message);
  }
  search.result_paper_ids = [...papers.keys()];
  search.pages_received = fetchedPages;
  return { searches: [search], papers: [...papers.values()], transport: network.summary(), notice: NOTICE };
}

function decodeEntities(value) {
  const named = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' };
  return value.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (whole, key) => {
    if (key[0] !== '#') return named[key.toLowerCase()] ?? whole;
    const n = key[1].toLowerCase() === 'x' ? parseInt(key.slice(2), 16) : Number(key.slice(1));
    return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff) ? String.fromCodePoint(n) : whole;
  });
}

const xmlText = (xml, tag) => decodeEntities(new RegExp(`<${tag}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/${tag}>`, 'i').exec(xml)?.[1]?.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim() ?? '');

/** Identity resolution reports metadata separately from interpretation. Offline never becomes not_found. */
export async function verifyIdentifier(options = {}, dependencies = {}) {
  if (Boolean(options.doi) === Boolean(options.arxiv)) throw new Error('Provide exactly one DOI or arXiv ID');
  if (options.expectTitle !== undefined && !nonempty(options.expectTitle)) throw new Error('expectTitle must be a nonempty string');
  if (options.expectYear !== undefined) integer(options.expectYear, 'expectYear', undefined, 9999);
  const kind = options.doi ? 'doi' : 'arxiv';
  const identifier = kind === 'doi' ? normalizeDoi(options.doi) : normalizeArxiv(options.arxiv);
  const result = { kind, identifier, checked_at: new Date().toISOString(), status: 'unresolved', reason: '', paper: null, comparison: null, notice: NOTICE };
  if (options.offline) return { ...result, status: 'offline', reason: 'No network verification requested.' };
  const network = transport(options, dependencies);
  let acquiredResponse = false;
  try {
    const url = kind === 'doi' ? `https://api.crossref.org/works/${encodeURIComponent(identifier)}` : `https://export.arxiv.org/api/query?id_list=${encodeURIComponent(identifier)}`;
    const response = await network.get(url, new Set([kind === 'doi' ? 'api.crossref.org' : 'export.arxiv.org']));
    acquiredResponse = response.status === 200;
    if (response.status === 404) {
      result.reason = kind === 'doi' ? 'DOI not found in Crossref; it may belong to another registration agency.' : 'arXiv endpoint returned HTTP 404.';
    } else if (response.status !== 200) throw new Error(`Identity endpoint HTTP ${response.status}`);
    else if (kind === 'doi') {
      const payload = JSON.parse(response.bytes.toString('utf8'));
      if (payload.status !== 'ok' || !payload.message) throw new Error('Unexpected Crossref identity response');
      result.paper = crossrefPaper(payload.message, result.checked_at);
      if (result.paper.identifiers.doi !== identifier) throw new Error('Returned DOI differs from requested DOI');
      result.status = 'resolved';
    } else {
      const xml = response.bytes.toString('utf8');
      if (/<!DOCTYPE|<!ENTITY/i.test(xml) || !/<feed\b/i.test(xml)) throw new Error('Unsupported or malformed Atom response');
      const entry = /<entry\b[^>]*>([\s\S]*?)<\/entry>/i.exec(xml)?.[1];
      if (!entry) result.reason = 'No matching entry reported by arXiv.';
      else {
        const returnedUrl = xmlText(entry, 'id');
        const title = xmlText(entry, 'title');
        if (!/^https?:\/\/arxiv\.org\/abs\//i.test(returnedUrl) || !nonempty(title)) throw new Error('arXiv returned an error or unidentifiable entry');
        const resolved = normalizeArxiv(returnedUrl);
        if (resolved.replace(/v\d+$/, '') !== identifier.replace(/v\d+$/, '') || (/v\d+$/.test(identifier) && resolved !== identifier)) throw new Error('Returned arXiv identity/version differs from request');
        const published = xmlText(entry, 'published');
        const year = /^\d{4}-\d\d-\d\dT/.test(published) ? Number(published.slice(0, 4)) : null;
        result.paper = { id: `arxiv-${hash(resolved.replace(/v\d+$/, '')).slice(0, 24)}`, title, year,
          url: `https://arxiv.org/abs/${resolved}`, identifiers: { arxiv: resolved },
          version: /v\d+$/.test(resolved) ? `arXiv ${/v\d+$/.exec(resolved)[0]}` : 'unknown', accessed_at: result.checked_at };
        result.status = 'resolved';
      }
    }
    if (result.paper) {
      result.comparison = {
        title: options.expectTitle === undefined ? 'not_checked' : titleKey(options.expectTitle) === titleKey(result.paper.title) ? 'match' : 'different',
        year: options.expectYear === undefined ? 'not_checked' : result.paper.year === null ? 'unknown' : Number(options.expectYear) === result.paper.year ? 'match' : 'different'
      };
      result.reason = 'Identifier resolved; metadata comparisons require human review and do not verify source claims.';
    }
  } catch (error) {
    // A 200 header alone does not establish that a usable response was acquired.
    result.status = acquiredResponse ? 'failed' : 'unresolved';
    result.reason = error.message;
    result.paper = null;
  }
  return { ...result, transport: network.summary() };
}

/** Lossy HTML text blocks; offsets refer to the original decoded HTML, not PDF pages. */
export function extractHtml(html, sourceUrl) {
  const blocks = [], stack = [];
  const blockTags = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'pre', 'figcaption', 'td', 'th']);
  const skipped = new Set(['script', 'style', 'template', 'noscript']);
  let current = null;
  const flush = end => {
    if (!current) return;
    const text = decodeEntities(current.text).replace(/\s+/g, ' ').trim();
    if (text) blocks.push({ kind: current.kind, text, locator: { source_url: sourceUrl, html_id: current.anchor, start_offset: current.start, end_offset: end, offset_unit: 'UTF-16 code units' } });
    current.text = '';
    current = null;
  };
  for (const token of html.matchAll(/<!--[\s\S]*?-->|<(?:[^"'<>]|"[^"]*"|'[^']*')+>|[^<]+|</g)) {
    const raw = token[0], offset = token.index;
    if (raw.startsWith('<!--')) continue;
    const tagMatch = /^<\s*(\/?)\s*([a-z][\w:-]*)\b/i.exec(raw);
    if (!tagMatch) { if (!stack.some(item => skipped.has(item.tag)) && current) current.text += ` ${raw}`; continue; }
    const closing = Boolean(tagMatch[1]), tag = tagMatch[2].toLowerCase();
    if (closing) {
      const index = stack.map(item => item.tag).lastIndexOf(tag);
      const closesBlock = Boolean(current) && index >= 0 && stack.slice(index).some(item => item.frame === current);
      if (closesBlock) flush(offset + raw.length);
      if (index >= 0) stack.splice(index);
      if (closesBlock) {
        current = [...stack].reverse().find(item => item.frame)?.frame ?? null;
        if (current) current.start = offset + raw.length;
      }
      continue;
    }
    const id = /\bid\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/i.exec(raw);
    const anchor = id ? decodeEntities(id[1] ?? id[2] ?? id[3]) : stack.findLast?.(item => item.id)?.id ?? [...stack].reverse().find(item => item.id)?.id ?? null;
    const startsBlock = !stack.some(item => skipped.has(item.tag)) && blockTags.has(tag);
    if (startsBlock) {
      flush(offset);
      current = { kind: tag, anchor, start: offset, text: '' };
    }
    if (!/\/\s*>$/.test(raw) && !['br', 'img', 'hr', 'meta', 'link', 'input', 'wbr', 'source', 'area', 'base', 'embed', 'param', 'track', 'col'].includes(tag)) stack.push({ tag, id: id ? anchor : null, frame: startsBlock ? current : null });
  }
  flush(html.length);
  return blocks;
}

/** Save only a new file inside an existing, non-symlink root and existing parent directories. */
export async function saveSourceBytes(root, output, bytes) {
  if (!nonempty(root) || !nonempty(output) || path.isAbsolute(output) || /(^|[\\/])\.\.?([\\/]|$)/.test(output) || /[\x00-\x1f:]/.test(output)) throw new Error('Output must be a safe relative file path under an explicit root');
  if (output.split(/[\\/]/).some(part => !part || /[. ]$/.test(part) || /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part))) throw new Error('Output contains an ambiguous or reserved filename');
  const absoluteRoot = path.resolve(root);
  const parsed = path.parse(absoluteRoot);
  let cursor = parsed.root;
  for (const part of absoluteRoot.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    cursor = path.join(cursor, part);
    const info = await fs.lstat(cursor);
    if (info.isSymbolicLink() || !info.isDirectory()) throw new Error('Root path contains a symlink or non-directory');
  }
  const target = path.resolve(absoluteRoot, output);
  const relative = path.relative(absoluteRoot, target);
  if (!relative || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) throw new Error('Output escapes project root');
  cursor = absoluteRoot;
  for (const part of path.dirname(relative).split(path.sep).filter(part => part && part !== '.')) {
    cursor = path.join(cursor, part);
    const info = await fs.lstat(cursor);
    if (info.isSymbolicLink() || !info.isDirectory()) throw new Error('Output parent contains a symlink or non-directory');
  }
  const file = await fs.open(target, 'wx', 0o600);
  try { await file.writeFile(bytes); } finally { await file.close(); }
  return target;
}

export async function acquireFulltext(options = {}, dependencies = {}) {
  if (options.format !== undefined && !['html', 'pdf'].includes(options.format)) throw new Error('format must be html or pdf');
  if (options.trustedProviderTransport && !options.arxiv) throw new Error('Trusted-provider transport is unavailable for arbitrary URL acquisition; use a fixed arXiv ID');
  if (Boolean(options.url) === Boolean(options.arxiv)) throw new Error('Provide exactly one explicit URL or arXiv ID');
  if (Boolean(options.out) !== Boolean(options.root)) throw new Error('Saving requires both root and out');
  const id = options.arxiv ? normalizeArxiv(options.arxiv) : null;
  const input = id ? `https://arxiv.org/${options.format === 'pdf' ? 'pdf' : 'html'}/${id}` : options.url;
  const permitted = new Set([publicUrl(input).hostname.toLowerCase()]);
  const result = { requested_url: input, retrieved_at: options.offline ? null : new Date().toISOString(), status: 'unresolved', content_kind: 'unknown', reading_scope: 'not_assigned', saved_path: null, blocks: [], limitations: [], notice: NOTICE };
  if (options.offline) return { ...result, status: 'offline', limitations: ['No acquisition requested; source availability and body content remain unknown.'], transport: { requests: [], bytes_received: 0 } };
  const network = transport(options, dependencies, options.trustedProviderTransport ? publicUrl(input).href : null);
  try {
    const response = await network.get(input, permitted);
    result.source_url = response.url;
    if ([404, 410].includes(response.status)) return { ...result, status: 'not_available', limitations: [`Requested representation returned HTTP ${response.status}; this does not establish that the paper does not exist.`], transport: network.summary() };
    if (response.status !== 200) throw new Error(`Full-text source HTTP ${response.status}; no fallback or access bypass attempted`);
    result.byte_length = response.bytes.length;
    result.sha256 = hash(response.bytes);
    result.content_type = response.headers.get('content-type') ?? 'unknown';
    if (response.bytes.subarray(0, 5).toString('ascii') === '%PDF-') {
      result.status = 'needs_host_extraction';
      result.limitations.push('PDF bytes acquired only; no text, OCR, page, figure, or equation reading has occurred.');
    } else if (/^(?:text\/html|application\/xhtml\+xml)(?:;|$)/i.test(result.content_type)) {
      const charset = /charset\s*=\s*["']?([^;\s"']+)/i.exec(result.content_type)?.[1] ?? 'utf-8';
      let text;
      try { text = new TextDecoder(charset, { fatal: true }).decode(response.bytes); }
      catch { throw new Error('Unsupported charset or invalid encoded HTML; use host extraction'); }
      result.blocks = extractHtml(text, response.url);
      result.extraction_status = result.blocks.length ? 'html_blocks_extracted' : 'no_text_blocks';
      result.status = result.blocks.length ? 'needs_host_review' : 'needs_host_extraction';
      result.limitations.push('Lossy HTML blocks; host must confirm this is the paper body, verify equations/tables/figures, and assign actual reading scope. Unknown named entities are preserved.');
    } else throw new Error('Unsupported content type or invalid PDF signature; no text extraction attempted');
    if (options.out) result.saved_path = await saveSourceBytes(options.root, options.out, response.bytes);
    else result.limitations.push('Original source bytes were not saved; provide root and a new out path when a durable source artifact is needed.');
    if (id && !/v\d+$/.test(id)) result.limitations.push('Unversioned arXiv request; retrieved technical version must be confirmed before creating evidence.');
  } catch (error) {
    result.status = 'failed';
    result.limitations.push(error.message);
  }
  return { ...result, transport: network.summary() };
}

async function cli() {
  const [command, ...args] = process.argv.slice(2);
  if (!['search', 'verify', 'fulltext'].includes(command)) throw new Error('Usage: research_sources.mjs search --query <text> | verify --doi <id> | verify --arxiv <id> | fulltext --arxiv <id> [--format pdf] | fulltext --url <explicit-url>');
  const shared = ['timeout', 'max-bytes', 'byte-budget', 'request-budget', 'offline'];
  const allowed = new Set([...shared, ...(command === 'search' ? ['query', 'rows', 'pages', 'mailto', 'search-id', 'trusted-provider-transport'] : command === 'verify' ? ['doi', 'arxiv', 'expect-title', 'expect-year', 'trusted-provider-transport'] : ['arxiv', 'url', 'format', 'root', 'out', 'trusted-provider-transport'])]);
  const options = {};
  for (let index = 0; index < args.length; index++) {
    const name = args[index].replace(/^--/, '');
    if (!args[index].startsWith('--') || !allowed.has(name)) throw new Error(`Unknown option: ${args[index]}`);
    const key = name.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    if (Object.hasOwn(options, key)) throw new Error(`Repeated option: ${args[index]}`);
    if (['offline', 'trusted-provider-transport'].includes(name)) options[key] = true;
    else {
      const value = args[++index];
      if (!nonempty(value) || value.startsWith('--')) throw new Error(`Value required for --${name}`);
      options[key] = value;
    }
  }
  if (options.format && !['html', 'pdf'].includes(options.format)) throw new Error('format must be html or pdf');
  const output = await (command === 'search' ? searchCrossref : command === 'verify' ? verifyIdentifier : acquireFulltext)(options);
  process.stdout.write(`${JSON.stringify(output, null, 2)}\n`);
  if (command === 'search' ? output.searches[0]?.status === 'failed' : ['failed', 'unresolved', 'not_available'].includes(output.status)) process.exitCode = 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  cli().catch(error => { process.stderr.write(`${error.message}\n`); process.exitCode = 1; });
}
