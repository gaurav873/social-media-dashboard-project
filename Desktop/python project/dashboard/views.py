from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile
from .api_utils import fetch_twitter_posts, fetch_instagram_posts
import logging

# Create your views here.

# User Registration
def register_view(request):
    try:
        if request.method == 'POST':
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            if not username or not password:
                messages.error(request, 'Username and password are required.')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                messages.success(request, 'Registration successful. Please log in.')
                return redirect('login')
        return render(request, 'dashboard/register.html')
    except Exception as e:
        logging.error(f"Error in register_view: {e}")
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return render(request, 'dashboard/register.html')

# User Login
from django.contrib.auth.views import LoginView, LogoutView

# Profile Update
@login_required
def profile_view(request):
    try:
        profile = request.user.profile
        if request.method == 'POST':
            bio = request.POST.get('bio', '')
            profile.bio = bio
            profile.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
        return render(request, 'dashboard/profile.html', {'profile': profile})
    except Exception as e:
        logging.error(f"Error in profile_view: {e}")
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return render(request, 'dashboard/profile.html', {'profile': request.user.profile})

@login_required
def dashboard_view(request):
    try:
        twitter_posts = fetch_twitter_posts()
        instagram_posts = fetch_instagram_posts()
        return render(request, 'dashboard/dashboard.html', {
            'twitter_posts': twitter_posts,
            'instagram_posts': instagram_posts,
        })
    except Exception as e:
        logging.error(f"Error in dashboard_view: {e}")
        messages.error(request, 'Unable to load your dashboard at this time. Please try again later.')
        return render(request, 'dashboard/dashboard.html', {
            'twitter_posts': [],
            'instagram_posts': [],
        })
