from django.contrib import admin
from .models import Circle, News

@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'pub_date')