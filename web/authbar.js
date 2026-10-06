// Sign-in strip. Only an e-mail field for a magic link: no record-entry forms, no passwords.
export function mountAuthBar(root, {auth, viewer, demo, doc = document}) {
  const el = (tag, text, cls) => { const n = doc.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  const status = el('p', '', 'auth-status');
  function signedOut(message = '') {
    const email = el('input'); email.type = 'email'; email.autocomplete = 'email';
    email.setAttribute('aria-label', 'E-mail для входа'); email.placeholder = 'e-mail для входа';
    const send = el('button', 'Получить ссылку');
    send.addEventListener('click', async () => {
      send.disabled = true;
      try { await auth.sendMagicLink(email.value); status.textContent = 'Ссылка отправлена. Откройте её на этом устройстве.'; }
      catch { status.textContent = 'Не удалось отправить ссылку. Проверьте адрес.'; }
      finally { send.disabled = false; }
    });
    status.textContent = message;
    root.replaceChildren(email, send, status);
  }
  function signedIn() {
    const out = el('button', 'Выйти');
    out.addEventListener('click', async () => { await auth.logout(); viewer.loadDataset(demo); signedOut('Вы вышли.'); });
    status.textContent = '';
    root.replaceChildren(out, status);
  }
  async function refresh(message) {
    try {
      const result = await auth.loadOwnJournal();
      if (result) { await viewer.loadAuthenticated(async () => result); signedIn(); return; }
      signedOut(message);
    } catch {
      viewer.loadDataset(demo);
      signedOut('Не удалось загрузить личные записи. Показана демонстрация.');
    }
  }
  return {signedOut, refresh};
}
