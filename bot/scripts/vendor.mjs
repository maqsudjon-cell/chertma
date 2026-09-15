// Copy the engine and one lexicon build into bot/_vendor/ (gitignored) so the Vercel
// project rooted at bot/ can bundle them. Files are copied byte for byte; engine/ and
// data/ are never touched. BOT_LEXICON picks the build: full (default), mid, lite.
// Writes _vendor/MANIFEST.json with the build name and sha256 sums.
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
const lexicon = process.env.BOT_LEXICON ?? 'full';
if (!['full', 'mid', 'lite'].includes(lexicon)) throw new Error(`BOT_LEXICON must be full, mid or lite, not ${lexicon}`);
copyFileSync(repo + `data/lexicon-${lexicon}.bin`, out + 'lexicon.bin');
manifest['lexicon.bin'] = sha(out + 'lexicon.bin');
writeFileSync(out + 'MANIFEST.json', JSON.stringify({ lexicon, files: manifest }, null, 2) + '\n');
console.log(`vendored engine + lexicon-${lexicon}.bin (${Object.keys(manifest).length} files) into bot/_vendor/`);
