"""Формат шоу «Car Service Podcast» (Golden Horse) и вся промпт-логика.

Каждый выпуск — эпизод-ОТЗЫВ об опыте КОНКРЕТНОЙ услуги автосервиса (ремонт/обслуживание):
ведущие + гость (как записался, как прошло, результат, сервис) + короткий блок эксперта
Golden Horse с полезным советом. Выпуски разные за счёт ротации истории гостя, самого гостя,
темы эксперта и рубрики.

Честность:
  - Гость — ИЛЛЮСТРАТИВНЫЙ персонаж бренда, не выдаётся за реального проверенного клиента.
  - Эксперт/ведущие опираются ТОЛЬКО на факты из knowledge.py + конкретику со страницы услуги;
    цену называют лишь если она есть на странице этой услуги.
  - Не называем шоу «прямым эфиром» — предзаписано.
"""

HOST_A = "Alex"            # ведущий (муж.)
HOST_B = "Sam"             # ведущая (жен.)
EXPERT = "Omar"            # эксперт Golden Horse (советы по авто)

SHOW_NAME = "Car Service Podcast"

# --- Базовые правила шоу (в каждом выпуске) ---
BASE_RULES = f"""You write ONE episode of the audio podcast "{SHOW_NAME}" by Golden Horse
(golden-horse.ae) — a car service / auto repair & maintenance workshop in Dubai (Al Quoz 3).
Audio only. English. Aim for 1000-1400 words total, but as a LIVELY, fast back-and-forth chat.

Recurring cast:
- {HOST_A}: male host, warm and energetic, keeps the show moving.
- {HOST_B}: female host, sharp and curious, asks the good questions.
- {EXPERT}: Golden Horse's service expert. Appears for a short expert segment with ONE genuinely
  useful tip about TODAY'S service. He NEVER invents prices, durations, parts or guarantees.
  PRICE RULE: he may state a price ONLY if the input 'Price (AED)' field (from this service's own
  page) has one. The general price examples in the FACTS block are background ONLY — never quote
  them as this service's price (e.g. do NOT say "oil change from AED 200" in a brake-repair
  episode). If this service has no price, don't mention numbers — say it depends on the car.

Episode flow (keep this order, keep it natural, not robotic):
1) Cold open + hosts introduce today's SERVICE and welcome the guest.
2) GUEST STORY — the heart of the episode, but told as a REAL CONVERSATION, not a monologue:
   the guest got THIS service done at Golden Horse. Across many short turns, with the hosts
   reacting and asking follow-ups, cover concretely:
   - why they came in (the symptom/need) and how they booked;
   - arriving at the Al Quoz workshop: how it looked, how professional;
   - the diagnosis and the WORK — what was done, roughly how long;
   - the RESULT — how the car runs/feels now;
   - the SERVICE — how clearly the team explained things, trust, no surprises;
   - genuine emotion — whether it was worth it.
3) EXPERT SEGMENT with {EXPERT}: one short, genuinely useful car-care/maintenance tip, using
   ONLY the FACTS and the service page details.
4) SEGMENT: the short recurring rubric given in the input.
5) (If GIVEAWAY is enabled) the giveaway announcement with its real mechanics.
6) Warm outro + one soft booking nudge to golden-horse.ae (Dubai).

Style — make it sound like a REAL conversation, not a script being read:
- NO line is longer than 2 sentences; many lines are just a few words ("Wait, really?",
  "How long did that take?", "No surprises?", "Exactly.").
- The guest has NO monologues — their story is broken into short turns with the hosts jumping in,
  reacting, finishing thoughts, light friendly interruptions and overlaps.
- Natural and chatty: contractions, little reactions ("honestly", "oh nice", "makes sense").
- Keep concrete specifics (the workshop, the diagnosis, the fix) but spread across the chat.
- Still stay honest (see rules below).

Honesty rules (strict):
- The guest is an ILLUSTRATIVE brand character, NOT a verified named customer review. Authentic
  and positive, but never fabricate proof, star ratings or "verified customer".
- Never invent durations, parts, warranties or results.
- PRICES: quote a price ONLY if the input 'Price (AED)' field for THIS service has one, tied to
  this service. Never present the general price examples from FACTS as this service's price, and
  never label a number "verified".
- Never call the show or the giveaway "live" — it is pre-recorded. One booking nudge total.

Return STRICT JSON only (no markdown fences), shape:
{{
  "youtube_title": "ENGLISH review headline, <=100 chars, EXACTLY: 'Review of {{Service}} at Golden Horse {{City}}' (if city unknown: 'Review of {{Service}} at Golden Horse'). {{Service}} = the input 'Service (clean name)' field, {{City}} = the input 'City' field. Show's experience format — NOT a verified review by a specific real named customer.",
  "episode_title": "short episode title with the service name",
  "episode_description": "EXACTLY this one line: 'Car Service Podcast: a guest's experience with {{Service}} at Golden Horse in {{City}}: {{service_url}}' where {{service_url}} is the full 'Service page' URL. No price, no extra sentences — the link must stay visible.",
  "lines": [{{"speaker": "A|B|G|E", "text": "..."}}]
}}
Speakers: A={HOST_A}, B={HOST_B}, G=guest, E={EXPERT} (expert). Alternate naturally and often;
NO line longer than 2 sentences (many just a few words). Prefer MANY short turns over few long ones."""


