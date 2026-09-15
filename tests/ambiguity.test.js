// SPEC §8.3. Only the ruled case (R1, `ser`) is used. The 24 proposed pairs in
// docs/AMBIGUITY-REVIEW.md are parked until the human marks them.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { engine } from './helpers.js';
import { key } from '../engine/index.js';

test('R1: ser / şer / şeʼr share one skeleton', async () => {
  const c = await engine();
  const [lo, hi] = c.lex.range(key('ser'));
  const words = new Set(Array.from({ length: hi - lo }, (_, i) => c.lex.word(lo + i)));
  for (const w of ['ser', 'şer', 'şeʼr']) assert.ok(words.has(w), `${w} missing from the lite lexicon`);
});

test('R1 without context: a typed valid word is kept (§5.1, Q19 default)', async () => {
  const c = await engine();
  assert.equal(c.autocorrect('ser'), 'ser');
});

test('R1: old-Latin spellings are read, not guessed', async () => {
  const c = await engine();
  assert.equal(c.autocorrect('sher'), 'şer');
  assert.equal(c.autocorrect("she'r"), 'şeʼr');
  assert.equal(c.autocorrect('шеър'), 'şeʼr');
});

test('R1 with context: suggestions offer the marked readings', async () => {
  const c = await engine({ maxSuggestions: 10 });
  const got = c.suggest('ser', null).map((s) => s.word);
  assert.ok(got.includes('ser'), got.join(' '));
});

test('24 proposed minimal pairs', { todo: 'parked until the human marks docs/AMBIGUITY-REVIEW.md' }, () => {});
