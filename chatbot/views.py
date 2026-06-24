"""Chatbot HTTP endpoints + dialogue manager."""
import json
import random
import uuid
from datetime import datetime
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from django.utils import timezone

from booking.models import Flight, Hotel, Coupon, WishlistItem
from .models import ChatMessage, ChatSession
from .nlp_engine import parse


# ---------- Helpers ----------

def _get_or_create_session(request):
    """Use Django's session_key as a stable identifier for chat sessions."""
    if not request.session.session_key:
        request.session.save()
    sk = request.session.session_key
    session, _ = ChatSession.objects.get_or_create(
        session_key=sk,
        defaults={'user': request.user if request.user.is_authenticated else None},
    )
    if request.user.is_authenticated and session.user is None:
        session.user = request.user
        session.save()
    return session


def _format_flight_card(f: Flight) -> dict:
    return {
        'type': 'flight',
        'id': f.id,
        'title': f"{f.airline} {f.flight_number}",
        'subtitle': f"{f.origin} → {f.destination}",
        'departure': f.departure_time.strftime('%a %d %b · %H:%M'),
        'arrival': f.arrival_time.strftime('%H:%M'),
        'duration': f.duration_str,
        'cabin': f.get_cabin_class_display(),
        'price': float(f.price),
        'seats': f.seats_available,
        'book_url': reverse('booking:flight_book', args=[f.id]),
    }


def _format_hotel_card(h: Hotel) -> dict:
    return {
        'type': 'hotel',
        'id': h.id,
        'title': h.name,
        'subtitle': f"{h.city}, {h.country}",
        'stars': h.star_rating,
        'amenities': h.amenity_list[:5],
        'price': float(h.price_per_night),
        'rooms': h.rooms_available,
        'image': h.image_url,
        'book_url': reverse('booking:hotel_book', args=[h.id]),
    }


# ---------- Dialogue logic ----------

GREETING_RESPONSES = [
    "Hi there! 👋 I'm your travel buddy. I can help you find flights, book hotels, or suggest destinations. What would you like to do?",
    "Hello! Looking to fly somewhere or book a hotel? Just tell me where and when.",
    "Namaste! 🙏 Where would you like to travel today?",
]

HELP_TEXT = (
    "Here's what I can do for you:\n"
    "• Search flights — <em>flights from Delhi to Mumbai tomorrow</em>\n"
    "• Find hotels — <em>hotels in Goa for 3 nights, 4 stars</em>\n"
    "• Recommend destinations — <em>where should I go next weekend?</em>\n"
    "• Show your bookings — <em>my bookings</em>\n"
    "• Check promo codes — <em>any offers?</em>\n"
    "• Loyalty points — <em>how many points do I have?</em>\n"
    "• Wishlist — <em>show my wishlist</em>"
)

RECOMMENDATIONS = [
    {'name': 'Goa', 'tagline': 'Beaches, sunsets and seafood. ⛱️'},
    {'name': 'Manali', 'tagline': 'Snowy peaks and pine forests. ❄️'},
    {'name': 'Jaipur', 'tagline': 'Forts, palaces and royal heritage. 🏰'},
    {'name': 'Kerala', 'tagline': 'Backwaters and houseboats. 🛶'},
    {'name': 'Udaipur', 'tagline': 'The City of Lakes. 🛥️'},
    {'name': 'Andaman', 'tagline': 'Crystal beaches and coral reefs. 🐠'},
]


def _handle_search_flight(request, nlu, session):
    qs = Flight.objects.filter(is_active=True, seats_available__gt=0)
    e = nlu.entities

    if e.get('origin'):
        qs = qs.filter(origin__icontains=e['origin'])
    if e.get('destination'):
        qs = qs.filter(destination__icontains=e['destination'])
    if e.get('departure_date'):
        try:
            d = datetime.fromisoformat(e['departure_date']).date()
            qs = qs.filter(departure_time__date=d)
        except Exception:
            pass
    if e.get('cabin_class'):
        qs = qs.filter(cabin_class=e['cabin_class'])
    if e.get('budget'):
        qs = qs.filter(price__lte=e['budget'])

    qs = qs.order_by('price', 'departure_time')[:5]
    cards = [_format_flight_card(f) for f in qs]

    if not cards:
        text = ("I couldn't find any flights matching that. Try different cities or dates, "
                "or use the full Flights page below.")
    else:
        bits = []
        if e.get('origin'):
            bits.append(f"from <b>{escape(e['origin'])}</b>")
        if e.get('destination'):
            bits.append(f"to <b>{escape(e['destination'])}</b>")
        if e.get('departure_date'):
            bits.append(f"on <b>{escape(e['departure_date'])}</b>")
        prefix = "Here are the top flights " + " ".join(bits) if bits else "Here are some flights"
        text = f"{prefix}. Tap a card to book."

    params = {}
    if e.get('origin'):
        params['origin'] = e['origin']
    if e.get('destination'):
        params['destination'] = e['destination']
    if e.get('departure_date'):
        params['departure_date'] = e['departure_date']
    if e.get('cabin_class'):
        params['cabin_class'] = e['cabin_class']
    search_url = reverse('booking:flight_search') + ('?' + urlencode(params) if params else '')

    actions = [{'label': '🔎 Open full flight search', 'url': search_url}]
    return text, cards, actions


