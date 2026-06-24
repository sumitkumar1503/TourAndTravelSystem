"""Seed sample flights, hotels, coupons, reviews for the demo."""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User

from booking.models import Flight, Hotel, Coupon, HotelReview


AIRLINES = [
    ('IndiGo', '6E'), ('Air India', 'AI'), ('Vistara', 'UK'),
    ('SpiceJet', 'SG'), ('Akasa Air', 'QP'), ('Air India Express', 'IX'),
]
AIRPORTS = [
    ('Delhi', 'DEL'), ('Mumbai', 'BOM'), ('Bengaluru', 'BLR'),
    ('Hyderabad', 'HYD'), ('Chennai', 'MAA'), ('Kolkata', 'CCU'),
    ('Goa', 'GOI'), ('Jaipur', 'JAI'), ('Ahmedabad', 'AMD'),
    ('Pune', 'PNQ'), ('Kochi', 'COK'), ('Lucknow', 'LKO'),
    ('Srinagar', 'SXR'), ('Guwahati', 'GAU'), ('Trivandrum', 'TRV'),
]
CABINS = ['economy', 'economy', 'economy', 'premium', 'business']
AIRCRAFT = ['Airbus A320', 'Boeing 737', 'Airbus A321', 'Boeing 787', 'ATR 72']

HOTELS = [
    ('The Leela Palace', 'New Delhi', 5, 18000, 'WiFi, Pool, Spa, Gym, Fine Dining, Concierge'),
    ('Taj Mahal Palace', 'Mumbai', 5, 21000, 'WiFi, Pool, Spa, Gym, Sea View, Restaurant'),
    ('ITC Grand Chola', 'Chennai', 5, 14000, 'WiFi, Pool, Spa, Gym, Multi-cuisine, Bar'),
    ('Goa Marriott Resort', 'Goa', 5, 12500, 'WiFi, Beach Access, Pool, Spa, Casino, Bar'),
    ('Oberoi Udaivilas', 'Udaipur', 5, 35000, 'WiFi, Lake View, Pool, Spa, Butler Service'),
    ('Wildflower Hall', 'Shimla', 5, 22000, 'WiFi, Mountain View, Spa, Restaurant, Adventure'),
    ('Radisson Blu', 'Bengaluru', 4, 7500, 'WiFi, Pool, Gym, Restaurant, Bar, Conference'),
    ('Novotel Hyderabad', 'Hyderabad', 4, 6900, 'WiFi, Pool, Gym, Spa, Restaurant'),
    ('The Park', 'Kolkata', 4, 6500, 'WiFi, Pool, Bar, Restaurant, Nightclub'),
    ('Crowne Plaza', 'Pune', 4, 5800, 'WiFi, Pool, Gym, Multi-cuisine'),
    ('Cidade de Goa', 'Goa', 4, 6200, 'WiFi, Beach, Pool, Spa, Water Sports'),
    ('Hotel Holiday Heights', 'Manali', 3, 3200, 'WiFi, Mountain View, Restaurant, Heating'),
    ('Hyatt Regency', 'Jaipur', 5, 11000, 'WiFi, Pool, Spa, Gym, Heritage Tours'),
    ('Backwater Ripples', 'Alleppey', 4, 5200, 'WiFi, Houseboat, Backwater View, Restaurant'),
    ('Spice Tree Munnar', 'Munnar', 4, 4900, 'WiFi, Tea Plantation View, Restaurant, Spa'),
    ('Mayfair Darjeeling', 'Darjeeling', 4, 6100, 'WiFi, Mountain View, Heritage, Restaurant'),
    ('Vivanta Andaman', 'Port Blair', 5, 13500, 'WiFi, Beach, Diving, Pool, Spa'),
    ('Welcomhotel Coorg', 'Mysuru', 4, 5500, 'WiFi, Coffee Plantation, Pool, Spa, Adventure'),
    ('Le Meridien', 'Kochi', 5, 9800, 'WiFi, Pool, Backwater, Spa, Restaurant'),
    ('OYO Townhouse Central', 'Lucknow', 3, 2800, 'WiFi, AC, Restaurant, Free Breakfast'),
    ('Treebo Trend', 'Ahmedabad', 3, 2400, 'WiFi, AC, 24x7 Reception, Restaurant'),
    ('FabHotel Prime', 'Indore', 3, 2200, 'WiFi, AC, Restaurant, Free Breakfast'),
]

HOTEL_IMAGES = [
    'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600',
    'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=600',
    'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600',
    'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=600',
    'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=600',
    'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=600',
    'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=600',
    'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=600',
]


