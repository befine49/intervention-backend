from django.db import models
from django.conf import settings

class Intervention(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_for_client', 'Waiting for Client'),
        ('waiting_for_employee', 'Waiting for Employee'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    problem_type = models.CharField(max_length=100, blank=True, help_text="Type of problem (e.g., Technical, Billing, etc.)")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_interventions'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='created_interventions'
    )
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    chat_ended_by_employee = models.BooleanField(default=False)
    chat_ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.status})"
    
    def get_available_employees(self):
        """Get available employees who can handle this intervention"""
        from authentication.models import User
        return User.objects.filter(user_type__in=['employee', 'admin'])

    def end_chat_by_employee(self):
        from django.utils import timezone
        self.chat_ended_by_employee = True
        self.chat_ended_at = timezone.now()
        self.save()

class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('client_message', 'Client Message'),
        ('employee_message', 'Employee Message'),
        ('system_message', 'System Message'),
    ]
    
    intervention = models.ForeignKey(Intervention, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='client_message')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.intervention.id}] {self.user.username}: {self.content[:30]}"
    
    class Meta:
        ordering = ['timestamp']
