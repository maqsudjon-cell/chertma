"""Suffix-chain inventory for the engine's morphological fallback (SPEC §5.2).

A suffix chain is a word ending that the corpus shows attached to many
different frequent stems: `ting` in işla·ting, yoz·ting… The inventory is data,
not grammar — it contains no morpheme boundaries, only whole chains.

derive(counts) → sorted list of chains, from admitted canonical words and their
merged counts. with_section(buf, chains) → a v1 lexicon with section 9 filled
and the CRC recomputed (SPEC §9.3).
"""

import struct
import zlib
from collections import defaultdict

# Build constants — docs/OPEN-QUESTIONS.md M5.
STEM_MIN_COUNT = 1000      # a stem that licenses a suffix must itself be a frequent word
STEM_MIN_LETTERS = 3
WORD_MIN_COUNT = 10        # only words seen at least this often are split
SUFFIX_MIN_LETTERS = 2
SUFFIX_MAX_LETTERS = 12
MIN_DISTINCT_STEMS = 100   # a chain must follow at least this many different stems

TUTUQ = "ʼ"
CPUZ = {chr(c): c for c in range(0x61, 0x7B)}
CPUZ.update({"ş": 0x80, "ç": 0x81, "ö": 0x82, "ğ": 0x83, TUTUQ: 0x84})


def _letters(s):
    return len(s) - s.count(TUTUQ)


def derive(counts):
    stems = {w for w, c in counts.items() if c >= STEM_MIN_COUNT and _letters(w) >= STEM_MIN_LETTERS}
    support = defaultdict(int)
    for w, c in counts.items():
        if c < WORD_MIN_COUNT:
            continue
        for i in range(1, len(w)):
            s = w[i:]
            if s[0] == TUTUQ or not (SUFFIX_MIN_LETTERS <= _letters(s) <= SUFFIX_MAX_LETTERS):
                continue
            if w[:i] in stems:
                support[s] += 1
    return sorted(s for s, n in support.items() if n >= MIN_DISTINCT_STEMS)


def encode_section(chains):
    out = bytearray(struct.pack("<I", len(chains)))
    for s in chains:
        b = bytes(CPUZ[c] for c in s)
        out += struct.pack("<B", len(b)) + b
    return bytes(out)


def with_section(buf, chains):
    """Return a copy of a v1 lexicon file with section 9 = the suffix inventory."""
    buf = bytearray(buf)
    table = [struct.unpack_from("<II", buf, 0x40 + 8 * i) for i in range(12)]
    body_end = len(buf)
    while body_end % 4:
        body_end += 1
    sec = encode_section(chains)
    buf += b"\0" * (body_end - len(buf))
    off = len(buf)
    buf += sec
    while len(buf) % 4:
        buf.append(0)
    table[9] = (off, len(sec))
    for i, (o, ln) in enumerate(table):
        struct.pack_into("<II", buf, 0x40 + 8 * i, o, ln)
    flags = struct.unpack_from("<H", buf, 6)[0] | 16  # bit4 HAS_SUFFIXES
    struct.pack_into("<H", buf, 6, flags)
    struct.pack_into("<I", buf, 0x24, zlib.crc32(bytes(buf[0x40:])) & 0xFFFFFFFF)
    return bytes(buf)
