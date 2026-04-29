"""
search.py  —  Strict Catalog Search Pipeline
═════════════════════════════════════════════
Stage 0  Domain validation     Is the query about baby/kids/mom products at all?
                               If not → "No matching products found. Please try a valid product query."
Stage 1  Budget extraction     Parse "under 300 AED", "below 200", etc.
Stage 2  Age extraction        Parse months, years, ranges, under/above correctly.
                               "12 years" ≠ "12 months". Never mix them up.
Stage 3  Intent extraction     Map query → product type via INTENT_MAP keyword matching
Stage 4  Hard keyword filter   Keep only products whose name/description contain
                               an intent keyword AND whose category is allowed.
Stage 5  Age filter            Drop products whose age_group is incompatible with
                               the requested age. Strict month/year boundary logic.
Stage 6  Price filter          Drop products above effective budget.
Stage 7  Cosine re-rank        Semantic ranking within the valid shortlist only.
Stage 8  Groq generation       Warm structured card output.

Return flags:
  "invalid_query"  True  → query is not about our catalog domain
  "no_match"       True  → intent found, but no products pass keyword+age+price filters
  "budget_miss"    True  → products exist for intent/age, but all exceed budget
  "age_miss"       True  → products exist for intent, but none fit the requested age
  normal           recommendations list is non-empty
"""

import os
import re
import json
from typing import Optional
from groq import Groq
from sentence_transformers import SentenceTransformer
from ingest import get_collection

EMBED_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL  = "llama-3.3-70b-versatile"

# ─────────────────────────────────────────────────────────────────────────────
# CATALOG DOMAIN KEYWORDS
# A query must contain at least one of these (or match an INTENT_MAP label)
# to be considered valid for our catalog.
# ─────────────────────────────────────────────────────────────────────────────
CATALOG_DOMAIN_KEYWORDS = [
    # product types
    "stroller", "pram", "pushchair", "buggy",
    "car seat", "carseat", "infant seat", "booster seat",
    "carrier", "baby carrier",
    "travel cot", "playpen",
    "diaper bag", "nappy bag",
    "toy", "toys", "puzzle", "blocks", "play mat", "activity gym",
    "high chair", "highchair", "feeding chair", "booster chair", "feeding seat",
    "bottle", "feeding bottle",
    "sterilizer", "steriliser",
    "bottle warmer",
    "sippy cup", "training cup",
    "bib",
    "food maker", "baby blender",
    "diaper", "diapers", "nappy", "nappies",
    "baby wipes", "wet wipes",
    "baby shampoo", "baby wash",
    "baby lotion", "baby cream", "baby oil",
    "pacifier", "dummy", "soother",
    "thermometer",
    "swaddle",
    "breast pump", "nursing pump",
    "nursing cover", "nursing pillow", "breastfeeding",
    "maternity pillow", "pregnancy pillow",
    "postpartum", "postnatal",
    "stretch mark cream",
    # age/person anchors that imply catalog relevance
    "baby", "babies", "infant", "newborn", "toddler", "toddlers",
    "kids", "children", "child",
    "mom", "mum", "mother", "mommy", "mummy", "mama",
    "pregnancy", "pregnant",
    # domain anchors
    "feeding", "nursery", "bath time", "bath toy",
    "gift for baby", "gift for mom", "baby shower",
    "mumzworld",
]

