"""Python reference of autocorrect() — SPEC §5, §7.3, §8.2 plus the defaults
taken unattended (docs/OPEN-QUESTIONS.md, "Defaults taken unattended").

Used only to build test fixtures: tests/golden.json keeps human-written text
whose correct form these rules determine uniquely. The engine in engine/ is
the product; where the two disagree, a golden test fails and one of them is
wrong. No bigrams here, so ranking between several surviving candidates is
not modelled — such cases are excluded from the strict golden set.
"""

import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_lexicon  # noqa: E402
import uzscript as uz  # noqa: E402

NU_EVIDENCE = 0.5
BREAK_RE = re.compile(r"[.!?…\n]")
ACRONYM_MAX = 4          # default D3: an isolated upper-case token this short is never corrected

_CLASS = {"s": "S", "ş": "S", "w": "S", "c": "C", "ç": "C",
          "o": "O", "ö": "O", "ó": "O", "ő": "O", "g": "G", "ğ": "G", "ǵ": "G"}


class Lex:
    def __init__(self, path):
        d = pack_lexicon.read_lexicon(Path(path).read_bytes())
        self.words = d["words"]
        self.index = {w: i for i, w in enumerate(self.words)}
        self.by_key = defaultdict(list)
        for w in self.words:
            self.by_key[uz.key(w)].append(w)
        self.uni_q = d["uni_q"]
        self.wflags = d["wflags"]
        self.qs = d["qs_uni"]

    def capitalized(self, w):
        return bool(self.wflags[self.index[w]] & 1)

    def ln_uni(self, w):
        return self.uni_q[self.index[w]] / self.qs


# --- units for evidence ---------------------------------------------------------

def _letters(chars):
    """[(ch, origin, apos)] from [(ch, origin)] where ch may be an apostrophe."""
    out = []
    for ch, origin in chars:
        if ch in uz.APOS_SET or ch == uz.TUTUQ:
            if out:
                out[-1][2] += 1
            continue
        out.append([ch, origin, 0])
    return out


def _units(letters):
    units = []
    i = 0
    while i < len(letters):
        ch, origin, apos = letters[i]
        if ch in "scg" and i + 1 < len(letters) and letters[i + 1][0] == "h":
            h = letters[i + 1]
            units.append({"sym": ch.upper(), "spell": ch + ("'h" if apos else "h"),
                          "origin": (origin, h[1]), "apos": h[2]})
            i += 2
        else:
            units.append({"sym": _CLASS.get(ch, ch), "spell": ch, "origin": origin, "apos": apos})
            i += 1
    return units


def latin_units(low):
    return _units(_letters([(c, None) for c in low]))


def cyr_units(low, reading_opts):
    """reading_opts: one chosen output string per Cyrillic position."""
    chars = []
    for cyr, out in zip(low, reading_opts):
        if out == uz.TUTUQ:
            chars.append((uz.TUTUQ, cyr))
        else:
            chars.extend((c, cyr) for c in out)
    return _units(_letters(chars))


def cand_units(word):
    return _units(_letters([(c, None) for c in word]))


_MARKED_SPELL = {"ş": ("ş", "sh", "w"), "ç": ("ç", "ch"),
                 "ö": ("ö", "ó", "ő"), "ğ": ("ğ", "gh", "ǵ")}
_BARE = {"ş": "s", "ç": "c", "ö": "o", "ğ": "g"}


def _latin_letter(inp, cand):
    """(evidence, apostrophes consumed) for one aligned unit, Latin input."""
    sp, cs = inp["spell"], cand["spell"]
    if cs in _MARKED_SPELL:                                     # ş ç ö ğ
        if sp in _MARKED_SPELL[cs]:
            return 1, 0
        if sp == _BARE[cs]:
            if cs in "öğ" and inp["apos"] > 0:
                return 1, 1                                     # o' / g'
            return 0, 0
        return -1, 0
    if cs in ("sh", "ch", "gh"):                                # literal s+h etc.
        if sp == cs[0] + "'h":
            return 1, 0
        if sp == cs:
            return 0, 0
        return -1, 0
    if cs in ("s", "c", "o", "g"):
        if sp == cs:
            if cs in "og" and inp["apos"] > 0 and cand["apos"] == 0:
                return -1, 1                                    # o' against plain o
            return 0, 0
        return -1, 0
    return 0, 0


def _cyr_letter(inp, cand):
    o, cs = inp["origin"], cand["spell"]
    first = o[0] if isinstance(o, tuple) else o
    table = {
        "ş": {"ш": 1, "с": -1, "ц": -1},
        "s": {"с": 1, "ш": -1},
        "ç": {"ч": 1},
        "ö": {"ў": 1},
        "o": {"ў": -1},
        "ğ": {"ғ": 1},
        "g": {"ғ": -1},
        "q": {"қ": 1},
        "h": {"ҳ": 1},
    }
    if cs == "sh":
        if isinstance(o, tuple) and o[0] == "с":
            return 1 if o[1] == "ҳ" else 0
        return -1
    if cs == "gh":
        if isinstance(o, tuple) and o[0] == "г":
            return 1 if o[1] == "ҳ" else 0
        return -1
    return table.get(cs, {}).get(first, 0)


