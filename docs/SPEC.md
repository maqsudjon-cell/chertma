# Chertma — Engine Specification

**Version:** 0.1 (draft)
**Status:** ⏸ CHECKPOINT 1. Nothing past this document has been written yet.

This document is normative. Code, tests and the Python pipeline follow it; if
they disagree with it, they are wrong or this document gets amended first.

Markers used below:

- **[BRIEF]** — taken as-is from `CLAUDE.md`.
- **[PROPOSED]** — goes beyond `CLAUDE.md` or deviates from it. Needs a yes/no.
- **[Qn]** — linked to `docs/OPEN-QUESTIONS.md`. Decided provisionally, blocking
  only where noted.

---

## 1. Terms

| Term | Meaning |
|---|---|
| **new** | New Latin script (2026 law): `ş ç ö ğ`, tutuq `ʼ` |
| **old** | Old Latin script (1995): `sh ch oʻ gʻ`, tutuq `ʼ` |
| **cyrillic** | Uzbek Cyrillic: 35 letters incl. `ў қ ғ ҳ` |
| **canonical form** | new Latin, lowercase where the lexicon is concerned, NFC |
| **token** | a maximal word span produced by §3; everything else is a *gap* |
| **skeleton** | the result of `skeleton(token)` (§4) |
| **candidate** | a lexicon or user-model word whose skeleton equals the input's |
| **correction** | replacing a token with a candidate that is not the token itself |

---

## 2. Characters and canonical form

### 2.1 The new letters [BRIEF]

| Char | Name | Upper | Lower |
|---|---|---|---|
| Ş ş | S with cedilla | U+015E | U+015F |
| Ç ç | C with cedilla | U+00C7 | U+00E7 |
| Ö ö | O with diaeresis | U+00D6 | U+00F6 |
| Ğ ğ | G with breve | U+011E | U+011F |

### 2.2 Apostrophes [BRIEF]

| Char | Codepoint | Role |
|---|---|---|
| `ʼ` | U+02BC | **tutuq belgisi**. The only apostrophe in canonical text. |
| `ʻ` | U+02BB | old-Latin `oʻ gʻ` only. Never appears in canonical text. |

Canonical text contains no U+0027, U+2019, U+02BB or any other apostrophe-like
character. Output in the `old` script uses U+02BB inside `oʻ gʻ` and U+02BC for
tutuq.

### 2.3 Apostrophe-likes (the inbound fold set)

`A` denotes this set everywhere below.

| Codepoint | Char | Source |
|---|---|---|
| U+0027 | `'` | [BRIEF] |
| U+0060 | `` ` `` | [BRIEF] |
| U+00B4 | `´` | [BRIEF] |
| U+2018 | `‘` | [BRIEF] |
| U+2019 | `’` | [BRIEF] |
| U+02BB | `ʻ` | [BRIEF] |
| U+02BC | `ʼ` | [BRIEF] |
| U+02BD | `ʽ` | [PROPOSED] seen in Word autocorrect output |
| U+02BF | `ʿ` | [PROPOSED] used for `ʻ` by several Uzbek sites |
| U+2032 | `′` | [PROPOSED] prime, macOS/iOS smart punctuation leftovers |

### 2.4 Inbound normalization — `normalize(text)`

Applied to all engine input before anything else. Pure function, no locale.

1. Unicode **NFC**. This folds decomposed `s◌̧ c◌̧ o◌̈ g◌̆` into the precomposed
   letters of §2.1. [BRIEF]
2. **Confusable fold** [PROPOSED, Q7]:

   | From | To | Why |
   |---|---|---|
   | `ș Ș` U+0219/U+0218 (comma below) | `ş Ş` | Romanian layout, visually identical, very common |
   | `ǧ Ǧ` U+01E7/U+01E6 (caron) | `ğ Ğ` | seen in PDFs and some fonts |
   | `ı` U+0131 (dotless i) | `i` | Turkish keyboards; Uzbek has no dotless i |
   | `İ` U+0130 | `I` | Turkish keyboards |
   | `һ Һ` U+04BB/U+04BA | `ҳ Ҳ` | Kazakh/Bashkir layouts used for Uzbek |
   | `ӯ Ӯ` U+04EF/U+04EE | `ў Ў` | Tajik layout |

3. Apostrophe-likes are **not** rewritten by `normalize()`. They are
   interpreted by the stage that consumes them (§4, §6), because `o'` means
   different things in different scripts.

Lowercasing anywhere in this project uses locale-independent case mapping
(`String.prototype.toLowerCase()`, Python `str.lower()`), **never** a Turkish
or Azerbaijani locale — those map `I` to `ı`.

---

## 3. Tokenization

Tokenization splits text into alternating *tokens* and *gaps* such that
concatenating them reproduces the input byte-for-byte. Only tokens are ever
candidates for change. Gaps are copied through verbatim.

### 3.1 Letters

