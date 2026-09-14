# Chertma — Build Brief

**Domain:** `chertma.maqsudjon.com`
**Owner:** Maqsudjon Polatov
**Read this entire file before writing a single line of code.**
**Stop at every `⏸ CHECKPOINT` and wait for the human.**

---

## 0. What you are building

Uzbekistan is replacing four letters in its Latin alphabet:

| Old Latin | New Latin |
|---|---|
| `Sh sh` | `Ş ş` |
| `Ch ch` | `Ç ç` |
| `Oʻ oʻ` | `Ö ö` |
| `Gʻ gʻ` | `Ğ ğ` |

The law passed in September 2026. Textbooks convert between 2027 and 2031. For
roughly five years Uzbeks will write in **three scripts at once**: Cyrillic, old
Latin, and new Latin. No phone keyboard has `ş ç ö ğ`. Nobody wants to hunt for
apostrophes.

Chertma solves exactly one problem:

> **Type plain ASCII on an ordinary QWERTY keyboard. Get correct Uzbek out, in
> whichever script you choose.**

```
input:   sosib pisib yozsam togri kelasizmi
output:  şoşib pişib yozsam töğri kelasizmi
```

There are **two deliverables**, not one:

1. **The engine + web demo** at `chertma.maqsudjon.com`.
2. **`uz-alphabet-bench`** — an open evaluation dataset published to Hugging
   Face. Nobody has built one yet because the alphabet only just changed. It
   falls out of the same test fixtures the engine needs anyway, so it costs
   almost nothing extra and it is the part of this project the wider world will
   actually cite.

The **engine** is the core asset. It must later drop into an Android keyboard
(HeliBoard fork) and an iOS keyboard extension (hard ~60 MB memory ceiling).
Therefore: zero dependencies, zero DOM access, zero network calls, zero
framework, plain ES modules.

Prior art to read before starting: Turkish **deasciifier** and **Zemberek** solve
a structurally identical problem (`ş/s`, `ç/c`, `ğ/g`, `ö/o`, `ı/i`, `ü/u`). Do
not invent a novel approach where theirs works.

---

## 1. The hard invariant

This is the single most important rule in the project. It is the product's
entire positioning. Encode it as a test, not as a convention.

> **A correction is permitted if and only if `skeleton(input) === skeleton(candidate)`.
> If the skeletons differ by even one character, return the input UNCHANGED.**

`skeleton()` maps a token into equivalence classes, discarding every distinction
a keyboard could plausibly have destroyed:

| Class | Collapses |
|---|---|
| `S` | `ş` `Ş` `sh` `SH` `Sh` `s` `S` `w` `W` `ш` `Ш` `с` `С` |
| `C` | `ç` `Ç` `ch` `CH` `Ch` `c` `C` `ч` `Ч` |
| `O` | `ö` `Ö` `oʻ` `o'` `o‘` `o’` `` o` `` `ó` `ő` `o` `O` `ў` `Ў` `о` `О` |
| `G` | `ğ` `Ğ` `gʻ` `g'` `g‘` `g’` `` g` `` `ǵ` `gh` `g` `G` `ғ` `Ғ` `г` `Г` |
| `∅` | `ʼ` `ʻ` `'` `’` `‘` `` ` `` `´` `ъ` `ь` — dropped entirely |

Everything else maps to its own lowercase self. Cyrillic folds into the same
classes so that a Cyrillic word and its Latin transliteration share one skeleton.

### What this buys you

These pass through **untouched**, because no lexicon entry shares their skeleton:

```
kelaslar      (dialect: -sizlar → -slar)
qisela        (spoken contraction of qilsanglar)
balu          (dialect for baliq)
kettik   bormimiz   shoshima   qoyvor
```

These **are** corrected, because the skeleton matches a real word:

```
togri     → töğri      (missing apostrophes)
wunaqa    → şunaqa     (internet w-for-sh)
sosib     → şoşib      (bare ASCII)
ozbekcha  → özbekça    (mixed conventions)
тўғри     → töğri      (Cyrillic)
```

**We correct orthography. We never touch morphology, dialect, or voice.**
A keyboard that rewrites `kelaslar` into `kelasizlar` loses the user on day one.
That user is the entire market.

### Two exceptions, both OFF by default

Real minimal pairs exist, so these need sentence context and must never ship on
by default:

- `q ↔ k` — `qor`/`kor`, `qil`/`kil`, `qish`/`kish`
- `x ↔ h` — `xol`/`hol`, `xat`/`hat`

Implement behind flags `{ fuzzyQK: false, fuzzyXH: false }`. Write the tests.
Leave them off.

---

## 2. Character reference — get this exactly right

Use these codepoints. Mixing them up silently breaks everything downstream, and
it is the single most common failure in Uzbek text tooling.

| Char | Name | Codepoint |
|---|---|---|
| `Ş ş` | S with cedilla | U+015E / U+015F |
| `Ç ç` | C with cedilla | U+00C7 / U+00E7 |
| `Ö ö` | O with diaeresis | U+00D6 / U+00F6 |
| `Ğ ğ` | G with breve | U+011E / U+011F |
| `ʼ` | tutuq belgisi — the ONE apostrophe the new alphabet keeps | U+02BC |
| `ʻ` | turned comma — appears in OLD Latin `oʻ` `gʻ` only, never in new | U+02BB |

Canonical internal form is **new Latin, NFC-normalized**. Corpus, lexicon and all
intermediate state are stored canonically. Script is an output concern only.

Inbound normalization must accept and fold: U+0027 `'`, U+0060 `` ` ``,
U+00B4 `´`, U+2018 `‘`, U+2019 `’`, U+02BB `ʻ`, U+02BC `ʼ`, plus precomposed and
decomposed forms of all four new letters.