# ─────────────────────────────────────────────────────────────────────────────
# INTENT MAP
# ─────────────────────────────────────────────────────────────────────────────
INTENT_MAP = {
    "stroller": {
        "categories":    ["Travel"],
        "name_keywords": ["stroller", "pram", "pushchair", "buggy"],
        "desc_keywords": ["stroller", "pram", "pushchair"],
    },
    "car seat": {
        "categories":    ["Travel"],
        "name_keywords": ["car seat", "carseat", "car-seat", "infant seat", "booster seat"],
        "desc_keywords": ["car seat", "vehicle seat"],
    },
    "carrier": {
        "categories":    ["Travel"],
        "name_keywords": ["carrier", "baby carrier"],
        "desc_keywords": ["baby carrier", "ergonomic carry"],
    },
    "travel cot": {
        "categories":    ["Travel"],
        "name_keywords": ["cot", "playpen", "travel cot"],
        "desc_keywords": ["portable cot", "travel cot", "playpen"],
    },
    "diaper bag": {
        "categories":    ["Travel"],
        "name_keywords": ["diaper bag", "nappy bag", "changing bag"],
        "desc_keywords": ["diaper bag", "nappy bag"],
    },
    "toy": {
        "categories":    ["Toys"],
        "name_keywords": ["toy", "toys", "puzzle", "blocks", "block set", "piano",
                          "kitchen set", "hopper", "play mat", "activity gym",
                          "stacking", "sorting", "game"],
        "desc_keywords": ["toy", "play", "educational", "develop"],
    },
    "feeding chair": {
        "categories":    ["Feeding"],
        "name_keywords": ["high chair", "highchair", "booster chair",
                          "feeding seat", "feeding chair", "high-chair"],
        "desc_keywords": ["high chair", "feeding seat", "mealtime seat"],
    },
    "bottle": {
        "categories":    ["Feeding", "Baby Essentials"],
        "name_keywords": ["bottle", "feeding bottle"],
        "desc_keywords": ["bottle", "anti-colic"],
    },
    "sterilizer": {
        "categories":    ["Feeding"],
        "name_keywords": ["sterilizer", "steriliser"],
        "desc_keywords": ["sterilize", "sterilise"],
    },
    "bottle warmer": {
        "categories":    ["Feeding"],
        "name_keywords": ["bottle warmer", "warmer"],
        "desc_keywords": ["warm milk", "bottle warming"],
    },
    "sippy cup": {
        "categories":    ["Feeding"],
        "name_keywords": ["sippy cup", "sippy", "training cup", "toddler cup"],
        "desc_keywords": ["sippy", "spill-proof cup", "training cup"],
    },
    "bib": {
        "categories":    ["Feeding"],
        "name_keywords": ["bib", "silicone bib", "crumb catcher"],
        "desc_keywords": ["bib", "mealtime"],
    },
    "food maker": {
        "categories":    ["Feeding"],
        "name_keywords": ["food maker", "blender", "baby food maker"],
        "desc_keywords": ["puree", "steam blend", "baby food"],
    },
    "diaper": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["diaper", "diapers", "nappy", "nappies"],
        "desc_keywords": ["diaper", "nappy"],
    },
    "wipes": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["wipes", "wet wipes", "baby wipes"],
        "desc_keywords": ["wipes", "gentle clean"],
    },
    "shampoo": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["shampoo", "baby wash", "hair wash", "bath wash"],
        "desc_keywords": ["shampoo", "baby wash", "tear-free"],
    },
    "lotion": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["lotion", "moisturizer", "moisturiser", "baby cream", "baby oil"],
        "desc_keywords": ["moisturize", "skin care", "lotion"],
    },
    "pacifier": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["pacifier", "dummy", "soother"],
        "desc_keywords": ["pacifier", "dummy", "soother"],
    },
    "thermometer": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["thermometer"],
        "desc_keywords": ["temperature", "fever"],
    },
    "swaddle": {
        "categories":    ["Baby Essentials"],
        "name_keywords": ["swaddle", "swaddling blanket", "muslin wrap"],
        "desc_keywords": ["swaddle", "wrap baby"],
    },
    "breast pump": {
        "categories":    ["Mom Care"],
        "name_keywords": ["breast pump", "nursing pump", "electric pump", "manual pump"],
        "desc_keywords": ["breast pump", "expressing milk"],
    },
    "nursing": {
        "categories":    ["Mom Care"],
        "name_keywords": ["nursing cover", "nursing pillow", "breastfeeding pillow",
                          "nursing bra", "lactation"],
        "desc_keywords": ["nursing", "breastfeeding", "lactation"],
    },
    "maternity": {
        "categories":    ["Mom Care"],
        "name_keywords": ["maternity pillow", "pregnancy pillow", "maternity belt"],
        "desc_keywords": ["maternity", "pregnancy", "prenatal"],
    },
    "postpartum": {
        "categories":    ["Mom Care"],
        "name_keywords": ["postpartum", "recovery belt", "postnatal"],
        "desc_keywords": ["postpartum", "recovery", "after birth"],
    },
    "stretch mark": {
        "categories":    ["Mom Care"],
        "name_keywords": ["stretch mark", "belly cream", "belly oil"],
        "desc_keywords": ["stretch mark", "belly"],
    },
    # ── Open / occasion intents (no strict name_keyword gate) ─────────────────
    "gift": {
        "categories":    [],           # any category
        "name_keywords": [],
        "desc_keywords": [],
    },
    "newborn": {
        "categories":    ["Baby Essentials", "Feeding", "Travel", "Mom Care"],
        "name_keywords": [],
        "desc_keywords": ["newborn", "0-3 months", "infant"],
    },
    "bath": {
        "categories":    ["Toys", "Baby Essentials"],
        "name_keywords": ["bath toy", "bath", "bathtub"],
        "desc_keywords": ["bath", "bathing"],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# AGE GROUP TABLE
# Maps each catalog age_group label → (min_months, max_months) inclusive.
# Products labelled "All Ages" are always included regardless of age filter.
# ─────────────────────────────────────────────────────────────────────────────
AGE_GROUP_RANGES: dict[str, tuple[int, int]] = {
    # Newborn / infant
    "newborn":           (0,   3),
    "0-3 months":        (0,   3),
    "0-6 months":        (0,   6),
    "3-6 months":        (3,   6),
    "6-12 months":       (6,  12),
    "0-12 months":       (0,  12),
    "6-18 months":       (6,  18),
    # Toddler
    "12-18 months":     (12,  18),
    "18-24 months":     (18,  24),
    "1-2 years":        (12,  24),
    "1-3 years":        (12,  36),
    "2-3 years":        (24,  36),
    "18 months-3 years":(18,  36),
    # Pre-school
    "2-4 years":        (24,  48),
    "3-5 years":        (36,  60),
    "3+ years":         (36, 999),
    "3-6 years":        (36,  72),
    "4-6 years":        (48,  72),
    # School age
    "5-8 years":        (60,  96),
    "6-10 years":       (72, 120),
    "8-12 years":       (96, 144),
    "10+ years":       (120, 999),
    "12+ years":       (144, 999),
    # Broad / open
    "0-2 years":        (0,   24),
    "0-4 years":        (0,   48),
    "0-5 years":        (0,   60),
    "toddler":          (12,  48),
    "kids":             (12, 144),
    "all ages":         (0,  999),
    "prenatal":         (0,    0),   # mom products — never age-filtered out
    "mom":              (0,    0),   # mom products — never age-filtered out
    "pregnancy":        (0,    0),
}

_embed_model: Optional[SentenceTransformer] = None
_groq_client: Optional[Groq] = None


# ── Singleton helpers ─────────────────────────────────────────────────────────

def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    return _groq_client


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 0  Domain validation
# ─────────────────────────────────────────────────────────────────────────────

def is_valid_catalog_query(query: str) -> bool:
    """
    Return True ONLY if the query is clearly about baby/kids/mom products.
    Checks:
      1. Any CATALOG_DOMAIN_KEYWORD appears in the query.
      2. Any INTENT_MAP label or its keywords appear in the query.
    If neither matches → invalid query.
    """
    q = " " + query.lower() + " "

    # Check domain keywords
    for kw in CATALOG_DOMAIN_KEYWORDS:
        if kw in q:
            return True

    # Check every intent's name/desc keywords
    for cfg in INTENT_MAP.values():
        for kw in cfg["name_keywords"] + cfg["desc_keywords"]:
            if kw and kw in q:
                return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1  Budget extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_budget(query: str) -> Optional[float]:
    patterns = [
        r"(?:under|below|less\s+than|max(?:imum)?|up\s+to)\s*(\d+(?:\.\d+)?)\s*(?:aed|dirhams?)?",
        r"(\d+(?:\.\d+)?)\s*(?:aed|dirhams?)\s*(?:or\s+less|max(?:imum)?|budget)",
    ]
    for pat in patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            return float(m.group(1))
    return None


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2  Age extraction → (min_months, max_months) or None
# ─────────────────────────────────────────────────────────────────────────────

def _to_months(value: float, unit: str) -> int:
    """Convert a numeric age value + unit string to integer months."""
    u = unit.lower().strip()
    if u in ("year", "years", "yr", "yrs", "y"):
        return int(round(value * 12))
    # months / month / mo / mos / m
    return int(round(value))


def extract_age_range(query: str) -> Optional[tuple[int, int]]:
    """
    Parse the query and return (min_months, max_months) or None.

    Handles:
      • "for a 2-year-old"       → (24, 24)  exact match
      • "for 18 months"          → (18, 18)
      • "under 2 years"          → (0,  24)
      • "above 3 years"          → (36, 999)
      • "between 1 and 3 years"  → (12, 36)
      • "1-2 years"              → (12, 24)
      • "3 to 5 years"           → (36, 60)
      • "12 year old"            → (144, 144)  ← correctly 12 years, not months

    Key rule: if unit is "year/years" → multiply by 12.
              if unit is "month/months" → use as-is.
    """
    q = query.lower()

    # ── Range: "between X and Y unit" / "X to Y unit" / "X-Y unit" ───────────
    range_patterns = [
        # "between 1 and 3 years" / "between 6 and 12 months"
        r"between\s+(\d+(?:\.\d+)?)\s+and\s+(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)",
        # "1 to 3 years" / "6 to 12 months"
        r"(\d+(?:\.\d+)?)\s+to\s+(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)",
        # "1-3 years" / "6-12 months"
        r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)",
    ]
    for pat in range_patterns:
        m = re.search(pat, q)
        if m:
            lo = _to_months(float(m.group(1)), m.group(3))
            hi = _to_months(float(m.group(2)), m.group(3))
            return (min(lo, hi), max(lo, hi))

    # ── Upper bound: "under/below/less than X unit" ───────────────────────────
    upper_patterns = [
        r"(?:under|below|less\s+than|up\s+to|younger\s+than)\s+(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)",
    ]
    for pat in upper_patterns:
        m = re.search(pat, q)
        if m:
            hi = _to_months(float(m.group(1)), m.group(2))
            return (0, hi)

    # ── Lower bound: "above/over/older than X unit" ───────────────────────────
    lower_patterns = [
        r"(?:above|over|older\s+than|at\s+least)\s+(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)",
        r"(\d+(?:\.\d+)?)\s*\+\s*(year|years|month|months|yr|yrs|mo|mos)",
        r"(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)\s*(?:and\s+)?(?:above|over|older|plus|\+)",
    ]
    for pat in lower_patterns:
        m = re.search(pat, q)
        if m:
            lo = _to_months(float(m.group(1)), m.group(2))
            return (lo, 999)

    # ── Exact: "for a 2-year-old" / "for 18 months" / "12 year old" ──────────
    exact_patterns = [
        # "2-year-old" / "2 year old"
        r"(\d+(?:\.\d+)?)\s*[-\s]?(year|years|yr|yrs)[-\s]?old",
        # "for 18 months" / "18 month old"
        r"(\d+(?:\.\d+)?)\s*(month|months|mo|mos)[-\s]?old",
        # plain "for 3 years" / "for 6 months" (no "old")
        r"(?:for\s+(?:a\s+)?|age\s+)(\d+(?:\.\d+)?)\s*(year|years|month|months|yr|yrs|mo|mos)",
        # "suitable for 2 years"
        r"(?:suitable\s+for|designed\s+for|recommended\s+for)\s+(\d+(?:\.\d+)?)\s*(year|years|month|months)",
    ]
    for pat in exact_patterns:
        m = re.search(pat, q)
        if m:
            val = _to_months(float(m.group(1)), m.group(2))
            # Allow ±3 months tolerance for exact age match
            return (max(0, val - 3), val + 3)

    return None   # no age mentioned in query


