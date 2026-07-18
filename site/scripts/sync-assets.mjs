// Copy corpus assets into public/ so the site can serve them:
//   amps/<id>/schematic.kicad_sch -> public/schematics/<id>.kicad_sch  (KiCanvas)
//   amps/<id>/layout.svg          -> public/layouts/<id>.svg           (board diagram)
import fs from 'node:fs';
import path from 'node:path';

const ampsDir = path.resolve(process.cwd(), '..', 'amps');
const schemaOut = path.resolve(process.cwd(), 'public', 'schematics');
const layoutOut = path.resolve(process.cwd(), 'public', 'layouts');
fs.mkdirSync(schemaOut, { recursive: true });
fs.mkdirSync(layoutOut, { recursive: true });

let nSch = 0;
let nLay = 0;
for (const d of fs.readdirSync(ampsDir, { withFileTypes: true })) {
  if (!d.isDirectory() || d.name.startsWith('_')) continue;
  const sch = path.join(ampsDir, d.name, 'schematic.kicad_sch');
  if (fs.existsSync(sch)) {
    fs.copyFileSync(sch, path.join(schemaOut, `${d.name}.kicad_sch`));
    nSch += 1;
  }
  const lay = path.join(ampsDir, d.name, 'layout.svg');
  if (fs.existsSync(lay)) {
    fs.copyFileSync(lay, path.join(layoutOut, `${d.name}.svg`));
    nLay += 1;
  }
}
console.log(`synced ${nSch} schematic(s) to public/schematics/, ${nLay} layout(s) to public/layouts/`);
