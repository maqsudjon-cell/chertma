# Open questions

Every linguistic or design question that could not be settled from `CLAUDE.md`
alone. Each has a **provisional answer** that `docs/SPEC.md` currently follows.
Nothing here is buried in code: when a question is answered, SPEC is amended
and the entry is marked closed.

Status: `OPEN` = needs the human · `CLOSED` = answered (with date).

**Blocking checkpoint 1** — the equivalence table depends on these:
Q3, Q4, Q6, Q12, Q17.

---

## Linguistic

### Q1 — Cyrillic `ц` after a consonant · OPEN

The brief: `s` word-initially, `ts` after a vowel, exception list e.g.
`акция → aksiya`. The brief is silent on *after a consonant*, and `акция` is
only an exception if the default there is `ts`.

My understanding of the 1995 orthography rules is: `s` word-initially **and
after consonants**, `ts` after vowels — `концерт → konsert`,
`функция → funksiya`, `акция → aksiya` all follow the rule; `милиция →
militsiya`, `лицей → litsey` too.

**Provisional:** `s` after consonants. The exception list starts empty and is
filled only from reviewed diffs against `uz-books-v2` at checkpoint 2.
**Needs:** confirm the rule; confirm that word-final `ц` after a vowel
(e.g. `абзац`) is a genuine exception, and which way.

### Q2 — Cyrillic `ъ` and `ь` before iotated vowels · OPEN

The brief: `ъ → ʼ` (`маъно → maʼno`), `ь → dropped`. Russian loans break both:

| Cyrillic | Brief's table gives | Standard spelling (as I understand it) |
|---|---|---|
| объект | obʼyekt | obyekt |
| съезд | sʼyezd | syezd |
| бульон | bulon | bulyon |
| павильон | pavilon | pavilyon |

**Provisional:** `ъ` before `е ё ю я` is dropped; `ь` before `о` becomes `y`.
**Needs:** confirm, or give the preferred spellings.

### Q3 — "Never split `ng` across a correction boundary" · OPEN · blocking

Taken literally this forbids `n` + `ğ`, but real words have it:
`yongʻoq → yonğoq` (walnut), `yongʻin → yonğin` (fire),
`qoʻngʻiroq → qönğiroq` (bell). ASCII `yongoq` *should* become `yonğoq`.

**Provisional reading:** `ng` is never treated as one unit by the skeleton
(`n` stays `n`, `g` joins class `G`), and the Latin→Cyrillic converter always
emits `нг` for `ng` — never a special letter. `n`+`ğ` is allowed when a
lexicon word has it.
**Needs:** what did the rule intend? If it meant "never produce `nğ`", the
walnut/fire/bell words become uncorrectable.

### Q4 — Literal `s+h`, `c+h`, `g+h` in new Latin · OPEN · blocking

The skeleton folds `sh → S` greedily, so a canonical word with a literal s+h
(`Ishoq`, old `Isʼhoq`) has the same skeleton as `işoq` and `isoq`. Typed
`isoq` could therefore be "corrected" by inserting an `h`.

