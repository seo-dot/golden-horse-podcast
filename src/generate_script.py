"""Генерация сценария подкаста (диалог двух ведущих) + SEO-заголовок и описание.

Провайдеры LLM: groq (бесплатно, по умолчанию), openai, anthropic, gemini.
Каждый выпуск использует один "угол подачи" из src/angles.py — приложение чередует
их по порядковому номеру эпизода, поэтому выпуски получаются РАЗНЫМИ.

Если провайдер = none или нет ключа — используется офлайн-шаблон (fallback),
чтобы пайплайн работал даже без LLM.
"""
import json
import re
from . import config, angles, knowledge


def _city_or_none(car):
    """Город услуги. На golden-horse.ae город — всегда Дубай (в URL не указан)."""
    hay = f"{car.get('url', '')} {car.get('title', '')}".lower()
    if "abu-dhabi" in hay or "abu dhabi" in hay:
        return "Abu Dhabi"
    if "/services/" in hay or "dubai" in hay:
        return "Dubai"
    return None


def _city_of(car):
    """Как _city_or_none, но с дефолтом 'the UAE' (для текста промпта)."""
    return _city_or_none(car) or "the UAE"


def clean_car_name(title):
    """Чистое имя услуги: 'Car Bumper Repair in Dubai' -> 'Car Bumper Repair',
    'Oil Change ... Price from 200 AED - Golden Horse ...' -> 'Oil Change ...'."""
    name = title or ""
    name = name.replace("​", "").replace("‎", "")                       # невидимые символы
    name = re.sub(r"\s+at\s+Golden\s+Horse.*$", "", name, flags=re.IGNORECASE)    # '... at Golden Horse'
    name = re.sub(r"\s+Price\s+from\b.*$", "", name, flags=re.IGNORECASE)         # '... Price from N AED'
    name = re.sub(r"\s*\|.*$", "", name)                                          # хвост сайта после '|'
    name = re.sub(r"\s+-\s+.*$", "", name)                                        # SEO-хвост после ' - '
    name = re.sub(r"\s+in\s+Dubai\s*$", "", name, flags=re.IGNORECASE)            # '... in Dubai'
    name = re.sub(r"\s+Dubai\s*$", "", name, flags=re.IGNORECASE)                 # хвост-город без 'in'
    return name.strip() or (title or "this service")


# обратная совместимость
_clean_car_name = clean_car_name


def review_title(car):
    """Детерминированный заголовок-отзыв (<=100 симв.):
    'Review of {Service} at Golden Horse {City}'
    (без города — 'Review of {Service} at Golden Horse')."""
    service = clean_car_name(car.get("title", ""))
    city = _city_or_none(car)
    if city:
        t = f"Review of {service} at Golden Horse {city}"
    else:
        t = f"Review of {service} at Golden Horse"
    return t[:100]


def episode_description(car):
    """Детерминированное короткое описание, заканчивающееся ПОЛНОЙ ссылкой на услугу."""
    service = clean_car_name(car.get("title", ""))
    city = _city_of(car)
    service_url = car.get("url", "https://golden-horse.ae")
    return (f"Car Service Podcast: a guest's experience with {service} at Golden Horse "
            f"in {city}: {service_url}")


def _build_user_prompt(car, facts):
    return (
        f"Service page: {car['url']}\n"
        f"Service name: {car['title']}\n"
        f"Service (clean name): {_clean_car_name(car['title'])}\n"
        f"City: {_city_of(car)}\n"
        f"Price (AED): {car.get('price') or 'not specified'}\n"
        f"Page description: {car.get('description') or ''}\n\n"
        f"{facts}\n"
    )


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


# ---------- Провайдеры ----------

