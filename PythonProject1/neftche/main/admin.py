from django.contrib import admin
from .models import News, HallBooking, Events, create_seats_for_event, Seat, Ticket

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'pub_date')


@admin.register(HallBooking)
class HallBookingAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'user', 'date', 'time', 'duration', 'created_at')
    list_filter = ('date', 'user')
    search_fields = ('event_name', 'user__phone')

@admin.register(Events)
class EventsAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new:
            create_seats_for_event(obj)


admin.site.register(Seat)
admin.site.register(Ticket)
