// Handler logic with mocked Telegram payloads. The real engine and lexicon are used;
// the real Telegram API is never called.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { engine } from '../src/engine.js';
import { createBot, MAX_TEXT, INPUT_CUT, MESSAGE_LIMIT, INLINE_LIMIT } from '../src/core.js';
import { BOT_ID, USERNAME, textMessage, message, inline, user, groupChat } from './helpers.js';

const newBot = () => createBot({ engine, botId: BOT_ID, username: USERNAME });
const convert = (t, s) => { engine.options.script = s; const o = engine.autocorrect(t); engine.options.script = 'new'; return o; };
const T0 = 1_000_000;

test('direct text: all three forms, labelled, each in a code block', () => {
  const r = newBot().handleUpdate(textMessage('sosib pisib togri'), T0);
  assert.equal(r.kind, 'text');
  assert.equal(r.messages.length, 1);
  const m = r.messages[0];
  assert.equal(m.parse_mode, 'HTML');
  assert.equal(m.chat_id, 42);
  for (const [label, script] of [['Yangi alifbo', 'new'], ['Eski lotin', 'old'], ['Kirill', 'cyrillic']]) {
    assert.ok(m.text.includes(`<b>${label}</b>\n<pre>${convert('sosib pisib togri', script)}</pre>`), label);
  }
  assert.ok(m.text.indexOf('Yangi alifbo') < m.text.indexOf('Eski lotin') && m.text.indexOf('Eski lotin') < m.text.indexOf('Kirill'));
});

test('already correct in a script: says so instead of echoing', () => {
  const r = newBot().handleUpdate(textMessage('töğri gap'), T0);
  const t = r.messages[0].text;
  assert.ok(t.includes('<b>Yangi alifbo</b> — matn allaqachon toʻgʻri ✓'), t);
  assert.ok(t.includes('<b>Eski lotin</b>\n<pre>toʻgʻri gap</pre>'), t);
  const c = newBot().handleUpdate(textMessage('тўғри гап'), T0).messages[0].text;
  assert.ok(c.includes('<b>Kirill</b> — matn allaqachon toʻgʻri ✓'), c);
});

test('unknown words are still written in every script, never left in Latin (§6.5)', () => {
  const t = newBot().handleUpdate(textMessage('kelaslar ishlating'), T0).messages[0].text;
  assert.ok(t.includes('<b>Kirill</b>\n<pre>келаслар ишлатинг</pre>'), t);
  assert.ok(t.includes('<b>Yangi alifbo</b> — matn allaqachon toʻgʻri ✓') || t.includes('<pre>kelaslar'), t);
  const c = newBot().handleUpdate(textMessage('келаслар'), T0).messages[0].text;
  assert.ok(!/[\u0400-\u052f]/.test(c.split('<b>Kirill</b>')[0]), c);
});

test('HTML in the input is escaped', () => {
  const t = newBot().handleUpdate(textMessage('<b>togri</b> & gap'), T0).messages[0].text;
  assert.ok(!t.includes('<b>togri</b>') && t.includes('&lt;b&gt;'), t);
});

test('no letters: short reply', () => {
  const r = newBot().handleUpdate(textMessage('12345 😊 !!!'), T0);
  assert.equal(r.kind, 'no_letters');
  assert.ok(r.messages[0].text.length < 80);
});

test('text over 4096 characters: first 4000 processed, cut is announced, every message fits', () => {
  const long = 'togri gap '.repeat(410) + 'OXIRGIQISM'; // 4110 characters; the marker sits past 4000
  const r = newBot().handleUpdate(textMessage(long), T0);
  assert.equal(r.kind, 'text');
  assert.equal(r.cut, true);
  assert.ok(r.messages[0].text.includes('birinchi 4000 belgi'), r.messages[0].text.slice(0, 200));
  for (const m of r.messages) assert.ok(m.text.length <= MAX_TEXT, `message of ${m.text.length}`);
  const joined = r.messages.map((m) => m.text).join('');
  assert.ok(!joined.includes('OXIRGIQISM'), 'text beyond 4000 must not appear');
  assert.ok(joined.includes('töğri gap'));
});

test('a reply too long for one message is split per script, each within the limit', () => {
  const r = newBot().handleUpdate(textMessage('shoshib pishib togri '.repeat(150)), T0); // 3150 chars
  assert.equal(r.messages.length, 3);
  for (const m of r.messages) assert.ok(m.text.length <= MAX_TEXT);
  assert.ok(r.messages[0].text.startsWith('<b>Yangi alifbo</b>'));
  assert.ok(r.messages[2].text.startsWith('<b>Kirill</b>'));
});