`L` = any codepoint of Unicode general category `L*` or `M*`, **excluding** the
apostrophe-likes in `A` (U+02BB and U+02BC are category `Lm` and would
otherwise be letters).

### 3.2 Token grammar

```
token := L+ ( A+ L+ )* tail?
tail  := A        -- only if the preceding letter is o O g G
                  -- (old-Latin word-final oʻ gʻ: bogʻ, togʻ)
       | U+02BC   -- after any letter (explicit tutuq: manʼ, jamʼ)
```

- Apostrophes between letters are always token-internal: `to'g'ri`,
  `ma'no`, `mo''jiza`.
- Leading apostrophes are never part of a token: in `'salom'` the token is
  `salom`.
- A hyphen always ends a token: `oʻsha-oʻsha` → `oʻsha` `-` `oʻsha`;
  `2026-yil` → `2026` `-` `yil`.

### 3.3 Protected spans — never modified [PROPOSED, Q8]

The following spans are treated as gaps even though they contain letters:

| Span | Pattern (informal) | Example |
|---|---|---|
| URL | `scheme://…` or `www.…` up to whitespace | `https://chertma.maqsudjon.com` |
| bare domain | `label(.label)+` ending in a known TLD | `flarestamina.com` |
| email | `…@…` | `nom@mail.uz` |
| mention / hashtag | `@\w+`, `#\w+` | `@maqsudjon`, `#togri` |
| letters glued to digits | letters adjacent to a digit with no separator | `5ta`, `A4`, `mp3` |
| mixed-case token | not all-lower, not Title, not ALL-CAPS | `iPhone`, `YouTube` |

Without this, `chertma.maqsudjon.com` would be "corrected" into a broken link.

### 3.4 Case pattern

Every token has a case pattern: `lower`, `title` (first letter upper, rest
lower), or `upper`. Tokens of one letter that is uppercase are `title`. Mixed
case is protected (§3.3). Output tokens take the case pattern of the input
token (§7.3). **Case is never changed** by `autocorrect()`. [PROPOSED, Q9]

---

## 4. Skeleton — the equivalence function

`skeleton(token)` maps a token to a string over a small alphabet, discarding
every distinction a keyboard could plausibly have destroyed. It is the only
thing that decides whether a correction is allowed.

### 4.1 Pipeline (normative order)

```
skeleton(token) =
  1. normalize(token)                          §2.4
  2. lowercase                                 locale-independent
  3. transliterate Cyrillic letters → new      §6.1  (Latin letters untouched)
  4. delete every apostrophe-like (set A)      the ∅ class
  5. scan left→right, digraphs first:
        sh → S    ch → C    gh → G
     then single letters:
        s ş w      → S
        c ç        → C
        o ö ó ő    → O
        g ğ ǵ      → G
        any other  → itself
  6. if fuzzyQK:  q k → K                      §4.7, off by default
     if fuzzyXH:  x h → H                      §4.7, off by default
```

The class symbols `S C O G K H` are uppercase ASCII; every other symbol is
lowercase, so they cannot collide. For every lexicon word the skeleton is pure
ASCII.

### 4.2 Why this order — two deliberate changes from a flat lookup table

**Step 3 before step 5 (Cyrillic transliterated first).** The brief's class
table puts Cyrillic letters directly into classes. That works for `ш с ч ў о ғ
г ъ ь`, but it cannot work for `ц` and `е`, whose Latin value depends on
position (`цирк → sirk`, `милиция → militsiya`, `ер → yer`, `кел → kel`). A
per-character table would give `цирк` and `sirk` different skeletons.
Transliterating first reproduces **exactly** the brief's class memberships for
every Cyrillic letter the brief lists (`ш→ş→S`, `с→s→S`, `ч→ç→C`, `ў→ö→O`,
`о→o→O`, `ғ→ğ→G`, `г→g→G`, `ъ→ʼ→∅`, `ь→∅`) and additionally makes `ц е ё ю я`
consistent. Cyrillic→Latin is deterministic, so this stays a pure function.

**Step 4 before step 5 (apostrophes dropped before digraphs).** Old Latin
writes `sʼh` to mean *s + h, not sh* (`Isʼhoq`). Its new-Latin form is
`Ishoq`. If digraphs were folded first, `Is'hoq` would give `iShOq` (the `s`
is not followed by `h`), while `Ishoq` gives `iSOq`: a real word would fail its
own invariant. Dropping apostrophes first gives `iSOq` for both.

### 4.3 Resulting class table

This is the brief's table restated as the output of §4.1. It is a test
fixture (`tests/skeleton.fixtures.json`, shared by the JS and Python
implementations).

