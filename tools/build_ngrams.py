"""Count unigrams and bigrams over the corpus.

Step 3 of the pipeline (CLAUDE.md §6). Two passes, so the books never sit on
disk in full (the machine has ~22 GB free; the books split is 6.8 GB of
parquet):

  vocab   crawl (both splits) + the first --book-shards book shards, unigrams
          only → a provisional vocabulary (canonical forms with count >= 2).
          Bigram ids in the next pass refer to it. A form missing from it loses
          only its bigrams, never its unigram count; the number of lexicon words
          affected is reported at checkpoint 2.
  count   every shard: exact unigram counts per source, capitalisation counts,
          telegram surface forms, writing-class counts, and bigram counts over
          the provisional vocabulary. A book shard is deleted once counted.
  merge   → data/uz-unigrams.tsv, data/uz-bigrams.tsv and data/raw/ngrams/*.

Resumable: a shard whose output exists is skipped.

  python tools/build_ngrams.py vocab --workers 4
  python tools/build_ngrams.py count --workers 4
  python tools/build_ngrams.py merge
"""

import argparse
import json
import pickle
import sys
import time
from array import array
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_corpus  # noqa: E402
import normalize_corpus as nc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NGRAMS = ROOT / "data" / "raw" / "ngrams"

# (dataset, split, label). Labels are the three count columns.
SOURCES = [
    ("uz-crawl", "telegram_blogs", "telegram"),
    ("uz-crawl", "news", "news"),
    ("uz-books-v2", "lat", "books"),
]
ID_BITS = 21                     # vocabulary ids < 2^21; a bigram key is id_a << 21 | id_b
MAX_VOCAB = (1 << ID_BITS) - 1
FLUSH_IDS = 16_000_000           # bigram id buffer flushed to numpy at this size
CLASS_COUNTS = ("latin_bare", "cyr_ru_layout")
CASE_CODE = {"lower": 1, "title": 2, "upper": 3}


def _log(msg):
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def _unique_sum(keys, counts):
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    counts = counts[order]
    if len(keys) == 0:
        return keys, counts
    starts = np.concatenate(([0], np.flatnonzero(np.diff(keys)) + 1))
    return keys[starts], np.add.reduceat(counts, starts)


