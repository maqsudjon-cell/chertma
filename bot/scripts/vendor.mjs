// Copy the frozen engine and the lite lexicon into bot/_vendor/ (gitignored) so the
// Vercel project rooted at bot/ can bundle them. Files are copied byte for byte;
// engine/ itself is never touched. Writes _vendor/MANIFEST.json with sha256 sums.
import { createHash } from 'node:crypto';
import { copyFileSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const bot = fileURLToPath(new URL('..', import.meta.url));
const repo = fileURLToPath(new URL('../..', import.meta.url));
const out = bot + '_vendor/';
rmSync(out, { recursive: true, force: true });
mkdirSync(out + 'engine', { recursive: true });

const manifest = {};
const sha = (p) => createHash('sha256').update(readFileSync(p)).digest('hex');
for (const f of readdirSync(repo + 'engine').filter((n) => n.endsWith('.js')).sort()) {
  copyFileSync(repo + 'engine/' + f, out + 'engine/' + f);
  manifest['engine/' + f] = sha(out + 'engine/' + f);
}
copyFileSync(repo + 'data/lexicon-lite.bin', out + 'lexicon-lite.bin');
manifest['lexicon-lite.bin'] = sha(out + 'lexicon-lite.bin');
writeFileSync(out + 'MANIFEST.json', JSON.stringify(manifest, null, 2) + '\n');
console.log(`vendored ${Object.keys(manifest).length} files into bot/_vendor/`);