**Provisional:** accept the collision (it is what the brief's table specifies);
the pipeline counts such words at checkpoint 2. `new → old` writes a literal
s+h as `sʼh`; `old → new` turns `sʼh` into `sh`.
**Needs:** OK to accept? Alternative is a set-valued skeleton (input `sh` →
{`S`, `Sh`}), which is more exact but makes the invariant
`skeleton(candidate) ∈ skeletons(input)` instead of `===`.

### Q5 — Non-Uzbek characters in conversion · OPEN

- Cyrillic `щ ы` and other Russian-only letters: provisional — the letter is
  left unconverted (usually it means the token is Russian).
- Latin tokens containing `c` or `w` in Cyrillic output: provisional — left in
  Latin (`Windows`, `Coca-Cola`) unless the word is in the lexicon.

**Needs:** confirm.

### Q6 — Russian-layout Cyrillic · OPEN · blocking

People typing Uzbek on a Russian layout write `у` for `ў`, `к` for `қ`, `х`
for `ҳ`, `г` for `ғ`. The brief's table covers `г/ғ` and `о/ў`, but not
`у/ў` — which is the common one (`тугри` for `тўғри`). `к/қ` and `х/ҳ` are
real minimal pairs, like the Latin `q/k`, `x/h` flags.

**Provisional:** not covered in v1; `тугри` passes through unchanged.
**Needs:** should `у ↔ ў` join class `O`? (That would also make Latin `u` vs
`ö` a question, since the skeleton runs after transliteration.) Or a third
flag `fuzzyCyrRu`, off by default?

### Q13 — Ambiguity fixtures · OPEN

See SPEC Appendix A. Suspected errors in the brief's list:

- `ser`: the poem is `şeʼr` (шеър), not `şer` — so there are three candidates.
- `gor`: cave is `ğor` (ғор), not `gor`.
- `kop` and `boli`/`böli`: I cannot confirm either side as a standalone word.

Plus 24 proposed minimal pairs. **Needs:** mark each keep / fix / drop.

### Q18 — One-letter whitelist · OPEN

The brief drops tokens shorter than 2 chars "except a known whitelist".
**Provisional:** `u` (he/she/that), `o` (interjection), `e` (interjection),
`a` (interjection). **Needs:** confirm or extend.

---

## Design

### Q7 — Confusable characters · OPEN

Proposed folds beyond the brief: `ș→ş` (Romanian comma-below), `ǧ→ğ`,
`ı→i`, `İ→I`, `һ→ҳ`, `ӯ→ў`, and three more apostrophe-likes (U+02BD,
U+02BF, U+2032). Tokens mixing Latin and Cyrillic homoglyphs are not repaired
in v1. **Needs:** yes/no.

### Q8 — Protected spans · OPEN

URLs, bare domains, emails, `@mentions`, `#hashtags`, letters glued to digits
(`5ta`, `mp3`) and mixed-case tokens (`iPhone`) are never modified.
**Needs:** yes/no. (`5ta` in particular: Uzbek writes `5 ta`, but the glued
form is common in chat.)

### Q9 — Case is never changed · OPEN

`toshkent` becomes `toşkent`, not `Toşkent`. Capitalization is orthography,
but changing it is the kind of rewrite users notice and resent. `suggest()`
may still offer the capitalized form (lexicon flag `CAPITALIZED`).
**Needs:** yes/no.

### Q10 — `load(url)` vs the no-network grep · OPEN

The brief requires both `load('/data/lexicon-lite.bin')` and that `engine/`
contains no `fetch`. Provisional: the engine takes bytes, or a URL plus a
host-supplied `loader` option. **Needs:** yes/no.

### Q11 — Autocorrect margin · OPEN

Without a margin, a correctly typed `ot` (horse) is rewritten to `öt` whenever
`öt` is more frequent. Provisional: a typed word that is itself a valid word is
replaced only if the alternative wins by `AUTOCORRECT_MARGIN` (start 1.0 nats).
**Needs:** yes/no; the value is tuned on the golden file.

### Q12 — Distance = skeleton-aligned mismatches, not Levenshtein · OPEN · blocking

Levenshtein makes `shoshib → şoşib` (4) look worse than `sosib → şoşib` (2),
although `sh` is explicit evidence for `ş`. Provisional: count aligned
positions where the input's spelling does not denote the candidate's letter
(SPEC §8.2). **Needs:** yes/no.

### Q14 — No morphology in v1 · OPEN

Uzbek is agglutinative; a 50k surface-form lexicon will miss many inflected
forms, which then pass through uncorrected (safe, but a miss). Token coverage
of the lite build is reported at checkpoint 2. **Needs:** acknowledge; decide
after seeing the number.

### Q17 — Keeping misspellings out of the lexicon · OPEN · blocking

Crawl text contains `togri` often enough to enter any frequency list, and then
`togri` would protect itself from correction. Provisional rule (SPEC §9.6):
a diacritic-stripped form is admitted only if book text (Cyrillic-derived,
where these errors cannot occur) attests it; otherwise it is merged into the
marked form. **Needs:** yes/no.

---

## Process

### Q15 — Hugging Face namespace · OPEN

`huggingface.co/datasets/<HF_USERNAME>/uz-alphabet-bench` — not needed until
step 5. Not guessed.

### Q16 — Dataset licences · OPEN

`uz-books` is Apache-2.0 per the brief. `uz-crawl` and `uz-books-v2` are to be
checked individually at step 2 and recorded in `data/SOURCES.md` before any
data is used.
