// Keep a lab's shareable address in step with its controls without flooding the
// History API. Browsers cap history.replaceState: Chrome silently drops calls past
// about 200 in 10 s and Safari throws, so writing on every slider `input` event left
// the address (and any link copied from it) showing a setting the reader had
// already dragged past. The address is now written once the controls settle, and a
// copied link is built from the page's state rather than read back from
// location.href.
//
// build() returns the address for the current state (string or URL).
export function urlSync(build, {
  delay = 250,
  history = globalThis.history,
  target = globalThis,
  setTimer = setTimeout,
  clearTimer = clearTimeout,
} = {}) {
  let timer = null;
  function flush() {
    if (timer !== null) clearTimer(timer);
    timer = null;
    try {
      history.replaceState(null, '', build());
    } catch {
      // Throttled. The address catches up on the next settled change, and copied
      // links never depend on it.
    }
  }
  // A reload or navigation inside the settle window keeps the latest setting.
  target.addEventListener?.('pagehide', () => { if (timer !== null) flush(); });
  return {
    schedule() {
      if (timer !== null) clearTimer(timer);
      timer = setTimer(flush, delay);
    },
    flush,
  };
}
