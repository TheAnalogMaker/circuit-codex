import { loadCorpus } from '../../lib/corpus.js';
import { circuitDownload } from '../../lib/downloads.js';
export function getStaticPaths() {
  return loadCorpus().map((amp) => ({ params: { id: amp.id }, props: { amp } }));
}
export function GET({ props }) {
  return new Response(JSON.stringify(circuitDownload(props.amp), null, 2) + '\n', {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
