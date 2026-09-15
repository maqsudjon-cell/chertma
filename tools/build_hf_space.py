"""Assemble hf/space/: the web demo as a Hugging Face static Space.

Starts from the same build as the live site (tools/build_site.py → _site/), then:
  - drops CNAME and .nojekyll (GitHub Pages only)
  - adds footer links to chertma.maqsudjon.com and the lexicon dataset
  - recomputes the service-worker cache version for the changed index.html
  - checks that no asset is referenced by a root-absolute path
hf/space/README.md (the Space card, tracked in git) is left untouched.

  python3 tools/build_site.py && python3 tools/build_hf_space.py
"""

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
OUT = ROOT / "hf" / "space"

FOOTER_ANCHOR = '<span><a class="link" href="https://github.com/maqsudjon-cell/chertma" rel="noopener" data-i18n="source">Manba kodi</a></span>'
FOOTER_LINKS = (
    '<span><a class="link" href="https://chertma.maqsudjon.com" target="_blank" rel="noopener">chertma.maqsudjon.com</a></span>\n'
    '  <span><a class="link" href="https://huggingface.co/datasets/Maqsudjonpolatov/uz-lexicon-skeleton" target="_blank" rel="noopener">uz-lexicon-skeleton</a></span>\n  '
)


def main():
    if not (SITE / "index.html").exists():
        sys.exit("run python3 tools/build_site.py first")
    readme = (OUT / "README.md").read_bytes() if (OUT / "README.md").exists() else None
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SITE, OUT, ignore=shutil.ignore_patterns("CNAME", ".nojekyll"))
    if readme is not None:
        (OUT / "README.md").write_bytes(readme)

    index = (OUT / "index.html").read_text(encoding="utf-8")
    assert index.count(FOOTER_ANCHOR) == 1, "footer anchor not found"
    index = index.replace(FOOTER_ANCHOR, FOOTER_LINKS + FOOTER_ANCHOR)
    index = index.replace('rel="noopener"', 'target="_blank" rel="noopener"').replace('target="_blank" target="_blank"', 'target="_blank"')
    (OUT / "index.html").write_text(index, encoding="utf-8")

    sw = (OUT / "sw.js").read_text(encoding="utf-8")
    assets = json.loads(re.search(r"const ASSETS = (\[.*?\]);", sw).group(1))
    h = hashlib.sha256()
    for rel in assets[1:]:
        h.update((OUT / rel).read_bytes())
    sw = re.sub(r"const VERSION = '[^']*';|const VERSION = \"[^\"]*\";", f"const VERSION = {json.dumps('chertma-space-' + h.hexdigest()[:12])};", sw)
    (OUT / "sw.js").write_text(sw, encoding="utf-8")

    # No root-absolute references: the Space is served from its own subdomain and
    # shown inside an iframe on huggingface.co, so every asset path must be relative.
    problems = []
    for f in OUT.rglob("*"):
        if f.suffix not in {".html", ".js", ".css", ".json"}:
            continue
        text = f.read_text(encoding="utf-8")
        for pat in (r'(?:src|href)="/(?!/)', r"url\(\s*['\"]?/(?!/)", r"""(?:fetch|register|import)\(\s*['"]/(?!/)""",
                    r"""from\s+['"]/(?!/)""", r'"start_url":\s*"/', r'"src":\s*"/'):
            for m in re.finditer(pat, text):
                problems.append(f"{f.relative_to(OUT)}: {text[m.start():m.start() + 60]!r}")
    if problems:
        sys.exit("root-absolute paths:\n  " + "\n  ".join(problems))
    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    print(f"hf/space: {len(files)} files, {sum(p.stat().st_size for p in files):,} bytes; no root-absolute paths")


if __name__ == "__main__":
    main()
