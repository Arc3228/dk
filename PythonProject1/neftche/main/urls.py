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

    # админ
    path('admin_panel', views.admin_panel, name='admin_panel'),
    path('admin_panel/news/create/', views.news_create, name='news_create'),
    path('admin_panel/news/<int:pk>/edit/', views.news_edit, name='news_edit'),
    path('admin_panel/news/<int:pk>/delete/', views.news_delete, name='news_delete'),

]