# --- Истории подачи гостя (флейвор рассказа) ---
STORY_ANGLES = [
    {"key": "warning-light", "name": "Warning light",
     "prompt": "Guest story flavor: a warning light / odd noise came up and they finally brought "
               "the car in to get it diagnosed and fixed."},
    {"key": "overdue-service", "name": "Overdue service",
     "prompt": "Guest story flavor: a long-overdue service/maintenance they kept putting off, and "
               "the relief once it was sorted properly."},
    {"key": "second-opinion", "name": "Second opinion",
     "prompt": "Guest story flavor: a guest who wanted an honest second opinion after another "
               "garage, and how the diagnosis went here."},
    {"key": "pre-trip", "name": "Before a road trip",
     "prompt": "Guest story flavor: getting the car checked/serviced before a long drive or summer, "
               "wanting peace of mind."},
    {"key": "luxury-care", "name": "Luxury car owner",
     "prompt": "Guest story flavor: a luxury-car owner who was picky about who touches their car "
               "and was reassured by the expertise."},
    {"key": "used-car", "name": "Pre-purchase check",
     "prompt": "Guest story flavor: a pre-purchase inspection before buying a used car, and what "
               "the check revealed."},
    {"key": "breakdown", "name": "Sudden issue",
     "prompt": "Guest story flavor: a sudden issue (AC died in summer, brakes felt off) handled "
               "quickly and professionally."},
]

# --- Гости (ротация: разные нации, соло/пары). Персона — иллюстративная. ---
GUESTS = [
    {"key": "uk-solo", "seed": "a British expat in Dubai, dry humour"},
    {"key": "german-couple", "seed": "a German driver, precise and detail-loving"},
    {"key": "indian-pro", "seed": "an Indian professional, warm and expressive"},
    {"key": "saudi-local", "seed": "a Saudi visitor who knows cars, relaxed and proud"},
    {"key": "american-creator", "seed": "an American content creator, upbeat and visual"},
    {"key": "french-couple", "seed": "a French driver, stylish and particular"},
    {"key": "russian-expat", "seed": "a Russian-speaking expat living in Dubai, cool and candid"},
    {"key": "nigerian-solo", "seed": "a Nigerian entrepreneur, curious and joyful"},
    {"key": "filipino-pro", "seed": "a Filipino professional, friendly and practical"},
    {"key": "emirati-local", "seed": "an Emirati local car enthusiast, generous host energy"},
]

# --- Темы экспертного блока (Omar) — каждая опирается на FACTS/страницу услуги ---
EXPERT_TOPICS = [
    {"key": "oil-interval", "q": "How often should I really change my oil in the UAE heat?"},
    {"key": "ac-summer", "q": "How do I keep my car's AC healthy through Dubai summer?"},
    {"key": "brakes-signs", "q": "What are the early signs my brakes need attention?"},
    {"key": "warning-lights", "q": "Which dashboard warning lights should I never ignore?"},
    {"key": "battery-heat", "q": "Why do car batteries fail so fast here, and what helps?"},
    {"key": "suspension", "q": "How do Dubai roads and speed bumps affect my suspension?"},
    {"key": "pre-purchase", "q": "What does a proper pre-purchase inspection actually check?"},
    {"key": "maintenance-plan", "q": "What basic maintenance keeps a car reliable long-term?"},
]

# --- Рубрики (короткий повторяющийся блок) ---
SEGMENTS = [
    {"key": "care-lifehack", "name": "Car-care life-hack",
     "prompt": "Short rubric 'Car-care life-hack': one genuinely useful, FACTS-consistent "
               "maintenance tip for UAE drivers."},
    {"key": "warning-sign", "name": "Warning sign of the week",
     "prompt": "Short rubric 'Warning sign of the week': hosts name one symptom drivers shouldn't "
               "ignore and why."},
    {"key": "myth-busting", "name": "Myth busting",
     "prompt": "Short rubric 'Myth busting': hosts bust one common car-maintenance myth, staying "
               "consistent with the FACTS."},
    {"key": "service-duel", "name": "Service duel",
     "prompt": "Short rubric 'Service duel': hosts playfully debate 'fix now vs wait' for a common "
               "car issue."},
]

# --- Розыгрыш (реальная механика; НЕ «прямой эфир») ---
GIVEAWAY = {
    "every_n_episodes": 3,   # анонс каждые N выпусков
    "prize": "a free car health check at Golden Horse",
    "how_to_enter": "subscribe to the channel and leave a comment with your car",
    "prompt": (
        "GIVEAWAY block: announce an ongoing Golden Horse giveaway. Prize: {prize}. To enter: {how}. "
        "State clearly it's easy and free to enter and the winner is announced in a future episode "
        "and on Golden Horse's social channels. Do NOT say 'live' or 'right now on air'. Keep it short."
    ),
}


def plan_episode(index):
    """Детерминированно собирает состав выпуска по его номеру — соседние выпуски разные."""
    story = STORY_ANGLES[index % len(STORY_ANGLES)]
    guest = GUESTS[index % len(GUESTS)]
    topic = EXPERT_TOPICS[index % len(EXPERT_TOPICS)]
    segment = SEGMENTS[index % len(SEGMENTS)]
    giveaway = (index % GIVEAWAY["every_n_episodes"]) == 0
    return {
        "index": index,
        "story": story,
        "guest": guest,
        "expert_topic": topic,
        "segment": segment,
        "giveaway": giveaway,
    }


def build_system_prompt(plan):
    parts = [BASE_RULES, "", "This episode's setup:",
             f"- {plan['story']['prompt']}",
             f"- Guest persona (illustrative): {plan['guest']['seed']}.",
             f"- Expert question for {EXPERT}: \"{plan['expert_topic']['q']}\" (answer ONLY from FACTS).",
             f"- {plan['segment']['prompt']}"]
    if plan["giveaway"]:
        parts.append("- " + GIVEAWAY["prompt"].format(prize=GIVEAWAY["prize"], how=GIVEAWAY["how_to_enter"]))
    else:
        parts.append("- No giveaway this episode.")
    return "\n".join(parts)
