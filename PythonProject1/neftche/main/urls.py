from tkinter.font import names

from django.contrib.auth.views import LogoutView
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('news', views.news_list, name='news_list'),
    path('news/detail/<int:news_id>', views.news_detail, name='news_detail'),
    path('events', views.events_list, name='events_list'),
    path('events/detail/<int:events_id>', views.events_detail, name='events_detail'),
    path('events/<int:events_id>/buy/', views.buy_ticket, name='buy_ticket'),
    path('profile/', views.profile, name='profile'),
    path('top-up/', views.top_up_balance, name='top_up_balance'),
    path('book-hall/', views.book_hall, name='book_hall'),
    path('bookings/slots/', views.get_booked_slots, name='get_booked_slots'),
    path('seat/payment/<int:seat_id>/', views.seat_payment, name='seat_payment'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('payment-history/', views.payment_history, name='payment_history'),


    # админ
    path('admin_panel', views.admin_panel, name='admin_panel'),
    path('admin_panel/news/create/', views.news_create, name='news_create'),
    path('admin_panel/news/<int:pk>/edit/', views.news_edit, name='news_edit'),
    path('admin_panel/news/<int:pk>/delete/', views.news_delete, name='news_delete'),
    path('admin_panel/events/create/', views.events_create, name='events_create'),
    path('admin_panel/events/<int:pk>/edit/', views.events_edit, name='events_edit'),
    path('admin_panel/events/<int:pk>/delete/', views.events_delete, name='events_delete'),
    path('hall-bookings/', views.hall_bookings_view, name='hall_bookings'),
    path('edit-booking/<int:booking_id>/', views.edit_booking, name='edit_booking'),
    path('delete-booking/<int:booking_id>/', views.delete_booking, name='delete_booking'),
    path('site-statistics/', views.site_statistics, name='site_statistics'),
]