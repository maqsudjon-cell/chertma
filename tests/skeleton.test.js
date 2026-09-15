// SPEC §2–§6 rules against the fixture file shared with tools/uzscript.py.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { json } from './helpers.js';
import { skeleton, key, normalize, cyrToNewLower, oldToNewLower, tokenize } from '../engine/index.js';

const FIX = json('tests/fixtures/skeleton.json');

test('skeleton keys', () => {
  for (const e of FIX.skeleton) {
    assert.deepEqual(skeleton(e.in, undefined, e.opts ?? {}), e.keys, `${e.in} ${JSON.stringify(e.opts ?? {})}`);
  }
});

test('Cyrillic → new Latin', () => {
  for (const [src, want] of FIX.cyr_to_new) assert.equal(cyrToNewLower(normalize(src).toLowerCase()), want, src);
});

test('old Latin → new Latin', () => {
  for (const [src, want] of FIX.old_to_new) assert.equal(oldToNewLower(normalize(src).toLowerCase()), want, src);
});

test('tokenization', () => {
  // tools/uzscript.py yields null for a token glued to a digit or underscore and
  // leaves out tokens inside URLs, mentions and hashtags. Same view here.
  const glued = (t, s) => /[\p{Nd}\p{No}_]/u.test(t[s.start - 1] ?? '') || /[\p{Nd}\p{No}_]/u.test(t[s.end] ?? '');
  for (const e of FIX.tokens) {
    const got = tokenize(e.in)
      .filter((s) => s.kind === 'token' || (s.kind === 'protected' && glued(e.in, s)))
      .map((s) => (s.kind === 'token' ? e.in.slice(s.start, s.end) : null));
    assert.deepEqual(got, e.tokens, e.in);
  }
});

test('script-blind: key(w) is in the skeleton of its Cyrillic form', () => {
  for (const [src, want] of FIX.cyr_to_new) assert.ok(skeleton(src).includes(key(want)), src);
});
