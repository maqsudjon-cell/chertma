"""Uzbek script rules for the build tools.

Python mirror of engine/normalize.js, skeleton.js and translit.js. The source
of truth is docs/SPEC.md (§2 normalization, §3 tokenization, §4 skeleton, §6
conversion); both implementations are checked against
tests/fixtures/skeleton.json.

Known difference from the JS engine: Python's `re` has no \\p{L}. A letter here
is `[^\\W\\d_]` (Unicode alphanumerics minus digits) minus super/subscript and
other No-category digits, plus U+0300–U+036F combining marks, minus the
modifier-letter apostrophes. The two agree on every
Uzbek, Russian and English letter.
"""

import itertools
import re
import unicodedata

# §2.3 — apostrophe-likes (set A).
APOS = "'`´‘’ʻʼʽʿ′"
APOS_SET = frozenset(APOS)
TUTUQ = "ʼ"
OKINA = "ʻ"

# §2.4 step 2 — confusable fold.
_CONFUSABLE = str.maketrans({
    "ș": "ş", "Ș": "Ş",  # ș Ș → ş Ş
    "ǧ": "ğ", "Ǧ": "Ğ",  # ǧ Ǧ → ğ Ğ
    "ı": "i", "İ": "I",            # ı İ → i I
    "һ": "ҳ", "Һ": "Ҳ",  # һ Һ → ҳ Ҳ
    "ӯ": "ў", "Ӯ": "Ў",  # ӯ Ӯ → ў Ў
})


_CONFUSABLE_RE = re.compile("[\u0219\u0218\u01e7\u01e6\u0131\u0130\u04bb\u04ba\u04ef\u04ee]")


def normalize(text):
    """§2.4: NFC, then confusable fold. Apostrophes are left alone."""
    if not unicodedata.is_normalized("NFC", text):
        text = unicodedata.normalize("NFC", text)
    if _CONFUSABLE_RE.search(text):
        text = text.translate(_CONFUSABLE)
    return text


# --- characters -------------------------------------------------------------

_A = re.escape(APOS)
_L = r"(?:[^\W\d_\u02bb\u02bc\u02bd\u02bf\u00b2\u00b3\u00b9\u00bc-\u00be\u2070-\u209f\u2150-\u218f\u2460-\u24ff\u2776-\u2793]|[\u0300-\u036f])"

# §3.2 — token := L+ (A+ L+)* tail?
# Alternative 1: not preceded by an apostrophe-like; tail allowed.
# Alternative 2: preceded by one (a quotation); no o/g tail.
TOKEN_RE = re.compile(
    rf"(?<![{_A}])({_L}+(?:[{_A}]+{_L}+)*(?:(?<=[oOgG])[{_A}]|ʼ)?)"
    rf"|(?<=[{_A}])({_L}+(?:[{_A}]+{_L}+)*(?:(?<![oOgG])ʼ)?)"
)

# §3.3 — protected spans (URL, bare domain, email, mention, hashtag). Found by
# a cheap anchor; the whole whitespace-delimited run around it is protected.
_TLD = "uz|com|ru|org|net|io|me|info|tv|gov|edu|app|dev|ai|co|su|kz|tj|kg|tm|tr|de|uk|us|biz|pro|online|site|xyz"
PROTECTED_ANCHOR_RE = re.compile(rf"://|\bwww\.|[@#]\w|\.(?:{_TLD})\b", re.IGNORECASE)
_DIGIT_OR_UNDERSCORE_RE = re.compile(r"[\d_\u00b2\u00b3\u00b9\u00bc-\u00be\u2070-\u209f\u2150-\u218f\u2460-\u24ff\u2776-\u2793]")


def blank_protected_spans(text, repl="\n"):
    if not PROTECTED_ANCHOR_RE.search(text):
        return text
    out = []
    pos = 0
    n = len(text)
    for m in PROTECTED_ANCHOR_RE.finditer(text):
        s, e = m.span()
        if s < pos:
            continue
        while s > pos and not text[s - 1].isspace():
            s -= 1
        while e < n and not text[e].isspace():
            e += 1
        out.append(text[pos:s])
        out.append(repl)
        pos = e
    out.append(text[pos:])
    return "".join(out)


