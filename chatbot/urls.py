from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('api/message/', views.chat_api, name='api_message'),
    path('api/history/', views.chat_history, name='api_history'),
    path('widget/', views.chat_widget_partial, name='widget'),
]
