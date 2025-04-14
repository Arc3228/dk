from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The Phone field must be set')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone, password, **extra_fields)


class Role(models.Model):
    ROLE_TYPES = [
        ('admin', 'Администратор'),
        ('bibliographer', 'Библиограф'),
        ('chief', 'Руководитель клубного формирования'),
        ('user', 'Пользователь'),
        ('guest', 'Гость'),
    ]

    name = models.CharField(max_length=50, choices=ROLE_TYPES, unique=True, verbose_name="Название роли")
    description = models.TextField(verbose_name="Описание роли", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return self.get_name_display()

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"


class User(AbstractBaseUser):
    name = models.CharField(max_length=30)
    surname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    education = models.CharField(max_length=100)
    prof = models.CharField(max_length=100)
    study_work = models.CharField(max_length=100)
    phone = models.CharField(max_length=18, unique=True)
    passport = models.CharField(max_length=11, unique=True)
    given = models.CharField(max_length=100)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Роль",
        related_name="users"
    )

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name', 'surname', 'lastname', 'date_of_birth', 'education', 'prof', 'study_work', 'passport',
                       'given']

    objects = UserManager()

    def __str__(self):
        return f"{self.surname} {self.name}"

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

class Circle(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='circles/', blank=True, null=True)

    def __str__(self):
        return self.name

class News(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    pub_date = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, default=1)