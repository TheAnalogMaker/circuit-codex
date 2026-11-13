// JSON for a <script type="application/json"> or "application/ld+json" block.
// The HTML parser ends a script element at the first "</script" in its text, no
// matter that the text is JSON, so a data string carrying one (a quoted note, a
// study excerpt) would cut the block short and spill the rest into the page.
// Escaping every "<" as < is invisible to JSON.parse and to structured-data
// readers, and leaves the parser nothing to stop on.
export function jsonForScript(value) {
  return JSON.stringify(value).replaceAll('<', '\\u003c');
}
