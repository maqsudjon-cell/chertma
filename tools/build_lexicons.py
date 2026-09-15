"""Rebuild the shipped lexicons from the checkpoint-2 counts, with held-out text removed.

  1. data/uz-unigrams.tsv minus the held-out documents (tools/build_heldout.py),
     so no build has seen the text its coverage is measured on.
  2. SPEC §9.6 admission, unchanged (tools/pack_lexicon.py admit()).
  3. Builds:
       lite  50 000 words chosen by coverage of the crawl (news + telegram token
             counts, merged forms included), 200 000 bigrams — the mobile build
       full  400 000 words by total count, 2 000 000 bigrams — the bot
       mid   150 000 words by total count, 1 000 000 bigrams — only with --mid
     plus, for comparison only, lite chosen by total count (never written).
  4. Section 9: the suffix-chain inventory (tools/suffixes.py).
  5. Token coverage of every build on the held-out crawl text.

Writes data/lexicon-lite.bin, data/lexicon-full.bin (and data/lexicon-mid.bin),
data/lexicon-build-report.json.

  tools/.venv/bin/python tools/build_lexicons.py [--mid]
"""

import argparse
import gc
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_lexicon as pl  # noqa: E402
import suffixes as sx  # noqa: E402
import uzscript as uz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HELD = DATA / "heldout"

BUILDS = {
    "lite": {"words": 50_000, "bigrams": 200_000, "rank": "crawl", "budget_gz": 2_000_000},
    "full": {"words": 400_000, "bigrams": 2_000_000, "rank": "total", "budget_gz": 8_000_000},
    "mid": {"words": 150_000, "bigrams": 1_000_000, "rank": "total", "budget_gz": 8_000_000},
    "lite_by_frequency": {"words": 50_000, "bigrams": 0, "rank": "total", "budget_gz": 2_000_000},
}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def read_heldout():
    rows = {}
    for label in ("news", "telegram"):
        with open(HELD / f"heldout-{label}.tsv", encoding="utf-8") as fh:
            next(fh)
            rows[label] = [(s, c, int(n)) for s, c, n in (line.rstrip("\n").split("\t") for line in fh)]
    return rows


