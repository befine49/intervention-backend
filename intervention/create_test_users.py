#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intervention.settings')
django.setup()

from authentication.models import User
from rest_framework.authtoken.models import Token

def create_test_users():
    # Create a client user
    client, created = User.objects.get_or_create(
        username='client1',
        defaults={
            'email': 'client1@example.com',
            'first_name': 'John',
            'last_name': 'Client',
            'user_type': 'client',
            'is_staff': False,
            'is_superuser': False
        }
    )
    if created:
        client.set_password('password123')
        client.save()
        Token.objects.create(user=client)
        print(f"Created client user: {client.username}")

    # Create an employee user
    employee, created = User.objects.get_or_create(
        username='employee1',
        defaults={
            'email': 'employee1@example.com',
            'first_name': 'Sarah',
            'last_name': 'Technician',
            'user_type': 'employee',
            'department': 'Technical Support',
            'specialization': 'Software Issues',
            'is_staff': True,
            'is_superuser': False
        }
    )
    if created:
        employee.set_password('password123')
        employee.save()
        Token.objects.create(user=employee)
        print(f"Created employee user: {employee.username}")

    # Create an admin user
    admin, created = User.objects.get_or_create(
        username='admin1',
        defaults={
            'email': 'admin1@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'user_type': 'admin',
            'department': 'Management',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('password123')
        admin.save()
        Token.objects.create(user=admin)
        print(f"Created admin user: {admin.username}")

    print("\nTest users created successfully!")
    print("Client credentials: client1 / password123")
    print("Employee credentials: employee1 / password123")
    print("Admin credentials: admin1 / password123")

if __name__ == '__main__':
    create_test_users() 