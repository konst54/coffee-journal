// Supabase Auth (magic link, implicit flow) + read of the owner's projection, via plain fetch.
// Access token lives in memory only; the rotating refresh token is kept in localStorage so the
// phone does not need a new e-mail every visit. Risk accepted: data is read-only for the browser,
// CSP forbids third-party/inline scripts and all rendering uses textContent.
const REFRESH_KEY = 'coffee-journal.refresh';
const PROJECT_URL = /^https:\/\/[a-z0-9-]+\.supabase\.co$/;

export function createSupabaseAuth({url, key, fetch, storage, location, history, now = () => Date.now()}) {
  const configured = Boolean(url && key);
  if (configured && !PROJECT_URL.test(url)) throw new Error('Unexpected Supabase URL');
  let access = null, expiresAt = 0;
  const base = {apikey: key, 'content-type': 'application/json'};
  const read = () => { try { return storage.getItem(REFRESH_KEY); } catch { return null; } };
  const write = t => { try { t ? storage.setItem(REFRESH_KEY, t) : storage.removeItem(REFRESH_KEY); } catch { /* storage blocked */ } };
  function adopt(tokens) {
    if (typeof tokens?.access_token !== 'string' || typeof tokens?.refresh_token !== 'string') throw new Error('Bad session');
    access = tokens.access_token;
    expiresAt = now() + (Number(tokens.expires_in) > 0 ? Number(tokens.expires_in) : 3600) * 1000;
    write(tokens.refresh_token);
  }
  function clear() { access = null; expiresAt = 0; write(null); }

  return {
    configured,
    /** Take tokens from the magic-link redirect fragment and remove them from the address bar. */
    consumeRedirect() {
      const hash = location.hash?.startsWith('#') ? location.hash.slice(1) : '';
      if (!hash) return null;
      const p = new URLSearchParams(hash);
      if (!p.has('access_token') && !p.has('error') && !p.has('error_description')) return null;
      history.replaceState(null, '', location.pathname + location.search);
      if (p.has('error') || p.has('error_description')) return {error: p.get('error_description') || p.get('error')};
      adopt({access_token: p.get('access_token'), refresh_token: p.get('refresh_token'), expires_in: p.get('expires_in')});
      return {ok: true};
    },
    async sendMagicLink(email) {
      if (!configured) throw new Error('Not configured');
      if (typeof email !== 'string' || !/^[^\s@]+@[^\s@]+$/.test(email.trim())) throw new Error('Invalid email');
      const redirect = location.origin + location.pathname;
      const res = await fetch(`${url}/auth/v1/otp?redirect_to=${encodeURIComponent(redirect)}`, {
        method: 'POST', headers: base, body: JSON.stringify({email: email.trim(), create_user: false})});
      if (!res.ok) throw new Error('Login request failed');
    },
    async session() {
      if (!configured) return null;
      if (access && expiresAt - now() > 30000) return access;
      const refresh = read();
      if (!refresh) { access = null; return null; }
      const res = await fetch(`${url}/auth/v1/token?grant_type=refresh_token`, {
        method: 'POST', headers: base, body: JSON.stringify({refresh_token: refresh})});
      if (!res.ok) { clear(); return null; }
      adopt(await res.json());
      return access;
    },
    /** Resolves {authenticated:true, dataset} for the signed-in owner, or null when signed out. */
    async loadOwnJournal() {
      const token = await this.session();
      if (!token) return null;
      const res = await fetch(`${url}/rest/v1/journal_snapshots?select=dataset,revision`, {
        headers: {apikey: key, authorization: `Bearer ${token}`, accept: 'application/json'}});
      if (res.status === 401 || res.status === 403) { clear(); return null; }
      if (!res.ok) throw new Error('Journal request failed');
      const rows = await res.json();
      if (!Array.isArray(rows) || rows.length > 1) throw new Error('Unexpected response');
      const dataset = rows[0]?.dataset ?? {schema_version: 1, coffees: [], batches: [], equipment: [], recipes: [], brews: []};
      return {authenticated: true, dataset, revision: rows[0]?.revision ?? 0};
    },
    async logout() {
      const token = access;
      clear();
      if (token) {
        try { await fetch(`${url}/auth/v1/logout`, {method: 'POST', headers: {...base, authorization: `Bearer ${token}`}}); }
        catch { /* local sign-out already done */ }
      }
    },
  };
}
