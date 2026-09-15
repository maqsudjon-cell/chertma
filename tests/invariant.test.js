// SPEC §5: a token no lexicon word shares a skeleton with comes back byte-identical.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { engine, json, root } from './helpers.js';

const generated = readFileSync(root + 'tests/fixtures/invariant-generated.txt', 'utf8').split('\n').filter(Boolean);
const handwritten = json('tests/fixtures/dialect-handwritten.json').forms;
const HANDWRITTEN_TARGET = 200;

test(`invariant: ${generated.length} generated forms (Q23b) come back byte-identical`, async () => {
  const c = await engine();
  const changed = generated.filter((s) => c.autocorrect(s) !== s);
  assert.equal(changed.length, 0, `changed: ${changed.slice(0, 20).map((s) => `${s} → ${c.autocorrect(s)}`).join(', ')}`);
});

test('invariant: the same forms in running text', async () => {
  const c = await engine();
  const text = generated.slice(0, 2000).join(' ');
  assert.equal(c.autocorrect(text), text);
});

const incomplete = handwritten.length < HANDWRITTEN_TARGET;
test(`invariant: hand-written dialect forms (Q23a) — ${handwritten.length}/${HANDWRITTEN_TARGET}`,
  { todo: incomplete ? `INCOMPLETE: ${handwritten.length} of ${HANDWRITTEN_TARGET} hand-written forms have landed (Q23a)` : false },
  async (t) => {
    if (incomplete) t.diagnostic('INVARIANT SUITE INCOMPLETE until tests/fixtures/dialect-handwritten.json has the human-written forms');
    const c = await engine();
    const changed = handwritten.filter((s) => c.autocorrect(s) !== s);
    assert.equal(changed.length, 0, `changed: ${changed.join(', ')}`);
  });
