from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    FlightSearchForm, HotelSearchForm, PaymentForm,
    HotelReviewForm, ContactForm,
)
from .models import (
    Flight, Hotel, Booking, Payment, Coupon, HotelReview,
    WishlistItem, Notification, NewsletterSubscriber, ContactMessage,
    INSURANCE_RATE,
)
from .pdf_utils import generate_ticket_pdf


# =====================================================
#  Public pages
# =====================================================
def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('dashboard:overview')

    popular_destinations = [
        {'name': 'Goa', 'image': 'https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=600',
         'tagline': 'Beaches & Nightlife'},
        {'name': 'Manali', 'image': 'https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=600',
         'tagline': 'Snowy Himalayas'},
        {'name': 'Jaipur', 'image': 'https://images.unsplash.com/photo-1599661046289-e31897846e41?w=600',
         'tagline': 'The Pink City'},
        {'name': 'Mumbai', 'image': 'https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=600',
         'tagline': 'City of Dreams'},
        {'name': 'Bengaluru', 'image': 'https://images.unsplash.com/photo-1596176530529-78163a4f7af2?w=600',
         'tagline': 'Garden City'},
        {'name': 'Kolkata', 'image': 'https://images.unsplash.com/photo-1558431382-27e303142255?w=600',
         'tagline': 'City of Joy'},
    ]

    active_offers = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now(),
    )[:3]

    return render(request, 'booking/home.html', {
        'flight_form': FlightSearchForm(),
        'hotel_form': HotelSearchForm(),
        'destinations': popular_destinations,
        'offers': active_offers,
        'currencies': [
            ('INR', '₹', 1.0),
            ('USD', '$', 0.012),
            ('EUR', '€', 0.011),
            ('GBP', '£', 0.0094),
            ('AED', 'AED ', 0.044),
            ('SGD', 'S$ ', 0.016),
        ],
    })


def about(request):
    stats = {
        'users': sum(1 for _ in range(0)) + 50000,
        'bookings': 120000,
        'destinations': 50,
        'partners': 200,
    }
    return render(request, 'booking/about.html', {'stats': stats})


def faq(request):
    faqs = [
        ('How do I book a flight?',
         "Use the search bar on the homepage, pick your flight from the results, "
         "and follow the booking and payment steps. You can also just chat with TravelBot!"),
        ('How does the AI chatbot work?',
         "Our chatbot understands natural language using NLP. Try: "
         "'flights from Delhi to Goa tomorrow' or 'hotels in Manali, 4 stars, under ₹5000'."),
        ('What payment methods are accepted?',
         "Credit/debit cards, UPI, net banking and digital wallets. Note: this is a demo, "
         "so no real money is charged."),
        ('Can I cancel my booking?',
         "Yes, anytime from the My Bookings page. Confirmed bookings are refunded automatically."),
        ('How do loyalty points work?',
         "Earn 1 point for every ₹100 you spend on confirmed bookings. Redeem 1 point = ₹1 off at checkout."),
        ('Can I download my e-ticket?',
         "Yes. After a confirmed booking, click the Download PDF button on your confirmation page."),
        ('Is the payment secure?',
         "All payment data is processed via SSL. We don't store card numbers, only the last 4 digits."),
        ('How do promo codes work?',
         "Enter a valid promo code on the payment page to instantly see the discount applied."),
        ('Can I leave a hotel review?',
         "Yes, after a confirmed hotel booking you can leave a 1-5 star review on the hotel's page."),
    ]
    return render(request, 'booking/faq.html', {'faqs': faqs})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        msg = form.save()
        messages.success(request,
            f"Thanks {msg.name}! Your message has been sent. We'll get back to you soon.")
        return redirect('booking:contact')
    return render(request, 'booking/contact.html', {'form': form})


