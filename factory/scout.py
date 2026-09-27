"""Scout: asks Claude for niche, text-based shirt concepts plus Etsy listing copy."""
import json
import random

MODEL = "claude-opus-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "concepts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "niche": {"type": "string"},
                    "lines": {"type": "array", "items": {"type": "string"}},
                    "accent_line": {"type": "integer"},
                    "style": {"type": "string", "enum": ["retro", "bold", "script"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "price": {"type": "number"},
                },
                "required": ["niche", "lines", "accent_line", "style", "title", "description", "tags", "price"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["concepts"],
    "additionalProperties": False,
}

PROMPT = """You're the product researcher for a small Etsy print-on-demand shop selling \
typography T-shirts (the design is just text, rendered in a nice font).

Come up with {count} new shirt concepts. What sells: a specific audience that identifies \
hard with a hobby, job or life stage (book lovers, nurses, new dads, plant people, teachers, \
dog moms, anglers...), a short phrase they'd say themselves, and a gift angle.

Rules:
- Original phrases only. No brands, trademarks, sports teams, celebrities, characters, \
song lyrics, movie quotes, or anything that might already be a registered slogan.
- 1 to 4 lines, each 16 characters max, uppercase or title case.
- accent_line = index (0-based) of the line to highlight in color.
- style: "retro" (chunky serif), "bold" (tall condensed caps) or "script" (for one-word accents).
- title: Etsy listing title under 140 characters, front-load the search terms buyers type.
- description: 3 short paragraphs: who it's for / gift idea, then the shirt (soft unisex \
Bella+Canvas 3001, printed on demand and shipped by our production partner), then care/sizing.
- tags: exactly 13, each 20 characters max, long-tail search phrases.
- price: USD retail between 22 and 32.
{avoid}"""

SAMPLES = [
    {"niche": "book lovers", "lines": ["JUST ONE", "MORE", "CHAPTER"], "accent_line": 1, "style": "retro"},
    {"niche": "coffee people", "lines": ["COFFEE", "FIRST", "PEOPLE", "LATER"], "accent_line": 0, "style": "bold"},
    {"niche": "plant parents", "lines": ["Plant", "Mama"], "accent_line": 0, "style": "script"},
    {"niche": "teachers", "lines": ["RUNNING ON", "CRAYONS &", "CAFFEINE"], "accent_line": 2, "style": "retro"},
    {"niche": "anglers", "lines": ["REEL", "COOL", "GRANDPA"], "accent_line": 1, "style": "bold"},
    {"niche": "nurses", "lines": ["NIGHT SHIFT", "SURVIVOR"], "accent_line": 1, "style": "bold"},
    {"niche": "dog owners", "lines": ["DOG HAIR", "IS MY", "GLITTER"], "accent_line": 2, "style": "retro"},
    {"niche": "gardeners", "lines": ["Dirt", "Is My", "Therapy"], "accent_line": 0, "style": "script"},
]


def generate(count, existing_titles, demo=False):
    if demo:
        return _demo(count, existing_titles)

    import anthropic

    avoid = ""
    if existing_titles:
        avoid = "\nAlready in the shop, don't repeat these:\n" + "\n".join(f"- {t}" for t in existing_titles[-60:])

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": PROMPT.format(count=count, avoid=avoid)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the request; try again or change the prompt.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Response was cut off; ask for fewer concepts.")
    text = next(b.text for b in response.content if b.type == "text")
    return [_clean(c) for c in json.loads(text)["concepts"]]


def _clean(c):
    c["lines"] = [l.strip()[:16] for l in c["lines"] if l.strip()][:4] or ["UNTITLED"]
    c["accent_line"] = max(0, min(int(c["accent_line"]), len(c["lines"]) - 1))
    c["title"] = c["title"][:140]
    c["tags"] = [t.strip()[:20] for t in c["tags"] if t.strip()][:13]
    c["price"] = round(min(max(float(c["price"]), 18), 40), 2)
    return c


def _demo(count, existing_titles):
    """Offline samples so the whole pipeline runs without an API key."""
    pool = [s for s in SAMPLES if _title(s) not in existing_titles] or SAMPLES
    picks = random.sample(pool, min(count, len(pool)))
    out = []
    for s in picks:
        phrase = " ".join(s["lines"]).title()
        out.append(_clean({
            **s,
            "title": _title(s),
            "description": (
                f"Made for {s['niche']} who get it. A fun gift for birthdays, holidays, or just because.\n\n"
                "Soft unisex Bella+Canvas 3001 tee, printed on demand and shipped by our production partner.\n\n"
                "Relaxed unisex fit, size up for oversized. Wash cold inside out, tumble dry low."
            ),
            "tags": [phrase[:20], f"{s['niche']} gift"[:20], f"{s['niche']} shirt"[:20], "funny tshirt",
                     "gift for her", "gift for him", "birthday gift", "unisex tee", "graphic tee",
                     "trendy shirt", "christmas gift", "typography shirt", "cute shirt"],
            "price": 26.0,
        }))
    return out


def _title(s):
    phrase = " ".join(s["lines"]).title()
    return f"{phrase} Shirt, Gift for {s['niche'].title()}, Funny {s['niche'].title()} Tee"
