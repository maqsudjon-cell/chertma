# Uploading to Hugging Face — step by step

Everything here is prepared on this Mac and **nothing has been uploaded**. Do the steps in
order. Where there is a choice, the terminal way is more reliable for big files; the
website way is fine for small ones.

| Order | What | Folder | Upload now? |
|---|---|---|---|
| 1 | Lexicon dataset | `hf/uz-lexicon-skeleton/` | **yes** |
| 2 | Demo Space | `hf/space/` | **yes** (after 1, because it links to it) |
| 3 | Benchmark | `hf/uz-alphabet-bench/` | **no** — waits for your review |

---

## 0. One-time setup

### 0.1 Create an account

1. Open https://huggingface.co/join
2. Enter your email and a password, then pick a **username**. It becomes part of every
   address, e.g. `huggingface.co/datasets/USERNAME/uz-lexicon-skeleton`. Short and
   permanent: `maqsudjon`, `mpolatov`, …
3. Confirm the email Hugging Face sends you.

### 0.2 Put your username into the files

The cards and the Space link to each other through a placeholder, `HF_USERNAME`. Replace
it with your real username (write it where it says `your-username`):

```bash
cd ~/Downloads/chertma && grep -rl --include='*.md' --include='*.html' --include='*.py' HF_USERNAME hf | xargs sed -i '' 's/HF_USERNAME/your-username/g'
```

Check nothing is left (this should print nothing):

```bash
cd ~/Downloads/chertma && grep -rn --include='*.md' --include='*.html' --include='*.py' HF_USERNAME hf
```

### 0.3 Create an access token (only for the terminal way)

1. Open https://huggingface.co/settings/tokens
2. **Create new token** → Token type **Write** → name it `chertma-upload` → **Create token**.
3. Copy it. You see it only once. Do not paste it into any file in the repository.

### 0.4 Log in from the terminal (only for the terminal way)

The `hf` command is already installed on this Mac.

```bash
hf auth login
```

Paste the token when asked (nothing appears while you paste — that is normal), press Enter,
and answer `n` to "Add token as git credential?".

If you see `CERTIFICATE_VERIFY_FAILED`, the python.org Python on this Mac is missing its
certificate bundle; run this once and log in again:

```bash
open "/Applications/Python 3.13/Install Certificates.command"
```

---

## 1. Lexicon dataset — `uz-lexicon-skeleton`

Files (the three TSVs are not in git; they exist in this folder on this Mac):

| File | Bytes |
|---|---|
| `README.md` | 12,888 (before the username replacement) |
| `unigrams.tsv` | 122,955,106 |
| `skeleton-index.tsv` | 109,603,683 |
| `bigrams.tsv` | 463,187,708 |

If the TSVs are ever missing, rebuild them (about 8 minutes; needs `data/uz-unigrams.tsv` and
`data/uz-bigrams.tsv`): `tools/.venv/bin/python tools/build_hf_lexicon.py`

### 1.1 Create the dataset

1. Open https://huggingface.co/new-dataset
2. **Owner**: your username. **Dataset name**: `uz-lexicon-skeleton`.
3. **License**: `cc-by-4.0`.
4. **Public**.
5. **Create dataset**.

### 1.2 Upload — terminal way (recommended: the bigram file is 463 MB)

```bash
hf upload your-username/uz-lexicon-skeleton ~/Downloads/chertma/hf/uz-lexicon-skeleton . --repo-type dataset --commit-message "Uzbek frequency lexicon with skeleton index"
```

It shows progress for each file. On a slow connection the 463 MB file takes a while; if it
is interrupted, run the same command again — finished files are skipped.

### 1.2 Upload — website way (alternative)

1. On the dataset page, open **Files and versions** → **Add file** → **Upload files**.
2. Drag in all four files from `~/Downloads/chertma/hf/uz-lexicon-skeleton/`.
3. Commit message `Uzbek frequency lexicon with skeleton index` → **Commit changes to main**.
4. Keep the tab open until it finishes. If the 463 MB upload fails in the browser, use the
   terminal way for that file.

### 1.3 Check

1. The dataset page shows the card, starting with "Derived from tahrirchi/uz-books-v2 (MIT) …".
2. The **Dataset Viewer** on the page shows two subsets, `unigrams` and `bigrams`. The first
   rows should be `va 43338110 va` and `özbekiston respublikasi 1473482`. The viewer can take
   several minutes to appear. `skeleton-index.tsv` has no viewer on purpose (its rows have
   different lengths); it is still downloadable under **Files and versions**.
3. If the card shows a yellow "metadata" warning, open it and read the message — the YAML
   block at the top of `README.md` is where to fix it.

---

## 2. Demo Space — `chertma`

A copy of the site as a static Space: 24 files, 2,780,352 bytes.

