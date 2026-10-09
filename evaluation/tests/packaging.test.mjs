import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { buildPackage, readPackage, readSkillFiles, assertNoLinks, crc32 } from '../package-skill.mjs';
import { verifyPackage } from '../check-package.mjs';

async function fixture(t) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'academic-package-'));
  const resolved = path.resolve(root);
  t.after(async () => {
    assert.equal(path.dirname(resolved), path.resolve(os.tmpdir()));
    assert.match(path.basename(resolved), /^academic-package-/);
    await fs.rm(resolved, { recursive: true, force: true });
  });
  const skill = path.join(root, 'ai-research-mentor');
  await fs.mkdir(path.join(skill, 'references'), { recursive: true });
  await fs.writeFile(path.join(skill, 'SKILL.md'), 'synthetic test skill\n');
  await fs.writeFile(path.join(skill, 'references', '合成资料.md'), '中文 synthetic\n');
  await fs.writeFile(path.join(skill, 'empty.txt'), '');
  return { root, skill };
}

test('ZIP CRC32 matches the standard check value', () => {
  assert.equal(crc32(Buffer.from('123456789')), 0xcbf43926);
});

test('release archive is deterministic and preserves all UTF-8 and empty file bytes', async t => {
  const { skill } = await fixture(t);
  const first = await buildPackage(skill);
  const second = await buildPackage(skill);
  assert.ok(first.bytes.equals(second.bytes));
  const result = await verifyPackage(skill, first.bytes);
  assert.equal(result.valid, true);
  assert.equal(result.files, 3);
  assert.equal(readPackage(first.bytes).get('ai-research-mentor/references/合成资料.md').toString(), '中文 synthetic\n');
});

test('archive verification rejects stale source bytes', async t => {
  const { skill } = await fixture(t);
  const { bytes } = await buildPackage(skill);
  await fs.writeFile(path.join(skill, 'SKILL.md'), 'changed\n');
  await assert.rejects(verifyPackage(skill, bytes), /changed.*SKILL/);
});

test('archive verification rejects missing and extra resources', async t => {
  const { skill } = await fixture(t);
  const { bytes } = await buildPackage(skill);
  await fs.writeFile(path.join(skill, 'new.txt'), 'new resource');
  await assert.rejects(verifyPackage(skill, bytes), /missing.*new.txt/);
  await fs.unlink(path.join(skill, 'new.txt'));
  await fs.unlink(path.join(skill, 'empty.txt'));
  await assert.rejects(verifyPackage(skill, bytes), /extra.*empty.txt/);
});

test('corrupted ZIP payload is rejected before comparing with source', async t => {
  const { skill } = await fixture(t);
  const { bytes } = await buildPackage(skill);
  const corrupt = Buffer.from(bytes);
  const dataOffset = 30 + corrupt.readUInt16LE(26) + corrupt.readUInt16LE(28);
  corrupt[dataOffset] ^= 1;
  assert.throws(() => readPackage(corrupt), /checksum/);
});

test('truncated ZIP and central/local filename mismatches are rejected', async t => {
  const { skill } = await fixture(t);
  const { bytes } = await buildPackage(skill);
  assert.throws(() => readPackage(bytes.subarray(0, bytes.length - 1)), /end record/);
  const corrupt = Buffer.from(bytes);
  corrupt[30] = 'z'.charCodeAt(0);
  assert.throws(() => readPackage(corrupt), /local name/);
});

test('ZIP path traversal is rejected even when both filenames are changed', async t => {
  const { skill } = await fixture(t);
  const { bytes } = await buildPackage(skill);
  const corrupt = Buffer.from(bytes);
  const end = corrupt.length - 22;
  const central = corrupt.readUInt32LE(end + 16);
  corrupt.write('../', 30, 'utf8');
  corrupt.write('../', central + 46, 'utf8');
  assert.throws(() => readPackage(corrupt), /Unsafe package entry/);
});

test('linked source directories and linked source ancestors are rejected', async t => {
  const { root, skill } = await fixture(t);
  const outside = path.join(root, 'separate');
  await fs.mkdir(outside);
  const linked = path.join(skill, 'linked');
  await fs.symlink(outside, linked, process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(buildPackage(skill), /Linked source entry/);
  await assert.rejects(assertNoLinks(path.join(linked, 'nonexistent.txt'), { allowMissing: true }), /Linked path/);
});

test('an explicit license joins the package first and survives verification', async t => {
  const { root, skill } = await fixture(t);
  const license = path.join(root, 'LICENSE');
  await fs.writeFile(license, 'MIT License\n\nCopyright (c) 2026 Example\n');
  const files = await readSkillFiles(skill, { licensePath: license });
  assert.equal([...files.keys()][0], 'ai-research-mentor/LICENSE');
  const { bytes } = await buildPackage(skill, { licensePath: license });
  const result = await verifyPackage(skill, bytes, { licensePath: license });
  assert.equal(result.valid, true);
  assert.equal(result.files, 4);
  assert.equal(readPackage(bytes).get('ai-research-mentor/LICENSE').toString(), 'MIT License\n\nCopyright (c) 2026 Example\n');
});

test('verification rejects a package that omits the required license', async t => {
  const { root, skill } = await fixture(t);
  const license = path.join(root, 'LICENSE');
  await fs.writeFile(license, 'MIT License\n');
  const { bytes } = await buildPackage(skill);
  await assert.rejects(verifyPackage(skill, bytes, { licensePath: license }), /missing.*LICENSE/);
});

test('a skill directory that already contains LICENSE is rejected instead of overridden', async t => {
  const { root, skill } = await fixture(t);
  await fs.writeFile(path.join(skill, 'LICENSE'), 'in-tree\n');
  const license = path.join(root, 'LICENSE');
  await fs.writeFile(license, 'root\n');
  await assert.rejects(buildPackage(skill, { licensePath: license }), /Duplicate source package entry/);
});

test('a regular source folder without SKILL.md cannot become a release package', async t => {
  const { root } = await fixture(t);
  const source = path.join(root, 'other');
  await fs.mkdir(source);
  await fs.writeFile(path.join(source, 'file.txt'), 'data');
  await assert.rejects(buildPackage(source), /lacks SKILL/);
});
