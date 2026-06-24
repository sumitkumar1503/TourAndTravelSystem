"""Admin-side ModelForms for managing Flights, Hotels, Coupons."""
from django import forms
from booking.models import Flight, Hotel, Coupon


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = (css + ' form-check-input').strip()
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = (css + ' form-select').strip()
            else:
                field.widget.attrs['class'] = (css + ' form-control').strip()


class FlightAdminForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Flight
        fields = [
            'flight_number', 'airline', 'aircraft',
            'origin', 'origin_code', 'destination', 'destination_code',
            'departure_time', 'arrival_time', 'duration_minutes',
            'cabin_class', 'price',
            'seats_total', 'seats_available', 'is_active',
        ]
        widgets = {
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        data = super().clean()
        if data.get('arrival_time') and data.get('departure_time'):
            if data['arrival_time'] <= data['departure_time']:
                raise forms.ValidationError("Arrival must be after departure.")
        if (data.get('seats_available') or 0) > (data.get('seats_total') or 0):
            raise forms.ValidationError("Seats available cannot exceed total seats.")
        return data


class HotelAdminForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Hotel
        fields = [
            'name', 'city', 'country', 'address', 'star_rating',
            'description', 'amenities', 'price_per_night',
            'rooms_total', 'rooms_available', 'image_url', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'amenities': forms.TextInput(attrs={'placeholder': 'WiFi, Pool, Gym, Spa'}),
        }

    def clean(self):
        data = super().clean()
        if (data.get('rooms_available') or 0) > (data.get('rooms_total') or 0):
            raise forms.ValidationError("Rooms available cannot exceed total rooms.")
        stars = data.get('star_rating', 0)
        if stars and (stars < 1 or stars > 5):
            raise forms.ValidationError("Star rating must be between 1 and 5.")
        return data


class CouponAdminForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Coupon
        fields = [
            'code', 'description', 'applies_to',
            'discount_percent', 'discount_flat',
            'min_booking_amount', 'max_discount',
            'valid_from', 'valid_to', 'max_uses', 'is_active',
        ]
        widgets = {
            'valid_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.TextInput(attrs={'placeholder': 'e.g. Save 10% on flights this month'}),
        }

    def clean_code(self):
        return self.cleaned_data['code'].upper().strip()

    def clean(self):
        data = super().clean()
        if data.get('valid_from') and data.get('valid_to') and data['valid_to'] <= data['valid_from']:
            raise forms.ValidationError("'Valid to' must be after 'Valid from'.")
        if not data.get('discount_percent') and not data.get('discount_flat'):
            raise forms.ValidationError("Set either a discount percent or a flat amount.")
        return data
