"""Draft uz-alphabet-bench items into bench/review.md for human review.

Nothing here is published and nothing becomes dev.jsonl / test.jsonl until the
human marks rows `keep`. Run `python tools/build_benchmark.py --export` after
review to write only the kept rows (CLAUDE.md §8).

Sources: data/lexicon-full.bin (words and their book counts via
data/uz-unigrams.tsv), data/bench-pool.json (crawl sentences, generated
passthrough forms), and the brief's own examples. The 24 proposed minimal
pairs in docs/AMBIGUITY-REVIEW.md are parked and not used; the `ambiguity`
category holds only the ruled R1 case.

  python tools/build_benchmark.py            # writes bench/review.md
  python tools/build_benchmark.py --export   # kept rows → bench/dev.jsonl, bench/test.jsonl
"""

import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference as ref  # noqa: E402
import uzscript as uz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEED = 20260915
TARGET = {"ascii2new": 100, "old2new": 80, "cyr2new": 80, "preserve": 100, "ambiguity": 60, "apostrophe": 40, "edge": 40}
UNCHANGED = "o'zgarmaydi"
MARK_UNMARK = {"ş": "s", "ç": "c", "ö": "o", "ğ": "g"}
BARE_MARK = {"s": "ş", "c": "ç", "o": "ö", "g": "ğ"}