| Class | Collapses (after normalize + lowercase + Cyrillic→new) |
|---|---|
| `S` | `ş` `sh` `s` `w` · via Cyrillic `ш` `с` · via `ц` word-initially and after consonants |
| `C` | `ç` `ch` `c` · via Cyrillic `ч` |
| `O` | `ö` `o` `ó` `ő` (+ any following apostrophe, dropped in step 4) · via Cyrillic `ў` `о`, and the `o` inside `ё → yo` |
| `G` | `ğ` `gh` `g` `ǵ` (+ any following apostrophe) · via Cyrillic `ғ` `г` |
| `∅` | every char in `A` · via Cyrillic `ъ` `ь` |
| self | everything else, lowercased |

### 4.4 Worked examples

| Input | After step 3–4 | Skeleton |
|---|---|---|
| `şoşib` | `şoşib` | `SOSib` |
| `shoshib` | `shoshib` | `SOSib` |
| `sosib` | `sosib` | `SOSib` |
| `togri` | `togri` | `tOGri` |
| `to'g'ri` | `togri` | `tOGri` |
| `тўғри` | `töğri` | `tOGri` |
| `TOʻGʻRI` | `togri` | `tOGri` |
| `wunaqa` | `wunaqa` | `Sunaqa` |
| `ozbekcha` | `ozbekcha` | `OzbekCa` |
| `yong'oq` | `yongoq` | `yOnGOq` |
| `maʼno` / `mano` | `mano` | `manO` |
| `цирк` / `sirk` | `sirk` | `Sirk` |
| `милиция` | `militsiya` | `militSiya` |
| `kelaslar` | `kelaslar` | `kelaSlar` |
| `Is'hoq` / `Ishoq` / `Işoq` | `ishoq` / `ishoq` / `işoq` | `iSOq` |
| `shoshima` | `shoshima` | `SOSima` — no lexicon word has it, so it passes through |

### 4.5 Properties the implementation must have (all tested)

1. **Pure and deterministic.** No options other than the two fuzzy flags
   affect it.
2. **Keys, not text.** A skeleton is never rendered, stored in the lexicon
   file, or fed back into `skeleton()`. The JS and Python implementations must
   agree on every entry of the shared fixture file.
3. **Prefix monotonic.** For any string `b` and character `x`,
   `skeleton(b + x)` starts with `skeleton(b)` **or** equals it. This holds
   because each digraph folds to the class of its own first letter
   (`s→S, sh→S`; `c→C, ch→C`; `g→G, gh→G`), apostrophes vanish, and every
   position-dependent Cyrillic rule looks only backwards. `suggest()` depends
   on this: the candidate set can only narrow as the user types.
4. **Script-blind.** For every lexicon word `w`:
   `skeleton(w) === skeleton(convert(w,'new','old')) === skeleton(convert(w,'new','cyrillic'))`.

### 4.6 Consequences to be aware of

- **Literal `s+h`, `c+h`, `g+h` in canonical words** share a skeleton with
  `ş`/`s`, `ç`/`c`, `ğ`/`g`. `Ishoq` (s+h) and a hypothetical `isoq` collide.
  Such words are rare in new Latin (the digraph ambiguity is what the reform
  removed). The pipeline counts them at checkpoint 2. [Q4]
- **`ng`** is not a class: `n` stays `n`, `g` joins `G`. So `yongoq → yonğoq`
  (walnut, old `yongʻoq`) *is* a correction, and it is correct. See [Q3] for
  what "never split `ng` across a correction boundary" is taken to mean.
- **Russian-layout Cyrillic** (`у` for `ў`, `к` for `қ`, `х` for `ҳ`) is **not**
  covered: `тугри` has skeleton `tuGri`, not `tOGri`, so it passes through
  unchanged. `г` for `ғ` and `о` for `ў` *are* covered. [Q6]
- **Latin/Cyrillic homoglyphs inside one token** (`тoғ` with a Latin `o`) are
  not repaired in v1; such a token is script-mixed and passes through. [Q7]

### 4.7 Fuzzy flags [BRIEF]

`{ fuzzyQK: false, fuzzyXH: false }`. When on, step 6 adds `K` and `H`
classes. The lexicon index is sorted by the non-fuzzy skeleton, so a fuzzy
lookup expands the query into every `q/k`, `x/h` variant (capped at
`FUZZY_MAX_VARIANTS` in `constants.js`, default 16) and unions the results.
`h` consumed by a digraph in step 5 is not subject to `fuzzyXH`. Both flags are
tested on and off; both ship off.

---

## 5. The invariant

> A correction is permitted **if and only if**
> `skeleton(input) === skeleton(candidate)`.
> Otherwise the input token is returned **unchanged, byte-identical.** [BRIEF]

Enforced in three places, not one:

1. **By construction** — candidates are only ever fetched by skeleton key.
2. **By a runtime guard** — immediately before a token is emitted,
   `autocorrect()` recomputes `skeleton(output)` against `skeleton(input)`; on
   mismatch it emits the input bytes. This is cheap and survives future
   refactors of the ranking code.