def _gen_openai_compatible(system, user, api_key, base_url, model):
    """Groq и OpenAI используют один и тот же клиент (OpenAI-совместимый API)."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,  # выше -> заметнее вариативность между выпусками
    )
    try:
        kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
    except Exception:
        kwargs.pop("response_format", None)
        resp = client.chat.completions.create(**kwargs)
    return _extract_json(resp.choices[0].message.content)


def _gen_openrouter(system, user):
    """OpenRouter: пробуем основную модель, при ошибке (429/недоступна) — запасные по очереди.
    Возвращает (data, model). Если все модели не ответили — бросает последнее исключение."""
    models = [config.OPENROUTER_MODEL] + list(config.OPENROUTER_FALLBACK_MODELS)
    last_err = None
    for model in models:
        if not model:
            continue
        try:
            data = _gen_openai_compatible(system, user, config.OPENROUTER_API_KEY,
                                          config.OPENROUTER_BASE_URL, model)
            print(f"[script] OpenRouter: сценарий сгенерён моделью {model}")
            return data, model
        except Exception as e:
            last_err = e
            print(f"[script] модель {model} не ответила ({e}); пробую следующую…")
    raise last_err if last_err else RuntimeError("нет доступных моделей OpenRouter")


def _gen_anthropic(system, user):
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=2000,
        temperature=0.9,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _extract_json(resp.content[0].text)


def _gen_gemini(system, user):
    import google.generativeai as genai
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(system + "\n\n" + user)
    return _extract_json(resp.text)


VALID_SPEAKERS = {"A", "B", "G", "E"}


def _gen_fallback(car, plan):
    """Офлайн-шаблон без LLM: эпизод-отзыв об услуге автосервиса + эксперт + рубрика.
    Короткие реплики, разговорный тон."""
    service = clean_car_name(car["title"])
    city = _city_of(car)
    price = car.get("price") or ""
    guest = plan["guest"]["seed"]
    lines = [
        ("A", f"Welcome back to the Car Service Podcast. Today — {service} at Golden Horse in {city}."),
        ("B", "And our guest just had it done. Hey!"),
        ("G", f"Hey! {guest.split(',')[0]} here."),
        ("G", f"I booked {service} and honestly? Really smooth."),
        ("A", "How was booking?"),
        ("G", "Easy. Called, got a slot the same week."),
        ("B", "Wait, same week? Nice."),
        ("G", "Yeah. The workshop in Al Quoz was clean and organised."),
        ("A", "And the work itself?"),
        ("G", "They diagnosed it properly and explained everything first."),
        ("G", "No surprises. The car drives great now."),
        ("B", f"Omar, quick one — {plan['expert_topic']['q']}"),
        ("E", "Good question. Golden Horse is an all-makes workshop in Al Quoz, Dubai, "
              "including luxury brands."),
        ("E", "Exact pricing and timing depend on the car and the specific service."),
    ]
    if price:
        lines.append(("A", f"On this one it starts around {price}."))
    lines += [
        ("B", f"Quick rubric — {plan['segment']['name']}."),
    ]
    if plan["giveaway"]:
        lines.append(("A", "Before we go — giveaway's on: subscribe and comment your car to enter. "
                           "Winner announced in a future episode."))
    lines += [
        ("B", f"That's {service} at Golden Horse. Book yours in Dubai at golden dash horse dot a e."),
        ("A", "See you next time."),
    ]
    return {
        "youtube_title": review_title(car),
        "episode_title": f"{service} — {plan['story']['name']}",
        "episode_description": episode_description(car),
        "lines": [{"speaker": s, "text": t} for s, t in lines],
    }


def generate(car, episode_index=0):
    """episode_index — номер выпуска: определяет состав (гость, эксперт, рубрика, розыгрыш)."""
    plan = angles.plan_episode(episode_index)
    facts = knowledge.facts_text()
    system = angles.build_system_prompt(plan)
    user = _build_user_prompt(car, facts)
    provider = config.SCRIPT_PROVIDER

    try:
        if provider == "openrouter" and config.OPENROUTER_API_KEY:
            data, _ = _gen_openrouter(system, user)
        elif provider == "groq" and config.GROQ_API_KEY:
            data = _gen_openai_compatible(system, user, config.GROQ_API_KEY,
                                          config.GROQ_BASE_URL, config.GROQ_MODEL)
        elif provider == "openai" and config.OPENAI_API_KEY:
            data = _gen_openai_compatible(system, user, config.OPENAI_API_KEY, None, "gpt-4o-mini")
        elif provider == "anthropic" and config.ANTHROPIC_API_KEY:
            data = _gen_anthropic(system, user)
        elif provider == "gemini" and config.GEMINI_API_KEY:
            data = _gen_gemini(system, user)
        else:
            print(f"[script] провайдер '{provider}' недоступен/без ключа — шаблон.")
            data = _gen_fallback(car, plan)
    except Exception as e:
        print(f"[script] ошибка LLM ({e}); шаблон.")
        data = _gen_fallback(car, plan)

    # Валидация/нормализация
    if not data.get("lines"):
        data = _gen_fallback(car, plan)
    for ln in data["lines"]:
        sp = str(ln.get("speaker", "A")).upper().strip()[:1]
        ln["speaker"] = sp if sp in VALID_SPEAKERS else "A"
        ln["text"] = str(ln.get("text", "")).strip()
    data["lines"] = [ln for ln in data["lines"] if ln["text"]]
    # Заголовок и описание строим ДЕТЕРМИНИРОВАННО в коде (не полагаемся на LLM),
    # чтобы гарантировать строгий формат и полную ссылку на страницу авто.
    data["youtube_title"] = review_title(car)
    data["episode_description"] = episode_description(car)
    data.setdefault("episode_title", car["title"])
    data["angle"] = plan["story"]["key"]
    data["plan"] = {
        "story": plan["story"]["key"], "guest": plan["guest"]["key"],
        "expert_topic": plan["expert_topic"]["key"], "segment": plan["segment"]["key"],
        "giveaway": plan["giveaway"],
    }
    return data


if __name__ == "__main__":
    demo = {"url": "https://octane.rent/sports-cars/lamborghini-huracan-for-rent-dubai/",
            "title": "Lamborghini Huracan", "price": "2500 AED",
            "spec_text": "engine V10 | 640 hp | 0-100 3.2s", "description": ""}
    for i in range(3):
        out = generate(demo, episode_index=i)
        print(f"\n=== эпизод {i} ===", out["plan"])
        print(out["youtube_title"])