SENTENCE_BREAK_RE = re.compile(r"[.!?…\n]+")

UZ_CYRILLIC = frozenset("абвгдеёжзийклмнопрстуфхцчшъьэюяўқғҳ")
UZ_LATIN_CANONICAL = frozenset("abdefghijklmnopqrstuvxyz") | frozenset("şçöğ") | {TUTUQ}
MARKED = frozenset("şçöğ") | {TUTUQ}


def is_cyrillic(ch):
    return "Ѐ" <= ch <= "ԯ"


def is_latin(ch):
    return ch.isascii() or "À" <= ch <= "ɏ" or "Ḁ" <= ch <= "ỿ"


def detect_script(token):
    """§4.8: 'latin', 'cyrillic' or 'mixed' (anything else, incl. other scripts)."""
    lat = cyr = other = False
    for ch in token:
        if ch in APOS_SET or not (ch.isalpha() or unicodedata.category(ch).startswith("M")):
            continue
        if is_cyrillic(ch):
            cyr = True
        elif is_latin(ch):
            lat = True
        else:
            other = True
    if other or (lat and cyr):
        return "mixed"
    if cyr:
        return "cyrillic"
    return "latin"


def case_pattern(token):
    """§3.4: 'lower', 'title', 'upper' or 'mixed'."""
    letters = [c for c in token if c.isalpha() and c not in APOS_SET]
    if not letters:
        return "lower"
    w = "".join(letters)
    if w == w.lower():
        return "lower"
    if w == w.upper():
        return "title" if len(w) == 1 else "upper"
    if w[0] == w[0].upper() and w[1:] == w[1:].lower():
        return "title"
    return "mixed"


# --- §6.1 Cyrillic → new ------------------------------------------------------

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ч": "ç", "ш": "ş",
    "ў": "ö", "қ": "q", "ғ": "ğ", "ҳ": "h", "э": "e", "ё": "yo", "ю": "yu",
    "я": "ya",
}
_CYR_VOWELS = frozenset("аеёиоуэюяў")
_IOTATED = frozenset("еёюя")
_RECOVERY = {"у": ("u", "ö"), "к": ("k", "q"), "х": ("x", "h")}


def _cyr_options(low, recovery):
    """Per-position output options for a lowercase Cyrillic token."""
    opts = []
    n = len(low)
    for i, ch in enumerate(low):
        prev = low[i - 1] if i else None
        nxt = low[i + 1] if i + 1 < n else None
        if ch == "е":
            o = "ye" if prev is None or prev in _CYR_VOWELS or prev in "ъь" or prev in APOS_SET else "e"
        elif ch == "ц":
            o = "ts" if prev is not None and prev in _CYR_VOWELS else "s"
        elif ch == "ъ" or ch in APOS_SET:
            o = "" if nxt in _IOTATED else TUTUQ
        elif ch == "ь":
            o = "y" if nxt == "о" else ""
        elif recovery and ch in _RECOVERY:
            opts.append(_RECOVERY[ch])
            continue
        else:
            o = _CYR.get(ch, ch)
        opts.append((o,))
    return opts


def cyr_to_new_lower(low):
    """Deterministic §6.1 transliteration of a lowercase Cyrillic token."""
    return "".join(o[0] for o in _cyr_options(low, False))


def cyr_readings(low, recovery=True, limit=4096):
    opts = _cyr_options(low, recovery)
    count = 1
    for o in opts:
        count *= len(o)
    if count > limit:  # pathological tokens only; the engine prunes instead
        opts = [(o[0],) for o in opts]
    return ["".join(p) for p in itertools.product(*opts)]


# --- §6.3 old Latin → new ---------------------------------------------------

def old_to_new_lower(low):
    out = []
    i, n = 0, len(low)
    while i < n:
        c = low[i]
        nxt = low[i + 1] if i + 1 < n else ""
        if c == "s" and nxt in APOS_SET and i + 2 < n and low[i + 2] == "h":
            out.append("sh")
            i += 3
        elif c == "s" and nxt == "h":
            out.append("ş")
            i += 2
        elif c == "c" and nxt == "h":
            out.append("ç")
            i += 2
        elif c in "og" and nxt and nxt in APOS_SET:
            out.append("ö" if c == "o" else "ğ")
            i += 2
        elif c in APOS_SET:
            out.append(TUTUQ)
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def literal_lower(low):
    """§5.1 literal reading of a Latin token: every apostrophe-like → ʼ."""
    return "".join(TUTUQ if c in APOS_SET else c for c in low)


