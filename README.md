# Octane Podcast — ежедневный подкаст-шоу про машины Octane Rent

Приложение раз в день само:
1. берёт следующую **необработанную машину** из sitemap сайта octane.rent,
2. парсит её (название, цена, характеристики, фото) и подтягивает **реальные правила
   аренды** с `octane.rent/policies.json`,
3. пишет **сценарий шоу** «Octane Drive Stories»: ведущие + гость + эксперт Дарья
   (на проверенных фактах) + рубрика + розыгрыш (через бесплатный LLM),
4. **озвучивает** его голосами AWS Polly (4 роли) и склеивает MP3,
5. делает **субтитры (SRT)** и собирает **видео**: заставка + фото машины + вшитые субтитры,
6. **загружает видео на твой YouTube-канал** через YouTube Data API,
7. параллельно (опционально) обновляет **RSS-фид** для YouTube Music / Spotify / Apple.

Своего сервера не нужно. Всё крутится на бесплатном GitHub Actions; из платного — только
AWS Polly (копейки). LLM — бесплатный (OpenRouter), загрузка на YouTube — бесплатная.

> Видео идёт на YouTube через API и **не** хранится в репозитории (чтобы не раздувать его).
> В репозиторий коммитятся только лёгкие MP3 + SRT + фид. RSS-путь можно оставить включённым
> параллельно — тогда аудио-версия попадёт ещё и в YouTube Music/Spotify/Apple.

---

## Привязка YouTube-канала (делается один раз)

Чтобы приложение само заливало видео на твой канал, ему нужен доступ по OAuth. Это
разовая настройка; дальше загрузка идёт автоматически, без твоего участия.

1. **Google Cloud Console** (console.cloud.google.com): создай проект (например `octane-podcast`).
2. **APIs & Services → Library** → найди **YouTube Data API v3** → **Enable**.
3. **APIs & Services → OAuth consent screen**: тип **External**, заполни название/почту,
   в **Test users** добавь свой Google-аккаунт (тот, что владеет каналом
   `UCYpHq90Cf5zVS9-Mmk8eP4Q`). Публиковать приложение не нужно — режима Testing достаточно.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID** →
   тип **Desktop app** → создать → **Download JSON**. Переименуй в `client_secret.json`.
5. На своём компьютере получи refresh-токен (разово):
   ```bash
   pip install google-auth-oauthlib
   python get_youtube_token.py        # client_secret.json должен лежать рядом
   ```
   Откроется браузер — войди аккаунтом, **владеющим каналом**, и разреши доступ.
   Скрипт распечатает три значения.
6. Положи их в **GitHub → Settings → Secrets and variables → Actions → Secrets**:
   `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.
7. В **Variables** поставь `YOUTUBE_ENABLED=true`, `YOUTUBE_PRIVACY=private`
   (сначала private — проверишь пару выпусков, потом переключишь на `public`).

Видео зальётся на тот канал, которым владеет аккаунт из шага 5. Заголовок/описание/теги
и субтитры проставляются автоматически (SEO — на твоей стороне).

> Пока `YOUTUBE_ENABLED=false`, приложение всё равно собирает видео (лежит в `videos/`
> в раннере) — можно проверить результат до подключения канала.

---

## Как это работает (схема)

```
GitHub Actions (cron, раз в день)
        │
        ├─ fetch_car.py     → следующий URL авто из sitemap + парсинг
        ├─ generate_script.py → диалог 2 ведущих (LLM)
        ├─ synthesize.py    → 2 голоса Polly → episodes/YYYY-MM-DD-car.mp3
        ├─ build_feed.py    → обновляет feed.xml
        └─ git commit + деплой на GitHub Pages
        │
        ▼
https://ТВОЙ.github.io/octane-podcast/feed.xml   ← этот URL сабмитишь 1 раз
        │
        ├──► YouTube Music
        ├──► Spotify
        └──► Apple Podcasts
