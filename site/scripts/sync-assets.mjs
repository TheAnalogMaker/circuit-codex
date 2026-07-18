// Copy corpus schematic files into public/ so KiCanvas can fetch them.
import fs from 'node:fs';
import path from 'node:path';

const ampsDir = path.resolve(process.cwd(), '..', 'amps');
const outDir = path.resolve(process.cwd(), 'public', 'schematics');
fs.mkdirSync(outDir, { recursive: true });
let n = 0;
for (const d of fs.readdirSync(ampsDir, { withFileTypes: true })) {
  if (!d.isDirectory() || d.name.startsWith('_')) continue;
  const src = path.join(ampsDir, d.name, 'schematic.kicad_sch');
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, path.join(outDir, `${d.name}.kicad_sch`));
    n += 1;
  }
}
console.log(`synced ${n} schematic(s) to public/schematics/`);
