from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


# Percent of subtotal added if user opts for travel insurance
INSURANCE_RATE = Decimal('0.05')


class Flight(models.Model):
    CABIN_CHOICES = [
        ('economy', 'Economy'),
        ('premium', 'Premium Economy'),
        ('business', 'Business'),
        ('first', 'First Class'),
    ]

    flight_number = models.CharField(max_length=20, unique=True)
    airline = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)
    origin_code = models.CharField(max_length=5, blank=True)
    destination = models.CharField(max_length=100)
    destination_code = models.CharField(max_length=5, blank=True)
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=0)
    cabin_class = models.CharField(max_length=20, choices=CABIN_CHOICES, default='economy')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    seats_total = models.PositiveIntegerField(default=180)
    seats_available = models.PositiveIntegerField(default=180)
    aircraft = models.CharField(max_length=80, blank=True, default='Boeing 737')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['departure_time']

    def __str__(self):
        return f"{self.airline} {self.flight_number}: {self.origin} → {self.destination}"

    @property
    def duration_str(self):
        h, m = divmod(self.duration_minutes, 60)
        return f"{h}h {m}m"

    @property
    def is_full(self):
        return self.seats_available <= 0


class Hotel(models.Model):
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default='India')
    address = models.TextField(blank=True)
    star_rating = models.PositiveSmallIntegerField(default=3)
    description = models.TextField(blank=True)
    amenities = models.CharField(
        max_length=500, blank=True,
        help_text="Comma-separated list, e.g., WiFi, Pool, Gym, Spa"
    )
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    rooms_total = models.PositiveIntegerField(default=50)
    rooms_available = models.PositiveIntegerField(default=50)
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-star_rating', 'price_per_night']

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def amenity_list(self):
        return [a.strip() for a in self.amenities.split(',') if a.strip()]

    @property
    def map_query(self):
        """Build a search query string for Google Maps."""
        parts = [self.name, self.address, self.city, self.country]
        return ', '.join(p for p in parts if p)

    @property
    def map_embed_url(self):
        """Iframe-friendly Google Maps URL — no API key required."""
        from urllib.parse import quote_plus
        return (f"https://maps.google.com/maps?q={quote_plus(self.map_query)}"
                f"&z=14&output=embed")

    @property
    def map_directions_url(self):
        """Open Google Maps directions in a new tab."""
        from urllib.parse import quote_plus
        return f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(self.map_query)}"


class Booking(models.Model):
    BOOKING_TYPES = [
        ('flight', 'Flight'),
        ('hotel', 'Hotel'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPES)

    # Flight booking
    flight = models.ForeignKey(Flight, on_delete=models.SET_NULL, null=True, blank=True)
    passengers = models.PositiveIntegerField(default=1)

    # Hotel booking
    hotel = models.ForeignKey(Hotel, on_delete=models.SET_NULL, null=True, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    rooms = models.PositiveIntegerField(default=1)
    guests = models.PositiveIntegerField(default=1)

    # Pricing breakdown
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    insurance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Addons / discounts
    has_insurance = models.BooleanField(default=False)
    coupon_code = models.CharField(max_length=32, blank=True)
    loyalty_points_earned = models.PositiveIntegerField(default=0)
    loyalty_points_redeemed = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            prefix = 'FLT' if self.booking_type == 'flight' else 'HTL'
            self.reference = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} ({self.user.username})"

    @property
    def nights(self):
        if self.check_in and self.check_out:
            return max((self.check_out - self.check_in).days, 1)
        return 0

    @property
    def title(self):
        if self.booking_type == 'flight' and self.flight:
            return f"{self.flight.airline} {self.flight.flight_number}"
        if self.booking_type == 'hotel' and self.hotel:
            return self.hotel.name
        return self.reference


class Payment(models.Model):
    METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('upi', 'UPI'),
        ('netbanking', 'Net Banking'),
        ('wallet', 'Wallet'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    transaction_id = models.CharField(max_length=40, unique=True, editable=False)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='card')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    card_last4 = models.CharField(max_length=4, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def mark_success(self):
        self.status = 'success'
        self.paid_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"


# ============================================================
#  Reviews & Ratings
# ============================================================
class HotelReview(models.Model):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hotel_reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 (worst) to 5 (best)",
    )
    title = models.CharField(max_length=120, blank=True)
    comment = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False,
        help_text="True if user has a confirmed booking for this hotel.")
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('hotel', 'user')]

    def __str__(self):
        return f"{self.user.username} → {self.hotel.name} ({self.rating}★)"


# ============================================================
#  Wishlist / Favourites
# ============================================================
class WishlistItem(models.Model):
    ITEM_TYPES = [('flight', 'Flight'), ('hotel', 'Hotel')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, null=True, blank=True)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [
            ('user', 'item_type', 'flight'),
            ('user', 'item_type', 'hotel'),
        ]

    def __str__(self):
        target = self.flight or self.hotel
        return f"{self.user.username} ♥ {target}"


# ============================================================
#  Coupon / Promo codes
# ============================================================
class Coupon(models.Model):
    APPLIES_TO = [
        ('all', 'Flights & Hotels'),
        ('flight', 'Flights only'),
        ('hotel', 'Hotels only'),
    ]

    code = models.CharField(max_length=32, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_percent = models.PositiveSmallIntegerField(default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)])
    discount_flat = models.DecimalField(max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        help_text="Flat amount discount (used if discount_percent is 0).")
    min_booking_amount = models.DecimalField(max_digits=10, decimal_places=2,
        default=Decimal('0.00'))
    max_discount = models.DecimalField(max_digits=10, decimal_places=2,
        default=Decimal('0.00'),
        help_text="Cap on percent discount. 0 = no cap.")
    applies_to = models.CharField(max_length=10, choices=APPLIES_TO, default='all')
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    max_uses = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.code} ({self.label})"

    @property
    def label(self):
        if self.discount_percent:
            return f"{self.discount_percent}% off"
        return f"₹{self.discount_flat:.0f} off"

    def is_valid(self, booking_type=None, amount=None):
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is not active."
        if now < self.valid_from:
            return False, "Coupon is not yet valid."
        if now > self.valid_to:
            return False, "Coupon has expired."
        if self.used_count >= self.max_uses:
            return False, "Coupon usage limit reached."
        if self.applies_to != 'all' and booking_type and self.applies_to != booking_type:
            return False, f"This coupon is only for {self.get_applies_to_display()}."
        if amount is not None and Decimal(amount) < self.min_booking_amount:
            return False, f"Minimum booking amount is ₹{self.min_booking_amount:.0f}."
        return True, ""

    def compute_discount(self, amount):
        amount = Decimal(amount)
        if self.discount_percent:
            d = amount * Decimal(self.discount_percent) / Decimal(100)
            if self.max_discount and self.max_discount > 0:
                d = min(d, self.max_discount)
            return d.quantize(Decimal('0.01'))
        return min(self.discount_flat, amount).quantize(Decimal('0.01'))


# ============================================================
#  Notifications
# ============================================================
class Notification(models.Model):
    TYPE_CHOICES = [
        ('booking', 'Booking'),
        ('payment', 'Payment'),
        ('promo', 'Promotion'),
        ('system', 'System'),
        ('loyalty', 'Loyalty'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=120)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=300, blank=True)
    icon = models.CharField(max_length=8, default='🔔')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read'])]

    def __str__(self):
        return f"[{self.type}] {self.title} → {self.user.username}"


# ============================================================
#  Newsletter Subscribers
# ============================================================
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email


# ============================================================
#  Contact form messages
# ============================================================
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"
