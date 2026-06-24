"""Admin dashboard: overview, CRUD for flights/hotels/users/bookings, reports."""
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from booking.models import (
    Flight, Hotel, Booking, Payment, Coupon, HotelReview,
    Notification, NewsletterSubscriber, ContactMessage,
)
from chatbot.models import ChatSession, ChatMessage
from .forms import FlightAdminForm, HotelAdminForm, CouponAdminForm


# =============================================================
#  Overview / Reports
# =============================================================
@staff_member_required
def overview(request):
    today = timezone.localdate()
    last_7 = [today - timedelta(days=i) for i in range(6, -1, -1)]

    bookings_per_day = (
        Booking.objects.filter(created_at__date__gte=last_7[0])
        .annotate(d=TruncDate('created_at'))
        .values('d').annotate(c=Count('id'))
    )
    by_day = {b['d']: b['c'] for b in bookings_per_day}
    chart_labels = [d.strftime('%d %b') for d in last_7]
    chart_values = [by_day.get(d, 0) for d in last_7]

    revenue = (Booking.objects.filter(status='confirmed')
               .aggregate(total=Sum('total_amount'))['total'] or 0)

    context = {
        'total_users': User.objects.filter(is_staff=False).count(),
        'total_flights': Flight.objects.count(),
        'total_hotels': Hotel.objects.count(),
        'total_bookings': Booking.objects.count(),
        'confirmed_bookings': Booking.objects.filter(status='confirmed').count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'cancelled_bookings': Booking.objects.filter(status='cancelled').count(),
        'flight_bookings': Booking.objects.filter(booking_type='flight').count(),
        'hotel_bookings': Booking.objects.filter(booking_type='hotel').count(),
        'total_revenue': revenue,
        'chat_sessions': ChatSession.objects.count(),
        'chat_messages': ChatMessage.objects.count(),
        'recent_bookings': (Booking.objects
                            .select_related('user', 'flight', 'hotel')[:8]),
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'top_routes': (Flight.objects.values('origin', 'destination')
                       .annotate(c=Count('booking')).order_by('-c')[:5]),
        'top_hotels': (Hotel.objects.annotate(c=Count('booking'))
                       .order_by('-c', '-star_rating')[:5]),
        'newsletter_count': NewsletterSubscriber.objects.filter(is_active=True).count(),
        'open_messages': ContactMessage.objects.filter(is_resolved=False).count(),
        'review_count': HotelReview.objects.count(),
        'avg_review': HotelReview.objects.aggregate(a=Avg('rating'))['a'] or 0,
    }
    return render(request, 'dashboard/overview.html', context)


@staff_member_required
def reports(request):
    revenue_by_type = (Booking.objects.filter(status='confirmed')
                       .values('booking_type')
                       .annotate(total=Sum('total_amount'), n=Count('id')))
    avg_booking = (Booking.objects.filter(status='confirmed')
                   .aggregate(a=Avg('total_amount'))['a'] or 0)
    top_users = (User.objects.filter(is_staff=False)
                 .annotate(spent=Sum('bookings__total_amount',
                                     filter=Q(bookings__status='confirmed')))
                 .filter(spent__gt=0).order_by('-spent')[:10])

    # Revenue trend last 30 days
    today = timezone.localdate()
    last_30 = [today - timedelta(days=i) for i in range(29, -1, -1)]
    rev_qs = (Booking.objects.filter(status='confirmed', created_at__date__gte=last_30[0])
              .annotate(d=TruncDate('created_at'))
              .values('d').annotate(t=Sum('total_amount')))
    by_day = {x['d']: float(x['t'] or 0) for x in rev_qs}
    trend_labels = [d.strftime('%d %b') for d in last_30]
    trend_values = [by_day.get(d, 0) for d in last_30]

    return render(request, 'dashboard/reports.html', {
        'revenue_by_type': revenue_by_type,
        'avg_booking': avg_booking,
        'top_users': top_users,
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'total_coupons_used': Coupon.objects.aggregate(s=Sum('used_count'))['s'] or 0,
        'active_coupons': Coupon.objects.filter(is_active=True).count(),
    })


# =============================================================
#  USERS — list / edit / delete
# =============================================================
@staff_member_required
def users_list(request):
    q = request.GET.get('q', '').strip()
    users = User.objects.annotate(booking_count=Count('bookings'))
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(email__icontains=q)
            | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    users = users.order_by('-date_joined')
    return render(request, 'dashboard/users.html', {'users': users, 'q': q})


