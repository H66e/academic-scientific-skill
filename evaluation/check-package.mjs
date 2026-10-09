import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { assertNoLinks, defaultSkill, defaultPackage, defaultLicense, readSkillFiles, readPackage } from './package-skill.mjs';

export async function verifyPackage(root, bytes, options = {}) {
  const expected = await readSkillFiles(root, options);
  const actual = readPackage(bytes);
  const missing = [...expected.keys()].filter(name => !actual.has(name));
  const extra = [...actual.keys()].filter(name => !expected.has(name));
  const changed = [...expected].filter(([name, content]) => actual.has(name) && !content.equals(actual.get(name))).map(([name]) => name);
  if (missing.length || extra.length || changed.length) throw new Error(`Package differs from skill source: ${JSON.stringify({ missing, extra, changed })}`);
  return { valid: true, files: actual.size, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex') };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 2) throw new Error('Usage: node evaluation/check-package.mjs');
  try {
    await assertNoLinks(defaultPackage);
    const bytes = await fs.readFile(defaultPackage);
    process.stdout.write(`${JSON.stringify(await verifyPackage(defaultSkill, bytes, { licensePath: defaultLicense }), null, 2)}\n`);
  } catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