| File | Bytes |
|---|---|
| `README.md` | 2,468 (before the username replacement) |
| `index.html` | 7,619 |
| `app.js` | 12,464 |
| `style.css` | 7,042 |
| `sw.js` | 1,388 |
| `manifest.json` | 674 |
| `icon.svg` | 2,276 |
| `icons/apple-touch-icon.png` | 937 |
| `icons/icon-192.png` | 978 |
| `icons/icon-512.png` | 4,174 |
| `icons/maskable-512.png` | 3,457 |
| `fonts/JetBrainsMono-Regular.ttf` | 270,224 |
| `fonts/JetBrainsMono-Bold.ttf` | 274,096 |
| `fonts/OFL.txt` | 4,399 |
| `data/lexicon-lite.bin.gz` | 739,813 |
| `data/lexicon-lite.bin` | 1,411,032 |
| `engine/index.js` | 11,773 |
| `engine/translit.js` | 5,494 |
| `engine/lexicon.js` | 5,800 |
| `engine/rank.js` | 4,643 |
| `engine/normalize.js` | 4,115 |
| `engine/skeleton.js` | 2,092 |
| `engine/learn.js` | 1,943 |
| `engine/constants.js` | 1,451 |

If the folder is ever missing or `web/` changes, rebuild it:
`python3 tools/build_site.py && python3 tools/build_hf_space.py` — then do step 0.2 again,
because the rebuild restores the `HF_USERNAME` placeholder in `index.html`.

### 2.1 Create the Space

1. Open https://huggingface.co/new-space
2. **Owner**: your username. **Space name**: `chertma`.
3. **License**: leave empty (no code licence has been chosen yet).
4. **Select the Space SDK**: **Static**. Template: **Blank**.
5. **Space hardware**: CPU basic (free).
6. **Public** → **Create Space**.

### 2.2 Upload — terminal way

```bash
hf upload your-username/chertma ~/Downloads/chertma/hf/space . --repo-type space --commit-message "Chertma demo"
```

This replaces the Space's placeholder `README.md` and `index.html` with ours.

### 2.2 Upload — website way (alternative)

1. In the Space, open **Files** → **Add file** → **Upload files**.
2. Open `~/Downloads/chertma/hf/space/` in Finder, select **everything inside it** (including
   the folders `data`, `engine`, `fonts`, `icons`) and drag it into the browser window. Chrome
   keeps the folder structure.
3. **Commit changes to main**. Hugging Face asks to overwrite `README.md` and `index.html` —
   yes.

### 2.3 Check

1. Open the **App** tab. It should read "Oddiy klaviaturada yozing — töğri özbekça oling."
2. Click the example `togri gap, ozbekcha…` — the first box shows `töğri gap, özbekça yoziş oson`.
3. The footer links to `chertma.maqsudjon.com` and to your `uz-lexicon-skeleton` dataset.
4. The Space runs inside a frame on huggingface.co, so the "works offline" indicator may not
   turn green there. That is expected; it works on the Space's own address
   (`https://your-username-chertma.static.hf.space`).

---

## 3. Benchmark — `uz-alphabet-bench` — NOT NOW

The folder holds only the card and the evaluator:

| File | Bytes |
|---|---|
| `README.md` | 7,558 |
| `run_eval.py` | 11,276 |
| `chertma_mcq.mjs` | 1,137 |

There is no `dev.jsonl` or `test.jsonl` — they wait for your review. When you are ready:

1. Review every row of `bench/review.md` and mark it `keep`, `fix: …` or `drop`.
2. `tools/.venv/bin/python tools/build_benchmark.py --export` → writes `bench/dev.jsonl` and
   `bench/test.jsonl` from the rows you kept.
3. Copy both into `hf/uz-alphabet-bench/`.
4. In `hf/uz-alphabet-bench/README.md`: replace every `PLACEHOLDER` (counts, authors, review,
   contact), and **delete the first line** ("NOT READY — …") so the card's metadata block is
   at the very top.
5. Check the evaluator still works: `python3 hf/uz-alphabet-bench/run_eval.py --self-test`
6. Decide where it lives. If you co-publish with Tahrirchi, create it under a shared
   organization (https://huggingface.co/organizations/new) rather than your own name.
7. Create the dataset at https://huggingface.co/new-dataset (licence `cc-by-4.0`), then:

```bash
hf upload OWNER/uz-alphabet-bench ~/Downloads/chertma/hf/uz-alphabet-bench . --repo-type dataset --commit-message "uz-alphabet-bench v1"
```

8. Run a baseline and put it in the card:

```bash
python3 ~/Downloads/chertma/hf/uz-alphabet-bench/run_eval.py --items ~/Downloads/chertma/hf/uz-alphabet-bench/test.jsonl --backend chertma --write-readme ~/Downloads/chertma/hf/uz-alphabet-bench/README.md
```

---

## Afterwards (optional)

- Log out of the terminal when done: `hf auth logout`.
- The live site `chertma.maqsudjon.com` does not link to the dataset yet; `web/` was left
  unchanged on purpose.
