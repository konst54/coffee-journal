import {createViewer} from './app.js';
import {demoDataset} from './demo.js';
import {createSupabaseAuth} from './auth.js';
import {mountAuthBar} from './authbar.js';
import {SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY} from './config.js';

const viewer = createViewer(document.getElementById('app'));
viewer.loadDataset(demoDataset);

let storage = null;
try { storage = window.localStorage; } catch { /* blocked: session lasts until reload */ }
const memory = new Map();
storage ??= {getItem: k => memory.get(k) ?? null, setItem: (k, v) => memory.set(k, v), removeItem: k => memory.delete(k)};

const auth = createSupabaseAuth({url: SUPABASE_URL, key: SUPABASE_PUBLISHABLE_KEY,
  fetch: window.fetch.bind(window), storage, location: window.location, history: window.history});
if (auth.configured) {
  const bar = mountAuthBar(document.getElementById('auth'), {auth, viewer, demo: demoDataset});
  let message = '';
  try {
    const redirect = auth.consumeRedirect();
    if (redirect?.error) message = 'Ссылка для входа недействительна или устарела. Запросите новую.';
  } catch { message = 'Не удалось завершить вход.'; }
  bar.refresh(message);
}
