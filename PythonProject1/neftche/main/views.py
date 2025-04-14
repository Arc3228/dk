from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, get_object_or_404, redirect
from .models import Circle, News
from django.contrib.auth.decorators import login_required



def home(request):
    latest_news = News.objects.order_by('-pub_date')[:3]
    return render(request, 'main/home.html', {'latest_news': latest_news})


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

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})

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