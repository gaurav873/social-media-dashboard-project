from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile
from .api_utils import fetch_twitter_posts, fetch_instagram_posts
import logging
from social_django.models import UserSocialAuth
import pkce
import secrets
import requests
import base64
import json
from urllib.parse import urlencode, quote
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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
    twitter_connected = False
    twitter_username = None
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            twitter_connected = profile.is_twitter_connected
            twitter_username = profile.twitter_username
        except Profile.DoesNotExist:
            twitter_connected = False
    
    try:
        twitter_posts = fetch_twitter_posts()
        instagram_posts = fetch_instagram_posts()
        return render(request, 'dashboard/dashboard.html', {
            'twitter_posts': twitter_posts,
            'instagram_posts': instagram_posts,
            'twitter_connected': twitter_connected,
            'twitter_username': twitter_username,
        })
    except Exception as e:
        logging.error(f"Error in dashboard_view: {e}")
        messages.error(request, 'Unable to load your dashboard at this time. Please try again later.')
        return render(request, 'dashboard/dashboard.html', {
            'twitter_posts': [],
            'instagram_posts': [],
            'twitter_connected': False,
            'twitter_username': None,
        })

@login_required
def disconnect_twitter(request):
    if request.method == 'POST':
        try:
            profile = request.user.profile
            # Clear Twitter-related fields
            profile.twitter_username = None
            profile.twitter_id = None
            profile.twitter_access_token = None
            profile.twitter_refresh_token = None
            profile.twitter_token_expires_at = None
            profile.save()
            
            # Clear session data
            request.session.pop('twitter_access_token', None)
            request.session.pop('twitter_refresh_token', None)
            
            messages.success(request, 'Twitter account disconnected successfully.')
        except Profile.DoesNotExist:
            messages.warning(request, 'No Twitter connection found to disconnect.')
        except Exception as e:
            logging.error(f"Error in disconnect_twitter: {e}")
            messages.error(request, 'An error occurred while disconnecting Twitter.')
    return redirect('dashboard')

def connect_twitter(request):
    """
    Initiate Twitter OAuth 2.0 flow with PKCE.
    """
    try:
        # Generate PKCE values
        code_verifier = pkce.generate_code_verifier()
        code_challenge = pkce.get_code_challenge(code_verifier)

        # Save verifier and state in session for later validation
        request.session['code_verifier'] = code_verifier
        state = secrets.token_urlsafe(16)
        request.session['oauth_state'] = state

        params = {
            "response_type": "code",
            "client_id": settings.TWITTER_CLIENT_ID,
            "redirect_uri": settings.TWITTER_REDIRECT_URI,
            "scope": "tweet.read tweet.write users.read offline.access",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        auth_url = "https://twitter.com/i/oauth2/authorize?" + urlencode(params)
        return redirect(auth_url)
    except Exception as e:
        logging.error(f"Error in connect_twitter: {e}")
        messages.error(request, 'Unable to start Twitter authentication. Please try again.')
        return redirect('dashboard')

@csrf_exempt
def twitter_callback(request):
    """
    Handle Twitter OAuth 2.0 callback with PKCE.
    """
    print("CALLBACK triggered.")
    try:
        code = request.GET.get("code")
        state = request.GET.get("state")
        code_verifier = request.session.get("code_verifier")
        stored_state = request.session.get("oauth_state")

        # Validate state parameter
        if state != stored_state:
            messages.error(request, 'Invalid state parameter. Please try again.')
            return redirect('dashboard')

        if not code or not code_verifier:
            messages.error(request, 'Missing authorization code or code verifier.')
            return redirect('dashboard')

        # Exchange code for access token
        token_data = exchange_code_for_token(code, code_verifier)
        
        # Debug: Print token data
        print("=== TOKEN DATA ===")
        print(f"Token Response: {token_data}")
        
        if 'access_token' in token_data:
            # Store the access token in user's session or profile
            request.session['twitter_access_token'] = token_data['access_token']
            request.session['twitter_refresh_token'] = token_data.get('refresh_token')
            
            print(f"Access Token: {token_data['access_token']}")
            print(f"Refresh Token: {token_data.get('refresh_token')}")
            print(f"Token Type: {token_data.get('token_type')}")
            print(f"Expires In: {token_data.get('expires_in')}")
            
            # Get user info from Twitter
            user_info = get_twitter_user_info(token_data['access_token'])
            
            print("=== USER INFO ===")
            print(f"User Info: {user_info}")
            
            if user_info:
                # Update or create user profile with Twitter info
                update_user_twitter_info(request.user, user_info, token_data)
                messages.success(request, f'Successfully connected to Twitter! Welcome, @{user_info.get("username", "user")}')
            else:
                messages.warning(request, 'Connected to Twitter but unable to fetch user info.')
            
            # Clean up session data
            request.session.pop('code_verifier', None)
            request.session.pop('oauth_state', None)
            
            return redirect('dashboard')
        else:
            print(f"Token exchange failed: {token_data}")
            messages.error(request, 'Failed to obtain access token from Twitter.')
            return redirect('dashboard')
            
    except Exception as e:
        logging.error(f"Error in twitter_callback: {e}")
        messages.error(request, 'An error occurred during Twitter authentication. Please try again.')
        return redirect('dashboard')

def exchange_code_for_token(code, code_verifier):
    """
    Exchange authorization code for access token using PKCE.
    """
    try:
        # Create Basic Auth header with client credentials
        # URL encode the client ID and secret first, then base64 encode
        client_id_encoded = quote(settings.TWITTER_CLIENT_ID, safe='')
        client_secret_encoded = quote(settings.TWITTER_CLIENT_SECRET, safe='')
        client_credentials = f"{client_id_encoded}:{client_secret_encoded}"
        encoded_credentials = base64.b64encode(client_credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.TWITTER_REDIRECT_URI,
            "code_verifier": code_verifier,
        }

        token_url = "https://api.twitter.com/2/oauth2/token"
        
        # Debug logging
        logging.info(f"Token exchange request - URL: {token_url}")
        logging.info(f"Token exchange request - Headers: {headers}")
        logging.info(f"Token exchange request - Data: {data}")
        
        response = requests.post(token_url, data=data, headers=headers)
        
        # Debug logging
        logging.info(f"Token exchange response - Status: {response.status_code}")
        logging.info(f"Token exchange response - Headers: {dict(response.headers)}")
        logging.info(f"Token exchange response - Body: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Token exchange failed: {response.status_code} - {response.text}")
            return {"error": f"Token exchange failed: {response.status_code}"}
            
    except Exception as e:
        logging.error(f"Error in exchange_code_for_token: {e}")
        return {"error": str(e)}

def get_twitter_user_info(access_token):
    """
    Get user information from Twitter using the access token.
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        user_url = "https://api.twitter.com/2/users/me"
        response = requests.get(user_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
        else:
            logging.error(f"Failed to get user info: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"Error in get_twitter_user_info: {e}")
        return None

def update_user_twitter_info(user, twitter_user_info, token_data):
    """
    Update user profile with Twitter information.
    """
    try:
        # Get or create user profile
        profile, created = Profile.objects.get_or_create(user=user)
        
        # Update profile with Twitter info
        profile.twitter_username = twitter_user_info.get('username')
        profile.twitter_id = twitter_user_info.get('id')
        profile.twitter_access_token = token_data.get('access_token')
        profile.twitter_refresh_token = token_data.get('refresh_token')
        profile.save()
        
    except Exception as e:
        logging.error(f"Error in update_user_twitter_info: {e}")