### Cyrillic ↔ Latin table

| Cyrillic | New Latin | Note |
|---|---|---|
| а б в г д | a b v g d | |
| е | e / ye | `ye` word-initially and after a vowel; `e` otherwise |
| ё ж з и й | yo j z i y | |
| к л м н о п р с т у ф | k l m n o p r s t u f | |
| х | x | |
| ц | s / ts | `s` word-initially (цирк→sirk), `ts` after a vowel; keep an exception list (акция→aksiya) |
| ч | ç | |
| ш | ş | |
| ъ | ʼ | maʼno, taʼsir |
| ь | — | dropped |
| э | e | |
| ю я | yu ya | |
| ў | ö | |
| қ | q | |
| ғ | ğ | |
| ҳ | h | |

`ng` is no longer a separate alphabet unit but the digraph still occurs. Never
split it across a correction boundary.

Cyrillic→Latin is deterministic. Latin→Cyrillic is **not** (`e`/`ye`, `s`/`ts`
collide) — build it lexicon-first with rule fallback, and have the roundtrip test
assert only `new → cyrillic → new` identity, not the reverse.

---

## 3. Repository layout

```
chertma/
├── CLAUDE.md                  ← this file
├── README.md
├── docs/
│   ├── SPEC.md                ← you write this first
│   └── OPEN-QUESTIONS.md      ← grows as you work
├── engine/                    ← pure ES modules, ZERO dependencies
│   ├── normalize.js           inbound cleanup → canonical NFC new-Latin
│   ├── skeleton.js            the invariant
│   ├── translit.js            new ↔ old ↔ cyrillic
│   ├── lexicon.js             binary loader, prefix + skeleton lookup
│   ├── rank.js                scoring
│   ├── learn.js               on-device personalization
│   ├── constants.js           all tunable weights, in ONE place
│   └── index.js               public API
├── tools/                     ← Python, build-time only
│   ├── fetch_corpus.py
│   ├── normalize_corpus.py
│   ├── build_ngrams.py
│   ├── pack_lexicon.py
│   └── build_benchmark.py     generates uz-alphabet-bench from fixtures
├── data/
│   ├── raw/                   gitignored
│   ├── SOURCES.md             every input, its origin and its licence
│   ├── uz-unigrams.tsv        gitignored
│   ├── uz-bigrams.tsv         gitignored
│   ├── lexicon-full.bin       committed
│   └── lexicon-lite.bin       committed
├── bench/                     ← the Hugging Face deliverable
│   ├── dev.jsonl
│   ├── test.jsonl
│   ├── README.md              dataset card (EN + UZ)
│   └── run_eval.py
├── web/
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   ├── sw.js
│   ├── manifest.json
│   └── CNAME                  → chertma.maqsudjon.com
└── tests/
    ├── golden.json
    ├── invariant.test.js
    ├── translit.test.js
    ├── ambiguity.test.js
    └── perf.test.js
```