@staff_member_required
def user_detail(request, pk):
    """View a user's profile (admin POV) without acting as them."""
    u = get_object_or_404(User, pk=pk)
    bookings = u.bookings.select_related('flight', 'hotel')[:30]
    return render(request, 'dashboard/user_detail.html', {
        'u': u, 'bookings': bookings,
        'total_spent': u.bookings.filter(status='confirmed')
                        .aggregate(s=Sum('total_amount'))['s'] or 0,
    })


@staff_member_required
def user_toggle(request, pk, action):
    if request.method != 'POST':
        return redirect('dashboard:users')
    u = get_object_or_404(User, pk=pk)
    if u == request.user:
        messages.warning(request, "You can't modify your own account from here.")
        return redirect('dashboard:user_detail', pk=pk)
    if action == 'active':
        u.is_active = not u.is_active
        u.save()
        messages.success(request, f"{u.username} is now {'active' if u.is_active else 'inactive'}.")
    elif action == 'staff':
        u.is_staff = not u.is_staff
        u.save()
        messages.success(request, f"{u.username} staff status: {u.is_staff}.")
    return redirect('dashboard:user_detail', pk=pk)


@staff_member_required
def user_delete(request, pk):
    if request.method != 'POST':
        return redirect('dashboard:users')
    u = get_object_or_404(User, pk=pk)
    if u == request.user:
        messages.error(request, "You cannot delete yourself.")
        return redirect('dashboard:users')
    if u.is_superuser:
        messages.error(request, "Superusers cannot be deleted from this dashboard.")
        return redirect('dashboard:users')
    name = u.username
    u.delete()
    messages.success(request, f"Deleted user '{name}'.")
    return redirect('dashboard:users')


# =============================================================
#  FLIGHTS CRUD
# =============================================================
@staff_member_required
def flights_list(request):
    q = request.GET.get('q', '').strip()
    qs = Flight.objects.all()
    if q:
        qs = qs.filter(
            Q(flight_number__icontains=q) | Q(airline__icontains=q)
            | Q(origin__icontains=q) | Q(destination__icontains=q)
        )
    qs = qs.order_by('-id')[:200]
    return render(request, 'dashboard/flights.html', {'flights': qs, 'q': q})


@staff_member_required
def flight_create(request):
    form = FlightAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Flight created successfully.")
        return redirect('dashboard:flights')
    return render(request, 'dashboard/flight_form.html', {'form': form, 'mode': 'Create'})


@staff_member_required
def flight_edit(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    form = FlightAdminForm(request.POST or None, instance=flight)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Flight {flight.flight_number} updated.")
        return redirect('dashboard:flights')
    return render(request, 'dashboard/flight_form.html',
                  {'form': form, 'flight': flight, 'mode': 'Edit'})


@staff_member_required
def flight_delete(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    if request.method == 'POST':
        fn = flight.flight_number
        flight.delete()
        messages.success(request, f"Flight {fn} deleted.")
        return redirect('dashboard:flights')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': flight, 'title': 'flight',
        'back_url': reverse('dashboard:flights'),
    })


# =============================================================
#  HOTELS CRUD
# =============================================================
@staff_member_required
def hotels_list(request):
    q = request.GET.get('q', '').strip()
    qs = Hotel.objects.all()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q))
    qs = qs.order_by('-id')[:200]
    return render(request, 'dashboard/hotels.html', {'hotels': qs, 'q': q})


@staff_member_required
def hotel_create(request):
    form = HotelAdminForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Hotel created successfully.")
        return redirect('dashboard:hotels')
    return render(request, 'dashboard/hotel_form.html', {'form': form, 'mode': 'Create'})


@staff_member_required
def hotel_edit(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    form = HotelAdminForm(request.POST or None, request.FILES or None, instance=hotel)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"{hotel.name} updated.")
        return redirect('dashboard:hotels')
    return render(request, 'dashboard/hotel_form.html',
                  {'form': form, 'hotel': hotel, 'mode': 'Edit'})


@staff_member_required
def hotel_delete(request, pk):
    hotel = get_object_or_404(Hotel, pk=pk)
    if request.method == 'POST':
        name = hotel.name
        hotel.delete()
        messages.success(request, f"Hotel '{name}' deleted.")
        return redirect('dashboard:hotels')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': hotel, 'title': 'hotel',
        'back_url': reverse('dashboard:hotels'),
    })


