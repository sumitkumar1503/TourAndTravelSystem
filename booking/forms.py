from django import forms
from django.utils import timezone
from .models import Payment, HotelReview, ContactMessage


class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = (css + ' form-select').strip()
            elif isinstance(field.widget, (forms.CheckboxInput,)):
                field.widget.attrs['class'] = (css + ' form-check-input').strip()
            else:
                field.widget.attrs['class'] = (css + ' form-control').strip()


class FlightSearchForm(BootstrapMixin, forms.Form):
    CABIN_CHOICES = [
        ('', 'Any class'),
        ('economy', 'Economy'),
        ('premium', 'Premium Economy'),
        ('business', 'Business'),
        ('first', 'First Class'),
    ]

    origin = forms.CharField(max_length=100, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'From (e.g. Delhi)'}))
    destination = forms.CharField(max_length=100, required=False,
                                  widget=forms.TextInput(attrs={'placeholder': 'To (e.g. Mumbai)'}))
    departure_date = forms.DateField(required=False,
                                     widget=forms.DateInput(attrs={'type': 'date'}))
    cabin_class = forms.ChoiceField(choices=CABIN_CHOICES, required=False)
    passengers = forms.IntegerField(min_value=1, max_value=9, initial=1, required=False)


class HotelSearchForm(BootstrapMixin, forms.Form):
    city = forms.CharField(max_length=100, required=False,
                           widget=forms.TextInput(attrs={'placeholder': 'City (e.g. Goa)'}))
    check_in = forms.DateField(required=False,
                               widget=forms.DateInput(attrs={'type': 'date'}))
    check_out = forms.DateField(required=False,
                                widget=forms.DateInput(attrs={'type': 'date'}))
    rooms = forms.IntegerField(min_value=1, max_value=10, initial=1, required=False)
    guests = forms.IntegerField(min_value=1, max_value=20, initial=2, required=False)
    min_stars = forms.IntegerField(min_value=1, max_value=5, required=False,
                                   widget=forms.NumberInput(attrs={'placeholder': 'Min stars'}))

    def clean(self):
        cleaned = super().clean()
        ci = cleaned.get('check_in')
        co = cleaned.get('check_out')
        if ci and co and co <= ci:
            raise forms.ValidationError("Check-out must be after check-in.")
        return cleaned


class PaymentForm(BootstrapMixin, forms.Form):
    METHOD_CHOICES = Payment.METHOD_CHOICES

    method = forms.ChoiceField(choices=METHOD_CHOICES, initial='card')
    card_number = forms.CharField(
        max_length=19, required=False,
        widget=forms.TextInput(attrs={'placeholder': '4111 1111 1111 1111',
                                      'autocomplete': 'cc-number'})
    )
    name_on_card = forms.CharField(max_length=80, required=False,
                                   widget=forms.TextInput(attrs={'placeholder': 'Name on card'}))
    expiry = forms.CharField(max_length=7, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'MM/YY'}))
    cvv = forms.CharField(
        max_length=4, required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'CVV'})
    )
    upi_id = forms.CharField(max_length=80, required=False,
                             widget=forms.TextInput(attrs={'placeholder': 'name@upi'}))

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('method')
        if method == 'card':
            if not cleaned.get('card_number') or not cleaned.get('cvv') \
                    or not cleaned.get('expiry') or not cleaned.get('name_on_card'):
                raise forms.ValidationError("Please complete all card details.")
            digits = ''.join(c for c in cleaned['card_number'] if c.isdigit())
            if len(digits) < 12:
                raise forms.ValidationError("Card number looks invalid.")
            cleaned['card_last4'] = digits[-4:]
        elif method == 'upi':
            upi = cleaned.get('upi_id', '')
            if '@' not in upi:
                raise forms.ValidationError("Please enter a valid UPI ID like name@upi.")
            cleaned['card_last4'] = ''
        else:
            cleaned['card_last4'] = ''
        return cleaned


class HotelReviewForm(BootstrapMixin, forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={'min': 1, 'max': 5, 'step': 1}),
        help_text="Rate from 1 (worst) to 5 (best)",
    )

    class Meta:
        model = HotelReview
        fields = ['rating', 'title', 'comment']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Sum up your stay in a few words'}),
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell other travelers about your experience...'}),
        }


class ContactForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'How can we help you?'}),
            'subject': forms.TextInput(attrs={'placeholder': 'Subject of your inquiry'}),
        }
