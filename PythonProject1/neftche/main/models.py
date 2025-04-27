from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    name = models.CharField(max_length=30)
    surname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=18, blank=True, null=True)


class News(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=1)

class Events(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='events_images/', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=1)

    def __str__(self):
        return self.title

class Ticket(models.Model):
    event = models.ForeignKey(Events, on_delete=models.CASCADE, related_name='tickets')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    purchased_at = models.DateTimeField(auto_now_add=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.user} — {self.event.title} ({self.quantity})"


class Seat(models.Model):
    event = models.ForeignKey(Events, on_delete=models.CASCADE, related_name='seats')
    row = models.IntegerField()
    number = models.IntegerField()
    is_taken = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Ряд {self.row}, Место {self.number} ({'занято' if self.is_taken else 'свободно'})"

class HallBooking(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    event_name = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    duration = models.PositiveIntegerField(help_text="Продолжительность в часах")
    check_oborydovanie = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    price = models.PositiveIntegerField(default=0, help_text="Стоимость бронирования в рублях")

    def __str__(self):
        return f"{self.event_name} ({self.date} {self.time}) от {self.user}"



def create_seats_for_event(event):
    total_seats = 987
    seats_per_row = 30
    for i in range(total_seats):
        row = (i // seats_per_row) + 1
        number = (i % seats_per_row) + 1
        Seat.objects.create(event=event, row=row, number=number)


class PaymentHistory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.amount}₽ - {self.created_at.strftime('%d.%m.%Y %H:%M')}"
