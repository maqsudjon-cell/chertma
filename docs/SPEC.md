# Chertma — Engine Specification

**Version:** 0.2 — checkpoint-1 rulings applied (2026-09-14)
**Status:** normative for step 2 onward.

This document is normative. Code, tests and the Python pipeline follow it; if
they disagree with it, they are wrong or this document gets amended first.

Markers used below:

- **[BRIEF]** — taken as-is from `CLAUDE.md`.
- **[RULED]** — goes beyond `CLAUDE.md` or deviates from it; decided by the human
  at checkpoint 1.
- **[Qn]** — the question in `docs/OPEN-QUESTIONS.md` where the ruling is recorded.

Where this document and `CLAUDE.md` disagree, this document wins.

---

## 1. Terms

| Term | Meaning |
|---|---|
| **new** | New Latin script (2026 law): `ş ç ö ğ`, tutuq `ʼ` |
| **old** | Old Latin script (1995): `sh ch oʻ gʻ`, tutuq `ʼ` |
| **cyrillic** | Uzbek Cyrillic: 35 letters incl. `ў қ ғ ҳ` |
| **canonical form** | new Latin, lowercase where the lexicon is concerned, NFC |
| **token** | a maximal word span produced by §3; everything else is a *gap* |
| **skeleton** | the set of keys `skeleton(token, script, opts)` (§4) |
| **key** | the single skeleton element of a canonical word, `key(w)` |
| **candidate** | a lexicon or user-model word whose key is in the input's skeleton |
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
| U+02BD | `ʽ` | [RULED] seen in Word autocorrect output |
| U+02BF | `ʿ` | [RULED] used for `ʻ` by several Uzbek sites |
| U+2032 | `′` | [RULED] prime, macOS/iOS smart punctuation leftovers |

### 2.4 Inbound normalization — `normalize(text)`

Applied to all engine input before anything else. Pure function, no locale.

1. Unicode **NFC**. This folds decomposed `s◌̧ c◌̧ o◌̈ g◌̆` into the precomposed
   letters of §2.1. [BRIEF]
2. **Confusable fold** [RULED, Q7]:

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
- A trailing apostrophe-like after `o`/`g` is **not** taken as `tail` when the
  token is immediately preceded by an apostrophe-like: the pair is a quotation
  (`'kino'` → token `kino`, not `kino'` → `kinö`). Cost: a quoted word that
  really ends in `oʻ`/`gʻ` loses its mark.

### 3.3 Protected spans — never modified [RULED, Q8]

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
token (§7.3). **Case is never changed** by `autocorrect()`. [RULED, Q9]

---

## 4. Skeleton — the equivalence function

`skeleton(token, script, opts)` maps a token to a **set of keys**, discarding
every distinction a keyboard could plausibly have destroyed. It is the only
thing that decides whether a correction is allowed.

- `script` is the token's detected input script, `'latin'` or `'cyrillic'`
  (§4.8). Script-mixed tokens are protected and never reach it.
- `opts` = `{ fuzzyQK, fuzzyXH, cyrillicKeyboardRecovery }`.
- For Latin input with both fuzzy flags off — the default — the set has exactly
  one element, and that element is the brief's string skeleton.
- A canonical word has exactly one key: `key(w)` = the single element of
  `skeleton(w, 'latin', {})`. The lexicon is indexed by `key`.

### 4.1 Pipeline (normative order)

```
skeleton(token, script, opts) =
  1. normalize(token)                                     §2.4
  2. lowercase                                            locale-independent
  3. script 'cyrillic': transliterate to new Latin        §6.1
       with cyrillicKeyboardRecovery, each у к х has two
       readings (§4.8), so this step yields a set of strings
     script 'latin': one string, untouched
  4. per string, delete every apostrophe-like (set A)     the ∅ class
  5. per string, scan left→right, digraphs first:
        sh → S    ch → C    gh → G
     then single letters:
        s ş w      → S
        c ç        → C
        o ö ó ő    → O
        g ğ ǵ      → G
        any other  → itself
  6. fuzzyQK: every q or k symbol has both readings q, k  §4.7, off by default
     fuzzyXH: every x or h symbol has both readings x, h  §4.7, off by default
  7. return the set of distinct results
```