3. **By tests** — `tests/invariant.test.js` (10 000 informal strings, byte
   identity) and a property test over the golden file.

"Unchanged" means the exact input code units, including decomposed accents,
non-canonical apostrophes and original case. A token that needs no letter
change is never re-encoded (e.g. `ma'no` stays `ma'no` if the chosen candidate
renders to the same letters in the output script — see §7.3 step 5).

**We correct orthography. We never touch morphology, dialect, or voice.**

---
## 6. Script conversion — `convert(text, from, to)`

Pure conversion. No correction, no lexicon lookup on the `→ new`/`→ old`
paths. Protected spans (§3.3) are copied through. Every path goes through
canonical new Latin: `from → new → to`.

### 6.1 Cyrillic → new (deterministic)

Letter table [BRIEF], with the position rules made explicit.
"Vowel" = `а е ё и о у э ю я ў`.

| Cyrillic | New | Rule |
|---|---|---|
| а б в г д ж з и й к л м н о п р с т у ф х | a b v g d j z i y k l m n o p r s t u f x | |
| ч ш ў қ ғ ҳ | ç ş ö q ğ h | |
| э | e | |
| ё ю я | yo yu ya | always |
| е | `ye` | word-initially, after a vowel, after `ъ` or `ь` |
| е | `e` | otherwise |
| ц | `s` | word-initially **and after a consonant** [Q1] |
| ц | `ts` | after a vowel |
| ъ | `ʼ` U+02BC | default: `маъно→maʼno`, `таъсир→taʼsir`, `шеър→şeʼr` |
| ъ | *(dropped)* | before `е ё ю я` [Q2]: `объект→obyekt`, `съезд→syezd` |
| ь | *(dropped)* | default: `компьютер→kompyuter` |
| ь | `y` | before `о` [Q2]: `бульон→bulyon`, `павильон→pavilyon` |
| other Cyrillic (`щ ы` …) | *(unchanged)* | not Uzbek letters; token is left as-is [Q5] |

A fixed exception list (words the rules get wrong) lives in
`engine/translit.js` and is mirrored byte-for-byte in `tools/`. Its initial
contents are **empty by design**: candidates will be generated at checkpoint 2
by diffing our output against `uz-books-v2`'s own transliteration, and each
entry is added only after human review. [Q1]

**Case of multi-letter outputs** (`ye yo yu ya ts`): if the source letter is
uppercase and the next letter in the token is also uppercase (or there is no
next letter and the previous one is uppercase), emit all caps (`ЁЗУВ→YOZUV`);
if only the source letter is uppercase, emit Title (`Ёзув→Yozuv`).

### 6.2 new → old

| New | Old | Note |
|---|---|---|
| ş Ş | sh Sh / SH | `SH` inside an all-caps token |
| ç Ç | ch Ch / CH | same |
| ö Ö | oʻ Oʻ | U+02BB |
| ğ Ğ | gʻ Gʻ | U+02BB |
| literal `s`+`h` | `sʼh` | separator, so old readers don't see `sh` (`Ishoq→Isʼhoq`) [Q4] |
| ʼ | ʼ | U+02BC unchanged |

### 6.3 old → new

Inside a token, left to right:

| Old | New | Note |
|---|---|---|
| `s` + A + `h` | `sh` | old separator → literal s+h, apostrophe removed |
| `sh` | ş | |
| `ch` | ç | |
| `o` + A | ö | first apostrophe-like after `o` is the letter's mark |
| `g` + A | ğ | same |
| any other A | ʼ U+02BC | tutuq: `ma'no→maʼno`, `mo''jiza→möʼjiza` |

`w` and `c` are **not** converted — `w` for `sh` is a typing habit, not old
orthography. Only `autocorrect()` handles it (through the skeleton).

### 6.4 new → Cyrillic (lexicon-first, rule fallback) [BRIEF]

1. If the lowercase canonical token is a lexicon word with a stored Cyrillic
   exception (§9 section `CYR_EXC`), emit it with the token's case pattern.
2. Otherwise apply rules:

| New | Cyrillic | Rule |
|---|---|---|
| `ye` | е | word-initially or after a vowel |
| `ye` | ъе | after a consonant (`obyekt→объект`) |
| `e` | э | word-initially or after a vowel (`eshik→эшик`, `poeziya→поэзия`) |
| `e` | е | otherwise |
| `yo yu ya` | ё ю я | always |
| `ts` | тс | **always** — native forms `ketsin`, `aytsin`, `otsiz` are far more frequent than loans; loans (`militsiya→милиция`) come from step 1 |
| `s` | с | always; `sirk→цирк` comes from step 1 |
| `ʼ` | ъ | |
| ş ç ö ğ q h x | ш ч ў ғ қ ҳ х | |
| other Latin | letter table reversed | |

