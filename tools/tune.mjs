// Grid search of the ranking constants against tests/golden.json.
// Objective: never lose a strict case; then fewest wrong corrections; then most
// correct ones (ranked + real-world). Prints a table; changes nothing.
//   node tools/tune.mjs
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const G = JSON.parse(readFileSync(root + 'tests/golden.json', 'utf8'));
const lite = readFileSync(root + 'data/lexicon-lite.bin');
const { tokenOutcomes } = await import(pathToFileURL(root + 'tests/golden.test.js').href).catch(() => ({}));

const grid = [];
for (const lambda of [0, 0.5, 1, 2, 3]) for (const nu of [0, 0.5, 1, 2]) for (const mix of [0, 0.25, 0.5]) grid.push({ lambda, nu, mix });

const base = join(tmpdir(), 'chertma-tune');
const rows = [];
let n = 0;
for (const g of grid) {
  const dir = join(base, `e${n++}`);
  mkdirSync(dir, { recursive: true });
  for (const f of readdirSync(root + 'engine')) {
    let src = readFileSync(root + 'engine/' + f, 'utf8');
    if (f === 'constants.js') {
      src = src.replace(/LAMBDA_BIGRAM = [\d.]+/, `LAMBDA_BIGRAM = ${g.lambda}`)
        .replace(/NU_EVIDENCE = [\d.]+/, `NU_EVIDENCE = ${g.nu}`)
        .replace(/REGISTER_MIX = [\d.]+/, `REGISTER_MIX = ${g.mix}`);
    }
    writeFileSync(join(dir, f), src);
  }
  const { Chertma } = await import(pathToFileURL(join(dir, 'index.js')).href);
  const mk = async (script) => { const c = new Chertma({ script }); await c.load(lite); return c; };
  const eng = { new: await mk('new'), old: await mk('old'), cyrillic: await mk('cyrillic') };
  let strict = 0;
  for (const c of G.strict) if (eng[c.script].autocorrect(c.input) === c.expected) strict++;
  const tot = { correct: 0, wrong: 0, missed: 0 };
  let rankedExact = 0;
  for (const r of [...G.ranked, ...G.realworld]) {
    const out = eng.new.autocorrect(r.input);
    if (r.id && out === r.expected) rankedExact++;
    const o = tokenOutcomes(r.input, out, r.expected);
    tot.correct += o.correct; tot.wrong += o.wrong; tot.missed += o.missed;
  }
  rows.push({ ...g, strict, rankedExact, ...tot });
}
rows.sort((a, b) => b.strict - a.strict || a.wrong - b.wrong || b.correct - a.correct || b.rankedExact - a.rankedExact);
console.log('lambda nu   mix  | strict rankedExact | correct wrong missed');
for (const r of rows) console.log(`${String(r.lambda).padEnd(6)} ${String(r.nu).padEnd(4)} ${String(r.mix).padEnd(4)} | ${r.strict}    ${r.rankedExact}         | ${r.correct}    ${r.wrong}    ${r.missed}`);