The class symbols `S C O G` are uppercase ASCII; every other symbol is
lowercase, so they cannot collide. Every key of every lexicon word is pure
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

1. **Pure and deterministic.** The result depends only on the token, `script`
   and the three options.
2. **Keys, not text.** A key is never rendered, stored in the lexicon file, or
   fed back into `skeleton()`. The JS and Python implementations must agree on
   every entry of the shared fixture file.
3. **Prefix monotonic.** For any string `b` and character `x`, every key of
   `skeleton(b + x)` starts with some key of `skeleton(b)`. This holds because
   each digraph folds to the class of its own first letter (`s→S, sh→S`;
   `c→C, ch→C`; `g→G, gh→G`), apostrophes vanish, readings are chosen per
   letter, and the only forward-looking Cyrillic rules (`ъ`, `ь` before a
   vowel) either vanish or insert a letter. `suggest()` depends on this: the
   candidate set can only narrow as the user types.
4. **Script-blind.** For every lexicon word `w`, under every option combination:
   `key(w) ∈ skeleton(convert(w,'new','old'), 'latin')` and
   `key(w) ∈ skeleton(convert(w,'new','cyrillic'), 'cyrillic')`.

### 4.6 Consequences to be aware of

- **Literal `s+h`, `c+h`, `g+h`** in canonical words share a key with
  `ş`/`s`, `ç`/`c`, `ğ`/`g`: `Ishoq` and `isoq` collide. Accepted [Q4]. Such
  words are covered by §5.1: a valid token is never rewritten, and a
  protected-word list keeps names like `Ishoq` valid in every build.
- **`ng` is never a unit** [Q3]. `n` stays `n`; `g` joins `G`. `n`+`ğ` is
  produced wherever a lexicon word has it (`yongoq → yonğoq`). No
  special-casing: only one of the spellings is a word, and the lexicon knows
  which.
- **Latin/Cyrillic homoglyphs inside one token** (`тoғ` with a Latin `o`) are
  not repaired in v1; the token is script-mixed and passes through [Q7].

### 4.7 Fuzzy flags [BRIEF]

`{ fuzzyQK: false, fuzzyXH: false }`. When on, each `q`/`k` (and each `x`/`h`
symbol left after step 5) has both readings. Both flags are tested on and off;
both ship off. For Latin input they stay off: `qor/kor` and `xol/hol` are real
minimal pairs, and nothing in Latin text says which letter the writer meant.

### 4.8 Cyrillic keyboard recovery [Q6]

Uzbek is widely typed on a Russian layout, which has no `ў қ ғ ҳ`; writers
substitute `у к г х`. A Cyrillic text with none of `ў қ ғ ҳ` is itself
evidence of that layout. Latin text carries no equivalent evidence.

**Detection.** `detectScript(token)` is `'cyrillic'` if every letter is
Cyrillic, `'latin'` if every letter is Latin, `'mixed'` otherwise (§3.3).

**Rule.** Option `cyrillicKeyboardRecovery`, **default `true`**. For Cyrillic
input, step 3 reads:

| Cyrillic | Readings | Note |
|---|---|---|
| `у` | `u`, `ö` | |
| `к` | `k`, `q` | |
| `х` | `x`, `h` | an `h` reading can form a digraph in step 5: `исхок` → `ishoq` → `iSOq` |
| `г` | `g` | already in class `G` with `ğ` |
| `о` | `o` | already in class `O` with `ö` |

Latin input keeps the narrow classes.

| Input | Keys | Word found |
|---|---|---|
| `тугри` | `tuGri`, `tOGri` | `töğri` |
| `кушик` | 8 keys, `kuSik` … `qOSiq` | `qöşiq` (`qOSiq`) |

**Lookup.** Readings double with every `у к х`. Implementations enumerate them
by descending the key-sorted index one symbol at a time, discarding a branch as
soon as its prefix matches no word. A branch that does match is never
discarded: there is no cap, so recall is never silently truncated.

---

## 5. The invariant

> A correction is permitted **if and only if**
> `key(candidate) ∈ skeleton(input, detectScript(input), opts)`.
> Otherwise the input token is returned **unchanged, byte-identical.**

