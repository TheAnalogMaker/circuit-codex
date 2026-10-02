import { execFileSync } from 'node:child_process';
import path from 'node:path';
import fs from 'node:fs';
import yaml from 'js-yaml';

const root = path.resolve(process.cwd(), '..');
const repo = 'https://github.com/TheAnalogMaker/circuit-codex';
let revision;
export function archiveRevision() {
  if (revision !== undefined) return revision;
  try {
    const sha = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    revision = /^[a-f0-9]{40}$/.test(sha) ? { sha, short: sha.slice(0, 7), url: `${repo}/commit/${sha}` } : null;
  } catch { revision = null; }
  return revision;
}
let corrections;
export function loadCorrections() {
  if (!corrections) {
    const file = path.join(root, 'reference/corrections.yaml');
    corrections = fs.existsSync(file) ? (yaml.load(fs.readFileSync(file, 'utf8')).corrections || []) : [];
    const ids = new Set();
    for (const c of corrections) {
      if (!/^[a-z0-9-]+$/.test(c.id || '') || ids.has(c.id)
        || !/^\d{4}-\d{2}-\d{2}$/.test(c.date || '')
        || !/^[a-f0-9]{7,40}$/.test(c.commit || '')
        || !Array.isArray(c.amps) || !c.amps.length
        || c.amps.some((id) => !/^[a-z0-9-]+$/.test(id) || !fs.existsSync(path.join(root, 'amps', id, 'meta.yaml')))
        || !c.title || !c.description) throw new Error(`Invalid correction record: ${c.id || 'missing id'}`);
      ids.add(c.id);
    }
    corrections = corrections.map((item) => ({ ...item, date: String(item.date), url: `${repo}/commit/${item.commit}` }))
      .sort((a, b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id));
  }
  return corrections;
}
export const ampCorrections = (id) => loadCorrections().filter((c) => c.amps.includes(id));
