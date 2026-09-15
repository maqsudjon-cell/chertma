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

- Checkpoint 1: SPEC (commit 9027215).
- Checkpoint 2: corpus pipeline, lexicons, report (commit 8b66e0f).
- `gh` is authenticated as `maqsudjon-cell` (checked 2026-09-15).

## Running

Nothing.

## Next

1. Test fixtures from `data/raw` (golden, invariant-generated 10k, perf
   prefixes, books lat/cyr pairs, foreign-collision list, bench source pool).
2. `tests/` — all suites, failing.
3. `engine/` until tests pass.
4. Delete `data/raw`.
5. `bench/review.md` draft, `bench/README.md`, `bench/run_eval.py`.
6. `web/` demo + PWA.
7. Deploy, README, `docs/FOR-MAQSUDJON.md`.
