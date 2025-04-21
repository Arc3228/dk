from datetime import timedelta, datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import News, CustomUser, Events, Ticket, HallBooking


class SignUpForm(UserCreationForm):
    name = forms.CharField(max_length=50)
    surname = forms.CharField(max_length=100)
    lastname = forms.CharField(max_length=100)
    phone_number = forms.CharField(max_length=18, required=True, help_text='Обязательное поле.')
    email = forms.EmailField(max_length=254, help_text='Обязательное поле. Введите действующий email.')

    class Meta:
        model = CustomUser
        fields = ('username', 'surname', 'name', 'lastname', 'phone_number', 'email', 'password1', 'password2')

class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Имя пользователя')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)

class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'content', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите заголовок'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Введите текст новости'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }


class EventsForm(forms.ModelForm):
    class Meta:
        model = Events
        fields = ['title', 'content', 'image', 'price']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Введите описание события'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите цену билета'
            }),
        }

class TicketPurchaseForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['quantity']


class BalanceTopUpForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, label="Сумма пополнения")


class HallBookingForm(forms.ModelForm):
    class Meta:
        model = HallBooking
        fields = ['event_name', 'date', 'time', 'duration']

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        duration = cleaned_data.get('duration')

        if date and time and duration:
            start_new = datetime.combine(date, time)
            end_new = start_new + timedelta(hours=duration)

            bookings = HallBooking.objects.filter(date=date)

            for booking in bookings:
                start_existing = datetime.combine(booking.date, booking.time)
                end_existing = start_existing + timedelta(hours=booking.duration)

                # Проверка на пересечение по времени
                if (start_new < end_existing and end_new > start_existing):
                    raise forms.ValidationError(
                        f"Зал уже забронирован на {booking.time.strftime('%H:%M')} "
                        f"до {(end_existing).strftime('%H:%M')}"
                    )

        return cleaned_data
