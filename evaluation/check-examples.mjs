// Readonly verification that public example records remain valid and version-bound.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateDossier, rankDossier } from '../skills/ai-research-mentor/scripts/research_audit.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const results = [];
for (const type of ['empirical', 'theoretical', 'measurement']) {
  const directory = path.join(root, 'examples', `${type}-example`);
  const record = JSON.parse(await fs.readFile(path.join(directory, 'dossier.json'), 'utf8'));
  const readme = await fs.readFile(path.join(directory, 'README.md'), 'utf8');
  if (!readme.includes('SYNTHETIC EXAMPLE — NOT A REAL SCIENTIFIC CLAIM')) throw new Error(`Example lacks clear synthetic provenance: ${type}`);
  const checked = validateDossier(record);
  if (!checked.valid) throw new Error(`${type}: ${checked.errors.join('; ')}`);
  const ranked = rankDossier(record);
  const expected = type === 'measurement' ? ranked.held : ranked.ranked;
  if (expected.length !== 1 || ranked.killed.length !== 0) throw new Error(`Example review or intended next step is stale: ${type}`);
  results.push({ type, valid: true, decision: expected[0].decision, synthetic: true });
}
process.stdout.write(`${JSON.stringify({ examples: results, note: 'Synthetic schema examples, not scientific findings.' }, null, 2)}\n`);
