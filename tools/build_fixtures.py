"""Build test fixtures and benchmark source material from the corpus.

Needs data/raw (the crawl parquet and the checkpoint-2 ngram outputs) and
data/lexicon-lite.bin. Writes:

  tests/golden.json                    ~300 strict cases + ranked + real-world samples
  tests/fixtures/invariant-generated.txt   10 000 surface forms (Q23b)
  tests/fixtures/dialect-handwritten.json  empty placeholder for the human's 200 (Q23a)
  tests/fixtures/perf-prefixes.json    10 000 (buffer, prevWord) pairs
  data/foreign-collisions.tsv          parked: foreign tokens whose skeleton hits a word
  data/bench-pool.json                 gitignored source material for bench/review.md

The expected output of every golden case is the human-written original,
converted to new Latin by the SPEC §6 rules. The Python reference
(tools/reference.py) only decides which cases are *strict* — fully determined
by the rules — and never changes an expected value.

  python tools/build_fixtures.py
"""

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import normalize_corpus as nc  # noqa: E402
import reference as ref  # noqa: E402
import uzscript as uz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
FIX = ROOT / "tests" / "fixtures"
SEED = 20260915

SENT_RE = re.compile(r"(?<=[.!?…])\s+|\n+")
RU_LAYOUT = str.maketrans({"ў": "у", "Ў": "У", "қ": "к", "Қ": "К", "ғ": "г", "Ғ": "Г", "ҳ": "х", "Ҳ": "Х"})


def convert_text(text, frm, to):
    """Mirror of engine convert(): tokens converted with their case, gaps and
    protected spans untouched, mixed-case and wrong-script tokens untouched."""
    out = []
    for s, e, kind in uz.spans(text):
        seg = text[s:e]
        if kind != "token":
            out.append(seg)
            continue
        low = uz.normalize(seg).lower()
        case = uz.case_pattern(seg)
        script = uz.detect_script(low)
        if case == "mixed" or script == "mixed" or (frm == "cyrillic") != (script == "cyrillic"):
            out.append(seg)
            continue
        if frm == "cyrillic":
            canon = uz.cyr_to_new_lower(low)
        elif frm == "old":
            canon = uz.old_to_new_lower(low)
        else:
            canon = uz.literal_lower(low)
        out.append(ref.render(canon, to, case) if to != "cyrillic" or uz.new_to_cyr_lower(canon) else seg)
    return "".join(out)


def strip_apostrophes(text):
    out = []
    for s, e, kind in uz.spans(text):
        seg = text[s:e]
        out.append("".join(c for c in seg if c not in uz.APOS_SET) if kind == "token" else seg)
    return "".join(out)


def bare_sh(text):
    out = []
    for s, e, kind in uz.spans(text):
        seg = text[s:e]
        out.append(seg.replace("sh", "s").replace("Sh", "S").replace("SH", "S") if kind == "token" else seg)
    return "".join(out)


def sentences(path, want, limit_docs):
    """Yield (sentence, doc_class) from a parquet shard."""
    an = nc.Analyzer()
    for i, text in enumerate(nc.iter_documents(path, batch_size=256)):
        if i >= limit_docs:
            break
        sents, st = nc.process_document(text, an)
        if not st["keep"]:
            continue
        cls = nc.doc_class(sents)
        if cls not in want:
            continue
        for s in SENT_RE.split(text):
            s = s.strip()
            if 30 <= len(s) <= 170:
                yield s, cls


def token_count(s):
    return sum(1 for a, b, k in uz.spans(s) if k == "token")


