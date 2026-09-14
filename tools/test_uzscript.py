"""Check tools/uzscript.py against tests/fixtures/skeleton.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uzscript as uz  # noqa: E402

FIX = json.loads((Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "skeleton.json").read_text())
fails = 0


def check(label, got, want):
    global fails
    if got != want:
        fails += 1
        print(f"FAIL {label}: got {got!r}, want {want!r}")


for e in FIX["skeleton"]:
    check(f"skeleton {e['in']} {e.get('opts', {})}", sorted(uz.skeleton(e["in"], **e.get("opts", {}))), e["keys"])
for src, want in FIX["cyr_to_new"]:
    check(f"cyr_to_new {src}", uz.cyr_to_new_lower(uz.normalize(src).lower()), want)
for src, want in FIX["old_to_new"]:
    check(f"old_to_new {src}", uz.old_to_new_lower(uz.normalize(src).lower()), want)
for e in FIX["tokens"]:
    got = [t for sent in uz.iter_sentences(e["in"]) for t in sent]
    check(f"tokens {e['in']}", got, e["tokens"])
for src, want in FIX["cyr_to_new"]:  # script-blind property on the conversion fixtures
    k = uz.key(want)
    check(f"script-blind {src}", k in uz.skeleton(src), True)

total = len(FIX["skeleton"]) + 2 * len(FIX["cyr_to_new"]) + len(FIX["old_to_new"]) + len(FIX["tokens"])
print(f"{total - fails}/{total} passed")
sys.exit(1 if fails else 0)
