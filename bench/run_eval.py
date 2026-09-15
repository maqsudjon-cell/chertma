"""Score a system on uz-alphabet-bench and print per-category accuracy.

Backends:
  chertma   the engine in this repository (runs bench/chertma_mcq.mjs with node)
  hf        a Hugging Face causal LM: each option scored by log-likelihood
            (needs `pip install torch transformers`; not a dependency of this repo)
  api       an OpenAI-compatible chat endpoint: the model answers A/B/C/D
            (URL via --endpoint, key via the EVAL_API_KEY environment variable)

  python bench/run_eval.py --items bench/test.jsonl --backend chertma
  python bench/run_eval.py --items bench/test.jsonl --backend hf --model <hf-model-id>
  python bench/run_eval.py --items bench/test.jsonl --backend api --endpoint <url> --model <name>
  add --write-readme to put the result row into bench/README.md's leaderboard

The benchmark is not released: bench/test.jsonl exists only after the human
has reviewed bench/review.md and run `tools/build_benchmark.py --export`.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LETTERS = "ABCD"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def prompt(item):
    ctx = f"Gap: {item['context']}\n" if item.get("context") else ""
    opts = "\n".join(f"{LETTERS[i]}) {o}" for i, o in enumerate(item["options"]))
    return f"{ctx}{item['question']}\n{opts}\nJavob (faqat harf):"


def run_chertma(items):
    proc = subprocess.run(["node", str(ROOT / "bench" / "chertma_mcq.mjs")], input=json.dumps(items),
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def run_hf(items, model_id):
    import torch  # noqa: PLC0415
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)
    model.eval()
    answers = []
    for it in items:
        base = prompt(it).rsplit("\n", 1)[0] + "\nJavob: "
        scores = []
        for opt in it["options"]:
            ids = tok(base + opt, return_tensors="pt").input_ids
            n_base = tok(base, return_tensors="pt").input_ids.shape[1]
            with torch.no_grad():
                logits = model(ids).logits
            logp = torch.log_softmax(logits[0, :-1], dim=-1)
            target = ids[0, 1:]
            scores.append(logp[n_base - 1:].gather(1, target[n_base - 1:, None]).sum().item())
        answers.append(max(range(len(scores)), key=scores.__getitem__))
    return answers


def run_api(items, endpoint, model):
    key = os.environ.get("EVAL_API_KEY", "")
    answers = []
    for it in items:
        body = json.dumps({"model": model, "temperature": 0, "max_tokens": 4,
                           "messages": [{"role": "user", "content": prompt(it)}]}).encode()
        req = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json",
                                                                   "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=120) as r:
            text = json.load(r)["choices"][0]["message"]["content"]
        m = re.search(r"[ABCD]", text.upper())
        answers.append(LETTERS.index(m.group(0)) if m else -1)
    return answers


def score(items, answers):
    per = defaultdict(lambda: [0, 0])
    for it, a in zip(items, answers):
        per[it["category"]][1] += 1
        per[it["category"]][0] += int(a == it["answer"])
    total = [sum(v[0] for v in per.values()), sum(v[1] for v in per.values())]
    return per, total


def write_readme(name, per, total):
    path = ROOT / "bench" / "README.md"
    text = path.read_text(encoding="utf-8")
    cats = ["ascii2new", "old2new", "cyr2new", "preserve", "ambiguity", "apostrophe", "edge"]
    start, end = "<!-- leaderboard:start -->", "<!-- leaderboard:end -->"
    block = text[text.index(start) + len(start):text.index(end)]
    rows = [l for l in block.strip().splitlines() if l.startswith("| ") and not l.startswith("| System") and not l.startswith("|---")]
    rows = [r for r in rows if not r.startswith(f"| {name} |")]
    cell = lambda c: f"{100 * per[c][0] / per[c][1]:.1f}" if per[c][1] else "–"  # noqa: E731
    rows.append(f"| {name} | {100 * total[0] / max(1, total[1]):.1f} | " + " | ".join(cell(c) for c in cats) + " |")
    table = "\n| System | All | " + " | ".join(cats) + " |\n|---|---|" + "---|" * len(cats) + "\n" + "\n".join(rows) + "\n"
    path.write_text(text[:text.index(start) + len(start)] + table + text[text.index(end):], encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--backend", choices=["chertma", "hf", "api"], required=True)
    ap.add_argument("--model")
    ap.add_argument("--endpoint")
    ap.add_argument("--name")
    ap.add_argument("--write-readme", action="store_true")
    a = ap.parse_args()
    items = load(a.items)
    if a.backend == "chertma":
        answers = run_chertma(items)
    elif a.backend == "hf":
        answers = run_hf(items, a.model)
    else:
        answers = run_api(items, a.endpoint, a.model)
    per, total = score(items, answers)
    name = a.name or (a.model if a.backend != "chertma" else "Chertma engine (lite)")
    print(f"{name}: {total[0]}/{total[1]} = {100 * total[0] / max(1, total[1]):.1f} %")
    for cat, (ok, n) in sorted(per.items()):
        print(f"  {cat:12} {ok}/{n} = {100 * ok / n:.1f} %")
    if a.write_readme:
        write_readme(name, per, total)


if __name__ == "__main__":
    main()