def _parse_product_age_range(age_group: str) -> tuple[int, int]:
    """
    Convert a product's age_group label to (min_months, max_months).
    Falls back to (0, 999) if the label is unknown (treat as all-ages).
    """
    ag = age_group.strip().lower()

    # Direct lookup
    if ag in AGE_GROUP_RANGES:
        return AGE_GROUP_RANGES[ag]

    # "all ages" / "mom" / "prenatal" / "pregnancy" → never filter out
    for open_label in ("all ages", "mom", "prenatal", "pregnancy", "all"):
        if open_label in ag:
            return (0, 999)

    # Try to parse on the fly (e.g. "5+ years", "2-4 years")
    # Range "X-Y unit"
    m = re.match(r"(\d+)\s*[-–]\s*(\d+)\s*(year|years|month|months)?", ag)
    if m:
        unit = m.group(3) or "months"
        lo = _to_months(float(m.group(1)), unit)
        hi = _to_months(float(m.group(2)), unit)
        return (lo, hi)

    # "X+ unit"
    m = re.match(r"(\d+)\+?\s*(year|years|month|months)", ag)
    if m:
        lo = _to_months(float(m.group(1)), m.group(2))
        return (lo, 999)

    # Unknown label — don't filter out
    return (0, 999)


def age_groups_overlap(
    product_range: tuple[int, int],
    query_range: tuple[int, int],
) -> bool:
    """
    Return True if [product_min, product_max] overlaps [query_min, query_max].
    Products labelled all-ages (0, 999) always return True.
    """
    p_min, p_max = product_range
    q_min, q_max = query_range
    # Ranges overlap when p_min <= q_max AND p_max >= q_min
    return p_min <= q_max and p_max >= q_min


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3  Intent extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_intent(query: str) -> Optional[dict]:
    q = query.lower()
    for label, cfg in INTENT_MAP.items():
        trigger_words = [label] + cfg["name_keywords"] + cfg["desc_keywords"]
        trigger_words = list(dict.fromkeys(w for w in trigger_words if w))
        for kw in trigger_words:
            if kw in q:
                return {"label": label, **cfg}
    return None


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 4  Hard keyword filter
# ─────────────────────────────────────────────────────────────────────────────

