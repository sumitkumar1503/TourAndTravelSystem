from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.home, name='home'),

    # Static informational pages
    path('about/', views.about, name='about'),
    path('faq/', views.faq, name='faq'),
    path('contact/', views.contact, name='contact'),

    # Flights
    path('flights/', views.flight_search, name='flight_search'),
    path('flights/<int:pk>/book/', views.flight_book, name='flight_book'),

    # Hotels
    path('hotels/', views.hotel_search, name='hotel_search'),
    path('hotels/map/', views.hotel_map, name='hotel_map'),
    path('hotels/<int:pk>/', views.hotel_detail, name='hotel_detail'),
    path('hotels/<int:pk>/book/', views.hotel_book, name='hotel_book'),
    path('hotels/<int:pk>/review/', views.hotel_review_add, name='hotel_review_add'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/toggle/<str:item_type>/<int:pk>/', views.wishlist_toggle, name='wishlist_toggle'),

    # Payment + addons (AJAX)
    path('payment/<str:reference>/', views.payment, name='payment'),
    path('payment/<str:reference>/coupon/', views.coupon_apply, name='coupon_apply'),
    path('payment/<str:reference>/coupon/remove/', views.coupon_remove, name='coupon_remove'),
    path('payment/<str:reference>/insurance/', views.insurance_toggle, name='insurance_toggle'),
    path('payment/<str:reference>/loyalty/', views.loyalty_apply, name='loyalty_apply'),

    # Confirmation / Ticket
    path('confirmation/<str:reference>/', views.confirmation, name='confirmation'),
    path('confirmation/<str:reference>/ticket.pdf', views.ticket_pdf, name='ticket_pdf'),

    # History
    path('my-bookings/', views.booking_history, name='history'),
    path('my-bookings/<str:reference>/cancel/', views.booking_cancel, name='cancel'),

    # Loyalty
    path('loyalty/', views.loyalty, name='loyalty'),

    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/read-all/', views.notifications_read_all, name='notifications_read_all'),

    # Newsletter
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
]