def subtract(uni, held):
    col = {"news": 1, "telegram": 2}
    stats = Counter()
    for label, rows in held.items():
        for surface, canon, n in rows:
            r = uni.get(canon)
            stats[f"{label}_tokens"] += n
            if r is None:
                stats[f"{label}_tokens_not_in_counts"] += n   # the form's total was 1: never counted
                continue
            take = min(n, r[col[label]])
            if take < n:
                stats[f"{label}_tokens_over_subtracted"] += n - take
            r[col[label]] -= take
            case = uz.case_pattern(surface)
            if case == "title":
                r[3] = max(0, r[3] - n)
            elif case == "lower":
                r[4] = max(0, r[4] - n)
    before = len(uni)
    for w in [w for w, r in uni.items() if sum(r[:3]) < pl.MIN_COUNT]:
        del uni[w]
    stats["forms_dropped_below_min_count"] = before - len(uni)
    return dict(stats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mid", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    rep = {"builds": {}, "coverage": {}}

    uni = pl.load_unigrams()
    held = read_heldout()
    rep["heldout_subtraction"] = subtract(uni, held)
    log(f"unigrams after subtracting held-out: {len(uni):,}  {rep['heldout_subtraction']}")

    protected = pl.load_protected()
    admitted, reason, merge_into, _ = pl.admit(uni, protected)
    total, crawl, tg, title, lower = {}, {}, {}, {}, {}
    for w in admitted:
        r = uni[w]
        total[w], crawl[w], tg[w], title[w], lower[w] = sum(r[:3]), r[1] + r[2], r[2], r[3], r[4]
    for w, g in merge_into.items():
        r = uni[w]
        total[g] += sum(r[:3]); crawl[g] += r[1] + r[2]; tg[g] += r[2]; title[g] += r[3]; lower[g] += r[4]
    rep["admitted"] = len(admitted)
    rep["merged"] = len(merge_into)
    del uni, reason
    gc.collect()
    log(f"admitted {len(admitted):,}, merged {len(merge_into):,}")

    chains = sx.derive(total)
    rep["suffix_chains"] = len(chains)
    log(f"suffix chains: {len(chains):,}")

    by_total = sorted(admitted, key=lambda w: (-total[w], w))
    by_crawl = sorted(admitted, key=lambda w: (-crawl[w], -total[w], w))
    wanted = ["lite", "full", "lite_by_frequency"] + (["mid"] if a.mid else [])
    words = {}
    for name in wanted:
        cfg = BUILDS[name]
        order = by_crawl if cfg["rank"] == "crawl" else by_total
        chosen = order[: cfg["words"]]
        missing = [w for w in protected if w not in set(chosen)]
        words[name] = chosen[: cfg["words"] - len(missing)] + missing
    lite_new_vs_freq = len(set(words["lite"]) - set(words["lite_by_frequency"]))
    rep["lite_words_not_in_frequency_lite"] = lite_new_vs_freq

    union = sorted(set().union(*(words[n] for n in wanted if BUILDS[n]["bigrams"])), key=lambda w: (-total[w], w))
    rank = {w: i for i, w in enumerate(union)}
    ba, bb, bc, rows = pl.load_bigrams(rank, merge_into)
    log(f"bigrams usable over {len(union):,} words: {len(bc):,} of {rows:,} rows")
    corpus_tokens = int(sum(total.values()))

    for name in wanted:
        cfg = BUILDS[name]
        ws = words[name]
        if not cfg["bigrams"]:
            continue
        local = np.full(len(union), -1, np.int64)
        local[np.array([rank[w] for w in ws], np.int64)] = np.arange(len(ws))
        la, lb = local[ba], local[bb]
        sel = np.flatnonzero((la >= 0) & (lb >= 0))[: cfg["bigrams"]]

        def wflag(w):
            t, lo = title[w], lower[w]
            f = pl.WFLAG_CAPITALIZED if t + lo and t / (t + lo) >= pl.CAPITALIZED_SHARE else 0
            return f | (pl.WFLAG_PROTECTED if w in protected else 0)

        buf = pl.pack(ws, [total[w] for w in ws], [tg[w] for w in ws], [wflag(w) for w in ws],
                      la[sel], lb[sel], bc[sel], corpus_tokens)
        buf = sx.with_section(buf, chains)
        lex = pl.read_lexicon(buf)
        assert lex["n"] == len(ws)
        gz = pl.gz_size(buf)
        (DATA / f"lexicon-{name}.bin").write_bytes(buf)
        rep["builds"][name] = {"words": lex["n"], "bigrams": lex["bigrams"], "bytes": len(buf), "gzip": gz,
                               "budget_gzip": cfg["budget_gz"], "within_budget": gz <= cfg["budget_gz"],
                               "selection": f"top by {cfg['rank']} count"}
        log(f"{name}: {lex['n']:,} words, {lex['bigrams']:,} bigrams, {len(buf):,} B, gz {gz:,}")
    del ba, bb, bc
    gc.collect()

    # Coverage on held-out crawl text.
    chain_set = set(chains)
    for name in wanted:
        ws = set(words[name])
        keys = {uz.key(w) for w in ws}
        cov = {}
        for label, rows in held.items():
            tot = inlex = keym = morph = 0
            for surface, canon, n in rows:
                tot += n
                if canon in ws:
                    inlex += n; keym += n; morph += n
                    continue
                if uz.key(canon) in keys:
                    keym += n
                if any(canon[:i] in ws and canon[i:] in chain_set
                       for i in range(sx.STEM_MIN_LETTERS, len(canon) - sx.SUFFIX_MIN_LETTERS + 1)):
                    morph += n
            cov[label] = {"tokens": tot, "in_lexicon": inlex / tot, "in_lexicon_or_skeleton_match": keym / tot,
                          "in_lexicon_or_stem_plus_suffix": morph / tot}
        rep["coverage"][name] = cov
        log(f"coverage {name}: " + ", ".join(f"{k} {100 * v['in_lexicon']:.2f} %" for k, v in cov.items()))

    lite = set(words["lite"])
    freq = set(words["lite_by_frequency"])
    rep["examples"] = {
        w: {"total": total.get(w), "crawl": crawl.get(w), "in_lite": w in lite, "in_lite_by_frequency": w in freq,
            "in_full": w in set(words["full"])}
        for w in ("işlating", "işlatiş", "işla", "töğri", "kelaslar", "qisela", "balu", "kettik", "qöyvor")
    }
    gained = sorted(lite - freq, key=lambda w: -crawl[w])
    lost = sorted(freq - lite, key=lambda w: -total[w])
    rep["lite_gained_top"] = [[w, crawl[w], total[w]] for w in gained[:40]]
    rep["lite_lost_top"] = [[w, crawl[w], total[w]] for w in lost[:40]]
    rep["seconds"] = round(time.time() - t0)
    (DATA / "lexicon-build-report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    log(f"done in {rep['seconds']} s")


if __name__ == "__main__":
    main()
