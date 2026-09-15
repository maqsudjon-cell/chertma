// Bot API calls for the few cases a webhook reply cannot cover. Every failure is
// returned as a value, never thrown, and never includes the token or message text.
export async function callApi(token, method, params, { fetchImpl = globalThis.fetch, timeoutMs = 8000 } = {}) {
  if (!token) return { ok: false, code: 'no_token' };
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetchImpl(`https://api.telegram.org/bot${token}/${method}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(params),
      signal: ctrl.signal,
    });
    let data = null;
    try { data = await res.json(); } catch { /* non-JSON error page */ }
    if (data && data.ok) return { ok: true, result: data.result };
    return { ok: false, code: data?.error_code ?? res.status ?? 'bad_response' };
  } catch (err) {
    return { ok: false, code: err?.name === 'AbortError' ? 'timeout' : 'network' };
  } finally {
    clearTimeout(timer);
  }
}
