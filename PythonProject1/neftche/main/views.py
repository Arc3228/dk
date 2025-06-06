import base64
from decimal import Decimal
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from io import BytesIO
import qrcode
from django.conf import settings
from django.db.models.functions import TruncDay
from django.template.loader import get_template
from django.utils import timezone
from django.contrib.auth import login, authenticate
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date
from xhtml2pdf import pisa
from . import forms
from django.core.mail import send_mail
from django.db.models import Sum, Count, F
from .forms import NewsForm, SignUpForm, LoginForm, EventsForm, TicketPurchaseForm, BalanceTopUpForm, HallBookingForm
from django.contrib import messages
from .models import News, Events, Ticket, HallBooking, Seat, create_seats_for_event, PaymentHistory, CartItem, Chat
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model

def home(request):
    latest_news = News.objects.order_by('-pub_date')[:3]
    events = Events.objects.filter(is_archived=False).order_by('-pub_date')[:5]
    return render(request, 'main/home.html', {'latest_news': latest_news, 'events': events})


def news_list(request):
    news_list = News.objects.order_by('-pub_date')
    return render(request, 'main/news_list.html', {'news_list': news_list})


def news_detail(request, news_id):
    item = get_object_or_404(News, id=news_id)
    return render(request, 'main/news_detail.html', {'news': item})


def events_list(request):
    events_list = Events.objects.filter(is_archived=False).order_by('-pub_date')
    return render(request, 'main/events_list.html', {'events_list': events_list})


def events_detail(request, events_id):
    item = get_object_or_404(Events, id=events_id)
    return render(request, 'main/events_detail.html', {'events': item})


@login_required(login_url='login')
def seat_payment(request, seat_id):
    seat = get_object_or_404(Seat, id=seat_id, is_taken=False)
    event = seat.event

    if request.method == 'POST':
        user = request.user
        if user.balance >= event.price:
            # Списание средств
            user.balance -= event.price
            user.save()

            # Бронирование места с сохранением пользователя
            seat.is_taken = True
            seat.user = user  # Это критически важная строка
            seat.save()

            # Создание билета
            ticket = Ticket.objects.create(
                event=event,
                user=user,
                quantity=1
            )

            messages.success(request, f'Место успешно оплачено! С вашего баланса списано {event.price} руб.')
            return redirect('ticket_detail', ticket_id=ticket.id)
        else:
            messages.error(request, 'Недостаточно средств на балансе. Пожалуйста, пополните баланс.')

    context = {
        'seat': seat,
        'event': event,
    }
    return render(request, 'main/seat_payment.html', context)

def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()          # Сохраняем нового пользователя
            login(request, user)        # Выполняем вход
            return redirect('home')     # Перенаправляем на главную страницу
    else:
        form = SignUpForm()
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    form = LoginForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password) # Проверяем учетные данные
            if user is not None:
                login(request, user)     # Выполняем вход
                return redirect('home')  # Перенаправляем на главную страницу
    return render(request, 'auth/login.html', {'form': form})


@staff_member_required
def admin_panel(request):
    return render(request, 'admin/admin_panel.html')


@staff_member_required
def news_create(request):
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES)
        if form.is_valid():
            news = form.save(commit=False)
            news.author = request.user
            news.save()
            return redirect('home')
    else:
        form = NewsForm()
    return render(request, 'main/news_form.html', {'form': form})


@staff_member_required
def news_edit(request, pk):
    news = News.objects.get(pk=pk)
    if request.user != news.author:
        return redirect('home')
    if request.method == 'POST':
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = NewsForm(instance=news)
    return render(request, 'main/news_form.html', {'form': form})


@staff_member_required
def news_delete(request, pk):
    news = News.objects.get(pk=pk)
    if request.user == news.author:
        news.delete()
    return redirect('home')


@staff_member_required
def events_create(request):
    if request.method == 'POST':
        form = EventsForm(request.POST, request.FILES)
        if form.is_valid():
            events = form.save(commit=False)
            events.author = request.user
            events.save()

            # ✅ создаём места после сохранения события
            create_seats_for_event(events)

            return redirect('home')
    else:
        form = EventsForm()
    return render(request, 'main/events_form.html', {'form': form})

