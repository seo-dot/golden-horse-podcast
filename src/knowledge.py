"""Проверенные факты о Golden Horse — «источник правды» для экспертного блока.

Машиночитаемого JSON у golden-horse.ae нет, поэтому сетевые загрузки отключены: используем
зашитые VERIFIED-факты. Конкретику по каждой услуге (что входит, цена, сроки) эксперт берёт
со страницы услуги в промпте. Эксперт и гости НЕ выдумывают цен/сроков/характеристик.
"""

# --- Проверенные факты Golden Horse (fallback, сеть не нужна) ---
VERIFIED_FALLBACK = {
    "workshop_facts": [
        "Golden Horse is a car service / auto repair & maintenance workshop in Dubai, Al Quoz 3, 22nd Street, Warehouse 4.",
        "Opening hours: 10:00-20:00.",
        "Services: engine diagnostics & repair, oil change, AC repair, brakes, suspension, "
        "transmission, electrical diagnostics, tyres & wheel alignment, body repair & painting, "
        "pre-purchase inspection and detailing.",
        "Services all makes, including luxury brands (Mercedes, BMW, Porsche, Rolls-Royce, "
        "Bentley, Maserati) — 30+ brands.",
        "Booking is available online at golden-horse.ae.",
    ],
    "price_guide": [
        "Oil change from AED 200.",
        "Brake repair from AED 150.",
        "AC diagnostics AED 80.",
        "These are general examples only — the exact price for a specific service comes only "
        "from that service's own page.",
    ],
}


def refresh(force=False):
    """Возвращает проверенные факты Golden Horse (без сетевых запросов)."""
    return {
        "workshop_facts": list(VERIFIED_FALLBACK["workshop_facts"]),
        "price_guide": list(VERIFIED_FALLBACK["price_guide"]),
    }


def facts_text(knowledge=None):
    """Компактный блок фактов для промпта."""
    k = knowledge or refresh()
    workshop = "\n".join(f"- {x}" for x in k.get("workshop_facts", []))
    prices = "\n".join(f"- {x}" for x in k.get("price_guide", []))
    return (
        "VERIFIED GOLDEN HORSE FACTS (use ONLY these for any workshop/service/price claims; "
        "never invent prices, durations, parts or guarantees — exact per-service price only from "
        "the service page; the price examples below are general BACKGROUND only):\n"
        f"[Workshop]\n{workshop}\n[Price guide (background only)]\n{prices}"
    )


if __name__ == "__main__":
    print(facts_text())
