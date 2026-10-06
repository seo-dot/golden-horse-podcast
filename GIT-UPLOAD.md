# ТЗ для Claude Code — залить проект в GitHub

Задача: загрузить содержимое этой папки в репозиторий пользователя и запушить в ветку `main`.

**Репозиторий:** `https://github.com/seo-dot/octane-podcast.git`

## Что сделать

1. Убедись, что находишься в корне проекта (там, где `README.md`, `TASK.md`, папка `src/`).
2. Проверь, что git-аутентификация настроена. Если нет — подскажи пользователю выполнить
   `gh auth login` (GitHub CLI) или настроить credential manager. Не продолжай пуш без auth.
3. **Безопасность (критично):** перед коммитом убедись, что в индекс НЕ попадают секреты.
   В репозиторий не должны уйти: `.env`, `client_secret.json`, папки `videos/`, `tmp/`,
   любые файлы с ключами/токенами. Они уже перечислены в `.gitignore` — проверь, что он на месте
   и работает (`git status` не должен показывать эти файлы). Если увидишь `.env` или
   `client_secret.json` в списке на коммит — останови и убери их из индекса.
4. Инициализируй и запушь:
   ```bash
   git init
   git add .
   git status                     # ПРОВЕРЬ: нет .env, client_secret.json, videos/, tmp/
   git commit -m "Octane Drive Stories: automated daily car podcast/video pipeline"
   git branch -M main
   git remote add origin https://github.com/seo-dot/octane-podcast.git
   git push -u origin main
   ```
   Если репозиторий уже не пустой и пуш отклонён — сделай `git pull --rebase origin main`,
   реши конфликты и запушь снова (или, если пользователь подтвердит, что репо пустое и можно
   перезаписать, — согласуй `--force`). Не форси без подтверждения пользователя.
5. После пуша выведи ссылку на репозиторий и краткий отчёт: что загружено, что осталось
   сделать пользователю вручную (это НЕ делается через git):
   - **Settings → Secrets and variables → Actions** — добавить Secrets и Variables
     (ключи OpenRouter/AWS/YouTube и настройки; список — в `README.md`).
   - **Settings → Pages → Source = GitHub Actions** — включить, если нужен RSS/аудио-путь.
   - Запустить **Actions → Daily podcast episode → Run workflow** для проверки.

## Ограничения

- Не коммить секреты и большие видео. Не меняй код проекта — задача только залить.
- Если `git push` требует токен/логин, которого нет, — не пытайся обойти, а сообщи
  пользователю, что нужно авторизоваться, и остановись.
- Все настройки (какие Secrets/Variables нужны) уже описаны в `README.md` — сошлись на него.
