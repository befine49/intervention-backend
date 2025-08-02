from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('client', 'Client'),
        ('employee', 'Employee/Technician'),
        ('admin', 'Administrator'),
    ]
    
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='client')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    specialization = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def is_employee(self):
        return self.user_type in ['employee', 'admin']
    
    def is_client(self):
        return self.user_type == 'client'