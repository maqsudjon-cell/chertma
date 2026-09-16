// Prove the live bot answers, and that Telegram can reach it. Run after every deploy.
//
//   node scripts/check-live.mjs [--since <unix seconds>]
//
// Fails loudly (exit 1) on any of:
//   - the production health endpoint is not 200
//   - a signed test update does not come back as a sendMessage reply
//   - getWebhookInfo has no url, or a url that is not the production one
//   - the webhook url is a deployment url (a hash in the host) instead of the stable domain
//   - Telegram reports an error newer than --since (default: the start of this check)
//
// Reads .env (gitignored). Prints no secret and no message content.

import { readFileSync } from 'node:fs';

const PROD = 'https://chertma-bot.vercel.app/api/telegram';
const argSince = process.argv.indexOf('--since');
const since = argSince > 0 ? Number(process.argv[argSince + 1]) : Math.floor(Date.now() / 1000);

const env = Object.fromEntries(
  readFileSync(new URL('../../.env', import.meta.url), 'utf8')
    .split('\n').filter((l) => l.includes('=') && !l.trimStart().startsWith('#'))
    .map((l) => [l.slice(0, l.indexOf('=')).trim(), l.slice(l.indexOf('=') + 1).trim()]),
);

const fail = (msg) => { console.error(`FAIL  ${msg}`); process.exitCode = 1; };
const ok = (msg) => console.log(`ok    ${msg}`);

// 1. The function is there at all. This is what a bad deploy breaks: a build from the
//    repo root has no api/, so Telegram gets 404 on every update and the bot goes silent.
const health = await fetch(PROD);
if (health.status !== 200) fail(`GET ${PROD} → ${health.status} (expected 200; is the deploy rooted at bot/?)`);
else {
  const h = await health.json();
  ok(`health 200, lexicon ${h.lexicon} (${h.lexiconWords} words), engine init ${h.engineInitMs} ms`);
}

// 2. It answers a real update, with the secret Telegram sends.
const upd = {
  update_id: Date.now() % 1e9,
  message: { message_id: 1, date: since, chat: { id: 1, type: 'private' }, from: { id: 1, is_bot: false }, text: '/start' },
};
const res = await fetch(PROD, {
  method: 'POST',
  headers: { 'content-type': 'application/json', 'x-telegram-bot-api-secret-token': env.CHERTMA_WEBHOOK_SECRET ?? '' },
  body: JSON.stringify(upd),
});
const body = await res.json().catch(() => null);
if (res.status !== 200 || body?.method !== 'sendMessage' || !body?.text) fail(`/start → ${res.status} ${JSON.stringify(body)?.slice(0, 120)}`);
else ok(`/start answered in ${res.headers.get('server-timing') ?? '?'}`);

// 3. Telegram's side: the webhook points at the stable domain and is not erroring.
const info = await (await fetch(`https://api.telegram.org/bot${env.CHERTMA_BOT_TOKEN}/getWebhookInfo`)).json();
const w = info.result ?? {};
if (!w.url) fail('getWebhookInfo: url is empty — the webhook is not set');
else if (w.url !== PROD) fail(`getWebhookInfo: url is ${w.url}, expected ${PROD}`);
else if (/-[a-z0-9]{9}-|\/\/chertma-[a-z0-9]{9}\./.test(w.url)) fail(`getWebhookInfo: url is a deployment url, not the stable domain: ${w.url}`);
else ok(`webhook → ${w.url}`);
if (w.last_error_message && (w.last_error_date ?? 0) >= since) {
  fail(`Telegram error at ${new Date(w.last_error_date * 1000).toISOString()}: ${w.last_error_message}`);
} else if (w.last_error_message) {
  ok(`last Telegram error is older than this deploy (${new Date(w.last_error_date * 1000).toISOString()}: ${w.last_error_message})`);
}
if (w.pending_update_count) console.log(`note  ${w.pending_update_count} pending update(s) queued`);

if (process.exitCode) console.error('\nThe bot is NOT serving. Deploy from bot/ with scripts/deploy.mjs and check the webhook.');
else console.log('\nlive bot verified');
