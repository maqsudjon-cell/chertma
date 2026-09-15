"""tests/fixtures/books-pairs.tsv — aligned word pairs from uz-books-v2's lat and cyr splits.

The two splits hold the same 38 339 books, each produced by Tahrirchi's own
transliteration scripts. Shard 0 of each split starts at book 0, so row i of
lat-00000 and cyr-00000 is the same book for every row both shards contain.
A line pair is used only when both lines have the same number of word tokens;
tokens are then paired by position. Only pairs seen at least MIN_COUNT times are
kept, so OCR noise drops out. The test converts both sides with our rules and
measures how often they agree — an independent check of translit.js.

  python tools/build_books_pairs.py            # needs the two shards in data/raw
"""

import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_corpus  # noqa: E402
import uzscript as uz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MIN_COUNT = 3
KEEP = 40000


def tokens(line):
    return [line[s:e] for s, e, k in uz.spans(line) if k == "token"]


def main():
    lat_shard = fetch_corpus.list_shards("uz-books-v2", "lat")[0]
    cyr_shard = fetch_corpus.list_shards("uz-books-v2", "cyr")[0]
    lat = pq.ParquetFile(fetch_corpus.shard_path("uz-books-v2", lat_shard))
    cyr = pq.ParquetFile(fetch_corpus.shard_path("uz-books-v2", cyr_shard))
    n = min(lat.metadata.num_rows, cyr.metadata.num_rows)
    pairs = Counter()
    lines_used = lines_seen = 0
    li = lat.iter_batches(batch_size=16, columns=["text"])
    ci = cyr.iter_batches(batch_size=16, columns=["text"])
    row = 0
    for lb, cb in zip(li, ci):
        for lt, ct in zip(lb.column(0).to_pylist(), cb.column(0).to_pylist()):
            if row >= n or not lt or not ct:
                row += 1
                continue
            row += 1
            ll, cl = lt.split("\n"), ct.split("\n")
            if len(ll) != len(cl):
                continue
            for a, b in zip(ll, cl):
                lines_seen += 1
                ta, tb = tokens(a), tokens(b)
                if not ta or len(ta) != len(tb):
                    continue
                if not any(uz.detect_script(t.lower()) == "cyrillic" for t in tb):
                    continue
                lines_used += 1
                for x, y in zip(ta, tb):
                    xl, yl = uz.normalize(x).lower(), uz.normalize(y).lower()
                    if uz.detect_script(xl) == "latin" and uz.detect_script(yl) == "cyrillic":
                        pairs[(yl, xl)] += 1
        if row >= n:
            break
    kept = [(c, l, k) for (c, l), k in pairs.most_common() if k >= MIN_COUNT][:KEEP]
    out = ROOT / "tests" / "fixtures" / "books-pairs.tsv"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"# uz-books-v2 (MIT) lat-00000 / cyr-00000, rows 0..{n - 1}: {lines_used} of {lines_seen} lines aligned; "
                 f"pairs seen >= {MIN_COUNT} times, top {KEEP}\n")
        fh.write("cyr\tlat\tcount\n")
        for c, l, k in kept:
            fh.write(f"{c}\t{l}\t{k}\n")
    print(f"rows {n}, lines aligned {lines_used}/{lines_seen}, distinct pairs {len(pairs)}, kept {len(kept)}", file=sys.stderr)


if __name__ == "__main__":
    main()
