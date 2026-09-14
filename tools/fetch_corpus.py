"""Download corpus shards from Hugging Face at pinned revisions.

Step 1 of the pipeline (CLAUDE.md §6, docs/SPEC.md §9.6).

The brief suggests datasets.load_dataset(). It is not used: a full
load_dataset() of uz-books-v2 needs ~50 GB of disk (16 GB of parquet plus a
33 GB arrow cache) and pulls in pandas, fsspec, aiohttp and more. This script
downloads the same parquet files one shard at a time, pinned to a revision and
checked against the sha256 the Hub publishes, so a shard can be counted and
deleted before the next one arrives.

Usage:
  python tools/fetch_corpus.py list  uz-books-v2 lat
  python tools/fetch_corpus.py fetch uz-crawl telegram_blogs
  python tools/fetch_corpus.py fetch uz-crawl news --shards 0 1 2
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# Pinned revisions. Licences are copied from each dataset card at this
# revision and recorded in data/SOURCES.md.
SOURCES = {
    "uz-crawl": {
        "repo": "tahrirchi/uz-crawl",
        "revision": "8fff2d17bb2607c5d875199c8a7256a4a7ce7e39",
        "license": "apache-2.0",
    },
    "uz-books-v2": {
        "repo": "tahrirchi/uz-books-v2",
        "revision": "aac9c105622abf1b554640793d1fe17ab2ff28d9",
        "license": "mit",
    },
}


def _curl(args):
    # System curl, not urllib: python.org builds of Python ship without a CA
    # bundle, and fixing that would mean changing the system installation.
    return subprocess.run(["curl", "-sSfL", "--retry", "3", *args], check=True, capture_output=True)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def list_shards(dataset, split):
    """Return [{path, size, sha256}] for one split, sorted by shard index."""
    src = SOURCES[dataset]
    cache = RAW / dataset / "_tree.json"
    if cache.exists():
        tree = json.loads(cache.read_text())
    else:
        url = f"https://huggingface.co/api/datasets/{src['repo']}/tree/{src['revision']}/data"
        tree = json.loads(_curl([url]).stdout)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(tree))
    out = []
    for f in tree:
        name = f["path"].rsplit("/", 1)[-1]
        if f["type"] == "file" and name.startswith(split + "-") and name.endswith(".parquet"):
            out.append({"path": f["path"], "size": f["size"], "sha256": f["lfs"]["oid"]})
    return sorted(out, key=lambda x: x["path"])


def shard_path(dataset, shard):
    return RAW / dataset / shard["path"].rsplit("/", 1)[-1]


def fetch_shard(dataset, shard, retries=5):
    """Download one shard if absent; verify size and sha256. Returns the local path."""
    src = SOURCES[dataset]
    dest = shard_path(dataset, shard)
    dest.parent.mkdir(parents=True, exist_ok=True)
    done = dest.with_suffix(".verified")
    if dest.exists() and done.exists():
        return dest
    if dest.exists() and dest.stat().st_size == shard["size"] and _sha256(dest) == shard["sha256"]:
        done.write_text(shard["sha256"] + "\n")
        return dest
    url = f"https://huggingface.co/datasets/{src['repo']}/resolve/{src['revision']}/{shard['path']}"
    tmp = dest.with_suffix(".part")
    for attempt in range(1, retries + 1):
        try:
            t0 = time.time()
            _curl(["-C", "-", "-o", str(tmp), url])
            size = tmp.stat().st_size
            if size != shard["size"]:
                raise IOError(f"size {size} != {shard['size']}")
            if _sha256(tmp) != shard["sha256"]:
                tmp.unlink()
                raise IOError("sha256 mismatch")
            tmp.rename(dest)
            done.write_text(shard["sha256"] + "\n")
            print(f"fetched {dest.name} {size / 1e6:.0f} MB in {time.time() - t0:.0f}s", file=sys.stderr)
            return dest
        except Exception as e:  # network hiccups: retry; curl resumes the .part file
            print(f"{dest.name}: attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(min(60, 5 * attempt))
    raise RuntimeError(f"could not fetch {shard['path']}")


def delete_shard(dataset, shard):
    for p in (shard_path(dataset, shard), shard_path(dataset, shard).with_suffix(".verified")):
        if p.exists():
            p.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["list", "fetch"])
    ap.add_argument("dataset", choices=sorted(SOURCES))
    ap.add_argument("split")
    ap.add_argument("--shards", type=int, nargs="*")
    a = ap.parse_args()
    shards = list_shards(a.dataset, a.split)
    if a.shards is not None:
        shards = [shards[i] for i in a.shards]
    if a.cmd == "list":
        for i, s in enumerate(shards):
            print(i, s["size"], s["path"])
        print(f"{len(shards)} shards, {sum(s['size'] for s in shards) / 1e9:.2f} GB")
        return
    for s in shards:
        fetch_shard(a.dataset, s)


if __name__ == "__main__":
    main()
