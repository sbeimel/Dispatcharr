from django.urls import path
from .views import M3UDashboardView

urlpatterns = [
    path('dashboard', M3UDashboardView.as_view(), name='m3u_dashboard'),
]
