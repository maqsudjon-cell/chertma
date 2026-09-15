// Binary lexicon reader — docs/SPEC.md §9. Read in place; words and keys are
// decoded lazily, only when a lookup touches them.

import { key as keyOf } from './skeleton.js';

const MAGIC = 0x54524843; // "CHRT" little-endian
const FLAG_WIDE_IDS = 4;
const WFLAG_CAPITALIZED = 1;
const WFLAG_PROTECTED = 2;

const DECODE = new Array(256).fill(null);
for (let b = 0x61; b <= 0x7a; b++) DECODE[b] = String.fromCharCode(b);
DECODE[0x80] = 'ş'; DECODE[0x81] = 'ç'; DECODE[0x82] = 'ö'; DECODE[0x83] = 'ğ'; DECODE[0x84] = 'ʼ';

let CRC_TABLE = null;
function crc32(bytes) {
  if (!CRC_TABLE) {
    CRC_TABLE = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      CRC_TABLE[n] = c >>> 0;
    }
  }
  let c = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

export class Lexicon {
  constructor(input) {
    let buf;
    if (input instanceof ArrayBuffer) buf = input;
    else if (ArrayBuffer.isView(input)) {
      buf = input.byteOffset === 0 && input.byteLength === input.buffer.byteLength
        ? input.buffer
        : input.buffer.slice(input.byteOffset, input.byteOffset + input.byteLength);
    } else throw new TypeError('Chertma: lexicon must be an ArrayBuffer or a typed array');
    if (new Uint8Array(new Uint16Array([1]).buffer)[0] !== 1) throw new Error('Chertma: big-endian hosts are not supported');
    const dv = new DataView(buf);
    if (buf.byteLength < 0xa0 || dv.getUint32(0, true) !== MAGIC) throw new Error('Chertma: not a lexicon file');
    if (dv.getUint16(4, true) !== 1) throw new Error('Chertma: unsupported lexicon version');
    if (crc32(new Uint8Array(buf, 0x40)) !== dv.getUint32(0x24, true)) throw new Error('Chertma: lexicon checksum mismatch');
    const flags = dv.getUint16(6, true);
    const n = dv.getUint32(8, true);
    const b = dv.getUint32(12, true);
    this.qsUni = dv.getFloat32(0x14, true);
    this.qsBi = dv.getFloat32(0x18, true);
    const sec = (i) => [dv.getUint32(0x40 + 8 * i, true), dv.getUint32(0x44 + 8 * i, true)];
    const [strOff, strLen] = sec(0);
    this.buffer = buf;
    this.size = n;
    this.bigramCount = b;
    this.str = new Uint8Array(buf, strOff, strLen);
    const lens = new Uint8Array(buf, sec(1)[0], n);
    this.offsets = new Uint32Array(n + 1);
    for (let i = 0; i < n; i++) this.offsets[i + 1] = this.offsets[i] + lens[i];
    if (this.offsets[n] !== strLen) throw new Error('Chertma: corrupt string table');
    this.uniQ = new Uint8Array(buf, sec(2)[0], n);
    this.infQ = new Uint8Array(buf, sec(3)[0], n);
    this.wflags = new Uint8Array(buf, sec(4)[0], n);
    this.bgOff = new Uint32Array(buf, sec(5)[0], n + 1);
    this.bgId = flags & FLAG_WIDE_IDS ? new Uint32Array(buf, sec(6)[0], b) : new Uint16Array(buf, sec(6)[0], b);
    this.bgQ = new Uint8Array(buf, sec(7)[0], b);
    this._words = new Array(n);
    this._keys = new Array(n);
    // Section 9 (optional): the suffix-chain inventory for morphological fallback (§5.2, §9.3).
    this.suffixes = null;
    const [sfxOff, sfxLen] = sec(9);
    if (sfxLen >= 4) {
      const count = dv.getUint32(sfxOff, true);
      const set = new Set();
      let p = sfxOff + 4;
      for (let j = 0; j < count; j++) {
        const len = dv.getUint8(p++);
        let s = '';
        for (let e = p + len; p < e; p++) s += DECODE[dv.getUint8(p)];
        set.add(s);
      }
      this.suffixes = set;
    }
  }

  word(i) {
    let w = this._words[i];
    if (w === undefined) {
      w = '';
      for (let p = this.offsets[i], e = this.offsets[i + 1]; p < e; p++) w += DECODE[this.str[p]];
      this._words[i] = w;
    }
    return w;
  }

  key(i) {
    let k = this._keys[i];
    if (k === undefined) this._keys[i] = k = keyOf(this.word(i));
    return k;
  }

  /** First id whose key is >= k. */
  lowerBound(k) {
    let lo = 0;
    let hi = this.size;
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      if (this.key(mid) < k) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  }

  /** [lo, hi) of words whose key equals k. */
  range(k) {
    const lo = this.lowerBound(k);
    let hi = lo;
    while (hi < this.size && this.key(hi) === k) hi++;
    return [lo, hi];
  }

  /** [lo, hi) of words whose key starts with k. Keys are ASCII, so k + DEL bounds them. */
  prefixRange(k) {
    return [this.lowerBound(k), this.lowerBound(k + '')];
  }

  hasPrefix(k) {
    const i = this.lowerBound(k);
    return i < this.size && this.key(i).startsWith(k);
  }

  indexOf(word) {
    const [lo, hi] = this.range(keyOf(word));
    for (let i = lo; i < hi; i++) if (this.word(i) === word) return i;
    return -1;
  }

  lnUnigram(i) { return this.uniQ[i] / this.qsUni; }
  lnInformal(i) { return this.infQ[i] ? this.infQ[i] / this.qsUni : null; }
  capitalized(i) { return (this.wflags[i] & WFLAG_CAPITALIZED) !== 0; }
  isProtected(i) { return (this.wflags[i] & WFLAG_PROTECTED) !== 0; }

  /** ln(count + 1) of the bigram (prev, id); 0 when absent. */
  lnBigram(prev, id) {
    if (prev < 0) return 0;
    let lo = this.bgOff[prev];
    let hi = this.bgOff[prev + 1];
    while (lo < hi) {
      const mid = (lo + hi) >>> 1;
      const v = this.bgId[mid];
      if (v < id) lo = mid + 1;
      else if (v > id) hi = mid;
      else return Math.log(Math.exp(this.bgQ[mid] / this.qsBi) + 1);
    }
    return 0;
  }

  /** Bigram successors of prev with ids in [lo, hi): [[id, lnBigram], …]. */
  successors(prev, lo = 0, hi = this.size) {
    if (prev < 0) return [];
    const start = this.bgOff[prev];
    const end = this.bgOff[prev + 1];
    let a = start;
    let b = end;
    while (a < b) { const m = (a + b) >>> 1; if (this.bgId[m] < lo) a = m + 1; else b = m; }
    const out = [];
    for (let p = a; p < end && this.bgId[p] < hi; p++) out.push([this.bgId[p], Math.log(Math.exp(this.bgQ[p] / this.qsBi) + 1)]);
    return out;
  }

  memoryBytes() {
    let cached = 0;
    for (const w of this._words) if (w !== undefined) cached += 2 * w.length + 32;
    for (const k of this._keys) if (k !== undefined) cached += 2 * k.length + 32;
    return this.buffer.byteLength + this.offsets.byteLength + 16 * this.size + cached;
  }
}
