"""Carve a held-out sample out of the crawl, for honest coverage numbers.

Held out: every document in uz-crawl `telegram_blogs` and in `news` shard 2
whose sha1(text) ends in a digit ≡ 0 (mod 10) — a deterministic 10 %. Their
word counts were part of data/uz-unigrams.tsv; tools/build_lexicons.py
subtracts them before any word is admitted or selected, so no build has seen
this text. Counting uses the same code as the original count
(normalize_corpus.process_document, unchanged since checkpoint 2), including
the contamination filter, so the subtraction is exact.

Writes (gitignored):
  data/heldout/heldout-telegram.tsv, heldout-news.tsv   surface, canonical, count
  data/heldout/heldout-stats.json

  tools/.venv/bin/python tools/build_heldout.py
"""

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_corpus  # noqa: E402
import normalize_corpus as nc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "heldout"
SHARDS = [("uz-crawl", "telegram_blogs", 0, "telegram"), ("uz-crawl", "news", 2, "news")]
MODULUS = 10


def held_out(text):
    return int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % MODULUS == 0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {"rule": f"sha1(text) % {MODULUS} == 0", "shards": {}}
    for dataset, split, idx, label in SHARDS:
        shard = fetch_corpus.list_shards(dataset, split)[idx]
        path = fetch_corpus.fetch_shard(dataset, shard)
        analyze = nc.Analyzer()
        counts = Counter()
        st = Counter()
        for text in nc.iter_documents(path):
            st["docs"] += 1
            if not held_out(text):
                continue
            st["held_docs"] += 1
            sents, s = nc.process_document(text, analyze)
            if not s["keep"]:
                st["held_docs_dropped"] += 1
                continue
            for sent in sents:
                for it in sent:
                    if it is not None:
                        counts[(it[0], it[1])] += 1
        st["held_tokens"] = sum(counts.values())
        st["held_surface_forms"] = len(counts)
        with open(OUT / f"heldout-{label}.tsv", "w", encoding="utf-8") as fh:
            fh.write("surface\tcanonical\tcount\n")
            for (surf, canon), n in counts.most_common():
                fh.write(f"{surf}\t{canon}\t{n}\n")
        stats["shards"][label] = {"dataset": dataset, "split": split, "shard": idx, **st}
        print(label, dict(st), file=sys.stderr, flush=True)
    (OUT / "heldout-stats.json").write_text(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