# =====================================================
#  Flights
# =====================================================
def flight_search(request):
    form = FlightSearchForm(request.GET or None)
    flights = Flight.objects.filter(is_active=True, seats_available__gt=0)

    if form.is_valid():
        d = form.cleaned_data
        if d.get('origin'):
            flights = flights.filter(
                Q(origin__icontains=d['origin']) | Q(origin_code__iexact=d['origin'])
            )
        if d.get('destination'):
            flights = flights.filter(
                Q(destination__icontains=d['destination']) | Q(destination_code__iexact=d['destination'])
            )
        if d.get('departure_date'):
            flights = flights.filter(departure_time__date=d['departure_date'])
        if d.get('cabin_class'):
            flights = flights.filter(cabin_class=d['cabin_class'])

    flights = flights.order_by('departure_time', 'price')[:50]

    wishlisted = set()
    if request.user.is_authenticated:
        wishlisted = set(WishlistItem.objects.filter(
            user=request.user, item_type='flight',
        ).values_list('flight_id', flat=True))

    return render(request, 'booking/flight_results.html', {
        'form': form,
        'flights': flights,
        'count': len(flights),
        'wishlisted_ids': wishlisted,
    })


@login_required
def flight_book(request, pk):
    flight = get_object_or_404(Flight, pk=pk, is_active=True)
    passengers = max(int(request.POST.get('passengers') or request.GET.get('passengers') or 1), 1)

    if flight.seats_available < passengers:
        messages.error(request, "Not enough seats available for this flight.")
        return redirect('booking:flight_search')

    if request.method == 'POST':
        subtotal = flight.price * passengers
        with transaction.atomic():
            booking = Booking.objects.create(
                user=request.user,
                booking_type='flight',
                flight=flight,
                passengers=passengers,
                subtotal=subtotal,
                total_amount=subtotal,
                status='pending',
            )
        return redirect('booking:payment', reference=booking.reference)

    return render(request, 'booking/flight_book.html', {
        'flight': flight,
        'passengers': passengers,
        'total': flight.price * passengers,
    })


# =====================================================
#  Hotels
# =====================================================
def hotel_search(request):
    form = HotelSearchForm(request.GET or None)
    hotels = Hotel.objects.filter(is_active=True, rooms_available__gt=0)

    nights = 1
    if form.is_valid():
        d = form.cleaned_data
        if d.get('city'):
            hotels = hotels.filter(city__icontains=d['city'])
        if d.get('min_stars'):
            hotels = hotels.filter(star_rating__gte=d['min_stars'])
        if d.get('check_in') and d.get('check_out'):
            nights = max((d['check_out'] - d['check_in']).days, 1)

    hotels = hotels.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews'),
    ).order_by('-star_rating', 'price_per_night')[:50]

    wishlisted = set()
    if request.user.is_authenticated:
        wishlisted = set(WishlistItem.objects.filter(
            user=request.user, item_type='hotel',
        ).values_list('hotel_id', flat=True))

    return render(request, 'booking/hotel_results.html', {
        'form': form,
        'hotels': hotels,
        'nights': nights,
        'count': len(hotels),
        'wishlisted_ids': wishlisted,
    })


def hotel_map(request):
    """Browse hotels on a Google Map — pick a city and see all hotels there."""
    city = request.GET.get('city', '').strip()
    qs = Hotel.objects.filter(is_active=True)
    if city:
        qs = qs.filter(city__icontains=city)
    hotels = qs.order_by('-star_rating', 'price_per_night')[:60]

    cities = (Hotel.objects.filter(is_active=True)
              .values_list('city', flat=True).distinct().order_by('city'))

    # Compose a map query for the *first* hotel (or the city itself)
    if hotels:
        focus = hotels[0].map_query
    elif city:
        focus = f"{city}, India"
    else:
        focus = "India"

    from urllib.parse import quote_plus
    embed_url = (f"https://maps.google.com/maps?q={quote_plus(focus)}"
                 f"&z={'12' if city else '5'}&output=embed")

    return render(request, 'booking/hotel_map.html', {
        'hotels': hotels,
        'cities': cities,
        'city': city,
        'embed_url': embed_url,
    })


