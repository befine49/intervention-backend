from rest_framework import serializers
from .models import Intervention, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    user_type = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'user_type', 'email', 'first_name', 'last_name']

class MessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    
    class Meta:
        model = Message
        fields = ['id', 'content', 'timestamp', 'user', 'message_type', 'message_type_display', 'is_read']

class InterventionSerializer(serializers.ModelSerializer):
    assigned_to = UserSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    available_employees = serializers.SerializerMethodField()

    class Meta:
        model = Intervention
        fields = [
            'id', 'title', 'description', 'problem_type', 'priority', 'priority_display',
            'assigned_to', 'created_by', 'status', 'status_display', 
            'created_at', 'updated_at', 'messages', 'available_employees',
            'chat_ended_by_employee', 'chat_ended_at', 'chat_rating'
        ]
    
    def get_available_employees(self, obj):
        """Return available employees for this intervention"""
        employees = obj.get_available_employees()
        return UserSerializer(employees, many=True).data
