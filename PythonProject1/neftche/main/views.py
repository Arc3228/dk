from django.shortcuts import render, get_object_or_404
from .models import Circle, News


def home(request):
    latest_news = News.objects.order_by('-pub_date')[:3]
    return render(request, 'main/home.html', {'latest_news': latest_news})


def circles(request):
    circles = Circle.objects.all()
    return render(request, 'main/circles.html', {'circles': circles})


def contacts(request):
    return render(request, 'main/contacts.html')


def news_list(request):
    news = News.objects.order_by('-pub_date')
    return render(request, 'main/news_list.html', {'news_list': news})


def news_detail(request, news_id):
    item = get_object_or_404(News, id=news_id)
    return render(request, 'main/news_detail.html', {'news': item})