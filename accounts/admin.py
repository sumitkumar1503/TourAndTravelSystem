from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'city', 'country', 'preferred_language', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone', 'city')
    list_filter = ('country', 'gender', 'preferred_language')
