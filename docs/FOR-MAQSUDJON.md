# For Maqsudjon — unattended run of steps 3–7 (2026-09-15)

One file. Everything below is measured; `docs/TEST-OUTPUT.txt` is the full test run
it quotes.

## 1. The site is live

```
$ curl -sI https://chertma.maqsudjon.com | head -1
HTTP/2 200
```

- **https://chertma.maqsudjon.com** — GitHub Pages, certificate approved, HTTPS
  enforced (`http://` answers 301). Your DNS record resolves:
  `chertma.maqsudjon.com → maqsudjon-cell.github.io`.
- Repo: **https://github.com/maqsudjon-cell/chertma** (public). `main` holds the
  code; `gh-pages` holds the built site.
- Checked on the live URL in a browser: the engine loads, corrections and
  suggestions work, the service worker is active (status reads "internetsiz
  tayyor"), no console errors.
- Offline: checked locally — after one visit I stopped the server; the page
  reloaded from the service worker and corrected text with no network (an
  uncached request failed with a network error at the same moment).
- The page opens in Uzbek (new Latin); EN is one tap. It links to the benchmark
  *draft* on GitHub, not to Hugging Face.

To redeploy after any change: `python3 tools/build_site.py && tools/deploy_pages.sh`.

## 2. Acceptance criteria (CLAUDE.md §13)

| # | Criterion | Result | Measured |
|---|---|---|---|
| 1 | `sosib pisib togri kelasizmi` → `şoşib pişib töğri kelasizmi` | **FAIL** | Output is `şoşib pisib töğri kelasizmi`. `pisib` is a real word ("sneaking up", 3 394 times in books) and a valid word is never rewritten (Q19, default D1). The bigram table would pick `pişib` (`şoşib pişib` 3 004, `şoşib pisib` 0). Reported as TODO in `tests/acceptance.test.js`. |
| 2 | `kelaslar`, `qisela`, `balu`, `kettik` byte-identical | PASS | lite and full builds |
| 3 | All three scripts convert both directions on the golden file | PASS | every strict golden sentence: new → cyrillic → new and new → old → new; golden Cyrillic and old-Latin inputs → new |
| 4 | Round trip verified independently against uz-books-v2 lat/cyr | PASS | 99.83 % token agreement over 29 853 810 aligned words (floor 99.8 %). Lexicon round trip holds for every word except 53 (lite) / 373 (full) with ʼ before e/ye/yo/yu/ya — the Q2 `ъ` rule, reopened as Q2b |
| 5 | Every size budget met, numbers in the README | PASS | engine 12 009 B gz (≤ 30 KB); lite 739 813 B gz (≤ 2 MB); full 7 336 860 B gz (≤ 8 MB); heap growth with lite loaded 0.83 MB with forced GC (≤ 25 MB) |
| 6 | `suggest()` p95 under 5 ms | PASS | 0.82 ms p95 over 10 000 real prefixes, cold process; `load()` lite 23.7 ms (≤ 400 ms) |
| 7 | Site works with the network disconnected after first load | PASS | verified as described in §1 |
| 8 | `grep -ri "fetch\|XMLHttpRequest\|sendBeacon" engine/` returns nothing | PASS | exit 1, no output |
| 9 | `package.json` has an empty `dependencies` object | PASS | `{}` |
| 10 | `data/SOURCES.md` names every licence | PASS | uz-books-v2 MIT, uz-crawl Apache-2.0 |
| 11 | All benchmark items reviewed and signed off | **PARKED** | 440 drafted in `bench/review.md`, none reviewed |

`npm test`: **45 tests — 40 pass, 0 fail, 5 TODO** (criterion 1, criterion 7 as a
manual check, criterion 11, the 24 pairs, and the INCOMPLETE hand-written invariant set).

How well it corrects, on an unfiltered sample of real sentences (not tuned on):

| Input | Corrected | Wrong corrections | Precision | Missed |
|---|---|---|---|---|
| Latin news text with apostrophes removed | 695 | 1 | 99.9 % | 290 |
| Telegram Cyrillic with ў қ ғ ҳ replaced by у к г х | 471 | 14 | 97.1 % | 686 |

Several of the 14 "wrong" ones are the engine fixing a misspelling that was already
in the human-written original (`хужжатларига` → `hujjatlariga` where the source had
`х`); they are counted against the engine anyway.

## 3. Defaults I took, and why

Standing rule: the conservative default is "return the input unchanged". Full table
with file locations: `docs/OPEN-QUESTIONS.md` → "Defaults taken unattended".

| # | Default | Why | To reverse |
|---|---|---|---|
| D1 | A token that is already a word is never rewritten (Q19) | your Q4 ruling read literally; it is what makes criterion 1 fail | `engine/index.js` `_valid()` — allow a bigram-backed replacement |
| D2 | `autocorrect()` never applies a candidate that removes a typed mark, drops a typed tutuq, or turns Cyrillic `с` into `ş` (Q28) | `ўлимлар` → `olimlar` (deaths → scholars) and `шимдан` → `simdan` were real outputs | the `ev.min >= 0` filter |
| D3 | Title/UPPER words mid-sentence are only corrected to words the corpus capitalises; isolated ALL-CAPS words of ≤ 4 letters are never corrected (Q21) | `Sunday` → `Şunday`, `Elon` → `eʼlon`, `ХАМАС` → `hamas` | two filters in `autocorrect()`, `ACRONYM_MAX_LETTERS` |
| D4 | One-letter tokens never corrected (Q24) | `Ў` → `o` | one line in `autocorrect()` |
| D5 | Books' Russian-layout spellings (`tugri`, `bulgan`) left in the lexicon (Q29) | removing them adds corrections — the less conservative direction | `tools/pack_lexicon.py`, re-pack |
| D6 | Q2 `ъ` rule kept as you ruled; the round-trip failures it causes are counted, not failed | data contradicts it (`меъёр`/`meʼyor`) but it was your ruling | `engine/translit.js` `cyrOptions`, `tools/uzscript.py` |
| D7 | Rule 3 restored to "any marks removed" (Q20) | as approved at Q17 | — |
| D8 | Contamination filter counts only 2+ character tokens (Q22) | formula symbols were dropping textbooks | `tools/normalize_corpus.py` |
| D9 | "~10 000 generated" invariant forms = unknown Telegram surface forms that share no skeleton with a lite word (Q23b) | no written spec was in the repo | `tools/build_fixtures.py` |
| D10 | Site serves `lexicon-lite.bin.gz` and inflates it with `DecompressionStream` (Q26) | Pages serves `.gz` as `application/gzip` without re-compressing — confirmed live | `web/app.js` |
| D11 | Ranking constants left at the brief's λ 2.0, ν 0.5, informal mix 0.5 | grid search: every setting keeps all strict cases; these are in the best group | `engine/constants.js`, `tools/tune.mjs` |
| D12 | Books agreement floor 99.8 % | measured 99.83 % | `tests/thresholds.js` |
| D13 | A typed valid word is always among the suggestions | a keyboard should offer what you typed | `suggest()` |
| D14 | Hand-written invariant file is an empty placeholder; suite says INCOMPLETE | your 200 forms | `tests/fixtures/dialect-handwritten.json` |
| D15 | Foreign-collision list definition (see §5.3) | "as I specified" was not in the repo | `tools/build_fixtures.py` |
| D16 | No Hugging Face link on the site; link to the GitHub draft | nothing is published; namespace (Q15) undecided | `web/index.html` |
| D17 | Site opens in Uzbek for everyone | many Uzbek phones use Russian or English locales | `web/app.js` |
| D18 | No code licence chosen | the brief does not name one | `README.md` |
| D19 | Suggestions for Cyrillic input are shown in Cyrillic | `хозир kelib` looked broken | `web/app.js` |

## 4. What failed or did not work

- **Criterion 1** — see §2. It needs your Q19 ruling, not a code fix.
- **`тугри` stays `tugri`.** This is the headline example of Cyrillic keyboard recovery in SPEC §4.8 (the brief's own `тўғри` works). `tugri` is in the
  books 57 301 times (3.9 % of `töğri`), so it is a valid word. Q29 has the numbers for
  fixing it at 1 %, 5 % and 10 %, and the real words each threshold would wrongly drop.
- **Unknown words stay as typed in every output script** — Cyrillic output can contain
  a Latin word the lexicon does not know (`yozsangiz`). The page says so.
- **Ranked golden cases**: 98 of 150 sentences come out exactly right. Most misses are
  a different token in the sentence (a missed correction), not a ranking error.
- **Font**: JetBrains Mono has no `ʻ` (U+02BB) or `ҳ Ҳ`; those glyphs fall back to the
  system monospace font.
- **Specs you referred to as already given** — the ~200 / ~10 000 dialect split (Q23a/b)
  and the protected-word risk list "as I specified, expect under 100" — were not written
  anywhere in the repo or earlier messages. I took the definitions in D9 and D15.
- A crash in the count pipeline (output directory created too late) was caught by a smoke
  test before the full run. Nothing else failed. The first Pages API call returned 409
  "already enabled" because pushing `gh-pages` had enabled it; harmless.

## 5. The four parked items

1. **The 24 minimal pairs** — `docs/AMBIGUITY-REVIEW.md`, untouched and unmarked. Book
   counts are filled in to help. They are not in any test or benchmark item;
   `tests/ambiguity.test.js` uses only the ruled `ser / şer / şeʼr` and has a TODO for the rest.
2. **~200 hand-written dialect forms (Q23a)** — put them in
   `tests/fixtures/dialect-handwritten.json` as `{"forms": ["kelaslar", …]}`.
   `tests/invariant.test.js` then checks each comes back byte-identical and drops the
   INCOMPLETE label at 200. The 10 000 generated forms already pass.
3. **Protected-word risk list** — `data/foreign-collisions.tsv`, **77 rows**: crawl forms
   with ≥ 30 occurrences, ≥ 80 % title case, no tutuq, not a lite word, whose skeleton
   matches a lite word that is not itself a proper noun (`şarja → sarja`, `sunday →
   şunday`, `kisida → kişida`, `singh → sing`, …). **Nothing uses it.** Also still there:
   `data/protected-words.candidates.tsv` (3 725 literal sh/ch/gh words from checkpoint 2,
   gitignored) and `data/protected-words.txt` (empty).
4. **The benchmark** — `bench/review.md`, **440 draft items**: ascii2new 100, old2new 80,
   cyr2new 80, preserve 100 (the brief's four forms, then generated forms to replace with
   yours), apostrophe 40, edge 40, ambiguity 0 (parked with the pairs). Mark the last
   column `keep`, `fix: …` or `drop`, then `python3 tools/build_benchmark.py --export`
   writes `bench/dev.jsonl` / `bench/test.jsonl` from kept rows only.
   `bench/README.md` is a draft card (EN + UZ); `bench/run_eval.py` scores the engine, a
   Hugging Face model, or an API — tested only on a 3-item synthetic file, leaderboard
   empty. **Nothing was published to Hugging Face** — no repo, no stub.

## 6. Waiting for your ruling

Blocking better behaviour: **Q19** (valid words vs context — criterion 1), **Q29** (Russian-
layout spellings in books, and a ratio), **Q28** (confirm D2), **Q21** (confirm D3),
**Q2b** (`ъ` after a vowel, `ўъ`), **Q30** (vowel before `и`: `nuqtai` vs `nuqtayi`),
**Q31** (`qoyvor` — passthrough or `qöyvor`?).
Yes/no: Q20, Q22, Q23, Q24, Q25. Later: Q15 (Hugging Face namespace), the code licence (D18).

## 7. Housekeeping

- `data/raw` (3.9 GB) was deleted after the engine passed its tests. `data/uz-bigrams.tsv`
  (1.5 GB, gitignored) is still on disk; it is needed only to re-pack the lexicons:
  `rm data/uz-bigrams.tsv` frees it. 20 GB free now.
- Rebuilding fixtures or the lexicon needs the corpus again: `tools/fetch_corpus.py` +
  `tools/build_ngrams.py` (~3 hours, see `docs/STATUS.md`).
- `docs/STATUS.md` is current; a fresh session can resume from it.

---

## Telegram bot (2026-09-15)

Code: `bot/` (commit `1da4628` and later). `npm test` in `bot/`: **42 tests, 42 pass**, all with
mocked Telegram payloads and a mocked `fetch` — the real API is never called. `engine/`
is untouched; the bot runs a byte-identical copy and a test enforces it.

### Deployed — 2026-09-15

**https://chertma-bot.vercel.app/api/telegram** (Vercel project `chertma-bot`, production, `fra1`).
Env vars `CHERTMA_BOT_TOKEN`, `CHERTMA_WEBHOOK_SECRET`, `CHERTMA_BOT_USERNAME` set via the CLI.

| Step | Result |
|---|---|
| Deploy | Ready, first attempt. `GET /api/telegram` → 200, `lexiconWords` 50000, engine init 39.4 ms on Vercel. |
| setWebhook | ok, first attempt; `allowed_updates` message + inline_query. |
| getWebhookInfo | url set, `pending_update_count` 0, `last_error_message` null. |
| Real message | A Telegram-format update for `sosib pisib togri` was posted to the live function (with the secret header); its reply was delivered to your private chat with the bot through Bot API `sendMessage` (message_id 15). All three scripts present: `şoşib pisib töğri` / `shoshib pisib toʻgʻri` / `шошиб писиб тўғри`. |
| Inline | `getMe` now reports `supports_inline_queries: true`. The live function answers an inline query with three results in order Yangi alifbo, Eski lotin, Kirill, and an empty query with the usage hint. A real `answerInlineQuery` needs a query id that only Telegram issues when a person types `@Chertmabot …`; with a synthetic id the API returns 400 "query ID is invalid", as expected. |
| No secret | `POST` without the header → 401. |

`pisib` stays unconverted because of the open Q19 — the engine is frozen for the bot.

### Timings

On Vercel (from Tashkent): first GET after deploy 955 ms total (cold); webhook handler 13 ms for the first text update, 1.3 ms for an inline query; warm round trip median 316 ms, max 328 ms over 10 posts (mostly network).

Locally

Five fresh Node 22 processes on this Mac, handler called directly:

| | Measured |
|---|---|
| Module init: engine import + read + parse of `lexicon-lite.bin` | 56–77 ms |
| Node process start → handler ready | 311–389 ms |
| First update handled (cold) | 15–21 ms |
| Warm update (200 mixed messages and inline queries) | p50 0.5 ms, p95 1.3 ms, max 13 ms |

On Vercel, cold start adds the platform's own container start on top of the ~0.35 s
process-to-ready figure; the webhook round trip adds Telegram ↔ Frankfurt network time.
`node scripts/webhook.mjs smoke …` measures both on the real deployment. The function also
returns `Server-Timing: handler;dur=…` on every reply and reports `engineInitMs` and
`cold` on `GET /api/telegram`.

### BotFather settings you still need to set

1. `/setinline` — done (inline mode is on).
2. `/setcommands` → @Chertmabot →
   ```
   start - Chertma nima qiladi
   help - Qisqa yordam
   nima - Nimani toʻgʻrilaydi, nimaga tegmaydi
   ```
3. `/setdescription` (shown before someone presses Start), suggestion:
   `Oddiy klaviaturada yozilgan oʻzbekcha matnni yangi alifbo (Ş Ç Ö Ğ), eski lotin va kirillga oʻgiradi. Shevaga tegmaydi.`
4. `/setabouttext`, suggestion: `Matnni uch yozuvda qaytaradi. chertma.maqsudjon.com`
5. `/setuserpic` — optional; `web/icons/icon-512.png` is the dot-matrix Ş.
6. Leave `/setprivacy` **enabled** (it is) and `/setinlinefeedback` **disabled** — the bot
   keeps no data, so inline feedback would only send Telegram's copy of chosen results.

### Defaults I took without you

All sixteen are in `docs/OPEN-QUESTIONS.md` → "Telegram bot — defaults taken unattended".
The ones you will notice:

- **B1** Replies travel in the webhook response body; the Bot API is called only when a reply
  has to be split. Faster, and the token is used for almost nothing at run time.
- **B2** A random webhook secret (in `.env` and the Vercel env) — requests without it get 401.
- **B3** The bot's own messages are in old Latin with ʻ; conversions are shown in all three scripts.
- **B4** Your inline example will not come out as written: the engine gives `şoşib pisib töğri`
  (Q19) and writes old Latin with ʻ (`toʻgʻri`), not `to'g'ri`. The engine is frozen.
- **B5** Inline queries get their own 60/min per user; the 20/min applies to messages.
- **B6** Forwarded messages get the friendly reply even when they contain text.
- **B7** In groups a bare `@Chertmabot` replying to someone converts that message; bare `/start`
  without the username is ignored.
- **B8** "matn allaqachon toʻgʻri ✓" only when the text is unchanged *and* already in that
  script; otherwise "oʻzgarmadi — tanilmagan soʻzlar yozilganidek qoldi".
- **B12** Region `fra1`.

### What failed and why

Nothing failed. Not tested for real: `answerInlineQuery` with a Telegram-issued query id — type
`@Chertmabot togri gap` in any chat to see it. The first message you get from the bot in your chat
(message_id 15) is the test.

**Token hygiene.** The token lives only in the Vercel env and in the gitignored repo-root `.env`;
it was never printed, written to a new file, or committed. Every commit's staged diff was checked
for its first 8 characters (0 hits), and `.git/hooks/pre-commit` blocks any commit containing them.

---

## Morphology, mixed script and a bigger word list (2026-09-15 evening)

Details and full lists: **`docs/MORPHOLOGY-REVIEW.md`**.

### The number you asked for — not zero, so stopped

Invariant forms (10 000 generated, all three output scripts) that the morphological fallback
touches and did not before:

- **`'read'` mode** (stem + suffix valid exactly as typed, old-Latin spelling converted): **809**,
  all in new-Latin output — `ishlating → işlating`, `mashinangiz → maşinangiz`. No letter is corrected.
- **`true` mode** (stem corrected, suffix kept): **13 more**, and by my reading 12 of them are wrong
  (`maqtasin → maqtaşin`, `island → işland`, `ogʻritib → öğritib`). It also turns **`qoyvor` into `qöyvor`**.
- Dialect forms `kelaslar`, `qisela`, `balu`, `kettik`, `bormimiz` stay byte-identical in every mode (tested).

So the engine ships with **`morphology: false`**. The code (`engine/index.js` `_morph`), the suffix
inventory (2 232 chains, lexicon section 9) and tests pinning each mode are in place; switching it on
is one option.

### Mixed-script output — fixed and deployed to the bot

Anything not corrected is now transliterated by rule into the output script (SPEC §6.5): `ishlating`
in Kirill output is `ишлатинг`, `ишлатинг` in Latin output is `işlating`, `15та` → `15ta`, `TOGGнинг`
→ `TOGGning`, `Windows` → `Виндовс`, `щётка` → `şyotka`. URLs, emails, `@mentions` and `#hashtags`
stay as typed — the only exception. A new test checks every golden input in every script. Two golden
expectations that encoded the old behaviour were updated (G177, G207).

### Word list

Rebuilt from the checkpoint-2 counts with a **held-out 10 % of two crawl shards removed first**
(5.05 M tokens; subtraction exact — no count went negative).

Coverage on that held-out text (share of tokens whose word is in the lexicon):

| Build | Words | Gzipped | News | Telegram |
|---|---|---|---|---|
| lite, picked by frequency (the shipped word list) | 50 000 | 0.75 MB | 89.7 % | 87.6 % |
| lite, picked by crawl coverage (**parked**) | 50 000 | 0.75 MB | 92.8 % | 89.5 % |
| mid (built, measured, not used) | 150 000 | 3.40 MB | 95.0 % | 93.9 % |
| full (**bot**) | 400 000 | 7.34 MB | 97.2 % | 96.8 % |

The shipped lite was selected from counts that still contained the held-out text, so its row is
measured on the same selection rule rebuilt without that text.

Adding "or a stem in the lexicon + a suffix chain" raises lite-by-frequency to 95.3 % / 95.5 %
and full to 98.6 % / 98.9 % — the hole segmentation could close.

**Lite by coverage is parked**, same stop rule: it changes 181 invariant forms (25 with letters
substituted, some wrong) and breaks 6 strict golden cases (`Shirinning` no longer fixed; crawl-frequent
Russian-layout misspellings `xozir`, `kuyidan` became words). It also lifts ranked-sentence accuracy from
65.3 % to 72.7 %. The mobile lite keeps its word list and 2 MB budget (0.75 MB gz); it only gained the
suffix section.

### Bot on lexicon-full

| | Cold (first request) | Engine init | Warm round trip, median | Handler, median |
|---|---|---|---|---|
| before: lite, after hours idle | 5 367 ms | 43 ms | 598 ms | 0.9 ms |
| lite, right after a deploy | 934 ms | 42.3 ms | 383 ms | 0.9 ms |
| mid, right after a deploy | 960 ms | 128.6 ms | 429 ms | 0.8 ms |
| full, right after a deploy (2 runs) | 1085 / 1052 ms | 249.6 ms | 389 / 410 ms | 0.8 ms |
| full, after 25 min idle | 1 788 ms | 251 ms | 323 ms | 0.9 ms |

Round trips are from Tashkent to Frankfurt. The full lexicon adds about 200 ms of engine init; cold
start stays far under 3 s, so the bot runs **full** and no mid tier is used. Locally (5 runs each):
process start → ready 139–151 ms lite, 173–178 ms mid, 224–233 ms full; warm p95 under 1 ms for all.
Deployed: `https://chertma-bot.vercel.app/api/telegram`, webhook unchanged, `getWebhookInfo` clean.

### Not deployed

The **website** still runs the old engine, so it still leaves unknown words in the wrong script. The
new engine passes every test with the shipped lite; redeploy when you want it live:
`python3 tools/build_site.py && tools/deploy_pages.sh`.

### Needs you

1. Morphology: look at the 13 stage-2 forms and the 809 stage-1 list; say `false`, `'read'` or `true`.
2. Lite by coverage: accept the 25 substitutions and 6 golden regressions for +3 points coverage, or
   keep the frequency lite. The regressions come from Q29 (Russian-layout spellings admitted as words) —
   ruling Q29 would fix most of them in either build.
3. Defaults M1–M14 in `docs/OPEN-QUESTIONS.md`.

Tests: engine 54 tests — 48 pass, 0 fail, 6 TODO (the new one: `qoyvor` under `morphology: true`);
bot 42/42.
