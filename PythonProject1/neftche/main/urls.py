from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('circles/', views.circles, name='circles'),
    path('contacts/', views.contacts, name='contacts'),
    path('news/', views.news_list, name='news_list'),
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),
]