```

---

## Что нужно от тебя (чек-лист доступов)

Собери это — и подкаст поедет. Ничего сложного, всё по ссылкам-инструкциям ниже.

| # | Что | Зачем | Платно? |
|---|-----|-------|---------|
| 1 | **GitHub аккаунт** + новый репозиторий | хостинг кода, запуск по расписанию, хранение MP3, RSS | бесплатно |
| 2 | **AWS аккаунт** → ключ доступа для Polly (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) | озвучка | ~$0 первый год (free tier 5 млн символов/мес), потом ~$16 за 1 млн символов |
| 3 | **Ключ LLM** для сценария: Google **Gemini API key** (рекомендую, есть бесплатный тариф) *или* OpenAI/Anthropic | текст диалога | Gemini free tier — бесплатно |
| 4 | **Обложка подкаста** JPG/PNG, минимум 1400×1400 (лучше 3000×3000) | требование YouTube Music/Apple | — |
| 5 | Доступ к **YouTube Music** (тот же Google-аккаунт бренда) | сабмит RSS-фида | бесплатно |

> Пункт 3 не обязателен для запуска: без LLM-ключа приложение соберёт выпуск по
> встроенному шаблону. Но с LLM подкаст звучит живее — советую подключить Gemini.

---

## Установка (пошагово)

### Шаг 1. Создай репозиторий
Создай на GitHub **приватный или публичный** репозиторий (например `octane-podcast`)
и залей туда все файлы из этой папки.

### Шаг 2. Обложка
Положи обложку подкаста в `assets/cover.jpg` (≥1400×1400). Замени плейсхолдер.

### Шаг 3. AWS Polly (озвучка)
1. Заведи/войди в AWS Console → сервис **IAM** → создай пользователя с правом
   `AmazonPollyReadOnlyAccess`.
2. Создай для него **Access key** → получишь `AWS_ACCESS_KEY_ID` и `AWS_SECRET_ACCESS_KEY`.
3. Регион оставь `us-east-1` (там дешевле и есть все neural-голоса).

### Шаг 4. LLM (сценарий) — опционально, но желательно
Получи **Gemini API key** в Google AI Studio (aistudio.google.com → Get API key).

### Шаг 5. Впиши настройки в GitHub
В репозитории: **Settings → Secrets and variables → Actions**.

**Variables** (вкладка *Variables* — не секретные):
```
PUBLIC_BASE_URL     = https://ТВОЙ-логин.github.io/octane-podcast
PODCAST_TITLE       = Octane Rent — Daily Supercar
PODCAST_AUTHOR      = Octane Rent
PODCAST_EMAIL       = bpe@octaneluxurycarrental.com
PODCAST_DESCRIPTION = Every day one exotic car from Octane Rent...
PODCAST_LANGUAGE    = en
PODCAST_CATEGORY    = Leisure
PODCAST_SITE        = https://octane.rent
SCRIPT_PROVIDER     = gemini
TTS_PROVIDER        = polly
AWS_REGION          = us-east-1
POLLY_VOICE_A       = Matthew
POLLY_VOICE_B       = Joanna
POLLY_ENGINE        = neural
```

**Secrets** (вкладка *Secrets* — приватные ключи):
```
AWS_ACCESS_KEY_ID       = ...
AWS_SECRET_ACCESS_KEY   = ...
GEMINI_API_KEY          = ...   (если используешь Gemini)
```

### Шаг 6. Включи GitHub Pages
**Settings → Pages → Build and deployment → Source = GitHub Actions.**
После первого запуска твои файлы будут доступны по `PUBLIC_BASE_URL`.

### Шаг 7. Первый запуск вручную
Вкладка **Actions → Daily podcast episode → Run workflow**.
Через пару минут в `episodes/` появится первый MP3, а `feed.xml` обновится.
Проверь в браузере: `https://ТВОЙ-логин.github.io/octane-podcast/feed.xml`.

### Шаг 8. Заведи подкаст в YouTube Music (один раз)
Открой **YouTube Music** под аккаунтом бренда → раздел для подкастов →
**добавить существующий подкаст по RSS** → вставь URL фида (`.../feed.xml`) →
подтверди владение (код придёт на `PODCAST_EMAIL`).
Дальше каждый новый выпуск появляется автоматически.
(Тем же фидом можно завести подкаст в Spotify for Podcasters и Apple Podcasts.)

---

## Локальный запуск / тест

```bash
pip install -r requirements.txt        # нужен ffmpeg в системе
cp .env.example .env                    # впиши ключи
python -m src.main                      # сделает 1 выпуск
```

Без ключей LLM выпуск соберётся по шаблону. Для реального Polly нужны AWS-ключи.

---

## Расписание

Время запуска — в `.github/workflows/daily.yml`, строка `cron: "0 7 * * *"`
(07:00 UTC = 10:00 Дубай/Минск). Поменяй под себя.

---

## Настройки под себя

- **Голоса.** `POLLY_VOICE_A` / `POLLY_VOICE_B` — любые neural-голоса Polly
  (Matthew, Joanna, Stephen, Ruth, Danielle…). Так делается «два ведущих».
- **Язык.** Сейчас английский. Для другого языка поменяй голоса Polly,
  `PODCAST_LANGUAGE` и промпт в `generate_script.py`.
- **Сколько выпусков за раз.** `CARS_PER_RUN` (по умолчанию 1).
- **Какие URL считать машинами.** Регэксп `CAR_URL_PATTERN` в `.env`.
- **Заставка.** Положи `assets/intro.mp3` — первые 4 сек подмешаются в начало.
- **Запасной TTS.** `TTS_PROVIDER=ttsmp3` + `TTSMP3_API_KEY` (нужен платный ключ ttsmp3).

---

## Ограничения и на что заложиться

- **Хранение MP3.** Пока лежат в самом репозитории (ок на сотни выпусков).
  Когда накопится много — вынесем на S3/Cloudflare R2, поменяв только `PUBLIC_BASE_URL`
  и место заливки. Код к этому готов.
- **Живой доступ к octane.rent.** Парсер работает по публичным страницам и sitemap;
  если вёрстка карточек сильно поменяется — подправим селекторы в `fetch_car.py`.
- **Модерация YouTube Music.** Первый подкаст проходит проверку владения по email —
  это разовая процедура.

---

## Структура

```
octane-podcast/
├─ src/
│  ├─ config.py          # настройки из .env / переменных окружения
│  ├─ state.py           # какие машины уже обработаны + список эпизодов
│  ├─ fetch_car.py       # выбор машины из sitemap + парсинг
│  ├─ generate_script.py # сценарий диалога (Gemini/OpenAI/Anthropic/шаблон)
│  ├─ synthesize.py      # Polly/ttsmp3 → склейка MP3
│  ├─ build_feed.py      # RSS-фид подкаста
│  └─ main.py            # оркестратор (1 запуск = 1 выпуск)
├─ episodes/             # сгенерированные MP3 (отдаёт GitHub Pages)
├─ assets/cover.jpg      # обложка подкаста (положи свою)
├─ feed.xml              # RSS-фид (сабмитишь в YouTube Music)
├─ state.json            # прогресс
├─ .github/workflows/daily.yml  # ежедневный запуск
├─ requirements.txt
└─ .env.example
```
