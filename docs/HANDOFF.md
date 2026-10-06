# Handoff — Coffee Journal

STATUS: READY_FOR_HANDOFF

Владелец: никто. Claude завершил этап «Supabase-код и подготовка к публичному репозиторию» 2026-10-06. Следующий агент перед началом работы ставит `STATUS: IN_PROGRESS` со своим именем отдельным коммитом и пушит его.

Это рабочий checkpoint, НЕ продакшен-релиз. Облако не развёрнуто.

## Откуда продолжать
- https://github.com/konst54/coffee-journal, ветка `feat/initial-journal`, draft PR #1. `main` содержит только bootstrap.
- Последний коммит с кодом: `78a8717` (Pages build script). Коммит с этим хэндоффом идёт следом — продолжать с последнего коммита удалённой ветки.
- Этапы: Гермес `117253c` (CLI, viewer, SQL/RLS) → Claude `b3085d6` (import), `ff979e1` (update/history) → Claude `cb9f2b3` (hygiene gate), `277ef26` (web auth), `3355d39` (publisher), `78a8717` (Pages bundle).

## Сделано на этом этапе
1. **Готовность к публичному репозиторию.** Вся история (каждый коммит обеих веток, PR #1) проверена regex-сканом и `detect-secrets`: 0 находок, авторы только с noreply-адресами. `tests/test_repo_hygiene.py` в обязательном гейте падает на секретных ключах Supabase, не-anon JWT, приватных ключах, токенах GitHub/AWS/OpenAI/Anthropic, URL Postgres с паролем и файлах БД/фото/.env. В `.gitignore` добавлены ключи и сессии.
2. **Сайт: вход и личные данные** (`web/auth.js`, `web/authbar.js`, `web/config.js`, `web/demo.js`). Вход по ссылке из письма, без создания пользователей. Чтение `journal_snapshots` своей строки. Ротация токена, выход. Пустой config → только демо. Записи по-прежнему нельзя вносить через сайт.
3. **Публикатор** (`coffee_journal/publish.py`, команды `publish-login` и `publish`): действует от имени владельца, хранит только refresh token (0600), использует ожидаемую ревизию, проверяет результат чтением, приватные source-поля не уходят.
4. **Сборка Pages** `tools/build-pages.sh OUT`: только runtime-файлы, отказ при подозрительном содержимом.
5. Документация: `docs/SETUP_SUPABASE.md` (шаги владельца), `docs/DEPLOYMENT.md`, `SECURITY.md` (решения и принятые риски), `docs/HERMES.md` (publish), README, BACKLOG.

Отклонение от TDD: тесты `web/tests/auth.test.js` написаны сразу после кода, а не до него. Остальное — тест → реализация.

## Проверки — реально выполнены 2026-10-06
- `python3 -m unittest discover -s tests -v` — 24 теста, OK (import, update/history/restore, publish против фейкового Auth/PostgREST, hygiene).
- `npm test --prefix web` — 14/14.
- `npm test --prefix tools/sql-check` — PASS (PGlite); `npm audit` — 0 уязвимостей.
- Chromium (Playwright 1.58): `tests/browser_smoke.py` (демо, 390/1280px) — PASS; `tests/browser_auth_smoke.py` (вход → личные данные → токен убран из URL → выход, Supabase замокан через route) — PASS, JS-ошибок нет.
- `git diff --check` — чисто.
- **Не проверено:** реальный Supabase (письма, CORS, publishable key, RLS по HTTP), реальный хостинг, удалённый CI.

## Блокеры (нужен владелец)
1. **Supabase.** У агента нет доступа к аккаунту Supabase: коннектора в сессии нет, ключа доступа тоже. Интеграция Supabase↔GitHub только применяет миграции при слиянии в production-ветку. Шаги для владельца — `docs/SETUP_SUPABASE.md` (≈10 минут). Агенту нужны только Project URL и publishable key — их можно прислать в чат, они публичны по дизайну.
2. **Публичность репозитория.** У GitHub-инструментов агента нет операции смены видимости — переключает владелец (Settings → Change visibility).
3. **Деплой на Pages.** Попытка запушить ветку `gh-pages` заблокирована средой агента как production deploy; AGENTS.md тоже запрещает автодеплой. Нужно явное разрешение владельца (или он деплоит сам: `tools/build-pages.sh` → ветка `gh-pages` → Settings → Pages).
4. **Skill Гермеса** на его хосте ещё не знает `import`/`update`/`publish`. Обновляет тот, у кого есть доступ к хосту.
5. Вопрос о порядке полей в slash-строке (см. предыдущий хэндофф) остаётся открытым.

## Связь с Гермесом и Supabase — фактическое состояние
- Гермес: внесение через `add` работает на его хосте. `import`, `update`, `publish` есть в коде, но skill их не использует.
- Supabase: код и SQL готовы, проект не настроен. `web/config.js` пустой, сайт показывает только демо.
- Pages: не опубликовано.

## Приватные данные
- Каноническая БД: `/opt/data/coffee-journal-private/journal.sqlite3` (хост Гермеса, вне Git). Сессия публикатора — `supabase-session.json` в той же директории (600). Пароль нигде не хранится.
- В Supabase попадает только экспорт без `source_text`/`source_refs` и без `history`. Он всё равно личный и доступен только владельцу через RLS.
- Секретные ключи Supabase, пароль БД и пароль пользователя не нужны ни агенту, ни сайту. Их нельзя присылать в чат и нельзя коммитить.

## Команды
```sh
git fetch origin && git switch feat/initial-journal && git pull --ff-only
python3 -m unittest discover -s tests -v
npm test --prefix web
npm ci --ignore-scripts --prefix tools/sql-check && npm test --prefix tools/sql-check
npm audit --prefix tools/sql-check --audit-level=moderate
CHROMIUM_PATH=/path/to/chrome uv run --with playwright==1.58.0 python tests/browser_auth_smoke.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory web   # + tests/browser_smoke.py
tools/build-pages.sh /tmp/site
```

## Следующий шаг
Когда владелец пришлёт Project URL и publishable key: вписать их в `web/config.js` (hygiene-тест пропускает только publishable/anon), пройти раздел 6 `SETUP_SUPABASE.md` на реальном проекте (аноним, второй пользователь, вход с телефона), получить разрешение и опубликовать Pages, затем обновить skill Гермеса на `import`/`publish`.
