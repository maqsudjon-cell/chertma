// The only way to deploy the bot. Vendor → test → deploy from bot/ → verify live.
//
//   node scripts/deploy.mjs [--skip-tests]
//
// Never deploy with a bare `vercel --prod` from anywhere else: a deployment built from
// the repo root has no api/ directory, Telegram gets 404 on every update, and the bot
// goes silent with the webhook still pointing at the right url. That is exactly what
// happened on 2026-09-16 — see docs/FOR-MAQSUDJON.md.

import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const bot = fileURLToPath(new URL('..', import.meta.url));
const run = (cmd, args) => execFileSync(cmd, args, { cwd: bot, stdio: 'inherit', env: process.env });
const since = Math.floor(Date.now() / 1000);

run('node', ['scripts/vendor.mjs']);
if (!process.argv.includes('--skip-tests')) run('npm', ['test']);
run('npx', ['vercel', 'deploy', '--prod', '--yes']);
run('node', ['scripts/check-live.mjs', '--since', String(since)]);
