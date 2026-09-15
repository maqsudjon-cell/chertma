// Sliding-window rate limit, in memory, per function instance. No persistence.
export class RateLimiter {
  constructor(limit, windowMs = 60_000, maxKeys = 10_000) {
    this.limit = limit;
    this.windowMs = windowMs;
    this.maxKeys = maxKeys;
    this.hits = new Map(); // key → timestamps (ms)
  }

  allow(key, now = Date.now()) {
    const since = now - this.windowMs;
    const list = (this.hits.get(key) ?? []).filter((t) => t > since);
    if (list.length >= this.limit) {
      this.hits.set(key, list);
      return false;
    }
    list.push(now);
    this.hits.delete(key); // re-insert so Map order is least-recently-used first
    this.hits.set(key, list);
    if (this.hits.size > this.maxKeys) this.hits.delete(this.hits.keys().next().value);
    return true;
  }
}
