from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import News, CustomUser, Events


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
        fields = ['title', 'content', 'image']
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
        }