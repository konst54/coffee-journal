# Hosting and Supabase — код готов, облако не развёрнуто

Пошаговая инструкция для владельца: [SETUP_SUPABASE.md](SETUP_SUPABASE.md).

## Архитектура v1
Каноническая база — приватный SQLite на хосте Гермеса. Supabase хранит только авторизованную read-only проекцию `journal_snapshots` (одна строка на владельца, без `source_*` полей). Публикует её `python3 -m coffee_journal publish` от имени обычного Auth-пользователя-владельца (allowlist `journal_private.writers`) с проверкой ревизии и чтением результата. Секретные/service ключи не используются нигде.

Сайт — статический (`web/`, без сборки и зависимостей), подходит для GitHub Pages. При пустом `web/config.js` показывает только вымышленное демо. Если задать URL проекта и publishable key, появляется вход по magic link: только для существующих пользователей, после входа читается собственная строка проекции.

## Реализовано и проверено локально
- `web/auth.js`, `web/authbar.js`: unit-тесты с фейковым fetch и настоящий Chromium (`tests/browser_auth_smoke.py`) с подменённой сетью Supabase.
- `coffee_journal/publish.py`: тесты против локального фейкового Auth/PostgREST (`tests/test_publish.py`): ротация токена, конфликт ревизии, отказ writer, подмена при чтении назад.
- SQL/RLS: PGlite (`tools/sql-check`).

## НЕ проверено (нужен реальный проект)
Реальные GoTrue/PostgREST, письма magic link, CORS, ограничения частоты, поведение publishable key, реальный хостинг и заголовки. До выполнения раздела 6 в SETUP_SUPABASE система не считается развёрнутой.

## Почему не автодеплой
AGENTS.md запрещает автоматический production-деплой. Публикация на Pages выполняется по явному разрешению владельца (`tools/build-pages.sh`, ветка `gh-pages`). CI с deploy-шагом можно добавить позже, когда у токена будет workflow scope.
