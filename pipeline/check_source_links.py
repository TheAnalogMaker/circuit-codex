#!/usr/bin/env python3
"""Periodic check that the corpus's cited sources still resolve.

Every claim in this archive is anchored to a published document, and a citation
that 404s is a claim a reader cannot check. This walks every external URL in
amps/*/meta.yaml, reference/tubes/*.yaml and history/families/*.yaml, fetches
each one, and says which are genuinely gone.

The distinction that matters is DEAD versus everything else. A 404 or 410 is the
archive's problem and needs a replacement URL. A 403, a 429, a 5xx or a timeout
is the far end having a bad day, or not liking robots, and says nothing about
whether the document still exists — reporting those as breakage would train a
reader to ignore the report. So they are listed separately and never counted as
failures.

    python3 check_source_links.py              # report, exit 0 whatever happens
    python3 check_source_links.py --strict     # exit 1 if any URL is DEAD
    python3 check_source_links.py --json out.json
    python3 check_source_links.py --only pocnet   # substring filter

NOT A CI GATE, and --strict is for a human running it deliberately. The build
must never depend on somebody else's web server being up: the IndexNow pings
taught that lesson once already, and a gate that fails for reasons nobody in
this repo can fix is a gate people learn to force past.

Replacing a dead link is not a mechanical swap. Check that the replacement
really carries what the citation claims — the same publisher, the same edition,
and the numbers the description quotes. In 2026-09 both dead datasheet links
here had an obvious-looking replacement in the same directory that turned out to
be a differential sheet ("the 6V6 is the same as the 6V6GTA except...") carrying
none of the average characteristics the model's anchor cites.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ("amps/*/meta.yaml", "reference/tubes/*.yaml", "history/families/*.yaml")
URL_RE = re.compile(r'https?://[^\s"\'<>)\]]+')
# A trailing comma or period is prose punctuation, not part of the URL.
TRIM = ".,;:"

UA = "circuit-codex-link-check/1.0 (+https://circuitcodex.com; contact via GitHub issues)"
TIMEOUT = 25
PER_HOST_DELAY = 1.0          # be a polite guest: one request per host per second

# Classification. Only DEAD is actionable by this repo.
DEAD, OK, BLOCKED, FLAKY = "DEAD", "OK", "BLOCKED", "FLAKY"


def cited_urls() -> dict[str, list[str]]:
    """url -> the repo files that cite it."""
    out: dict[str, list[str]] = defaultdict(list)
    for pattern in SOURCES:
        for path in sorted(glob.glob(str(ROOT / pattern))):
            rel = str(Path(path).relative_to(ROOT))
            for url in URL_RE.findall(Path(path).read_text()):
                out[url.rstrip(TRIM)].append(rel)
    return out


def fetch(url: str, method: str = "HEAD") -> tuple[str, str]:
    """(classification, detail). Follows redirects; a redirect to a live page is OK."""
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            code, ctype = resp.status, resp.headers.get("Content-Type", "?")
            landed = resp.geturl()
            detail = f"{code} {ctype.split(';')[0]}"
            if landed.rstrip("/") != url.rstrip("/"):
                detail += f"  -> {landed}"
            return OK, detail
    except urllib.error.HTTPError as e:
        # Some servers refuse HEAD but serve GET perfectly well.
        if e.code in (403, 405, 501) and method == "HEAD":
            return fetch(url, "GET")
        if e.code in (404, 410):
            return DEAD, f"{e.code} {e.reason}"
        if e.code in (401, 403, 429):
            return BLOCKED, f"{e.code} {e.reason}"
        return FLAKY, f"{e.code} {e.reason}"
    except urllib.error.URLError as e:
        return FLAKY, f"connection: {e.reason}"
    except Exception as e:                                    # noqa: BLE001
        return FLAKY, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any URL is DEAD (for a human, not for CI)")
    ap.add_argument("--json", metavar="PATH", help="write the full result as JSON")
    ap.add_argument("--only", metavar="SUBSTR", help="check only URLs containing SUBSTR")
    args = ap.parse_args()

    urls = cited_urls()
    if args.only:
        urls = {u: c for u, c in urls.items() if args.only in u}
    if not urls:
        print("no cited URLs matched")
        return 0

    last_hit: dict[str, float] = {}
    results = []
    print(f"checking {len(urls)} cited URL(s) across "
          f"{len({urlsplit(u).netloc for u in urls})} host(s)\n", flush=True)

    for url in sorted(urls):
        host = urlsplit(url).netloc
        wait = PER_HOST_DELAY - (time.monotonic() - last_hit.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        verdict, detail = fetch(url)
        last_hit[host] = time.monotonic()
        results.append({"url": url, "verdict": verdict, "detail": detail,
                        "cited_by": sorted(set(urls[url]))})
        if verdict != OK:
            print(f"{verdict:<8} {url}\n         {detail}\n"
                  f"         cited by: {', '.join(sorted(set(urls[url])))}", flush=True)

    counts = defaultdict(int)
    for r in results:
        counts[r["verdict"]] += 1
    print(f"\n{len(results)} checked — "
          + ", ".join(f"{counts[k]} {k}" for k in (OK, DEAD, BLOCKED, FLAKY) if counts[k]))

    if counts[DEAD]:
        print("\nDEAD links need a replacement that genuinely carries what the citation "
              "claims — publisher, edition and the quoted numbers. Read the replacement "
              "before swapping it in; see this file's header.")
    if counts[BLOCKED] or counts[FLAKY]:
        print("BLOCKED/FLAKY are the far end's problem, not evidence the document is "
              "gone. Re-run before acting on one.")

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2) + "\n")
        print(f"wrote {args.json}")

    return 1 if (args.strict and counts[DEAD]) else 0


if __name__ == "__main__":
    sys.exit(main())
