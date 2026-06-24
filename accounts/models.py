import secrets

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


def _gen_referral_code():
    return secrets.token_urlsafe(6).replace('_', '').replace('-', '').upper()[:8]


class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Hindi', 'हिन्दी (Hindi)'),
        ('Spanish', 'Español (Spanish)'),
        ('French', 'Français (French)'),
        ('German', 'Deutsch (German)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default='India')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    preferred_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='English')

    # New features
    loyalty_points = models.PositiveIntegerField(default=0,
        help_text="1 point = ₹1 discount. Earned on confirmed bookings.")
    referral_code = models.CharField(max_length=12, blank=True, db_index=True)
    newsletter_subscribed = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def tier(self):
        """Loyalty tier based on points earned."""
        p = self.loyalty_points
        if p >= 5000:
            return ('Platinum', '💎', 'platinum')
        if p >= 2000:
            return ('Gold', '🥇', 'gold')
        if p >= 500:
            return ('Silver', '🥈', 'silver')
        return ('Bronze', '🥉', 'bronze')

    def save(self, *args, **kwargs):
        if not self.referral_code:
            code = _gen_referral_code()
            while UserProfile.objects.filter(referral_code=code).exists():
                code = _gen_referral_code()
            self.referral_code = code
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
