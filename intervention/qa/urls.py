from django.urls import path

from . views import QAListView

urlpatterns = [
    path('qa-list/', view=QAListView, name='qa-list'),
]