---

## 4. Public API

Freeze this signature now. The mobile keyboards will bind against it.

```js
import { Chertma } from './engine/index.js';

const c = new Chertma({
  script:   'new',          // 'new' | 'old' | 'cyrillic'
  fuzzyQK:  false,
  fuzzyXH:  false,
  maxSuggestions: 3,
});

await c.load('/data/lexicon-lite.bin');   // or lexicon-full.bin

c.suggest(buffer, prevWord)   // → [{ word, score, source }]  live, per keystroke
c.autocorrect(text)           // → string  whole-text pass, invariant enforced
c.convert(text, from, to)     // → string  script conversion, NO correction
c.learn(word)                 // → void    on-device only, never transmitted
c.export()                    // → serializable user model, for device backup
c.stats()                     // → { lexiconSize, memoryBytes, loadMs }
```

`source` is one of `'exact' | 'lexicon' | 'bigram' | 'user'` so the UI can show
why a suggestion appeared.

---

## 5. Ranking

```
score = log(unigram_freq)
      + λ · log(bigram_freq(candidate | prevWord) + 1)
      + μ · user_bonus(candidate)
      − ν · edit_distance(input, candidate)
```

Start with `λ=2.0, μ=3.0, ν=0.5`. All four live in `engine/constants.js` and
nowhere else. Tune against `tests/golden.json`. No magic numbers scattered in
the code.

`user_bonus` is decayed frequency from `learn.js`. It lives on-device. It is
never uploaded. There is no telemetry endpoint anywhere in this codebase.

### Genuine ambiguities

Two valid skeleton-matching candidates; needs bigram context. All of these go in
`tests/ambiguity.test.js` and into the benchmark:

```
sok   → sok (juice)        | şok (shock)
ser   → ser (rich in)      | şer (lion / verse)
och   → oç  (open/hungry)  | öç  (revenge)
gor   → gör (grave)        | gor (cave)
kop   → köp (many)         | kop
boli  → boli               | böli
```

---

## 6. Corpus

**Do not crawl anything. The data already exists and is open.** Tahrirchi has
published Uzbek corpora on Hugging Face since 2023. Use them.

| Dataset | What it is | Why it matters here |
|---|---|---|
| `tahrirchi/uz-crawl` | web + Telegram crawl, ~1.2 M unique sources, v2 current to March 2024, ~1.7 GB generated | The Telegram portion is **informal** Uzbek — dialect, slang, contractions. This is the material the invariant test needs. |
| `tahrirchi/uz-books-v2` | ~40 000 books, separate `lat` and `cyr` splits generated by curated transliteration scripts, Google Cloud Vision OCR | A ready-made **parallel Latin/Cyrillic corpus**. Your `translit.js` roundtrip test runs directly against it. Do not build this yourself. |
| `tahrirchi/uz-books` (v1) | same books, Apache-2.0, ~33 GB expanded | Only if v2 is insufficient. Start with v2. |

**Check the licence of each dataset before use and record it in
`data/SOURCES.md`.** `uz-books` is Apache-2.0; confirm the others individually
rather than assuming.

### Pipeline

1. **Fetch** — `datasets.load_dataset(...)`. Record source and licence per input.
2. **Normalize** — everything to canonical new Latin, NFC. Cyrillic goes through
   the same rules as `translit.js`, mirrored in Python. Drop any document where
   more than 5% of tokens fall outside the Uzbek charset (kills Russian/English
   contamination).
3. **Count** — unigrams and bigrams. Drop hapax legomena. Drop tokens under 2
   chars except a known whitelist. **Keep a separate frequency table for the
   Telegram/informal slice** — the register differs sharply from books and the
   suggestions should reflect how people actually write.
4. **Index** — group unigrams by `skeleton()`. This is the runtime lookup.
5. **Pack** — binary, loaded via `fetch` + `DataView`.