@staff_member_required
def events_edit(request, pk):
    events = Events.objects.get(pk=pk)
    if request.user != events.author:
        return redirect('home')
    if request.method == 'POST':
        form = EventsForm(request.POST, request.FILES, instance=events)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = EventsForm(instance=events)
    return render(request, 'main/events_form.html', {'form': form})


@staff_member_required
def events_delete(request, pk):
    events = Events.objects.get(pk=pk)
    if request.user == events.author:
        events.delete()
    return redirect('home')





def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    # Получаем все места, связанные с билетом
    seats = ticket.seats.all()

    # Генерируем QR-код с информацией обо всех местах
    qr_data = f"Билет ID: {ticket.id}\nМероприятие: {ticket.event.title}\nВладелец: {request.user.username}\n"

    if seats.exists():
        for seat in seats:
            qr_data += f"Место: {seat.row}-{seat.number}\n"
    else:
        qr_data += "Места: Не указаны\n"

    context = {
        'ticket': ticket,
        'seats': seats,
        'qr_data': qr_data,
    }
    return render(request, 'main/ticket_detail.html', context)


# Регистрируем кириллический шрифт с абсолютным путем
font_path = os.path.join('main', 'static', 'main', 'fonts', 'Unbounded-Regular.ttf')
pdfmetrics.registerFont(TTFont('Unbounded', font_path))


@login_required
def download_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    seats = ticket.seats.all()
    event = ticket.event

    # Создаем буфер для PDF
    buffer = io.BytesIO()

    # Создаем PDF-документ
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Устанавливаем кириллический шрифт
    p.setFont("Unbounded", 12)

    # Заголовок
    p.setFont("Unbounded", 18)
    p.drawCentredString(width / 2, height - 2 * cm, "БИЛЕТ НА МЕРОПРИЯТИЕ")
    p.line(1 * cm, height - 2.5 * cm, width - 1 * cm, height - 2.5 * cm)

    # Информация о билете
    y_position = height - 4 * cm

    # Основная информация
    p.drawString(2 * cm, y_position, f"Мероприятие: {event.title}")
    y_position -= 0.7 * cm
    p.drawString(2 * cm, y_position, f"Дата проведения: {event.data.strftime('%d.%m.%Y %H:%M')}")
    y_position -= 0.7 * cm
    p.drawString(2 * cm, y_position, f"Дата покупки: {ticket.purchased_at.strftime('%d.%m.%Y %H:%M')}")
    y_position -= 0.7 * cm

    # Информация о владельце
    p.setFont("Unbounded", 14)
    p.drawString(2 * cm, y_position, "ДАННЫЕ ПОСЕТИТЕЛЯ:")
    p.setFont("Unbounded", 14)
    y_position -= 0.7 * cm
    p.drawString(2 * cm, y_position, f"ФИО: {request.user.surname} {request.user.name} {request.user.lastname}")
    y_position -= 1.2 * cm

    # Информация о местах
    if seats.exists():
        p.setFont("Unbounded", 14)
        p.drawString(2 * cm, y_position, "МЕСТО:")
        p.setFont("Unbounded", 12)
        y_position -= 0.7 * cm

        for seat in seats:
            p.drawString(3 * cm, y_position, f"• Ряд {seat.row}, Место {seat.number}")
            y_position -= 0.7 * cm
    else:
        p.setFont("Unbounded", 14)
        p.drawString(2 * cm, y_position, "МЕСТА:")
        p.setFont("Unbounded", 12)
        y_position -= 0.7 * cm
        p.drawString(3 * cm, y_position, "Не указаны")
        y_position -= 0.7 * cm

    # Генерация QR-кода
    qr_data = f"Билет ID: {ticket.id}\nМероприятие: {event.title}\n"
    qr_data += f"Посетитель: {request.user.surname} {request.user.name} {request.user.lastname}\n"

    if seats.exists():
        qr_data += "Место:"
        for seat in seats:
            qr_data += f"  - Ряд {seat.row}, Место {seat.number}\n"
    else:
        qr_data += "Места: Не указаны\n"

    qr = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Создаем ImageReader из буфера
    qr_image = ImageReader(qr_buffer)

    # Размещаем QR-код в PDF
    qr_size = 9 * cm
    qr_x = width - 6 * cm - qr_size
    qr_y = 3 * cm
    p.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)

    # Добавляем подпись под QR-код
    p.setFont("Unbounded", 10)
    p.drawCentredString(width - 6 * cm - qr_size / 2, 2.5 * cm, "QR-код билета")

    # Добавляем рамку
    p.rect(1 * cm, 1 * cm, width - 2 * cm, height - 2 * cm)

    # Завершаем PDF
    p.showPage()
    p.save()

    # Возвращаем PDF как ответ
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket_id}.pdf"'
    return response




