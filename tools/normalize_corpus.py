"""Normalize corpus documents to canonical new Latin.

Step 2 of the pipeline (CLAUDE.md §6). Rules live in uzscript.py; this module
applies them to whole documents and applies the brief's contamination filter:
a document is dropped when more than MAX_OUTSIDE of its word tokens fall
outside the Uzbek charset (Russian ы щ, English c w, other scripts).

Only tokens of two or more characters take part in that ratio. Measured on
uz-books-v2: with single letters counted, 7.5 % of books were dropped, and the
dropped books were overwhelmingly Uzbek maths, physics and chemistry textbooks
whose "outside" tokens were formula variables (C, W, c, α). One-letter tokens
say nothing about which language a document is in.

Nothing is written to disk here — canonical text for 40 000 books would be
tens of GB. build_ngrams.py calls process_document() and counts directly.

Inspect what normalization does to a sample:
  python tools/normalize_corpus.py uz-crawl telegram_blogs --docs 5
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uzscript as uz  # noqa: E402

MAX_OUTSIDE = 0.05       # brief §6: drop a document above 5 % outside-charset tokens
MIN_TOKENS_FOR_CLASS = 20

_CYR_UZ_ONLY = frozenset("ўқғҳЎҚҒҲ")


class Analyzer:
    """uz.analyze() with a per-process cache; corpora are Zipfian."""

    def __init__(self, max_size=3_000_000):
        self.cache = {}
        self.max_size = max_size

    def __call__(self, surface):
        r = self.cache.get(surface)
        if r is None:
            if len(self.cache) >= self.max_size:
                self.cache.clear()
            r = uz.analyze(surface, normalized=True)
            self.cache[surface] = r
        return r


def process_document(text, analyze):
    """Return (sentences, stats).

    sentences: list of lists of (surface, canonical, case) for word tokens and
    None for anything that breaks a bigram chain (protected or outside-charset
    tokens). stats: dict with token counts, the filter decision and the
    document's writing class (see doc_class()).
    """
    sentences = []
    words = outside = words2 = outside2 = 0
    for items in uz.iter_sentences(text):
        out = []
        for surface in items:
            if surface is None:
                out.append(None)
                continue
            kind, canon, case = analyze(surface)
            long_enough = len(surface) >= 2
            if kind == "word":
                words += 1
                words2 += long_enough
                out.append((surface, canon, case))
            else:
                if kind == "outside":
                    outside += 1
                    outside2 += long_enough
                out.append(None)
        sentences.append(out)
    total = words2 + outside2
    keep = total > 0 and outside2 / total <= MAX_OUTSIDE
    return sentences, {"words": words, "outside": outside, "keep": keep}


def doc_class(sentences):
    """How the document was typed, for the checkpoint report:

    latin_marked    Latin, uses oʻ/gʻ (ö/ğ) at least once
    latin_bare      Latin, never marks ö/ğ — an apostrophe-less writer
    cyr_uz          Cyrillic with at least one of ў қ ғ ҳ
    cyr_ru_layout   Cyrillic with none of ў қ ғ ҳ — typed on a Russian layout
    short           fewer than MIN_TOKENS_FOR_CLASS word tokens
    """
    n = lat = cyr = 0
    marked = uzcyr = False
    for sent in sentences:
        for it in sent:
            if it is None:
                continue
            surface, canon, _ = it
            n += 1
            if surface[0] >= "Ѐ":
                cyr += 1
                if not uzcyr and any(c in _CYR_UZ_ONLY for c in surface):
                    uzcyr = True
            else:
                lat += 1
                if not marked and ("ö" in canon or "ğ" in canon):
                    marked = True
    if n < MIN_TOKENS_FOR_CLASS:
        return "short"
    if cyr > lat:
        return "cyr_uz" if uzcyr else "cyr_ru_layout"
    return "latin_marked" if marked else "latin_bare"


def iter_documents(parquet_path, batch_size=256):
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(parquet_path)
    for batch in pf.iter_batches(batch_size=batch_size, columns=["text"]):
        for text in batch.column(0).to_pylist():
            if text:
                yield text


def main():
    import fetch_corpus

    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("split")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--docs", type=int, default=3)
    ap.add_argument("--chars", type=int, default=600)
    a = ap.parse_args()
    shard = fetch_corpus.list_shards(a.dataset, a.split)[a.shard]
    path = fetch_corpus.fetch_shard(a.dataset, shard)
    analyze = Analyzer()
    for i, text in enumerate(iter_documents(path, batch_size=8)):
        if i >= a.docs:
            break
        sents, st = process_document(text, analyze)
        canon = " / ".join(" ".join(it[1] if it else "·" for it in s) for s in sents)
        print(f"--- doc {i}: {st}, class={doc_class(sents)}")
        print("IN :", text[: a.chars].replace("\n", " ⏎ "))
        print("OUT:", canon[: a.chars])


if __name__ == "__main__":
    main()