# --- §4 skeleton --------------------------------------------------------------

_CLASS = {
    "s": "S", "ş": "S", "w": "S",
    "c": "C", "ç": "C",
    "o": "O", "ö": "O", "ó": "O", "ő": "O",
    "g": "G", "ğ": "G", "ǵ": "G",
}


def _fold(s):
    """Steps 4–5 on one lowercase Latin string."""
    s = "".join(c for c in s if c not in APOS_SET)
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "scg" and i + 1 < n and s[i + 1] == "h":
            out.append(c.upper())
            i += 2
        else:
            out.append(_CLASS.get(c, c))
            i += 1
    return "".join(out)


def _fuzzy(k, qk, xh):
    if not (qk or xh):
        return {k}
    opts = []
    for c in k:
        if qk and c in "qk":
            opts.append("qk")
        elif xh and c in "xh":
            opts.append("xh")
        else:
            opts.append(c)
    return {"".join(p) for p in itertools.product(*opts)}


def key(word):
    """key(w) for a canonical lowercase word."""
    return _fold(word)


def skeleton(token, script=None, fuzzyQK=False, fuzzyXH=False, cyrillicKeyboardRecovery=True):
    """§4.1: the set of keys of a surface token."""
    low = normalize(token).lower()
    if script is None:
        script = detect_script(low)
    if script == "cyrillic":
        strings = cyr_readings(low, cyrillicKeyboardRecovery)
    else:
        strings = [low]
    keys = set()
    for s in strings:
        keys |= _fuzzy(_fold(s), fuzzyQK, fuzzyXH)
    return keys


def strip_marks(word):
    """§9.6 rule 3: the fully stripped variant of a canonical word."""
    return word.translate(_STRIP).replace(TUTUQ, "")


_STRIP = str.maketrans({"ş": "s", "ç": "c", "ö": "o", "ğ": "g"})


# --- corpus analysis ----------------------------------------------------------

def analyze(surface, normalized=False):
    """Classify one surface token for counting.

    Returns (kind, canonical, case) where kind is
      'word'      canonical is a lowercase new-Latin form in the Uzbek charset
      'outside'   letters outside the Uzbek charset (Russian ы щ, English c w, …)
      'protected' mixed case (§3.3), never counted
    """
    case = case_pattern(surface)
    if case == "mixed":
        return ("protected", None, case)
    low = (surface if normalized else normalize(surface)).lower()
    script = detect_script(low)
    if script == "cyrillic":
        if any(c not in UZ_CYRILLIC and c not in APOS_SET for c in low):
            return ("outside", None, case)
        canon = cyr_to_new_lower(low)
    elif script == "latin":
        canon = old_to_new_lower(low)
        if any(c not in UZ_LATIN_CANONICAL for c in canon):
            return ("outside", None, case)
    else:
        return ("outside", None, case)
    canon = canon.lstrip(TUTUQ)
    if not canon:
        return ("outside", None, case)
    return ("word", canon, case)


def iter_sentences(text):
    """Yield sentences as lists of surface tokens; None marks a chain break
    (a token glued to a digit or underscore, §3.3). Text is normalized here."""
    text = blank_protected_spans(normalize(text))
    for chunk in SENTENCE_BREAK_RE.split(text):
        if not chunk:
            continue
        if not _DIGIT_OR_UNDERSCORE_RE.search(chunk):
            items = [a or b for a, b in TOKEN_RE.findall(chunk)]
        else:
            items = []
            n = len(chunk)
            for m in TOKEN_RE.finditer(chunk):
                s, e = m.span()
                before = chunk[s - 1] if s else ""
                after = chunk[e] if e < n else ""
                if before.isdigit() or after.isdigit() or before == "_" or after == "_":
                    items.append(None)
                else:
                    items.append(m.group(m.lastindex))
        if items:
            yield items
