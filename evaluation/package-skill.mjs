// Deterministic stored ZIP archives; no network, npm, shell, or directory deletion.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { inflateRawSync } from 'node:zlib';

export const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const defaultSkill = path.join(repoRoot, 'skills', 'ai-research-mentor');
export const defaultPackage = path.join(repoRoot, 'dist', 'ai-research-mentor.zip');
const packageRoot = 'ai-research-mentor';
const maxBytes = 128 * 1024 * 1024;
const crcTable = Array.from({ length: 256 }, (_, initial) => {
  let crc = initial;
  for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  return crc >>> 0;
});

export function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) crc = (crc >>> 8) ^ crcTable[(crc ^ byte) & 0xff];
  return (crc ^ 0xffffffff) >>> 0;
}

export async function assertNoLinks(target, { allowMissing = false } = {}) {
  let current = path.resolve(target);
  while (true) {
    try {
      if ((await fs.lstat(current)).isSymbolicLink()) throw new Error(`Linked path is forbidden: ${current}`);
    } catch (error) {
      if (!(allowMissing && error.code === 'ENOENT')) throw error;
    }
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
}

function safeName(input) {
  const name = input.replaceAll('\\', '/');
  const segments = name.replace(/\/$/, '').split('/');
  if (!name || name.includes('\0') || segments.some(segment => !segment || segment === '.' || segment === '..' || segment.includes(':')) ||
      segments[0] !== packageRoot || (segments.length < 2 && !name.endsWith('/'))) throw new Error(`Unsafe package entry: ${input}`);
  return name;
}

export async function readSkillFiles(root = defaultSkill) {
  const absolute = path.resolve(root);
  await assertNoLinks(absolute);
  if (!(await fs.lstat(absolute)).isDirectory()) throw new Error('Skill source is not a directory');
  const files = new Map();
  let total = 0;
  async function walk(directory, relative) {
    const entries = await fs.readdir(directory, { withFileTypes: true });
    entries.sort((a, b) => a.name < b.name ? -1 : a.name > b.name ? 1 : 0);
    for (const entry of entries) {
      if (entry.name.includes('\\')) throw new Error(`Unsupported source filename: ${entry.name}`);
      const target = path.join(directory, entry.name);
      const child = relative ? `${relative}/${entry.name}` : entry.name;
      const stat = await fs.lstat(target);
      if (stat.isSymbolicLink()) throw new Error(`Linked source entry is forbidden: ${child}`);
      if (stat.isDirectory()) await walk(target, child);
      else if (stat.isFile()) {
        const name = safeName(`${packageRoot}/${child}`);
        if (stat.size > maxBytes - total) throw new Error('Skill source exceeds package size limit');
        const bytes = await fs.readFile(target);
        total += bytes.length;
        if (total > maxBytes) throw new Error('Skill source exceeds package size limit');
        if (files.has(name)) throw new Error(`Duplicate source package entry: ${name}`);
        files.set(name, bytes);
      } else throw new Error(`Unsupported source entry: ${child}`);
    }
  }
  await walk(absolute, '');
  if (!files.has(`${packageRoot}/SKILL.md`)) throw new Error('Skill source lacks SKILL.md');
  if (files.size > 65534) throw new Error('ZIP64 archives are not supported');
  return files;
}

export async function buildPackage(root = defaultSkill) {
  const files = await readSkillFiles(root);
  const localParts = [];
  const centralParts = [];
  let offset = 0;
  for (const [name, bytes] of files) {
    const encoded = Buffer.from(name, 'utf8');
    if (encoded.length > 65535) throw new Error('ZIP entry name is too long');
    const crc = crc32(bytes);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0x0800, 6); // UTF-8; stored method and midnight 1980-01-01.
    local.writeUInt16LE(0x0021, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(bytes.length, 18);
    local.writeUInt32LE(bytes.length, 22);
    local.writeUInt16LE(encoded.length, 26);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0x0800, 8);
    central.writeUInt16LE(0x0021, 14);
    central.writeUInt32LE(crc, 16);
    central.writeUInt32LE(bytes.length, 20);
    central.writeUInt32LE(bytes.length, 24);
    central.writeUInt16LE(encoded.length, 28);
    central.writeUInt32LE(offset, 42);
    localParts.push(local, encoded, bytes);
    centralParts.push(central, encoded);
    offset += local.length + encoded.length + bytes.length;
  }
  const central = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(files.size, 8);
  end.writeUInt16LE(files.size, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(offset, 16);
  return { bytes: Buffer.concat([...localParts, central, end]), fileCount: files.size };
}

export function readPackage(bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length < 22 || bytes.length > maxBytes * 2) throw new Error('Invalid ZIP size');
  let end = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (bytes.readUInt32LE(i) === 0x06054b50 && i + 22 + bytes.readUInt16LE(i + 20) === bytes.length) { end = i; break; }
  }
  if (end < 0) throw new Error('Missing ZIP end record');
  const count = bytes.readUInt16LE(end + 10);
  const centralLength = bytes.readUInt32LE(end + 12);
  const centralOffset = bytes.readUInt32LE(end + 16);
  if (bytes.readUInt16LE(end + 4) || bytes.readUInt16LE(end + 6) || bytes.readUInt16LE(end + 8) !== count ||
      count === 65535 || centralOffset + centralLength !== end) throw new Error('Unsupported or invalid ZIP directory');
  const files = new Map();
  const names = new Set();
  const regions = [];
  let cursor = centralOffset;
  let total = 0;
  for (let index = 0; index < count; index++) {
    if (cursor + 46 > end || bytes.readUInt32LE(cursor) !== 0x02014b50) throw new Error('Invalid ZIP central entry');
    const flags = bytes.readUInt16LE(cursor + 8);
    const method = bytes.readUInt16LE(cursor + 10);
    const crc = bytes.readUInt32LE(cursor + 16);
    const compressed = bytes.readUInt32LE(cursor + 20);
    const size = bytes.readUInt32LE(cursor + 24);
    const nameLength = bytes.readUInt16LE(cursor + 28);
    const extraLength = bytes.readUInt16LE(cursor + 30);
    const commentLength = bytes.readUInt16LE(cursor + 32);
    const localOffset = bytes.readUInt32LE(cursor + 42);
    const next = cursor + 46 + nameLength + extraLength + commentLength;
    if (next > end || flags & ~0x0808 || ![0, 8].includes(method) || bytes.readUInt16LE(cursor + 34) ||
        ((bytes.readUInt32LE(cursor + 38) >>> 16) & 0xf000) === 0xa000) throw new Error('Unsupported or linked ZIP entry');
    const encoded = bytes.subarray(cursor + 46, cursor + 46 + nameLength);
    const rawName = encoded.toString('utf8');
    if (!Buffer.from(rawName, 'utf8').equals(encoded)) throw new Error('ZIP entry name is not valid UTF-8');
    const name = safeName(rawName);
    if (names.has(name)) throw new Error(`Duplicate ZIP entry: ${name}`);
    names.add(name);
    if (localOffset + 30 > centralOffset || bytes.readUInt32LE(localOffset) !== 0x04034b50 ||
        bytes.readUInt16LE(localOffset + 6) !== flags || bytes.readUInt16LE(localOffset + 8) !== method) throw new Error('Invalid ZIP local entry');
    const localNameLength = bytes.readUInt16LE(localOffset + 26);
    const dataOffset = localOffset + 30 + localNameLength + bytes.readUInt16LE(localOffset + 28);
    if (dataOffset + compressed > centralOffset || !bytes.subarray(localOffset + 30, localOffset + 30 + localNameLength).equals(encoded)) throw new Error('ZIP local name or length mismatch');
    if (!(flags & 8) && (bytes.readUInt32LE(localOffset + 14) !== crc || bytes.readUInt32LE(localOffset + 18) !== compressed ||
        bytes.readUInt32LE(localOffset + 22) !== size)) throw new Error('ZIP local checksum or size mismatch');
    regions.push([localOffset, dataOffset + compressed]);
    total += size;
    if (total > maxBytes || (method === 0 && compressed !== size)) throw new Error('ZIP uncompressed size is invalid');
    const payload = bytes.subarray(dataOffset, dataOffset + compressed);
    const content = method === 0 ? payload : inflateRawSync(payload, { maxOutputLength: Math.max(1, size + 1) });
    if (content.length !== size || crc32(content) !== crc) throw new Error(`ZIP checksum mismatch: ${name}`);
    if (name.endsWith('/')) {
      if (size !== 0) throw new Error('ZIP directory has content');
    } else files.set(name, content);
    cursor = next;
  }
  if (cursor !== end) throw new Error('ZIP directory length mismatch');
  regions.sort((a, b) => a[0] - b[0]);
  if (regions.some((region, index) => index > 0 && regions[index - 1][1] > region[0])) throw new Error('Overlapping ZIP entries');
  if (!files.has(`${packageRoot}/SKILL.md`)) throw new Error('ZIP lacks SKILL.md');
  return files;
}

export async function writeDefaultPackage() {
  const built = await buildPackage();
  await assertNoLinks(defaultPackage, { allowMissing: true });
  try {
    const existing = await fs.lstat(defaultPackage);
    if (!existing.isFile()) throw new Error('Package target is not a regular file');
    readPackage(await fs.readFile(defaultPackage)); // Only replace the designated skill ZIP.
  } catch (error) { if (error.code !== 'ENOENT') throw error; }
  await fs.mkdir(path.dirname(defaultPackage), { recursive: true });
  await fs.writeFile(defaultPackage, built.bytes);
  return { package: defaultPackage, files: built.fileCount, bytes: built.bytes.length,
    sha256: createHash('sha256').update(built.bytes).digest('hex') };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 2) throw new Error('Usage: node evaluation/package-skill.mjs (writes only dist/ai-research-mentor.zip)');
  try { process.stdout.write(`${JSON.stringify(await writeDefaultPackage(), null, 2)}\n`); }
  catch (error) { process.stderr.write(`${error.message}\n`); process.exitCode = 1; }
}
