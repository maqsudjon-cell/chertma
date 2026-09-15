// Scoring — docs/SPEC.md §8. Evidence (§8.2) aligns input and candidate unit by
// unit over their shared skeleton.

import { TUTUQ, isApos } from './normalize.js';
import {
  LAMBDA_BIGRAM, MU_USER, NU_EVIDENCE, REGISTER_MIX,
  EVIDENCE_MATCH as MATCH, EVIDENCE_AMBIGUOUS as AMBIG, EVIDENCE_CONTRADICT as CONTRA,
} from './constants.js';

const CLASS = {
  's': 'S', 'ş': 'S', 'w': 'S', 'c': 'C', 'ç': 'C',
  'o': 'O', 'ö': 'O', 'ó': 'O', 'ő': 'O', 'g': 'G', 'ğ': 'G', 'ǵ': 'G',
};

function letters(chars) {
  const out = [];
  for (const [ch, origin] of chars) {
    if (isApos(ch) || ch === TUTUQ) {
      if (out.length) out[out.length - 1].apos++;
      continue;
    }
    out.push({ ch, origin, apos: 0 });
  }
  return out;
}

function units(ls) {
  const out = [];
  for (let i = 0; i < ls.length; i++) {
    const { ch, origin, apos } = ls[i];
    if ((ch === 's' || ch === 'c' || ch === 'g') && ls[i + 1] && ls[i + 1].ch === 'h') {
      const h = ls[i + 1];
      out.push({ sym: ch.toUpperCase(), spell: ch + (apos ? "'h" : 'h'), origin: [origin, h.origin], apos: h.apos });
      i++;
    } else {
      out.push({ sym: CLASS[ch] ?? ch, spell: ch, origin, apos });
    }
  }
  return out;
}

export function latinUnits(low) {
  return units(letters(Array.from(low, (c) => [c, null])));
}

/** choice: the chosen output string for each Cyrillic position. */
export function cyrillicUnits(low, choice) {
  const chars = [];
  for (let i = 0; i < choice.length; i++) {
    const o = choice[i];
    if (o === TUTUQ) chars.push([TUTUQ, low[i]]);
    else for (const c of o) chars.push([c, low[i]]);
  }
  return units(letters(chars));
}

const unitCache = new Map();
function candidateUnits(word) {
  let u = unitCache.get(word);
  if (!u) {
    u = units(letters(Array.from(word, (c) => [c, null])));
    if (unitCache.size > 20000) unitCache.clear();
    unitCache.set(word, u);
  }
  return u;
}

const MARKED_SPELL = {
  'ş': ['ş', 'sh', 'w'], 'ç': ['ç', 'ch'],
  'ö': ['ö', 'ó', 'ő'], 'ğ': ['ğ', 'gh', 'ǵ'],
};
const BARE = { 'ş': 's', 'ç': 'c', 'ö': 'o', 'ğ': 'g' };

function latinLetter(inp, cand) {
  const sp = inp.spell;
  const cs = cand.spell;
  if (MARKED_SPELL[cs]) {
    if (MARKED_SPELL[cs].includes(sp)) return [MATCH, 0];
    if (sp === BARE[cs]) return (cs === 'ö' || cs === 'ğ') && inp.apos > 0 ? [MATCH, 1] : [AMBIG, 0];
    return [CONTRA, 0];
  }
  if (cs === 'sh' || cs === 'ch' || cs === 'gh') {
    if (sp === cs[0] + "'h") return [MATCH, 0];
    return sp === cs ? [AMBIG, 0] : [CONTRA, 0];
  }
  if (cs === 's' || cs === 'c' || cs === 'o' || cs === 'g') {
    if (sp !== cs) return [CONTRA, 0];
    if ((cs === 'o' || cs === 'g') && inp.apos > 0 && cand.apos === 0) return [CONTRA, 1];
    return [AMBIG, 0];
  }
  return [AMBIG, 0];
}

const CYR_TABLE = {
  'ş': { 'ш': MATCH, 'с': CONTRA, 'ц': CONTRA },
  's': { 'с': MATCH, 'ш': CONTRA },
  'ç': { 'ч': MATCH },
  'ö': { 'ў': MATCH },
  'o': { 'ў': CONTRA },
  'ğ': { 'ғ': MATCH },
  'g': { 'ғ': CONTRA },
  'q': { 'қ': MATCH },
  'h': { 'ҳ': MATCH },
};

function cyrillicLetter(inp, cand) {
  const o = inp.origin;
  const cs = cand.spell;
  if (cs === 'sh' || cs === 'gh') {
    const head = cs === 'sh' ? 'с' : 'г';
    if (Array.isArray(o) && o[0] === head) return o[1] === 'ҳ' ? MATCH : AMBIG;
    return CONTRA;
  }
  const first = Array.isArray(o) ? o[0] : o;
  return CYR_TABLE[cs]?.[first] ?? AMBIG;
}

/**
 * Evidence of input units for a candidate: { sum, min } or null when the
 * units do not align. `prefix` compares only the typed positions.
 */
export function evidence(inputUnits, word, cyrillic, prefix = false) {
  const cu = candidateUnits(word);
  if (prefix ? inputUnits.length > cu.length : inputUnits.length !== cu.length) return null;
  let sum = 0;
  let min = 0;
  for (let i = 0; i < inputUnits.length; i++) {
    const iu = inputUnits[i];
    const c = cu[i];
    if (iu.sym !== c.sym) return null;
    let e;
    let used = 0;
    if (cyrillic) e = cyrillicLetter(iu, c);
    else [e, used] = latinLetter(iu, c);
    const rest = iu.apos - used;
    let t = 0;
    if (rest > 0) t = c.apos > 0 ? MATCH : CONTRA;
    sum += e + t;
    min = Math.min(min, e, t);
  }
  return { sum, min };
}

/** ln unigram with the informal register mixed in (§8.1). */
export function lnUnigram(lex, id) {
  const all = lex.lnUnigram(id);
  const inf = lex.lnInformal(id);
  return inf === null ? all : (1 - REGISTER_MIX) * all + REGISTER_MIX * inf;
}

export function score(lnUni, lnBi, userBonus, ev) {
  return lnUni + LAMBDA_BIGRAM * lnBi + MU_USER * userBonus + NU_EVIDENCE * ev;
}
