# Open questions

Every linguistic or design question that could not be settled from `CLAUDE.md`
alone. When a question is answered, `docs/SPEC.md` is amended and the entry is
marked closed with the ruling. Nothing is decided silently in code.

Status: `OPEN` = needs the human · `CLOSED` = ruled (date).

---

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
**Needs:** confirm after seeing the measured cost at checkpoint 2 (how often
informal text uses a bare spelling whose marked sibling is far more frequent).
Blocks step 4 (engine), not step 2.

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
