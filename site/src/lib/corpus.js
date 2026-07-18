// Build-time corpus loader — reads ../amps/*/ (meta.yaml, voltages.yaml,
// notes.md) so every page on the site is generated from the repo data.
import fs from 'node:fs';
import path from 'node:path';
import yaml from 'js-yaml';
import { marked } from 'marked';

const REPO_ROOT = path.resolve(process.cwd(), '..');
const AMPS_DIR = path.join(REPO_ROOT, 'amps');
const MODELS_DIR = path.join(REPO_ROOT, 'models');

function readIfExists(p) {
  return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : null;
}

export function loadCorpus() {
  const amps = fs.readdirSync(AMPS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory() && !d.name.startsWith('_'))
    .map((d) => {
      const dir = path.join(AMPS_DIR, d.name);
      const meta = yaml.load(fs.readFileSync(path.join(dir, 'meta.yaml'), 'utf8'));
      const voltagesRaw = readIfExists(path.join(dir, 'voltages.yaml'));
      const bomRaw = readIfExists(path.join(dir, 'bom.yaml'));
      const notesRaw = readIfExists(path.join(dir, 'notes.md'));
      return {
        id: meta.id,
        meta,
        voltages: voltagesRaw ? yaml.load(voltagesRaw) : null,
        bom: bomRaw ? yaml.load(bomRaw) : null,
        notesHtml: notesRaw ? marked.parse(notesRaw.replace(/^# .*\n/, '')) : null,
        hasNetlist: fs.existsSync(path.join(dir, 'netlist.cir')),
        hasSchematic: fs.existsSync(path.join(dir, 'schematic.kicad_sch')),
      };
    })
    .sort((a, b) => a.id.localeCompare(b.id));
  return amps;
}

export function corpusStats() {
  const amps = loadCorpus();
  const models = fs.readdirSync(MODELS_DIR).filter((f) => f.endsWith('.inc'));
  return {
    circuits: amps.length,
    verified: amps.filter((a) => a.meta.verification?.status === 'verified').length,
    models: models.length,
  };
}

export const GITHUB = 'https://github.com/TheAnalogMaker/circuit-codex';
