// Public API — docs/SPEC.md §7. Zero dependencies, no DOM, no network.

import {
  DEFAULT_OPTIONS, ACRONYM_MAX_LETTERS, SUGGEST_SCAN_ALL, SUGGEST_UNIGRAM_POOL, SUGGEST_BIGRAM_POOL,
} from './constants.js';
import { normalize, tokenize, detectScript, casePattern, letterCount, isApos, BREAK_RE } from './normalize.js';
import { cyrOptions, cyrToNewLower, oldToNewLower, literalLower, render, convert as convertText } from './translit.js';
import { fold, key as keyOf, skeleton } from './skeleton.js';
import { Lexicon } from './lexicon.js';
import { latinUnits, cyrillicUnits, evidence, lnUnigram, score } from './rank.js';
import { UserModel } from './learn.js';

export { normalize, tokenize, detectScript, casePattern } from './normalize.js';
export { skeleton, key, fold } from './skeleton.js';
export { convert, cyrToNewLower, oldToNewLower, newToOldLower, newToCyrLower } from './translit.js';

const now = () => (globalThis.performance ? globalThis.performance.now() : Date.now());

function sameLetters(a, b) {
  const f = (x) => Array.from(normalize(x), (c) => (isApos(c) ? "'" : c)).join('');
  return f(a) === f(b);
}

export class Chertma {
  constructor(options = {}) {
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.lex = null;
    this.loadMs = 0;
    this.user = new UserModel(this.options.userModel, this.options.clock ?? (() => Date.now()));
  }

  /** §7.1: bytes, or a URL resolved by the host-supplied `loader`. */
  async load(source) {
    let bytes = source;
    if (typeof source === 'string') {
      if (typeof this.options.loader !== 'function') {
        throw new Error('Chertma: load(url) needs a loader option, async (url) => ArrayBuffer');
      }
      bytes = await this.options.loader(source);
    }
    const t0 = now();
    this.lex = new Lexicon(bytes);
    this.loadMs = now() - t0;
  }

  _lexicon() {
    if (!this.lex) throw new Error('Chertma: call load() first');
    return this.lex;
  }

  _knownId(word) {
    const id = this.lex.indexOf(word);
    if (id >= 0) return id;
    return this.user.has(word) ? -1 : null;
  }

  /** §5.1: the first reading that is a word → { word, id } (id -1 for user-only words). */
  _valid(low, script) {
    const tries = script === 'cyrillic' ? [cyrToNewLower(low)] : [literalLower(low), oldToNewLower(low)];
    for (const w of tries) {
      const id = this._knownId(w);
      if (id !== null) return { word: w, id };
    }
    return null;
  }

  _exists(k, prefix) {
    if (prefix) { if (this.lex.hasPrefix(k)) return true; } else { const [lo, hi] = this.lex.range(k); if (lo < hi) return true; }
    return prefix ? this.user.withKeyPrefix(k).length > 0 : [...this.user.withKey(k)].length > 0;
  }

  /** Latin readings of a token as [choice | null, key] leaves, pruned by the index. */
  _leaves(low, script, prefix) {
    const { fuzzyQK, fuzzyXH, cyrillicKeyboardRecovery } = this.options;
    if (fuzzyQK || fuzzyXH) {
      return skeleton(low, script, this.options).map((k) => [null, k]);
    }
    if (script !== 'cyrillic') return [[null, fold(low)]];
    const opts = cyrOptions(low, cyrillicKeyboardRecovery);
    const leaves = [];
    const choice = [];
    const walk = (i, str) => {
      if (i === opts.length) { leaves.push([choice.slice(), fold(str)]); return; }
      for (const o of opts[i]) {
        const next = str + o;
        if (opts[i].length > 1 && !this._exists(fold(next), true)) continue;
        choice.push(o);
        walk(i + 1, next);
        choice.pop();
      }
    };
    walk(0, '');
    return prefix ? leaves : leaves.filter(([, k]) => this._exists(k, false));
  }

  _unitsFor(low, script, choice) {
    return script === 'cyrillic' && choice ? cyrillicUnits(low, choice) : latinUnits(low);
  }

