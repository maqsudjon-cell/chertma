// SPEC §5: a token no lexicon word shares a skeleton with is never corrected.
// In its own script it comes back byte-identical; in another script it comes back
// transliterated by rule and nothing else (§6.5) — output is never mixed-script.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { engine, json, root } from './helpers.js';
import { ruleToken } from '../engine/index.js';

const generated = readFileSync(root + 'tests/fixtures/invariant-generated.txt', 'utf8').split('\n').filter(Boolean);
const handwritten = json('tests/fixtures/dialect-handwritten.json').forms;
const HANDWRITTEN_TARGET = 200;
const isCyr = (s) => /[\u0400-\u052f]/.test(s);

function check(c, forms, label) {
  const changed = [];
  for (const script of ['new', 'old', 'cyrillic']) {
    c.options.script = script;
    for (const s of forms) {
      const got = c.autocorrect(s);
      const own = (script === 'cyrillic') === isCyr(s) && script !== 'old';
      const want = own ? s : ruleToken(s, script, 'old');
      if (got !== want) changed.push(`${script}: ${s} → ${got} (want ${want})`);
    }
  }
  c.options.script = 'new';
  assert.equal(changed.length, 0, `${label}: ${changed.length} changed: ${changed.slice(0, 20).join(', ')}`);
}

test(`invariant: ${generated.length} generated forms (Q23b), all three output scripts`, async () => {
  check(await engine(), generated, 'generated');
});

test('invariant: the same forms in running text', async () => {
  const c = await engine();
  const lat = generated.filter((s) => !isCyr(s)).slice(0, 1500).join(' ');
  const cyr = generated.filter(isCyr).slice(0, 1500).join(' ');
  assert.equal(c.autocorrect(lat), lat);
  c.options.script = 'cyrillic';
  assert.equal(c.autocorrect(cyr), cyr);
});

const incomplete = handwritten.length < HANDWRITTEN_TARGET;
test(`invariant: hand-written dialect forms (Q23a) — ${handwritten.length}/${HANDWRITTEN_TARGET}`,
  { todo: incomplete ? `INCOMPLETE: ${handwritten.length} of ${HANDWRITTEN_TARGET} hand-written forms have landed (Q23a)` : false },
  async (t) => {
    if (incomplete) t.diagnostic('INVARIANT SUITE INCOMPLETE until tests/fixtures/dialect-handwritten.json has the human-written forms');
    check(await engine(), handwritten, 'handwritten');
  });