def evidence(inp_units, cand, cyrillic):
    """Per-position evidence list (SPEC §8.2), or None if units do not align."""
    cu = cand_units(cand)
    if [u["sym"] for u in inp_units] != [u["sym"] for u in cu]:
        return None
    ev = []
    for iu, c in zip(inp_units, cu):
        if cyrillic:
            e, used = _cyr_letter(iu, c), 0
        else:
            e, used = _latin_letter(iu, c)
        rest = iu["apos"] - used
        if c["apos"] > 0 and rest > 0:
            t = 1
        elif c["apos"] == 0 and rest > 0:
            t = -1
        else:
            t = 0
        ev.append(e)
        if t:
            ev.append(t)
    return ev


# --- autocorrect -----------------------------------------------------------------

def valid_reading(tok_low, script, words):
    if script == "cyrillic":
        r = uz.cyr_to_new_lower(tok_low)
        return r if r in words else None
    for r in (uz.literal_lower(tok_low), uz.old_to_new_lower(tok_low)):
        if r in words:
            return r
    return None


def candidates(token, lex, recovery=True):
    """[(word, evidence list)] for a token with no valid reading."""
    low = uz.normalize(token).lower()
    script = uz.detect_script(low)
    out = {}
    if script == "cyrillic":
        opts = uz._cyr_options(low, recovery)
        count = math.prod(len(o) for o in opts)
        if count > 4096:
            opts = [(o[0],) for o in opts]
        import itertools
        for choice in itertools.product(*opts):
            k = uz._fold("".join(choice))
            for w in lex.by_key.get(k, ()):
                ev = evidence(cyr_units(low, choice), w, True)
                if ev is not None and (w not in out or sum(ev) > sum(out[w])):
                    out[w] = ev
    else:
        k = uz._fold(low)
        units = latin_units(low)
        for w in lex.by_key.get(k, ()):
            ev = evidence(units, w, False)
            if ev is not None:
                out[w] = ev
    return list(out.items())


def render(word, script, case):
    if script == "old":
        s = uz.new_to_old_lower(word)
    elif script == "cyrillic":
        s = uz.new_to_cyr_lower(word)
        if s is None:
            s = word
    else:
        s = word
    return uz.apply_case(s, case)


def _same_letters(a, b):
    f = lambda x: "".join("'" if c in uz.APOS_SET else c for c in x)  # noqa: E731
    return f(uz.normalize(a)) == f(uz.normalize(b))


def autocorrect(text, lex, script="new"):
    """Returns (output, decisions). decisions: [(surface, action, result, n_candidates)]."""
    sp = uz.spans(text)
    words = lex.index
    # sentence chunks for the case rules
    tok_idx = [i for i, s in enumerate(sp) if s[2] == "token"]
    initial = set()
    chunk_of = {}
    chunk, chunks = [], []
    last = None
    for i, (s, e, kind) in enumerate(sp):
        if kind == "gap" and BREAK_RE.search(text[s:e]):
            if chunk:
                chunks.append(chunk)
            chunk = []
            last = None
        if kind == "token":
            if last is None:
                initial.add(i)
            chunk.append(i)
            last = i
    if chunk:
        chunks.append(chunk)
    shouting = set()
    for ch in chunks:
        toks = [text[sp[i][0]:sp[i][1]] for i in ch]
        long = [t for t in toks if len(t) >= 2]
        if long and all(uz.case_pattern(t) == "upper" for t in long):
            shouting.update(ch)

    out, decisions = [], []
    for i, (s, e, kind) in enumerate(sp):
        seg = text[s:e]
        if kind != "token":
            out.append(seg)
            continue
        low = uz.normalize(seg).lower()
        script_in = uz.detect_script(low)
        case = uz.case_pattern(seg)
        letters = sum(1 for c in low if c not in uz.APOS_SET)
        if script_in == "mixed" or case == "mixed":
            out.append(seg); decisions.append((seg, "protected", seg, 0)); continue
        if letters < 2:                                                   # D4 (Q24)
            out.append(seg); decisions.append((seg, "one-letter", seg, 0)); continue
        chosen = valid_reading(low, script_in, words)
        action = "valid"
        n = 0
        if chosen is None:
            if case == "upper" and i not in shouting and letters <= ACRONYM_MAX:   # D3 (Q21)
                out.append(seg); decisions.append((seg, "acronym", seg, 0)); continue
            cands = candidates(seg, lex)
            n = len(cands)
            cands = [(w, ev) for w, ev in cands if min(ev, default=0) >= 0]         # D2 (Q28)
            if case in ("title", "upper") and i not in initial and i not in shouting:
                cands = [(w, ev) for w, ev in cands if lex.capitalized(w)]           # D3 (Q21)
            if not cands:
                out.append(seg); decisions.append((seg, "unchanged", seg, n)); continue
            if len(cands) > 1:
                cands.sort(key=lambda c: -(lex.ln_uni(c[0]) + NU_EVIDENCE * sum(c[1])))
                action = "ranked"
            else:
                action = "corrected"
            chosen = cands[0][0]
        rendered = render(chosen, script, case)
        if _same_letters(rendered, seg):
            rendered = seg
        out.append(rendered)
        decisions.append((seg, action, rendered, n))
    return "".join(out), decisions