def _handle_search_hotel(request, nlu, session):
    qs = Hotel.objects.filter(is_active=True, rooms_available__gt=0)
    e = nlu.entities

    city = e.get('city') or e.get('destination')
    if city:
        qs = qs.filter(city__icontains=city)
    if e.get('min_stars'):
        qs = qs.filter(star_rating__gte=e['min_stars'])
    if e.get('budget'):
        qs = qs.filter(price_per_night__lte=e['budget'])

    qs = qs.order_by('-star_rating', 'price_per_night')[:5]
    cards = [_format_hotel_card(h) for h in qs]

    if not cards:
        text = ("I couldn't find hotels matching those filters. Try a different city, "
                "or relax the budget/star rating.")
    else:
        bits = []
        if city:
            bits.append(f"in <b>{escape(city)}</b>")
        if e.get('min_stars'):
            bits.append(f"with <b>{e['min_stars']}★</b> or above")
        prefix = "Here are top hotels " + " ".join(bits) if bits else "Here are some hotels"
        text = f"{prefix}. Tap a card to book."

    params = {}
    if city:
        params['city'] = city
    if e.get('min_stars'):
        params['min_stars'] = e['min_stars']
    if e.get('departure_date'):
        params['check_in'] = e['departure_date']
    if e.get('return_date'):
        params['check_out'] = e['return_date']
    search_url = reverse('booking:hotel_search') + ('?' + urlencode(params) if params else '')

    actions = [{'label': '🏨 Open full hotel search', 'url': search_url}]
    return text, cards, actions


def _handle_show_bookings(request, nlu, session):
    if not request.user.is_authenticated:
        return ("You'll need to log in first to see your bookings.",
                [], [{'label': 'Login', 'url': reverse('accounts:login')}])

    bookings = request.user.bookings.all()[:5]
    if not bookings:
        return ("You don't have any bookings yet. Want me to find a flight or hotel?",
                [], [
                    {'label': '✈️ Flights', 'url': reverse('booking:flight_search')},
                    {'label': '🏨 Hotels', 'url': reverse('booking:hotel_search')},
                ])

    lines = ["Here are your latest bookings:"]
    for b in bookings:
        lines.append(
            f"• <b>{b.reference}</b> — {b.title} "
            f"({b.get_status_display()}) — ₹{b.total_amount}"
        )
    return ("\n".join(lines), [],
            [{'label': '📜 View full history', 'url': reverse('booking:history')}])


def _handle_recommend(request, nlu, session):
    picks = random.sample(RECOMMENDATIONS, 3)
    text = "Here are a few destinations I love:\n" + "\n".join(
        f"• <b>{p['name']}</b> — {p['tagline']}" for p in picks
    )
    actions = []
    for p in picks:
        actions.append({
            'label': f"Hotels in {p['name']}",
            'url': reverse('booking:hotel_search') + f"?city={p['name']}",
        })
    return text, [], actions


def _handle_help(request, nlu, session):
    return HELP_TEXT, [], [
        {'label': '✈️ Search flights', 'url': reverse('booking:flight_search')},
        {'label': '🏨 Search hotels', 'url': reverse('booking:hotel_search')},
    ]


def _handle_greet(request, nlu, session):
    name = request.user.first_name if request.user.is_authenticated else None
    msg = random.choice(GREETING_RESPONSES)
    if name:
        msg = f"Hi {name}! " + msg.split(' ', 1)[1]
    return msg, [], [
        {'label': '✈️ Find a flight', 'url': reverse('booking:flight_search')},
        {'label': '🏨 Find a hotel', 'url': reverse('booking:hotel_search')},
    ]


def _handle_thanks(request, nlu, session):
    return "You're welcome! Anything else I can help you with?", [], []


def _handle_goodbye(request, nlu, session):
    return "Safe travels! ✈️ Come back anytime.", [], []