def count_shard(job):
    dataset, split, label, idx, stage = job["dataset"], job["split"], job["label"], job["idx"], job["stage"]
    out = NGRAMS / stage / f"{label}-{idx:05d}.pkl"
    if out.exists():
        return str(out), None
    out.parent.mkdir(parents=True, exist_ok=True)
    shard = fetch_corpus.list_shards(dataset, split)[idx]
    path = fetch_corpus.fetch_shard(dataset, shard)
    t0 = time.time()

    vocab = None
    if stage == "count":
        with open(NGRAMS / "vocab.pkl", "rb") as fh:
            vocab_list = pickle.load(fh)
        vocab = {w: i for i, w in enumerate(vocab_list)}

    analyze = nc.Analyzer(max_size=500_000)
    uni, title, lower = Counter(), Counter(), Counter()   # vocab stage, and OOV forms in the count stage
    surface = Counter() if label == "telegram" else None
    cls_docs = Counter()
    cls_uni = {c: Counter() for c in CLASS_COUNTS} if label != "books" else None
    st = Counter()
    ids = array("i")   # count stage: vocab_id * 4 + case code, -1 = chain break
    parts = []
    if vocab is not None:
        V = len(vocab)
        v_uni = np.zeros(V, np.int64)
        v_title = np.zeros(V, np.int64)
        v_lower = np.zeros(V, np.int64)
        get = vocab.get

    def flush():
        nonlocal ids
        a = np.frombuffer(ids, dtype=np.int32).astype(np.int64)
        pos = a[a >= 0]
        vid, code = pos >> 2, pos & 3
        v_uni[:] += np.bincount(vid, minlength=V)
        v_title[:] += np.bincount(vid[code == CASE_CODE["title"]], minlength=V)
        v_lower[:] += np.bincount(vid[code == CASE_CODE["lower"]], minlength=V)
        x, y = a[:-1], a[1:]
        m = (x >= 0) & (y >= 0)
        k = ((x[m] >> 2) << ID_BITS) | (y[m] >> 2)
        u, c = np.unique(k, return_counts=True)
        parts.append((u, c.astype(np.int64)))
        ids = array("i")

    for text in nc.iter_documents(path, batch_size=64 if label == "books" else 512):
        sents, s = nc.process_document(text, analyze)
        st["docs"] += 1
        st["chars"] += len(text)
        st["words_seen"] += s["words"]
        st["outside_seen"] += s["outside"]
        if not s["keep"]:
            st["docs_dropped"] += 1
            st["words_dropped"] += s["words"]
            continue
        doc_words = [] if cls_uni is not None else None
        for sent in sents:
            for it in sent:
                if it is None:
                    if vocab is not None:
                        ids.append(-1)
                    continue
                surf, canon, case = it
                if surface is not None:
                    surface[surf] += 1
                if doc_words is not None:
                    doc_words.append(canon)
                if vocab is not None:
                    v = get(canon)
                    if v is not None:
                        ids.append(v * 4 + CASE_CODE[case])
                        continue
                    ids.append(-1)
                uni[canon] += 1
                if case == "title":
                    title[canon] += 1
                elif case == "lower":
                    lower[canon] += 1
            if vocab is not None:
                ids.append(-1)
                if len(ids) >= FLUSH_IDS:
                    flush()
        if cls_uni is not None:
            c = nc.doc_class(sents)
            cls_docs[c] += 1
            if c in cls_uni:
                cls_uni[c].update(doc_words)

    if vocab is not None:
        if len(ids):
            flush()
        words = vocab_list
        for i in np.flatnonzero(v_uni).tolist():
            uni[words[i]] = int(v_uni[i])
        for i in np.flatnonzero(v_title).tolist():
            title[words[i]] = int(v_title[i])
        for i in np.flatnonzero(v_lower).tolist():
            lower[words[i]] = int(v_lower[i])
        if parts:
            keys, counts = _unique_sum(np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts]))
        else:
            keys, counts = np.zeros(0, np.int64), np.zeros(0, np.int64)
        np.savez_compressed(out.with_suffix(".bigrams.npz"), keys=keys, counts=counts.astype(np.int32))
        st["bigram_types"] = int(len(keys))
        st["bigram_tokens"] = int(counts.sum())
    st["words_kept"] = sum(uni.values())

    tmp = out.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        pickle.dump({"label": label, "dataset": dataset, "split": split, "idx": idx,
                     "uni": dict(uni), "title": dict(title), "lower": dict(lower),
                     "surface": dict(surface) if surface is not None else None,
                     "cls_docs": dict(cls_docs),
                     "cls_uni": {k: dict(v) for k, v in cls_uni.items()} if cls_uni is not None else None,
                     "stats": dict(st)}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.rename(out)
    if job.get("delete_after"):
        fetch_corpus.delete_shard(dataset, shard)
    st["seconds"] = round(time.time() - t0)
    return str(out), dict(st)


def _jobs(stage, book_shards):
    jobs = []
    for dataset, split, label in SOURCES:
        n = len(fetch_corpus.list_shards(dataset, split))
        idxs = range(n)
        if stage == "vocab" and label == "books":
            idxs = range(min(book_shards, n))
        for i in idxs:
            jobs.append({"dataset": dataset, "split": split, "label": label, "idx": i, "stage": stage,
                         # vocab-stage book shards stay for the count stage; count stage deletes them
                         "delete_after": stage == "count" and label == "books"})
    return jobs


def run_stage(stage, workers, book_shards):
    jobs = _jobs(stage, book_shards)
    _log(f"{stage}: {len(jobs)} shards, {workers} workers")
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(count_shard, j): j for j in jobs}
        for f in as_completed(futs):
            j = futs[f]
            path, st = f.result()
            if st:
                _log(f"{j['label']}-{j['idx']:05d}: {st['words_kept']:,} words, "
                     f"{st['docs_dropped']}/{st['docs']} docs dropped, {st['seconds']}s")
            else:
                _log(f"{j['label']}-{j['idx']:05d}: already done")


def build_vocab():
    total = Counter()
    for p in sorted((NGRAMS / "vocab").glob("*.pkl")):
        with open(p, "rb") as fh:
            total.update(pickle.load(fh)["uni"])
    words = [w for w, c in total.most_common() if c >= 2][:MAX_VOCAB]
    with open(NGRAMS / "vocab.pkl", "wb") as fh:
        pickle.dump(words, fh, protocol=pickle.HIGHEST_PROTOCOL)
    _log(f"provisional vocabulary: {len(words):,} forms (of {len(total):,} types in the sample)")


