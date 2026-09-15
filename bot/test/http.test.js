// The Vercel function with fake requests and a mocked fetch.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeHandler } from '../api/telegram.js';
import { FAKE_TOKEN, USERNAME, textMessage, inline, http } from './helpers.js';

const SECRET = 'test-secret-value';
const env = { CHERTMA_BOT_TOKEN: FAKE_TOKEN, CHERTMA_WEBHOOK_SECRET: SECRET, CHERTMA_BOT_USERNAME: USERNAME };
const headers = { 'x-telegram-bot-api-secret-token': SECRET };
const noFetch = async () => { throw new Error('the real API must not be called in this test'); };

test('GET: health with timings and counts, no token, no content', async () => {
  const h = makeHandler({ env, fetchImpl: noFetch });
  const a = http('GET');
  await h(a.req, a.res);
  const body = a.json();
  assert.equal(a.res.statusCode, 200);
  assert.equal(body.cold, true);
  assert.ok(body.engineInitMs > 0);
  assert.equal(body.lexiconWords, 50000);
  const b = http('GET');
  await h(b.req, b.res);
  assert.equal(b.json().cold, false);
  assert.ok(!a.res.body.includes(FAKE_TOKEN.split(':')[1]));
});

test('POST without the right secret: 401, update not processed', async () => {
  const h = makeHandler({ env, fetchImpl: noFetch });
  for (const hd of [{}, { 'x-telegram-bot-api-secret-token': 'wrong' }]) {
    const x = http('POST', textMessage('togri'), hd);
    await h(x.req, x.res);
    assert.equal(x.res.statusCode, 401);
  }
});

test('POST text: sendMessage in the webhook response, no outbound call', async () => {
  const h = makeHandler({ env, fetchImpl: noFetch });
  const x = http('POST', textMessage('togri gap'), headers);
  await h(x.req, x.res);
  const body = x.json();
  assert.equal(x.res.statusCode, 200);
  assert.equal(body.method, 'sendMessage');
  assert.ok(body.text.includes('töğri gap'));
  assert.match(x.res.headers['server-timing'], /^handler;dur=/);
});

test('POST inline query: answerInlineQuery in the webhook response', async () => {
  const h = makeHandler({ env, fetchImpl: noFetch });
  const x = http('POST', inline('togri'), headers);
  await h(x.req, x.res);
  assert.equal(x.json().method, 'answerInlineQuery');
  assert.equal(x.json().results.length, 3);
});

test('POST raw JSON string and malformed bodies: 200, no crash', async () => {
  const h = makeHandler({ env, fetchImpl: noFetch });
  const ok = http('POST', JSON.stringify(textMessage('togri')), headers);
  await h(ok.req, ok.res);
  assert.equal(ok.json().method, 'sendMessage');
  for (const bad of ['{not json', '', undefined]) {
    const x = http('POST', bad, headers);
    await h(x.req, x.res);
    assert.equal(x.res.statusCode, 200);
    assert.deepEqual(x.json(), {});
  }
});

test('long reply: one Bot API call per part, then an empty 200', async () => {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, body: JSON.parse(init.body) });
    return { status: 200, json: async () => ({ ok: true, result: {} }) };
  };
  const h = makeHandler({ env, fetchImpl });
  const x = http('POST', textMessage('shoshib pishib togri '.repeat(150)), headers);
  await h(x.req, x.res);
  assert.equal(calls.length, 3);
  assert.ok(calls.every((c) => c.url.endsWith('/sendMessage') && c.body.text.length <= 4096));
  assert.deepEqual(x.json(), {});
});

test('Telegram API errors are caught: network failure, error response, timeout', async () => {
  for (const [label, fetchImpl, code] of [
    ['network', async () => { throw new TypeError('fetch failed'); }, 'api_error_network'],
    ['403', async () => ({ status: 403, json: async () => ({ ok: false, error_code: 403, description: 'bot was blocked' }) }), 'api_error_403'],
    ['bad json', async () => ({ status: 502, json: async () => { throw new SyntaxError('x'); } }), 'api_error_502'],
  ]) {
    const h = makeHandler({ env, fetchImpl });
    const x = http('POST', textMessage('shoshib pishib togri '.repeat(150)), headers);
    await h(x.req, x.res);
    assert.equal(x.res.statusCode, 200, label);
    const g = http('GET');
    await h(g.req, g.res);
    assert.equal(g.json().counts[code], 3, `${label}: ${JSON.stringify(g.json().counts)}`);
  }
});

test('an exception inside handling is caught: 200, counted, nothing logged', async () => {
  const broken = { options: {}, autocorrect() { throw new RangeError('boom'); }, stats: () => ({ lexiconSize: 0 }) };
  const seen = [];
  const orig = console.error;
  console.error = (...a) => seen.push(a);
  try {
    const h = makeHandler({ env, fetchImpl: noFetch, engine: broken });
    const x = http('POST', textMessage('togri'), headers);
    await h(x.req, x.res);
    assert.equal(x.res.statusCode, 200);
    const g = http('GET');
    await h(g.req, g.res);
    assert.equal(g.json().counts.handler_error_RangeError, 1);
  } finally {
    console.error = orig;
  }
  assert.equal(seen.length, 0);
});

test('bot username from getMe when not configured; getMe failure does not crash', async () => {
  const good = async (url) => ({ status: 200, json: async () => (url.endsWith('/getMe') ? { ok: true, result: { username: 'FromGetMe' } } : { ok: true }) });
  const h = makeHandler({ env: { ...env, CHERTMA_BOT_USERNAME: undefined }, fetchImpl: good });
  const x = http('POST', textMessage('/help'), headers);
  await h(x.req, x.res);
  assert.ok(x.json().text.includes('@FromGetMe'));
  const h2 = makeHandler({ env: { ...env, CHERTMA_BOT_USERNAME: undefined }, fetchImpl: async () => { throw new Error('down'); } });
  const y = http('POST', textMessage('togri'), headers);
  await h2(y.req, y.res);
  assert.equal(y.json().method, 'sendMessage');
});

test('other methods: 405', async () => {
  const x = http('PUT');
  await makeHandler({ env, fetchImpl: noFetch })(x.req, x.res);
  assert.equal(x.res.statusCode, 405);
});
