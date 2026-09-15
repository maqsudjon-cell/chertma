# Chertma

**Type plain ASCII on an ordinary keyboard. Get correct Uzbek — new Latin, old Latin or Cyrillic.**

```
input:   togri gap, ozbekcha yozish oson
output:  töğri gap, özbekça yoziş oson          (new Latin)
         toʻgʻri gap, oʻzbekcha yozish oson     (old Latin)
         тўғри гап, ўзбекча ёзиш осон           (Cyrillic)

input:   хозир келаман, рахмат                  (typed on a Russian layout)
output:  hozir kelaman, rahmat

input:   kelaslar qisela balu kettik
output:  kelaslar qisela balu kettik            (dialect is not touched)
```

Every line above is real output of `engine/` with `data/lexicon-lite.bin`.

**Try it:** [chertma.maqsudjon.com](https://chertma.maqsudjon.com) — works offline after the first visit, sends nothing anywhere.

---

## Why

Uzbekistan is moving its Latin alphabet from `sh ch oʻ gʻ` to `ş ç ö ğ`. For
years people will write in three scripts, and no phone keyboard has the new
letters. Chertma restores what a keyboard destroyed — and nothing else.

The one rule: a correction is allowed only if the input and the corrected word
have the same *skeleton* — the word with every distinction a keyboard could
lose (`ş/sh/s/w`, `ö/oʻ/o`, `ğ/gʻ/g`, apostrophes, Cyrillic vs Latin) folded
away. If no real word shares the skeleton, the input comes back byte for byte.
We correct orthography. We never touch morphology, dialect, or voice.
Details: [`docs/SPEC.md`](docs/SPEC.md).

## Engine

Plain ES modules, zero dependencies, no DOM, no network access.

```js
import { Chertma } from './engine/index.js';

const c = new Chertma({ script: 'new' });        // 'new' | 'old' | 'cyrillic'
await c.load(bytesOfLexiconLiteBin);             // or load(url) with a `loader` option

c.autocorrect('togri gap');                      // 'töğri gap'
c.suggest('ozbe', null);                         // [{ word: 'özbekiston', score, source: 'lexicon' }, …]
c.convert('Тошкент', 'cyrillic', 'new');         // 'Toşkent'
c.learn('qisela');                               // on-device only
c.export();                                      // user model for backup
c.stats();                                       // { lexiconSize, memoryBytes, loadMs }
```

## Measured

| | Budget | Measured |
|---|---|---|
| `engine/` gzipped | ≤ 30 KB | 12.0 KB |
| `lexicon-lite.bin` gzipped (50 000 words, 200 000 bigrams) | ≤ 2 MB | 0.74 MB |
| `lexicon-full.bin` gzipped (400 000 words, 2 000 000 bigrams) | ≤ 8 MB | 7.34 MB |
| `load()` lite | < 400 ms | 38 ms |
| `suggest()` p95, cold V8, 10 000 real prefixes | < 5 ms | 1.2 ms |
| Heap growth with lite loaded | ≤ 25 MB | 19.5 MB (without forced GC; engine's own estimate 4 MB) |

Lexicon built from 1.75 billion word tokens of
[`tahrirchi/uz-books-v2`](https://huggingface.co/datasets/tahrirchi/uz-books-v2) (MIT) and
[`tahrirchi/uz-crawl`](https://huggingface.co/datasets/tahrirchi/uz-crawl) (Apache-2.0);
see [`data/SOURCES.md`](data/SOURCES.md) and [`docs/CHECKPOINT-2.md`](docs/CHECKPOINT-2.md).

Quality, measured on an unfiltered sample of real text (`npm test`, golden suite):

- Latin text with apostrophes removed: 695 corrections, **1 wrong** (99.9 % precision), 290 missed.
- Cyrillic typed on a Russian layout: 471 corrections, 14 wrong (97.1 %), 686 missed.
- Round trip new Latin → Cyrillic → new Latin holds for every lexicon word except a
  documented class (open question Q2b); uz-books-v2's own Latin and Cyrillic
  splits agree with our rules on 99.83 % of 29.9 million aligned words.

## Known limits

Chertma is conservative on purpose — a missed correction is a minor loss, a wrong
one is the failure it exists to avoid.

- A word that is already a real word is never rewritten. `sosib pisib togri`
  becomes `şoşib pisib töğri`: `pisib` ("sneaking up") is a real word, so it
  stays, even though `şoşib pişib` is the idiom. Open question Q19.
- Words the lexicon does not know stay exactly as typed, in every output script.
- Names and foreign words in capitals mid-sentence are only corrected to known
  proper nouns (`Sunday`, `Elon` stay as they are).

Every open question and every default taken is in [`docs/OPEN-QUESTIONS.md`](docs/OPEN-QUESTIONS.md).

## Repository

```
engine/      the product — plain ES modules
web/         the demo site and PWA (tools/build_site.py → _site/ → gh-pages)
tests/       node:test suites, golden file, fixtures        npm test
tools/       Python corpus pipeline and build scripts (build time only)
data/        lexicons, sources, build report
bench/       uz-alphabet-bench draft — not published, awaiting review
docs/        SPEC, open questions, status
```

## Licence

The engine and site code have no licence chosen yet. Data licences are in
[`data/SOURCES.md`](data/SOURCES.md); the JetBrains Mono font is under the SIL Open
Font License ([`web/fonts/OFL.txt`](web/fonts/OFL.txt)).

Maqsudjon Polatov · [maqsudjon.com](https://maqsudjon.com)
