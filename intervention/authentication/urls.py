from django.urls import path

from .views import register, login, employees

urlpatterns = [
    path('login', login, name='login'),
    path('register', register, name='register'),
    path('employees/', employees, name='employees'),
]