from datetime import timedelta, datetime, date
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import News, CustomUser, Events, Ticket, HallBooking
class SignUpForm(UserCreationForm):
    username = forms.CharField(label='Имя пользователя', required=True)
    name = forms.CharField(max_length=50, label='Имя')
    surname = forms.CharField(max_length=100, label='Фамилия')
    lastname = forms.CharField(max_length=100, label='Отчество')
    phone_number = forms.CharField(max_length=18, required=True, label='Номер телефона')
    email = forms.EmailField(max_length=254, label='Почта')


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
        fields = ['title', 'content', 'image', 'price', 'data']
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
            'data': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'  # ← Это ключевое!
            }),
        }

class TicketPurchaseForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['quantity']


class BalanceTopUpForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2, label="Сумма пополнения")



class HallBookingForm(forms.ModelForm):
    full_day = forms.BooleanField(required=False, label="Бронирование на весь день (10 часов)")

    class Meta:
        model = HallBooking
        fields = ['event_name', 'date', 'time', 'duration', 'check_oborydovanie']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'min': date.today().strftime('%Y-%m-%d')}),
            'time': forms.TimeInput(attrs={'type': 'time', 'min': '10:00', 'max': '19:00'}),
            'check_oborydovanie': forms.CheckboxInput(attrs={'id': 'id_check_oborydovanie'}),  # Добавьте ID
        }
        labels = {
            'event_name': 'Название мероприятия',
            'date': 'Дата',
            'time': 'Время проведения',
            'duration': 'Продолжительность (часы)',
            'check_oborydovanie': 'Нужно оборудование',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs['min'] = date.today().strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        date_val = cleaned_data.get('date')
        time_val = cleaned_data.get('time')
        duration = cleaned_data.get('duration')
        full_day = cleaned_data.get('full_day')
        check_oborydovanie = cleaned_data.get('check_oborydovanie')

        # Валидация времени
        if time_val and (time_val < datetime.strptime('10:00', '%H:%M').time() or time_val > datetime.strptime('19:00', '%H:%M').time()):
            self.add_error('time', "Выберите время с 10:00 до 19:00.")

        # Проверка пересечений с существующими бронированиями
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

        # Расчёт стоимости
        price_per_hour = 25000

        if full_day:
            total_price = price_per_hour * 10
            cleaned_data['duration'] = 10
        else:
            total_price = price_per_hour * duration

        if check_oborydovanie:
            total_price = int(total_price * 1.1)  # Добавляем 10% за оборудование

        cleaned_data['calculated_price'] = total_price

        # Проверка баланса пользователя
        if self.user and self.user.balance < total_price:
            raise forms.ValidationError("Недостаточно средств на балансе для бронирования.")

        return cleaned_data