For Latin input with the fuzzy flags off — the default — the skeleton has one
element and this is exactly the brief's
`skeleton(input) === skeleton(candidate)`. The only default widening is the
one ruled for Cyrillic input (§4.8).

Enforced in three places, not one:

1. **By construction** — candidates are only ever fetched by key.
2. **By a runtime guard** — immediately before a token is emitted,
   `autocorrect()` checks `key(output) ∈ skeleton(input)`; on failure it emits
   the input bytes. This is cheap and survives future refactors of the ranking
   code.
3. **By tests** — `tests/invariant.test.js` (10 000 informal strings, byte
   identity) and a property test over the golden file.

"Unchanged" means the exact input code units, including decomposed accents,
non-canonical apostrophes and original case. A token whose chosen word renders
to the same letters is never re-encoded (e.g. `ma'no` stays `ma'no`, §7.3
step 6).

**We correct orthography. We never touch morphology, dialect, or voice.**

### 5.1 Valid tokens are never rewritten [Q4]

A token is *valid* if one of its readings is a word: a lexicon word, a protected
word, or a word learned on the device.

| Script | Readings, in order |
|---|---|
| Latin | 1. **literal** — NFC, lowercase, every apostrophe-like → `ʼ` (`Ishoq → ishoq`, `ma'no → maʼno`) · 2. **old** — §6.3 (`shok → şok`, `to'g'ri → töğri`) |
| Cyrillic | the §6.1 transliteration, narrow (no recovery readings) |

The first reading that is a word is chosen and **no candidates are
considered**. Choosing the old reading is script conversion, not correction.
Only a token with no valid reading goes to candidate lookup and ranking (§8).

| Input | Result | Why |
|---|---|---|
| `sok` | `sok` | literal reading is a word |
| `Ishoq` | `Ishoq` | literal reading is a word (protected) |
| `shok` | `şok` | old reading is a word |
| `to'g'ri` | `töğri` | old reading is a word |
| `togri` | `töğri` | no valid reading → candidates |
| `кул` | `kul` | Cyrillic reading is a word, although `қўл` is far more frequent |

**Protected words.** `data/protected-words.txt`, one canonical word per line,
human-reviewed. Every entry is forced into both lexicon builds with the
`PROTECTED` word flag (§9.3), so it is always valid. The seed list is words
with a literal `s+h`, `c+h` or `g+h` (`Ishoq`, `Ishoqov`, …), generated from
the corpus and not used until reviewed.

**Consequence [Q19].** When the bare spelling of an ambiguity pair is itself a
word (`sok`/`şok`, `oz`/`öz`), `autocorrect()` always keeps the bare word.
Sentence context decides only in `suggest()` and for tokens with no valid
reading.

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
  cyrillicKeyboardRecovery: true,   // [RULED, Q6] §4.8
  maxSuggestions: 3,
  loader: undefined,         // [RULED] async (url) => ArrayBuffer   §7.1
  userModel: undefined,      // [RULED] object from a previous export() §7.5
  clock: undefined,          // [RULED] () => ms since epoch; default Date.now
});
```

### 7.1 `await c.load(source)` → `void`

`source` is an `ArrayBuffer`, a `Uint8Array`, or a URL string.

**Conflict in the brief, resolved [RULED, Q10]:** the brief shows
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
- Candidates: lexicon and user words whose key **starts with** a key of
  `skeleton(buffer)` (prefix monotonicity, §4.5). Evidence (§8.2) is computed
  over the typed positions only.
- Empty `buffer` with a `prevWord`: next-word prediction from bigrams.
- Returns at most `maxSuggestions`, best first, `word` rendered in `script`
  with the buffer's case pattern.
- `source`, by precedence: `'exact'` — the candidate is a valid reading of
  the buffer (§5.1); `'user'` — the
  user bonus term is non-zero; `'bigram'` — the bigram term is non-zero;
  `'lexicon'` — otherwise.

### 7.3 `c.autocorrect(text)` → `string`

1. Tokenize (§3). Gaps and protected spans are copied through.
2. Detect each token's script (§4.8). `mixed` → emit the input bytes.
3. **Valid token** (§5.1) → the chosen word is its first valid reading.
4. Otherwise fetch candidates: every word whose key is in
   `skeleton(token, script, opts)`. None → emit the input bytes.
5. Rank (§8). `prevWord` is the previous token's chosen word, reset after
   `. ! ? …` and newlines.
6. Render the chosen word in `script` with the input's case pattern. If the
   rendered string has the same letters as the input — all apostrophe-likes
   compared as equal — emit the input bytes.
7. Runtime invariant guard (§5).

The engine does **not** learn from `autocorrect()`. Learning is explicit.

Step 3 supersedes the margin rule approved under Q11: a word the user typed is
never replaced, however frequent the alternative.

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
  which keeps the frozen method list unchanged. [RULED]
- Never transmitted. There is no network code in `engine/` (§7.1).

### 7.6 `c.stats()` → `{ lexiconSize, memoryBytes, loadMs }`

`lexiconSize` = word count N. `memoryBytes` = lexicon `ArrayBuffer` +
derived typed arrays + an estimate of the user model. `loadMs` = wall time of
the last `load()` excluding the host loader. Real heap is measured separately
in `tests/perf.test.js` with `process.memoryUsage()`.

---

## 8. Ranking

Ranking orders the candidates of a token with no valid reading (§5.1), and the
suggestions of `suggest()`.

### 8.1 Score

```
score(cand | input, prevWord) =
        ln(unigram(cand))
      + λ · ln(bigram(prevWord, cand) + 1)
      + μ · user_bonus(cand)
      + ν · evidence(input, cand)