### Size budgets — hard limits

| Artifact | Budget |
|---|---|
| `engine/` gzipped | ≤ 30 KB |
| `lexicon-full.bin` gzipped | ≤ 8 MB |
| `lexicon-lite.bin` gzipped | ≤ 2 MB |
| Runtime heap, lite | ≤ 25 MB |

`lexicon-lite` = top 50k unigrams + top 200k bigrams. It is the mobile build and
the budget that actually matters — an iOS keyboard extension gets roughly 60 MB
for everything.

Start with gzipped TSV and a simple packed format. Only reach for a DAWG or FST
if a budget is genuinely missed. Measure before optimizing.

---

## 7. Tests — write these BEFORE the engine

1. **`golden.json`** — ~300 `{ input, expected, script }` triples across all
   three scripts, mixed case, punctuation, numbers, emoji passthrough.
2. **`invariant.test.js`** — pull 10 000 informal strings from the `uz-crawl`
   Telegram slice that are absent from the lexicon; assert
   `autocorrect(s) === s` for every one. This test failing means the product is
   broken, not the test.
3. **`translit.test.js`** — for every lexicon entry, assert
   `convert(convert(w,'new','cyrillic'),'cyrillic','new') === w`. Then run the
   same check against `uz-books-v2`'s paired `lat`/`cyr` splits as an
   independent source of truth.
4. **`ambiguity.test.js`** — §5 pairs, with and without context.
5. **`perf.test.js`** — `suggest()` p95 under 5 ms on cold V8; `load()` under
   400 ms for lite.

Node's built-in `node:test`. No Jest, no Vitest, no dependencies.

---

## 8. `uz-alphabet-bench` — the Hugging Face deliverable

The alphabet changed in September 2026. As of now there is **no public
evaluation set** for it. Every Uzbek LLM, every transliteration tool and every
publisher migrating an archive needs one. Build it.

### Format

JSONL, mirroring `tahrirchi/uzlib` so it drops into existing eval harnesses:

```json
{
  "id": "ASC0142",
  "category": "ascii2new",
  "context": null,
  "question": "\"sosib\" so'zining yangi alifbodagi to'g'ri shakli qaysi?",
  "options": ["şoşib", "shoshib", "soşib", "şosib"],
  "answer": 0
}
```

### Categories — roughly 500 items total

| Category | n | Tests |
|---|---|---|
| `ascii2new` | 100 | bare ASCII → new Latin |
| `old2new` | 80 | `toʻgʻri` → `töğri` |
| `cyr2new` | 80 | `тўғри` → `töğri` |
| `preserve` | 100 | dialect/slang that must NOT change; correct option is "o'zgarmaydi" |
| `ambiguity` | 60 | `sok`/`şok` etc., resolved by sentence context |
| `apostrophe` | 40 | `ʼ` U+02BC vs `ʻ` U+02BB placement — `maʼno`, `taʼsir` |
| `edge` | 40 | `ng`, `e`/`ye`, `ц`, proper nouns, loanwords, code-switching |

`preserve` is the most important category and the one no other benchmark has.
It is what separates a tool that respects how people write from one that
flattens them.

### Splits

- `dev.jsonl` — 50 items, answers public, for calibration
- `test.jsonl` — 450 items

### Required alongside

- `bench/README.md` — dataset card in **English and Uzbek**: motivation,
  construction method, category definitions, known limitations, licence
  (CC-BY-4.0), citation block, contact.
- `bench/run_eval.py` — scores any Hugging Face model or API endpoint, prints
  per-category accuracy, writes a leaderboard table into the README.
- A baseline row for Chertma's own engine, and rows for 2–3 public models so the
  leaderboard is not empty on day one.

### ⚠ Non-negotiable

**Every one of the ~500 items must be reviewed by hand by the human before
publication.** You may draft them from `golden.json`, the ambiguity fixtures and
the corpus, but a linguistic benchmark that a model generated and nobody checked
is worse than no benchmark. Generate them into a reviewable table, hand it over,
and stop.

---

## 9. Web demo

Vanilla JS, no framework, no build step beyond optional esbuild for
minification.

**Two modes on one page:**

