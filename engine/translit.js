// Script conversion — docs/SPEC.md §6. Canonical form is lowercase new Latin.

import { TUTUQ, OKINA, isApos, normalize, tokenize, detectScript, casePattern } from './normalize.js';

const CYR = {
  'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y',
  'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
  'у': 'u', 'ф': 'f', 'х': 'x', 'ч': 'ç', 'ш': 'ş', 'ў': 'ö', 'қ': 'q',
  'ғ': 'ğ', 'ҳ': 'h', 'э': 'e', 'ё': 'yo', 'ю': 'yu', 'я': 'ya',
};
const CYR_VOWELS = new Set('аеёиоуэюяў');
const IOTATED = new Set('еёюя');
const RECOVERY = { 'у': ['u', 'ö'], 'к': ['k', 'q'], 'х': ['x', 'h'] };

/** Per-position output options of a lowercase Cyrillic token (§6.1, §4.8). */
export function cyrOptions(low, recovery) {
  const opts = [];
  for (let i = 0; i < low.length; i++) {
    const ch = low[i];
    const prev = i ? low[i - 1] : null;
    const next = i + 1 < low.length ? low[i + 1] : null;
    let o;
    if (ch === 'е') o = prev === null || CYR_VOWELS.has(prev) || prev === 'ъ' || prev === 'ь' || isApos(prev) ? 'ye' : 'e';
    else if (ch === 'ц') o = prev !== null && CYR_VOWELS.has(prev) ? 'ts' : 's';
    else if (ch === 'ъ' || isApos(ch)) o = next !== null && IOTATED.has(next) ? '' : TUTUQ;
    else if (ch === 'ь') o = next === 'о' ? 'y' : '';
    else if (recovery && RECOVERY[ch]) { opts.push(RECOVERY[ch]); continue; }
    else o = CYR[ch] ?? ch;
    opts.push([o]);
  }
  return opts;
}

export function cyrToNewLower(low) {
  return cyrOptions(low, false).map((o) => o[0]).join('');
}

/** §6.3 old Latin → new, on a lowercase token. */
export function oldToNewLower(low) {
  let out = '';
  for (let i = 0; i < low.length;) {
    const c = low[i];
    const next = low[i + 1] ?? '';
    if (c === 's' && isApos(next) && low[i + 2] === 'h') { out += 'sh'; i += 3; }
    else if (c === 's' && next === 'h') { out += 'ş'; i += 2; }
    else if (c === 'c' && next === 'h') { out += 'ç'; i += 2; }
    else if ((c === 'o' || c === 'g') && next && isApos(next)) { out += c === 'o' ? 'ö' : 'ğ'; i += 2; }
    else if (isApos(c)) { out += TUTUQ; i += 1; }
    else { out += c; i += 1; }
  }
  return out;
}

/** §5.1 literal reading of a Latin token: every apostrophe-like → ʼ. */
export function literalLower(low) {
  let out = '';
  for (const c of low) out += isApos(c) ? TUTUQ : c;
  return out;
}

const NEW_TO_OLD = { 'ş': 'sh', 'ç': 'ch', 'ö': 'o' + OKINA, 'ğ': 'g' + OKINA };

/** §6.2. A literal s+h gets the separator. */
export function newToOldLower(w) {
  let out = '';
  for (let i = 0; i < w.length; i++) {
    const c = w[i];
    out += c === 's' && w[i + 1] === 'h' ? 's' + TUTUQ : (NEW_TO_OLD[c] ?? c);
  }
  return out;
}

const NEW_TO_CYR = {
  'a': 'а', 'b': 'б', 'd': 'д', 'f': 'ф', 'g': 'г', 'i': 'и', 'j': 'ж', 'k': 'к', 'l': 'л',
  'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'v': 'в',
  'x': 'х', 'y': 'й', 'z': 'з', 'h': 'ҳ', 'q': 'қ', 'ş': 'ш', 'ç': 'ч',
  'ö': 'ў', 'ğ': 'ғ', [TUTUQ]: 'ъ',
};
const LAT_VOWELS = new Set('aeiouö');
const IOT = { 'e': 'е', 'o': 'ё', 'u': 'ю', 'a': 'я' };

/** §6.4 rule fallback. null for a token with c or w (foreign, stays Latin). */
export function newToCyrLower(w, exceptions) {
  const exc = exceptions && exceptions.get(w);
  if (exc) return exc;
  if (w.includes('c') || w.includes('w')) return null;
  let out = '';
  for (let i = 0; i < w.length;) {
    const c = w[i];
    const prev = i ? w[i - 1] : null;
    if (c === 'y' && IOT[w[i + 1]]) {
      const next = w[i + 1];
      out += next === 'e' && prev !== null && !LAT_VOWELS.has(prev) && prev !== TUTUQ ? 'ъе' : IOT[next];
      i += 2;
      continue;
    }
    if (c === 'e') out += prev === null || LAT_VOWELS.has(prev) ? 'э' : 'е';
    else out += NEW_TO_CYR[c] ?? c;
    i += 1;
  }
  return out;
}

export function applyCase(s, pattern) {
  if (pattern === 'upper') return s.toUpperCase();
  if (pattern === 'title') return s.charAt(0).toUpperCase() + s.slice(1);
  return s;
}

/** Canonical reading of a token written in `from` ('new' | 'old' | 'cyrillic'). */
export function canonical(low, from) {
  if (from === 'cyrillic') return cyrToNewLower(low);
  if (from === 'old') return oldToNewLower(low);
  return literalLower(low);
}

/** Render a canonical word in `script` with a case pattern. */
export function render(word, script, pattern, exceptions) {
  let s = word;
  if (script === 'old') s = newToOldLower(word);
  else if (script === 'cyrillic') s = newToCyrLower(word, exceptions) ?? word;
  return applyCase(s, pattern);
}

/** §6 / §7.4: pure conversion, no correction. */
export function convert(text, from, to, exceptions) {
  if (from === to) return text;
  let out = '';
  for (const seg of tokenize(text)) {
    const raw = text.slice(seg.start, seg.end);
    if (seg.kind !== 'token') { out += raw; continue; }
    const low = normalize(raw).toLowerCase();
    const pattern = casePattern(raw);
    const script = detectScript(low);
    if (pattern === 'mixed' || script === 'mixed' || (from === 'cyrillic') !== (script === 'cyrillic')) {
      out += raw;
      continue;
    }
    const canon = canonical(low, from);
    if (to === 'cyrillic' && newToCyrLower(canon, exceptions) === null) { out += raw; continue; }
    out += render(canon, to, pattern, exceptions);
  }
  return out;
}
