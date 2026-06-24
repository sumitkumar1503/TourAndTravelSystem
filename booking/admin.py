from django.contrib import admin
from .models import (
    Flight, Hotel, Booking, Payment, Coupon, HotelReview,
    WishlistItem, Notification, NewsletterSubscriber, ContactMessage,
)


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('flight_number', 'airline', 'origin', 'destination',
                    'departure_time', 'price', 'seats_available', 'is_active')
    list_filter = ('airline', 'cabin_class', 'is_active')
    search_fields = ('flight_number', 'airline', 'origin', 'destination')
    list_editable = ('is_active',)


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'star_rating', 'price_per_night',
                    'rooms_available', 'is_active')
    list_filter = ('city', 'star_rating', 'is_active')
    search_fields = ('name', 'city')
    list_editable = ('is_active',)


class PaymentInline(admin.StackedInline):
    model = Payment
    can_delete = False
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'booking_type', 'title',
                    'total_amount', 'status', 'created_at')
    list_filter = ('booking_type', 'status', 'created_at')
    search_fields = ('reference', 'user__username', 'user__email')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'booking', 'method', 'amount', 'status', 'paid_at')
    list_filter = ('method', 'status')
    search_fields = ('transaction_id', 'booking__reference')
    readonly_fields = ('transaction_id', 'created_at')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'applies_to', 'discount_percent', 'discount_flat',
                    'used_count', 'max_uses', 'valid_to', 'is_active')
    list_filter = ('applies_to', 'is_active')
    search_fields = ('code', 'description')


@admin.register(HotelReview)
class HotelReviewAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'user', 'rating', 'title', 'is_verified', 'created_at')
    list_filter = ('rating', 'is_verified')
    search_fields = ('hotel__name', 'user__username', 'title')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'item_type', 'flight', 'hotel', 'created_at')
    list_filter = ('item_type',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('title', 'message', 'user__username')


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'is_active', 'subscribed_at')
    list_filter = ('is_active',)
    search_fields = ('email',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'is_resolved', 'created_at')
    list_filter = ('is_resolved',)
    search_fields = ('name', 'email', 'subject')
