"""
Lightweight NLP engine for the travel chatbot.

Uses NLTK tokenizer + lemmatizer when available, with a robust regex / keyword
fallback so the bot still works without network access. Performs:

- Intent classification (greet, search_flight, search_hotel, recommend, help,
  show_bookings, cancel, fallback).
- Entity extraction (origin, destination, city, dates, passengers, rooms,
  cabin class, star rating, budget).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

try:
    from dateutil import parser as dateparser
except Exception:  # pragma: no cover
    dateparser = None

# ---- NLTK (best-effort, optional) ----
_LEMMATIZER = None
try:
    import nltk

    for pkg in ('punkt', 'punkt_tab', 'wordnet', 'omw-1.4'):
        try:
            nltk.data.find(f'tokenizers/{pkg}' if 'punkt' in pkg else f'corpora/{pkg}')
        except LookupError:
            try:
                nltk.download(pkg, quiet=True)
            except Exception:
                pass
    from nltk.stem import WordNetLemmatizer
    _LEMMATIZER = WordNetLemmatizer()
except Exception:  # pragma: no cover
    nltk = None


# ---- Knowledge bases ----
INDIAN_CITIES = [
    'Delhi', 'New Delhi', 'Mumbai', 'Bangalore', 'Bengaluru', 'Hyderabad',
    'Chennai', 'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Surat',
    'Goa', 'Kochi', 'Cochin', 'Trivandrum', 'Thiruvananthapuram', 'Coimbatore',
    'Indore', 'Bhopal', 'Patna', 'Chandigarh', 'Manali', 'Shimla', 'Srinagar',
    'Leh', 'Darjeeling', 'Gangtok', 'Guwahati', 'Bhubaneswar', 'Visakhapatnam',
    'Vijayawada', 'Mysore', 'Mysuru', 'Mangalore', 'Mangaluru', 'Udaipur',
    'Jodhpur', 'Agra', 'Varanasi', 'Amritsar', 'Nagpur', 'Vadodara', 'Rishikesh',
    'Haridwar', 'Pondicherry', 'Puducherry', 'Andaman', 'Port Blair', 'Ooty',
    'Munnar', 'Alleppey', 'Alappuzha', 'Thekkady', 'Kanyakumari', 'Madurai',
    'Tirupati', 'Hampi', 'Khajuraho',
]
INDIAN_CITIES_LOWER = {c.lower(): c for c in INDIAN_CITIES}

CABIN_KEYWORDS = {
    'economy': 'economy', 'eco': 'economy',
    'premium economy': 'premium', 'premium': 'premium',
    'business': 'business', 'business class': 'business',
    'first class': 'first', 'first': 'first',
}

GREETINGS = ['hi', 'hello', 'hey', 'namaste', 'hola', 'good morning',
             'good afternoon', 'good evening', 'yo']
THANKS = ['thanks', 'thank you', 'thx', 'thankyou', 'cheers']
GOODBYES = ['bye', 'goodbye', 'see you', 'cya', 'tata']
HELP_KW = ['help', 'what can you do', 'how does this work', 'guide', 'menu']
BOOK_VIEW_KW = ['my bookings', 'my booking', 'booking history',
                'show bookings', 'view bookings', 'bookings list']
RECOMMEND_KW = ['recommend', 'suggest', 'where should i go', 'where to go',
                'best destination', 'good place', 'travel ideas', 'suggestion']
CANCEL_KW = ['cancel', 'refund']

FLIGHT_KW = ['flight', 'flights', 'fly', 'flying', 'plane', 'airfare',
             'air ticket', 'air tickets', 'tickets to', 'airline']
HOTEL_KW = ['hotel', 'hotels', 'stay', 'room', 'rooms', 'resort',
            'lodge', 'hostel', 'accommodation']

PROMO_KW = ['promo', 'promo code', 'coupon', 'coupons', 'offer', 'offers',
            'discount', 'deals', 'sale', 'voucher']
LOYALTY_KW = ['loyalty', 'points', 'rewards', 'reward points', 'my points',
              'travel points', 'tier', 'membership']
WISHLIST_KW = ['wishlist', 'favorite', 'favorites', 'saved', 'favourites']


@dataclass
class NluResult:
    intent: str
    confidence: float = 0.0
    entities: Dict = field(default_factory=dict)
    raw: str = ''


# ---------- Helpers ----------

def _tokenize(text: str) -> List[str]:
    if nltk is not None:
        try:
            return [t.lower() for t in nltk.word_tokenize(text)]
        except Exception:
            pass
    return re.findall(r"[A-Za-z']+|\d+", text.lower())


def _lemmatize(tokens: List[str]) -> List[str]:
    if _LEMMATIZER is None:
        return tokens
    try:
        return [_LEMMATIZER.lemmatize(t) for t in tokens]
    except Exception:
        return tokens


def _contains_any(text: str, words: List[str]) -> bool:
    t = text.lower()
    return any(re.search(rf"\b{re.escape(w)}\b", t) for w in words)


def _extract_cities(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (origin, destination) by looking for 'from X to Y' or 'X to Y'."""
    t = text.lower()
    origin = destination = None

    m = re.search(
        r"from\s+([A-Za-z][A-Za-z\s]+?)\s+(?:to|->|—|–|until)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|\s+for|\s+next|\s+tomorrow|\s+today|[.,?!]|$)",
        t,
    )
    if m:
        origin = INDIAN_CITIES_LOWER.get(m.group(1).strip(), m.group(1).strip().title())
        destination = INDIAN_CITIES_LOWER.get(m.group(2).strip(), m.group(2).strip().title())
        return origin, destination

    m = re.search(
        r"\b([A-Za-z][A-Za-z\s]+?)\s+(?:to|->|—|–)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+on|\s+for|\s+next|\s+tomorrow|\s+today|[.,?!]|$)",
        t,
    )
    if m:
        a = INDIAN_CITIES_LOWER.get(m.group(1).strip())
        b = INDIAN_CITIES_LOWER.get(m.group(2).strip())
        if a and b:
            return a, b

    # Single-city extraction (for hotel queries / fallback)
    found = []
    for c_lower, c in INDIAN_CITIES_LOWER.items():
        if re.search(rf"\b{re.escape(c_lower)}\b", t):
            found.append(c)
    found = list(dict.fromkeys(found))  # dedupe, preserve order
    if len(found) >= 2:
        return found[0], found[1]
    if len(found) == 1:
        return None, found[0]
    return None, None