class Command(BaseCommand):
    help = "Seed the database with demo flights and hotels."

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete existing flights and hotels first.')
        parser.add_argument('--days', type=int, default=14,
                            help='How many days of flights to generate.')

    def handle(self, *args, **opts):
        if opts['flush']:
            Flight.objects.all().delete()
            Hotel.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed existing flights and hotels."))

        self.stdout.write("Seeding hotels...")
        for name, city, stars, price, amenities in HOTELS:
            Hotel.objects.update_or_create(
                name=name, city=city,
                defaults={
                    'star_rating': stars,
                    'price_per_night': Decimal(price),
                    'amenities': amenities,
                    'rooms_total': random.randint(40, 120),
                    'rooms_available': random.randint(15, 60),
                    'description': f"{name} is a {stars}-star property in {city} offering an "
                                   f"excellent stay with world-class amenities.",
                    'image_url': random.choice(HOTEL_IMAGES),
                    'country': 'India',
                    'address': f"{name}, {city}, India",
                },
            )
        self.stdout.write(self.style.SUCCESS(f"  -> {Hotel.objects.count()} hotels."))

        self.stdout.write("Seeding flights...")
        today = timezone.now().replace(minute=0, second=0, microsecond=0)
        flight_count_before = Flight.objects.count()

        flight_no = 100
        for d in range(opts['days']):
            for origin, ocode in AIRPORTS:
                for dest, dcode in random.sample(
                        [a for a in AIRPORTS if a[0] != origin], 4):
                    flight_no += 1
                    airline, code = random.choice(AIRLINES)
                    duration = random.randint(60, 240)
                    dep = today + timedelta(days=d, hours=random.randint(5, 22))
                    arr = dep + timedelta(minutes=duration)
                    cabin = random.choice(CABINS)
                    base = random.randint(2200, 9500)
                    if cabin == 'business':
                        base *= 3
                    elif cabin == 'premium':
                        base *= 2

                    Flight.objects.update_or_create(
                        flight_number=f"{code}{flight_no:04d}",
                        defaults={
                            'airline': airline,
                            'origin': origin,
                            'origin_code': ocode,
                            'destination': dest,
                            'destination_code': dcode,
                            'departure_time': dep,
                            'arrival_time': arr,
                            'duration_minutes': duration,
                            'cabin_class': cabin,
                            'price': Decimal(base),
                            'seats_total': 180,
                            'seats_available': random.randint(20, 180),
                            'aircraft': random.choice(AIRCRAFT),
                        },
                    )
        added = Flight.objects.count() - flight_count_before
        self.stdout.write(self.style.SUCCESS(f"  -> {added} new flights ({Flight.objects.count()} total)."))

        # Demo admin user (only if missing)
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', email='admin@travelbot.local', password='admin123',
                first_name='Admin', last_name='User',
            )
            self.stdout.write(self.style.SUCCESS("Created superuser: admin / admin123"))

        # Demo regular user
        if not User.objects.filter(username='demo').exists():
            User.objects.create_user(
                username='demo', email='demo@travelbot.local', password='demo12345',
                first_name='Demo', last_name='User',
            )
            self.stdout.write(self.style.SUCCESS("Created user: demo / demo12345"))

        # Sample coupons
        self.stdout.write("Seeding coupons...")
        now = timezone.now()
        future = now + timedelta(days=90)
        SAMPLE_COUPONS = [
            ('WELCOME10', '10% off your first booking', 10, 0, 0, 1000, 'all', 500),
            ('FLAT500', '₹500 off on bookings above ₹3000', 0, 500, 3000, 0, 'all', 200),
            ('FLY20', '20% off on flights (max ₹2000)', 20, 0, 0, 2000, 'flight', 300),
            ('STAY15', '15% off on hotels', 15, 0, 0, 1500, 'hotel', 250),
            ('SUMMER25', 'Summer special: 25% off', 25, 0, 5000, 3000, 'all', 100),
        ]
        for code, desc, pct, flat, min_amt, max_disc, applies, uses in SAMPLE_COUPONS:
            Coupon.objects.update_or_create(
                code=code,
                defaults={
                    'description': desc,
                    'discount_percent': pct,
                    'discount_flat': Decimal(flat),
                    'min_booking_amount': Decimal(min_amt),
                    'max_discount': Decimal(max_disc),
                    'applies_to': applies,
                    'valid_from': now,
                    'valid_to': future,
                    'max_uses': uses,
                    'is_active': True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"  -> {Coupon.objects.count()} coupons."))

        # Sample reviews — only if we have at least one hotel & user
        demo_user = User.objects.filter(username='demo').first()
        if demo_user and Hotel.objects.exists() and HotelReview.objects.count() == 0:
            sample_reviews = [
                (5, 'Amazing experience!', 'Loved the rooms and the view. Staff were excellent.'),
                (4, 'Great stay', 'Comfortable beds and clean rooms. Breakfast was decent.'),
                (5, 'Best hotel in town', 'Will definitely come back. Pool and spa are top-notch.'),
                (3, 'Average', 'Decent stay but a bit pricey for what you get.'),
                (4, 'Recommended', 'Lovely location, friendly staff, will visit again.'),
            ]
            for h in Hotel.objects.all()[:5]:
                rating, title, comment = random.choice(sample_reviews)
                HotelReview.objects.get_or_create(
                    user=demo_user, hotel=h,
                    defaults={'rating': rating, 'title': title,
                              'comment': comment, 'is_verified': True},
                )
            self.stdout.write(self.style.SUCCESS(
                f"  -> {HotelReview.objects.count()} sample reviews."))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
