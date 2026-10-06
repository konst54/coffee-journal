# Подключение Supabase и сайта — шаги для владельца

Код готов. Эти шаги требуют вашего входа в Supabase и GitHub, поэтому агент их не выполняет. Секретные ключи (`sb_secret_…`, service_role, пароль базы) **никому не пересылать**, в чат и в репозиторий не вставлять. Нужны только два публичных значения: адрес проекта и publishable key.

## 1. Проект и таблица (≈3 мин)
1. Supabase → создать проект (или выбрать существующий, если он нужен только для дневника).
2. SQL Editor → вставить целиком `supabase/migrations/001_projection.sql` → Run. Повторно не запускать: скрипт рассчитан на один запуск.
   Интеграцию Supabase с GitHub можно не использовать. Она применяет миграции только при слиянии в production-ветку (`main`), а незавершённую работу туда сливать не нужно.

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
