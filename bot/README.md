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
scripts/vendor.mjs  copies engine/ and one lexicon build into _vendor/ (gitignored)
scripts/deploy.mjs  vendor → test → deploy from bot/ → verify live. THE way to deploy.
scripts/check-live.mjs  asserts the live bot answers and Telegram has no fresh error
scripts/webhook.mjs set / info / smoke — reads the token from ../.env, never prints it
test/               node:test, mocked payloads, no real API calls
```

- `engine/` is never modified; `scripts/vendor.mjs` copies it byte for byte and a test checks it.
- No database, no accounts, no state beyond an in-memory rate limit, no logging of what people type.
- The token lives only in Vercel's environment (`CHERTMA_BOT_TOKEN`) and in the repo's gitignored `.env`.

```bash
npm test
```

Deploying: `npm run deploy` (from `bot/`). Nothing else.

**Never run `vercel --prod` from the repo root.** The Vercel project has no root
directory set, so a deployment built from the repo root contains no `api/`, every
Telegram update gets 404, and the bot goes silent while `getWebhookInfo` still shows
the right url. That is how it died on 2026-09-16: a `git push` to `main` triggered a
production build from the repo root through the GitHub integration. The integration is
now disconnected — this project deploys from the CLI only — and `npm run deploy` ends
with `scripts/check-live.mjs`, which fails loudly if the function is missing or the
webhook is erroring.
