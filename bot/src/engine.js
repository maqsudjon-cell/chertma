// The engine, loaded once per function instance at module scope, so warm
// invocations reuse the parsed lexicon. initMs is reported by the health endpoint.
import { readFileSync } from 'node:fs';

const t0 = performance.now();
const { Chertma } = await import('../_vendor/engine/index.js');
const bytes = readFileSync(new URL('../_vendor/lexicon-lite.bin', import.meta.url));

export const engine = new Chertma({ script: 'new' });
await engine.load(bytes);

/** Engine import + lexicon read + parse, in ms. */
export const initMs = performance.now() - t0;
