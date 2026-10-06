"""Забор следующей необработанной услуги из sitemap и парсинг её страницы (Desert Diamond)."""
import re
import requests
from bs4 import BeautifulSoup
from . import config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CarServicePodcastBot/1.0; +https://golden-horse.ae)"
}
TIMEOUT = 30

# Берём только под-sitemap услуг; блог/страницы/авторов/бренд-каталог — пропускаем.
# (бренд-услуги вида /services/audi/audi-oil-change/ лежат в этом же service-sitemap.xml)
SERVICE_SITEMAPS = ("service-sitemap.xml",)


def _get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def _urls_from_sitemap(xml):
    """Достаёт <loc> из sitemap (индекса или обычного)."""
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def collect_car_urls():
    """Собирает все URL-кандидаты страниц авто из всех под-sitemap'ов."""
    index_xml = _get(config.SITEMAP_INDEX)
    locs = _urls_from_sitemap(index_xml)

    sub_sitemaps = [u for u in locs if u.endswith(".xml")]
    if not sub_sitemaps:
        # Индекс оказался обычным sitemap'ом
        sub_sitemaps = [config.SITEMAP_INDEX]

    pattern = re.compile(config.CAR_URL_PATTERN, re.IGNORECASE)
    car_urls = []
    seen = set()
    for sm in sub_sitemaps:
        # только под-sitemap'ы услуг
        if not any(sm.endswith(name) for name in SERVICE_SITEMAPS):
            continue
        try:
            xml = _get(sm)
        except Exception as e:
            print(f"[fetch] пропускаю {sm}: {e}")
            continue
        for u in _urls_from_sitemap(xml):
            if u.endswith(".xml"):
                continue
            if pattern.search(u) and u not in seen:
                # только English-версия (без /ru/ и /ar/ языковых префиксов)
                if re.search(r"/(ru|ar)/", u):
                    continue
                seen.add(u)
                car_urls.append(u)
    return _order_by_city_priority(car_urls)


def _city_rank(url):
    """Индекс города URL в CITY_PRIORITY. На car-care.center страницы Абу-Даби содержат
    '/abu-dhabi/', а страницы Дубая город в URL НЕ указывают — поэтому «город не найден»
    трактуем как Дубай (первый в приоритете)."""
    low = url.lower()
    for i, city in enumerate(config.CITY_PRIORITY):
        # учитываем и 'abu-dhabi', и 'abu dhabi'
        if city in low or city.replace("-", " ") in low:
            return i
    # по умолчанию — Дубай (его позиция в списке, иначе 0)
    return config.CITY_PRIORITY.index("dubai") if "dubai" in config.CITY_PRIORITY else 0


def _brand_rank(url):
    """Индекс марки URL в BRAND_PRIORITY; не найденная марка идёт после премиум-марок."""
    low = url.lower()
    for i, brand in enumerate(config.BRAND_PRIORITY):
        if brand in low or brand.replace("-", " ") in low:
            return i
    return len(config.BRAND_PRIORITY)


def _order_by_city_priority(urls):
    """Стабильная двухуровневая сортировка: сначала город (Дубай первым),
    затем внутри города — марка (премиум первыми). Внутри одинаковых (город, марка)
    сохраняется исходный порядок карты сайта (sorted стабилен)."""
    return sorted(urls, key=lambda u: (_city_rank(u), _brand_rank(u)))


def pick_next_url(state):
    """Возвращает следующий необработанный URL авто (с учётом приоритета городов), либо None."""
    urls = collect_car_urls()
    processed = state.get("processed_urls", [])
    for u in urls:
        if u not in processed:
            return u
    return None


def _text(el):
    return el.get_text(" ", strip=True) if el else ""


def parse_car(url):
    """Парсит страницу услуги. Возвращает dict с полями для сценария."""
    html = _get(url)
    soup = BeautifulSoup(html, "lxml")

    # Название услуги
    title = ""
    if soup.find("h1"):
        title = _text(soup.find("h1"))
    if not title and soup.find("meta", property="og:title"):
        title = soup.find("meta", property="og:title").get("content", "")
    if not title and soup.title:
        title = _text(soup.title)
    title = title.replace("​", "").replace("‎", "")  # убрать невидимые символы
    title = re.sub(r"\s*\|.*$", "", title).strip()  # убрать хвост сайта после '|'

    # Описание
    description = ""
    md = soup.find("meta", attrs={"name": "description"})
    if md:
        description = md.get("content", "")
    if not description:
        ogd = soup.find("meta", property="og:description")
        if ogd:
            description = ogd.get("content", "")

    # Цена (ищем AED; у многих услуг её нет — это нормально)
    price = ""
    body_text = soup.get_text(" ", strip=True)
    m = (re.search(r"(\d[\d\s,]*)\s*AED", body_text)
         or re.search(r"AED\s*(\d[\d\s,]*)", body_text))
    if m:
        price = m.group(0).strip()

    # Главное фото
    image = ""
    ogi = soup.find("meta", property="og:image")
    if ogi:
        image = ogi.get("content", "")

    return {
        "url": url,
        "title": title or "Car detailing service",
        "description": description,
        "price": price,
        "specs": {},        # у услуг нет авто-характеристик
        "spec_text": "",
        "image": image,
        "raw_excerpt": body_text[:1500],
    }


if __name__ == "__main__":
    # Быстрый ручной тест
    from . import state as st
    s = st.load()
    url = pick_next_url(s)
    print("Следующий URL:", url)
    if url:
        car = parse_car(url)
        for k, v in car.items():
            if k != "raw_excerpt":
                print(f"  {k}: {v}")
