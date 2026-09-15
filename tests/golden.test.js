// tests/golden.json — see its _doc. Strict cases must all pass; ranked and
// real-world cases are measurements, printed as diagnostics.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { engine, json } from './helpers.js';
import { tokenize, normalize, convert } from '../engine/index.js';
import { RANKED_FLOOR } from './thresholds.js';

const G = json('tests/golden.json');
const engines = {};
const get = async (script) => (engines[script] ??= await engine({ script }));

test('golden: strict cases', async (t) => {
  const byCat = {};
  for (const c of G.strict) (byCat[c.category] ??= []).push(c);
  for (const [cat, cases] of Object.entries(byCat)) {
    await t.test(`${cat} (${cases.length})`, async () => {
      const bad = [];
      for (const c of cases) {
        const got = (await get(c.script)).autocorrect(c.input);
        if (got !== c.expected) bad.push(`${c.id}\n  input:    ${c.input}\n  expected: ${c.expected}\n  got:      ${got}`);
      }
      assert.equal(bad.length, 0, `${bad.length} failing:\n${bad.slice(0, 10).join('\n')}`);
    });
  }
});

test('golden: ranked cases (several candidates survive)', async (t) => {
  const c = await get('new');
  let ok = 0;
  const misses = [];
  for (const r of G.ranked) {
    const got = c.autocorrect(r.input);
    if (got === r.expected) ok++;
    else misses.push(`${r.id}: ${got}  ≠  ${r.expected}`);
  }
  const acc = ok / G.ranked.length;
  t.diagnostic(`ranked sentence accuracy: ${ok}/${G.ranked.length} = ${(100 * acc).toFixed(1)} %`);
  for (const m of misses.slice(0, 5)) t.diagnostic(m);
  assert.ok(acc >= RANKED_FLOOR, `accuracy ${acc} below floor ${RANKED_FLOOR}`);
});

const fold = (s) => Array.from(normalize(s), (ch) => ("'`´‘’ʻʼʽʿ′".includes(ch) ? "'" : ch)).join('');

// A token counts as *corrected* when the output is the expected word, *wrong*
// when the engine substituted some other word, and *missed* when it left the
// token as typed or only converted its script (the same letters, e.g. булган →
// bulgan). Wrong corrections are the failure this product exists to avoid.
export function tokenOutcomes(input, output, expected) {
  const toks = (s) => tokenize(s).filter((x) => x.kind === 'token').map((x) => s.slice(x.start, x.end));
  const [a, b, e] = [toks(input), toks(output), toks(expected)];
  const res = { correct: 0, wrong: 0, missed: 0, kept: 0, misaligned: 0, wrongExamples: [] };
  if (a.length !== b.length || a.length !== e.length) { res.misaligned = 1; return res; }
  for (let i = 0; i < a.length; i++) {
    const asTyped = fold(convert(a[i], /[\u0400-\u052f]/.test(a[i]) ? 'cyrillic' : 'old', 'new'));
    const out = fold(b[i]);
    const inputNeedsChange = fold(a[i]) !== fold(e[i]) && asTyped !== fold(e[i]);
    if (out === fold(e[i])) { if (inputNeedsChange) res.correct++; else res.kept++; }
    else if (out === fold(a[i]) || out === asTyped) res.missed++;
    else { res.wrong++; res.wrongExamples.push(`${a[i]} → ${b[i]} (expected ${e[i]})`); }
  }
  return res;
}

test('golden: real-world sample (measurement)', async (t) => {
  const c = await get('new');
  for (const kind of ['latin_apostropheless', 'cyr_russian_layout']) {
    const tot = { correct: 0, wrong: 0, missed: 0, kept: 0, misaligned: 0, wrongExamples: [] };
    for (const r of G.realworld.filter((x) => x.kind === kind)) {
      const o = tokenOutcomes(r.input, c.autocorrect(r.input), r.expected);
      for (const k of ['correct', 'wrong', 'missed', 'kept', 'misaligned']) tot[k] += o[k];
      tot.wrongExamples.push(...o.wrongExamples);
    }
    const changed = tot.correct + tot.wrong;
    t.diagnostic(`${kind}: corrected ${tot.correct}; wrong corrections ${tot.wrong} ` +
      `(precision ${(100 * tot.correct / Math.max(1, changed)).toFixed(1)} %); missed ${tot.missed}; ` +
      `already right or converted right ${tot.kept}; misaligned sentences ${tot.misaligned}`);
    for (const w of tot.wrongExamples.slice(0, 12)) t.diagnostic(`  wrong: ${w}`);
  }
});
