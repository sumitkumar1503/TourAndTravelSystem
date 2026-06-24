from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('reports/', views.reports, name='reports'),

    # Users
    path('users/', views.users_list, name='users'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/toggle/<str:action>/', views.user_toggle, name='user_toggle'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # Flights CRUD
    path('flights/', views.flights_list, name='flights'),
    path('flights/new/', views.flight_create, name='flight_create'),
    path('flights/<int:pk>/edit/', views.flight_edit, name='flight_edit'),
    path('flights/<int:pk>/delete/', views.flight_delete, name='flight_delete'),

    # Hotels CRUD
    path('hotels/', views.hotels_list, name='hotels'),
    path('hotels/new/', views.hotel_create, name='hotel_create'),
    path('hotels/<int:pk>/edit/', views.hotel_edit, name='hotel_edit'),
    path('hotels/<int:pk>/delete/', views.hotel_delete, name='hotel_delete'),

    # Bookings
    path('bookings/', views.bookings_list, name='bookings'),
    path('bookings/<str:reference>/status/', views.booking_update_status, name='booking_status'),
    path('bookings/<str:reference>/delete/', views.booking_delete, name='booking_delete'),

    # Coupons CRUD
    path('coupons/', views.coupons_list, name='coupons'),
    path('coupons/new/', views.coupon_create, name='coupon_create'),
    path('coupons/<int:pk>/edit/', views.coupon_edit, name='coupon_edit'),
    path('coupons/<int:pk>/delete/', views.coupon_delete, name='coupon_delete'),

    # Communications
    path('messages/', views.messages_list, name='messages'),
    path('newsletter/', views.newsletter_list, name='newsletter'),
]
