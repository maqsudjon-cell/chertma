// On-device personalization — docs/SPEC.md §7.5. Nothing here leaves the device.

import { USER_HALF_LIFE_MS, USER_MAX_WORDS } from './constants.js';
import { key as keyOf } from './skeleton.js';

export class UserModel {
  constructor(saved, clock) {
    this.clock = clock;
    this.words = new Map(); // word → { count, last }
    this.byKey = new Map(); // key → Set(word)
    if (saved && saved.format === 'chertma-user' && Array.isArray(saved.words)) {
      for (const [w, count, last] of saved.words) this._put(w, { count, last });
    }
  }

  _put(word, entry) {
    if (!this.words.has(word)) {
      const k = keyOf(word);
      if (!this.byKey.has(k)) this.byKey.set(k, new Set());
      this.byKey.get(k).add(word);
    }
    this.words.set(word, entry);
  }

  _decayed(entry, now) {
    return entry.count * Math.pow(2, -(now - entry.last) / USER_HALF_LIFE_MS);
  }

  learn(word) {
    const now = this.clock();
    const e = this.words.get(word);
    this._put(word, { count: (e ? this._decayed(e, now) : 0) + 1, last: now });
    if (this.words.size > USER_MAX_WORDS) {
      let worst = null;
      let low = Infinity;
      for (const [w, en] of this.words) {
        const d = this._decayed(en, now);
        if (d < low) { low = d; worst = w; }
      }
      this.words.delete(worst);
      const k = keyOf(worst);
      this.byKey.get(k)?.delete(worst);
    }
  }

  has(word) { return this.words.has(word); }

  bonus(word) {
    const e = this.words.get(word);
    return e ? Math.log(1 + this._decayed(e, this.clock())) : 0;
  }

  withKey(k) { return this.byKey.get(k) ?? []; }

  withKeyPrefix(k) {
    const out = [];
    for (const [key, set] of this.byKey) if (key.startsWith(k)) out.push(...set);
    return out;
  }

  export() {
    return { format: 'chertma-user', version: 1, words: [...this.words].map(([w, e]) => [w, e.count, e.last]) };
  }

  estimateBytes() { return this.words.size * 96; }
}
