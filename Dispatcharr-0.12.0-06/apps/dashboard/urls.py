from django.urls import path
from .views import dashboard_view, settings_view, live_dashboard_data

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('settings/', settings_view, name='settings'),
    path('api/dashboard-data/', live_dashboard_data, name='dashboard_data'),
]
