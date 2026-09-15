// Mocked Telegram payloads. IDs and the token are fake; no test reaches the real API.
export const BOT_ID = 111111;
export const USERNAME = 'ChertmaTestBot';
export const FAKE_TOKEN = `${BOT_ID}:TEST-not-a-real-token`;

let nextId = 1;
export const user = (id = 42) => ({ id, is_bot: false, first_name: 'Test' });
export const privateChat = (id = 42) => ({ id, type: 'private' });
export const groupChat = (id = -100500) => ({ id, type: 'supergroup', title: 'Group' });

export function message(extra = {}) {
  return { update_id: nextId++, message: { message_id: nextId++, date: 0, chat: privateChat(), from: user(), ...extra } };
}

export function textMessage(text, extra = {}) {
  const entities = [];
  const m = /^\/[a-z_]+(@\w+)?/i.exec(text);
  if (m) entities.push({ type: 'bot_command', offset: 0, length: m[0].length });
  for (const mm of text.matchAll(/@\w+/g)) {
    if (!(m && mm.index < m[0].length)) entities.push({ type: 'mention', offset: mm.index, length: mm[0].length });
  }
  return message({ text, ...(entities.length ? { entities } : {}), ...extra });
}

export function inline(query, from = user()) {
  return { update_id: nextId++, inline_query: { id: `iq${nextId++}`, from, query, offset: '' } };
}

/** A fake Vercel request/response pair. */
export function http(method, body, headers = {}) {
  const req = { method, headers, body };
  const res = {
    statusCode: 0, headers: {}, body: '',
    setHeader(k, v) { this.headers[k.toLowerCase()] = v; },
    end(b) { this.body = b ?? ''; this.ended = true; },
  };
  return { req, res, json: () => JSON.parse(res.body || 'null') };
}