def hard_filter(all_products: list[dict], intent: Optional[dict]) -> list[dict]:
    """
    For a known intent: product MUST pass both:
      (a) category gate  — product.category in intent["categories"] (if non-empty)
      (b) keyword gate   — product name or description contains an intent keyword

    For an unknown intent (None): return all products (cosine will rank).
    """
    if intent is None:
        return all_products

    name_kws = intent["name_keywords"]
    desc_kws = intent["desc_keywords"]
    cats     = intent["categories"]

    passed = []
    for p in all_products:
        name = p["product_name"].lower()
        desc = p["description"].lower()
        cat  = p["category"]

        # Category gate
        if cats and cat not in cats:
            continue

        # Keyword gate (skip if no keywords defined — open intent)
        if not name_kws and not desc_kws:
            passed.append(p)
            continue

        name_hit = any(kw in name for kw in name_kws)
        desc_hit = any(kw in desc for kw in desc_kws)
        if name_hit or desc_hit:
            passed.append(p)

    return passed


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 5  Age filter
# ─────────────────────────────────────────────────────────────────────────────

def age_filter(
    products: list[dict],
    age_range: Optional[tuple[int, int]],
) -> list[dict]:
    """
    If an age_range was extracted from the query, keep only products whose
    age_group overlaps that range.
    Products with "all ages", "mom", "prenatal" are always kept.
    """
    if age_range is None:
        return products   # no age mentioned → no filtering

    kept = []
    for p in products:
        product_range = _parse_product_age_range(p["age_group"])
        # Mom/prenatal/pregnancy products are never age-filtered
        ag_lower = p["age_group"].lower()
        if any(t in ag_lower for t in ("mom", "prenatal", "pregnancy", "all")):
            kept.append(p)
            continue
        if age_groups_overlap(product_range, age_range):
            kept.append(p)

    return kept


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 6  Price filter
# ─────────────────────────────────────────────────────────────────────────────

