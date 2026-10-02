#!/usr/bin/env node
// Write dist/version.json: which source revision this build was made from.
//
// A green build is not evidence that the right revision reached production.
// On 2026-09-29 every branch build deployed to circuitcodex.com, and an unmerged
// PR stayed live for hours while main's own checks were all green. This marker
// lets anything outside the build ask the live site what it is serving:
// scripts/circuit-codex/land.sh polls it after each landing, and
// .github/workflows/production-revision.yml compares it with main on a schedule.
//
// Revision: WORKERS_CI_COMMIT_SHA on Workers Builds, else `git rev-parse HEAD`.
// Branch: WORKERS_CI_BRANCH, else GITHUB_HEAD_REF / GITHUB_REF_NAME, else git.
// public/_headers serves this file with Cache-Control: no-store.
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const git = (cmd) => {
  try { return execSync(`git ${cmd}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); }
  catch { return ''; }
};

const revision = process.env.WORKERS_CI_COMMIT_SHA || git('rev-parse HEAD');
const branch = process.env.WORKERS_CI_BRANCH || process.env.GITHUB_HEAD_REF
  || process.env.GITHUB_REF_NAME || git('rev-parse --abbrev-ref HEAD');

if (!/^[0-9a-f]{40}$/.test(revision)) {
  console.error(`[version] no 40-hex source revision available (got ${JSON.stringify(revision)})`);
  process.exit(1);
}
if (!fs.existsSync(DIST)) {
  console.error('[version] dist/ does not exist; run after astro build');
  process.exit(1);
}
const out = { revision, branch, builtAt: new Date().toISOString(),
  builder: process.env.WORKERS_CI ? 'workers-builds' : (process.env.GITHUB_ACTIONS ? 'github-actions' : 'local') };
fs.writeFileSync(path.join(DIST, 'version.json'), JSON.stringify(out, null, 2) + '\n');
console.log(`[version] dist/version.json: ${revision.slice(0, 7)} on ${branch}`);
