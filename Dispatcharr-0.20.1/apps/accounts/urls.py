from django.urls import path
from django.contrib.auth import views as auth_views

app_name = 'accounts'

urlpatterns = [
    # Login view using Django's built-in authentication
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    # Logout view using Django's built-in authentication
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:login'), name='logout'),
    # Onetime use superuser account creation
]
