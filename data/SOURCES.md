# Data sources

Every corpus input to the lexicon, with its origin and licence. Licences are
copied from each dataset card at the pinned revision; they are the licences the
publisher declares for the dataset.

| Input | Revision | Licence (dataset card) | Used for |
|---|---|---|---|
| [`tahrirchi/uz-books-v2`](https://huggingface.co/datasets/tahrirchi/uz-books-v2), split `lat` (38 339 books, 26 parquet shards, 6.79 GB) | `aac9c105622abf1b554640793d1fe17ab2ff28d9` | **MIT** | The authority on what is a word (SPEC §9.6); unigram and bigram counts |
| [`tahrirchi/uz-crawl`](https://huggingface.co/datasets/tahrirchi/uz-crawl), split `news` (1 250 018 articles, 7 shards, 1.50 GB) | `8fff2d17bb2607c5d875199c8a7256a4a7ce7e39` | **Apache-2.0** | Frequency weight; marked forms may enter the lexicon |
| [`tahrirchi/uz-crawl`](https://huggingface.co/datasets/tahrirchi/uz-crawl), split `telegram_blogs` (368 017 posts, 1 shard, 0.18 GB) | same | **Apache-2.0** | Frequency weight; the separate informal table (`INF_Q`); the informal passthrough set (§9.7) |
| `tahrirchi/uz-books` (v1) | — | Apache-2.0 | **Not used.** v2 is sufficient. |

Every shard is downloaded by `tools/fetch_corpus.py` over HTTPS from the pinned
revision and verified against the sha256 the Hub publishes before it is read.

## What the cards say, and what they don't

- **uz-books-v2** — "Books were collected from various public sources and
  processed using Google Cloud Vision OCR", then "`lat` and `cyr` splits were
  generated using curated transliteration scripts." The card does not say
  which books were originally Latin and which Cyrillic, so neither split is
  pure original text. The card's MIT licence covers the dataset; the card does
  not document the rights status of the underlying books. Chertma ships only
  derived word and word-pair frequencies from it, never running text.
- **uz-crawl `telegram_blogs`** — the card: "manually curated texts from 128
  high-quality Telegram channels." This is **channel and blog posts, not chat**.
  Measured on the whole split (posts of 20+ words): 196 818 are Cyrillic with
  ў қ ғ ҳ, 57 478 Latin with oʻ/gʻ marks, 962 Latin without any oʻ/gʻ, and 248
  Cyrillic typed on a Russian layout — about 0.5 % of posts are
  keyboard-limited. It is the most informal slice available, but it is not the
  dialect-and-slang register the brief expected (docs/OPEN-QUESTIONS.md Q23).
- **uz-crawl `news`** — "crawled from 57 different websites using Scrapy".

## Derived files

| File | Committed | Contents |
|---|---|---|
| `data/uz-unigrams.tsv` | no (gitignored) | canonical form, books / news / telegram counts, title-case and lower-case occurrence counts; count ≥ 2 |
| `data/uz-bigrams.tsv` | no (gitignored) | bigram counts ≥ 2 over the provisional vocabulary |
| `data/build-report.json` | yes | every number in `docs/CHECKPOINT-2.md` |
| `data/merges.tsv` | no (gitignored) | every rejected form and the word its counts were merged into (§9.6) |
| `data/lexicon-lite.bin` | yes | SPEC §9 lite lexicon: the checkpoint-2 word list (50 000 by total count) plus the suffix section |
| `data/lexicon-full.bin` | yes | 400 000 words, 2 000 000 bigrams, suffix section; built by `tools/build_lexicons.py` with the held-out documents removed |
| `data/lexicon-lite-coverage.bin` | yes | **parked**: 50 000 words chosen by crawl coverage; not used until reviewed (docs/FOR-MAQSUDJON.md) |
| `data/lexicon-build-report.json` | yes | held-out subtraction, builds, sizes, coverage on held-out text |
| `data/suffix-chains.txt` | yes | the 2 232 suffix chains in section 9 |
| `data/heldout/` | no (gitignored) | held-out word counts: 10 % of telegram_blogs and of news shard 2 (sha1 rule) |
| `data/protected-words.txt` | yes | human-reviewed protected words (§5.1) |
