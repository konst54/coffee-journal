import test from 'node:test';
import assert from 'node:assert/strict';
import {createSupabaseAuth} from '../auth.js';

const URL_ = 'https://abcdefgh.supabase.co', KEY = 'sb_publishable_test';
function env({hash = '', responses = []} = {}) {
  const calls = [], store = new Map();
  const location = {hash, origin: 'https://user.github.io', pathname: '/coffee-journal/', search: ''};
  const history = {replaceState: (_s, _t, u) => { location.hash = ''; history.last = u; }};
  const fetch = async (u, init = {}) => {
    calls.push({u, init});
    const r = responses.shift() ?? {status: 500, body: {}};
    return {ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.body};
  };
  const storage = {getItem: k => store.get(k) ?? null, setItem: (k, v) => store.set(k, v), removeItem: k => store.delete(k)};
  let t = 1_000_000;
  const auth = createSupabaseAuth({url: URL_, key: KEY, fetch, storage, location, history, now: () => t});
  return {auth, calls, store, location, history, advance: ms => { t += ms; }};
}
const ok = body => ({status: 200, body});
const tokens = n => ({access_token: 'acc' + n, refresh_token: 'ref' + n, expires_in: 3600});

test('unconfigured means demo only; foreign URLs are refused', async () => {
  const a = createSupabaseAuth({url: '', key: '', fetch: null, storage: null, location: {}, history: {}});
  assert.equal(a.configured, false);
  assert.equal(await a.session(), null);
  assert.throws(() => createSupabaseAuth({url: 'https://evil.example', key: KEY}));
});

test('magic link request never creates users and returns to this page', async () => {
  const {auth, calls} = env({responses: [ok({})]});
  await assert.rejects(auth.sendMagicLink('not-an-email'));
  await auth.sendMagicLink(' me@example.org ');
  assert.equal(calls.length, 1);
  assert.match(calls[0].u, /\/auth\/v1\/otp\?redirect_to=https%3A%2F%2Fuser\.github\.io%2Fcoffee-journal%2F$/);
  assert.deepEqual(JSON.parse(calls[0].init.body), {email: 'me@example.org', create_user: false});
  assert.equal(calls[0].init.headers.apikey, KEY);
});

test('redirect tokens are consumed and wiped from the address bar', async () => {
  const {auth, store, location, history, calls} = env({hash: '#access_token=acc1&refresh_token=ref1&expires_in=3600&type=magiclink',
    responses: [ok([{dataset: {schema_version: 1, coffees: [], batches: [], equipment: [], recipes: [], brews: []}, revision: 4}])]});
  assert.deepEqual(auth.consumeRedirect(), {ok: true});
  assert.equal(location.hash, '');
  assert.equal(history.last, '/coffee-journal/');
  assert.equal([...store.values()][0], 'ref1');
  const result = await auth.loadOwnJournal();
  assert.equal(result.authenticated, true);
  assert.equal(result.revision, 4);
  assert.equal(calls[0].init.headers.authorization, 'Bearer acc1');
  assert.match(calls[0].u, /\/rest\/v1\/journal_snapshots\?select=dataset,revision$/);
});

test('error fragment is reported and cleared; unrelated fragments are ignored', () => {
  const e = env({hash: '#error=access_denied&error_description=Email+link+is+invalid'});
  assert.deepEqual(e.auth.consumeRedirect(), {error: 'Email link is invalid'});
  assert.equal(e.location.hash, '');
  const other = env({hash: '#section'});
  assert.equal(other.auth.consumeRedirect(), null);
  assert.equal(other.location.hash, '#section');
});

test('expired access is refreshed with rotation; failed refresh signs out', async () => {
  const {auth, store, calls, advance} = env({hash: '#access_token=acc1&refresh_token=ref1&expires_in=60',
    responses: [ok(tokens(2)), {status: 400, body: {}}]});
  auth.consumeRedirect();
  advance(45_000);
  assert.equal(await auth.session(), 'acc2');
  assert.deepEqual(JSON.parse(calls[0].init.body), {refresh_token: 'ref1'});
  assert.equal([...store.values()][0], 'ref2');
  advance(3_600_000);
  assert.equal(await auth.session(), null);
  assert.equal(store.size, 0);
});

test('401 from data API clears the session; signed-out load returns null', async () => {
  const {auth, store} = env({hash: '#access_token=a&refresh_token=r&expires_in=3600', responses: [{status: 401, body: {}}]});
  auth.consumeRedirect();
  assert.equal(await auth.loadOwnJournal(), null);
  assert.equal(store.size, 0);
  assert.equal(await auth.loadOwnJournal(), null);
});

test('logout clears local session even if the network call fails', async () => {
  const {auth, store} = env({hash: '#access_token=a&refresh_token=r&expires_in=3600'});
  auth.consumeRedirect();
  await auth.logout();
  assert.equal(store.size, 0);
  assert.equal(await auth.session(), null);
});