def merge():
    shards = sorted((NGRAMS / "count").glob("*.pkl"))
    labels = ("books", "news", "telegram")
    uni = {}
    caps = {}
    surface = Counter()
    cls_docs = {lab: Counter() for lab in labels}
    cls_uni = {c: Counter() for c in CLASS_COUNTS}
    stats = {lab: Counter() for lab in labels}
    for p in shards:
        with open(p, "rb") as fh:
            d = pickle.load(fh)
        col = labels.index(d["label"])
        for w, c in d["uni"].items():
            row = uni.get(w)
            if row is None:
                row = uni[w] = [0, 0, 0]
            row[col] += c
        for w, c in d["title"].items():
            r = caps.setdefault(w, [0, 0])
            r[0] += c
        for w, c in d["lower"].items():
            r = caps.setdefault(w, [0, 0])
            r[1] += c
        if d["surface"]:
            surface.update(d["surface"])
        cls_docs[d["label"]].update(d["cls_docs"])
        if d["cls_uni"]:
            for k, v in d["cls_uni"].items():
                cls_uni[k].update(v)
        stats[d["label"]].update(d["stats"])
        stats[d["label"]]["shards"] += 1
        del d
        _log(f"merged unigrams {p.name}: {len(uni):,} types so far")

    # Hapax legomena are dropped here (brief §6); admission rules come later.
    kept = {w: r for w, r in uni.items() if sum(r) >= 2}
    n_uni_all = len(uni)
    _log(f"unigram types: {n_uni_all:,}, count >= 2: {len(kept):,}")
    with open(ROOT / "data" / "uz-unigrams.tsv", "w", encoding="utf-8") as fh:
        fh.write("word\tbooks\tnews\ttelegram\ttitle\tlower\n")
        for w, r in sorted(kept.items(), key=lambda kv: (-sum(kv[1]), kv[0])):
            t, lo = caps.get(w, (0, 0))
            fh.write(f"{w}\t{r[0]}\t{r[1]}\t{r[2]}\t{t}\t{lo}\n")
    with open(NGRAMS / "telegram-surface.tsv", "w", encoding="utf-8") as fh:
        for s, c in surface.most_common():
            if c < 2:
                break
            fh.write(f"{s}\t{c}\n")
    with open(NGRAMS / "class-unigrams.pkl", "wb") as fh:
        pickle.dump({k: dict(v) for k, v in cls_uni.items()}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    n_kept = len(kept)
    del uni, caps, surface, cls_uni, kept

    # Bigrams: k-way merge of the per-shard sorted key arrays, in key chunks
    # so memory stays bounded.
    with open(NGRAMS / "vocab.pkl", "rb") as fh:
        vocab = pickle.load(fh)
    files = sorted((NGRAMS / "count").glob("*.bigrams.npz"))
    GROUPS, CHUNKS = 8, 8
    bounds = np.linspace(0, len(vocab), GROUPS * CHUNKS + 1).astype(np.int64) << ID_BITS
    n_types = n_tokens = n_written = 0
    with open(ROOT / "data" / "uz-bigrams.tsv", "w", encoding="utf-8") as fh:
        fh.write("w1\tw2\tcount\n")
        for g in range(GROUPS):
            # Decompress each shard once per group and keep only this group's key range.
            g_lo, g_hi = bounds[g * CHUNKS], bounds[(g + 1) * CHUNKS]
            slices = []
            for f in files:
                with np.load(f) as z:
                    k, c = z["keys"], z["counts"]
                s, e = np.searchsorted(k, g_lo), np.searchsorted(k, g_hi)
                slices.append((k[s:e].copy(), c[s:e].astype(np.int64)))
                del k, c
            for ci in range(g * CHUNKS, (g + 1) * CHUNKS):
                lo, hi = bounds[ci], bounds[ci + 1]
                ks, cs = [], []
                for k, c in slices:
                    s, e = np.searchsorted(k, lo), np.searchsorted(k, hi)
                    ks.append(k[s:e])
                    cs.append(c[s:e])
                keys, counts = _unique_sum(np.concatenate(ks), np.concatenate(cs))
                n_types += len(keys)
                n_tokens += int(counts.sum())
                m = counts >= 2
                for kk, cc in zip(keys[m].tolist(), counts[m].tolist()):
                    fh.write(f"{vocab[kk >> ID_BITS]}\t{vocab[kk & MAX_VOCAB]}\t{cc}\n")
                n_written += int(m.sum())
            del slices
            _log(f"bigram group {g + 1}/{GROUPS}: {n_types:,} types so far")
    _log(f"bigram types: {n_types:,}, count >= 2 written: {n_written:,}")

    report = {
        "stats": {k: dict(v) for k, v in stats.items()},
        "doc_classes": {k: dict(v) for k, v in cls_docs.items()},
        "unigram_types_all": n_uni_all,
        "unigram_types_ge2": n_kept,
        "bigram_types_all": n_types,
        "bigram_tokens": n_tokens,
        "bigram_types_ge2": n_written,
        "provisional_vocab": len(vocab),
    }
    (NGRAMS / "ngram-report.json").write_text(json.dumps(report, indent=2))
    _log("merge done")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["vocab", "count", "merge"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--book-shards", type=int, default=3)
    a = ap.parse_args()
    if a.stage == "vocab":
        run_stage("vocab", a.workers, a.book_shards)
        build_vocab()
    elif a.stage == "count":
        run_stage("count", a.workers, a.book_shards)
    else:
        merge()


if __name__ == "__main__":
    main()
