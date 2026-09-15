// Turns one Telegram update into what the bot should send. Pure: no network, no
// clock except the one passed in, no logging — and never any record of what
// people typed.

import { RateLimiter } from './ratelimit.js';
import {
  LABELS, T, esc, startText, helpText, nimaText, inlineHintMessage,
} from './texts.js';

export const MAX_TEXT = 4096;    // Telegram's message length limit
export const INPUT_CUT = 4000;   // longer input is cut to this many characters
export const INLINE_MAX = 256;   // Telegram's inline query length limit
export const MESSAGE_LIMIT = 20; // messages per user per minute (silent drop above)
export const INLINE_LIMIT = 60;  // inline queries per user per minute — default B6
export const INLINE_CACHE_S = 300;
const SCRIPTS = ['new', 'old', 'cyrillic'];

const CYR = /[Ѐ-ԯ]/;
const LAT = /[A-Za-zÀ-ɏ]/;
const LETTER = /\p{L}/u;
const OLD_MARKS = /sh|ch|[og]['`´‘’ʻʼʽʿ′]/i;
const NEW_MARKS = /[şçöğ]/i;

/**
 * 'changed' — the output differs from the input.
 * 'already' — unchanged, and the input is already written in that script.
 * 'unchanged' — unchanged, but not because it was already right (unknown words).
 */
export function status(script, text, out) {
  if (out !== text) return 'changed';
  if (script === 'cyrillic') return CYR.test(text) && !LAT.test(text) ? 'already' : 'unchanged';
  if (CYR.test(text)) return 'unchanged';
  if (script === 'new') return OLD_MARKS.test(text) ? 'unchanged' : 'already';
  return NEW_MARKS.test(text) ? 'unchanged' : 'already';
}

function cutString(s, n) {
  if (s.length <= n) return s;
  let end = n;
  const code = s.charCodeAt(end - 1);
  if (code >= 0xd800 && code <= 0xdbff) end -= 1; // never split a surrogate pair
  return s.slice(0, end);
}

export function createBot({ engine, botId, username, counts = {}, messageLimiter, inlineLimiter }) {
  const perMessage = messageLimiter ?? new RateLimiter(MESSAGE_LIMIT);
  const perInline = inlineLimiter ?? new RateLimiter(INLINE_LIMIT);
  const count = (k) => { counts[k] = (counts[k] ?? 0) + 1; };
  const uname = (username ?? '').toLowerCase();

  function convert(text, script) {
    engine.options.script = script;
    try {
      return engine.autocorrect(text);
    } finally {
      engine.options.script = 'new';
    }
  }

  const forms = (text) => Object.fromEntries(SCRIPTS.map((s) => [s, convert(text, s)]));

  function section(script, text, out) {
    const st = status(script, text, out);
    if (st === 'already') return `<b>${LABELS[script]}</b> — ${T.already}`;
    if (st === 'unchanged') return `<b>${LABELS[script]}</b> — ${T.unchanged}`;
    return `<b>${LABELS[script]}</b>\n<pre>${esc(out)}</pre>`;
  }

  /** One message when it fits; otherwise one message per script, each cut to fit. */
  function conversionMessages(text, cutNote) {
    const out = forms(text);
    const note = cutNote ? `<i>${esc(T.cut(INPUT_CUT))}</i>\n\n` : '';
    const whole = note + SCRIPTS.map((s) => section(s, text, out[s])).join('\n\n');
    if (whole.length <= MAX_TEXT) return [whole];
    return SCRIPTS.map((s, i) => {
      const head = (i === 0 ? note : '') + `<b>${LABELS[s]}</b>\n`;
      const st = status(s, text, out[s]);
      if (st !== 'changed') return head.trimEnd() + ' — ' + (st === 'already' ? T.already : T.unchanged);
      let body = out[s];
      let html = `${head}<pre>${esc(body)}</pre>`;
      while (html.length > MAX_TEXT) {
        body = cutString(body, Math.floor(body.length * 0.9));
        html = `${head}<pre>${esc(body)}${esc(T.partCut)}</pre>`;
      }
      return html;
    });
  }

  function reply(chat, message, texts, group) {
    return texts.map((text) => ({
      chat_id: chat.id,
      text,
      parse_mode: 'HTML',
      link_preview_options: { is_disabled: true },
      ...(group ? { reply_parameters: { message_id: message.message_id, allow_sending_without_reply: true } } : {}),
    }));
  }

  function handleInline(q, now) {
    if (!q.from || !perInline.allow(q.from.id, now)) { count('rate_limited'); return { kind: 'rate_limited' }; }
    const query = cutString((q.query ?? '').trim(), INLINE_MAX);
    const base = { inline_query_id: q.id, cache_time: INLINE_CACHE_S, is_personal: false };
    if (!query || !LETTER.test(query)) {
      count('inline_empty');
      return {
        kind: 'inline_empty',
        inline: {
          ...base,
          results: [{
            type: 'article',
            id: 'hint',
            title: T.inlineHintTitle,
            description: T.inlineHintDescription(username),
            input_message_content: { message_text: inlineHintMessage(username), parse_mode: 'HTML', link_preview_options: { is_disabled: true } },
          }],
        },
      };
    }
    count('inline');
    const out = forms(query);
    const results = SCRIPTS.map((s) => {
      const st = status(s, query, out[s]);
      const description = st === 'already' ? T.alreadyShort : st === 'unchanged' ? T.unchangedShort
        : out[s].length > 60 ? out[s].slice(0, 59) + '…' : out[s];
      return { type: 'article', id: s, title: LABELS[s], description, input_message_content: { message_text: out[s] } };
    });
    return { kind: 'inline', inline: { ...base, results } };
  }

  /** Is a group message addressed to the bot? Returns the text with the mention removed, or null. */
  function addressedText(message, text, entities) {
    const replyToBot = message.reply_to_message?.from?.id === botId;
    const ranges = [];
    let command = null;
    for (const e of entities) {
      const piece = text.slice(e.offset, e.offset + e.length);
      if (e.type === 'mention' && uname && piece.toLowerCase() === '@' + uname) ranges.push(e);
      else if (e.type === 'text_mention' && e.user?.id === botId) ranges.push(e);
      else if (e.type === 'bot_command' && e.offset === 0) command = piece;
    }
    const commandTarget = command && command.includes('@') ? command.split('@')[1].toLowerCase() : null;
    const addressed = replyToBot || ranges.length > 0 || (commandTarget && commandTarget === uname);
    if (!addressed) return null;
    let stripped = text;
    for (const e of [...ranges].sort((a, b) => b.offset - a.offset)) {
      stripped = stripped.slice(0, e.offset) + stripped.slice(e.offset + e.length);
    }
    return stripped.trim();
  }

  function handleMessage(message, now) {
    const chat = message.chat ?? {};
    const group = chat.type === 'group' || chat.type === 'supergroup';
    if (chat.type !== 'private' && !group) { count('ignored'); return { kind: 'ignored' }; }
    if (!message.from || message.from.is_bot || message.via_bot) { count('ignored'); return { kind: 'ignored' }; }

    const text = typeof message.text === 'string' ? message.text : null;
    const entities = message.entities ?? [];
    let body = text;
    if (group) {
      const replyToBot = message.reply_to_message?.from?.id === botId;
      if (text === null) {
        if (!replyToBot) { count('ignored'); return { kind: 'ignored' }; }
      } else {
        body = addressedText(message, text, entities);
        if (body === null) { count('ignored'); return { kind: 'ignored' }; }
        // "@bot" alone, replying to someone's message: convert that message.
        if (!body && message.reply_to_message?.text && message.reply_to_message.from?.id !== botId) {
          body = message.reply_to_message.text;
        }
      }
    }

    if (!perMessage.allow(message.from.id, now)) { count('rate_limited'); return { kind: 'rate_limited' }; }

    if (message.forward_origin || message.forward_date || message.forward_from || message.forward_from_chat) {
      count('forwarded');
      return { kind: 'forwarded', messages: reply(chat, message, [esc(T.forwarded)], group) };
    }
    if (text === null) {
      count('non_text');
      return { kind: 'non_text', messages: reply(chat, message, [esc(T.nonText)], group) };
    }

    const cmd = entities.find((e) => e.type === 'bot_command' && e.offset === 0);
    if (cmd) {
      const [name, target] = text.slice(1, cmd.length).split('@');
      if (target && target.toLowerCase() !== uname) { count('ignored'); return { kind: 'ignored' }; }
      count('command');
      const lower = name.toLowerCase();
      const out = lower === 'start' ? startText(username, convert)
        : lower === 'help' ? helpText(username)
          : lower === 'nima' ? nimaText(convert)
            : esc(T.unknownCommand);
      return { kind: 'command', command: lower, messages: reply(chat, message, [out], group) };
    }

    if (!body || !LETTER.test(body)) {
      count('no_letters');
      return { kind: 'no_letters', messages: reply(chat, message, [esc(T.noLetters)], group) };
    }

    const long = body.length > MAX_TEXT;
    if (long) count('cut');
    count('text');
    const input = long ? cutString(body, INPUT_CUT) : body;
    return { kind: 'text', cut: long, messages: reply(chat, message, conversionMessages(input, long), group) };
  }

  /** update → { kind, messages?: sendMessage params[], inline?: answerInlineQuery params } */
  function handleUpdate(update, now = Date.now()) {
    if (!update || typeof update !== 'object') { count('ignored'); return { kind: 'ignored' }; }
    if (update.inline_query) return handleInline(update.inline_query, now);
    if (update.message) return handleMessage(update.message, now);
    count('ignored');
    return { kind: 'ignored' };
  }

  return { handleUpdate, convert, forms };
}
