from django.urls import path
from .views import EPGDashboardView, epg_view

app_name = 'epg_dashboard'

urlpatterns = [
    path('dashboard/', EPGDashboardView.as_view(), name='epg_dashboard'),
    path('guide/', epg_view, name='epg_guide'),
]
