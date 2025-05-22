from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .forms import SignUpForm, NewsForm, EventsForm, HallBookingForm
from datetime import timedelta
from .models import CustomUser, News, Events, create_seats_for_event, Seat, HallBooking, CartItem, Ticket

class ModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            name='Тест',
            surname='Пользователь',
            lastname='Тестович',
            balance=1000.00,
            phone_number='+1234567890'
        )
        self.news = News.objects.create(
            title='Тестовая новость',
            content='Тестовый контент',
            author=self.user
        )
        self.event = Events.objects.create(
            title='Тестовое событие',
            content='Контент события',
            price=50.00,
            author=self.user,
            data=timezone.now()
        )
        create_seats_for_event(self.event)

    def test_custom_user_creation(self):
        self.assertEqual(self.user.name, 'Тест')
        self.assertEqual(self.user.balance, 1000.00)

    def test_news_str(self):
        self.assertEqual(str(self.news.title), 'Тестовая новость')

    def test_events_str(self):
        self.assertEqual(str(self.event), 'Тестовое событие')

    def test_seat_creation(self):
        seat = Seat.objects.filter(event=self.event).first()
        self.assertIsNotNone(seat)
        self.assertEqual(seat.row, 1)
        self.assertEqual(seat.number, 1)
        self.assertFalse(seat.is_taken)

class FormTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            name='Тест',
            surname='Пользователь',
            lastname='Тестович',
            balance=1000.00
        )

    def test_signup_form_valid(self):
        form_data = {
            'username': 'newuser',
            'name': 'Новый',
            'surname': 'Пользователь',
            'lastname': 'Новович',
            'phone_number': '+9876543210',
            'email': 'newuser@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123'
        }
        form = SignUpForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_news_form_valid(self):
        form_data = {
            'title': 'Новая новость',
            'content': 'Новый контент'
        }
        form = NewsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_events_form_valid(self):
        form_data = {
            'title': 'Новое событие',
            'content': 'Новый контент события',
            'price': 75.00,
            'data': timezone.now()
        }
        form = EventsForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_hall_booking_form_valid(self):
        form_data = {
            'event_name': 'Тестовое бронирование',
            'date': (timezone.now() + timedelta(days=1)).date(),
            'time': '12:00',
            'duration': 2,
            'check_oborydovanie': False
        }
        form = HallBookingForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())

    def test_hall_booking_form_conflict(self):
        HallBooking.objects.create(
            user=self.user,
            event_name='Конфликтное бронирование',
            date=(timezone.now() + timedelta(days=1)).date(),
            time='12:00',
            duration=2,
            price=50000
        )
        form_data = {
            'event_name': 'Новое бронирование',
            'date': (timezone.now() + timedelta(days=1)).date(),
            'time': '12:00',
            'duration': 2,
            'check_oborydovanie': False
        }
        form = HallBookingForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            balance=1000.00
        )
        self.event = Events.objects.create(
            title='Тестовое событие',
            content='Контент события',
            price=50.00,
            author=self.user
        )
        self.seat = Seat.objects.create(event=self.event, row=1, number=1)
        self.client.login(username='testuser', password='testpass123')

    def test_seat_payment_success(self):
        seat = Seat.objects.create(event=self.event, row=1, number=2)
        response = self.client.post(reverse('seat_payment', kwargs={'seat_id': seat.id}))
        self.assertEqual(response.status_code, 302)  # Перенаправление после успеха
        self.assertEqual(self.user.balance, 950.00)  # Баланс уменьшен на 50.00
        seat.refresh_from_db()
        self.assertTrue(seat.is_taken)

    def test_seat_payment_insufficient_funds(self):
        self.user.balance = 10.00
        self.user.save()
        seat = Seat.objects.create(event=self.event, row=1, number=3)
        response = self.client.post(reverse('seat_payment', kwargs={'seat_id': seat.id}))
        self.assertEqual(response.status_code, 200)  # Должно отобразить шаблон с ошибкой
        self.assertContains(response, 'Недостаточно средств')

    def test_process_payment_success(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            event=self.event,
            seat=self.seat,
            quantity=1
        )
        response = self.client.post(reverse('process_payment'))
        self.assertEqual(response.status_code, 302)  # Перенаправление после успеха
        self.assertEqual(self.user.balance, 950.00)  # Баланс уменьшен на 50.00
        self.assertTrue(Ticket.objects.filter(user=self.user, event=self.event).exists())
        self.assertFalse(CartItem.objects.filter(user=self.user).exists())

    def test_process_payment_insufficient_funds(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            event=self.event,
            seat=self.seat,
            quantity=1
        )
        self.user.balance = 10.00
        self.user.save()
        response = self.client.post(reverse('process_payment'))
        self.assertEqual(response.status_code, 302)  # Перенаправление с ошибкой
        self.assertContains(response, 'Недостаточно средств', status_code=200, msg_prefix='Ошибка в сообщении')
        self.assertTrue(CartItem.objects.filter(user=self.user).exists())

    def test_process_single_payment_success(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            event=self.event,
            seat=self.seat,
            quantity=1
        )
        response = self.client.post(reverse('process_single_payment', kwargs={'item_id': cart_item.id}))
        self.assertEqual(response.status_code, 302)  # Перенаправление после успеха
        self.assertEqual(self.user.balance, 950.00)  # Баланс уменьшен на 50.00
        self.assertTrue(Ticket.objects.filter(user=self.user, event=self.event).exists())
        self.assertFalse(CartItem.objects.filter(id=cart_item.id).exists())

    def test_process_single_payment_insufficient_funds(self):
        cart_item = CartItem.objects.create(
            user=self.user,
            event=self.event,
            seat=self.seat,
            quantity=1
        )
        self.user.balance = 10.00
        self.user.save()
        response = self.client.post(reverse('process_single_payment', kwargs={'item_id': cart_item.id}))
        self.assertEqual(response.status_code, 302)  # Перенаправление с ошибкой
        self.assertContains(response, 'Недостаточно средств', status_code=200, msg_prefix='Ошибка в сообщении')
        self.assertTrue(CartItem.objects.filter(id=cart_item.id).exists())