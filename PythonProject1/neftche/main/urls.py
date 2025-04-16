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

    # админ
    path('admin_panel', views.admin_panel, name='admin_panel'),
    path('admin_panel/news/create/', views.news_create, name='news_create'),
    path('admin_panel/news/<int:pk>/edit/', views.news_edit, name='news_edit'),
    path('admin_panel/news/<int:pk>/delete/', views.news_delete, name='news_delete'),
    path('admin_panel/events/create/', views.events_create, name='events_create'),
    path('admin_panel/events/<int:pk>/edit/', views.events_edit, name='events_edit'),
    path('admin_panel/events/<int:pk>/delete/', views.events_delete, name='events_delete'),

]