// engine/ is frozen: the bot runs a byte-identical copy and never changes the original.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const bot = fileURLToPath(new URL('..', import.meta.url));
const repo = fileURLToPath(new URL('../..', import.meta.url));

test('bot/_vendor holds a byte-identical engine/ and lexicon build', () => {
  const files = readdirSync(repo + 'engine').filter((f) => f.endsWith('.js')).sort();
  assert.deepEqual(readdirSync(bot + '_vendor/engine').sort(), files);
  for (const f of files) assert.ok(readFileSync(repo + 'engine/' + f).equals(readFileSync(bot + '_vendor/engine/' + f)), f);
  const { lexicon } = JSON.parse(readFileSync(bot + '_vendor/MANIFEST.json', 'utf8'));
  assert.ok(['full', 'mid', 'lite'].includes(lexicon));
  assert.ok(readFileSync(repo + `data/lexicon-${lexicon}.bin`).equals(readFileSync(bot + '_vendor/lexicon.bin')));
});

test('engine/ has no uncommitted changes', () => {
  const out = execFileSync('git', ['status', '--porcelain', '--', 'engine'], { cwd: repo, encoding: 'utf8' });
  assert.equal(out, '');
});
