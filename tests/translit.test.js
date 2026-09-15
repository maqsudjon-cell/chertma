// SPEC §6. Round trips over every lexicon word, the golden file in both
// directions, and uz-books-v2's own lat/cyr pairs as an independent check.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { engine, json, root } from './helpers.js';
import { convert, newToCyrLower, cyrToNewLower, newToOldLower, oldToNewLower, tokenize, casePattern } from '../engine/index.js';
import { BOOKS_AGREEMENT_FLOOR } from './thresholds.js';

// Q2 as ruled drops ъ before е ё ю я, so a word with ʼ before e, ye, yo, yu or
// ya (books write obʼekt, maʼyus) cannot survive new → Cyrillic → new.
// Reopened as Q2b; counted, not failed.
const Q2B = /ʼ(?:e|y[eoua])/;
// Old Latin writes oʻ and gʻ with an apostrophe, so a plain o or g followed by
// the tutuq is ambiguous in that script (§6.2). Counted, not failed.
const OLD_AMBIGUOUS = /[og]ʼ/;

for (const build of ['lite', 'full']) {
  test(`new → cyrillic → new for every ${build} word`, async (t) => {
    const c = await engine({}, `data/lexicon-${build}.bin`);
    const fails = [];
    let q2b = 0;
    for (let i = 0; i < c.lex.size; i++) {
      const w = c.lex.word(i);
      const cy = newToCyrLower(w);
      if (cyrToNewLower(cy) === w) continue;
      if (Q2B.test(w)) q2b++;
      else fails.push(`${w} → ${cy} → ${cyrToNewLower(cy)}`);
    }
    t.diagnostic(`${c.lex.size} words; ${q2b} fail only because of the Q2 ъ rule (Q2b)`);
    assert.equal(fails.length, 0, fails.slice(0, 20).join('\n'));
  });

  test(`new → old → new for every ${build} word`, async (t) => {
    const c = await engine({}, `data/lexicon-${build}.bin`);
    const fails = [];
    let ambiguous = 0;
    for (let i = 0; i < c.lex.size; i++) {
      const w = c.lex.word(i);
      if (oldToNewLower(newToOldLower(w)) === w) continue;
      if (OLD_AMBIGUOUS.test(w)) ambiguous++;
      else fails.push(w);
    }
    t.diagnostic(`${ambiguous} words with o or g before a tutuq cannot be written unambiguously in old Latin`);
    assert.equal(fails.length, 0, fails.slice(0, 20).join(', '));
  });
}

test('golden file converts in both directions', (t) => {
  const G = json('tests/golden.json');
  const bad = [];
  let skipped = 0;
  // Round trips hold for ordinary words. A token glued to a digit, in mixed case or
  // in mixed script is transliterated by rule (§6.5) and need not survive a round trip.
  const words = (s) => tokenize(s).filter((x) => x.kind === 'token' && casePattern(s.slice(x.start, x.end)) !== 'mixed')
    .map((x) => s.slice(x.start, x.end));
  const roundTrip = (e, via) => {
    const back = convert(convert(e, 'new', via), via, 'new');
    const a = words(e);
    const b = words(back);
    if (a.length !== b.length) return false;
    skipped += tokenize(e).filter((x) => x.kind !== 'gap').length - a.length;
    // Letters outside the Uzbek alphabet (COVID: c) have no way back from Cyrillic.
    const uzbek = (w) => !/[cw\u00c0-\u00e6\u00e8-\u00f5\u00f8-\u015e\u0160-\u024f]/i.test(w);
    skipped += a.filter((w) => !uzbek(w)).length;
    return a.every((w, i) => !uzbek(w) || w === b[i]);
  };
  for (const g of G.strict) {
    if (g.script !== 'new') continue;
    const e = g.expected;
    if (!Q2B.test(e) && !roundTrip(e, 'cyrillic')) bad.push(`cyr: ${e}`);
    if (!OLD_AMBIGUOUS.test(e) && !roundTrip(e, 'old')) bad.push(`old: ${e}`);
    if (g.category === 'old2new' && convert(g.input, 'old', 'new') !== e) bad.push(`old→new: ${g.input}`);
    if (g.category === 'cyr2new' && convert(g.input, 'cyrillic', 'new') !== e) bad.push(`cyr→new: ${g.input}`);
  }
  t.diagnostic(`${skipped} glued, mixed-case, protected or non-Uzbek-alphabet tokens not held to the round trip`);
  assert.equal(bad.length, 0, bad.slice(0, 10).join('\n'));
});

test('output is never mixed-script (§6.5): every golden input, every script', async () => {
  const G = json('tests/golden.json');
  const bad = [];
  for (const script of ['new', 'old', 'cyrillic']) {
    const c = await engine({ script });
    for (const g of G.strict.concat(G.ranked ?? [])) {
      const out = c.autocorrect(g.input);
      for (const x of tokenize(out)) {
        if (x.kind === 'gap' || (x.kind === 'protected' && !x.glued)) continue;
        const tok = out.slice(x.start, x.end);
        if (script === 'cyrillic' ? /[A-Za-z\u00c0-\u024f]/.test(tok) : /[\u0400-\u052f]/.test(tok)) bad.push(`${script}: ${tok} in ${out}`);
      }
      const from = /[\u0400-\u052f]/.test(g.input) ? 'cyrillic' : 'old';
      if (from === script) continue;  // §7.4: convert(text, s, s) returns text as it is
      const conv = convert(g.input, from, script);
      for (const x of tokenize(conv)) {
        if (x.kind === 'gap' || (x.kind === 'protected' && !x.glued)) continue;
        const tok = conv.slice(x.start, x.end);
        if (script === 'cyrillic' ? /[A-Za-z\u00c0-\u024f]/.test(tok) : /[\u0400-\u052f]/.test(tok)) bad.push(`convert ${script}: ${tok}`);
      }
    }
  }
  assert.equal(bad.length, 0, bad.slice(0, 10).join('\n'));
});


const PAIRS = 'tests/fixtures/books-pairs.tsv';
test('independent check: uz-books-v2 lat and cyr splits agree with our rules', { skip: !existsSync(root + PAIRS) && 'books-pairs fixture not built' }, (t) => {
  const rows = readFileSync(root + PAIRS, 'utf8').split('\n').filter((l) => l && !l.startsWith('#')).slice(1);
  let agree = 0;
  let total = 0;
  const diffs = [];
  for (const line of rows) {
    const [cyr, lat, count] = line.split('\t');
    const n = Number(count);
    const a = convert(cyr, 'cyrillic', 'new');
    const b = convert(lat, 'old', 'new');
    total += n;
    if (a === b) agree += n;
    else diffs.push([n, `${cyr} → ${a}  |  ${lat} → ${b}`]);
  }
  diffs.sort((x, y) => y[0] - x[0]);
  const rate = agree / total;
  t.diagnostic(`token agreement ${(100 * rate).toFixed(2)} % over ${total} aligned tokens (${rows.length} distinct pairs)`);
  for (const [n, d] of diffs.slice(0, 15)) t.diagnostic(`  ×${n} ${d}`);
  assert.ok(rate >= BOOKS_AGREEMENT_FLOOR, `agreement ${rate} below ${BOOKS_AGREEMENT_FLOOR}`);
});