@login_required
def profile(request):
    user = request.user
    tickets = user.tickets.filter(user=user)
    hall_bookings = HallBooking.objects.filter(user=user)

    return render(request, 'main/profile.html', {
        'user': user,
        'tickets': tickets,
        'hall_bookings': hall_bookings,
    })



@login_required
def top_up_balance(request):
    if request.method == 'POST':
        form = BalanceTopUpForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            request.user.balance += amount
            request.user.save()
            messages.success(request, f'Баланс успешно пополнен на {amount}₽')
            return redirect('profile')
    else:
        form = BalanceTopUpForm()
    return render(request, 'main/top_up_balance.html', {'form': form})


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

            if start_new < end_existing and end_new > start_existing:
                raise forms.ValidationError(
                    f"Зал уже забронирован с {start_existing.strftime('%H:%M')} до {end_existing.strftime('%H:%M')}."
                )

    return cleaned_data


@login_required
def book_hall(request):
    form = HallBookingForm(request.POST or None, user=request.user)
    selected_date = request.GET.get('date')

    if selected_date:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            bookings = HallBooking.objects.filter(date=date_obj).order_by('time')
        except ValueError:
            bookings = HallBooking.objects.all().order_by('date', 'time')
    else:
        bookings = HallBooking.objects.all().order_by('date', 'time')

    for booking in bookings:
        start = datetime.combine(booking.date, booking.time)
        booking.end_time = (start + timedelta(hours=booking.duration)).time()

    if request.method == 'POST' and form.is_valid():
        booking = form.save(commit=False)
        price = form.cleaned_data.get('calculated_price')

        # Списание денег
        request.user.balance -= price
        request.user.save()

        booking.price = price
        booking.user = request.user
        booking.save()

        # Создаем запись о платеже
        PaymentHistory.objects.create(
            user=request.user,
            amount=price,
            description=f"Бронирование зала: {booking.event_name} {booking.date} {booking.time.strftime('%H:%M')}"
        )

        messages.success(request, f"Зал успешно забронирован. С вашего баланса списано {price} ₽.")
        return redirect('book_hall')

    return render(request, 'main/book_hall.html', {
        'form': form,
        'bookings': bookings,
        'selected_date': selected_date,
    })




@staff_member_required
def hall_bookings_view(request):
    bookings = HallBooking.objects.all().filter().order_by('date')
    return render(request, 'main/hall_bookings.html', {'bookings': bookings})

def get_booked_slots(request):
    bookings = HallBooking.objects.all().values('date', 'start_time', 'end_time')
    return JsonResponse(list(bookings), safe=False)