  /** Candidates of a token with no valid reading: [{ word, id, ev }]. */
  _candidates(low, script) {
    const lex = this.lex;
    const best = new Map();
    const cyr = script === 'cyrillic';
    for (const [choice, k] of this._leaves(low, script, false)) {
      const units = this._unitsFor(low, script, choice);
      const consider = (word, id) => {
        const ev = evidence(units, word, cyr);
        if (!ev) return;
        const prev = best.get(word);
        if (!prev || ev.sum > prev.ev.sum) best.set(word, { word, id, ev });
      };
      const [lo, hi] = lex.range(k);
      for (let i = lo; i < hi; i++) consider(lex.word(i), i);
      for (const w of this.user.withKey(k)) if (lex.indexOf(w) < 0) consider(w, -1);
    }
    return [...best.values()];
  }

  _score(c, prevId) {
    const lex = this.lex;
    const uni = c.id >= 0 ? lnUnigram(lex, c.id) : 0;
    const bi = c.id >= 0 ? lex.lnBigram(prevId, c.id) : 0;
    return score(uni, bi, this.user.bonus(c.word), c.ev.sum);
  }

  /** §7.3 whole-text pass. */
  autocorrect(text) {
    const lex = this._lexicon();
    const { script: outScript } = this.options;
    const segs = tokenize(text);

    const initial = new Set();
    const shouting = new Set();
    let chunk = [];
    const closeChunk = () => {
      const long = chunk.filter((i) => segs[i].end - segs[i].start >= 2);
      if (long.length && long.every((i) => casePattern(text.slice(segs[i].start, segs[i].end)) === 'upper')) {
        for (const i of chunk) shouting.add(i);
      }
      chunk = [];
    };
    segs.forEach((s, i) => {
      if (s.kind === 'gap' && BREAK_RE.test(text.slice(s.start, s.end))) closeChunk();
      if (s.kind === 'token') {
        if (!chunk.length) initial.add(i);
        chunk.push(i);
      }
    });
    closeChunk();

    let out = '';
    let prevId = -1;
    segs.forEach((s, i) => {
      const raw = text.slice(s.start, s.end);
      if (s.kind === 'gap') {
        if (BREAK_RE.test(raw)) prevId = -1;
        out += raw;
        return;
      }
      if (s.kind === 'protected') { out += raw; prevId = -1; return; }
      const low = normalize(raw).toLowerCase();
      const script = detectScript(low);
      const pattern = casePattern(raw);
      if (script === 'mixed' || pattern === 'mixed') { out += raw; prevId = -1; return; }
      const letters = letterCount(low);
      const valid = this._valid(low, script);
      if (letters < 2) { out += raw; prevId = valid ? valid.id : -1; return; }  // default D4
      let chosen = valid;
      if (!chosen) {
        if (pattern === 'upper' && !shouting.has(i) && letters <= ACRONYM_MAX_LETTERS) {  // default D3
          out += raw; prevId = -1; return;
        }
        let cands = this._candidates(low, script).filter((c) => c.ev.min >= 0);  // default D2: never drop a typed mark
        if ((pattern === 'title' || pattern === 'upper') && !initial.has(i) && !shouting.has(i)) {
          cands = cands.filter((c) => c.id < 0 || lex.capitalized(c.id));  // default D3: proper-noun positions
        }
        if (!cands.length) { out += raw; prevId = -1; return; }
        let top = cands[0];
        let topScore = this._score(top, prevId);
        for (let j = 1; j < cands.length; j++) {
          const sc = this._score(cands[j], prevId);
          if (sc > topScore) { top = cands[j]; topScore = sc; }
        }
        // §5 runtime invariant guard.
        if (!skeleton(low, script, this.options).includes(keyOf(top.word))) { out += raw; prevId = -1; return; }
        chosen = top;
      }
      const rendered = render(chosen.word, outScript, pattern);
      out += sameLetters(rendered, raw) ? raw : rendered;
      prevId = chosen.id;
    });
    return out;
  }

  _contextId(word) {
    if (!word) return -1;
    const low = normalize(word).toLowerCase();
    const script = detectScript(low);
    if (script === 'mixed') return -1;
    const v = this._valid(low, script);
    return v ? v.id : -1;
  }

