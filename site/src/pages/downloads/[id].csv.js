import { loadCorpus } from '../../lib/corpus.js';
import { circuitDownload, bomCsv } from '../../lib/downloads.js';
export function getStaticPaths() {
  return loadCorpus().filter((a) => a.bom).map((amp) => ({ params: { id: amp.id }, props: { amp } }));
}
export function GET({ props }) {
  return new Response(bomCsv(circuitDownload(props.amp)), {
    headers: { 'Content-Type': 'text/csv; charset=utf-8' },
  });
}