@staff_member_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(HallBooking, id=booking_id)
    if request.method == 'POST':
        form = HallBookingForm(request.POST, instance=booking, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('hall_bookings')
    else:
        form = HallBookingForm(instance=booking, user=request.user)
    return render(request, 'main/edit_booking.html', {'form': form, 'booking': booking})


@staff_member_required
def delete_booking(request, booking_id):
    booking = get_object_or_404(HallBooking, id=booking_id)

    if request.method == 'POST':
        # Используем транзакцию для гарантии целостности данных
        with transaction.atomic():
            # Получаем пользователя и сумму до удаления брони
            user = booking.user
            refund_amount = Decimal(booking.price)

            # Удаляем бронирование
            booking.delete()

            # Возвращаем средства на баланс пользователя
            user.balance += refund_amount
            user.save()

        return redirect('hall_bookings')
    return render(request, 'main/delete_booking.html', {'booking': booking})

@login_required
def payment_history(request):
    # Получаем платежи и билеты пользователя
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-created_at')
    tickets = Ticket.objects.filter(user=request.user).select_related('event').order_by('-purchased_at')
    # Получаем архивные мероприятия и бронирования
    archived_events = Events.objects.filter(is_archived=True, author=request.user).order_by('-data')
    archived_bookings = HallBooking.objects.filter(is_archived=True, user=request.user).order_by('-date')

    # Рассчитываем общую сумму платежей
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0

    # Рассчитываем общую сумму билетов
    total_tickets = sum(ticket.event.price * ticket.quantity for ticket in tickets)

    return render(request, 'main/payment_history.html', {
        'payments': payments,
        'tickets': tickets,
        'total_payments': total_payments,
        'total_tickets': total_tickets,
        'archived_events': archived_events,
        'archived_bookings': archived_bookings,
    })


def update_archives():
    # Update Events
    for event in Events.objects.filter(is_archived=False):
        if event.data and event.data < timezone.now():
            event.is_archived = True
            event.save()

    # Update HallBookings
    for booking in HallBooking.objects.filter(is_archived=False):
        booking_datetime = timezone.datetime.combine(booking.date, booking.time)
        booking_datetime = timezone.make_aware(booking_datetime)
        if booking_datetime < timezone.now():
            booking.is_archived = True
            booking.save()


logger = logging.getLogger(__name__)

@staff_member_required
def site_statistics(request):
    User = get_user_model()

    # Получаем параметры фильтрации
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    event_id = request.GET.get('event')

    # Инициализация переменных
    start = end = None
    selected_event = None
    total_tickets_sold = 0
    event_revenue = 0

    # Парсим даты
    if start_date and end_date:
        try:
            start = parse_date(start_date)
            end = parse_date(end_date)
        except:
            pass

    # Получаем все мероприятия для выпадающего списка
    all_events = Events.objects.all()

    # Фильтрация по мероприятию
    if event_id:
        try:
            selected_event = Events.objects.get(id=event_id)
        except Events.DoesNotExist:
            pass

    # Базовые querysets
    news_queryset = News.objects.all()
    booking_queryset = HallBooking.objects.all()
    ticket_queryset = Ticket.objects.select_related('event')
    payment_queryset = PaymentHistory.objects.all()
    events_queryset = Events.objects.all()

    # Применяем фильтры дат
    if start and end:
        news_queryset = news_queryset.filter(pub_date__date__range=[start, end])
        booking_queryset = booking_queryset.filter(date__range=[start, end])
        ticket_queryset = ticket_queryset.filter(purchased_at__date__range=[start, end])
        payment_queryset = payment_queryset.filter(created_at__date__range=[start, end])
        events_queryset = events_queryset.filter(data__date__range=[start, end])

    # Фильтрация по выбранному мероприятию
    if selected_event:
        ticket_queryset = ticket_queryset.filter(event=selected_event)
        payment_queryset = payment_queryset.filter(description__icontains=selected_event.title)
        booking_queryset = booking_queryset.filter(event_name__icontains=selected_event.title)
        events_queryset = events_queryset.filter(id=selected_event.id)

    # Основная статистика
    total_users = User.objects.count()
    total_news = news_queryset.count()
    total_events_count = events_queryset.count()
    total_bookings = booking_queryset.count()

    # Расчет выручки
    total_hall_revenue = booking_queryset.aggregate(total=Sum('price'))['total'] or 0
    total_ticket_revenue = ticket_queryset.aggregate(
        total=Sum(F('event__price') * F('quantity'))
    )['total'] or 0
    total_payment_revenue = payment_queryset.aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = total_hall_revenue + total_ticket_revenue + total_payment_revenue

    # Статистика по выбранному мероприятию
    if selected_event:
        total_tickets_sold = ticket_queryset.aggregate(total=Sum('quantity'))['total'] or 0
        total_ticket_revenue = ticket_queryset.aggregate(
            total=Sum(F('event__price') * F('quantity'))
        )['total'] or 0
        payment_revenue = payment_queryset.filter(
            description__icontains=selected_event.title
        ).aggregate(total=Sum('amount'))['total'] or 0
        event_revenue = total_ticket_revenue + payment_revenue
    else:
        total_tickets_sold = 0
        event_revenue = 0

    # Данные для графика выручки
    revenue_data = []
    if selected_event:
        ticket_data = (
            Ticket.objects
            .filter(event=selected_event)
            .annotate(day=TruncDay('purchased_at'))
            .values('day')
            .annotate(
                total=Sum(F('event__price') * F('quantity')),
                tickets_sold=Sum('quantity')
            )
        )
        payment_data = (
            PaymentHistory.objects
            .filter(description__icontains=selected_event.title)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('amount'))
        )
        combined_data = {}
        for item in ticket_data:
            day_str = item['day'].strftime('%Y-%m-%d') if item['day'] else None
            if day_str:
                combined_data[day_str] = {
                    'total': combined_data.get(day_str, {}).get('total', 0) + (item['total'] or 0),
                    'tickets_sold': item['tickets_sold'] or 0
                }
        for item in payment_data:
            day_str = item['day'].strftime('%Y-%m-%d') if item['day'] else None
            if day_str:
                combined_data[day_str] = {
                    'total': combined_data.get(day_str, {}).get('total', 0) + (item['total'] or 0),
                    'tickets_sold': combined_data.get(day_str, {}).get('tickets_sold', 0)
                }
        revenue_data = [
            {'day': day, 'total': float(data['total']), 'tickets_sold': data['tickets_sold']}
            for day, data in combined_data.items()
        ]
        revenue_data.sort(key=lambda x: x['day'])
    else:
        hall_data = (
            HallBooking.objects
            .annotate(day=TruncDay('date'))
            .values('day')
            .annotate(total=Sum('price'))
        )
        ticket_data = (
            Ticket.objects
            .annotate(day=TruncDay('purchased_at'))
            .values('day')
            .annotate(
                total=Sum(F('event__price') * F('quantity')),
                tickets_sold=Sum('quantity')
            )
        )
        payment_data = (
            PaymentHistory.objects
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('amount'))
        )
        combined_data = {}
        for item in hall_data:
            day_str = item['day'].strftime('%Y-%m-%d') if item['day'] else None
            if day_str:
                combined_data[day_str] = {
                    'total': combined_data.get(day_str, {}).get('total', 0) + (item['total'] or 0),
                    'tickets_sold': combined_data.get(day_str, {}).get('tickets_sold', 0)
                }
        for item in ticket_data:
            day_str = item['day'].strftime('%Y-%m-%d') if item['day'] else None
            if day_str:
                combined_data[day_str] = {
                    'total': combined_data.get(day_str, {}).get('total', 0) + (item['total'] or 0),
                    'tickets_sold': item['tickets_sold'] or 0
                }
        for item in payment_data:
            day_str = item['day'].strftime('%Y-%m-%d') if item['day'] else None
            if day_str:
                combined_data[day_str] = {
                    'total': combined_data.get(day_str, {}).get('total', 0) + (item['total'] or 0),
                    'tickets_sold': combined_data.get(day_str, {}).get('tickets_sold', 0)
                }
        revenue_data = [
            {'day': day, 'total': float(data['total']), 'tickets_sold': data['tickets_sold']}
            for day, data in combined_data.items()
        ]
        revenue_data.sort(key=lambda x: x['day'])

    # Логирование для отладки
    logger.debug(f"Revenue Data: {revenue_data}")
    logger.debug(f"Total Revenue: {total_revenue}, Event Revenue: {event_revenue}")

    return render(request, 'main/site_statistics.html', {
        'total_users': total_users,
        'total_news': total_news,
        'total_events': total_events_count,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'revenue_data': json.dumps(revenue_data),
        'all_events': all_events,
        'selected_event': selected_event,
        'total_tickets_sold': total_tickets_sold,
        'event_revenue': event_revenue,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def add_to_cart(request, event_id, seat_id):
    event = get_object_or_404(Events, id=event_id)
    seat = get_object_or_404(Seat, id=seat_id, event=event)

    # Проверяем, занято ли место
    if seat.is_taken:
        messages.error(request, 'Это место уже занято.')
        return redirect('events_detail', events_id=event.id)

    # Создаем/обновляем элемент корзины
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        event=event,
        seat=seat
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    # Блокируем место
    seat.is_taken = True
    seat.user = request.user
    seat.save()

    messages.success(request, f'Место {seat.row}-{seat.number} добавлено в корзину.')
    return redirect('events_detail', events_id=event.id)


@login_required
def view_cart(request):
    # Удаляем устаревшие элементы и освобождаем места
    old_items = CartItem.objects.filter(
        user=request.user,
        added_at__lt=timezone.now() - timedelta(minutes=15)
    )

    for item in old_items:
        seat = item.seat
        seat.is_taken = False
        seat.user = None
        seat.save()
        item.delete()

    cart_items = CartItem.objects.filter(user=request.user)
    total_price = sum(item.event.price * item.quantity for item in cart_items)

    return render(request, 'main/cart.html', {
        'cart_items': cart_items,
        'total_price': total_price
    })


@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    seat = cart_item.seat

    # Освобождаем место
    seat.is_taken = False
    seat.user = None
    seat.save()

    cart_item.delete()
    messages.info(request, 'Билет удален из корзины. Место снова доступно.')
    return redirect('view_cart')


@transaction.atomic
@login_required
def process_payment(request):
    cart_items = CartItem.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.warning(request, 'Корзина пуста.')
        return redirect('view_cart')

    total_price = sum(item.event.price * item.quantity for item in cart_items)
    user = request.user

    if user.balance < total_price:
        messages.error(request, 'Недостаточно средств на балансе.')
        return redirect('view_cart')

    try:
        # Списание средств
        user.balance -= total_price
        user.save()

        # Создание билетов и привязка мест
        for item in cart_items:
            ticket = Ticket.objects.create(
                event=item.event,
                user=user,
                quantity=item.quantity
            )
            ticket.seats.add(item.seat)  # ← Сохраняем место в билете

        # Очистка корзины
        cart_items.delete()

        messages.success(request, 'Оплата прошла успешно! Билеты оформлены.')

    except Exception as e:
        messages.error(request, 'Ошибка при обработке оплаты. Пожалуйста, попробуйте позже.')
        return redirect('view_cart')

    return redirect('view_cart')


@transaction.atomic
@login_required
def process_single_payment(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    total_price = cart_item.event.price * cart_item.quantity
    user = request.user

    if user.balance < total_price:
        messages.error(request, 'Недостаточно средств на балансе.')
        return redirect('view_cart')

    try:
        # Списание средств
        user.balance -= total_price
        user.save()

        # Создание билета и привязка места
        ticket = Ticket.objects.create(
            event=cart_item.event,
            user=user,
            quantity=cart_item.quantity
        )
        ticket.seats.add(cart_item.seat)  # ← Сохраняем место в билете

        # Удаление из корзины
        cart_item.delete()

        messages.success(request, 'Билет успешно оплачен!')

    except Exception as e:
        messages.error(request, 'Ошибка при оплате билета. Пожалуйста, попробуйте позже.')

    return redirect('view_cart')




@login_required
def user_chat(request):
    # Создаем чат для пользователя, если его нет
    chat, created = Chat.objects.get_or_create(user=request.user)
    messages = chat.messages.order_by('timestamp')
    return render(request, 'chat/user_chat.html', {'chat': chat, 'messages': messages})

@staff_member_required
def admin_chat_list(request):
    chats = Chat.objects.all().prefetch_related('messages')
    return render(request, 'chat/admin_chat_list.html', {'chats': chats})

@staff_member_required
def admin_chat(request, chat_id):
    chat = Chat.objects.get(id=chat_id)
    messages = chat.messages.order_by('timestamp')
    return render(request, 'chat/admin_chat.html', {'chat': chat, 'messages': messages})