// CLAUDE.md §7.5: suggest() p95 under 5 ms on cold V8; load() under 400 ms for lite;
// §6 heap budget 25 MB for lite.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Chertma } from '../engine/index.js';
import { read, json } from './helpers.js';

const prefixes = json('tests/fixtures/perf-prefixes.json');

test('load() of the lite lexicon under 400 ms', async (t) => {
  const bytes = read('data/lexicon-lite.bin');
  const c = new Chertma();
  await c.load(bytes);
  t.diagnostic(`load ${c.stats().loadMs.toFixed(1)} ms`);
  assert.ok(c.stats().loadMs < 400);
});

test('suggest() p95 under 5 ms, cold', async (t) => {
  const c = new Chertma();
  await c.load(read('data/lexicon-lite.bin'));
  const times = [];
  for (const [buf, prev] of prefixes) {
    const t0 = performance.now();
    c.suggest(buf, prev);
    times.push(performance.now() - t0);
  }
  times.sort((a, b) => a - b);
  const p = (q) => times[Math.min(times.length - 1, Math.floor(q * times.length))];
  t.diagnostic(`${times.length} calls: p50 ${p(0.5).toFixed(3)} ms, p95 ${p(0.95).toFixed(3)} ms, p99 ${p(0.99).toFixed(3)} ms, max ${times[times.length - 1].toFixed(1)} ms`);
  assert.ok(p(0.95) < 5);
});

test('heap with lite loaded stays under 25 MB', async (t) => {
  globalThis.gc?.();
  const before = process.memoryUsage();
  const c = new Chertma();
  await c.load(read('data/lexicon-lite.bin'));
  for (const [buf, prev] of prefixes.slice(0, 1000)) c.suggest(buf, prev);
  c.autocorrect(prefixes.slice(0, 2000).map((p) => p[0]).join(' '));
  globalThis.gc?.();
  const after = process.memoryUsage();
  const delta = (after.heapUsed - before.heapUsed) + (after.arrayBuffers - before.arrayBuffers);
  t.diagnostic(`heap + array buffers grew by ${(delta / 1e6).toFixed(2)} MB (gc ${globalThis.gc ? 'forced' : 'not exposed'}); engine estimate ${(c.stats().memoryBytes / 1e6).toFixed(2)} MB`);
  assert.ok(delta < 25e6);
});