```

The brief's `− ν · edit_distance` is replaced by `+ ν · evidence` [Q12].
λ=2.0 and μ=3.0 as in the brief; ν starts at the brief's 0.5 and is tuned
against `tests/golden.json`. Every tunable lives in `engine/constants.js` and
nowhere else:

| Constant | Start | Meaning |
|---|---|---|
| `LAMBDA_BIGRAM` | 2.0 | λ |
| `MU_USER` | 3.0 | μ |
| `NU_EVIDENCE` | 0.5 | ν |
| `REGISTER_MIX` | 0.5 | weight of the informal table in `unigram()` |
| `USER_ONLY_LN_UNIGRAM` | 0 | `ln unigram` of a word known only from `learn()` |
| `USER_HALF_LIFE_MS` | 30 days | §7.5 |
| `USER_MAX_WORDS` | 5000 | §7.5 |

`unigram(w) = exp((1−REGISTER_MIX)·ln c_all(w) + REGISTER_MIX·ln c_inf(w))`,
falling back to `c_all` when the word never occurs in the informal slice. Counts
come from the quantized tables in §9.

### 8.2 Evidence [Q12]

Input and candidate share a key, so they align symbol by symbol.
`evidence(input, cand)` is the sum over aligned positions of:

- **+1** — the input used a marked spelling that denotes the candidate's
  letter (`sh` for `ş`).
- **0** — the input used a bare spelling that the writer's keyboard could not
  have marked (`s` on a Latin keyboard; `о`, `у`, `г`, `к`, `х` on a Russian
  one).
- **−1** — the input contradicts the candidate: a marked spelling of a
  different letter (`sh` against `s`), or a bare spelling on a keyboard that
  *could* have marked the letter (Cyrillic `с` against `ş`: every Cyrillic
  layout has `ш`).

Latin input:

| Candidate | +1 | 0 | −1 |
|---|---|---|---|
| `ş` | `ş` `sh` `w` | `s` | — |
| `s` | — | `s` | `ş` `sh` `w` |
| literal `s+h` | `s`A`h` | `sh` | `s` `ş` `w` |
| `ç` | `ç` `ch` | `c` | — |
| `c` | — | `c` | `ç` `ch` |
| `ö` | `ö` `o`A `ó` `ő` | `o` | — |
| `o` | — | `o` | `ö` `o`A `ó` `ő` |
| `ğ` | `ğ` `g`A `gh` `ǵ` | `g` | — |
| `g` | — | `g` | `ğ` `g`A `gh` `ǵ` |
| `q` `k` `x` `h` (fuzzy flags on) | the same letter | — | the other letter |

Cyrillic input:

| Candidate | +1 | 0 | −1 |
|---|---|---|---|
| `ş` | `ш` | — | `с` |
| `s` | `с` | — | `ш` |
| literal `s+h` | `сҳ` | `сх` | `с` `ш` |
| `ç` | `ч` | — | — |
| `ö` | `ў` | `о` `у` | — |
| `o` | — | `о` | `ў` |
| `u` | — | `у` | — |
| `ğ` | `ғ` | `г` | — |
| `g` | — | `г` | `ғ` |
| `q` | `қ` | `к` | — |
| `k` | — | `к` | — |
| `h` | `ҳ` | `х` | — |
| `x` | — | `х` | — |

Tutuq, both scripts. An apostrophe-like after `o`/`g` counts toward the letter
when the candidate has `ö`/`ğ` there, and toward the tutuq otherwise:

| Candidate | Input has an apostrophe-like / `ъ` there | Input has none |
|---|---|---|
| has `ʼ` | +1 | 0 |
| has no `ʼ` | −1 | 0 |

Every other aligned position contributes 0. Examples (tokens with no valid
reading): `wunaqa → şunaqa` +1; `tog'ri → töğri` +1; `тугри → töğri` 0;
`isoq → ishoq` −1.

