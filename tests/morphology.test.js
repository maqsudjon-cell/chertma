// SPEC §5.2: stem + suffix fallback. Off by default (docs/OPEN-QUESTIONS.md M1);
// these tests pin what each mode does so it can be reviewed before it is switched on.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { engine, json, root } from './helpers.js';
import { normalize, detectScript, skeleton, key, tokenize } from '../engine/index.js';

const PRESERVE = ['kelaslar', 'qisela', 'balu', 'kettik', 'bormimiz'];

test('morphology is off by default', async () => {
  const c = await engine();
  assert.equal(c.options.morphology, false);
  assert.equal(c.autocorrect('ishlating'), 'ishlating');
  assert.ok(c.lex.suffixes && c.lex.suffixes.size > 1000, 'lite carries the suffix section');
});

test("'read': a real stem + suffix read as old Latin is converted, nothing corrected", async () => {
  const c = await engine({ morphology: 'read' });
  assert.equal(c.autocorrect('ishlating'), 'işlating');
  assert.equal(c.autocorrect('islating'), 'islating');           // bare: would need a correction
  c.options.script = 'cyrillic';
  assert.equal(c.autocorrect('ishlating'), 'ишлатинг');
  c.options.script = 'new';
  assert.equal(c.autocorrect('ишлатинг'), 'işlating');
});

test('true: the stem is corrected and the suffix kept (lowercase Latin only)', async () => {
  const c = await engine({ morphology: true });
  assert.equal(c.autocorrect('islating'), 'işlating');
  assert.equal(c.autocorrect('Islating'), 'Islating');           // M6: capitalised tokens are never stem-corrected
});

for (const mode of [false, 'read', true]) {
  test(`preserve forms stay byte-identical (morphology: ${mode})`, async () => {
    const c = await engine({ morphology: mode });
    for (const w of PRESERVE) assert.equal(c.autocorrect(w), w, w);
  });
}

test('qoyvor stays as typed', { todo: 'fails with morphology: true — qoyvor → qöyvor (stage 2), see docs/FOR-MAQSUDJON.md' }, async () => {
  for (const mode of [false, 'read', true]) {
    const c = await engine({ morphology: mode });
    assert.equal(c.autocorrect('qoyvor'), 'qoyvor', `morphology: ${mode}`);
  }
});

test('segmentation never touches a token that has a whole-word skeleton match, and passes the §5 guard', async () => {
  const off = await engine();
  const on = await engine({ morphology: true });
  const G = json('tests/golden.json');
  const forms = readFileSync(root + 'tests/fixtures/invariant-generated.txt', 'utf8').split('\n').filter(Boolean);
  const texts = G.strict.map((g) => g.input).concat(G.ranked.map((g) => g.input), forms.slice(0, 3000));
  let changed = 0;
  for (const text of texts) {
    const a = off.autocorrect(text);
    const b = on.autocorrect(text);
    if (a === b) continue;
    const ta = tokenize(a).filter((x) => x.kind !== 'gap');
    const tb = tokenize(b).filter((x) => x.kind !== 'gap');
    const ti = tokenize(text).filter((x) => x.kind !== 'gap');
    assert.equal(ta.length, tb.length);
    for (let i = 0; i < ta.length; i++) {
      const wa = a.slice(ta[i].start, ta[i].end);
      const wb = b.slice(tb[i].start, tb[i].end);
      if (wa === wb) continue;
      changed++;
      const raw = text.slice(ti[i].start, ti[i].end);
      const low = normalize(raw).toLowerCase();
      const script = detectScript(low);
      for (const k of skeleton(low, script, on.options)) {
        const [lo, hi] = on.lex.range(k);
        assert.equal(lo, hi, `${raw}: has whole-word matches but was segmented (${wa} → ${wb})`);
      }
      assert.ok(skeleton(low, script, on.options).includes(key(normalize(wb).toLowerCase())), `${raw} → ${wb} breaks the invariant`);
    }
  }
  assert.ok(changed > 0, 'the property was exercised');
});
