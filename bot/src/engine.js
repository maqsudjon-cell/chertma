// The engine, loaded once per function instance at module scope, so warm
// invocations reuse the parsed lexicon. initMs is reported by the health endpoint.
import { readFileSync } from 'node:fs';

const t0 = performance.now();
const { Chertma } = await import('../_vendor/engine/index.js');
const bytes = readFileSync(new URL('../_vendor/lexicon.bin', import.meta.url));

/** Which build is bundled: full, mid or lite (scripts/vendor.mjs). */
export const lexiconBuild = JSON.parse(readFileSync(new URL('../_vendor/MANIFEST.json', import.meta.url), 'utf8')).lexicon;

export const engine = new Chertma({ script: 'new' });
await engine.load(bytes);

/** Engine import + lexicon read + parse, in ms. */
export const initMs = performance.now() - t0;
