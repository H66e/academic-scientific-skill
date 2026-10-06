// Protocol fixtures based on public metadata; these tests make no external requests.
import test from 'node:test';
import assert from 'node:assert/strict';
import { searchCrossref, acquireFulltext } from '../../skills/ai-research-mentor/scripts/research_sources.mjs';
import { draftDossier, renderCard, exportBibtex } from '../../skills/ai-research-mentor/scripts/research_outputs.mjs';
import { validateDossier, rankDossier } from '../../skills/ai-research-mentor/scripts/research_audit.mjs';

const metadata = { DOI: '10.18653/v1/2023.emnlp-main.298',
  title: ['GQA: Training Generalized Multi-Query Transformer Models from Multi-Head Checkpoints'],
  published: { 'date-parts': [[2023]] }, author: [{ given: 'Joshua', family: 'Ainslie' }] };
const dependencies = {
  lookup: async () => [{ address: '93.184.216.34', family: 4 }],
  fetch: async () => new Response(JSON.stringify({ status: 'ok', message: { items: [metadata], 'total-results': 1 } }), { headers: { 'content-type': 'application/json' } }),
};

test('source records pass the dossier contract and export citations without manufacturing a research approval', async () => {
  const sources = await searchCrossref({ query: metadata.title[0], rows: 2 }, dependencies);
  const notes = { question: 'Under which conditions does the KV grouping tradeoff change?', type: 'measurement',
    known: ['Metadata fixture only; the technical sections have not been read.'], decision: 'HOLD' };
  const dossier = draftDossier(notes, { name: 'workflow-fixture' });
  dossier.searches = sources.searches;
  dossier.papers = sources.papers;
  assert.equal(validateDossier(dossier).valid, true);
  assert.equal(dossier.papers[0].version, 'unknown');
  assert.deepEqual(dossier.evidence, []);
  assert.deepEqual(rankDossier(dossier).ranked, []);
  const bibliography = exportBibtex(dossier);
  assert.match(bibliography.bibtex, /10\.18653\/v1\/2023\.emnlp-main\.298/);
  assert.equal(bibliography.exported_count, 1);
  assert.match(renderCard(notes), /HOLD/);
});

test('a failed actual request stays failed and is never turned into empty-search novelty evidence', async () => {
  const sources = await searchCrossref({ query: 'a research question' }, { ...dependencies, fetch: async () => { throw new Error('protocol fixture connection unavailable'); } });
  const dossier = draftDossier({ question: 'Q', limitations: ['Search failed; novelty is unassessed.'] }, { name: 'failed-fixture' });
  dossier.searches = sources.searches;
  dossier.papers = sources.papers;
  assert.equal(dossier.searches[0].status, 'failed');
  assert.equal(validateDossier(dossier).valid, true);
  assert.deepEqual(dossier.papers, []);
  assert.deepEqual(dossier.ideas, []);
  assert.equal(exportBibtex(dossier).exported_count, 0);
});

test('landing-page HTML remains unassigned reading material throughout the workflow', async () => {
  const source = await acquireFulltext({ url: 'https://example.org/paper' }, { ...dependencies,
    fetch: async () => new Response('<html><h1 id="title">Paper landing page</h1><p id="abstract">An abstract fixture.</p></html>', { headers: { 'content-type': 'text/html' } }) });
  assert.equal(source.status, 'needs_host_review');
  assert.equal(source.reading_scope, 'not_assigned');
  assert.equal(source.content_kind, 'unknown');
  const dossier = draftDossier({ question: 'Q', limitations: ['Downloaded HTML has not been established as the paper body.'] }, { name: 'html-fixture' });
  assert.deepEqual(dossier.evidence, []);
  assert.deepEqual(rankDossier(dossier).ranked, []);
});
