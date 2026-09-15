// The equivalence function — docs/SPEC.md §4.

import { isApos, normalize, detectScript } from './normalize.js';
import { cyrOptions } from './translit.js';

const CLASS = {
  's': 'S', 'ş': 'S', 'w': 'S',
  'c': 'C', 'ç': 'C',
  'o': 'O', 'ö': 'O', 'ó': 'O', 'ő': 'O',
  'g': 'G', 'ğ': 'G', 'ǵ': 'G',
};

/** Steps 4–5 on one lowercase Latin string. */
export function fold(s) {
  let t = '';
  for (const c of s) if (!isApos(c)) t += c;
  let out = '';
  for (let i = 0; i < t.length; i++) {
    const c = t[i];
    if ((c === 's' || c === 'c' || c === 'g') && t[i + 1] === 'h') { out += c.toUpperCase(); i++; }
    else out += CLASS[c] ?? c;
  }
  return out;
}

/** key(w) of a canonical lowercase word. */
export const key = fold;

function fuzzy(k, qk, xh) {
  if (!qk && !xh) return [k];
  let acc = [''];
  for (const c of k) {
    const alts = qk && (c === 'q' || c === 'k') ? ['q', 'k'] : xh && (c === 'x' || c === 'h') ? ['x', 'h'] : [c];
    const next = [];
    for (const p of acc) for (const a of alts) next.push(p + a);
    acc = next;
    if (acc.length > 4096) return [k];
  }
  return acc;
}

const LIMIT = 4096;

/** Every Latin reading of a token (one for Latin input, several with recovery). */
export function readings(low, script, recovery) {
  if (script !== 'cyrillic') return [low];
  const opts = cyrOptions(low, recovery);
  let count = 1;
  for (const o of opts) count *= o.length;
  const use = count > LIMIT ? opts.map((o) => [o[0]]) : opts;
  let acc = [''];
  for (const o of use) {
    const next = [];
    for (const p of acc) for (const a of o) next.push(p + a);
    acc = next;
  }
  return acc;
}

/** §4.1: the set of keys of a surface token, sorted. */
export function skeleton(token, script, opts = {}) {
  const low = normalize(token).toLowerCase();
  const sc = script ?? detectScript(low);
  const recovery = opts.cyrillicKeyboardRecovery ?? true;
  const keys = new Set();
  for (const r of readings(low, sc, recovery)) {
    for (const k of fuzzy(fold(r), opts.fuzzyQK, opts.fuzzyXH)) keys.add(k);
  }
  return [...keys].sort();
}
