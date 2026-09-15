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

// Cyrillic letters outside the Uzbek alphabet (Russian, Kazakh, Tajik, …).
// Words containing them are never corrected, only transliterated (default M9).
const CYR_FOREIGN = {
  'щ': 'ş', 'ы': 'i', 'ә': 'a', 'ө': 'ö', 'ү': 'u', 'ұ': 'u', 'ң': 'ng', 'і': 'i', 'ї': 'yi',
  'є': 'ye', 'ґ': 'g', 'җ': 'j', 'ҷ': 'j', 'ӣ': 'i', 'ѓ': 'g', 'ќ': 'k', 'ђ': 'd', 'ћ': 'ç',
  'љ': 'l', 'њ': 'n', 'џ': 'j', 'ј': 'y', 'ѕ': 'z', 'ӂ': 'j', 'ӑ': 'a', 'ӗ': 'e', 'ҫ': 's',
};
export const hasForeignCyrillic = (low) => /[щыәөүұңіїєґҗҷӣѓќђћљњџјѕӂӑӗҫ]/.test(low);

/** Rule transliteration of any Cyrillic in a lowercase token; Latin letters pass through. */
export function cyrRuleLower(low) {
  let out = '';
  for (const o of cyrOptions(low, false)) out += o[0];
  return out.replace(/[щыәөүұңіїєґҗҷӣѓќђћљњџјѕӂӑӗҫ]/g, (c) => CYR_FOREIGN[c]);
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

/** A Latin letter outside the Uzbek alphabet → Cyrillic (default M8); Cyrillic passes through. */
function foreignLatinToCyr(c, next) {
  if (c === 'c') return next === 'e' || next === 'i' || next === 'y' ? 'ц' : 'к';
  if (c === 'w') return 'в';
  const base = c.normalize('NFD').replace(/\p{M}/gu, '');
  if (base !== c && base.length === 1) return base === 'c' ? 'к' : base === 'w' ? 'в' : (NEW_TO_CYR[base] ?? c);
  return c;
}

/** §6.4 rule fallback. Every Latin letter gets a Cyrillic letter: output is never mixed-script. */
export function newToCyrLower(w, exceptions) {
  const exc = exceptions && exceptions.get(w);
  if (exc) return exc;
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
    else out += NEW_TO_CYR[c] ?? foreignLatinToCyr(c, w[i + 1]);
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
  if (from === 'cyrillic') return cyrRuleLower(low);
  if (from === 'old') return oldToNewLower(low);
  return literalLower(low);
}

/** Render a canonical word in `script` with a case pattern. */
export function render(word, script, pattern, exceptions) {
  let s = word;
  if (script === 'old') s = newToOldLower(word);
  else if (script === 'cyrillic') s = newToCyrLower(word, exceptions);
  return applyCase(s, pattern);
}

const CYR_LETTER = /[Ѐ-ԯ]/;
const LAT_LETTER = /[A-Za-zÀ-ɏḀ-ỿ]/;
const OTHER_LETTER = /(?![Ѐ-ԯA-Za-zÀ-ɏḀ-ỿʻʼʽʿ])\p{L}/u;
const foldApos = (s) => Array.from(normalize(s).toLowerCase(), (c) => (isApos(c) ? "'" : c)).join('');

/**
 * §6.5 rule transliteration of one token into `to`, with no correction. A token
 * already written in the target script family comes back as typed; a token with
 * letters of any third script comes back as typed. `from` says how Latin is read
 * ('new' literally, 'old' with sh ch oʻ gʻ); Cyrillic is always read as Cyrillic.
 */
export function ruleToken(raw, to, from = 'old', exceptions) {
  const low = normalize(raw).toLowerCase();
  if (OTHER_LETTER.test(low)) return raw;
  const cyr = CYR_LETTER.test(low);
  const lat = LAT_LETTER.test(low);
  if (!cyr && !lat) return raw;
  if (to === 'cyrillic' ? !lat : (!cyr && to === 'new')) return raw;
  const pattern = casePattern(raw);
  if (pattern === 'mixed' || (cyr && lat)) {
    // Mixed case or mixed script (TOGGнинг, iPhone): convert each run of one script
    // and one case on its own, so the capitals stay where they were (default M10).
    const runs = [];
    for (const ch of normalize(raw)) {
      const kind = isApos(ch) || !/\p{L}/u.test(ch) ? null
        : `${CYR_LETTER.test(ch) ? 'c' : 'l'}${ch === ch.toLowerCase() ? 'l' : 'u'}`;
      const last = runs[runs.length - 1];
      if (last && (kind === null || kind === last.kind)) last.text += ch;
      else runs.push({ kind, text: ch });
    }
    if (runs.length > 1) return runs.map((r) => ruleToken(r.text, to, from, exceptions)).join('');
  }
  const canon = cyr ? cyrRuleLower(low) : from === 'new' ? literalLower(low) : oldToNewLower(low);
  const out = render(canon, to, pattern === 'mixed' ? 'lower' : pattern, exceptions);
  return foldApos(out) === foldApos(raw) ? raw : out;
}

/** §6 / §7.4: pure conversion, no correction. Output is never mixed-script (§6.5). */
export function convert(text, from, to, exceptions) {
  if (from === to) return text;
  let out = '';
  for (const seg of tokenize(text)) {
    const raw = text.slice(seg.start, seg.end);
    if (seg.kind === 'gap' || (seg.kind === 'protected' && !seg.glued)) { out += raw; continue; }
    const low = normalize(raw).toLowerCase();
    const pattern = casePattern(raw);
    const script = detectScript(low);
    if (seg.kind === 'token' && pattern !== 'mixed' && script !== 'mixed' && (from === 'cyrillic') === (script === 'cyrillic')) {
      out += render(canonical(low, from), to, pattern, exceptions);
    } else {
      out += ruleToken(raw, to, from === 'cyrillic' ? 'old' : from, exceptions);
    }
  }
  return out;
}