# =============================================================
#  BOOKINGS — list / status update / delete
# =============================================================
@staff_member_required
def bookings_list(request):
    status = request.GET.get('status', '')
    btype = request.GET.get('type', '')
    q = request.GET.get('q', '').strip()

    bookings = Booking.objects.select_related('user', 'flight', 'hotel', 'payment')
    if status:
        bookings = bookings.filter(status=status)
    if btype:
        bookings = bookings.filter(booking_type=btype)
    if q:
        bookings = bookings.filter(
            Q(reference__icontains=q) | Q(user__username__icontains=q)
            | Q(user__email__icontains=q)
        )
    bookings = bookings.order_by('-created_at')[:200]

    return render(request, 'dashboard/bookings.html', {
        'bookings': bookings, 'status': status, 'type': btype, 'q': q,
    })


@staff_member_required
def booking_update_status(request, reference):
    if request.method != 'POST':
        return redirect('dashboard:bookings')
    booking = get_object_or_404(Booking, reference=reference)
    new_status = request.POST.get('status')
    if new_status in dict(Booking.STATUS_CHOICES):
        booking.status = new_status
        booking.save()
        # Notify the user
        Notification.objects.create(
            user=booking.user, type='booking',
            title=f"Booking {booking.reference} updated",
            message=f"Your booking is now {booking.get_status_display()}.",
            icon='📝',
            link=reverse('booking:confirmation', args=[booking.reference]),
        )
        messages.success(request, f"Updated {booking.reference} → {booking.get_status_display()}.")
    return redirect('dashboard:bookings')


@staff_member_required
def booking_delete(request, reference):
    booking = get_object_or_404(Booking, reference=reference)
    if request.method == 'POST':
        ref = booking.reference
        booking.delete()
        messages.success(request, f"Booking {ref} deleted permanently.")
        return redirect('dashboard:bookings')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': booking, 'title': 'booking',
        'back_url': reverse('dashboard:bookings'),
    })


# =============================================================
#  COUPONS CRUD
# =============================================================
@staff_member_required
def coupons_list(request):
    coupons = Coupon.objects.all()
    return render(request, 'dashboard/coupons.html', {'coupons': coupons})


@staff_member_required
def coupon_create(request):
    form = CouponAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        c = form.save()
        # Broadcast a promo notification to all customers
        for u in User.objects.filter(is_staff=False, is_active=True):
            Notification.objects.create(
                user=u, type='promo', icon='🎟️',
                title=f"New promo: {c.code}",
                message=f"{c.label} on {c.get_applies_to_display()}. Use code {c.code}.",
            )
        messages.success(request, f"Coupon {c.code} created and broadcast to users.")
        return redirect('dashboard:coupons')
    return render(request, 'dashboard/coupon_form.html', {'form': form, 'mode': 'Create'})


@staff_member_required
def coupon_edit(request, pk):
    c = get_object_or_404(Coupon, pk=pk)
    form = CouponAdminForm(request.POST or None, instance=c)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Coupon {c.code} updated.")
        return redirect('dashboard:coupons')
    return render(request, 'dashboard/coupon_form.html',
                  {'form': form, 'coupon': c, 'mode': 'Edit'})


@staff_member_required
def coupon_delete(request, pk):
    c = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        code = c.code
        c.delete()
        messages.success(request, f"Coupon {code} deleted.")
        return redirect('dashboard:coupons')
    return render(request, 'dashboard/confirm_delete.html', {
        'object': c, 'title': 'coupon',
        'back_url': reverse('dashboard:coupons'),
    })


# =============================================================
#  Contact messages & newsletter
# =============================================================
@staff_member_required
def messages_list(request):
    items = ContactMessage.objects.all()
    if request.method == 'POST':
        msg_id = request.POST.get('id')
        m = get_object_or_404(ContactMessage, pk=msg_id)
        m.is_resolved = not m.is_resolved
        m.save()
        return redirect('dashboard:messages')
    return render(request, 'dashboard/messages.html', {'items': items})


@staff_member_required
def newsletter_list(request):
    subscribers = NewsletterSubscriber.objects.all()
    return render(request, 'dashboard/newsletter.html', {'subscribers': subscribers})
