"""Загрузка конфигурации из .env / переменных окружения."""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(key, default=""):
    v = os.environ.get(key)
    if v is None or v.strip() == "":
        return default
    return v.strip()


# Публикация
PUBLIC_BASE_URL = _get("PUBLIC_BASE_URL").rstrip("/")

# Метаданные подкаста
PODCAST_TITLE = _get("PODCAST_TITLE", "Car Service Podcast")
PODCAST_AUTHOR = _get("PODCAST_AUTHOR", "Golden Horse")
PODCAST_EMAIL = _get("PODCAST_EMAIL", "seo@mbear.ae")
PODCAST_DESCRIPTION = _get(
    "PODCAST_DESCRIPTION",
    "Car Service Podcast — real customer experiences at Golden Horse Car Service in Dubai: "
    "engine, AC, brakes, suspension, transmission, bodywork, detailing and more, all makes "
    "incl. luxury. Book at https://golden-horse.ae",
)
PODCAST_LANGUAGE = _get("PODCAST_LANGUAGE", "en")
PODCAST_CATEGORY = _get("PODCAST_CATEGORY", "Leisure")
PODCAST_SITE = _get("PODCAST_SITE", "https://golden-horse.ae")

# LLM
SCRIPT_PROVIDER = _get("SCRIPT_PROVIDER", "openrouter").lower()
GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = _get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = _get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _get("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
OPENROUTER_BASE_URL = _get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
# Запасные бесплатные модели (через запятую): пробуем по очереди при 429/ошибке основной.
OPENROUTER_FALLBACK_MODELS = [
    m.strip() for m in _get(
        "OPENROUTER_FALLBACK_MODELS",
        "nvidia/nemotron-3-super-120b-a12b:free,z-ai/glm-5.2:free",
    ).split(",") if m.strip()
]
GEMINI_API_KEY = _get("GEMINI_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")

# TTS
TTS_PROVIDER = _get("TTS_PROVIDER", "polly").lower()
AWS_ACCESS_KEY_ID = _get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = _get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = _get("AWS_REGION", "us-east-1")
# Голоса по ролям: A=ведущий, B=ведущая, G=гость, E=эксперт (Дарья)
POLLY_VOICE_A = _get("POLLY_VOICE_A", "Matthew")   # host male (US)
POLLY_VOICE_B = _get("POLLY_VOICE_B", "Joanna")    # host female (US)
POLLY_VOICE_G = _get("POLLY_VOICE_G", "Brian")     # guest — можно менять акцент (Brian=UK)
POLLY_VOICE_E = _get("POLLY_VOICE_E", "Ruth")      # expert Daria (US female)
POLLY_ENGINE = _get("POLLY_ENGINE", "neural")
TTSMP3_API_KEY = _get("TTSMP3_API_KEY")
TTSMP3_VOICE_A = _get("TTSMP3_VOICE_A", "Matthew")
TTSMP3_VOICE_B = _get("TTSMP3_VOICE_B", "Joanna")
TTSMP3_VOICE_G = _get("TTSMP3_VOICE_G", "Brian")
TTSMP3_VOICE_E = _get("TTSMP3_VOICE_E", "Ruth")

# gTTS (бесплатный тестовый провайдер, без ключа): 4 "голоса" имитируем
# разными акцентами (tld) + лёгким сдвигом высоты в synthesize.py.
GTTS_LANG = _get("GTTS_LANG", "en")
GTTS_TLD_A = _get("GTTS_TLD_A", "us")       # ведущий
GTTS_TLD_B = _get("GTTS_TLD_B", "co.uk")    # ведущая
GTTS_TLD_G = _get("GTTS_TLD_G", "com.au")   # гость
GTTS_TLD_E = _get("GTTS_TLD_E", "ca")       # эксперт

# Видео
VIDEO_ENABLED = _get("VIDEO_ENABLED", "true").lower() in ("1", "true", "yes")
INTRO_SECONDS = int(_get("INTRO_SECONDS", "3") or "3")

# YouTube upload
YOUTUBE_ENABLED = _get("YOUTUBE_ENABLED", "false").lower() in ("1", "true", "yes")
YOUTUBE_CLIENT_ID = _get("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = _get("YOUTUBE_CLIENT_SECRET")
YOUTUBE_REFRESH_TOKEN = _get("YOUTUBE_REFRESH_TOKEN")
YOUTUBE_PRIVACY = _get("YOUTUBE_PRIVACY", "private")  # private | unlisted | public
YOUTUBE_CATEGORY_ID = _get("YOUTUBE_CATEGORY_ID", "2")  # 2 = Autos & Vehicles
YOUTUBE_UPLOAD_CAPTIONS = _get("YOUTUBE_UPLOAD_CAPTIONS", "true").lower() in ("1", "true", "yes")

# RSS для YouTube Music (можно оставить включённым параллельно с видео)
RSS_ENABLED = _get("RSS_ENABLED", "true").lower() in ("1", "true", "yes")

# Город один (Dubai). URL услуг golden-horse.ae город в пути не указывают.
CITY_PRIORITY = [
    c.strip().lower()
    for c in _get("CITY_PRIORITY", "dubai").split(",")
    if c.strip()
]

# Приоритет марок для golden-horse не нужен — оставляем пустым.
BRAND_PRIORITY = [
    b.strip().lower()
    for b in _get("BRAND_PRIORITY", "").split(",")
    if b.strip()
]

# Прочее
CARS_PER_RUN = int(_get("CARS_PER_RUN", "1") or "1")
# Одиночная страница услуги на golden-horse.ae содержит '/services/'.
CAR_URL_PATTERN = _get("CAR_URL_PATTERN", r"/services/")

# sitemap.xml на golden-horse.ae 301-редиректит на sitemap_index.xml.
SITEMAP_INDEX = f"{PODCAST_SITE}/sitemap_index.xml"

# Пути (относительно корня репозитория)
import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
EPISODES_DIR = ROOT / "episodes"      # аудио MP3
VIDEOS_DIR = ROOT / "videos"          # видео MP4 для YouTube
TMP_DIR = ROOT / "tmp"
FEED_PATH = ROOT / "feed.xml"
STATE_PATH = ROOT / "state.json"
ASSETS_DIR = ROOT / "assets"
COVER_PATH = ASSETS_DIR / "cover.jpg"  # обложка подкаста 1400x1400+ (положи свою)