def hotel_detail(request, pk):
    """Hotel detail page with reviews."""
    hotel = get_object_or_404(Hotel, pk=pk, is_active=True)
    reviews = hotel.reviews.select_related('user')
    stats = reviews.aggregate(avg=Avg('rating'), n=Count('id'))

    user_review = None
    can_review = False
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        # Only customers with a confirmed hotel booking can post a review.
        can_review = (
            user_review is None and
            Booking.objects.filter(
                user=request.user, hotel=hotel, status__in=['confirmed', 'completed']
            ).exists()
        )

    distribution = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}
    total = stats['n'] or 0
    pct = {k: round((v / total) * 100) if total else 0 for k, v in distribution.items()}

    return render(request, 'booking/hotel_detail.html', {
        'hotel': hotel,
        'reviews': reviews[:20],
        'avg_rating': stats['avg'] or 0,
        'review_count': stats['n'] or 0,
        'distribution': distribution,
        'pct': pct,
        'can_review': can_review,
        'user_review': user_review,
        'review_form': HotelReviewForm(),
        'wishlisted': WishlistItem.objects.filter(
            user=request.user, item_type='hotel', hotel=hotel,
        ).exists() if request.user.is_authenticated else False,
    })


@login_required
def hotel_book(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk, is_active=True)
    today = timezone.localdate()

    check_in_str = request.POST.get('check_in') or request.GET.get('check_in')
    check_out_str = request.POST.get('check_out') or request.GET.get('check_out')
    rooms = max(int(request.POST.get('rooms') or request.GET.get('rooms') or 1), 1)
    guests = max(int(request.POST.get('guests') or request.GET.get('guests') or 1), 1)

    try:
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date() if check_in_str else today
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date() if check_out_str \
            else today + timedelta(days=2)
    except ValueError:
        return HttpResponseBadRequest("Invalid date format.")

    if check_out <= check_in:
        check_out = check_in + timedelta(days=1)

    nights = (check_out - check_in).days
    total = hotel.price_per_night * rooms * nights

    if request.method == 'POST':
        if hotel.rooms_available < rooms:
            messages.error(request, "Not enough rooms available.")
            return redirect('booking:hotel_search')
        with transaction.atomic():
            booking = Booking.objects.create(
                user=request.user,
                booking_type='hotel',
                hotel=hotel,
                check_in=check_in,
                check_out=check_out,
                rooms=rooms,
                guests=guests,
                subtotal=total,
                total_amount=total,
                status='pending',
            )
        return redirect('booking:payment', reference=booking.reference)

    return render(request, 'booking/hotel_book.html', {
        'hotel': hotel,
        'check_in': check_in,
        'check_out': check_out,
        'rooms': rooms,
        'guests': guests,
        'nights': nights,
        'total': total,
    })


# =====================================================
#  Reviews
# =====================================================
@login_required
@require_POST
def hotel_review_add(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    # Verify the user has a confirmed booking for this hotel.
    has_booking = Booking.objects.filter(
        user=request.user, hotel=hotel, status__in=['confirmed', 'completed'],
    ).exists()
    if not has_booking:
        messages.error(request, "You can only review hotels you've booked.")
        return redirect('booking:hotel_detail', pk=pk)

    if HotelReview.objects.filter(user=request.user, hotel=hotel).exists():
        messages.warning(request, "You already submitted a review for this hotel.")
        return redirect('booking:hotel_detail', pk=pk)

    form = HotelReviewForm(request.POST)
    if form.is_valid():
        r = form.save(commit=False)
        r.user = request.user
        r.hotel = hotel
        r.is_verified = True
        r.save()
        messages.success(request, "Thanks for sharing your experience!")
    else:
        messages.error(request, "Please fix the errors in your review and try again.")
    return redirect('booking:hotel_detail', pk=pk)


# =====================================================
#  Wishlist
# =====================================================
@login_required
@require_POST
def wishlist_toggle(request, item_type, pk):
    if item_type not in ('flight', 'hotel'):
        return JsonResponse({'error': 'Invalid type'}, status=400)

    if item_type == 'flight':
        f = get_object_or_404(Flight, pk=pk)
        item, created = WishlistItem.objects.get_or_create(
            user=request.user, item_type='flight', flight=f)
    else:
        h = get_object_or_404(Hotel, pk=pk)
        item, created = WishlistItem.objects.get_or_create(
            user=request.user, item_type='hotel', hotel=h)

    if not created:
        item.delete()
        added = False
    else:
        added = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' \
            or request.content_type == 'application/json':
        return JsonResponse({'added': added})

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('booking:home')
    messages.success(request, f"{'Added to' if added else 'Removed from'} your wishlist.")
    return redirect(next_url)


@login_required
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user)\
        .select_related('flight', 'hotel')
    return render(request, 'booking/wishlist.html', {'items': items})


