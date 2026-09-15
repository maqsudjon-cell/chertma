// Every tunable number that affects ranking or behaviour lives here and
// nowhere else in engine/. Semantics: docs/SPEC.md §8.1 and §8.2.

// score = ln(unigram) + λ·ln(bigram + 1) + μ·user_bonus + ν·evidence
export const LAMBDA_BIGRAM = 2.0;
export const MU_USER = 3.0;
export const NU_EVIDENCE = 0.5;

// Share of the informal (telegram_blogs) table in unigram().
export const REGISTER_MIX = 0.5;

// ln(unigram) of a word known only from learn().
export const USER_ONLY_LN_UNIGRAM = 0;

// On-device user model (§7.5).
export const USER_HALF_LIFE_MS = 30 * 24 * 60 * 60 * 1000;
export const USER_MAX_WORDS = 5000;

// Evidence per aligned position (§8.2).
export const EVIDENCE_MATCH = 1;
export const EVIDENCE_AMBIGUOUS = 0;
export const EVIDENCE_CONTRADICT = -1;

export const DEFAULT_OPTIONS = Object.freeze({
  script: 'new',
  fuzzyQK: false,
  fuzzyXH: false,
  cyrillicKeyboardRecovery: true,
  morphology: 'read',      // §5.2 stem + suffix fallback: false | 'read' (stage 1) | true (stages 1+2).
                           // 'read' is the shipped setting (M1, ruled 2026-09-16): a known stem plus a
                           // suffix chain is read as old Latin and converted, no letter is ever corrected.
                           // true (stage 2, stem correction) is rejected — it got 12 of 13 wrong and
                           // touched qoyvor; do not turn it on without much stronger evidence.
  maxSuggestions: 3,
});

// Conservative defaults taken unattended (docs/OPEN-QUESTIONS.md, D3).
export const ACRONYM_MAX_LETTERS = 4;   // an isolated all-caps token this short is never corrected

// suggest() candidate pools — speed, not ranking.
export const SUGGEST_SCAN_ALL = 256;     // prefix ranges up to this size are scored in full
export const SUGGEST_UNIGRAM_POOL = 64;  // otherwise: the most frequent words in the range…
export const SUGGEST_BIGRAM_POOL = 128;  // …plus the strongest bigram successors of prevWord

// Morphological fallback (§5.2). Conservative defaults, docs/OPEN-QUESTIONS.md M2–M4.
export const MORPH_MIN_STEM_LETTERS = 3;    // a stem shorter than this is never corrected
export const MORPH_MIN_SUFFIX_LETTERS = 2;  // one-letter suffixes are not split off