3. A token containing `c` or `w` (not letters of the Uzbek alphabet in either
   Latin script) and not in the lexicon is foreign; it is emitted **unchanged in
   Latin** inside Cyrillic output (`Windows`, `Coca-Cola`). [Q5]

The round-trip guarantee is one-directional [BRIEF]: for every lexicon word
`w`, `convert(convert(w,'new','cyrillic'),'cyrillic','new') === w`.

---

## 7. Public API

Signatures frozen [BRIEF]. This section fixes their semantics.

```js
import { Chertma } from './engine/index.js';

const c = new Chertma({
  script: 'new',             // 'new' | 'old' | 'cyrillic'
  fuzzyQK: false,
  fuzzyXH: false,
  maxSuggestions: 3,
  loader: undefined,         // [PROPOSED] async (url) => ArrayBuffer   §7.1
  userModel: undefined,      // [PROPOSED] object from a previous export() §7.5
  clock: undefined,          // [PROPOSED] () => ms since epoch; default Date.now
});
```

### 7.1 `await c.load(source)` → `void`

`source` is an `ArrayBuffer`, a `Uint8Array`, or a URL string.

**Conflict in the brief, resolved [PROPOSED, Q10]:** the brief shows
`load('/data/lexicon-lite.bin')` *and* requires that
`grep -ri "fetch\|XMLHttpRequest\|sendBeacon" engine/` returns nothing. The
engine cannot fetch a URL without a network API. Resolution: when `source` is a
string, the engine calls the host-supplied `options.loader(source)` and throws
a clear error if none was given. The web demo passes a one-line loader in
`web/app.js`; a keyboard passes a file read. The engine never touches the
network and the grep stays clean — honestly, not by string-splitting.

`load()` validates magic, version and CRC-32 (§9) and builds the offset table.
Calling it again replaces the lexicon.

### 7.2 `c.suggest(buffer, prevWord)` → `[{ word, score, source }]`

- `buffer`: the partial token being typed, any script. `prevWord`: the previous
  committed word or `null`.
- Candidates: lexicon and user words whose skeleton **starts with**
  `skeleton(buffer)` (prefix monotonicity, §4.5). Distance is computed over the
  typed positions only (§8.2).
- Empty `buffer` with a `prevWord`: next-word prediction from bigrams.
- Returns at most `maxSuggestions`, best first, `word` rendered in `script`
  with the buffer's case pattern.
- `source`, by precedence: `'exact'` — the candidate is a complete word and
  its letters equal the buffer's letters with zero distance; `'user'` — the
  user bonus term is non-zero; `'bigram'` — the bigram term is non-zero;
  `'lexicon'` — otherwise.

### 7.3 `c.autocorrect(text)` → `string`

1. Tokenize (§3). Gaps and protected spans are copied through.
2. For each token: fetch candidates by exact skeleton. None → emit input
   bytes.
3. Rank (§8). `prevWord` is the previous token's output, reset after
   `. ! ? …` and newlines.
4. **Margin rule [PROPOSED, Q11]:** let `z` be the candidate at distance 0
   from the input (the word the user literally typed, if it is one). If `z`
   exists and the best candidate `b ≠ z`, replace only if
   `score(b) − score(z) ≥ AUTOCORRECT_MARGIN`. A valid word is not overwritten
   by a merely *more frequent* word.
5. Render the winner in `script` with the input's case pattern. If the rendered
   string has the same letters as the input (e.g. `shok` in `old` script), emit
   the input bytes.
6. Runtime invariant guard (§5).

The engine does **not** learn from `autocorrect()`. Learning is explicit.

### 7.4 `c.convert(text, from, to)` → `string`

§6. `from`, `to` ∈ `'new' | 'old' | 'cyrillic'`. `from === to` returns `text`
unchanged.

### 7.5 `c.learn(word)` → `void`, `c.export()` → `object`

- `word` is interpreted in the current `script` and stored canonically.
- Model: `Map<canonicalWord, { count, lastSeen }>`. On learn:
  `count ← count · 2^(−Δt / USER_HALF_LIFE_MS) + 1`.
- `user_bonus(w) = ln(1 + decayedCount(w))`; 0 for unknown words.
- Learned words that are not in the lexicon become candidates too — still only
  through their skeleton, so the invariant is unaffected.
- Capped at `USER_MAX_WORDS`; the lowest decayed count is evicted.
- `export()` → `{ format: 'chertma-user', version: 1, words: [[word, count, lastSeenMs], …] }`,
  JSON-serializable. Restored through the `userModel` constructor option,
  which keeps the frozen method list unchanged. [PROPOSED]
- Never transmitted. There is no network code in `engine/` (§7.1).

### 7.6 `c.stats()` → `{ lexiconSize, memoryBytes, loadMs }`

`lexiconSize` = word count N. `memoryBytes` = lexicon `ArrayBuffer` +
derived typed arrays + an estimate of the user model. `loadMs` = wall time of
the last `load()` excluding the host loader. Real heap is measured separately
in `tests/perf.test.js` with `process.memoryUsage()`.

