# Open questions

Every linguistic or design question that could not be settled from `CLAUDE.md`
alone. When a question is answered, `docs/SPEC.md` is amended and the entry is
marked closed with the ruling. Nothing is decided silently in code.

Status: `OPEN` = needs the human · `CLOSED` = ruled (date).

---

## Defaults taken unattended (2026-09-15)

The human was away; standing rule: take the conservative default ("return the
input unchanged"), log it here, keep going. Each entry names the question, the
default, and where it lives so it can be reversed in one pass.

| # | Question | Default taken | Where |
|---|---|---|---|
| D1 | Q19 — valid bare words vs. context | Keep the provisional rule: a token whose reading is a word is never rewritten. Acceptance criterion 1 therefore fails (`pisib` kept) and is reported as TODO. | `engine/index.js` `_valid`; `tests/acceptance.test.js` |
| D2 | Q28 — corrections that remove a typed mark | `autocorrect()` drops every candidate with a −1 evidence position (a removed ʻ, ş→s, Cyrillic с→ş, a removed tutuq). `suggest()` still offers them. | `engine/index.js` (`ev.min >= 0`) |
| D3 | Q21 — foreign words and names | A Title- or UPPER-case token that is not first in its sentence is only corrected to a word the corpus capitalises ≥ 90 % of the time. An upper-case token of ≤ 4 letters outside an all-caps sentence is never corrected (acronyms: BMT, NATO, ХАМАС). All-caps sentences are treated like lower case. | `engine/index.js`, `ACRONYM_MAX_LETTERS` |
| D4 | Q24 — one-letter tokens | Never corrected. | `engine/index.js` |
| D5 | Q29 — Russian-layout spellings in books | Not applied; the lexicon is unchanged, so `тугри` stays `tugri`. Applying it would add corrections, which is the less conservative direction. | `tools/pack_lexicon.py` (what-if only) |
| D6 | Q2b — `ъ` after a vowel, `ўъ` | The Q2 ruling stays as ruled. Round-trip failures it causes (53 lite, 373 full words with ʼ before e/ye/yo/yu/ya) are counted, not failed. | `engine/translit.js`; `tests/translit.test.js` |
| D7 | Q20 — rule 3 restored to "any marks removed" | Kept as restored at checkpoint 2. | `tools/pack_lexicon.py` |
| D8 | Q22 — contamination filter on 2+ character tokens | Kept. | `tools/normalize_corpus.py` |
| D9 | Q23b — what the "~10 000 generated" invariant forms are | No written spec was found in the repo. Taken as: 10 000 surface forms sampled (seed 20260915) from the telegram_blogs forms that are not valid tokens and share no skeleton with a lite word — the brief's "informal strings absent from the lexicon". | `tools/build_fixtures.py`; `tests/fixtures/invariant-generated.txt` |
| D10 | Q26 — serving the lexicon | The site serves `lexicon-lite.bin.gz` and inflates it with the browser's `DecompressionStream`; no dependency. | `web/app.js` |
| D11 | Ranking constants | Grid search over λ ∈ {0 … 3}, ν ∈ {0 … 2}, informal mix ∈ {0, 0.25, 0.5}: every setting keeps 312/312 strict cases; λ > 0 with mix 0.5 gives the fewest wrong corrections (18 vs 20). The brief's starting values λ 2.0, ν 0.5, mix 0.5 are in the best group and are kept. Ranked-case floor set to 0.65 from the measured 98/150. | `engine/constants.js`; `tools/tune.mjs`; `tests/thresholds.js` |
| D12 | Books lat/cyr agreement floor | 0.998, from the measured 0.9983 over 29.9 M aligned tokens. | `tests/thresholds.js` |
| D13 | `suggest()` and a typed valid word | A buffer that is itself a word is always among the suggestions (it replaces the last slot if it was not in the top N). | `engine/index.js` |
| D14 | Q23a placeholder | `tests/fixtures/dialect-handwritten.json` is empty; the invariant suite reports INCOMPLETE until the 200 forms land. | `tests/invariant.test.js` |
| D15 | Foreign-collision list definition | "Foreign tokens whose skeleton collides with a real Uzbek word": crawl forms with ≥ 30 occurrences, ≥ 80 % title case, no tutuq, not a lite word, whose key matches a lite word that is not itself capitalised. 77 rows. Parked; nothing uses it. | `tools/build_fixtures.py`; `data/foreign-collisions.tsv` |
| D16 | Benchmark link on the site | The page does not link to a Hugging Face dataset (nothing is published and the namespace, Q15, is not decided). It links to the draft in the GitHub repo instead. | `web/index.html` |
| D17 | Site language | Uzbek (new Latin) by default for every visitor; English one tap away. | `web/app.js` |
| D18 | Code licence | None chosen; the brief does not name one. `package.json` has no licence field and the README says so. | `README.md`, `package.json` |
| D19 | Suggestions while typing Cyrillic | Rendered in Cyrillic; Latin input gets the chosen output script. | `web/app.js` |

## Morphology and word list — defaults taken (2026-09-15)

| # | Question | Default taken | Where |
|---|---|---|---|
| M1 | Ship the morphological fallback on? | **RULED 2026-09-16: stage 1 on, stage 2 off** (`morphology: 'read'`). Stage 1 changes 809 invariant forms, all pure old → new spelling conversions through a known stem, no letter corrected. Stage 2 corrects 13 and gets 12 wrong, including `qoyvor` — rejected, not to be revisited without much stronger evidence. Consequence: `shoshima → şoşima` in new-Latin output (G310). | `engine/constants.js`, SPEC §5.2 |
| M15 | Which lite ships? | **RULED 2026-09-16: the frequency-selected list stays.** The coverage-selected build is +3 points of held-out coverage but breaks 6 golden cases and admits `xozir`, `kuyidan` as words; kept as `data/lexicon-lite-coverage.bin`, unused. | `data/`, docs/MORPHOLOGY-REVIEW.md |
| M2 | Shortest stem | 3 letters. | `MORPH_MIN_STEM_LETTERS` |
| M3 | Shortest suffix chain | 2 letters — one-letter endings (`-i`, `-m`) fit too many unrelated words. | `MORPH_MIN_SUFFIX_LETTERS` |
| M4 | Splits that disagree | Stage 2 corrects only if every split with a candidate gives the same word; otherwise the token is left. A literally valid split anywhere blocks stage 2. | `engine/index.js` `_morph` |
| M5 | Suffix inventory | A chain is kept if it follows ≥ 100 different stems that are themselves words seen ≥ 1 000 times, in words seen ≥ 10 times; 2–12 letters. 2 235 chains; noisy fragments remain (`ullo`, `ub`). | `tools/suffixes.py` |
| M6 | Stage 2 on capitalised tokens | Never — the first measurement's wrong corrections were mostly names (`Камазлар`, `Сухов`, `Island`). | `_morph` |
| M7 | Stage 2 on Cyrillic input | Never — Russian-layout recovery inside a stem produced `кураб → қораб`, `куюнар → қуюнар`. | `_morph` |
| M8 | Latin letters outside the alphabet in Cyrillic output | `c` → `ц` before e/i/y, else `к`; `w` → `в`; accented letters by base letter. | `engine/translit.js` |
| M9 | Cyrillic letters outside the alphabet | `щ → ş`, `ы → i` and a table for Kazakh/Tajik/Serbian letters; words containing them are transliterated, never corrected. | `engine/translit.js` |
| M10 | Mixed case / mixed script tokens | Converted run by run so capitals stay (`TOGGнинг` → `TOGGning`, `iPhone` → `иПҳоне`). URLs, emails, mentions, hashtags stay as typed — the only mixed-script output left. | `ruleToken` |
| M11 | Latin input, new-Latin output, unknown word | As typed (`o‘quvching` stays) — Latin is ambiguous between old and new, and converting unknown words is what stage 1 would do. | §6.5 |
| M12 | Golden cases G177, G207 | Expected outputs changed to the new rule (`15ta`, `TOGGning`); the sentence round-trip test skips glued, mixed-case and non-Uzbek-alphabet tokens (counted). | `tests/` |
| M13 | Held-out text | sha1(document) % 10 == 0 in telegram_blogs and news shard 2: 5.05 M tokens, subtracted from the counts before admission and selection. Bigram counts still include those documents (unigram coverage is unaffected). | `tools/build_heldout.py` |
| M14 | "Coverage of the crawl slice" for lite | Rank by news + telegram token count after merging misspellings into their words; ties by total count. News is 92 % of those tokens. | `tools/build_lexicons.py` |

## Telegram bot — defaults taken unattended (2026-09-15)

| # | Question | Default taken | Where |
|---|---|---|---|
| B1 | How replies reach Telegram | In the webhook response body (Telegram executes the method), so a normal update makes no outbound call. The Bot API is called only when a reply must be split into several messages. | `bot/api/telegram.js` |
| B2 | Is a POST really from Telegram? | A random webhook secret (`CHERTMA_WEBHOOK_SECRET`, gitignored `.env` and Vercel env) is registered with `setWebhook`; requests without it get 401. | `bot/api/telegram.js`, `bot/scripts/webhook.mjs` |
| B3 | Script of the bot's own messages | Old Latin with ʻ — readable by everyone today. Engine output is shown in all three scripts. | `bot/src/texts.js` |
| B4 | The brief's inline example | The engine's output is shown as it is: `sosib pisib togri` gives `şoşib pisib töğri` (Q19), and old Latin uses ʻ, not ASCII '. The engine is frozen. | — |
| B5 | Inline rate limit | The brief's 20/min is for messages. Inline queries fire as you type, so they get their own 60/min per user; both drop silently. | `bot/src/core.js` |
| B6 | Forwarded messages with text | Friendly reply, not converted — the brief lists "forwarded" with non-text. | `bot/src/core.js` |
| B7 | Groups | Answered only on `@Chertmabot` mentions, `/cmd@Chertmabot`, or replies to the bot's messages. A bare mention that replies to someone's message converts that message. Bare `/start` without the username, messages from other bots, messages sent via the bot, edits and channel posts are ignored. Non-text only gets a reply when it replies to the bot. The rate limit counts only messages addressed to the bot. | `bot/src/core.js` |
| B8 | "Already correct" | Claimed only when the output equals the input and the input is written in that script; unknown words in another script get "oʻzgarmadi — tanilmagan soʻzlar yozilganidek qoldi". | `bot/src/core.js` `status()` |
| B9 | Text with no letters | A short reply instead of three copies of the input. | `bot/src/core.js` |
| B10 | Replies over 4096 characters | Split into one message per script, each cut to fit with "… (qolgani kesildi)". Input over 4096 is cut to 4000 first, as specified. | `bot/src/core.js` |
| B11 | Inline caching | `cache_time` 300 s, `is_personal` false — results depend only on the query. | `bot/src/core.js` |
| B12 | Region and limits | `fra1` (next to Telegram's European data centre), `maxDuration` 10 s. | `bot/vercel.json` |
| B13 | Getting the engine into a Vercel project rooted at `bot/` | `scripts/vendor.mjs` copies `engine/*.js` and the lite lexicon into `bot/_vendor/` (gitignored) before deploy; a test requires the copy to be byte-identical and `engine/` to have no changes. | `bot/scripts/vendor.mjs`, `bot/test/vendor.test.js` |
| B14 | Bot profile (commands, description) | Not changed through the API; listed as BotFather steps for the human. | `docs/FOR-MAQSUDJON.md` |
| B15 | Health endpoint | `GET /api/telegram` returns cold/warm, engine init time, lexicon size and update counts by kind — no content, no token. | `bot/api/telegram.js` |
| B16 | Webhook registration | `allowed_updates` = message, inline_query; `drop_pending_updates` true; `max_connections` 40. | `bot/scripts/webhook.mjs` |

Engine issues found while building the bot: none. The bot switches `engine.options.script` between calls, as the web demo does.

## Hugging Face packages — defaults taken unattended (2026-09-15)

| # | Question | Default taken | Where |
|---|---|---|---|
| H1 | Bigram cutoff | Count ≥ 3 would be 990,561,851 bytes (≥ 4: 721,519,271; ≥ 5: 563,061,817). The smallest cutoff under ~500 MB is **≥ 6** (463,187,708 bytes, 23,160,605 rows); stated in the card. | `tools/build_hf_lexicon.py` |
| H2 | Which words go in the lexicon | Exactly the engine's admission set (4,892,125 words, SPEC §9.6) with merged counts — not the raw counted forms, which include misspellings such as `togri`. Columns exactly `word, count, skeleton`; the per-source split is not included. | same |
| H3 | The card's worked example | The requested row "`sosib` → şoşib, sosib" is not what the data holds: `sosib` was merged into `şoşib` (16 book occurrences, under 1 %). The card shows the real row `SOSib → şoşib, söşib, sösib, şöşib` and says why `sosib` is absent. | `hf/uz-lexicon-skeleton/README.md` |
| H4 | `tugri` count | 57,301 was the books-only figure; the dataset count is 57,367 (all sources). The card gives both. | same |
| H5 | skeleton-index layout | Rows sorted by skeleton (code-point order, as in the engine); header `skeleton	candidates`; ragged rows, so not declared as a Hub viewer config — the card shows how to read it. | same |
| H6 | Generated data in git | The TSVs (≈ 700 MB) and the Space copy are gitignored — too large or duplicated; `tools/build_hf_lexicon.py` and `tools/build_hf_space.py` rebuild them. Cards and scripts are tracked. | `.gitignore` |
| H7 | "NOT READY" line on the benchmark card | Placed as the literal first line, above the YAML block: the Hub will not read the card's metadata until it is deleted — a deliberate guard. | `hf/uz-alphabet-bench/README.md` |
| H8 | Benchmark authors and contact | PLACEHOLDER, because of the possible co-publication with Tahrirchi. | same |
| H9 | Space links | Footer links in the Space copy open in a new tab (the Space runs inside an iframe on huggingface.co); `web/` is unchanged. | `tools/build_hf_space.py` |
| H10 | Space colours | `yellow` → `gray` — the Hub palette has no orange. | `hf/space/README.md` |
| H11 | Hub namespace | Undecided (Q15), so links use `HF_USERNAME`; `hf/UPLOAD-STEPS.md` has the one command that replaces it. | all cards |
| H12 | Uzbek in cards | Old Latin with ʻ (U+02BB), per the instruction. Data itself is new Latin. | all cards |
| H13 | Evaluator testing | `--self-test` runs 6 synthetic items (not benchmark items) through the engine backend and a local fake OpenAI-style endpoint, and checks the leaderboard writer. The `hf` backend is not exercised (needs torch and a model). | `hf/uz-alphabet-bench/run_eval.py` |

### Q32 — Stray apostrophes admitted as words · OPEN (found preparing the dataset)

A misplaced apostrophe turns a common word into a "marked" form (`vʼa`, `bilaʼn`,
`töʼğri`), and SPEC §9.6 rule 1 admits marked forms from any source with count ≥ 2.
84,547 lexicon words contain `ʼ`; 62,982 of them occur fewer than 10 times. They crowd the
skeleton index (161,414 skeletons with 2+ words, 42,204 with 2+ words of count ≥ 10) and,
in the full build, make `v'a` a valid token that is never corrected to `va`.
**Option:** treat a form whose only difference from a far more frequent word is added
or moved `ʼ` like a stripped variant (ratio test, merge).
**Needs:** ruling. Documented as a limitation in the dataset card.

## Open

### Q19 — "Valid tokens are never rewritten" vs. context-resolved ambiguity · OPEN

The Q4 ruling says a token already valid in canonical form is never rewritten
(SPEC §5.1). Read literally, it also covers every ambiguity pair whose bare
spelling is a word: `autocorrect()` keeps `sok`, `oz`, `qol`, `toy`, `bos`,
`is` even when the sentence clearly means `şok`, `öz`, `qöl`, `töy`, `boş`,
`iş`. Context (§8.3) then only affects `suggest()` ordering and tokens with no
valid reading. The same applies to Cyrillic `кул` (ash) vs `қўл` (hand) typed
on a Russian layout.

The margin rule approved under Q11 would have allowed a context-backed
replacement; the Q4 ruling supersedes it.

**Provisional:** the literal reading — never rewrite. It is the conservative
choice and matches the product's positioning.
**Measured (checkpoint 2).** The rule makes **acceptance criterion 1 fail**:
`sosib pisib togri kelasizmi` gives `şoşib pisib töğri kelasizmi`. `pisib` is
a real word — "sneaking up", 3 394 times in books; in the crawl: *makakaga
pisib yaqinlashib*, *panadan писиб тош отасиз* — so it is a valid token and is
kept. The bigram table knows better: `şoşib pişib` 3 004, `şoşib pisib` never
seen. Other costs: `docs/CHECKPOINT-2.md`, "Cost of valid tokens are never
rewritten".

**Options:** (a) keep the rule and change criterion 1; (b) allow a valid bare
token to be replaced only when the bigram with the previous word favours the
marked sibling by a wide margin (a context-only exception); (c) drop the rule
for ambiguity pairs only.
**Needs:** ruling. Blocks step 4 (engine), not step 2.

### Q20 — Partially marked forms · OPEN (confirm)

SPEC v0.2 (my rewrite) defined a stripped variant as a form with *all* marks
removed and applied the ratio test only to unmarked forms. The Q17 proposal as
approved said *any* of the marks. The narrowing let book-attested half-marked
errors in: `boyiça` (0.19 % of `böyiça`), `taminlaş` (0.83 % of `taʼminlaş`).

**Done:** rule 3 is restored to "any subset of marks removed, for any form"
(SPEC §9.6). Before/after numbers: `docs/CHECKPOINT-2.md`. What remains —
crawl-only half-marked forms that no book attests — is 116 forms, none in the
lite build.
**Needs:** confirm the restoration.

### Q21 — Foreign Latin words that share a key with an Uzbek word · OPEN

`Sunday` has the key `Sunday`, which is also `şunday`'s. Unless books attest
`sunday`, it is not a valid token, so `autocorrect()` would turn it into `Şunday`.
The invariant allows this — the skeletons match — but it is wrong. The risk
list in `docs/CHECKPOINT-2.md` shows how often this happens in the crawl.

More from the checkpoint-2 risk list: `Токаев` → `töqayev`, `Elon` →
`eʼlon`, `ХАМАС` → `hamas`, `Маскнинг` → `maşqning`.

**Provisional:** accepted for now; no mechanism.
**Options:** (a) a passthrough list of frequent crawl forms that books never
contain and whose would-be correction is rare; (b) never correct a Latin
token inside a run of tokens that are all unknown.
**Needs:** ruling. Blocks step 4.

### Q22 — Contamination filter counts only tokens of 2+ characters · OPEN

The brief drops a document when more than 5 % of its tokens fall outside the
Uzbek charset. Counted literally, 29 of the first 400 books were dropped, and
nearly all were Uzbek maths, physics, chemistry and IT textbooks whose
"outside" tokens were formula variables (`C`, `W`, `c`, `α`). Counting only
tokens of two or more characters (and treating sub/superscript digits as
digits, not letters) drops 5 of 400, all English-heavy IT books.

**Provisional:** the 2+ character rule is what the counts use.
**Needs:** yes/no.

### Q23 — `telegram_blogs` is not informal text · OPEN

The card says "manually curated texts from 128 high-quality Telegram
channels". Measured: most posts are Cyrillic news and commentary in standard
orthography; documents typed without ö/ğ marks or on a Russian layout are a
small fraction (`docs/CHECKPOINT-2.md`, "How the crawl was typed"). The
brief's invariant test and the separate informal frequency table both assume
dialect and slang that this split barely contains.

**Provisional:** use it, label it honestly as channel posts, and keep the
invariant test as specified. The test still guards byte identity; it just
covers less dialect than intended.
**Needs:** acknowledge, or name an openly licensed informal Uzbek corpus to
add (no crawling).

### Q24 — One-letter tokens · OPEN

`Ў` on its own (an interjection, or a list marker) has key `O` and would
become `o`. Proposal: a token of one letter is never corrected.
**Needs:** yes/no.

### Q25 — Build tooling deviations · OPEN (for the record)

- `datasets.load_dataset()` is not used: a full load of `uz-books-v2` needs
  ~50 GB of disk and this machine had ~22 GB free. `tools/fetch_corpus.py`
  downloads the same parquet files one at a time at a pinned revision,
  verifies their sha256, and `build_ngrams.py` deletes each book shard once
  counted.
- Build-time Python dependencies: `pyarrow` (parquet) and `numpy` (bigram
  counting), in `tools/.venv`, pinned in `tools/requirements.txt`. `engine/`
  stays at zero dependencies.
- Downloads use the system `curl`; the python.org Python on this machine has
  no CA bundle and fixing that would change the system installation.

**Needs:** yes/no on the two build-time dependencies.

### Q26 — Served size of the lexicon · CLOSED 2026-09-15 (verified at deploy)

The §6 budgets are gzipped sizes. GitHub Pages likely serves `.bin` as
`application/octet-stream` without compression, so browsers would download
the raw size. Option for step 6: publish `lexicon-lite.bin.gz` and inflate it
with the browser's built-in `DecompressionStream` — no dependency. Done (D10).
Live check: `data/lexicon-lite.bin.gz` is served as `application/gzip`,
739 813 bytes, not re-compressed; the page inflates it.

### Q2b — Cyrillic `ъ` after a vowel, and `ўъ` · OPEN (reopens Q2)

The Q2 ruling drops `ъ` before `е ё ю я`. The Latin books disagree for native
and Arabic-origin words, where `ъ` follows a vowel:

| Cyrillic | Q2 rule gives | Books (Latin) |
|---|---|---|
| меъёр | meyor (856) | **meʼyor** (28 770) |
| маъюс | mayus (661) | **maʼyus** (18 634) |

and they write no tutuq after `ў`:

| Cyrillic | §6.1 gives | Books (Latin) |
|---|---|---|
| мўъжиза | möʼjiza (124) | **möjiza** (18 965) |
| мўъмин | möʼmin (28) | **mömin** (31 680) |
| мўътадил | möʼtadil (667) | **mötadil** (26 183) |

**Proposal:** `ъ` before `е ё ю я` is dropped only after a consonant
(`объект → obyekt`, `съезд → syezd`), and becomes `ʼ` after a vowel
(`меъёр → meʼyor`); `ъ` directly after `ў` is dropped (`мўъжиза → möjiza`).
Whether the 2026 orthography writes `möjiza` or `möʼjiza` is for you to say.
**Needs:** ruling. Changing it means re-counting the Cyrillic crawl (about 40
minutes); the books are Latin and are not affected.

### Q28 — Never remove a mark the writer typed · OPEN

The invariant allows a correction that *removes* information: `ўлимлар`
(deaths) → `olimlar` (scholars), `Ўлмадим` → `olmadim`, `шимдан` (from the
trousers) → `simdan` (from the wire), `Саҳарлик` → `şaharlik`, `ўтасиз` →
`otasiz`. Each happens because the correct inflected form is not in the lite
lexicon and the only word with the same key lacks the mark. The evidence term
(§8.2) scores these −1 but cannot stop the only candidate.

**Proposal:** `autocorrect()` never applies a candidate with any −1 evidence
position; `suggest()` may still offer it. Measured on the risk list: vetoes
1 952 of 7 756 forms (`docs/CHECKPOINT-2.md`). Also vetoed: `мўъжиза → möjiza`,
which depends on Q2b.
**Needs:** ruling. Blocks step 4.

### Q29 — Books contain Russian-layout spellings · OPEN

Books are the authority on what is a word (Q17), but some of them were typed
on a Russian layout: `tugri` 57 301 times (3.9 % of `töğri`), `bulgan` 10 734,
`uzbekiston` 5 665, `kanday`, `xalkaro`. These are valid tokens in the lite
build, so §5.1 keeps them and Cyrillic keyboard recovery (Q6) never fires for
the commonest words — including SPEC §4.8's own example `тугри → töğri`. Rule 3 only
looks at marks, not `u/ö`, `k/q`, `x/h`.

**Option:** extend rule 3 to those substitutions. `docs/CHECKPOINT-2.md` shows
the effect at 1 %, 5 % and 10 % and the words closest to each threshold, which
is where real words (`uz`, `kul`, `tur`) would be wrongly rejected. `tugri`
needs 5 % or more.
**Needs:** ruling, and a ratio. Blocks step 4.

### Q30 — Vowel before и in Cyrillic · OPEN (found unattended)

The uz-books-v2 lat/cyr check (99.83 % agreement) shows a pattern besides
Q2b: Cyrillic `нуқтаи`, `манбаи`, `саин`, `моил` against Latin `nuqtayi`,
`manbayi`, `sayin`, `moyil` — the Latin inserts `y` between a vowel and `и`.
Our rule gives `nuqtai`. Nothing changed; counts are printed by
`tests/translit.test.js`.
**Needs:** ruling.

### Q31 — Is `qoyvor` a passthrough form? · OPEN (found unattended)

The brief lists `qoyvor` among forms that pass through untouched. The full
lexicon contains `qöyvor` (old `qoʻyvor`, "let go"), so in the full build
`qoyvor` is corrected to `qöyvor`; the lite build leaves it. If `qoyvor` is the
ASCII spelling of `qoʻyvor`, the correction is right and the brief's list is
wrong; if it is a separate dialect form, it needs the protected list.
**Default taken:** left out of the benchmark's `preserve` drafts and out of the
acceptance tests (criterion 2 does not name it). **Needs:** ruling.

### Q13b — The 24 proposed minimal pairs · OPEN

In `docs/AMBIGUITY-REVIEW.md`. Nothing enters `tests/` or `bench/` until each
row is marked keep / fix / drop.

### Q15 — Hugging Face namespace · OPEN

`huggingface.co/datasets/<HF_USERNAME>/uz-alphabet-bench`. Not needed until
step 5. Not guessed.

---

## Closed

### Q1 — Cyrillic `ц` after a consonant · CLOSED 2026-09-14

`s` word-initially and after consonants, `ts` after vowels. The exception list
starts empty and is filled only from reviewed diffs against `uz-books-v2`.

### Q2 — `ъ` and `ь` before iotated vowels · CLOSED 2026-09-14

`ъ` before `е ё ю я` is dropped (`объект → obyekt`); `ь` before `о` becomes
`y` (`бульон → bulyon`).

### Q3 — `ng` · CLOSED 2026-09-14

The brief's rule is dropped entirely. `ng` is never one unit; `n`+`ğ` is
allowed wherever a real word has it. The lexicon resolves `yongʻoq` vs
`yongoq` because only one is a word. No special-casing.

### Q4 — Literal `s+h` · CLOSED 2026-09-14

The collision is accepted. Add a proper-noun protection list (`Ishoq`,
`Ishoqov`, …) and the general rule that a token already valid in canonical
form is never rewritten. Don't over-engineer. → SPEC §5.1; see Q19 for a
consequence.

### Q5 — Non-Uzbek characters in conversion · CLOSED 2026-09-14

`щ ы` left unconverted; Latin tokens with `c`/`w` stay Latin in Cyrillic
output unless in the lexicon.

### Q6 — Russian keyboards · CLOSED 2026-09-14

In, script-conditional, not a global flag. `skeleton()` takes the detected
input script. For Cyrillic input the classes widen: `у ∈ {u, O}`,
`к ∈ {k, q}`, `г ∈ {g, G}`, `х ∈ {x, h}`. Latin input keeps the narrow classes
and `fuzzyQK`/`fuzzyXH` stay off. Rationale: a Cyrillic text with no `ў қ ғ ҳ`
is itself evidence of a Russian layout; that evidence does not exist in Latin.
Option `cyrillicKeyboardRecovery`, default `true`. → SPEC §4.8.

### Q7 — Confusable characters · CLOSED 2026-09-14

Yes as written.

### Q8 — Protected spans · CLOSED 2026-09-14

Yes as written.

### Q9 — Case is never changed · CLOSED 2026-09-14

Yes as written.

### Q10 — `load(url)` vs the no-network grep · CLOSED 2026-09-14

Yes: bytes, or a URL plus a host-supplied `loader`.

### Q11 — Autocorrect margin · CLOSED 2026-09-14, superseded

Approved, then superseded by the Q4 ruling (valid tokens are never rewritten).
`AUTOCORRECT_MARGIN` is removed.

### Q12 — Evidence instead of distance · CLOSED 2026-09-14

Replace edit distance with an evidence term over the skeleton alignment: +1
where the input used the digraph or diacritic form matching the candidate, 0
where the input was ambiguous, −1 where it contradicts the candidate.
→ SPEC §8.2, `engine/constants.js` (`NU_EVIDENCE`).

### Q13 — The brief's ambiguity list · CLOSED 2026-09-14

`şeʼr`, not `şer`: `ser` keeps three candidates (`ser` / `şer` / `şeʼr`).
Cave is `ğor`: that pair is dropped. `kop`, `boli`, `böli` are dropped. The
fixture is rebuilt from the 24 proposed pairs (see Q13b).

### Q14 — No morphology in v1 · CLOSED 2026-09-14

Acknowledged; decide after the coverage number at checkpoint 2.

### Q16 — Dataset licences · CLOSED 2026-09-14

Checked from each dataset card at a pinned revision; recorded in
`data/SOURCES.md`.

### Q17 — Misspellings in the lexicon · CLOSED 2026-09-14

Approved and made explicit. `uz-books-v2` is the authority on what is a word;
`uz-crawl` is used only for frequency weighting and the informal/dialect
passthrough set. A crawl token with no `ö ğ ş ç ʼ` may enter only if books also
has it; tokens carrying a mark may enter from either. → SPEC §9.6.

### Q18 — One-letter whitelist · CLOSED 2026-09-14

`u o e a`.