def price_filter(products: list[dict], max_price: Optional[float]) -> list[dict]:
    if max_price is None:
        return products
    return [p for p in products if p["price_aed"] <= max_price]


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 7  Cosine re-rank within the strict shortlist
# ─────────────────────────────────────────────────────────────────────────────

def cosine_rank(query: str, products: list[dict], n: int) -> list[dict]:
    if not products:
        return []

    collection = get_collection()
    model      = _get_embed_model()
    query_emb  = model.encode([query]).tolist()[0]

    all_results = collection.query(
        query_embeddings=[query_emb],
        n_results=collection.count(),
        include=["metadatas", "distances"],
    )

    name_to_score: dict[str, float] = {}
    for meta, dist in zip(all_results["metadatas"][0], all_results["distances"][0]):
        name_to_score[meta["product_name"]] = round(1 - dist, 4)

    for p in products:
        p["score"] = name_to_score.get(p["product_name"], 0.0)

    products.sort(key=lambda x: x["score"], reverse=True)
    return products[:n]


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 8  Groq recommendation generation
# ─────────────────────────────────────────────────────────────────────────────

def build_recommendation(query: str, products: list[dict]) -> dict:
    if not products:
        return {"intro": "", "recommendations": []}

    product_block = ""
    for i, p in enumerate(products, 1):
        product_block += (
            f"\nProduct {i}:\n"
            f"  Name: {p['product_name']}\n"
            f"  Brand: {p['brand']}\n"
            f"  Category: {p['category']}\n"
            f"  Price: {p['price_aed']} AED\n"
            f"  Age Group: {p['age_group']}\n"
            f"  Description: {p['description']}\n"
        )

    system_prompt = (
        "You are a helpful, friendly shopping assistant for Mumzworld, "
        "a leading baby and mom products retailer in the UAE. "
        "Your tone is warm, concise, and parent-focused. "
        "You respond ONLY with a valid JSON object — no markdown, no extra text."
    )

    user_prompt = f"""
A customer searched: "{query}"

Here are the matched products from our catalog (already ranked by best match):
{product_block}

Return a JSON object with EXACTLY this structure — no extra fields, no markdown:
{{
  "intro": "<One short warm sentence introducing these picks>",
  "recommendations": [
    {{
      "product_name": "<exact product name>",
      "why": "<1-2 sentences: why it fits — mention price, age suitability, key feature>"
    }}
  ]
}}

Rules:
- "intro": 1 sentence, warm and natural.
- "why": 1-2 sentences. Mention price and one key benefit.
- Preserve product order exactly as given.
- Return ONLY valid JSON. No preamble, no markdown fences, no extra text.
"""

    response = _get_groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=700,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?", "", raw, flags=re.MULTILINE).strip()
    raw = re.sub(r"```$",          "", raw, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "intro": "Here are the best matching products for your search.",
            "recommendations": [
                {"product_name": p["product_name"], "why": p["description"]}
                for p in products
            ],
        }

    why_map = {r["product_name"]: r.get("why", "") for r in parsed.get("recommendations", [])}
    for p in products:
        p["why"] = why_map.get(p["product_name"], p["description"])

    return {
        "intro": parsed.get("intro", "Here are my top picks for you."),
        "recommendations": products,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Fetch full catalog from ChromaDB
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_all_products() -> list[dict]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.get(include=["metadatas"])
    return [
        {
            "product_name": m["product_name"],
            "brand":        m["brand"],
            "category":     m["category"],
            "price_aed":    float(m["price_aed"]),
            "age_group":    m["age_group"],
            "description":  m["description"],
            "score":        0.0,
        }
        for m in results["metadatas"]
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run_query(
    query: str,
    manual_max_price: Optional[float] = None,
    n_results: int = 3,
) -> dict:
    """
    Returns a dict with keys:
      invalid_query  bool   — query is not about our catalog domain
      no_match       bool   — valid query but zero products pass all filters
      budget_miss    bool   — products exist for intent/age but all exceed budget
      age_miss       bool   — products exist for intent but none fit the age
      budget_used    float | None
      age_range      tuple | None
      intent_label   str | None
      intro          str
      recommendations list
    """

    BASE = {
        "invalid_query": False, "no_match": False,
        "budget_miss":   False, "age_miss":  False,
        "budget_used": None, "age_range": None, "intent_label": None,
        "intro": "", "recommendations": [],
    }

    # ── Stage 0  Domain validation ─────────────────────────────────────────────
    if not is_valid_catalog_query(query):
        return {**BASE, "invalid_query": True}

    # ── Stage 1  Budget ────────────────────────────────────────────────────────
    auto_budget      = extract_budget(query)
    effective_budget = manual_max_price if manual_max_price is not None else auto_budget
    BASE["budget_used"] = effective_budget

    # ── Stage 2  Age ───────────────────────────────────────────────────────────
    age_range = extract_age_range(query)
    BASE["age_range"] = age_range

    # ── Stage 3  Intent ────────────────────────────────────────────────────────
    intent = extract_intent(query)
    BASE["intent_label"] = intent["label"] if intent else None

    # ── Fetch full catalog ─────────────────────────────────────────────────────
    all_products = _fetch_all_products()

    # ── Stage 4  Hard keyword + category filter ────────────────────────────────
    intent_matched = hard_filter(all_products, intent)
    if intent and not intent_matched:
        return {**BASE, "no_match": True}

    # ── Stage 5  Age filter ────────────────────────────────────────────────────
    age_filtered = age_filter(intent_matched, age_range)
    if age_range is not None and not age_filtered and intent_matched:
        return {**BASE, "age_miss": True}

    pool = age_filtered if age_filtered else intent_matched

    # ── Stage 6  Price filter ──────────────────────────────────────────────────
    budget_filtered = price_filter(pool, effective_budget)
    if effective_budget is not None and not budget_filtered and pool:
        return {**BASE, "budget_miss": True}

    if not budget_filtered:
        return {**BASE, "no_match": True}

    # ── Stage 7  Cosine re-rank ────────────────────────────────────────────────
    final_products = cosine_rank(query, budget_filtered, n_results)

    # ── Stage 8  Groq recommendation ──────────────────────────────────────────
    result = build_recommendation(query, final_products)
    return {**BASE, **result}