"""Admit words, pack the binary lexicons, verify them, write the report.

Steps 4–5 of the pipeline (CLAUDE.md §6):
  - SPEC §9.6 admission (books are the authority on what is a word)
  - SPEC §9 binary format v1 → data/lexicon-lite.bin, data/lexicon-full.bin
  - an independent re-read of both files (CRC, ordering, lookups)
  - data/build-report.json: every number reported at checkpoint 2

  python tools/pack_lexicon.py
"""

import gzip
import itertools
import json
import math
import pickle
import random
import struct
import sys
import time
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.csv as pacsv

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uzscript as uz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
NGRAMS = DATA / "raw" / "ngrams"

# §9.6 admission — build constants.
MIN_COUNT = 2
BOOK_MIN_RATIO = 0.01
SHORT_WHITELIST = frozenset("uoea")
CAPITALIZED_SHARE = 0.90

# §9.5 builds and §10 budgets.
LITE_WORDS = 50_000
LITE_BIGRAMS = 200_000
LITE_BUDGET_GZ = 2_000_000
FULL_BUDGET_GZ = 8_000_000
FULL_GRID_WORDS = (100_000, 200_000, 300_000, 400_000, 600_000)
FULL_GRID_BIGRAMS = (1_000_000, 2_000_000, 3_000_000, 4_000_000, 6_000_000)
MAX_RANK = max(FULL_GRID_WORDS)
FULL_MIN_BIGRAMS = 2_000_000   # full = the most words that still fit this many bigrams, then the most bigrams
BIGRAM_LOAD_MIN = 3            # memory: pairs seen twice cannot reach the top millions of any build

# Reports.
DOMINANCE = 10          # "far more frequent": the marked sibling has ≥ 10× the count
AMBIGUITY_ROWS = [      # docs/AMBIGUITY-REVIEW.md, in table order
    ("ser", "şer", "şeʼr"),
    ("oq", "öq"), ("ot", "öt"), ("oz", "öz"), ("ol", "öl"), ("oy", "öy"), ("tor", "tör"),
    ("toq", "töq"), ("toy", "töy"), ("boy", "böy"), ("soy", "söy"), ("çol", "çöl"), ("çop", "çöp"),
    ("çok", "çök"), ("qol", "qöl"), ("bos", "boş", "böş"), ("tos", "toş", "töş"), ("qoş", "qöş"),
    ("şox", "şöx"), ("boğ", "böğ"), ("son", "şon"), ("sim", "şim"), ("is", "iş"), ("tus", "tuş"),
    ("qus", "quş"),
]
FROM_BRIEF = [("sok", "şok"), ("oç", "öç")]

MAGIC = b"CHRT"
VERSION = 1
FLAG_HAS_BIGRAMS, FLAG_HAS_INFORMAL, FLAG_WIDE_IDS, FLAG_HAS_CYR_EXC = 1, 2, 4, 8
WFLAG_CAPITALIZED, WFLAG_PROTECTED = 1, 2
CPUZ = {chr(c): c for c in range(0x61, 0x7B)}
CPUZ.update({"ş": 0x80, "ç": 0x81, "ö": 0x82, "ğ": 0x83, uz.TUTUQ: 0x84})
CPUZ_DECODE = {v: k for k, v in CPUZ.items()}


def _log(msg):
    print(time.strftime("%H:%M:%S"), msg, file=sys.stderr, flush=True)


def is_marked(w):
    return any(c in uz.MARKED for c in w)


def encode(w):
    return bytes(CPUZ[c] for c in w)


_UNMARK = {"\u015f": "s", "\u00e7": "c", "\u00f6": "o", "\u011f": "g"}


def stripped_from(g, w):
    """True if w is g with some marks removed (letters un-marked, ʼ deleted)."""
    i = j = 0
    while i < len(g):
        a = g[i]
        if j < len(w) and (w[j] == a or w[j] == _UNMARK.get(a)):
            i += 1
            j += 1
        elif a == uz.TUTUQ:
            i += 1
        else:
            return False
    return j == len(w)


# --- load ---------------------------------------------------------------------

