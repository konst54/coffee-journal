# Подключение Supabase и сайта — шаги для владельца

Код готов. Если подключить коннектор Supabase к claude.ai, агент сам проверит проект, миграции и ключи, а для изменений попросит подтверждение. Без коннектора эти шаги выполняет владелец. Секретные ключи (`sb_secret_…`, service_role, пароль базы) **никому не пересылать**, в чат и в репозиторий не вставлять. Нужны только два публичных значения: адрес проекта и publishable key.

## 1. Проект и таблица — через интеграцию GitHub (владелец её подключил)
Факты на 2026-10-06 (проверено через GitHub):
- `main` содержит только `AGENTS.md`. Папки `supabase/` в `main` нет, значит, интеграция ещё ничего не применяла.
- На PR #1 нет ни проверок, ни комментариев от Supabase: preview-ветки для этого PR не создаются. Возможные причины: интеграция привязана к другому репозиторию или каталогу, branching выключен, или ей нужен `supabase/config.toml`, которого в репозитории нет.
- Какой проект и какая production-ветка выбраны и включён ли «Deploy to production», видно только в Supabase: Project Settings → Integrations → GitHub. Агент Supabase пока не видит: коннектора нет, сеть среды не пускает к supabase.com.

Правила, чтобы не повредить облачную базу:
- **Не сливать PR #1 в production-ветку**, пока не подтверждены проект и ветка. Слияние может автоматически выполнить `supabase/migrations/001_projection.sql` в выбранном проекте.
- Выбрать один путь применения миграции: **либо** интеграция (слияние), **либо** ручной запуск в SQL Editor — не оба. Скрипт создаёт схему без `IF NOT EXISTS`. Повторный запуск откатится целиком (BEGIN/COMMIT), но деплой будет помечен как неудачный.
- Перед слиянием агент через коннектор проверяет: проект — тот самый, `journal_private` и `journal_snapshots` ещё не существуют, список применённых миграций пуст или ожидаем.

Ручной путь, если интеграция не нужна: SQL Editor → вставить `supabase/migrations/001_projection.sql` → Run, один раз.

## 2. Вход (≈3 мин)
1. Authentication → Sign In / Providers: **выключить «Allow new users to sign up»**. Email-провайдер оставить включённым.
2. Authentication → URL Configuration: Site URL и Redirect URLs = `https://konst54.github.io/coffee-journal/` (точный адрес, без `*`).
3. Authentication → Users → Add user → Create new user: ваш e-mail, **длинный уникальный пароль**, Auto Confirm. Пароль понадобится один раз — для входа публикатора на хосте Гермеса.
4. Скопировать User UID этого пользователя. В SQL Editor выполнить:
   ```sql
   insert into journal_private.writers(user_id) values ('ВАШ-USER-UID');
   ```

## 3. Публичные значения для сайта
Project Settings → API Keys: **Publishable key** (`sb_publishable_…`) и Project URL (`https://xxxx.supabase.co`). Их можно прислать в чат: они и так видны любому посетителю сайта, а защищает данные RLS. Агент впишет их в `web/config.js`.

## 4. Репозиторий и сайт
1. GitHub → Settings → Danger Zone → Change visibility → Public. История проверена: ключей и личных данных нет. Тест `tests/test_repo_hygiene.py` блокирует их появление в будущем.
2. Публикацию сайта агент делает только с вашего явного разрешения. Автоматический production-деплой в этом проекте запрещён правилами, и среда агента заблокировала попытку без вашего подтверждения. Сборка: `tools/build-pages.sh OUT` (только runtime-файлы, проверка на секреты). Затем Settings → Pages → Deploy from a branch → `gh-pages` / root.

## 5. Публикатор на хосте Гермеса (один раз)
```sh
export COFFEE_SUPABASE_URL=https://xxxx.supabase.co COFFEE_SUPABASE_KEY=sb_publishable_...
python3 -m coffee_journal publish-login --email you@example.org   # пароль вводится скрыто
python3 -m coffee_journal publish                                  # после каждого внесения
```
Пароль не сохраняется. В `supabase-session.json` рядом с приватной базой (права 600) хранится только обновляемый refresh token. Чтобы отозвать доступ, удалите файл и смените пароль или выйдите из всех сессий в Supabase.

## 6. Проверка перед тем, как считать готовым
- Аноним: `curl -s 'https://xxxx.supabase.co/rest/v1/journal_snapshots?select=*' -H 'apikey: sb_publishable_...'` → `[]` или ошибка, но не данные.
- Второй тестовый пользователь (создать временно, не добавлять в writers): видит пустой журнал, `publish` даёт `auth`. Затем удалить его.
- Ваш вход по ссылке на телефоне показывает «Личные данные» и ваши пробы.
