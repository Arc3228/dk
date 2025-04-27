from datetime import timedelta, datetime, date
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
        fields = ['event_name', 'date', 'time', 'duration', 'check_oborydovanie']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'min': date.today().strftime('%Y-%m-%d')}),
            'time': forms.TimeInput(attrs={'type': 'time', 'min': '10:00', 'max': '19:00'}),
        }
        labels = {
            'event_name': 'Название мероприятия',
            'date': 'Дата',
            'time': 'Время проведения',
            'duration': 'Продолжительность (часы)',
            'check_oborydovanie': 'Нужно оборудование',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs['min'] = date.today().strftime('%Y-%m-%d')

    def clean_date(self):
        selected_date = self.cleaned_data.get('date')
        if selected_date and selected_date < date.today():
            raise forms.ValidationError("Нельзя выбрать дату в прошлом!")
        return selected_date

    def clean(self):
        cleaned_data = super().clean()
        date_val = cleaned_data.get('date')
        time_val = cleaned_data.get('time')
        duration = cleaned_data.get('duration')

        if time_val and (time_val < datetime.strptime('10:00', '%H:%M').time() or time_val > datetime.strptime('19:00', '%H:%M').time()):
            self.add_error('time', "Выберите время с 10:00 до 19:00.")

        if date_val and time_val and duration:
            start_new = datetime.combine(date_val, time_val)
            end_new = start_new + timedelta(hours=duration)

            bookings = HallBooking.objects.filter(date=date_val)
            if self.instance.pk:
                bookings = bookings.exclude(pk=self.instance.pk)

            for booking in bookings:
                start_existing = datetime.combine(booking.date, booking.time)
                end_existing = start_existing + timedelta(hours=booking.duration)

                if start_new < end_existing and end_new > start_existing:
                    raise forms.ValidationError(
                        f"Зал уже забронирован на {booking.time.strftime('%H:%M')} "
                        f"до {end_existing.time().strftime('%H:%M')}"
                    )

        return cleaned_data


