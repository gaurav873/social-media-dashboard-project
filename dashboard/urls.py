from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='dashboard/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('disconnect-twitter/', views.disconnect_twitter, name='disconnect_twitter'),
    path('connect-twitter/', views.connect_twitter, name='connect_twitter'),
    path('twitter/callback/', views.twitter_callback, name='twitter_callback'),
] 