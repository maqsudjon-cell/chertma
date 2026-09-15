"""Assemble the static site into _site/ for GitHub Pages.

  web/*            → _site/
  engine/*.js      → _site/engine/
  data/lexicon-lite.bin → _site/data/ (plus a gzip copy the page inflates)
  sw.js            ← VERSION (content hash) and the precache list

  python tools/build_site.py
"""

import gzip
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "web", OUT)
    (OUT / "engine").mkdir()
    for f in sorted((ROOT / "engine").glob("*.js")):
        shutil.copy2(f, OUT / "engine" / f.name)
    (OUT / "data").mkdir()
    lite = (ROOT / "data" / "lexicon-lite.bin").read_bytes()
    (OUT / "data" / "lexicon-lite.bin").write_bytes(lite)
    (OUT / "data" / "lexicon-lite.bin.gz").write_bytes(gzip.compress(lite, compresslevel=9, mtime=0))
    (OUT / ".nojekyll").write_text("")

    precache = ["./", "index.html", "style.css", "app.js", "manifest.json", "icon.svg",
                "icons/apple-touch-icon.png", "icons/icon-192.png", "icons/icon-512.png",
                "fonts/JetBrainsMono-Regular.ttf", "fonts/JetBrainsMono-Bold.ttf", "data/lexicon-lite.bin.gz"]
    precache += [f"engine/{f.name}" for f in sorted((OUT / "engine").glob("*.js"))]
    h = hashlib.sha256()
    for rel in precache[1:]:
        h.update((OUT / rel).read_bytes())
    sw = (OUT / "sw.js").read_text()
    sw = sw.replace("'__VERSION__'", json.dumps("chertma-" + h.hexdigest()[:12])).replace("__ASSETS__", json.dumps(precache))
    (OUT / "sw.js").write_text(sw)

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"_site: {sum(1 for p in OUT.rglob('*') if p.is_file())} files, {total / 1e6:.2f} MB; cache {h.hexdigest()[:12]}")


if __name__ == "__main__":
    main()