### 8.3 Genuine ambiguities

Resolved by the bigram term — among the candidates of a token with no valid
reading, and in `suggest()` ordering. Because of §5.1, `autocorrect()` never
replaces a bare spelling that is itself a word [Q19]. The fixture list is in
`docs/AMBIGUITY-REVIEW.md`; no row enters tests or the benchmark until the
human has marked it.

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
| 4 | `WFLAGS` | `u8 × N` — bit0 `CAPITALIZED`: ≥ 90 % of corpus occurrences start uppercase (proper nouns; used by `suggest()` only) · bit1 `PROTECTED`: listed in `data/protected-words.txt` (§5.1) |
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

### 9.6 Lexicon admission [Q17]

**`uz-books-v2` is the authority on what is a word.** `uz-crawl` contributes
frequency weight and the informal passthrough set (§9.7). A crawl form enters
the lexicon on its own only if it carries a mark.

Why: crawl text is full of `togri`, `ozbek`, `sosib`. Under §5.1 such a form in
the lexicon would be a valid token and would block the very correction the
engine exists for.

A canonical form is *marked* if it contains at least one of `ş ç ö ğ ʼ`.
Counts are over canonical lowercase forms; `MIN_COUNT` = 2 (hapax dropped).

1. A **marked** form is admitted if `books + crawl ≥ MIN_COUNT` — from either
   source.
2. An **unmarked** form is admitted only if `books ≥ MIN_COUNT`.
3. In addition, an unmarked form `f` that is a *stripped variant* of an
   admitted marked form `g` with the same key — `f` is `g` with `ş→s|w`,
   `ç→c`, `ö→o`, `ğ→g` and `ʼ` deleted — is admitted only if
   `books(f) ≥ BOOK_MIN_RATIO · books(g)` for the most frequent such `g`.
   `BOOK_MIN_RATIO` = 0.01, a build constant in `tools/`. Book text is OCR of
   edited prose; a stripped spelling that survives there at under 1 % of the
   marked one is OCR noise, not a word.
4. Forms shorter than 2 letters are dropped, except `u o e a` [Q18].
5. Protected words (§5.1) are always admitted.
6. A rejected form that is a stripped variant of an admitted form with the same
   key has its counts (all, informal, bigrams) merged into the most frequent
   such form. Other rejected forms are dropped.

Every rejection and merge is written to `data/merges.tsv` (gitignored) and
summarized at checkpoint 2.

### 9.7 Informal passthrough set

Surface forms (exact code units) from the `telegram_blogs` split with count ≥ 2
that are not admitted and whose skeleton, with default options, contains no key
of the lexicon build under test. `tests/invariant.test.js` samples 10 000 of
them. Informal forms that are not admitted **but do match** a word form the
risk list: each is a place where `autocorrect()` would change something a
person actually wrote. A sample goes to the human at checkpoint 2.

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

## Appendix A — ambiguity fixtures

Moved to `docs/AMBIGUITY-REVIEW.md`. Rulings so far [Q13]: `ser` keeps three
candidates (`ser` / `şer` / `şeʼr`); `gor`, `kop` and `boli`/`böli` are
dropped; the fixture is rebuilt from the 24 proposed pairs, **none of which is
approved** until the human marks each row keep / fix / drop.
