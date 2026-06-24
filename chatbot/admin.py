from django.contrib import admin
from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('sender', 'message', 'intent', 'entities', 'timestamp')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'started_at', 'last_activity')
    search_fields = ('user__username', 'session_key')
    list_filter = ('started_at',)
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'sender', 'intent', 'timestamp')
    list_filter = ('sender', 'intent')
    search_fields = ('message',)
