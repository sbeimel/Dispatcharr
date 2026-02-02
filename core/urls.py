from django.urls import path
from .views import settings_view

urlpatterns = [
    path('', settings_view, name='settings'),
]