# =====================================================
#  Coupon / Promo
# =====================================================
@login_required
@require_POST
def coupon_apply(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.status == 'confirmed':
        return JsonResponse({'ok': False, 'error': 'Booking already confirmed.'})

    code = (request.POST.get('code') or '').strip().upper()
    if not code:
        return JsonResponse({'ok': False, 'error': 'Please enter a code.'})

    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Invalid promo code.'})

    ok, reason = coupon.is_valid(
        booking_type=booking.booking_type,
        amount=booking.subtotal,
    )
    if not ok:
        return JsonResponse({'ok': False, 'error': reason})

    discount = coupon.compute_discount(booking.subtotal)
    booking.coupon_code = coupon.code
    booking.discount_amount = discount
    _recalculate_total(booking)
    booking.save()

    return JsonResponse({
        'ok': True,
        'code': coupon.code,
        'discount': float(discount),
        'subtotal': float(booking.subtotal),
        'insurance': float(booking.insurance_amount),
        'loyalty_redeemed': booking.loyalty_points_redeemed,
        'total': float(booking.total_amount),
        'message': f"Coupon applied: {coupon.label}",
    })


@login_required
@require_POST
def coupon_remove(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    booking.coupon_code = ''
    booking.discount_amount = Decimal('0.00')
    _recalculate_total(booking)
    booking.save()
    return JsonResponse({
        'ok': True,
        'subtotal': float(booking.subtotal),
        'discount': 0,
        'insurance': float(booking.insurance_amount),
        'loyalty_redeemed': booking.loyalty_points_redeemed,
        'total': float(booking.total_amount),
    })


# =====================================================
#  Insurance / Loyalty
# =====================================================
@login_required
@require_POST
def insurance_toggle(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    booking.has_insurance = (request.POST.get('on') == '1')
    if booking.has_insurance:
        booking.insurance_amount = (booking.subtotal * INSURANCE_RATE).quantize(Decimal('0.01'))
    else:
        booking.insurance_amount = Decimal('0.00')
    _recalculate_total(booking)
    booking.save()
    return JsonResponse({
        'ok': True,
        'on': booking.has_insurance,
        'insurance': float(booking.insurance_amount),
        'total': float(booking.total_amount),
    })


@login_required
@require_POST
def loyalty_apply(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    available = request.user.profile.loyalty_points
    try:
        pts = int(request.POST.get('points') or 0)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid number of points.'})
    pts = max(0, min(pts, available))

    # Don't allow redemption to exceed (subtotal - discount + insurance)
    max_redeemable_amount = booking.subtotal - booking.discount_amount + booking.insurance_amount
    pts = min(pts, int(max_redeemable_amount))

    booking.loyalty_points_redeemed = pts
    _recalculate_total(booking)
    booking.save()
    return JsonResponse({
        'ok': True,
        'redeemed': pts,
        'available': available,
        'total': float(booking.total_amount),
    })


def _recalculate_total(booking: Booking):
    """Re-derive total = subtotal - discount + insurance - loyalty_redeemed."""
    sub = booking.subtotal or Decimal('0.00')
    disc = booking.discount_amount or Decimal('0.00')
    ins = booking.insurance_amount or Decimal('0.00')
    redeem = Decimal(booking.loyalty_points_redeemed or 0)
    total = sub - disc + ins - redeem
    if total < 0:
        total = Decimal('0.00')
    booking.total_amount = total.quantize(Decimal('0.01'))


# =====================================================
#  Payment
# =====================================================
@login_required
def payment(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)

    if booking.status == 'confirmed':
        return redirect('booking:confirmation', reference=booking.reference)

    # Ensure subtotal exists (compatibility with old data)
    if not booking.subtotal:
        booking.subtotal = booking.total_amount
        booking.save(update_fields=['subtotal'])

    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            pay, _ = Payment.objects.get_or_create(
                booking=booking,
                defaults={'method': form.cleaned_data['method'],
                          'amount': booking.total_amount,
                          'card_last4': form.cleaned_data.get('card_last4', '')},
            )
            pay.method = form.cleaned_data['method']
            pay.amount = booking.total_amount
            pay.card_last4 = form.cleaned_data.get('card_last4', '')
            pay.mark_success()

            # Loyalty math: earn 1 pt per ₹100 spent, deduct redeemed pts.
            profile = request.user.profile
            if booking.loyalty_points_redeemed:
                profile.loyalty_points = max(0, profile.loyalty_points - booking.loyalty_points_redeemed)
            earned = int(booking.total_amount // 100)
            booking.loyalty_points_earned = earned
            profile.loyalty_points += earned
            profile.save(update_fields=['loyalty_points'])

            # Bump coupon usage count
            if booking.coupon_code:
                Coupon.objects.filter(code__iexact=booking.coupon_code).update(
                    used_count=Coupon.objects.get(code__iexact=booking.coupon_code).used_count + 1
                )

            booking.status = 'confirmed'
            booking.save()

            # Decrement inventory
            if booking.booking_type == 'flight' and booking.flight:
                Flight.objects.filter(pk=booking.flight_id).update(
                    seats_available=max(booking.flight.seats_available - booking.passengers, 0)
                )
            elif booking.booking_type == 'hotel' and booking.hotel:
                Hotel.objects.filter(pk=booking.hotel_id).update(
                    rooms_available=max(booking.hotel.rooms_available - booking.rooms, 0)
                )

            # Send a notification to the user
            Notification.objects.create(
                user=request.user, type='booking', icon='✅',
                title=f"Booking confirmed: {booking.reference}",
                message=f"Your {booking.get_booking_type_display().lower()} booking is confirmed. "
                        f"You earned {earned} loyalty points!",
                link=reverse('booking:confirmation', args=[booking.reference]),
            )

        messages.success(request, "Payment successful! Your booking is confirmed.")
        return redirect('booking:confirmation', reference=booking.reference)

    return render(request, 'booking/payment.html', {
        'booking': booking,
        'form': form,
        'available_points': request.user.profile.loyalty_points,
        'insurance_rate_pct': int(INSURANCE_RATE * 100),
    })


@login_required
def confirmation(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    return render(request, 'booking/confirmation.html', {'booking': booking})


@login_required
def ticket_pdf(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.status not in ('confirmed', 'completed'):
        messages.warning(request, "Only confirmed bookings have e-tickets.")
        return redirect('booking:confirmation', reference=reference)
    pdf_bytes = generate_ticket_pdf(booking)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{booking.reference}.pdf"'
    return response


# =====================================================
#  History / Cancel
# =====================================================
@login_required
def booking_history(request):
    bookings = request.user.bookings.all()
    flight_bookings = bookings.filter(booking_type='flight')
    hotel_bookings = bookings.filter(booking_type='hotel')
    return render(request, 'booking/history.html', {
        'bookings': bookings,
        'flight_count': flight_bookings.count(),
        'hotel_count': hotel_bookings.count(),
        'total_spent': bookings.filter(status='confirmed').aggregate(s=Sum('total_amount'))['s'] or 0,
        'total_points': request.user.profile.loyalty_points,
    })


@login_required
def booking_cancel(request, reference):
    booking = get_object_or_404(Booking, reference=reference, user=request.user)
    if booking.status in ('confirmed', 'pending'):
        with transaction.atomic():
            if booking.status == 'confirmed':
                if booking.booking_type == 'flight' and booking.flight:
                    Flight.objects.filter(pk=booking.flight_id).update(
                        seats_available=booking.flight.seats_available + booking.passengers
                    )
                elif booking.booking_type == 'hotel' and booking.hotel:
                    Hotel.objects.filter(pk=booking.hotel_id).update(
                        rooms_available=booking.hotel.rooms_available + booking.rooms
                    )
                if hasattr(booking, 'payment'):
                    booking.payment.status = 'refunded'
                    booking.payment.save()
                # Roll back loyalty points
                profile = request.user.profile
                profile.loyalty_points = max(0, profile.loyalty_points - booking.loyalty_points_earned)
                if booking.loyalty_points_redeemed:
                    profile.loyalty_points += booking.loyalty_points_redeemed
                profile.save(update_fields=['loyalty_points'])
            booking.status = 'cancelled'
            booking.save()
            Notification.objects.create(
                user=request.user, type='booking', icon='❌',
                title=f"Booking cancelled: {booking.reference}",
                message="Your booking has been cancelled and any refund processed.",
                link=reverse('booking:history'),
            )
        messages.info(request, f"Booking {booking.reference} has been cancelled.")
    return redirect('booking:history')


# =====================================================
#  Loyalty page
# =====================================================
@login_required
def loyalty(request):
    p = request.user.profile
    tier_name, tier_icon, tier_class = p.tier
    next_tiers = {'Bronze': ('Silver', 500), 'Silver': ('Gold', 2000),
                  'Gold': ('Platinum', 5000), 'Platinum': ('Platinum', 0)}
    next_tier, next_required = next_tiers.get(tier_name, ('Platinum', 0))
    return render(request, 'booking/loyalty.html', {
        'points': p.loyalty_points,
        'tier_name': tier_name,
        'tier_icon': tier_icon,
        'tier_class': tier_class,
        'next_tier': next_tier,
        'next_required': next_required,
        'progress_pct': min(100, int((p.loyalty_points / next_required) * 100)) if next_required else 100,
        'referral_code': p.referral_code,
        'recent_history': request.user.bookings.filter(status='confirmed')[:10],
    })


# =====================================================
#  Notifications
# =====================================================
@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER') or 'booking:home')


@login_required
def notifications_list(request):
    items = Notification.objects.filter(user=request.user)[:50]
    return render(request, 'booking/notifications.html', {'items': items})


# =====================================================
#  Newsletter
# =====================================================
def newsletter_subscribe(request):
    if request.method != 'POST':
        return redirect('booking:home')
    email = (request.POST.get('email') or '').strip().lower()
    if not email or '@' not in email:
        messages.error(request, "Please enter a valid email address.")
        return redirect(request.META.get('HTTP_REFERER') or 'booking:home')

    sub, created = NewsletterSubscriber.objects.get_or_create(
        email=email,
        defaults={
            'user': request.user if request.user.is_authenticated else None,
            'is_active': True,
        },
    )
    if not created and not sub.is_active:
        sub.is_active = True
        sub.save()
    if request.user.is_authenticated:
        request.user.profile.newsletter_subscribed = True
        request.user.profile.save(update_fields=['newsletter_subscribed'])

    messages.success(request, "Thanks! You're subscribed to TravelBot updates.")
    return redirect(request.META.get('HTTP_REFERER') or 'booking:home')