for (const [name, extra] of [
  ['photo', { photo: [{ file_id: 'x', width: 1, height: 1 }], caption: 'togri' }],
  ['sticker', { sticker: { file_id: 'x', type: 'regular' } }],
  ['voice', { voice: { file_id: 'x', duration: 3 } }],
  ['document', { document: { file_id: 'x' } }],
]) {
  test(`non-text (${name}): friendly reply, no crash`, () => {
    const r = newBot().handleUpdate(message(extra), T0);
    assert.equal(r.kind, 'non_text');
    assert.match(r.messages[0].text, /matn bilan ishlayman/);
  });
}

test('forwarded message: friendly reply, text not converted', () => {
  const r = newBot().handleUpdate(textMessage('togri', { forward_origin: { type: 'user', date: 0, sender_user: user(7) } }), T0);
  assert.equal(r.kind, 'forwarded');
  assert.ok(!r.messages[0].text.includes('töğri'));
});

test('inline, empty query: a single usage hint', () => {
  for (const q of ['', '   ', '123']) {
    const r = newBot().handleUpdate(inline(q), T0);
    assert.equal(r.kind, 'inline_empty');
    assert.equal(r.inline.results.length, 1);
    assert.ok(r.inline.results[0].description.includes(`@${USERNAME}`));
  }
});

test('inline query: three results — new Latin first — with Uzbek titles and short descriptions', () => {
  const r = newBot().handleUpdate(inline('sosib pisib togri'), T0);
  assert.equal(r.kind, 'inline');
  const res = r.inline.results;
  assert.deepEqual(res.map((x) => x.title), ['Yangi alifbo', 'Eski lotin', 'Kirill']);
  assert.deepEqual(res.map((x) => x.input_message_content.message_text),
    ['new', 'old', 'cyrillic'].map((s) => convert('sosib pisib togri', s)));
  for (const x of res) assert.ok(x.description.length <= 60);
  assert.equal(r.inline.is_personal, false);
});

test('inline query already in new Latin: description says so', () => {
  const r = newBot().handleUpdate(inline('töğri'), T0);
  assert.equal(r.inline.results[0].description, 'allaqachon toʻgʻri');
});

test('rate limit: 20 messages a minute per user, silent drop above, recovers after a minute', () => {
  const bot = newBot();
  for (let i = 0; i < MESSAGE_LIMIT; i++) assert.equal(bot.handleUpdate(textMessage('togri'), T0 + i).kind, 'text');
  const dropped = bot.handleUpdate(textMessage('togri'), T0 + 100);
  assert.equal(dropped.kind, 'rate_limited');
  assert.equal(dropped.messages, undefined);
  assert.equal(bot.handleUpdate(textMessage('togri', { from: user(99), chat: { id: 99, type: 'private' } }), T0 + 100).kind, 'text', 'other users unaffected');
  assert.equal(bot.handleUpdate(textMessage('togri'), T0 + 61_000).kind, 'text');
});

test('rate limit: inline queries have their own, larger budget', () => {
  const bot = newBot();
  for (let i = 0; i < INLINE_LIMIT; i++) assert.notEqual(bot.handleUpdate(inline('togri'), T0 + i).kind, 'rate_limited');
  assert.equal(bot.handleUpdate(inline('togri'), T0 + 100).kind, 'rate_limited');
  assert.equal(bot.handleUpdate(textMessage('togri'), T0 + 100).kind, 'text');
});

test('group: ordinary messages are ignored', () => {
  const r = newBot().handleUpdate(textMessage('togri gap', { chat: groupChat() }), T0);
  assert.equal(r.kind, 'ignored');
});

test('group: a mention is answered, with the mention removed, as a reply', () => {
  const r = newBot().handleUpdate(textMessage(`@${USERNAME} togri gap`, { chat: groupChat() }), T0);
  assert.equal(r.kind, 'text');
  assert.ok(r.messages[0].text.includes(`<pre>${convert('togri gap', 'new')}</pre>`));
  assert.ok(!r.messages[0].text.includes(USERNAME));
  assert.ok(r.messages[0].reply_parameters.message_id);
});

test('group: mention of another account is ignored', () => {
  assert.equal(newBot().handleUpdate(textMessage('@someone togri', { chat: groupChat() }), T0).kind, 'ignored');
});

test('group: a reply to the bot is answered; a reply to someone else is not', () => {
  const toBot = newBot().handleUpdate(textMessage('togri', { chat: groupChat(), reply_to_message: { message_id: 5, from: { id: BOT_ID, is_bot: true } } }), T0);
  assert.equal(toBot.kind, 'text');
  const toUser = newBot().handleUpdate(textMessage('togri', { chat: groupChat(), reply_to_message: { message_id: 5, from: user(7), text: 'x' } }), T0);
  assert.equal(toUser.kind, 'ignored');
});

