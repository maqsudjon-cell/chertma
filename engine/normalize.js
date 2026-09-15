// Inbound cleanup, character classes and tokenization — docs/SPEC.md §2, §3.

export const APOS = "'`´‘’ʻʼʽʿ′";
export const TUTUQ = 'ʼ';
export const OKINA = 'ʻ';

const APOS_SET = new Set(APOS);
export const isApos = (c) => APOS_SET.has(c);

const CONFUSABLE = {
  'ș': 'ş', 'Ș': 'Ş', // ș Ș → ş Ş
  'ǧ': 'ğ', 'Ǧ': 'Ğ', // ǧ Ǧ → ğ Ğ
  'ı': 'i', 'İ': 'I',           // ı İ → i I
  'һ': 'ҳ', 'Һ': 'Ҳ', // һ Һ → ҳ Ҳ
  'ӯ': 'ў', 'Ӯ': 'Ў', // ӯ Ӯ → ў Ў
};
const CONFUSABLE_RE = /[șȘǧǦıİһҺӯӮ]/g;

/** §2.4: NFC, then confusable fold. Apostrophes are left for later stages. */
export function normalize(text) {
  return text.normalize('NFC').replace(CONFUSABLE_RE, (c) => CONFUSABLE[c]);
}

const A = "['`\\u00b4\\u2018\\u2019\\u02bb\\u02bc\\u02bd\\u02bf\\u2032]";
const L = '(?:(?![\\u02bb\\u02bc\\u02bd\\u02bf])[\\p{L}\\p{M}])';

// §3.2: token := L+ (A+ L+)* tail?  — the second branch is a token opened by a
// quotation mark, which may not take an o/g tail ('kino' is not kinö).
const TOKEN_RE = new RegExp(
  `(?<!${A})${L}+(?:${A}+${L}+)*(?:(?<=[oOgG])${A}|\\u02bc)?` +
  `|(?<=${A})${L}+(?:${A}+${L}+)*(?:(?<![oOgG])\\u02bc)?`,
  'gu',
);

const TLD = 'uz|com|ru|org|net|io|me|info|tv|gov|edu|app|dev|ai|co|su|kz|tj|kg|tm|tr|de|uk|us|biz|pro|online|site|xyz';
const ANCHOR_RE = new RegExp(
  `:\\/\\/|(?<![\\p{L}\\p{N}_])www\\.|[@#][\\p{L}\\p{N}_]|\\.(?:${TLD})(?![\\p{L}\\p{N}_])`,
  'giu',
);
const GLUE_RE = /[\p{Nd}\p{No}_]/u;
const SPACE_RE = /\s/u;
export const BREAK_RE = /[.!?…\n]/;

/**
 * §3: split text into segments covering it exactly.
 * kind: 'token' | 'gap' | 'protected' (URL, domain, email, mention, hashtag,
 * letters glued to a digit or underscore).
 */
export function tokenize(text) {
  const prot = [];
  ANCHOR_RE.lastIndex = 0;
  for (let m; (m = ANCHOR_RE.exec(text));) {
    let s = m.index;
    let e = s + m[0].length;
    while (s > 0 && !SPACE_RE.test(text[s - 1])) s--;
    while (e < text.length && !SPACE_RE.test(text[e])) e++;
    const last = prot[prot.length - 1];
    if (last && s <= last[1]) last[1] = Math.max(last[1], e);
    else prot.push([s, e]);
    ANCHOR_RE.lastIndex = e;
  }
  const out = [];
  let pos = 0;
  let pi = 0;
  TOKEN_RE.lastIndex = 0;
  for (let m; (m = TOKEN_RE.exec(text));) {
    const s = m.index;
    const e = s + m[0].length;
    while (pi < prot.length && prot[pi][1] <= s) pi++;
    const inside = pi < prot.length && prot[pi][0] < e && s < prot[pi][1];
    const glued = (s > 0 && GLUE_RE.test(text[s - 1])) || (e < text.length && GLUE_RE.test(text[e]));
    if (s > pos) out.push({ start: pos, end: s, kind: 'gap' });
    out.push({ start: s, end: e, kind: inside || glued ? 'protected' : 'token' });
    pos = e;
  }
  if (pos < text.length) out.push({ start: pos, end: text.length, kind: 'gap' });
  return out;
}

const LETTER_RE = /\p{L}/u;
const MARK_RE = /\p{M}/u;

const isCyrillic = (c) => c >= 'Ѐ' && c <= 'ԯ';
const isLatin = (c) => c <= '' || (c >= 'À' && c <= 'ɏ') || (c >= 'Ḁ' && c <= 'ỿ');

/** §4.8: 'latin' | 'cyrillic' | 'mixed'. */
export function detectScript(token) {
  let lat = false;
  let cyr = false;
  for (const c of token) {
    if (APOS_SET.has(c) || MARK_RE.test(c) || !LETTER_RE.test(c)) continue;
    if (isCyrillic(c)) cyr = true;
    else if (isLatin(c)) lat = true;
    else return 'mixed';
  }
  if (lat && cyr) return 'mixed';
  return cyr ? 'cyrillic' : 'latin';
}

/** §3.4: 'lower' | 'title' | 'upper' | 'mixed'. */
export function casePattern(token) {
  let w = '';
  for (const c of token) if (!APOS_SET.has(c) && LETTER_RE.test(c)) w += c;
  if (!w) return 'lower';
  if (w === w.toLowerCase()) return 'lower';
  if (w === w.toUpperCase()) return w.length === 1 ? 'title' : 'upper';
  const first = w[0];
  const rest = w.slice(1);
  if (first === first.toUpperCase() && rest === rest.toLowerCase()) return 'title';
  return 'mixed';
}

/** Number of letters, apostrophes excluded. */
export function letterCount(token) {
  let n = 0;
  for (const c of token) if (!APOS_SET.has(c)) n++;
  return n;
}