1. **Live typing** — a textarea. Type ASCII; all three scripts render below,
   updating per keystroke. Corrected characters briefly highlighted in the accent
   colour. A keystroke-savings counter ("you saved 47 keypresses").
2. **Paste & convert** — paste any text, pick source and target script, get clean
   output with a copy button. No correction, just conversion. **This is the
   acquisition hook** — immediately useful to every Uzbek on the internet today,
   including people who will never install a keyboard.

**Also:**

- Output-script toggle, persisted in `localStorage`
- A prominent "what we don't touch" panel showing `kelaslar`, `qisela`, `balu`
  passing through unchanged — this is the trust-builder, do not bury it
- A link to `uz-alphabet-bench` on Hugging Face
- PWA with service worker, fully functional offline after first load
- Zero network calls after load. Zero cookies. Zero analytics. Say so on the page.

**Design language — match `flarestamina.com`:**

- JetBrains Mono throughout
- Accent `#FF6A1A`
- Dark background
- Dot-matrix texture
- Restrained and technical. No gradients, no rounded-everything, no stock
  illustration.

---

## 10. Deploy

GitHub Pages from the repo. `web/CNAME` contains exactly:

```
chertma.maqsudjon.com
```

DNS: `chertma` → `CNAME` → `maqsudjon-cell.github.io`, DNS-only (not proxied).

The benchmark publishes separately to `huggingface.co/datasets/<HF_USERNAME>/uz-alphabet-bench`
— ask the human for the namespace, do not guess it.

---

## 11. Out of scope — do not scaffold these

Android keyboard. iOS keyboard extension. Voice input. User accounts. Cloud
sync. Any backend at all. A paid tier.

They come later. Stubs written now will be wrong and will have to be deleted.

---

## 12. Order of work

```
1. docs/SPEC.md — equivalence table, invariant, API, binary format.
   ⏸ CHECKPOINT — show SPEC.md and stop. If the equivalence table is wrong,
   every later step is wasted work.

2. tools/ — corpus pipeline end to end against the Tahrirchi datasets.
   Report: token counts, vocabulary size, licence of each source, and the
   actual byte size of both lexicons.
   ⏸ CHECKPOINT — show the numbers against the §6 budgets.

3. tests/ — golden file and all five suites. They will all fail. Good.

4. engine/ — until every test passes. Do not touch web/ before this.
   ⏸ CHECKPOINT — full test output plus perf numbers.

5. bench/ — generate ~500 draft items into a reviewable table.
   ⏸ CHECKPOINT — hand the table over for manual review. Do NOT publish.

6. web/ — demo and PWA.

7. Deploy the site. Then README.md with a real before/after example at the top.
```

---

## 13. Acceptance criteria

Ship only when all of these hold:

- [ ] `sosib pisib togri kelasizmi` → `şoşib pişib töğri kelasizmi`
- [ ] `kelaslar`, `qisela`, `balu`, `kettik` come through byte-identical
- [ ] All three scripts convert correctly both directions on the golden file
- [ ] Roundtrip verified independently against `uz-books-v2` lat/cyr splits
- [ ] Every size budget in §6 met, with measured numbers in the README
- [ ] `suggest()` p95 under 5 ms
- [ ] Site works with the network disconnected after first load
- [ ] `grep -ri "fetch\|XMLHttpRequest\|sendBeacon" engine/` returns nothing
- [ ] `package.json` has an empty `dependencies` object
- [ ] `data/SOURCES.md` names the licence of every corpus input
- [ ] All 500 benchmark items reviewed and signed off by the human

---

## 14. How to work

- Ask before adding any dependency. The answer is almost always no.
- Commit at each checkpoint, with a message naming what landed.
- When a linguistic question is genuinely ambiguous — a Cyrillic edge case, a
  dialect form you cannot classify, a loanword with no settled spelling —
  **stop and ask**. Do not guess and bury the guess in code. Log every one of
  them in `docs/OPEN-QUESTIONS.md` as you go.
- If a size or performance budget cannot be met, say so at the checkpoint with
  the measured number. Do not silently raise the budget.
- Do not publish anything to Hugging Face. Prepare it; the human publishes.
