from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import InterventionViewSet, MessageViewSet

# Main router for interventions
router = DefaultRouter()
router.register(r'interventions', InterventionViewSet, basename='intervention')

# Nested router for messages inside interventions
nested_router = NestedDefaultRouter(router, r'interventions', lookup='intervention')
nested_router.register(r'messages', MessageViewSet, basename='intervention-messages')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(nested_router.urls)),
]
