# Chertma Telegram bot

A thin Telegram front-end for `engine/`: send it text, get new Latin, old Latin and
Cyrillic back. Inline mode works in any chat. It runs as one Vercel serverless
function behind a Telegram webhook.

```
api/telegram.js     the function: POST = Telegram updates, GET = health (timings, counts)
src/core.js         update → reply; pure, no network, no logging
src/texts.js        everything the bot says (Uzbek)
src/engine.js       loads the engine and lite lexicon once per instance
src/ratelimit.js    20 messages/min per user, in memory
src/telegram.js     Bot API calls, errors returned as values
scripts/vendor.mjs  copies engine/ and the lite lexicon into _vendor/ (gitignored)
scripts/webhook.mjs set / info / smoke — reads the token from ../.env, never prints it
test/               node:test, mocked payloads, no real API calls
```

- `engine/` is never modified; `scripts/vendor.mjs` copies it byte for byte and a test checks it.
- No database, no accounts, no state beyond an in-memory rate limit, no logging of what people type.
- The token lives only in Vercel's environment (`CHERTMA_BOT_TOKEN`) and in the repo's gitignored `.env`.

```bash
npm test
```

Deploying: see `docs/FOR-MAQSUDJON.md`, section "Telegram bot".