def load_counts():
    counts = {}
    with open(ROOT / "data" / "uz-unigrams.tsv", encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            w, b, n, t, ti, lo = line.rstrip("\n").split("\t")
            counts[w] = int(b) + int(n) + int(t)
    return counts


def ascii_of(w):
    """What an ASCII typist writes: sh/ch kept, apostrophes and marks dropped."""
    return uz.new_to_old_lower(w).replace(uz.OKINA, "").replace(uz.TUTUQ, "")


def bare_of(w):
    return "".join(MARK_UNMARK.get(c, c) for c in w).replace(uz.TUTUQ, "")


def partial_variants(w):
    """Spellings with one mark removed or one bare letter wrongly marked."""
    out = set()
    for i, c in enumerate(w):
        if c in MARK_UNMARK:
            out.add(w[:i] + MARK_UNMARK[c] + w[i + 1:])
        elif c in BARE_MARK:
            out.add(w[:i] + BARE_MARK[c] + w[i + 1:])
        elif c == uz.TUTUQ:
            out.add(w[:i] + w[i + 1:])
    out.discard(w)
    return sorted(out)


def item(cat, n, question, options, answer, context=None, source="", note="", split="test"):
    return {"id": f"{cat[:3].upper()}{n:04d}", "category": cat, "context": context, "question": question,
            "options": options, "answer": answer, "source": source, "note": note, "split": split}


def mcq(correct, distractors, rng):
    opts = [correct] + [d for d in dict.fromkeys(distractors) if d != correct][:3]
    if len(opts) < 4:
        return None
    rng.shuffle(opts)
    return opts, opts.index(correct)


def main():
    rng = random.Random(SEED)
    lex = ref.Lex(ROOT / "data" / "lexicon-full.bin")
    lite = ref.Lex(ROOT / "data" / "lexicon-lite.bin")
    words = set(lex.index)
    counts = load_counts()
    pool = json.loads((ROOT / "data" / "bench-pool.json").read_text(encoding="utf-8"))
    items = []

    def valid_anywhere(s):
        return s in words or uz.old_to_new_lower(s) in words

    # Frequent marked words from the lite build, skipping the parked pairs' spellings.
    parked = set(re.findall(r"`([^` ]+)` [а-яўқғҳ]", (ROOT / "docs" / "AMBIGUITY-REVIEW.md").read_text(encoding="utf-8")))
    marked = [w for w in lite.words if any(c in "şçöğ" for c in w) and w not in parked and 4 <= len(w) <= 12
              and not lite.capitalized(w)]
    marked.sort(key=lambda w: -counts.get(w, 0))
    band = marked[150:6000]
    rng.shuffle(band)

    # ascii2new
    n = 0
    for w in band:
        a = ascii_of(w)
        if a == w or valid_anywhere(a) or valid_anywhere(bare_of(w)):
            continue
        d = [uz.new_to_old_lower(w)] + [v for v in partial_variants(w) if v not in words]
        q = mcq(w, d, rng)
        if not q:
            continue
        items.append(item("ascii2new", n, f"\"{a}\" so'zining yangi alifbodagi to'g'ri shakli qaysi?", q[0], q[1],
                          source=f"lexicon ({counts.get(w, 0)} corpus occurrences)"))
        n += 1
        if n >= TARGET["ascii2new"]:
            break
    used = {it["options"][it["answer"]] for it in items}

    # old2new
    n = 0
    for w in band:
        if w in used or ("ö" not in w and "ğ" not in w):
            continue
        old = uz.new_to_old_lower(w)
        d = [old.replace(uz.OKINA, ""), ascii_of(w).replace("sh", "ş").replace("ch", "ç")] + \
            [v for v in partial_variants(w) if v not in words]
        q = mcq(w, d, rng)
        if not q:
            continue
        items.append(item("old2new", n, f"Eski lotindagi \"{old}\" so'zi yangi alifboda qanday yoziladi?", q[0], q[1],
                          source=f"lexicon ({counts.get(w, 0)} corpus occurrences)"))
        used.add(w)
        n += 1
        if n >= TARGET["old2new"]:
            break

    # cyr2new — skip words touched by open questions Q2b (ъ) and Q30 (vowel + и).
    n = 0
    for w in band:
        if w in used or uz.TUTUQ in w or re.search(r"[aeiouö]i", w):
            continue
        cyr = uz.new_to_cyr_lower(w)
        if not cyr or uz.cyr_to_new_lower(cyr) != w:
            continue
        d = [uz.new_to_old_lower(w), bare_of(w)] + [v for v in partial_variants(w) if v not in words]
        q = mcq(w, d, rng)
        if not q:
            continue
        items.append(item("cyr2new", n, f"Kirilldagi \"{cyr}\" so'zining yangi lotin alifbosidagi to'g'ri shakli qaysi?",
                          q[0], q[1], source=f"lexicon ({counts.get(w, 0)} corpus occurrences)"))
        used.add(w)
        n += 1
        if n >= TARGET["cyr2new"]:
            break

    # preserve — the brief's own forms first, then generated passthrough forms (Q23b).
    # The brief's own forms, with distractors that make the forbidden kind of change
    # (morphology restored, a mark added, the case changed). qoyvor is left out: the
    # full lexicon has qöyvor, so "unchanged" may be the wrong answer (Q31).
    brief_distractors = {
        "kelaslar": ["kelasizlar", "kelaşlar", "Kelaslar"],
        "qisela": ["qilsanglar", "qişela", "Qisela"],
        "balu": ["baliq", "Balu", "balʼu"],
        "bormimiz": ["börmimiz", "Bormimiz", "bormimizʼ"],
    }
    for f, d in brief_distractors.items():
        q = mcq(UNCHANGED, d, rng)
        items.append(item("preserve", len([x for x in items if x["category"] == "preserve"]),
                          f"Avtomatik tuzatishda \"{f}\" so'zi qanday bo'lishi kerak?", q[0], q[1], source="CLAUDE.md §1"))
    brief_forms = []
    generated = (ROOT / "tests" / "fixtures" / "invariant-generated.txt").read_text(encoding="utf-8").split()
    gen = [f for f in dict.fromkeys(pool["passthrough"] + generated) if re.fullmatch(r"[abdefghijklmnopqrstuvxyz]{4,12}", f)
           and "sh" not in f and "ch" not in f and not valid_anywhere(f)]
    rng.shuffle(gen)
    n = len(brief_distractors)
    for f, src in [(f, "CLAUDE.md §1") for f in brief_forms] + [(f, "generated passthrough pool (Q23b) — replace with the Q23a hand-written forms") for f in gen]:
        spots = [i for i, c in enumerate(f) if c in BARE_MARK]
        wrong = [f[:i] + BARE_MARK[f[i]] + f[i + 1:] for i in spots]
        wrong += [f[:i] + BARE_MARK[f[i]] + f[i + 1:j] + BARE_MARK[f[j]] + f[j + 1:] for i in spots for j in spots if j > i]
        wrong = [x for x in dict.fromkeys(wrong) if x not in words]
        if len(wrong) < 3:
            continue
        rng.shuffle(wrong)
        q = mcq(UNCHANGED, wrong, rng)
        items.append(item("preserve", n, f"Avtomatik tuzatishda \"{f}\" so'zi qanday bo'lishi kerak?", q[0], q[1],
                          source=src, note="qoyvor: the full lexicon has qöyvor — check" if f == "qoyvor" else ""))
        n += 1
        if n >= TARGET["preserve"]:
            break

    # ambiguity — only the ruled R1 case, in real sentences containing şer / şeʼr / ser.
    n = 0
    for s in pool["latin"]:
        low = s.lower()
        for target in ("she'r", "she’r", "sheʼr", "sher"):
            m = re.search(rf"\b{re.escape(target)}\b", low)
            if m:
                correct = "şeʼr" if "'" in target or "’" in target or "ʼ" in target else "şer"
                ctx = s[:m.start()] + "____" + s[m.end():]
                q = mcq(correct, ["ser", "şer", "şeʼr", "seʼr"], rng)
                items.append(item("ambiguity", n, "Bo'sh joyga yangi alifbodagi qaysi so'z to'g'ri keladi?", q[0], q[1],
                                  context=ctx, source="uz-crawl news sentence (R1 ruled case)",
                                  note="context written in old Latin; blank replaces the original word"))
                n += 1
                break
        if n >= 6:
            break

    # apostrophe — tutuq words: U+02BC is the only correct mark.
    n = 0
    tut = [w for w in lite.words if uz.TUTUQ in w and w.count(uz.TUTUQ) == 1 and 4 <= len(w) <= 12 and w not in used]
    tut.sort(key=lambda w: -counts.get(w, 0))
    for w in tut[:400]:
        variants = [w.replace(uz.TUTUQ, uz.OKINA), w.replace(uz.TUTUQ, ""), w.replace(uz.TUTUQ, "’")]
        if any(v in words for v in variants[1:2]):
            continue
        q = mcq(w, variants, rng)
        items.append(item("apostrophe", n, f"\"{uz.new_to_old_lower(w)}\" so'zining yangi alifbodagi to'g'ri yozilishi qaysi?",
                          q[0], q[1], source=f"lexicon ({counts.get(w, 0)} corpus occurrences)",
                          note="options differ only in the apostrophe code point: U+02BC ʼ, U+02BB ʻ, U+2019 ’, none"))
        n += 1
        if n >= TARGET["apostrophe"]:
            break

    # edge — ng + ğ, word-initial е, ц, ь, capitalised names.
    n = 0
    edge_pools = [
        ("ng", [w for w in lite.words if "nğ" in w and w not in used]),
        ("ye", [w for w in lite.words if w.startswith("ye") and len(w) >= 4 and w not in used]),
        ("ts", [w for w in lite.words if "ts" in w and len(w) >= 5 and w not in used and uz.new_to_cyr_lower(w)]),
        ("name", [w for w in lite.words if lite.capitalized(w) and len(w) >= 5 and any(c in "şçöğ" for c in w) and w not in used]),
    ]
    for kind, ws in edge_pools:
        ws.sort(key=lambda w: -counts.get(w, 0))
        k = 0
        for w in ws:
            if kind == "ng":
                src_form, question = ascii_of(w), f"\"{ascii_of(w)}\" so'zining yangi alifbodagi to'g'ri shakli qaysi?"
                d = [w.replace("nğ", "ng"), w.replace("nğ", "ñ"), uz.new_to_old_lower(w)]
            elif kind == "ye":
                cyr = uz.new_to_cyr_lower(w)
                question = f"Kirilldagi \"{cyr}\" so'zining yangi lotin alifbosidagi to'g'ri shakli qaysi?"
                d = [w[1:], "ie" + w[2:], "je" + w[2:]]
            elif kind == "ts":
                cyr = uz.new_to_cyr_lower(w)
                question = f"Kirilldagi \"{cyr}\" so'zining yangi lotin alifbosidagi to'g'ri shakli qaysi?"
                d = [w.replace("ts", "s"), w.replace("ts", "ç"), w.replace("ts", "c")]
            else:
                title = uz.apply_case(w, "title")
                question = f"\"{uz.apply_case(ascii_of(w), 'title')}\" nomining yangi alifbodagi to'g'ri shakli qaysi?"
                d = [uz.apply_case(uz.new_to_old_lower(w), "title")] + [uz.apply_case(v, "title") for v in partial_variants(w)]
                w = title
            q = mcq(w, [x for x in d if x.lower() not in words or kind == "name"], rng)
            if not q:
                continue
            items.append(item("edge", n, question, q[0], q[1], source=f"lexicon, {kind}",
                              note="ts: native words keep ts (§6.4); check loanwords" if kind == "ts" else ""))
            n += 1
            k += 1
            if k >= 10:
                break

    # dev split: the first 50 items in a fixed shuffle, stratified by category order
    order = list(range(len(items)))
    rng.shuffle(order)
    for i in order[:50]:
        items[i]["split"] = "dev"

    by = {}
    for it in items:
        by.setdefault(it["category"], []).append(it)
    lines = ["# uz-alphabet-bench — DRAFT FOR REVIEW", "",
             "**Nothing here is published.** Every row must be marked `keep`, `fix: …` or `drop` by the human "
             "before `python tools/build_benchmark.py --export` writes `bench/dev.jsonl` and `bench/test.jsonl`.", "",
             "Generated by `tools/build_benchmark.py` (seed %d). Correct option is **bold**." % SEED, "",
             "| Category | Target | Drafted | Notes |", "|---|---|---|---|"]
    notes = {"ambiguity": "PARKED: only the ruled R1 case (ser / şer / şeʼr). The other 54 wait for docs/AMBIGUITY-REVIEW.md.",
             "preserve": "The brief's forms plus generated passthrough forms; swap in the Q23a hand-written forms.",
             "cyr2new": "Words touched by open questions Q2b (ъ) and Q30 (vowel + и) are excluded."}
    for cat, tgt in TARGET.items():
        lines.append(f"| {cat} | {tgt} | {len(by.get(cat, []))} | {notes.get(cat, '')} |")
    lines.append(f"| **total** | {sum(TARGET.values())} | **{len(items)}** | 50 marked `dev`, the rest `test` |")
    lines.append("")
    for cat in TARGET:
        rows = by.get(cat, [])
        if not rows:
            continue
        lines += [f"## {cat} ({len(rows)})", "", "| id | split | context | question | A | B | C | D | source | note | mark |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for it in rows:
            opts = [f"**{o}**" if i == it["answer"] else o for i, o in enumerate(it["options"])]
            cells = [it["id"], it["split"], (it["context"] or "").replace("|", "\\|"), it["question"].replace("|", "\\|")] + \
                    [o.replace("|", "\\|") for o in opts] + [it["source"], it["note"], ""]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    out = ROOT / "bench" / "review.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "bench" / "draft-items.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} items: " + ", ".join(f"{c} {len(by.get(c, []))}" for c in TARGET), file=sys.stderr)


def export():
    """Write only rows the human marked keep (or fix, with the fix applied by hand in draft-items.json)."""
    text = (ROOT / "bench" / "review.md").read_text(encoding="utf-8")
    items = {it["id"]: it for it in json.loads((ROOT / "bench" / "draft-items.json").read_text(encoding="utf-8"))}
    kept = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 11 and cells[0] in items and cells[10].lower().startswith("keep"):
            kept.append(items[cells[0]])
    if not kept:
        print("no rows are marked keep — nothing exported", file=sys.stderr)
        return
    for split in ("dev", "test"):
        with open(ROOT / "bench" / f"{split}.jsonl", "w", encoding="utf-8") as fh:
            for it in kept:
                if it["split"] == split:
                    fh.write(json.dumps({k: it[k] for k in ("id", "category", "context", "question", "options", "answer")},
                                        ensure_ascii=False) + "\n")
    print(f"exported {len(kept)} kept items", file=sys.stderr)


if __name__ == "__main__":
    export() if "--export" in sys.argv else main()