def _extract_city(text: str) -> Optional[str]:
    _, dest = _extract_cities(text)
    if dest:
        return dest
    return None


def _extract_dates(text: str) -> Dict[str, Optional[date]]:
    """Detect departure/check-in (and optional check-out) dates."""
    today = date.today()
    t = text.lower()

    departure = None
    return_date = None

    if 'today' in t:
        departure = today
    if 'tomorrow' in t:
        departure = today + timedelta(days=1)
    if 'day after tomorrow' in t:
        departure = today + timedelta(days=2)

    m = re.search(r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", t)
    if m:
        target = ['monday', 'tuesday', 'wednesday', 'thursday',
                  'friday', 'saturday', 'sunday'].index(m.group(1))
        delta = (target - today.weekday()) % 7 or 7
        departure = today + timedelta(days=delta)

    m = re.search(r"in\s+(\d+)\s+(day|days|week|weeks|month|months)", t)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if 'week' in unit:
            n *= 7
        elif 'month' in unit:
            n *= 30
        departure = today + timedelta(days=n)

    # Try ISO / general date strings using dateutil
    if dateparser is not None:
        # 'on 25 Dec', 'from 5 Jan to 9 Jan' etc.
        date_strs = re.findall(
            r"\b(?:on\s+|from\s+|after\s+)?"
            r"(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
            r"(?:\s+\d{2,4})?|"
            r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}"
            r"(?:\s+\d{2,4})?|"
            r"\d{4}-\d{2}-\d{2}|"
            r"\d{1,2}/\d{1,2}/\d{2,4})", t)
        parsed_dates: List[date] = []
        for s in date_strs:
            try:
                d = dateparser.parse(s, default=datetime(today.year, today.month, today.day)).date()
                if d < today - timedelta(days=1):
                    d = d.replace(year=d.year + 1)
                parsed_dates.append(d)
            except Exception:
                continue
        if parsed_dates:
            departure = departure or parsed_dates[0]
            if len(parsed_dates) >= 2:
                return_date = parsed_dates[1]

    # 'for N nights/days'
    m = re.search(r"for\s+(\d+)\s+(night|nights|day|days)", t)
    if m and departure and not return_date:
        n = int(m.group(1))
        return_date = departure + timedelta(days=n)

    return {'departure': departure, 'return': return_date}


