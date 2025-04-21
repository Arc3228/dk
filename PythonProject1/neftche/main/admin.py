from django.contrib import admin
from .models import Circle, News, HallBooking


@admin.register(Circle)
class CircleAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'pub_date')


@admin.register(HallBooking)
class HallBookingAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'user', 'date', 'time', 'duration', 'created_at')
    list_filter = ('date', 'user')
    search_fields = ('event_name', 'user__phone')