def load_unigrams():
    uni = {}
    with open(DATA / "uz-unigrams.tsv", encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            w, b, n, t, ti, lo = line.rstrip("\n").split("\t")
            uni[w] = [int(b), int(n), int(t), int(ti), int(lo)]
    return uni


def load_protected():
    p = DATA / "protected-words.txt"
    if not p.exists():
        return set()
    out = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.add(uz.old_to_new_lower(uz.normalize(line).lower()) if "'" in line else line.lower())
    return out


# --- §9.6 admission -----------------------------------------------------------

def admit(uni, protected):
    groups = defaultdict(list)
    for w in uni:
        groups[uz.key(w)].append(w)
    admitted, reason = set(), {}
    for w, r in uni.items():
        books, crawl = r[0], r[1] + r[2]
        if len(w.replace(uz.TUTUQ, "")) < 2 and w not in SHORT_WHITELIST:
            reason[w] = "shorter-than-2"
        elif any(c not in CPUZ for c in w) or len(encode(w)) > 255:
            reason[w] = "not-packable"
        elif is_marked(w):
            if books + crawl >= MIN_COUNT:
                admitted.add(w)
            else:
                reason[w] = "rare"
        elif books >= MIN_COUNT:
            admitted.add(w)
        else:
            reason[w] = "unmarked-not-in-books"
    # Rule 3: a stripped variant — the form with some of its marks removed
    # (ş→s, ç→c, ö→o, ğ→g, ʼ deleted) — of an admitted word with more marks
    # needs BOOK_MIN_RATIO of that word's book count. Compared against the
    # rule-1/2 admission set, so the order of removal does not matter.
    base = set(admitted)
    for w in list(admitted):
        sibs = [g for g in groups[uz.key(w)] if g != w and g in base and stripped_from(g, w)]
        if sibs:
            top = max(uni[g][0] for g in sibs)
            if uni[w][0] < BOOK_MIN_RATIO * top:
                admitted.discard(w)
                reason[w] = "stripped-variant-below-ratio"
    for w in protected:
        admitted.add(w)
        reason.pop(w, None)
        uni.setdefault(w, [0, 0, 0, 0, 0])
        groups[uz.key(w)].append(w)
    # Rule 6: merge a rejected stripped variant into its most frequent source.
    merge_into = {}
    for w in reason:
        targets = [g for g in groups[uz.key(w)] if g in admitted and g != w and stripped_from(g, w)]
        if targets:
            merge_into[w] = max(targets, key=lambda g: sum(uni[g][:3]))
    return admitted, reason, merge_into, groups


# --- bigrams --------------------------------------------------------------------

def load_bigrams(rank, merge_into):
    """uz-bigrams.tsv → (ra, rb, count) sorted by count desc, over word ranks
    < MAX_RANK, with rejected forms remapped to the word they merged into."""
    import pyarrow.compute as pc

    vs_words = sorted(rank, key=rank.get)
    vs_rank = list(range(len(vs_words)))
    for w, t in merge_into.items():
        if t in rank:
            vs_words.append(w)
            vs_rank.append(rank[t])
    value_set = pa.array(vs_words)
    lookup = np.array(vs_rank + [-1], np.int64)  # index -1 → -1
    reader = pacsv.open_csv(
        DATA / "uz-bigrams.tsv",
        read_options=pacsv.ReadOptions(block_size=1 << 26),
        parse_options=pacsv.ParseOptions(delimiter="\t", quote_char=False),
        convert_options=pacsv.ConvertOptions(column_types={"w1": pa.string(), "w2": pa.string(), "count": pa.int64()}),
    )
    keys, counts, rows = [], [], 0
    for batch in reader:
        rows += batch.num_rows
        a = lookup[pc.index_in(batch.column("w1"), value_set=value_set).fill_null(-1).to_numpy()]
        b = lookup[pc.index_in(batch.column("w2"), value_set=value_set).fill_null(-1).to_numpy()]
        cnt = batch.column("count").to_numpy()
        m = (a >= 0) & (b >= 0) & (cnt >= BIGRAM_LOAD_MIN)
        keys.append((a[m] << 21) | b[m])
        counts.append(cnt[m])
    k = np.concatenate(keys) if keys else np.zeros(0, np.int64)
    c = np.concatenate(counts) if counts else np.zeros(0, np.int64)
    order = np.argsort(k, kind="stable")
    k, c = k[order], c[order]
    if len(k):
        starts = np.concatenate(([0], np.flatnonzero(np.diff(k)) + 1))
        k, c = k[starts], np.add.reduceat(c, starts)
    by_count = np.argsort(-c, kind="stable")
    return k[by_count] >> 21, k[by_count] & ((1 << 21) - 1), c[by_count], rows


# --- §9 packing -------------------------------------------------------------------

def _quant(counts, scale):
    q = np.zeros(len(counts), np.uint8)
    nz = counts > 0
    q[nz] = np.clip(np.rint(np.log(counts[nz]) * scale), 1, 255).astype(np.uint8)
    return q


def pack(words, c_all, c_inf, wflags, ba, bb, bc, corpus_tokens):
    """words: canonical list; ba/bb: indices into words; bc: counts."""
    n = len(words)
    order = sorted(range(n), key=lambda i: (uz.key(words[i]), encode(words[i])))
    new_id = np.empty(n, np.int64)
    new_id[np.array(order, dtype=np.int64)] = np.arange(n)
    words_sorted = [words[i] for i in order]
    c_all = np.asarray(c_all, np.float64)[order]
    c_inf = np.asarray(c_inf, np.float64)[order]
    wflags = np.asarray(wflags, np.uint8)[order]

    enc = [encode(w) for w in words_sorted]
    STR = b"".join(enc)
    STR_LEN = np.array([len(e) for e in enc], np.uint8)
    qs_uni = 255.0 / math.log(max(2.0, c_all.max()))
    UNI_Q = _quant(c_all, qs_uni)
    INF_Q = _quant(c_inf, qs_uni)

    a = new_id[ba]
    b = new_id[bb]
    order_b = np.lexsort((b, a))
    a, b, c = a[order_b], b[order_b], np.asarray(bc, np.float64)[order_b]
    B = len(a)
    wide = n >= 65536
    BG_OFF = np.zeros(n + 1, np.uint32)
    np.cumsum(np.bincount(a, minlength=n), out=BG_OFF[1:])
    BG_ID = b.astype(np.uint32 if wide else np.uint16)
    qs_bi = 255.0 / math.log(max(2.0, c.max() if B else 2.0))
    BG_Q = _quant(c, qs_bi)

    sections = [STR, STR_LEN.tobytes(), UNI_Q.tobytes(), INF_Q.tobytes(), wflags.tobytes(),
                BG_OFF.astype("<u4").tobytes(), BG_ID.astype("<u4" if wide else "<u2").tobytes(), BG_Q.tobytes(),
                b"", b"", b"", b""]
    table = []
    body = bytearray()
    base = 0xA0
    for s in sections:
        if not s:
            table.append((0, 0))
            continue
        while (base + len(body)) % 4:
            body.append(0)
        table.append((base + len(body), len(s)))
        body += s
    while (base + len(body)) % 4:
        body.append(0)
    flags = FLAG_HAS_BIGRAMS * (B > 0) | FLAG_HAS_INFORMAL | FLAG_WIDE_IDS * wide
    tail = b"".join(struct.pack("<II", o, ln) for o, ln in table) + bytes(body)
    crc = zlib.crc32(tail) & 0xFFFFFFFF
    header = struct.pack("<4sHHIIIffIII24s", MAGIC, VERSION, flags, n, B, 0, qs_uni, qs_bi,
                         min(corpus_tokens, 0xFFFFFFFF), int(time.time()), crc, b"\0" * 24)
    assert len(header) == 64
    return header + tail


# --- independent reader -------------------------------------------------------

def read_lexicon(buf):
    """Parse a v1 file from scratch and check every structural invariant."""
    magic, ver, flags, n, B, E, qsu, qsb, toks, built, crc = struct.unpack_from("<4sHHIIIffIII", buf, 0)
    assert magic == MAGIC and ver == VERSION, "magic/version"
    assert zlib.crc32(buf[0x40:]) & 0xFFFFFFFF == crc, "crc"
    table = [struct.unpack_from("<II", buf, 0x40 + 8 * i) for i in range(12)]
    for off, ln in table:
        assert off % 4 == 0 and off + ln <= len(buf), "section bounds"
    sec = lambda i: memoryview(buf)[table[i][0]: table[i][0] + table[i][1]]  # noqa: E731
    lens = np.frombuffer(sec(1), np.uint8)
    assert len(lens) == n
    offs = np.zeros(n + 1, np.int64)
    np.cumsum(lens, out=offs[1:])
    s = bytes(sec(0))
    assert offs[-1] == len(s), "STR length"
    words = ["".join(CPUZ_DECODE[x] for x in s[offs[i]:offs[i + 1]]) for i in range(n)]
    keys = [(uz.key(w), encode(w)) for w in words]
    assert all(keys[i] < keys[i + 1] for i in range(n - 1)), "skeleton order"
    wide = bool(flags & FLAG_WIDE_IDS)
    bg_off = np.frombuffer(sec(5), "<u4")
    bg_id = np.frombuffer(sec(6), "<u4" if wide else "<u2")
    assert len(bg_off) == n + 1 and bg_off[-1] == B == len(bg_id), "bigram offsets"
    assert np.all(np.diff(bg_off.astype(np.int64)) >= 0)
    for i in range(n):
        g = bg_id[bg_off[i]:bg_off[i + 1]]
        if len(g) > 1:
            assert np.all(np.diff(g.astype(np.int64)) > 0), "bigram group order"
    assert (len(bg_id) == 0) or int(bg_id.max()) < n
    return {"n": n, "bigrams": B, "flags": flags, "words": words, "uni_q": np.frombuffer(sec(2), np.uint8),
            "inf_q": np.frombuffer(sec(3), np.uint8), "wflags": np.frombuffer(sec(4), np.uint8),
            "bg_off": bg_off, "bg_id": bg_id, "bg_q": np.frombuffer(sec(7), np.uint8), "qs_uni": qsu, "qs_bi": qsb}


def lookup_key(lex, k):
    """All words whose key equals k — binary search on the key order."""
    words = lex["words"]
    lo, hi = 0, len(words)
    while lo < hi:
        mid = (lo + hi) // 2
        if uz.key(words[mid]) < k:
            lo = mid + 1
        else:
            hi = mid
    out = []
    while lo < len(words) and uz.key(words[lo]) == k:
        out.append(words[lo])
        lo += 1
    return out


def gz_size(buf):
    return len(gzip.compress(buf, compresslevel=9, mtime=0))


# --- what-if analyses (reported, not applied) ---------------------------------------

_KB = {"u": "\u00f6", "k": "q", "x": "h"}             # Russian-layout substitutes (Q6)
_MARKABLE = {"o": "\u00f6", "g": "\u011f", "s": "\u015f", "c": "\u00e7"}
WHATIF_RATIOS = (0.01, 0.05, 0.10)


def _kb_variants(w, limit=512):
    """Spellings of w with at least one u/k/x replaced by ö/q/h, optionally
    combined with restored marks (tugri → töğri)."""
    opts = []
    for ch in w:
        if ch in _KB:
            opts.append((ch, _KB[ch]))
        elif ch in _MARKABLE:
            opts.append((ch, _MARKABLE[ch]))
        else:
            opts.append((ch,))
    if math.prod(len(o) for o in opts) > limit:
        return []
    out = []
    for p in itertools.product(*opts):
        v = "".join(p)
        if v != w and any(w[i] in _KB and v[i] != w[i] for i in range(len(w))):
            out.append(v)
    return out


def keyboard_variant_whatif(ranked, counts, uni, admitted, lite_set, cls):
    """Q29: lite words that look like a Russian-layout spelling of a far more
    frequent word (bulgan → bölgan, tugri → töğri), at several book-count
    ratios. Counted, not removed."""
    found = []
    for w in ranked[:LITE_WORDS]:
        bw = uni.get(w, [0])[0]
        best = max((g for g in _kb_variants(w) if g in admitted), key=lambda g: uni[g][0], default=None)
        if best and uni[best][0] > 0 and bw < max(WHATIF_RATIOS) * uni[best][0]:
            found.append((w, best, bw, uni[best][0], bw / uni[best][0]))
    c = cls["cyr_ru_layout"]
    sub = {"u": "u\u00f6", "o": "o\u00f6", "k": "kq", "x": "xh", "g": "g\u011f"}
    blocked = []
    for w, n in c.items():
        if w not in lite_set:
            continue
        opts = [sub.get(ch, ch) for ch in w]
        if math.prod(len(o) for o in opts) > 256:
            continue
        good = [v for v in {"".join(p) for p in itertools.product(*opts)} - {w} if v in lite_set]
        if good:
            g = max(good, key=lambda x: sum(counts[x][:3]))
            if sum(counts[g][:3]) >= DOMINANCE * sum(counts[w][:3]):
                blocked.append((w, n))
    out = {"cyr_ru_layout_blocked_now": sum(n for _, n in blocked), "by_ratio": []}
    for r in WHATIF_RATIOS:
        gone = {f[0] for f in found if f[4] < r}
        rows = sorted((f for f in found if f[4] < r), key=lambda f: -sum(counts[f[0]][:3]))
        out["by_ratio"].append({
            "ratio": r, "lite_forms": len(gone), "token_mass": sum(sum(counts[w][:3]) for w in gone),
            "cyr_ru_layout_blocked_after": sum(n for w, n in blocked if w not in gone),
            "top": [[w, g, bw, bg, round(q, 4)] for w, g, bw, bg, q in rows[:30]],
            "near_threshold": [[w, g, bw, bg, round(q, 4)] for w, g, bw, bg, q in
                               sorted((f for f in found if f[4] < r), key=lambda f: -f[4])[:30]],
        })
    return out


_MARK_OF = {"\u015f": "s", "\u00e7": "c", "\u00f6": "o", "\u011f": "g"}


def _contradicts(reading, cand, cyrillic):
    """Q28: does cand drop a mark (or tutuq) the input spelled out, or — for
    Cyrillic — put ş where the writer typed с? Letters are compared after
    removing ʼ; a tutuq the input has and the candidate lacks also counts."""
    r = reading.replace(uz.TUTUQ, "")
    c = cand.replace(uz.TUTUQ, "")
    if len(r) != len(c):
        return False
    for a, b in zip(r, c):
        if a in _MARK_OF and b == _MARK_OF[a]:
            return True
        if cyrillic and a == "s" and b == "\u015f":
            return True
    return reading.count(uz.TUTUQ) > cand.count(uz.TUTUQ)


def veto_whatif(risk, lite_set):
    vetoed, kept = [], []
    for s, n, hits in risk:
        if not hits:
            continue
        low = uz.normalize(s).lower()
        cyr = uz.detect_script(low) == "cyrillic"
        reading = uz.cyr_to_new_lower(low) if cyr else uz.old_to_new_lower(low)
        (vetoed if _contradicts(reading, hits[0], cyr) else kept).append((s, n, hits[0]))
    return {"risk_forms": len(risk), "vetoed": len(vetoed), "still_changed": len(kept),
            "vetoed_top": vetoed[:25], "still_changed_top": kept[:25]}


def brief_examples(lite_set, full_set, counts):
    """The brief's examples through a Python approximation of §5.1 + key lookup,
    ranked by frequency only (no bigrams, no evidence). Not the engine."""
    by_key = defaultdict(list)
    for w in full_set:
        by_key[uz.key(w)].append(w)

    def correct(tok, words):
        low = uz.normalize(tok).lower()
        script = uz.detect_script(low)
        readings = [uz.cyr_to_new_lower(low)] if script == "cyrillic" else [uz.literal_lower(low), uz.old_to_new_lower(low)]
        for r in readings:
            if r in words:
                return r, "valid"
        cands = sorted({w for k in uz.skeleton(tok) for w in by_key.get(k, ()) if w in words},
                       key=lambda w: -sum(counts[w][:3]))
        return (cands[0], "corrected") if cands else (tok, "unchanged")

    lines = ["sosib pisib yozsam togri kelasizmi", "kelaslar qisela balu kettik bormimiz shoshima qoyvor",
             "togri wunaqa sosib ozbekcha тўғри", "shok", "sok", "Ishoq", "ma'no", "кул", "тугри"]
    out = {}
    for name, words in (("lite", lite_set), ("full", full_set)):
        out[name] = [[line, [correct(t, words) for t in line.split()]] for line in lines]
    return out


# --- build ------------------------------------------------------------------------

def main():
    t0 = time.time()
    rep = {}
    uni = load_unigrams()
    ng = json.loads((NGRAMS / "ngram-report.json").read_text())
    _log(f"unigrams (count >= 2): {len(uni):,}")
    protected = load_protected()
    admitted, reason, merge_into, groups = admit(uni, protected)
    rep["admission"] = {
        "input_types": len(uni),
        "admitted": len(admitted),
        "admitted_marked": sum(1 for w in admitted if is_marked(w)),
        "admitted_unmarked": sum(1 for w in admitted if not is_marked(w)),
        "rejected_by_reason": dict(Counter(reason.values())),
        "merged": len(merge_into),
        "protected_forced": len(protected),
    }
    _log(f"admitted {len(admitted):,}; merged {len(merge_into):,}")

    with open(DATA / "merges.tsv", "w", encoding="utf-8") as fh:
        fh.write("form\treason\tmerged_into\tbooks\tnews\ttelegram\n")
        for w, why in sorted(reason.items(), key=lambda kv: -sum(uni[kv[0]][:3])):
            r = uni[w]
            fh.write(f"{w}\t{why}\t{merge_into.get(w, '')}\t{r[0]}\t{r[1]}\t{r[2]}\n")

    counts = {w: list(uni[w]) for w in admitted}
    merged_mass = 0
    for w, g in merge_into.items():
        for i in range(5):
            counts[g][i] += uni[w][i]
        merged_mass += sum(uni[w][:3])
    rep["admission"]["merged_token_mass"] = merged_mass

    ranked = sorted(admitted, key=lambda w: (-sum(counts[w][:3]), w))
    for w in protected:  # protected words always inside both builds
        if w in ranked[LITE_WORDS:]:
            ranked.remove(w)
            ranked.insert(0, w)
    rank = {w: i for i, w in enumerate(ranked[:MAX_RANK])}

    def wflag(w):
        t, lo = counts[w][3], counts[w][4]
        f = WFLAG_CAPITALIZED if t + lo and t / (t + lo) >= CAPITALIZED_SHARE else 0
        return f | (WFLAG_PROTECTED if w in protected else 0)

    ba, bb, bc, bigram_rows = load_bigrams(rank, merge_into)
    rep["bigrams_input_rows"] = bigram_rows
    rep["bigrams_in_top_ranks"] = int(len(bc))
    _log(f"bigrams usable: {len(bc):,} of {bigram_rows:,} rows")

    corpus_tokens = sum(ng["stats"][s].get("words_kept", 0) for s in ng["stats"])

    def build(nw, nb):
        words = ranked[:nw]
        m = (ba < nw) & (bb < nw)
        sel = np.flatnonzero(m)[:nb]
        buf = pack(words, [sum(counts[w][:3]) for w in words], [counts[w][2] for w in words],
                   [wflag(w) for w in words], ba[sel], bb[sel], bc[sel], corpus_tokens)
        return buf, len(sel)

    lite, _ = build(LITE_WORDS, LITE_BIGRAMS)
    grid = []
    candidates = []
    for nw in FULL_GRID_WORDS:
        if nw > len(ranked):
            continue
        for nb in FULL_GRID_BIGRAMS:
            buf, got_b = build(nw, nb)
            gz = gz_size(buf)
            fits = gz <= FULL_BUDGET_GZ
            grid.append({"words": nw, "bigrams_requested": nb, "bigrams": got_b, "bytes": len(buf), "gzip": gz,
                         "fits": fits})
            _log(f"full grid N={nw:,} B={got_b:,}: {len(buf):,} B, gz {gz:,}")
            if fits:
                candidates.append((nw, got_b, gz))
            if got_b < nb or not fits:
                break
    enough = [c for c in candidates if c[1] >= FULL_MIN_BIGRAMS]
    nw, nb_, _ = max(enough or candidates, key=lambda c: (c[0], c[1]))
    best = (nw, nb_, build(nw, nb_)[0])
    full = best[2]
    (DATA / "lexicon-lite.bin").write_bytes(lite)
    (DATA / "lexicon-full.bin").write_bytes(full)

    rep["builds"] = {}
    for name, buf, budget in (("lite", lite, LITE_BUDGET_GZ), ("full", full, FULL_BUDGET_GZ)):
        lex = read_lexicon(buf)
        for probe in ("töğri", "şoşib", "özbekça", "kelasizmi"):
            assert (probe in lookup_key(lex, uz.key(probe))) == (probe in set(lex["words"])), probe
        gz = gz_size(buf)
        rep["builds"][name] = {"words": lex["n"], "bigrams": lex["bigrams"], "bytes": len(buf), "gzip": gz,
                               "budget_gzip": budget, "within_budget": gz <= budget,
                               "wide_ids": bool(lex["flags"] & FLAG_WIDE_IDS),
                               "est_runtime_bytes": len(buf) + 4 * (lex["n"] + 1)}
        rep["builds"][name]["_lex"] = lex
    rep["full_grid"] = grid

    # Coverage: share of counted tokens whose canonical form is a lexicon word.
    cov = {}
    for name in ("lite", "full"):
        ws = set(rep["builds"][name]["_lex"]["words"])
        row = {}
        for i, src in enumerate(("books", "news", "telegram")):
            total = sum(r[i] for r in uni.values())
            inlex = sum(r[i] for w, r in uni.items() if w in ws)
            fixable = sum(r[i] for w, r in uni.items() if w not in ws and merge_into.get(w) in ws)
            row[src] = {"tokens_count_ge2": total, "in_lexicon": inlex / total if total else 0,
                        "stripped_variant_of_lexicon_word": fixable / total if total else 0}
        cov[name] = row
    rep["coverage"] = cov

    with open(NGRAMS / "vocab.pkl", "rb") as fh:
        prov = set(pickle.load(fh))
    full_words = rep["builds"]["full"]["_lex"]["words"]
    rep["full_words_without_bigram_ids"] = sum(1 for w in full_words if w not in prov)

    # Protected-word seed: literal s+h / c+h / g+h (§5.1). Not used until reviewed.
    seeds = sorted((w for w in uni if ("sh" in w or "ch" in w or "gh" in w)), key=lambda w: -sum(uni[w][:3]))
    with open(DATA / "protected-words.candidates.tsv", "w", encoding="utf-8") as fh:
        fh.write("word\tbooks\tnews\ttelegram\ttitle_share\tadmitted\n")
        for w in seeds:
            r = uni[w]
            share = r[3] / (r[3] + r[4]) if r[3] + r[4] else 0
            fh.write(f"{w}\t{r[0]}\t{r[1]}\t{r[2]}\t{share:.2f}\t{int(w in admitted)}\n")
    rep["protected_candidates"] = {"count": len(seeds), "top": seeds[:25]}

    # Crawl-only partially marked forms (admitted by rule 1) that shadow a far
    # more frequent fully marked sibling — e.g. toğri next to töğri.
    partial = []
    for w in admitted:
        if not is_marked(w) or uni.get(w, [0])[0] >= MIN_COUNT:
            continue
        for g in groups[uz.key(w)]:
            if g != w and g in admitted and stripped_from(g, w) \
                    and sum(counts[g][:3]) >= DOMINANCE * sum(counts[w][:3]):
                partial.append((w, g, sum(uni[w][:3]), sum(counts[g][:3])))
                break
    partial.sort(key=lambda x: -x[2])
    rep["partial_mark_forms"] = {"count": len(partial), "token_mass": sum(p[2] for p in partial),
                                 "in_lite": sum(1 for p in partial if p[0] in rank and rank[p[0]] < LITE_WORDS),
                                 "top": partial[:25]}

    # Cost of §5.1 (Q19): valid bare spellings with a far more frequent marked sibling.
    lite_set = set(rep["builds"]["lite"]["_lex"]["words"])
    lite_by_key = defaultdict(list)
    for w in lite_set:
        lite_by_key[uz.key(w)].append(w)
    with open(NGRAMS / "class-unigrams.pkl", "rb") as fh:
        cls = pickle.load(fh)

    def latin_cost(c):
        total = sum(c.values())
        blocked, fixed, ex = 0, 0, Counter()
        for w, n in c.items():
            sibs = [g for g in lite_by_key.get(uz.key(w), ()) if g != w and stripped_from(g, w)]
            if not sibs:
                continue
            g = max(sibs, key=lambda x: sum(counts[x][:3]))
            if w in lite_set:
                if sum(counts[g][:3]) >= DOMINANCE * sum(counts[w][:3]):
                    blocked += n
                    ex[(w, g)] = n
            else:
                fixed += n
        return {"tokens": total, "blocked": blocked, "corrected": fixed,
                "blocked_top": [[w, g, n] for (w, g), n in ex.most_common(20)]}

    def cyr_cost(c):
        total = sum(c.values())
        blocked, fixed, ex = 0, 0, Counter()
        sub = {"u": "uö", "o": "oö", "k": "kq", "x": "xh", "g": "gğ"}
        for w, n in c.items():
            opts = [sub.get(ch, ch) for ch in w]
            if math.prod(len(o) for o in opts) > 256:
                continue
            variants = {"".join(p) for p in itertools.product(*opts)} - {w}
            good = [v for v in variants if v in lite_set]
            if not good:
                continue
            g = max(good, key=lambda x: sum(counts[x][:3]))
            if w in lite_set:
                if sum(counts[g][:3]) >= DOMINANCE * sum(counts[w][:3]):
                    blocked += n
                    ex[(w, g)] = n
            else:
                fixed += n
        return {"tokens": total, "blocked": blocked, "corrected": fixed,
                "blocked_top": [[w, g, n] for (w, g), n in ex.most_common(20)]}

    rep["q19_cost"] = {"latin_bare_docs": latin_cost(cls["latin_bare"]),
                       "cyr_ru_layout_docs": cyr_cost(cls["cyr_ru_layout"])}
    rep["doc_classes"] = ng["doc_classes"]
    rep["ngram"] = {k: v for k, v in ng.items() if k != "doc_classes"}

    # Informal passthrough set and risk list (§9.7), against the lite build.
    lite_keys = set(lite_by_key)
    passthrough, risk = [], []
    with open(NGRAMS / "telegram-surface.tsv", encoding="utf-8") as fh:
        for line in fh:
            s, n = line.rstrip("\n").split("\t")
            kind, canon, case = uz.analyze(s)
            if kind == "protected":
                continue
            low = uz.normalize(s).lower()
            script = uz.detect_script(low)
            if script == "cyrillic":
                valid = kind == "word" and canon in lite_set
            elif script == "latin":
                valid = uz.literal_lower(low) in lite_set or uz.old_to_new_lower(low) in lite_set
            else:
                continue
            if valid:
                continue
            hits = sorted({w for k in uz.skeleton(s) if k in lite_keys for w in lite_by_key[k]},
                          key=lambda x: -sum(counts[x][:3]))
            (risk if hits else passthrough).append((s, int(n), hits[:3]))
    random.seed(20260914)
    rep["informal"] = {
        "surface_forms_ge2_not_valid": len(passthrough) + len(risk),
        "passthrough": len(passthrough), "risk": len(risk),
        "risk_top": risk[:30], "risk_random": random.sample(risk, min(30, len(risk))),
        "passthrough_random": random.sample(passthrough, min(30, len(passthrough))),
    }
    with open(NGRAMS / "passthrough-lite.tsv", "w", encoding="utf-8") as fh:
        for s, n, _ in passthrough:
            fh.write(f"{s}\t{n}\n")
    with open(NGRAMS / "risk-lite.tsv", "w", encoding="utf-8") as fh:
        for s, n, hits in risk:
            fh.write(f"{s}\t{n}\t{' '.join(hits)}\n")

    # Ambiguity review: book counts per candidate.
    rep["ambiguity_counts"] = {"rows": [[[w, uni.get(w, [0])[0], sum(uni.get(w, [0, 0, 0])[:3])] for w in row]
                                        for row in AMBIGUITY_ROWS],
                               "from_brief": [[[w, uni.get(w, [0])[0], sum(uni.get(w, [0, 0, 0])[:3])] for w in row]
                                              for row in FROM_BRIEF]}

    rep["whatif_keyboard_variants"] = keyboard_variant_whatif(ranked, counts, uni, admitted, lite_set, cls)
    rep["whatif_veto"] = veto_whatif(risk, lite_set)
    rep["brief_examples"] = brief_examples(lite_set, set(rep["builds"]["full"]["_lex"]["words"]), counts)

    engine_gz = gz_size(b"".join(p.read_bytes() for p in sorted((ROOT / "engine").glob("*.js"))))
    rep["engine_gzip_so_far"] = engine_gz
    for b in rep["builds"].values():
        b.pop("_lex")
    rep["seconds"] = round(time.time() - t0)
    (DATA / "build-report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    _log(f"done in {rep['seconds']}s: lite {rep['builds']['lite']}, full {rep['builds']['full']}")


if __name__ == "__main__":
    main()