---
## 8. Ranking

### 8.1 Score [BRIEF]

```
score(cand | input, prevWord) =
        ln(unigram(cand))
      + λ · ln(bigram(prevWord, cand) + 1)
      + μ · user_bonus(cand)
      − ν · distance(input, cand)
```

`λ=2.0, μ=3.0, ν=0.5` to start. Every tunable lives in `engine/constants.js`
and nowhere else:

| Constant | Start | Meaning |
|---|---|---|
| `LAMBDA_BIGRAM` | 2.0 | [BRIEF] λ |
| `MU_USER` | 3.0 | [BRIEF] μ |
| `NU_DISTANCE` | 0.5 | [BRIEF] ν |
| `REGISTER_MIX` | 0.5 | weight of the informal table in `unigram()` — [PROPOSED] |
| `AUTOCORRECT_MARGIN` | 1.0 | §7.3 step 4 — [PROPOSED] |
| `USER_HALF_LIFE_MS` | 30 days | §7.5 |
| `USER_MAX_WORDS` | 5000 | §7.5 |
| `FUZZY_MAX_VARIANTS` | 16 | §4.7 |

`unigram(w) = exp((1−REGISTER_MIX)·ln c_all(w) + REGISTER_MIX·ln c_inf(w))`,
falling back to `c_all` when the word never occurs in the informal slice. Counts
come from the quantized tables in §9. User-only words use
`unigram = USER_ONLY_UNIGRAM` (a constant, 1 by default, i.e. `ln = 0`).

### 8.2 Distance — skeleton-aligned, not Levenshtein [PROPOSED, Q12]

Plain Levenshtein on raw strings punishes exactly the most explicit input:
`shoshib → şoşib` is 4 edits while `sosib → şoşib` is 2, although `sh`
*tells* us the letter is `ş`. Because input and candidate have equal skeletons,
they align symbol-by-symbol. Distance is the number of aligned positions where
the input's spelling does not denote the candidate's letter:

| Candidate letter | Input spellings at distance 0 | Everything else |
|---|---|---|
| ş | `ş` `sh` `w` (and Cyrillic `ш`) | 1 |
| s | `s` (Cyrillic `с`, `ц`→s) | 1 |
| literal s+h | `sh`, `s`A`h` | 1 |
| ç | `ç` `ch` (`ч`) | 1 |
| c | `c` | 1 |
| ö | `ö` `o`+A `ó` `ő` (`ў`) | 1 |
| o | `o` (`о`) | 1 |
| ğ | `ğ` `g`+A `gh` `ǵ` (`ғ`) | 1 |
| g | `g` (`г`) | 1 |
| tutuq ʼ after a letter | any A not consumed as an `o`/`g` mark (`ъ`) | +1 if the input has none; +1 if the input has one the candidate lacks |
| any other symbol | always 0 (skeletons are equal) | — |

Examples: `sok → sok` 0, `sok → şok` 1, `shok → şok` 0, `shok → sok` 1,
`togri → töğri` 2, `to'g'ri → töğri` 0, `mano → maʼno` 1.

### 8.3 Genuine ambiguities

