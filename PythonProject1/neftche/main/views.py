from django.contrib.auth import login, authenticate
from django.shortcuts import render, get_object_or_404, redirect
from .forms import NewsForm, SignUpForm, LoginForm, EventsForm, TicketPurchaseForm, BalanceTopUpForm
from django.contrib import messages
from .models import Circle, News, Events, Ticket
from django.contrib.auth.decorators import login_required



def home(request):
    latest_news = News.objects.order_by('-pub_date')[:3]
    events = Events.objects.all().order_by('-pub_date')[:5]
    return render(request, 'main/home.html', {'latest_news': latest_news, 'events': events})


def circles(request):
    circles = Circle.objects.all()
    return render(request, 'main/circles.html', {'circles': circles})


def contacts(request):
    return render(request, 'main/contacts.html')


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

@login_required
def profile(request):
    user = request.user
    tickets = user.tickets.all()
    return render(request, 'main/profile.html', {
        'user': user,
        'tickets': tickets,
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