def _extract_int(text: str, keywords: List[str]) -> Optional[int]:
    for kw in keywords:
        m = re.search(rf"(\d+)\s+{kw}", text.lower())
        if m:
            return int(m.group(1))
        m = re.search(rf"{kw}\s*[:=]?\s*(\d+)", text.lower())
        if m:
            return int(m.group(1))
    return None


def _extract_cabin(text: str) -> Optional[str]:
    t = text.lower()
    for kw, val in sorted(CABIN_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if kw in t:
            return val
    return None


def _extract_stars(text: str) -> Optional[int]:
    m = re.search(r"(\d)\s*(?:star|stars|\*)", text.lower())
    if m:
        return min(max(int(m.group(1)), 1), 5)
    return None


def _extract_budget(text: str) -> Optional[int]:
    m = re.search(
        r"(?:under|below|less than|max|maximum|upto|up to|within|budget of)\s*"
        r"(?:rs\.?|inr|₹|\$)?\s*(\d{2,7})",
        text.lower(),
    )
    if m:
        return int(m.group(1))
    m = re.search(r"(?:rs\.?|inr|₹|\$)\s*(\d{2,7})", text.lower())
    if m:
        return int(m.group(1))
    return None


# ---------- Intent classification ----------

def classify_intent(text: str) -> Tuple[str, float]:
    t = text.lower().strip()
    if not t:
        return 'fallback', 0.0

    if _contains_any(t, GREETINGS):
        return 'greet', 0.9
    if _contains_any(t, GOODBYES):
        return 'goodbye', 0.9
    if _contains_any(t, THANKS):
        return 'thanks', 0.9
    if _contains_any(t, HELP_KW):
        return 'help', 0.9
    if _contains_any(t, BOOK_VIEW_KW):
        return 'show_bookings', 0.9
    if _contains_any(t, CANCEL_KW):
        return 'cancel', 0.7
    if _contains_any(t, RECOMMEND_KW):
        return 'recommend', 0.85
    if _contains_any(t, PROMO_KW):
        return 'promo', 0.85
    if _contains_any(t, LOYALTY_KW):
        return 'loyalty', 0.85
    if _contains_any(t, WISHLIST_KW):
        return 'wishlist', 0.85

    flight_score = sum(1 for kw in FLIGHT_KW if re.search(rf"\b{kw}\b", t))
    hotel_score = sum(1 for kw in HOTEL_KW if re.search(rf"\b{kw}\b", t))

    if flight_score and flight_score >= hotel_score:
        return 'search_flight', 0.8
    if hotel_score:
        return 'search_hotel', 0.8

    # Heuristic: 'book X to Y' implies flight
    if re.search(r"book\s+\w+\s+to\s+\w+", t):
        return 'search_flight', 0.6
    if 'book' in t and any(c in t for c in INDIAN_CITIES_LOWER):
        return 'search_hotel', 0.55

    return 'fallback', 0.3


# ---------- Public API ----------

def parse(text: str) -> NluResult:
    intent, confidence = classify_intent(text)
    entities: Dict = {}

    origin, destination = _extract_cities(text)
    if origin:
        entities['origin'] = origin
    if destination:
        entities['destination'] = destination

    dates = _extract_dates(text)
    if dates['departure']:
        entities['departure_date'] = dates['departure'].isoformat()
    if dates['return']:
        entities['return_date'] = dates['return'].isoformat()

    passengers = _extract_int(text, ['passenger', 'passengers', 'people',
                                     'pax', 'adult', 'adults'])
    if passengers:
        entities['passengers'] = passengers

    rooms = _extract_int(text, ['room', 'rooms'])
    if rooms:
        entities['rooms'] = rooms
    guests = _extract_int(text, ['guest', 'guests'])
    if guests:
        entities['guests'] = guests

    cabin = _extract_cabin(text)
    if cabin:
        entities['cabin_class'] = cabin

    stars = _extract_stars(text)
    if stars:
        entities['min_stars'] = stars

    budget = _extract_budget(text)
    if budget:
        entities['budget'] = budget

    if intent == 'search_hotel' and 'destination' not in entities:
        c = _extract_city(text)
        if c:
            entities['city'] = c
    elif intent == 'search_hotel' and 'destination' in entities:
        entities['city'] = entities['destination']

    return NluResult(intent=intent, confidence=confidence, entities=entities, raw=text)
