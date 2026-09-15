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

## Running

Nothing.

## Next

1. `bench/review.md` (~500 draft items, parked), `bench/README.md` (draft card),
   `bench/run_eval.py`. Publish nothing.
2. `docs/FOR-MAQSUDJON.md`; final test run into `docs/TEST-OUTPUT.txt`.

Deploy recipe (repeatable): `python3 tools/build_site.py && tools/deploy_pages.sh`.
