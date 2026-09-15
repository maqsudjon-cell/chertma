"""web/icons/*.png and web/icon.svg — a dot-matrix Ş in the accent colour on
the dark ground. Pure Python (zlib), no image library.

  python tools/make_icons.py
"""

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BG = (11, 11, 12)
ACCENT = (255, 106, 26)
DIM = (38, 38, 40)

# 5 × 9 dot-matrix Ş: the letter on rows 0–6, the cedilla on rows 7–8.
GLYPH = [
    ".###.",
    "#...#",
    "#....",
    ".###.",
    "....#",
    "#...#",
    ".###.",
    "..#..",
    ".#...",
]
COLS, ROWS = 5, 9


def png(size, maskable):
    pad = size * (0.22 if maskable else 0.16)
    cell = (size - 2 * pad) / ROWS
    left = (size - COLS * cell) / 2
    top = pad
    r = cell * 0.36
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            color = BG
            cx = (x + 0.5 - left) / cell
            cy = (y + 0.5 - top) / cell
            gx, gy = int(cx), int(cy)
            if 0 <= gx < COLS and 0 <= gy < ROWS and cx >= 0 and cy >= 0:
                dx = (cx - gx - 0.5) * cell
                dy = (cy - gy - 0.5) * cell
                if dx * dx + dy * dy <= r * r:
                    color = ACCENT if GLYPH[gy][gx] == "#" else DIM
            row += bytes(color)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 9)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", raw) + chunk(b"IEND", b""))


def svg():
    cell = 10
    dots = []
    for gy, line in enumerate(GLYPH):
        for gx, ch in enumerate(line):
            fill = "#FF6A1A" if ch == "#" else "#262628"
            dots.append(f'<circle cx="{25 + gx * cell + 5}" cy="{10 + gy * cell + 5}" r="3.6" fill="{fill}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 110">'
            '<rect width="100" height="110" fill="#0b0b0c"/>' + "".join(dots) + "</svg>\n")


def main():
    out = ROOT / "web" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for name, size, maskable in (("icon-192.png", 192, False), ("icon-512.png", 512, False),
                                 ("maskable-512.png", 512, True), ("apple-touch-icon.png", 180, False)):
        (out / name).write_bytes(png(size, maskable))
    (ROOT / "web" / "icon.svg").write_text(svg())


if __name__ == "__main__":
    main()
