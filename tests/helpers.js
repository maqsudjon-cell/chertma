// Shared test setup. Tests load lexicon bytes from disk and hand them to the
// engine; the engine itself never reads files or touches the network.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Chertma } from '../engine/index.js';

export const root = fileURLToPath(new URL('..', import.meta.url));
export const read = (p) => readFileSync(root + p);
export const json = (p) => JSON.parse(readFileSync(root + p, 'utf8'));

export async function engine(options = {}, lexicon = 'data/lexicon-lite.bin') {
  const c = new Chertma(options);
  await c.load(read(lexicon));
  return c;
}
