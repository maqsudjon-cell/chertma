#!/usr/bin/env python3
"""Evaluate a system on uz-alphabet-bench; print per-category accuracy.

Backends
  chertma  the Chertma engine — needs node and a checkout of github.com/maqsudjon-cell/chertma
  api      an OpenAI-compatible chat endpoint; the model answers A/B/C/D
           (--endpoint URL, --model NAME, key from the EVAL_API_KEY environment variable)
  hf       a Hugging Face causal language model; each option scored by log-likelihood
           (needs `pip install torch transformers`)

Items come from a local JSONL file (--items) or from the Hub (--dataset, --split;
needs `pip install datasets`). Only the standard library is needed otherwise.

  python run_eval.py --items test.jsonl --backend chertma --chertma-repo ../chertma
  python run_eval.py --dataset HF_USERNAME/uz-alphabet-bench --split test --backend api --endpoint https://…/v1/chat/completions --model NAME
  python run_eval.py --items test.jsonl --backend hf --model ORG/MODEL
  python run_eval.py --self-test --chertma-repo ../chertma   # checks this script; uses no benchmark items

Add --write-readme README.md to put the result row into the card's leaderboard.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LETTERS = "ABCD"
CATEGORIES = ["ascii2new", "old2new", "cyr2new", "preserve", "ambiguity", "apostrophe", "edge"]
UNCHANGED = "o'zgarmaydi"


def load_items(args):
    if args.items:
        with open(args.items, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    from datasets import load_dataset  # noqa: PLC0415  (optional dependency)
    return [dict(r) for r in load_dataset(args.dataset, split=args.split)]


def prompt(item):
    ctx = f"Gap: {item['context']}\n" if item.get("context") else ""
    opts = "\n".join(f"{LETTERS[i]}) {o}" for i, o in enumerate(item["options"]))
    return f"{ctx}{item['question']}\n{opts}\nJavob (faqat harf):"


def run_chertma(items, repo):
    script = HERE / "chertma_mcq.mjs"
    proc = subprocess.run(["node", str(script), str(repo)], input=json.dumps(items),
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def run_api(items, endpoint, model):
    key = os.environ.get("EVAL_API_KEY", "")
    answers = []
    for it in items:
        body = json.dumps({"model": model, "temperature": 0, "max_tokens": 4,
                           "messages": [{"role": "user", "content": prompt(it)}]}).encode()
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(endpoint, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                text = json.load(r)["choices"][0]["message"]["content"]
        except Exception as e:  # one failed request is one unanswered item, not a crash
            print(f"  {it.get('id')}: request failed ({type(e).__name__})", file=sys.stderr)
            answers.append(-1)
            continue
        m = re.search(r"\b([ABCD])\b", text.upper())
        answers.append(LETTERS.index(m.group(1)) if m else -1)
    return answers


def run_hf(items, model_id):
    import torch  # noqa: PLC0415
    from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: PLC0415

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id)
    model.eval()
    answers = []
    for it in items:
        base = prompt(it).rsplit("\n", 1)[0] + "\nJavob: "
        n_base = tok(base, return_tensors="pt").input_ids.shape[1]
        scores = []
        for opt in it["options"]:
            ids = tok(base + opt, return_tensors="pt").input_ids
            with torch.no_grad():
                logp = torch.log_softmax(model(ids).logits[0, :-1], dim=-1)
            target = ids[0, 1:]
            scores.append(logp[n_base - 1:].gather(1, target[n_base - 1:, None]).sum().item())
        answers.append(max(range(len(scores)), key=scores.__getitem__))
    return answers


def score(items, answers):
    per = defaultdict(lambda: [0, 0])
    for it, a in zip(items, answers):
        per[it["category"]][1] += 1
        per[it["category"]][0] += int(a == it["answer"])
    ok = sum(v[0] for v in per.values())
    n = sum(v[1] for v in per.values())
    return per, (ok, n)


def report(name, per, total):
    lines = [f"{name}: {total[0]}/{total[1]} = {100 * total[0] / max(1, total[1]):.1f} %"]
    for cat in CATEGORIES:
        if per[cat][1]:
            lines.append(f"  {cat:11} {per[cat][0]}/{per[cat][1]} = {100 * per[cat][0] / per[cat][1]:.1f} %")
    return "\n".join(lines)


def write_readme(path, name, per, total):
    text = Path(path).read_text(encoding="utf-8")
    start, end = "<!-- leaderboard:start -->", "<!-- leaderboard:end -->"
    if start not in text or end not in text:
        raise SystemExit(f"{path} has no leaderboard markers")
    block = text[text.index(start) + len(start):text.index(end)]
    rows = [r for r in block.splitlines() if r.startswith("| ") and not r.startswith("| System") and not r.startswith(f"| {name} |")]
    cell = lambda c: f"{100 * per[c][0] / per[c][1]:.1f}" if per[c][1] else "–"  # noqa: E731
    rows.append(f"| {name} | {100 * total[0] / max(1, total[1]):.1f} | " + " | ".join(cell(c) for c in CATEGORIES) + " |")
    table = ("\n| System | All | " + " | ".join(CATEGORIES) + " |\n|---|---|" + "---|" * len(CATEGORIES) + "\n"
             + "\n".join(rows) + "\n")
    Path(path).write_text(text[:text.index(start) + len(start)] + table + text[text.index(end):], encoding="utf-8")


# --- self-test: synthetic items written for this check, not benchmark items ------------------

SELF_TEST_ITEMS = [
    {"id": "T1", "category": "ascii2new", "context": None, "question": "\"togri\" so'zining yangi alifbodagi to'g'ri shakli qaysi?",
     "options": ["togri", "töğri", "toʻgʻri", "tögri"], "answer": 1},
    {"id": "T2", "category": "ascii2new", "context": None, "question": "\"wunaqa\" so'zining yangi alifbodagi to'g'ri shakli qaysi?",
     "options": ["wunaqa", "shunaqa", "şunaqa", "sunaqa"], "answer": 2},
    {"id": "T3", "category": "old2new", "context": None, "question": "Eski lotindagi \"oʻzbekcha\" so'zi yangi alifboda qanday yoziladi?",
     "options": ["özbekça", "ozbekça", "özbekcha", "oʻzbekça"], "answer": 0},
    {"id": "T4", "category": "cyr2new", "context": None, "question": "Kirilldagi \"тўғри\" so'zining yangi lotin alifbosidagi to'g'ri shakli qaysi?",
     "options": ["tugri", "toğri", "tögri", "töğri"], "answer": 3},
    {"id": "T5", "category": "preserve", "context": None, "question": "Avtomatik tuzatishda \"kelaslar\" so'zi qanday bo'lishi kerak?",
     "options": ["kelasizlar", UNCHANGED, "kelaşlar", "Kelaslar"], "answer": 1},
    {"id": "T6", "category": "preserve", "context": None, "question": "Avtomatik tuzatishda \"qisela\" so'zi qanday bo'lishi kerak?",
     "options": ["qilsanglar", "qişela", UNCHANGED, "Qisela"], "answer": 2},
]


def self_test(repo):
    failures = []
    per, total = score(SELF_TEST_ITEMS, run_chertma(SELF_TEST_ITEMS, repo))
    print(report("self-test · chertma backend", per, total))
    if total[0] != total[1]:
        failures.append("chertma backend did not answer every synthetic item correctly")

    class Fake(BaseHTTPRequestHandler):
        def do_POST(self):  # an OpenAI-style reply that always picks the right letter
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            asked = body["messages"][0]["content"]
            item = next(i for i in SELF_TEST_ITEMS if i["question"] in asked)
            out = json.dumps({"choices": [{"message": {"content": f"Javob: {LETTERS[item['answer']]}"}}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        per, total = score(SELF_TEST_ITEMS, run_api(SELF_TEST_ITEMS, f"http://127.0.0.1:{server.server_port}/v1/chat/completions", "fake"))
    finally:
        server.shutdown()
    print(report("self-test · api backend against a local fake endpoint", per, total))
    if total[0] != total[1]:
        failures.append("api backend did not parse the fake endpoint's answers")

    with tempfile.TemporaryDirectory() as d:
        card = Path(d) / "README.md"
        card.write_text("x\n<!-- leaderboard:start -->\nold\n<!-- leaderboard:end -->\ny\n", encoding="utf-8")
        write_readme(card, "Fake system", per, total)
        written = card.read_text(encoding="utf-8")
        if "| Fake system | 100.0 |" not in written or not written.endswith("<!-- leaderboard:end -->\ny\n"):
            failures.append("leaderboard writer produced an unexpected table")
        else:
            print("self-test · leaderboard writer: ok")

    if failures:
        print("SELF-TEST FAILED:\n  " + "\n  ".join(failures))
        sys.exit(1)
    print("SELF-TEST PASSED (hf backend not exercised: needs torch and a model)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--items", help="local JSONL file")
    src.add_argument("--dataset", help="Hub dataset id")
    ap.add_argument("--split", default="test")
    ap.add_argument("--backend", choices=["chertma", "api", "hf"])
    ap.add_argument("--chertma-repo", default=str(HERE.parent.parent), help="path to a chertma checkout (default: this repository)")
    ap.add_argument("--model")
    ap.add_argument("--endpoint")
    ap.add_argument("--name", help="leaderboard row name")
    ap.add_argument("--write-readme", metavar="README.md")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test(args.chertma_repo)
        return
    if not (args.items or args.dataset) or not args.backend:
        ap.error("--items or --dataset, and --backend, are required")
    items = load_items(args)
    if args.backend == "chertma":
        answers = run_chertma(items, args.chertma_repo)
    elif args.backend == "api":
        if not (args.endpoint and args.model):
            ap.error("--backend api needs --endpoint and --model")
        answers = run_api(items, args.endpoint, args.model)
    else:
        if not args.model:
            ap.error("--backend hf needs --model")
        answers = run_hf(items, args.model)
    per, total = score(items, answers)
    name = args.name or ("Chertma engine (lite lexicon)" if args.backend == "chertma" else args.model)
    print(report(name, per, total))
    if args.write_readme:
        write_readme(args.write_readme, name, per, total)


if __name__ == "__main__":
    main()
