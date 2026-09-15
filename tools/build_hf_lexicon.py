"""Build hf/uz-lexicon-skeleton/: the frequency lexicon and skeleton index.

Reads data/uz-unigrams.tsv and data/uz-bigrams.tsv (the checkpoint-2 counts)
and applies exactly the admission the engine's lexicons were built with
(tools/pack_lexicon.py admit(), SPEC §9.6): hapax legomena dropped, unmarked
forms only if attested in books, stripped variants under 1 % of their marked
word merged into it. Words are canonical new Latin, lowercase, NFC.

Writes (gitignored — too large for git):
  hf/uz-lexicon-skeleton/unigrams.tsv         word, count, skeleton
  hf/uz-lexicon-skeleton/bigrams.tsv          w1, w2, count — smallest cutoff >= 3 under the size cap
  hf/uz-lexicon-skeleton/skeleton-index.tsv   skeleton, then candidate words by frequency
  data/hf-lexicon-stats.json                  numbers the card is rendered from

  tools/.venv/bin/python tools/build_hf_lexicon.py
"""

import json
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_lexicon as pl  # noqa: E402
import uzscript as uz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "hf" / "uz-lexicon-skeleton"
BIGRAM_MIN_CUTOFF = 3
BIGRAM_SIZE_CAP = 500_000_000   # bytes; "~500 MB"
RANK_BITS = 23                  # 4.9 M words < 2^23


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    uni = pl.load_unigrams()
    log(f"unigram rows (count >= 2): {len(uni):,}")
    admitted, reason, merge_into, _ = pl.admit(uni, pl.load_protected())
    counts = {w: sum(uni[w][:3]) for w in admitted}
    for w, g in merge_into.items():
        counts[g] += sum(uni[w][:3])
    ranked = sorted(admitted, key=lambda w: (-counts[w], w))
    rank = {w: i for i, w in enumerate(ranked)}
    assert len(ranked) < (1 << RANK_BITS)
    bad = [w for w in ranked if not unicodedata.is_normalized("NFC", w) or any(c not in pl.CPUZ for c in w)]
    assert not bad, bad[:10]
    log(f"admitted {len(ranked):,}, merged {len(merge_into):,}; all NFC, canonical charset")

    # unigrams.tsv
    keys = [uz.key(w) for w in ranked]
    with open(OUT / "unigrams.tsv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("word\tcount\tskeleton\n")
        for i in range(0, len(ranked), 200_000):
            fh.write("".join(f"{w}\t{counts[w]}\t{k}\n" for w, k in zip(ranked[i:i + 200_000], keys[i:i + 200_000])))

    # skeleton-index.tsv — rows sorted by skeleton (code point order, as in the engine);
    # candidates within a row by frequency, which is `ranked` order.
    groups = defaultdict(list)
    for w, k in zip(ranked, keys):
        groups[k].append(w)
    with open(OUT / "skeleton-index.tsv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("skeleton\tcandidates\n")
        for k in sorted(groups):
            fh.write(k + "\t" + "\t".join(groups[k]) + "\n")
    sizes = [len(v) for v in groups.values()]
    multi = sum(1 for s in sizes if s > 1)
    log(f"skeletons {len(groups):,}; with 2+ candidates {multi:,}; max {max(sizes)}")

    # bigrams.tsv — remap merged forms, drop pairs outside the lexicon, sum, then cut.
    vs_words = ranked + [w for w, t in merge_into.items()]
    vs_rank = np.array(list(range(len(ranked))) + [rank[t] for t in merge_into.values()] + [-1], np.int64)
    value_set = pa.array(vs_words)
    reader = pacsv.open_csv(
        ROOT / "data" / "uz-bigrams.tsv",
        read_options=pacsv.ReadOptions(block_size=1 << 26),
        parse_options=pacsv.ParseOptions(delimiter="\t", quote_char=False),
        convert_options=pacsv.ConvertOptions(column_types={"w1": pa.string(), "w2": pa.string(), "count": pa.int64()}),
    )
    ks, cs, rows_in = [], [], 0
    for batch in reader:
        rows_in += batch.num_rows
        batch = batch.filter(pc.greater_equal(batch.column("count"), BIGRAM_MIN_CUTOFF))
        a = vs_rank[pc.index_in(batch.column("w1"), value_set=value_set).fill_null(-1).to_numpy()]
        b = vs_rank[pc.index_in(batch.column("w2"), value_set=value_set).fill_null(-1).to_numpy()]
        m = (a >= 0) & (b >= 0)
        ks.append((a[m] << RANK_BITS) | b[m])
        cs.append(batch.column("count").to_numpy()[m])
    k = np.concatenate(ks)
    c = np.concatenate(cs)
    del ks, cs
    order = np.argsort(k, kind="stable")
    k, c = k[order], c[order]
    starts = np.concatenate(([0], np.flatnonzero(np.diff(k)) + 1))
    k, c = k[starts], np.add.reduceat(c, starts)
    log(f"bigram rows read {rows_in:,}; in lexicon with count >= {BIGRAM_MIN_CUTOFF} after merges: {len(k):,}")

    wlen = np.array([len(w.encode("utf-8")) for w in ranked], np.int64)
    line = wlen[k >> RANK_BITS] + wlen[k & ((1 << RANK_BITS) - 1)] + np.floor(np.log10(c)).astype(np.int64) + 1 + 3
    header = len("w1\tw2\tcount\n")
    size_at = {}
    cutoff = None
    for t in range(BIGRAM_MIN_CUTOFF, 200):
        size_at[t] = int(line[c >= t].sum()) + header
        if size_at[t] <= BIGRAM_SIZE_CAP:
            cutoff = t
            break
    m = c >= cutoff
    k, c = k[m], c[m]
    order = np.lexsort((k, -c))
    k, c = k[order], c[order]
    a_idx = (k >> RANK_BITS).tolist()
    b_idx = (k & ((1 << RANK_BITS) - 1)).tolist()
    cl = c.tolist()
    with open(OUT / "bigrams.tsv", "w", encoding="utf-8", newline="\n") as fh:
        fh.write("w1\tw2\tcount\n")
        for i in range(0, len(cl), 500_000):
            fh.write("".join(f"{ranked[x]}\t{ranked[y]}\t{n}\n" for x, y, n in zip(a_idx[i:i + 500_000], b_idx[i:i + 500_000], cl[i:i + 500_000])))
    log(f"bigrams: cutoff count >= {cutoff}, {len(cl):,} rows")

    report = json.loads((ROOT / "data" / "build-report.json").read_text())
    st = report["ngram"]["stats"]
    example_keys = {w: uz.key(w) for w in ("sosib", "şoşib", "togri", "töğri", "oz", "tugri", "ser")}
    stats = {
        "words": len(ranked),
        "merged_forms": len(merge_into),
        "skeletons": len(groups),
        "skeletons_multi": multi,
        "max_candidates": max(sizes),
        "top_multi": sorted(((k2, v) for k2, v in groups.items() if len(v) > 1), key=lambda kv: -counts[kv[1][0]])[:15],
        "bigram_rows": len(cl),
        "bigram_cutoff": cutoff,
        "bigram_size_at_cutoff": size_at,
        "bigram_rows_read": rows_in,
        "tokens": {s: st[s]["words_kept"] for s in st},
        "tokens_total": sum(st[s]["words_kept"] for s in st),
        "examples": {w: {"skeleton": kk, "candidates": groups.get(kk, []), "counts": [counts[x] for x in groups.get(kk, [])]}
                     for w, kk in example_keys.items()},
        "tugri_count": counts.get("tugri"),
        "coverage": report["coverage"],
        "files": {f.name: f.stat().st_size for f in sorted(OUT.glob("*.tsv"))},
    }
    (ROOT / "data" / "hf-lexicon-stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    log("done: " + json.dumps(stats["files"]))


if __name__ == "__main__":
    main()
