import re
from datetime import timedelta, datetime, date
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from .models import News, CustomUser, Events, Ticket, HallBooking

class SignUpForm(UserCreationForm):
    username = forms.CharField(label='Имя пользователя', required=True)
    name = forms.CharField(
        max_length=50,
        label='Имя',
        widget=forms.TextInput(attrs={

            'data-cyrillic-input': ''
        })
    )
    surname = forms.CharField(
        max_length=100,
        label='Фамилия',
        widget=forms.TextInput(attrs={

            'data-cyrillic-input': ''
        })
    )
    lastname = forms.CharField(
        max_length=100,
        label='Отчество',
        required=False,
        widget=forms.TextInput(attrs={

            'data-cyrillic-input': ''
        })
    )
    phone_number = forms.CharField(
        max_length=18,
        required=True,
        label='Номер телефона',
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 999-99-99',
            'data-phone-input': ''
        })
    )
    email = forms.EmailField(max_length=254, label='Почта')

    class Meta:
        model = CustomUser
        fields = ('username', 'surname', 'name', 'lastname', 'phone_number', 'email', 'password1', 'password2')

    def clean_name(self):
        name = self.cleaned_data['name']
        if not re.match(r'^[А-ЯЁа-яё\- ]+$', name):
            raise ValidationError("Допустимы только русские буквы, пробелы и дефисы")
        return name.strip().title()

    def clean_surname(self):
        surname = self.cleaned_data['surname']
        if not re.match(r'^[А-ЯЁа-яё\- ]+$', surname):
            raise ValidationError("Допустимы только русские буквы, пробелы и дефисы")
        return surname.strip().title()

    def clean_lastname(self):
        lastname = self.cleaned_data.get('lastname', '')
        if lastname:
            if not re.match(r'^[А-ЯЁа-яё\- ]+$', lastname):
                raise ValidationError("Допустимы только русские буквы, пробелы и дефисы")
        return lastname.strip().title() if lastname else ''

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number']
        cleaned_phone = re.sub(r'\D', '', phone)
        if len(cleaned_phone) != 11:
            raise ValidationError("Номер телефона должен содержать 11 цифр")
        return f'+7 ({cleaned_phone[1:4]}) {cleaned_phone[4:7]}-{cleaned_phone[7:9]}-{cleaned_phone[9:11]}'




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
    full_day = forms.BooleanField(
        required=False,
        label="Бронирование на весь день (10 часов)",
        widget=forms.CheckboxInput(attrs={'id': 'id_full_day'}))

    class Meta:
        model = HallBooking
        fields = ['event_name', 'date', 'time', 'duration', 'check_oborydovanie']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'min': date.today().strftime('%Y-%m-%d'),
                'id': 'id_date'
            }),
            'time': forms.TimeInput(attrs={
                'type': 'time',
                'min': '10:00',
                'max': '19:00',
                'step': '1800',  # 30 минут
                'id': 'id_time'
            }),
            'check_oborydovanie': forms.CheckboxInput(attrs={'id': 'id_check_oborydovanie'}),
            'duration': forms.NumberInput(attrs={
                'id': 'id_duration',
                'min': '1',
                'max': '10'
            }),
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

    def clean_time(self):
        time_val = self.cleaned_data.get('time')
        if time_val:
            if time_val.minute % 30 != 0:
                raise ValidationError("Время должно быть кратно 30 минутам (например: 10:00, 10:30)")
        return time_val

    def clean(self):
        cleaned_data = super().clean()
        date_val = cleaned_data.get('date')
        time_val = cleaned_data.get('time')
        duration = cleaned_data.get('duration')
        full_day = cleaned_data.get('full_day')
        check_oborydovanie = cleaned_data.get('check_oborydovanie')

        # Валидация времени
        if time_val and (time_val < datetime.strptime('10:00', '%H:%M').time()
                         or time_val > datetime.strptime('19:00', '%H:%M').time()):
            self.add_error('time', "Выберите время с 10:00 до 19:00.")

        # Проверка пересечений бронирований
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
                        f"Зал уже забронирован с {booking.time.strftime('%H:%M')} "
                        f"до {end_existing.time().strftime('%H:%M')}"
                    )

        # Расчет стоимости
        price_per_hour = 25000
        if full_day:
            total_price = price_per_hour * 10
            cleaned_data['duration'] = 10
        else:
            total_price = price_per_hour * duration

        if check_oborydovanie:
            total_price = int(total_price * 1.1)

        cleaned_data['calculated_price'] = total_price

        # Проверка баланса
        if self.user and self.user.balance < total_price:
            raise forms.ValidationError("Недостаточно средств на балансе для бронирования.")

        return cleaned_data
