# Status

Resume point for any session. Update after every discrete piece of work.

**Mode:** unattended run of steps 3–7, started 2026-09-15. Standing rules from
the human (2026-09-15 message):

- Judgement call → conservative default ("return the input unchanged"), log it
  in `docs/OPEN-QUESTIONS.md` under "Defaults taken unattended", keep going.
- Parked, never used: the 24 minimal pairs; the ~200 hand-written dialect forms
  (Q23a, human writes them); the protected-word risk list (write file, use
  nothing); the ~500 benchmark items (draft to `bench/review.md`, publish
  nothing to Hugging Face).
- Keep `data/raw` until the engine passes its tests, then delete it and say so.
- 4 workers max. Commit after every piece; never leave the tree dirty.
- Deploy: public GitHub repo, push, Pages from a branch, `web/CNAME`. Verify
  with `curl -sI https://chertma.maqsudjon.com | head -1`, report the exact
  failing step, no retry loops. If `gh` is not authenticated, stop that step.
- Finish with `docs/FOR-MAQSUDJON.md`.

## Done

- Checkpoint 1: SPEC (commit 9027215). Checkpoint 2: corpus pipeline (8b66e0f).
- Step 3 tests: `tests/*.test.js`, fixtures in `tests/golden.json`, `tests/fixtures/`.
  Built by `tools/build_fixtures.py` + `tools/build_books_pairs.py` (both need
  corpus data that is now deleted; the fixtures are committed).
- Step 4 engine: `engine/*.js`. `npm test` → 45 tests, 40 pass, 5 TODO, 0 fail.
  Defaults D1–D15 logged in `docs/OPEN-QUESTIONS.md`.
- Constants tuned (`tools/tune.mjs`): brief's starting values kept.
- `data/raw` deleted after the engine passed (3.9 GB freed). `data/uz-bigrams.tsv`
  (1.6 GB, gitignored) is still on disk — needed only to re-pack.
- `gh` authenticated as `maqsudjon-cell`.

- Step 6 web: `web/` (commit 31d0cc9). Verified in the browser: live typing,
  suggestions, convert, offline with the local server stopped, phone layout.
  Build with `python3 tools/build_site.py` → `_site/` (gitignored).

- Step 7 deploy (2026-09-15): repo https://github.com/maqsudjon-cell/chertma
  (public), `main` pushed, `gh-pages` published by `tools/deploy_pages.sh`,
  Pages built, certificate approved, HTTPS enforced.
  `curl -sI https://chertma.maqsudjon.com | head -1` → `HTTP/2 200`.
  Live page checked in the browser: engine runs, service worker active.
- README.md written (real before/after at the top).

- Step 5 bench (parked): `bench/review.md` — 440 draft items (ascii2new 100,
  old2new 80, cyr2new 80, preserve 100, apostrophe 40, edge 40, ambiguity 0
  because the pairs are parked). `bench/README.md` draft card (EN + UZ),
  `bench/run_eval.py` (chertma / hf / api backends; checked on a 3-item synthetic
  file only), `tools/build_benchmark.py --export` writes jsonl from rows marked
  keep. Nothing published anywhere.

- `docs/FOR-MAQSUDJON.md` written: live check, acceptance criteria with numbers,
  defaults D1–D19, failures, the four parked items, rulings needed.
- `docs/TEST-OUTPUT.txt`: final `npm test` (45 tests, 40 pass, 0 fail, 5 TODO).

- Telegram bot (2026-09-15): `bot/` — Vercel webhook function, 42 tests pass,
  engine vendored byte-for-byte. Token only in gitignored `.env` (verified) and, after
  deploy, in the Vercel env. `.git/hooks/pre-commit` blocks commits containing the token
  prefix. DEPLOYED 2026-09-15: https://chertma-bot.vercel.app/api/telegram, webhook set,
  getWebhookInfo clean, real message delivered, inline enabled and answering. Redeploy:
  `cd bot && node scripts/vendor.mjs && vercel deploy --prod --yes`.

- Hugging Face packages prepared (2026-09-15), nothing uploaded: `hf/uz-lexicon-skeleton/`
  (card tracked; TSVs gitignored, rebuild `tools/.venv/bin/python tools/build_hf_lexicon.py`),
  `hf/uz-alphabet-bench/` (card with PLACEHOLDERs + NOT READY line, `run_eval.py --self-test`
  passes; no jsonl), `hf/space/` (README tracked; files gitignored, rebuild
  `python3 tools/build_site.py && python3 tools/build_hf_space.py`), `hf/UPLOAD-STEPS.md`.
  Defaults H1–H13 and Q32 in `docs/OPEN-QUESTIONS.md`.

## Running

Nothing.

## Next (waits for the human)

- Hugging Face: follow `hf/UPLOAD-STEPS.md` (lexicon, then Space; benchmark after review).

- Bot: BotFather `/setcommands`, `/setdescription` (suggested texts in `docs/FOR-MAQSUDJON.md`).
- Engine rulings: Q19, Q29, Q28, Q21, Q2b, Q30, Q31; yes/no Q20, Q22–Q25; Q15 (Hugging
  Face namespace); code licence (D18).
- Human work: mark the 24 pairs (`docs/AMBIGUITY-REVIEW.md`), write the ~200 dialect forms
  (`tests/fixtures/dialect-handwritten.json`), review `bench/review.md`.
- Site: after any engine or web change, `npm test`, then
  `python3 tools/build_site.py && tools/deploy_pages.sh`.
