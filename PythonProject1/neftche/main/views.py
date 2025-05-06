import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO

import qrcode
from django.template.loader import get_template
from django.utils import timezone
from django.contrib.auth import login, authenticate
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.dateparse import parse_date
from xhtml2pdf import pisa

from . import forms
from django.db.models import Sum, Count, F
from .forms import NewsForm, SignUpForm, LoginForm, EventsForm, TicketPurchaseForm, BalanceTopUpForm, HallBookingForm
from django.contrib import messages
from .models import News, Events, Ticket, HallBooking, Seat, create_seats_for_event, PaymentHistory, CartItem
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from qr_code.qrcode.utils import QRCodeOptions

def home(request):
    latest_news = News.objects.order_by('-pub_date')[:3]
    events = Events.objects.all().order_by('-pub_date')[:5]
    return render(request, 'main/home.html', {'latest_news': latest_news, 'events': events})


def news_list(request):
    news_list = News.objects.order_by('-pub_date')
    return render(request, 'main/news_list.html', {'news_list': news_list})


def news_detail(request, news_id):
    item = get_object_or_404(News, id=news_id)
    return render(request, 'main/news_detail.html', {'news': item})


def events_list(request):
    events_list = Events.objects.order_by('-pub_date')
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


@login_required
def admin_panel(request):
    return render(request, 'admin/admin_panel.html')


@login_required
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


@login_required
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


@login_required
def news_delete(request, pk):
    news = News.objects.get(pk=pk)
    if request.user == news.author:
        news.delete()
    return redirect('home')


@login_required
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

@login_required
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


@login_required
def events_delete(request, pk):
    events = Events.objects.get(pk=pk)
    if request.user == events.author:
        events.delete()
    return redirect('home')


@login_required
def buy_ticket(request, events_id):
    event = get_object_or_404(Events, id=events_id)

    if request.method == 'POST':
        if request.user.balance >= event.price:
            Ticket.objects.create(user=request.user, event=event)
            request.user.balance -= event.price
            request.user.save()
            messages.success(request, f'Вы успешно купили билет на "{event.title}"!')
            return redirect('profile')
        else:
            messages.error(request, 'Недостаточно средств для покупки билета.')
            return redirect('top_up_balance')

    return render(request, 'main/buy_ticket.html', {'event': event})


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


@login_required
def download_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    seats = ticket.seats.all()
    event = ticket.event

    # Генерация QR-кода
    qr_data = f"Билет ID: {ticket.id}\nМероприятие: {event.title}\nВладелец: {request.user.username}\n"
    if seats.exists():
        for seat in seats:
            qr_data += f"Место: {seat.row}-{seat.number}\n"
    else:
        qr_data += "Места: Не указаны\n"

    qr = qrcode.make(qr_data)
    qr_bytes = BytesIO()
    qr.save(qr_bytes, format='PNG')
    qr_base64 = base64.b64encode(qr_bytes.getvalue()).decode('utf-8')

    context = {
        'ticket': ticket,
        'event': event,
        'user': request.user,
        'seats': seats,
        'qr_code': qr_base64,
    }

    template = get_template('main/ticket_pdf.html')
    html = template.render(context)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket_id}.pdf"'
        return response

    return HttpResponse('Ошибка генерации PDF', status=500)


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




@login_required
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
        form = HallBookingForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            return redirect('hall_bookings')
    else:
        form = HallBookingForm(instance=booking)
    return render(request, 'main/edit_booking.html', {'form': form, 'booking': booking})


@staff_member_required
def delete_booking(request, booking_id):
    booking = get_object_or_404(HallBooking, id=booking_id)
    if request.method == 'POST':
        booking.delete()
        return redirect('hall_bookings')
    return render(request, 'main/delete_booking.html', {'booking': booking})

@login_required
def payment_history(request):
    # Получаем платежи и билеты пользователя
    payments = PaymentHistory.objects.filter(user=request.user).order_by('-created_at')
    tickets = Ticket.objects.filter(user=request.user).select_related('event').order_by('-purchased_at')

    # Рассчитываем общую сумму платежей
    total_payments = payments.aggregate(total=Sum('amount'))['total'] or 0

    # Рассчитываем общую сумму билетов
    total_tickets = sum(ticket.event.price * ticket.quantity for ticket in tickets)

    return render(request, 'main/payment_history.html', {
        'payments': payments,
        'tickets': tickets,
        'total_payments': total_payments,
        'total_tickets': total_tickets
    })


@staff_member_required
def site_statistics(request):
    User = get_user_model()

    # Получаем параметры фильтрации
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # Парсим даты
    start = None
    end = None
    if start_date and end_date:
        try:
            start = parse_date(start_date)
            end = parse_date(end_date)
        except:
            pass

    news_queryset = News.objects.all()
    booking_queryset = HallBooking.objects.all()
    ticket_queryset = Ticket.objects.select_related('event')

    if start and end:
        news_queryset = news_queryset.filter(pub_date__date__range=[start, end])
        booking_queryset = booking_queryset.filter(date__range=[start, end])
        ticket_queryset = ticket_queryset.filter(purchased_at__date__range=[start, end])

    total_users = User.objects.count()
    total_news = news_queryset.count()
    total_bookings = booking_queryset.count()

    # Общая выручка
    total_hall_revenue = booking_queryset.aggregate(total=Sum('price'))['total'] or 0
    total_ticket_revenue = ticket_queryset.aggregate(
        total=Sum(F('event__price') * F('quantity'))
    )['total'] or 0
    total_revenue = total_hall_revenue + total_ticket_revenue

    # Самый популярный день
    popular_booking_date = booking_queryset.values('date').annotate(count=Count('id')).order_by('-count').first()

    # График: выручка по дням (за последние 30 дней или за выбранный период)
    # График: выручка по дням
    if start:
        revenue_data = (
            HallBooking.objects
            .filter(date__gte=start - timedelta(days=30))
            .extra({'day': "date(date)"})
            .values('day')
            .annotate(total=Sum('price'))
            .order_by('day')
        )
    else:
        # Берём данные за последние 30 дней
        last_30_days = datetime.today() - timedelta(days=30)
        revenue_data = (
            HallBooking.objects
            .filter(date__gte=last_30_days)
            .extra({'day': "date(date)"})
            .values('day')
            .annotate(total=Sum('price'))
            .order_by('day')
        )


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