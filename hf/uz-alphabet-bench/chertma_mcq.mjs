// Answers uz-alphabet-bench items with the Chertma engine (github.com/maqsudjon-cell/chertma).
// Usage: node chertma_mcq.mjs <path-to-chertma-checkout> < items.json > answers.json
// The quoted word in each question goes through autocorrect() in new Latin; the option
// equal to the output is chosen. Output unchanged and an "o'zgarmaydi" option present →
// that option. Otherwise −1 (no answer, scored wrong).
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const repo = resolve(process.argv[2] ?? '.');
const { Chertma } = await import(pathToFileURL(resolve(repo, 'engine/index.js')).href);
const items = JSON.parse(readFileSync(0, 'utf8'));
const c = new Chertma({ script: 'new' });
await c.load(readFileSync(resolve(repo, 'data/lexicon-lite.bin')));

const answers = items.map((it) => {
  const m = it.question.match(/"([^"]+)"/);
  if (!m) return -1;
  const out = c.autocorrect(m[1]);
  let i = it.options.indexOf(out);
  if (i < 0 && out === m[1]) i = it.options.indexOf("o'zgarmaydi");
  return i;
});
process.stdout.write(JSON.stringify(answers));