test('group: a bare mention replying to someone converts that message', () => {
  const r = newBot().handleUpdate(textMessage(`@${USERNAME}`, { chat: groupChat(), reply_to_message: { message_id: 5, from: user(7), text: 'ozbekcha yozish' } }), T0);
  assert.equal(r.kind, 'text');
  assert.ok(r.messages[0].text.includes(convert('ozbekcha yozish', 'new')));
});

test('group: commands only when addressed to this bot', () => {
  assert.equal(newBot().handleUpdate(textMessage('/start', { chat: groupChat() }), T0).kind, 'ignored');
  assert.equal(newBot().handleUpdate(textMessage(`/start@${USERNAME}`, { chat: groupChat() }), T0).kind, 'command');
  assert.equal(newBot().handleUpdate(textMessage('/start@OtherBot', { chat: groupChat() }), T0).kind, 'ignored');
  assert.equal(newBot().handleUpdate(textMessage('/help@OtherBot'), T0).kind, 'ignored');
});

test('group: non-text only when replying to the bot', () => {
  assert.equal(newBot().handleUpdate(message({ chat: groupChat(), sticker: { file_id: 'x' } }), T0).kind, 'ignored');
  assert.equal(newBot().handleUpdate(message({ chat: groupChat(), sticker: { file_id: 'x' }, reply_to_message: { message_id: 1, from: { id: BOT_ID } } }), T0).kind, 'non_text');
});

test('ignored: other bots, messages sent via this bot, channels, edits, unknown update types', () => {
  const bot = newBot();
  assert.equal(bot.handleUpdate(textMessage('togri', { from: { id: 5, is_bot: true } }), T0).kind, 'ignored');
  assert.equal(bot.handleUpdate(textMessage('togri', { via_bot: { id: BOT_ID } }), T0).kind, 'ignored');
  assert.equal(bot.handleUpdate(textMessage('togri', { chat: { id: -1, type: 'channel' } }), T0).kind, 'ignored');
  assert.equal(bot.handleUpdate({ update_id: 1, edited_message: { text: 'togri' } }, T0).kind, 'ignored');
  assert.equal(bot.handleUpdate({ update_id: 1, callback_query: {} }, T0).kind, 'ignored');
  assert.equal(bot.handleUpdate(null, T0).kind, 'ignored');
});

test('/start: what it does, a real before/after, inline usage, the site', () => {
  const t = newBot().handleUpdate(textMessage('/start'), T0).messages[0].text;
  assert.ok(t.includes(`<code>${convert('togri gap, ozbekcha yozish oson', 'new')}</code>`), t);
  assert.ok(t.includes(`@${USERNAME} matn`));
  assert.ok(t.includes('chertma.maqsudjon.com'));
});

test('/help is shorter than /start', () => {
  const bot = newBot();
  const help = bot.handleUpdate(textMessage('/help'), T0).messages[0].text;
  const start = bot.handleUpdate(textMessage('/start'), T0 + 1).messages[0].text;
  assert.ok(help.length < start.length / 2);
  assert.ok(help.includes('chertma.maqsudjon.com'));
});

test('/nima: two sentences, kelaslar and qisela shown unchanged', () => {
  const t = newBot().handleUpdate(textMessage('/nima'), T0).messages[0].text;
  assert.ok(t.includes('<code>kelaslar</code> → <code>kelaslar</code> (oʻzgarmadi)'), t);
  assert.ok(t.includes('<code>qisela</code> → <code>qisela</code> (oʻzgarmadi)'), t);
  assert.equal(t.split('\n')[0].split('. ').length, 2);
});

test('unknown command: short hint', () => {
  assert.match(newBot().handleUpdate(textMessage('/foo'), T0).messages[0].text, /\/help/);
});

test('privacy: handling messages writes nothing to the console', () => {
  const marker = 'MAXFIY-matn-xyz togri';
  const seen = [];
  const orig = {};
  for (const k of ['log', 'info', 'warn', 'error', 'debug']) {
    orig[k] = console[k];
    console[k] = (...a) => seen.push(a.join(' '));
  }
  try {
    const bot = newBot();
    bot.handleUpdate(textMessage(marker), T0);
    bot.handleUpdate(inline(marker), T0);
    bot.handleUpdate(textMessage(`@${USERNAME} ${marker}`, { chat: groupChat() }), T0);
  } finally {
    Object.assign(console, orig);
  }
  assert.deepEqual(seen, []);
});
