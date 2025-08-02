from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Q
from .models import Intervention, Message
from .serializers import InterventionSerializer, MessageSerializer

class InterventionViewSet(viewsets.ModelViewSet):
    serializer_class = InterventionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_employee():
            # Employees can see all interventions
            return Intervention.objects.all()
        else:
            # Clients can only see their own interventions
            return Intervention.objects.filter(created_by=user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def assign_employee(self, request, pk=None):
        """Assign an employee to an intervention"""
        intervention = self.get_object()
        employee_id = request.data.get('employee_id')
        
        if not employee_id:
            return Response({'error': 'employee_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from authentication.models import User
            employee = User.objects.get(id=employee_id, user_type__in=['employee', 'admin'])
            intervention.assigned_to = employee
            intervention.status = 'in_progress'
            intervention.save()
            
            # Create a system message
            Message.objects.create(
                intervention=intervention,
                user=request.user,
                content=f"Intervention assigned to {employee.get_full_name() or employee.username}",
                message_type='system_message'
            )
            
            return Response({'message': 'Employee assigned successfully'})
        except User.DoesNotExist:
            return Response({'error': 'Employee not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update intervention status"""
        intervention = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Intervention.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        intervention.status = new_status
        intervention.save()
        
        # Create a system message
        Message.objects.create(
            intervention=intervention,
            user=request.user,
            content=f"Status updated to: {intervention.get_status_display()}",
            message_type='system_message'
        )
        
        return Response({'message': 'Status updated successfully'})

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        intervention_id = self.kwargs['intervention_pk']
        return Message.objects.filter(intervention_id=intervention_id).order_by('timestamp')
    
    def perform_create(self, serializer):
        intervention_id = self.kwargs['intervention_pk']
        intervention = Intervention.objects.get(id=intervention_id)
        
        # Determine message type based on user type
        user = self.request.user
        if user.is_employee():
            message_type = 'employee_message'
        else:
            message_type = 'client_message'
        
        serializer.save(
            intervention=intervention,
            user=user,
            message_type=message_type
        )
