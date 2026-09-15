// Register and check the webhook, and smoke-test a deployment. Reads
// CHERTMA_BOT_TOKEN and CHERTMA_WEBHOOK_SECRET from the environment or from the
// repo's .env (gitignored). Prints results, never the token or the secret.
//
//   node bot/scripts/webhook.mjs set   https://<deployment>/api/telegram
//   node bot/scripts/webhook.mjs info
//   node bot/scripts/webhook.mjs smoke https://<deployment>/api/telegram
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { callApi } from '../src/telegram.js';

const envFile = fileURLToPath(new URL('../../.env', import.meta.url));
const fileEnv = existsSync(envFile)
  ? Object.fromEntries(readFileSync(envFile, 'utf8').split('\n').filter((l) => l.includes('=')).map((l) => [l.slice(0, l.indexOf('=')), l.slice(l.indexOf('=') + 1).trim()]))
  : {};
const token = process.env.CHERTMA_BOT_TOKEN ?? fileEnv.CHERTMA_BOT_TOKEN;
const secret = process.env.CHERTMA_WEBHOOK_SECRET ?? fileEnv.CHERTMA_WEBHOOK_SECRET;
const [cmd, url] = process.argv.slice(2);

if (!token) { console.error('CHERTMA_BOT_TOKEN is not set'); process.exit(1); }

if (cmd === 'set') {
  if (!url?.startsWith('https://')) { console.error('usage: set https://…/api/telegram'); process.exit(1); }
  const r = await callApi(token, 'setWebhook', {
    url,
    secret_token: secret,
    allowed_updates: ['message', 'inline_query'],
    drop_pending_updates: true,
    max_connections: 40,
  });
  console.log('setWebhook:', r.ok ? 'ok' : `failed (${r.code})`);
} else if (cmd === 'info') {
  const r = await callApi(token, 'getWebhookInfo', {});
  if (!r.ok) { console.log('getWebhookInfo failed:', r.code); process.exit(1); }
  const { url: hook, pending_update_count, last_error_date, last_error_message, allowed_updates } = r.result;
  console.log(JSON.stringify({ url: hook, pending_update_count, last_error_message: last_error_message ?? null,
    last_error_date: last_error_date ? new Date(last_error_date * 1000).toISOString() : null, allowed_updates }, null, 2));
} else if (cmd === 'smoke') {
  // Synthetic updates in Telegram's format. The function answers in the webhook
  // response body, so the reply can be read here without a real chat.
  const post = async (update) => {
    const t0 = performance.now();
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-telegram-bot-api-secret-token': secret ?? '' },
      body: JSON.stringify(update),
    });
    const ms = performance.now() - t0;
    return { status: res.status, ms, timing: res.headers.get('server-timing'), body: await res.json().catch(() => null) };
  };
  const health = async () => {
    const t0 = performance.now();
    const res = await fetch(url);
    return { ms: performance.now() - t0, body: await res.json() };
  };
  const first = await health();
  console.log(`GET health: ${first.ms.toFixed(0)} ms total, cold=${first.body.cold}, engineInitMs=${first.body.engineInitMs}`);
  const chat = { id: 1, type: 'private' };
  const from = { id: 1, is_bot: false, first_name: 'smoke' };
  const text = await post({ update_id: 1, message: { message_id: 1, date: 0, chat, from, text: 'togri gap, ozbekcha yozish oson' } });
  console.log(`POST text: HTTP ${text.status}, ${text.ms.toFixed(0)} ms total, ${text.timing}`);
  console.log(text.body?.text);
  const inline = await post({ update_id: 2, inline_query: { id: 'q', from, query: 'sosib pisib togri', offset: '' } });
  console.log(`POST inline: HTTP ${inline.status}, ${inline.ms.toFixed(0)} ms total, ${inline.timing}`);
  for (const r of inline.body?.results ?? []) console.log(`  ${r.title}: ${r.input_message_content.message_text}`);
  const warm = [];
  for (let i = 0; i < 10; i++) warm.push((await post({ update_id: 10 + i, message: { message_id: 10 + i, date: 0, chat, from: { ...from, id: 100 + i }, text: 'wunaqa qilib yozsangiz ham boladi' } })).ms);
  warm.sort((a, b) => a - b);
  console.log(`warm POST ×10: median ${warm[5].toFixed(0)} ms, max ${warm[9].toFixed(0)} ms (round trip from this machine)`);
  const bad = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' });
  console.log(`POST without secret: HTTP ${bad.status} (expect 401)`);
} else {
  console.error('usage: webhook.mjs set <url> | info | smoke <url>');
  process.exit(1);
}
