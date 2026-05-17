import re

# ---------------------------------------------------------------------------
# Price
# ---------------------------------------------------------------------------

def parse_price(text: str) -> int | None:
    lower = text.lower()
    if re.search(r'\$[\d,]+\s*/\s*week', lower):
        return None
    m = re.search(r'\$\s*([\d,]+)\s*(?:/\s*mo(?:nth)?|per\s+month)', lower)
    if m:
        return int(m.group(1).replace(',', ''))
    # Fallback for bare dollar amounts (e.g., "Starting from $2,290")
    m = re.search(r'\$\s*([\d,]+)', lower)
    if m:
        return int(m.group(1).replace(',', ''))
    return None


# ---------------------------------------------------------------------------
# Bedrooms
# ---------------------------------------------------------------------------

def parse_bedrooms(text: str) -> int | None:
    m = re.search(r"(\d+)\s*[Bb]ed", text)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Pets
# ---------------------------------------------------------------------------

_CATS_CONFIRMED = re.compile(
    r"cats?\s+(?:ok|allowed|welcome|permitted|friendly|are\s+(?:ok|allowed|welcome))"
    r"|\d+\s+cats?\s+(?:ok|welcome|allowed|fine)",
    re.IGNORECASE,
)
_PETS_ALLOWED = re.compile(r"pets?\s+(?:allowed|welcome|ok|permitted|friendly)", re.IGNORECASE)
_PETS_DENIED = re.compile(r"no\s+pets?|pets?\s+not\s+allowed|no\s+animals?", re.IGNORECASE)


def parse_pets(body: str) -> str | None:
    if _CATS_CONFIRMED.search(body):
        return "cats_confirmed"
    if _PETS_DENIED.search(body):
        return "not_allowed"
    if _PETS_ALLOWED.search(body):
        return "allowed"
    return None


# ---------------------------------------------------------------------------
# Floor level
# ---------------------------------------------------------------------------

def parse_floor_level(body: str) -> str | None:
    lower = body.lower()
    if "basement" in lower:
        return "basement"
    if re.search(
        r"\b(?:upper\s+(?:floor|unit|front|rear)|upper\b|[2-9]\w*\s+floor|second\s+floor|third\s+floor)",
        lower,
    ):
        return "upper"
    if re.search(
        r"\b(?:main\s+floor|ground\s+floor|1st\s+floor|first\s+floor|garden\s+floor|garden\b|ground\b)",
        lower,
    ):
        return "main"
    return None


# ---------------------------------------------------------------------------
# Laundry
# ---------------------------------------------------------------------------

_LAUNDRY_INUNIT = re.compile(
    r"in[- ]?unit\s+laundry|laundry\s+in[- ]?unit"
    r"|ensuite\s+laundry|in[- ]?suite\s+laundry"
    r"|washer\s+(?:and\s+)?dryer\s+in\s+(?:the\s+)?unit",
    re.IGNORECASE,
)
_LAUNDRY_SHARED = re.compile(
    r"shared\s+laundry|coin\s+laundry|common\s+laundry"
    r"|laundry\s+in\s+(?:the\s+)?build|laundry\s+on[- ]?site|laundry\s+room",
    re.IGNORECASE,
)


def parse_laundry(body: str) -> bool | None:
    if not re.search(r"laundry|washer|dryer", body, re.IGNORECASE):
        return None
    if _LAUNDRY_INUNIT.search(body):
        return True
    if _LAUNDRY_SHARED.search(body):
        return False
    return None


# ---------------------------------------------------------------------------
# Outdoor space
# ---------------------------------------------------------------------------

_OUTDOOR = re.compile(
    r"balcony|backyard|back\s+yard|patio|terrace|\byards?\b|\bdeck\b", re.IGNORECASE
)


def parse_outdoor_space(body: str) -> bool | None:
    return True if _OUTDOOR.search(body) else None


# ---------------------------------------------------------------------------
# Parking
# ---------------------------------------------------------------------------

def parse_parking(body: str) -> int | None:
    lower = body.lower()
    if re.search(r"double\s+(?:car\s+)?garage|double\s+parking", lower):
        return 2
    m = re.search(r"(\d+)\s+parking", lower)
    if m:
        return int(m.group(1))
    if re.search(r"\bparking\b", lower):
        return 1
    return None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def parse_utilities(body: str) -> str | None:
    lower = body.lower()
    if re.search(r"\b(?:utilities|heat|hydro|water)\b", lower) and "included" in lower:
        return "included"
    if re.search(r"all\s+utilities", lower):
        return "included"
    if re.search(
        r"utilities\s+extra|utilities\s+not\s+incl|tenant\s+pays|\+\s*utilities|\bplus\s+utilities\b",
        lower,
    ):
        return "extra"
    return None
