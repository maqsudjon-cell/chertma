// Answers uz-alphabet-bench items with the Chertma engine: the quoted word in
// the question (or the blank in the context) is run through autocorrect() in
// new Latin, and the option equal to the output is chosen. Output unchanged
// and an "o'zgarmaydi" option present → that option. Otherwise −1 (no answer).
// stdin: JSON array of items; stdout: JSON array of answer indices.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Chertma } from '../engine/index.js';

const root = fileURLToPath(new URL('..', import.meta.url));
const items = JSON.parse(readFileSync(0, 'utf8'));
const c = new Chertma({ script: 'new' });
await c.load(readFileSync(root + 'data/lexicon-lite.bin'));

const answers = items.map((it) => {
  const m = it.question.match(/"([^"]+)"/);
  const word = m ? m[1] : null;
  if (!word) return -1;
  const out = c.autocorrect(word);
  let i = it.options.indexOf(out);
  if (i < 0 && out === word) i = it.options.indexOf("o'zgarmaydi");
  return i;
});
process.stdout.write(JSON.stringify(answers));