  _topByUnigram(lo, hi, count) {
    const q = this.lex.uniQ;
    if (hi - lo <= count) return Array.from({ length: hi - lo }, (_, j) => lo + j);
    const hist = new Uint32Array(256);
    for (let i = lo; i < hi; i++) hist[q[i]]++;
    let cut = 255;
    for (let acc = 0; cut > 0; cut--) { acc += hist[cut]; if (acc >= count) break; }
    const ids = [];
    for (let i = lo; i < hi && ids.length < count; i++) if (q[i] > cut) ids.push(i);
    for (let i = lo; i < hi && ids.length < count; i++) if (q[i] === cut) ids.push(i);
    return ids;
  }

  /** §7.2 live suggestions for a partial token. */
  suggest(buffer, prevWord = null) {
    const lex = this._lexicon();
    const { maxSuggestions, script: outScript } = this.options;
    const prevId = this._contextId(prevWord);
    const found = new Map();
    const add = (word, id, ev, exact) => {
      const bi = id >= 0 ? lex.lnBigram(prevId, id) : 0;
      const bonus = this.user.bonus(word);
      const sc = score(id >= 0 ? lnUnigram(lex, id) : 0, bi, bonus, ev);
      const prev = found.get(word);
      if (prev && prev.score >= sc) return;
      const source = exact ? 'exact' : bonus > 0 ? 'user' : bi > 0 ? 'bigram' : 'lexicon';
      found.set(word, { word, score: sc, source });
    };

    if (!buffer) {
      const succ = lex.successors(prevId).sort((a, b) => b[1] - a[1]).slice(0, SUGGEST_BIGRAM_POOL);
      for (const [id] of succ) add(lex.word(id), id, 0, false);
    } else {
      const low = normalize(buffer).toLowerCase();
      const script = detectScript(low);
      if (script === 'mixed') return [];
      const valid = this._valid(low, script);
      const cyr = script === 'cyrillic';
      for (const [choice, k] of this._leaves(low, script, true)) {
        const units = this._unitsFor(low, script, choice);
        const [lo, hi] = lex.prefixRange(k);
        const ids = new Set(hi - lo <= SUGGEST_SCAN_ALL
          ? Array.from({ length: hi - lo }, (_, j) => lo + j)
          : this._topByUnigram(lo, hi, SUGGEST_UNIGRAM_POOL));
        if (prevId >= 0) {
          const succ = lex.successors(prevId, lo, hi).sort((a, b) => b[1] - a[1]).slice(0, SUGGEST_BIGRAM_POOL);
          for (const [id] of succ) ids.add(id);
        }
        for (const id of ids) {
          const word = lex.word(id);
          const ev = evidence(units, word, cyr, true);
          if (ev) add(word, id, ev.sum, valid && valid.word === word);
        }
        for (const word of this.user.withKeyPrefix(k)) {
          const ev = evidence(units, word, cyr, true);
          if (ev) add(word, lex.indexOf(word), ev.sum, valid && valid.word === word);
        }
      }
      const pattern = casePattern(buffer) === 'mixed' ? 'lower' : casePattern(buffer);
      const ranked = [...found.values()].sort((a, b) => b.score - a.score);
      const top = ranked.slice(0, maxSuggestions);
      // Default D13: a typed word that is itself valid is always offered.
      const exact = valid && found.get(valid.word);
      if (exact && !top.includes(exact) && top.length) top[top.length - 1] = exact;
      return top.map((s) => ({ ...s, word: render(s.word, outScript, pattern) }));
    }
    return [...found.values()]
      .sort((a, b) => b.score - a.score)
      .slice(0, maxSuggestions)
      .map((s) => ({ ...s, word: render(s.word, outScript, 'lower') }));
  }

  /** §7.4 pure conversion. */
  convert(text, from, to) {
    return convertText(text, from, to);
  }

  /** §7.5 on-device learning. The word is read in the current output script. */
  learn(word) {
    const low = normalize(word).toLowerCase();
    const script = this.options.script;
    const canon = script === 'cyrillic' ? cyrToNewLower(low) : script === 'old' ? oldToNewLower(low) : literalLower(low);
    if (canon) this.user.learn(canon);
  }

  export() {
    return this.user.export();
  }

  stats() {
    return {
      lexiconSize: this.lex ? this.lex.size : 0,
      memoryBytes: (this.lex ? this.lex.memoryBytes() : 0) + this.user.estimateBytes(),
      loadMs: this.loadMs,
    };
  }
}
