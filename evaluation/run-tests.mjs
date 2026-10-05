// Resolve test files before invoking Node, so shells do not decide glob semantics.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const directories = ['skills/ai-research-mentor/tests', 'evaluation/tests'];
const files = [];
for (const directory of directories) {
  for (const entry of await fs.readdir(path.join(repo, directory), { withFileTypes: true })) {
    if (entry.isFile() && entry.name.endsWith('.test.mjs')) files.push(path.join(repo, directory, entry.name));
  }
}
files.sort();
for (const required of ['research_audit.test.mjs', 'evolution_guard.test.mjs', 'packaging.test.mjs']) {
  if (!files.some(file => path.basename(file) === required)) throw new Error(`Missing required test file: ${required}`);
}
const result = spawnSync(process.execPath, ['--test', ...files], { cwd: repo, stdio: 'inherit', shell: false });
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