def main():
    random.seed(SEED)
    lex = ref.Lex(ROOT / "data" / "lexicon-lite.bin")
    FIX.mkdir(parents=True, exist_ok=True)

    # ---------------- sentence pools ----------------
    latin, cyr = [], []
    for s, cls in sentences(RAW / "uz-crawl" / "news-00002-of-00007.parquet", {"latin_marked"}, 60000):
        if 5 <= token_count(s) <= 16 and not re.search(r"[\"«»“”]", s):
            latin.append(s)
        if len(latin) >= 40000:
            break
    for s, cls in sentences(RAW / "uz-crawl" / "telegram_blogs-00000-of-00001.parquet", {"cyr_uz"}, 120000):
        if 5 <= token_count(s) <= 16 and "ъ" not in s.lower() and not re.search(r"[\"«»“”]", s):
            cyr.append(s)
        if len(cyr) >= 30000:
            break
    random.shuffle(latin)
    random.shuffle(cyr)
    print(f"pools: {len(latin)} Latin, {len(cyr)} Cyrillic sentences", file=sys.stderr)

    strict, ranked = [], []
    seen = set()

    def add(category, inp, expected, script, source, cap, need_change=True):
        if inp in seen:
            return False
        full = sum(1 for c in strict if c["category"] == category) >= cap
        if full and not (category == "ascii_apostropheless" and len(ranked) < 150):
            return False
        got, dec = ref.autocorrect(inp, lex, script)
        if need_change and not any(a in ("corrected",) for _, a, _, _ in dec) and category not in ("old2new", "cyr2new", "protected", "script_old", "script_cyrillic"):
            return False
        if any(a == "ranked" for _, a, _, _ in dec):
            if len(ranked) < 150 and category == "ascii_apostropheless":
                ranked.append({"id": f"R{len(ranked):03d}", "category": category, "input": inp,
                               "expected": expected, "script": script, "source": source})
            return False
        if got != expected or full:
            return False
        seen.add(inp)
        strict.append({"id": f"G{len(strict):03d}", "category": category, "input": inp,
                       "expected": expected, "script": script, "source": source})
        return True

    for s in latin:
        exp = convert_text(s, "old", "new")
        add("ascii_apostropheless", strip_apostrophes(s), exp, "new", "uz-crawl news", 90)
        add("ascii_bare", bare_sh(strip_apostrophes(s)), exp, "new", "uz-crawl news", 30)
        add("old2new", s, exp, "new", "uz-crawl news", 30, need_change=False)
        if len([c for c in strict if c["category"] == "ascii_apostropheless"]) >= 90 and len(ranked) >= 150 \
                and len([c for c in strict if c["category"] == "ascii_bare"]) >= 30 \
                and len([c for c in strict if c["category"] == "old2new"]) >= 30:
            break
    for s in cyr:
        exp = convert_text(s, "cyrillic", "new")
        add("cyr2new", s, exp, "new", "uz-crawl telegram_blogs", 40, need_change=False)
        ru = s.translate(RU_LAYOUT)
        if ru != s:
            add("cyr_russian_layout", ru, exp, "new", "uz-crawl telegram_blogs (ў қ ғ ҳ replaced by у к г х)", 30)
        if sum(1 for c in strict if c["category"] in ("cyr2new", "cyr_russian_layout")) >= 70:
            break

    base = [c for c in strict if c["category"] == "ascii_apostropheless"]
    suffixes = [" https://kun.uz/news/2024/05/01", " @kunuz", " #yangilik", " 5ta", " 2026-yil", " \U0001F60A",
                " iPhone", " COVID-19", " info@example.uz", " 100%", " (2/3)", " — 12:30"]
    for i, c in enumerate(base[:40]):
        suf = suffixes[i % len(suffixes)]
        inp, exp = c["input"].rstrip(".") + suf, c["expected"].rstrip(".") + suf
        got, _ = ref.autocorrect(inp, lex, "new")
        if got == exp:
            strict.append({"id": f"G{len(strict):03d}", "category": "protected", "input": inp, "expected": exp,
                           "script": "new", "source": "golden sentence + protected span"})
    for c in base[:30]:
        inp, exp = c["input"].upper(), c["expected"].upper()
        got, _ = ref.autocorrect(inp, lex, "new")
        if got == exp and len([x for x in strict if x["category"] == "upper_case"]) < 20:
            strict.append({"id": f"G{len(strict):03d}", "category": "upper_case", "input": inp, "expected": exp,
                           "script": "new", "source": "golden sentence, upper-cased"})
    for script in ("old", "cyrillic"):
        n = 0
        for c in base:
            exp = convert_text(c["expected"], "new", script)
            got, _ = ref.autocorrect(c["input"], lex, script)
            if got == exp:
                strict.append({"id": f"G{len(strict):03d}", "category": f"script_{script}", "input": c["input"],
                               "expected": exp, "script": script, "source": c["source"]})
                n += 1
            if n >= 10:
                break

    # The brief's own examples (CLAUDE.md §1, §13). Passthrough forms are expected unchanged.
    brief = [("togri", "töğri"), ("wunaqa", "şunaqa"), ("sosib", "şoşib"), ("ozbekcha", "özbekça"), ("тўғри", "töğri")]
    for inp, exp in brief:
        strict.append({"id": f"G{len(strict):03d}", "category": "brief_correct", "input": inp, "expected": exp,
                       "script": "new", "source": "CLAUDE.md §1"})
    for w in ("kelaslar", "qisela", "balu", "kettik", "bormimiz", "shoshima", "qoyvor"):
        strict.append({"id": f"G{len(strict):03d}", "category": "brief_passthrough", "input": w, "expected": w,
                       "script": "new", "source": "CLAUDE.md §1"})

    # Real-world, unfiltered: the metric that matters most is wrong changes.
    realworld = []
    for s in latin[-600:]:
        realworld.append({"input": strip_apostrophes(s), "expected": convert_text(s, "old", "new"), "kind": "latin_apostropheless"})
    for s in cyr[-300:]:
        ru = s.translate(RU_LAYOUT)
        realworld.append({"input": ru, "expected": convert_text(s, "cyrillic", "new"), "kind": "cyr_russian_layout"})

    cats = Counter(c["category"] for c in strict)
    golden = {
        "_doc": ("Every expected value is human-written text from uz-crawl (Apache-2.0) converted to new Latin by "
                 "SPEC §6, or an example from CLAUDE.md. 'strict' cases are fully determined by the rules and "
                 "the conservative defaults, as checked by tools/reference.py; they must all pass. 'ranked' cases "
                 "have several surviving candidates and are used to tune constants.js. 'realworld' is an "
                 "unfiltered sample used only to measure correct / wrong / missed changes. Built by "
                 "tools/build_fixtures.py with seed %d against data/lexicon-lite.bin." % SEED),
        "counts": dict(cats),
        "strict": strict,
        "ranked": ranked,
        "realworld": realworld,
    }
    (ROOT / "tests" / "golden.json").write_text(json.dumps(golden, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"golden: {len(strict)} strict {dict(cats)}, {len(ranked)} ranked, {len(realworld)} realworld", file=sys.stderr)

    # ---------------- invariant: generated forms (Q23b) ----------------
    forms = [l.split("\t")[0] for l in (RAW / "ngrams" / "passthrough-lite.tsv").read_text(encoding="utf-8").splitlines()]
    random.shuffle(forms)
    picked = []
    for f in forms:
        if ref.autocorrect(f, lex)[0] == f:
            picked.append(f)
        if len(picked) >= 10000:
            break
    (FIX / "invariant-generated.txt").write_text("\n".join(picked) + "\n", encoding="utf-8")
    hw = FIX / "dialect-handwritten.json"
    if not hw.exists():
        hw.write_text(json.dumps({"_doc": "Q23a: ~200 hand-written dialect and slang forms, written by the human. "
                                          "Empty until they land; tests/invariant.test.js reports INCOMPLETE.",
                                  "forms": []}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"invariant-generated: {len(picked)}", file=sys.stderr)

    # ---------------- perf prefixes ----------------
    pref = []
    pool = [strip_apostrophes(s) for s in latin[:4000]] + [s.translate(RU_LAYOUT) for s in cyr[:1500]]
    random.shuffle(pool)
    for s in pool:
        toks = [s[a:b] for a, b, k in uz.spans(s) if k == "token"]
        for j, t in enumerate(toks):
            cut = random.randint(1, len(t))
            pref.append([t[:cut], toks[j - 1] if j else None])
            if len(pref) >= 10000:
                break
        if len(pref) >= 10000:
            break
    (FIX / "perf-prefixes.json").write_text(json.dumps(pref, ensure_ascii=False), encoding="utf-8")

    # ---------------- foreign collisions (parked) ----------------
    uni = {}
    with open(ROOT / "data" / "uz-unigrams.tsv", encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            w, b, n, t, ti, lo = line.rstrip("\n").split("\t")
            b, n, t, ti, lo = int(b), int(n), int(t), int(ti), int(lo)
            crawl = n + t
            if crawl < 30 or ti + lo == 0 or ti / (ti + lo) < 0.8 or uz.TUTUQ in w:
                continue
            uni[w] = (crawl, ti / (ti + lo))
    rows = []
    for w, (crawl, share) in uni.items():
        if w in lex.index or len(w) < 3:
            continue
        hits = [x for x in lex.by_key.get(uz.key(w), ()) if x != w and not lex.capitalized(x)]
        if hits:
            top = max(hits, key=lambda x: lex.ln_uni(x))
            rows.append((w, crawl, share, top))
    rows.sort(key=lambda r: -r[1])
    with open(ROOT / "data" / "foreign-collisions.tsv", "w", encoding="utf-8") as fh:
        fh.write("# PARKED — not used by the engine or tests. Foreign or proper-noun tokens: crawl forms with >= 30\n"
                 "# occurrences, >= 80 % title case, no tutuq, not a lite word, whose skeleton matches a lite word\n"
                 "# that is not itself a proper noun — the tokens autocorrect() could turn into a common word.\n")
        fh.write("form\tcrawl_count\ttitle_share\tcollides_with\n")
        for w, c, sh, top in rows:
            fh.write(f"{w}\t{c}\t{sh:.2f}\t{top}\n")
    print(f"foreign collisions: {len(rows)}", file=sys.stderr)

    # ---------------- bench source pool (gitignored) ----------------
    (ROOT / "data" / "bench-pool.json").write_text(json.dumps({
        "latin": latin[:3000], "cyrillic": cyr[:2000], "passthrough": forms[:3000],
    }, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
