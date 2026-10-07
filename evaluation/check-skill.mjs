// Repository-specific checks for the simple YAML used here; not a general YAML parser.
import fs from 'node:fs/promises';
import path from 'node:path';
const root = path.resolve(process.argv[2] ?? 'ai-research-mentor');
const errors = [];
const required = ['SKILL.md', 'agents/openai.yaml', 'scripts/research_audit.mjs',
  'references/data-contract.md', 'references/literature.md', 'references/ideation.md',
  'references/evaluation.md', 'references/feedback.md', 'references/design-basis.md',
  'references/self-improvement.md', 'scripts/evolution_guard.mjs',
  'references/retrieval-adapters.md',
  'references/fulltext.md', 'references/research-outputs.md', 'references/source-tools.md',
  'scripts/research_sources.mjs', 'scripts/research_outputs.mjs',
  'schemas/notes.schema.json', 'schemas/dossier.schema.json',
  'tests/research_audit.test.mjs', 'tests/evolution_guard.test.mjs',
  'tests/research_sources.test.mjs', 'tests/research_outputs.test.mjs'];
required.push('scripts/research_mentor.py', 'runtime/research_mentor/core.py',
  'runtime/research_mentor/judgment.py', 'references/python-core.md', 'schemas/ledger-event.schema.json');
for (const file of required) {
  try { await fs.access(path.join(root, file)); } catch { errors.push(`Missing ${file}`); }
}
const source = await fs.readFile(path.join(root, 'SKILL.md'), 'utf8');
const frontmatter = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(source);
if (!frontmatter) errors.push('Missing YAML frontmatter');
else {
  const fields = Object.fromEntries(frontmatter[1].split(/\r?\n/).map(line => {
    const match = /^(name|description): (.+)$/.exec(line);
    if (!match) { errors.push('Unexpected or unsupported frontmatter syntax'); return ['', '']; }
    return [match[1], match[2]];
  }));
  if (fields.name !== path.basename(root) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(fields.name ?? '') || fields.name.length > 64) errors.push('Invalid skill name');
  if (!fields.description || fields.description.length > 1024 || /[<>]/.test(fields.description)) errors.push('Invalid description');
  // These scalar values are intentionally plain; reject syntax needing a full YAML parser.
  if (Object.values(fields).some(value => /:\s|^[\[\]{}!&*#>|%@`]/.test(value))) errors.push('Frontmatter requires unsupported YAML syntax');
}
if (/^\s*\[TODO:[^\n]*\]\s*$/m.test(source)) errors.push('Unfinished scaffold');
const metadata = await fs.readFile(path.join(root, 'agents/openai.yaml'), 'utf8');
const ui = Object.fromEntries([...metadata.matchAll(/^  (display_name|short_description|default_prompt): ("[^"\r\n]*")$/gm)]
  .map(match => [match[1], JSON.parse(match[2])]));
if (!ui.display_name || !ui.short_description || !ui.default_prompt) errors.push('Missing quoted UI strings');
if (ui.short_description && (Array.from(ui.short_description).length < 25 || Array.from(ui.short_description).length > 64)) errors.push('UI description length outside 25–64');
if (!ui.default_prompt?.includes('$ai-research-mentor')) errors.push('Default prompt misses skill invocation');
if (!/^  allow_implicit_invocation: true$/m.test(metadata)) errors.push('Implicit invocation is not enabled');
let localLinks = 0;
for (const file of required.filter(file => file.endsWith('.md'))) {
  const content = await fs.readFile(path.join(root, file), 'utf8');
  for (const match of content.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const destination = match[1];
    if (/^(?:[a-z]+:|#)/i.test(destination)) continue;
    const target = path.resolve(path.dirname(path.join(root, file)), destination.split('#')[0]);
    const relative = path.relative(root, target);
    if (relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) errors.push(`Reference escapes skill: ${destination}`);
    else {
      try { await fs.access(target); localLinks++; } catch { errors.push(`Broken reference in ${file}: ${destination}`); }
    }
  }
}
// Check local JSON pointers without pretending to implement all of JSON Schema.
for (const file of required.filter(file => file.endsWith('.schema.json'))) {
  try {
    const schema = JSON.parse(await fs.readFile(path.join(root, file), 'utf8'));
    const inspect = value => {
      if (value === null || typeof value !== 'object') return;
      if (typeof value.$ref === 'string') {
        if (!value.$ref.startsWith('#/')) errors.push(`Unsupported external schema reference in ${file}`);
        else {
          const target = value.$ref.slice(2).split('/').reduce((current, part) => current?.[part.replaceAll('~1', '/').replaceAll('~0', '~')], schema);
          if (target === undefined) errors.push(`Broken schema reference in ${file}: ${value.$ref}`);
        }
      }
      for (const child of Object.values(value)) inspect(child);
    };
    inspect(schema);
  } catch (error) { errors.push(`Cannot parse schema ${file}: ${error.message}`); }
}
process.stdout.write(`${JSON.stringify({ valid: errors.length === 0, errors, local_links_checked: localLinks,
  skill_lines: source.split(/\r?\n/).length, note: 'Local metadata/reference checks; does not prove research quality.' }, null, 2)}\n`);
process.exitCode = errors.length ? 1 : 0;