Resolved by the bigram term. With no context, `unigram` and distance decide,
and the margin rule keeps a typed valid word. The fixture list (with
corrections to the brief's list) is in Appendix A and is **not final** until
the human signs off [Q13].

---

## 9. Binary lexicon format, version 1

One file, two builds: `lexicon-lite.bin` and `lexicon-full.bin`. Designed to
be read in place with typed-array views — no parsing into objects, no string
allocation until a word is returned — and to be trivial to re-implement in
Kotlin or Swift.

### 9.1 Conventions

- Little-endian everywhere. Every section starts at an offset divisible by 4
  (zero padding), so `Uint32Array`/`Uint16Array` views need no copy. On a
  big-endian host the reader falls back to `DataView`.
- **Word ids** are indices `0…N−1` in **skeleton order**: sorted by
  `skeleton(word)` compared by code unit, ties broken by the word's bytes.
  Consequence: every skeleton and every skeleton *prefix* is a contiguous id
  range, found by binary search that computes skeletons of probe words on the
  fly. Skeletons are never stored.
- **Words** are stored in **CP-UZ**, a one-byte encoding of the canonical
  alphabet: `a–z` = `0x61–0x7A`, `ş`=`0x80`, `ç`=`0x81`, `ö`=`0x82`,
  `ğ`=`0x83`, `ʼ`=`0x84`. Any other byte is invalid. Words with characters
  outside this alphabet are not packed.
- **Counts** are quantized: `q = clamp(round(ln(count) · QSCALE), 1, 255)`,
  `q = 0` means absent. Decoded `ln(count) = q / QSCALE`. `QSCALE` is chosen
  per file by the packer so the largest count maps to 255.

### 9.2 Header — 64 bytes

| Offset | Type | Field |
|---|---|---|
| 0x00 | `u8[4]` | magic `43 48 52 54` ("CHRT") |
| 0x04 | `u16` | format version = 1 |
| 0x06 | `u16` | flags: bit0 `HAS_BIGRAMS`, bit1 `HAS_INFORMAL`, bit2 `WIDE_IDS` (bigram ids are u32, else u16), bit3 `HAS_CYR_EXC` |
| 0x08 | `u32` | N — word count |
| 0x0C | `u32` | B — bigram count |
| 0x10 | `u32` | E — Cyrillic exception count |
| 0x14 | `f32` | `QSCALE_UNI` |
| 0x18 | `f32` | `QSCALE_BI` |
| 0x1C | `u32` | corpus tokens counted (informational) |
| 0x20 | `u32` | build time, Unix seconds |
| 0x24 | `u32` | CRC-32 (IEEE 802.3) of bytes `0x40…EOF` |
| 0x28 | `u8[24]` | reserved, zero |

### 9.3 Section table — at 0x40, 12 × (`u32 offset`, `u32 byteLength`)

Absolute offsets. Unused entries are `(0, 0)`. Sections follow at 0xA0.

| # | Section | Contents |
|---|---|---|
| 0 | `STR` | CP-UZ bytes of all words concatenated in id order, no separators |
| 1 | `STR_LEN` | `u8 × N` — byte length of each word (max 255); offsets are rebuilt at load into a `Uint32Array(N+1)` |
| 2 | `UNI_Q` | `u8 × N` — quantized count, all sources |
| 3 | `INF_Q` | `u8 × N` — quantized count, informal (Telegram) slice only |
| 4 | `WFLAGS` | `u8 × N` — bit0 `CAPITALIZED`: ≥ 90 % of corpus occurrences start uppercase (proper nouns; used by `suggest()` only) |
| 5 | `BG_OFF` | `u32 × (N+1)` — bigrams with first word *i* are `[BG_OFF[i], BG_OFF[i+1])` |
| 6 | `BG_ID` | `u16` or `u32` × B — second-word ids, ascending within each group |
| 7 | `BG_Q` | `u8 × B` — quantized bigram counts |
| 8 | `CYR_EXC` | E records sorted by id: `u32 wordId`, `u16 len`, `u16 × len` UTF-16 code units of the lowercase Cyrillic form, padded to 4 bytes |
| 9–11 | — | reserved |

### 9.4 Lookups this layout gives for free

| Operation | Cost |
|---|---|
| exact skeleton → candidates | 2 binary searches → id range |
| skeleton prefix → completions | 2 binary searches → id range, then scan `UNI_Q` in range for top-k |
| `bigram(prev, cand)` | binary search `cand` in `prev`'s sorted group |
| bigram completions for a prefix | the prefix id range is contiguous and the group is sorted by id → 2 binary searches give the sub-slice |

Measure before optimizing [BRIEF]. If a budget is missed at checkpoint 2, the
first fallbacks are (in order): varint-delta `BG_ID`, front-coded `STR` in
blocks of 16, a precomputed top-k table for 1–2-symbol prefixes. A DAWG/FST
only if those are not enough.

### 9.5 Lite vs full

- **lite** [BRIEF]: top 50 000 unigrams by `c_all`, top 200 000 bigrams whose
  both words are in the lite vocabulary. N < 65 536, so `WIDE_IDS` is off.
- **full**: the largest vocabulary and bigram set that fits 8 MB gzipped. The
  concrete N and B are measured and reported at checkpoint 2, not assumed.

### 9.6 Lexicon admission — keeping misspellings out [PROPOSED, Q17]

The informal crawl is full of `togri`, `ozbek`, `sosib`. If such a form entered
the lexicon, `togri` would become its own zero-distance candidate and the
margin rule would protect it — the engine would stop correcting the exact
errors it exists for.

Rule, applied per skeleton group by `tools/pack_lexicon.py`:

1. Call form `f` a **stripped variant** of form `g` in the same group if `f`
   is obtained from `g` by any of `ş→s`, `ç→c`, `ö→o`, `ğ→g`, deleting `ʼ`.
2. A stripped variant is admitted only if it is attested in the **book
   corpus** with a count ≥ `BOOK_MIN_RATIO` (build constant, start 0.01) of
   `g`'s book count. Book text is transliterated from Cyrillic, where `ш/с`,
   `ў/о`, `ғ/г`, `ч` and `ъ` are never confused, so it is the arbiter of which
   spellings exist.
3. A rejected variant's counts (all, informal, bigrams) are merged into `g`.
4. Forms with no marked sibling (`kelaslar`) are admitted on crawl evidence
   alone — they can never block a correction, because nothing else shares
   their skeleton.

Every merge is written to `data/merges.tsv` (gitignored) and summarized at
checkpoint 2.

---

## 10. Budgets and how they are measured [BRIEF]

| Artifact | Budget | Measured as |
|---|---|---|
| `engine/` | ≤ 30 KB gz | `cat engine/*.js \| gzip -9 \| wc -c` |
| `lexicon-full.bin` | ≤ 8 MB gz | `gzip -9 -c file \| wc -c` |
| `lexicon-lite.bin` | ≤ 2 MB gz | same |
| heap, lite loaded | ≤ 25 MB | `process.memoryUsage()` delta, `--expose-gc`, after `load()` + 1 000 `suggest()` calls |
| `suggest()` | p95 < 5 ms | cold Node process, 10 000 real prefixes from held-out text |
| `load()` lite | < 400 ms | cold, bytes already in memory, includes CRC |

A missed budget is reported with its measured number. Budgets are not raised
silently.

---

## 11. Prior art and what is taken from it

- **Turkish deasciifier** (Deniz Yuret; ports to Python/JS). Per ambiguous
  letter, a learned decision list of character-context patterns decides whether
  to add the diacritic. Works on words it has never seen. **Not adopted as the
  decision mechanism**: rewriting unseen words is precisely what the invariant
  forbids — it would turn `kelaslar` into whatever the patterns prefer. Taken:
  the framing of the task as restoring destroyed distinctions letter by letter,
  which is what the skeleton formalizes.
- **Zemberek-NLP** (Turkish). Its normalizer generates candidates with a
  diacritic-insensitive lexicon/morphology lookup and ranks them with an n-gram
  language model. **Adopted**: this is the Chertma architecture — skeleton key
  = diacritic-insensitive lookup, unigram + bigram score = the LM. Not taken
  (yet): morphological analysis to cover unseen inflections; v1 covers only
  surface forms present in the lexicon, so token coverage of the lite build is
  a number reported at checkpoint 2. [Q14]

---

## 12. Out of scope [BRIEF]

Android keyboard, iOS keyboard extension, voice input, accounts, cloud sync,
any backend, a paid tier. Not stubbed.

---

## Appendix A — ambiguity fixtures (draft, needs sign-off) [Q13]

The brief's list, with corrections where the brief appears to be wrong:

| Input | Candidates | Note |
|---|---|---|
| `sok` | sok *(juice)* · şok *(shock)* | as brief |
| `ser` | ser *(abundant)* · şer *(lion)* · **şeʼr** *(poem)* | brief lists "verse" under `şer`; the poem is `şeʼr` (шеър). Same skeleton, three candidates |
| `och` | oç *(hungry; open!)* · öç *(revenge)* | as brief |
| `gor` | gör *(grave, гўр)* · **ğor** *(cave, ғор)* | brief lists cave as `gor`; cave is `ğor` |
| `kop` | köp *(many)* · kop *(?)* | `kop` is not a standard word to my knowledge — confirm or drop |
| `boli` | boli · böli | neither form is clearly a standalone word — confirm or drop |

Proposed additions — high-frequency minimal pairs, every one to be confirmed:

| Input | Candidates |
|---|---|
| `oq` | oq *(white)* · öq *(bullet)* |
| `ot` | ot *(horse, name)* · öt *(fire, grass, pass!)* |
| `oz` | oz *(few)* · öz *(self)* |
| `ol` | ol *(take!)* · öl *(die!)* |
| `oy` | oy *(moon, month)* · öy *(thought)* |
| `tor` | tor *(narrow)* · tör *(net)* |
| `toq` | toq *(odd)* · töq *(full, dark)* |
| `toy` | toy *(foal)* · töy *(wedding)* |
| `boy` | boy *(rich)* · böy *(height)* |
| `soy` | soy *(stream)* · söy *(slaughter!)* |
| `chol` | çol *(old man)* · çöl *(desert)* |
| `chop` | çop *(gallop; print)* · çöp *(stick, rubbish)* |
| `chok` | çok *(seam)* · çök *(sink!)* |
| `qol` | qol *(stay!)* · qöl *(hand)* |
| `bos` | bos *(press!)* · boş *(head)* · böş *(empty)* |
| `tos` | tos *(pelvis)* · toş *(stone)* · töş *(chest)* |
| `qosh` | qoş *(eyebrow)* · qöş *(add!)* |
| `shox` | şox *(branch)* · şöx *(playful)* |
| `bog` | boğ *(garden)* · böğ *(strangle!)* |
| `son` | son *(number)* · şon *(glory)* |
| `sim` | sim *(wire)* · şim *(trousers)* |
| `is` | is *(soot, smell)* · iş *(work)* |
| `tus` | tus *(colour, look)* · tuş *(dream; noon)* |
| `qus` | qus *(vomit!)* · quş *(bird)* |

All pairs will be checked against corpus counts at checkpoint 2; a pair where
one side has negligible frequency is not a real ambiguity and is dropped.
