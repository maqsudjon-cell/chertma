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

### Q26 — Served size of the lexicon · OPEN (step 6)

The §6 budgets are gzipped sizes. GitHub Pages likely serves `.bin` as
`application/octet-stream` without compression, so browsers would download
the raw size. Option for step 6: publish `lexicon-lite.bin.gz` and inflate it
with the browser's built-in `DecompressionStream` — no dependency. To verify
at deploy.

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
the commonest words — including the brief's own `тугри → töğri`. Rule 3 only
looks at marks, not `u/ö`, `k/q`, `x/h`.

**Option:** extend rule 3 to those substitutions. `docs/CHECKPOINT-2.md` shows
the effect at 1 %, 5 % and 10 % and the words closest to each threshold, which
is where real words (`uz`, `kul`, `tur`) would be wrongly rejected. `tugri`
needs 5 % or more.
**Needs:** ruling, and a ratio. Blocks step 4.

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
