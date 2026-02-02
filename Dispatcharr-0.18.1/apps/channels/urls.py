from django.urls import path
from .views import StreamDashboardView, channels_dashboard_view

app_name = 'channels_dashboard'

urlpatterns = [
    # Example “dashboard” routes for streams
    path('streams/', StreamDashboardView.as_view(), name='stream_dashboard'),

    # Example “dashboard” route for channels
    path('channels/', channels_dashboard_view, name='channels_dashboard'),
]