def _handle_cancel(request, nlu, session):
    if not request.user.is_authenticated:
        return ("Please log in to manage your bookings.", [],
                [{'label': 'Login', 'url': reverse('accounts:login')}])
    return ("You can cancel a booking from your booking history page.",
            [], [{'label': '📜 My Bookings', 'url': reverse('booking:history')}])


def _handle_promo(request, nlu, session):
    coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now(),
    )[:5]
    if not coupons:
        return ("There are no active promo codes right now. Check back soon!",
                [], [])
    lines = ["🎟️ Here are the active offers:"]
    for c in coupons:
        lines.append(f"• <b>{c.code}</b> — {c.label} ({c.get_applies_to_display()}) · "
                     f"valid till {c.valid_to.strftime('%d %b')}")
    return ("\n".join(lines), [], [
        {'label': '🏨 Find hotels', 'url': reverse('booking:hotel_search')},
        {'label': '✈️ Find flights', 'url': reverse('booking:flight_search')},
    ])


def _handle_loyalty(request, nlu, session):
    if not request.user.is_authenticated:
        return ("Sign in to see your loyalty points and tier.", [],
                [{'label': 'Login', 'url': reverse('accounts:login')}])
    p = request.user.profile
    tier_name, tier_icon, _ = p.tier
    msg = (f"{tier_icon} You're a <b>{tier_name}</b> member with "
           f"<b>{p.loyalty_points}</b> loyalty points. "
           f"That's <b>₹{p.loyalty_points}</b> off your next booking! "
           f"Refer friends with code <code>{p.referral_code}</code>.")
    return msg, [], [{'label': '⭐ View loyalty', 'url': reverse('booking:loyalty')}]


def _handle_wishlist(request, nlu, session):
    if not request.user.is_authenticated:
        return ("Please log in to use your wishlist.", [],
                [{'label': 'Login', 'url': reverse('accounts:login')}])
    count = WishlistItem.objects.filter(user=request.user).count()
    if count == 0:
        return ("Your wishlist is empty. Tap the heart on any hotel or flight to save it!",
                [], [{'label': '🏨 Browse hotels', 'url': reverse('booking:hotel_search')}])
    return (f"You have <b>{count}</b> item(s) on your wishlist.",
            [], [{'label': '❤️ Open wishlist', 'url': reverse('booking:wishlist')}])


def _handle_fallback(request, nlu, session):
    return ("I'm not totally sure I got that. " + HELP_TEXT, [],
            [
                {'label': '✈️ Search flights', 'url': reverse('booking:flight_search')},
                {'label': '🏨 Search hotels', 'url': reverse('booking:hotel_search')},
            ])


HANDLERS = {
    'greet': _handle_greet,
    'thanks': _handle_thanks,
    'goodbye': _handle_goodbye,
    'help': _handle_help,
    'recommend': _handle_recommend,
    'show_bookings': _handle_show_bookings,
    'search_flight': _handle_search_flight,
    'search_hotel': _handle_search_hotel,
    'cancel': _handle_cancel,
    'promo': _handle_promo,
    'loyalty': _handle_loyalty,
    'wishlist': _handle_wishlist,
    'fallback': _handle_fallback,
}


# ---------- API ----------

@ensure_csrf_cookie
def chat_widget_partial(request):
    return render(request, 'chatbot/widget.html')


@require_POST
def chat_api(request):
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    text = (payload.get('message') or '').strip()
    if not text:
        return JsonResponse({'error': 'Empty message'}, status=400)

    session = _get_or_create_session(request)
    nlu = parse(text)

    ChatMessage.objects.create(
        session=session, sender='user',
        message=text, intent=nlu.intent, entities=nlu.entities,
    )

    handler = HANDLERS.get(nlu.intent, _handle_fallback)
    reply_text, cards, actions = handler(request, nlu, session)

    ChatMessage.objects.create(
        session=session, sender='bot',
        message=reply_text, intent=nlu.intent,
        entities={'cards': len(cards), 'actions': len(actions)},
    )

    # update context
    session.context.update(nlu.entities)
    session.save(update_fields=['context', 'last_activity'])

    return JsonResponse({
        'intent': nlu.intent,
        'confidence': nlu.confidence,
        'entities': nlu.entities,
        'reply': reply_text,
        'cards': cards,
        'actions': actions,
    })


@login_required
def chat_history(request):
    session = _get_or_create_session(request)
    msgs = list(session.messages.order_by('timestamp').values(
        'sender', 'message', 'intent', 'timestamp'))
    return JsonResponse({'messages': msgs})
