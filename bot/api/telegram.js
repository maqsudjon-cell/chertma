// Vercel serverless function: the Telegram webhook.
//
//   POST /api/telegram   Telegram updates. Checked against the webhook secret header.
//   GET  /api/telegram   Health: timings and invocation counts. Never message content.
//
// The reply goes back in the webhook response body (Telegram executes it), so a
// normal update costs no outbound call. Only a reply too long for one message is
// sent through the Bot API, one call per part.
//
// Privacy: nothing that people type is logged, stored or counted beyond a number.

import { timingSafeEqual } from 'node:crypto';
import { engine as sharedEngine, initMs, lexiconBuild } from '../src/engine.js';
import { createBot } from '../src/core.js';
import { callApi } from '../src/telegram.js';

const instanceStartedAt = Date.now();

function secretMatches(expected, got) {
  if (!expected) return true;
  if (typeof got !== 'string') return false;
  const a = Buffer.from(expected);
  const b = Buffer.from(got);
  return a.length === b.length && timingSafeEqual(a, b);
}

async function readBody(req) {
  if (req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body)) return req.body;
  let raw = typeof req.body === 'string' ? req.body : Buffer.isBuffer(req.body) ? req.body.toString('utf8') : null;
  if (raw === null && typeof req[Symbol.asyncIterator] === 'function') {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    raw = Buffer.concat(chunks).toString('utf8');
  }
  try { return JSON.parse(raw ?? ''); } catch { return null; }
}

function send(res, status, body, handlerMs) {
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  if (handlerMs !== undefined) res.setHeader('Server-Timing', `handler;dur=${handlerMs.toFixed(1)}`);
  res.end(JSON.stringify(body));
}

export function makeHandler({ env = process.env, fetchImpl = globalThis.fetch, now = Date.now, engine = sharedEngine } = {}) {
  const counts = {};
  const count = (k) => { counts[k] = (counts[k] ?? 0) + 1; };
  const token = env.CHERTMA_BOT_TOKEN;
  const botId = token ? Number(String(token).split(':')[0]) : undefined;
  let username = env.CHERTMA_BOT_USERNAME;
  let bot = null;
  let invocations = 0;

  async function getBot() {
    if (bot) return bot;
    if (!username && token) {
      const me = await callApi(token, 'getMe', {}, { fetchImpl });
      if (me.ok) username = me.result.username;
      else count(`api_error_${me.code}`);
    }
    bot = createBot({ engine, botId, username: username ?? 'Chertmabot', counts });
    return bot;
  }

  return async function handler(req, res) {
    const t0 = performance.now();
    invocations += 1;
    const cold = invocations === 1;
    try {
      if (req.method === 'GET') {
        send(res, 200, {
          ok: true,
          service: 'chertma-bot',
          cold,
          engineInitMs: Math.round(initMs * 10) / 10,
          instanceAgeS: Math.round((now() - instanceStartedAt) / 1000),
          lexicon: lexiconBuild,
          lexiconWords: engine.stats().lexiconSize,
          invocations,
          counts,
        }, performance.now() - t0);
        return;
      }
      if (req.method !== 'POST') { send(res, 405, { ok: false }); return; }
      if (!secretMatches(env.CHERTMA_WEBHOOK_SECRET, req.headers?.['x-telegram-bot-api-secret-token'])) {
        count('bad_secret');
        send(res, 401, { ok: false });
        return;
      }
      const update = await readBody(req);
      if (!update) { count('bad_body'); send(res, 200, {}, performance.now() - t0); return; }

      const result = (await getBot()).handleUpdate(update, now());
      count(`update_${result.kind}`);

      if (result.inline) {
        send(res, 200, { method: 'answerInlineQuery', ...result.inline }, performance.now() - t0);
        return;
      }
      const messages = result.messages ?? [];
      if (messages.length === 1) {
        send(res, 200, { method: 'sendMessage', ...messages[0] }, performance.now() - t0);
        return;
      }
      for (const params of messages) {
        const r = await callApi(token, 'sendMessage', params, { fetchImpl });
        if (!r.ok) count(`api_error_${r.code}`);
      }
      send(res, 200, {}, performance.now() - t0);
    } catch (err) {
      // Never crash, never let Telegram retry a poisoned update, never log its content.
      count(`handler_error_${err?.name ?? 'unknown'}`);
      try { send(res, 200, {}, performance.now() - t0); } catch { /* response already sent */ }
    }
  };
}

export default makeHandler();
