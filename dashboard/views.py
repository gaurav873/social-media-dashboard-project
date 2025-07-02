from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Profile, SocialAccount, Post, PostShare, PostAnalytics, AccountAnalytics
from .api_utils import fetch_twitter_posts, fetch_instagram_posts, post_to_twitter, get_twitter_post_analytics, get_twitter_account_analytics, store_analytics_snapshot, store_account_analytics_snapshot, fetch_reddit_posts
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
    # Get all social accounts for the user
    social_accounts = SocialAccount.objects.filter(user=request.user, is_active=True)
    
    # Group accounts by platform
    accounts_by_platform = {}
    for account in social_accounts:
        if account.platform not in accounts_by_platform:
            accounts_by_platform[account.platform] = []
        accounts_by_platform[account.platform].append(account)

    # Fetch posts from all platforms
    all_posts = []
    try:
        # Twitter
        for account in accounts_by_platform.get('twitter', []):
            twitter_posts = fetch_twitter_posts(account)
            for post in twitter_posts:
                post['platform'] = 'twitter'
                post['account_username'] = account.account_username
                all_posts.append(post)
        # Reddit
        for account in accounts_by_platform.get('reddit', []):
            reddit_posts = fetch_reddit_posts(account)
            for post in reddit_posts:
                post['account_username'] = account.account_username
                all_posts.append(post)
        # Sort all posts by created date (descending)
        all_posts.sort(key=lambda x: x.get('created_at') or x.get('created_utc', 0), reverse=True)
        # Recent Activity: most recent 6
        recent_posts = all_posts[:6]
        # Top Posts: top 6 by likes/upvotes/comments
        def post_score(post):
            if post['platform'] == 'twitter':
                return (post.get('like_count', 0) + post.get('reply_count', 0) + post.get('retweet_count', 0))
            elif post['platform'] == 'reddit':
                return (post.get('score', 0) + post.get('num_comments', 0))
            return 0
        top_posts = sorted(all_posts, key=post_score, reverse=True)[:6]
        return render(request, 'dashboard/dashboard.html', {
            'recent_posts': recent_posts,
            'top_posts': top_posts,
            'social_accounts': social_accounts,
            'accounts_by_platform': accounts_by_platform,
        })
    except Exception as e:
        logging.error(f"Error in dashboard_view: {e}")
        messages.error(request, 'Unable to load your dashboard at this time. Please try again later.')
        return render(request, 'dashboard/dashboard.html', {
            'recent_posts': [],
            'top_posts': [],
            'social_accounts': social_accounts,
            'accounts_by_platform': accounts_by_platform,
        })

@login_required
def create_post_view(request):
    """
    View to create a new post for sharing across platforms
    """
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        selected_platforms = request.POST.getlist('platforms')
        media_url = request.POST.get('media_url', '').strip()
        
        if not content:
            messages.error(request, 'Post content is required.')
            return redirect('create_post')
        
        if not selected_platforms:
            messages.error(request, 'Please select at least one platform to share to.')
            return redirect('create_post')
        
        try:
            # Create the post
            post = Post.objects.create(
                user=request.user,
                content=content,
                media_url=media_url if media_url else None
            )
            
            # Share to selected platforms
            success_count = 0
            for platform in selected_platforms:
                try:
                    # Get the first active account for this platform
                    social_account = SocialAccount.objects.filter(
                        user=request.user,
                        platform=platform,
                        is_active=True
                    ).first()
                    
                    if not social_account:
                        messages.warning(request, f'No active {platform} account found.')
                        continue
                    
                    # Share to the platform
                    if platform == 'twitter':
                        result = post_to_twitter(content, social_account.access_token, media_url)
                        if result['success']:
                            # Create PostShare record
                            PostShare.objects.create(
                                post=post,
                                social_account=social_account,
                                platform_post_id=result['tweet_id'],
                                platform_url=result['tweet_url'],
                                is_successful=True
                            )
                            success_count += 1
                            messages.success(request, f'Successfully posted to {platform}!')
                        else:
                            PostShare.objects.create(
                                post=post,
                                social_account=social_account,
                                is_successful=False,
                                error_message=result.get('error', 'Unknown error')
                            )
                            messages.error(request, f'Failed to post to {platform}: {result.get("error")}')
                    
                    # Add other platforms here (Instagram, Facebook, etc.)
                    
                except Exception as e:
                    logging.error(f"Error sharing to {platform}: {e}")
                    messages.error(request, f'Error sharing to {platform}: {str(e)}')
            
            if success_count > 0:
                messages.success(request, f'Post created and shared to {success_count} platform(s)!')
                return redirect('post_history')
            else:
                messages.warning(request, 'Post created but failed to share to any platforms.')
                return redirect('post_history')
                
        except Exception as e:
            logging.error(f"Error creating post: {e}")
            messages.error(request, 'An error occurred while creating the post.')
            return redirect('create_post')
    
    # GET request - show the form
    social_accounts = SocialAccount.objects.filter(user=request.user, is_active=True)
    platforms = list(set([account.platform for account in social_accounts]))
    
    return render(request, 'dashboard/create_post.html', {
        'platforms': platforms,
        'social_accounts': social_accounts
    })

@login_required
def post_history_view(request):
    """
    View to show post history with analytics
    """
    posts = Post.objects.filter(user=request.user).order_by('-created_at')
    
    # For each post, get live analytics if available
    for post in posts:
        for share in post.shares.all():
            if share.platform_post_id and share.is_successful:
                try:
                    # Try to get live analytics
                    if share.social_account.platform == 'twitter':
                        analytics_data = get_twitter_post_analytics(
                            share.platform_post_id, 
                            share.social_account.access_token
                        )
                        
                        if analytics_data['success']:
                            # Store snapshot for historical tracking
                            store_analytics_snapshot(share, analytics_data)
                            
                            # Add live data to share object for template
                            share.live_analytics = analytics_data
                        else:
                            # If live fetch fails, use stored data
                            if hasattr(share, 'analytics'):
                                share.live_analytics = {
                                    'likes': share.analytics.likes,
                                    'retweets': share.analytics.shares,
                                    'replies': share.analytics.comments,
                                    'impressions': share.analytics.impressions,
                                    'from_cache': True
                                }
                except Exception as e:
                    logging.error(f"Error fetching analytics for post {post.id}: {e}")
    
    return render(request, 'dashboard/post_history.html', {
        'posts': posts
    })

@login_required
def analytics_view(request):
    """
    View to show comprehensive analytics dashboard
    """
    social_accounts = SocialAccount.objects.filter(user=request.user, is_active=True)
    
    # Get live account analytics
    account_analytics = {}
    for account in social_accounts:
        try:
            if account.platform == 'twitter':
                analytics_data = get_twitter_account_analytics(account.access_token)
                if analytics_data['success']:
                    # Store snapshot
                    store_account_analytics_snapshot(account, analytics_data)
                    account_analytics[account.id] = analytics_data
                else:
                    # Use latest stored data
                    latest_analytics = AccountAnalytics.objects.filter(
                        social_account=account
                    ).order_by('-collected_at').first()
                    
                    if latest_analytics:
                        account_analytics[account.id] = {
                            'followers_count': latest_analytics.followers_count,
                            'following_count': latest_analytics.following_count,
                            'tweet_count': latest_analytics.total_posts,
                            'from_cache': True
                        }
        except Exception as e:
            logging.error(f"Error fetching account analytics for {account.platform}: {e}")
    
    # Get recent posts with analytics
    recent_posts = Post.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(request, 'dashboard/analytics.html', {
        'social_accounts': social_accounts,
        'account_analytics': account_analytics,
        'recent_posts': recent_posts
    })

@login_required
def disconnect_twitter(request):
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        try:
            if account_id:
                # Disconnect specific account
                social_account = SocialAccount.objects.get(
                    id=account_id, 
                    user=request.user, 
                    platform='twitter'
                )
                social_account.is_active = False
                social_account.save()
                messages.success(request, f'Twitter account @{social_account.account_username} disconnected successfully.')
            else:
                # Disconnect all Twitter accounts
                twitter_accounts = SocialAccount.objects.filter(
                    user=request.user, 
                    platform='twitter', 
                    is_active=True
                )
                for account in twitter_accounts:
                    account.is_active = False
                    account.save()
                messages.success(request, 'All Twitter accounts disconnected successfully.')
                
        except SocialAccount.DoesNotExist:
            messages.warning(request, 'Twitter account not found.')
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
            
            # Ensure user is logged in and redirect to dashboard
            if request.user.is_authenticated:
                return redirect('dashboard')
            else:
                # If user is not authenticated, redirect to login
                return redirect('login')
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
    Update or create social account with Twitter information.
    """
    try:
        # Get or create social account for this user and Twitter platform
        social_account, created = SocialAccount.objects.get_or_create(
            user=user,
            platform='twitter',
            account_username=twitter_user_info.get('username'),
            defaults={
                'account_id': twitter_user_info.get('id'),
                'account_name': twitter_user_info.get('name'),
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_type': token_data.get('token_type', 'bearer'),
                'expires_at': None,  # Will be calculated by update_tokens method
            }
        )
        
        # Update tokens and expiration
        social_account.update_tokens(
            access_token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            expires_in=token_data.get('expires_in')
        )
        
        # Update account info if not newly created
        if not created:
            social_account.account_id = twitter_user_info.get('id')
            social_account.account_name = twitter_user_info.get('name')
            social_account.save()
        
        # Mark as recently used
        social_account.mark_as_used()
        
    except Exception as e:
        logging.error(f"Error in update_user_twitter_info: {e}")

@login_required
def social_accounts_view(request):
    """
    View to manage all social media accounts for a user
    """
    social_accounts = SocialAccount.objects.filter(user=request.user).order_by('platform', 'account_username')
    
    # Group by platform
    accounts_by_platform = {}
    for account in social_accounts:
        if account.platform not in accounts_by_platform:
            accounts_by_platform[account.platform] = []
        accounts_by_platform[account.platform].append(account)
    
    return render(request, 'dashboard/social_accounts.html', {
        'social_accounts': social_accounts,
        'accounts_by_platform': accounts_by_platform,
    })

def connect_reddit(request):
    """
    Initiate Reddit OAuth2 flow.
    """
    import secrets
    from django.conf import settings
    from urllib.parse import urlencode
    
    state = secrets.token_urlsafe(16)
    request.session['reddit_oauth_state'] = state
    params = {
        'client_id': settings.REDDIT_CLIENT_ID,
        'response_type': 'code',
        'state': state,
        'redirect_uri': settings.REDDIT_REDIRECT_URI,
        'duration': 'permanent',
        'scope': 'identity submit read',
    }
    auth_url = f"https://www.reddit.com/api/v1/authorize?{urlencode(params)}"
    return redirect(auth_url)

@csrf_exempt
@login_required
def reddit_callback(request):
    """
    Handle Reddit OAuth2 callback.
    """
    import requests
    from django.conf import settings
    code = request.GET.get('code')
    state = request.GET.get('state')
    stored_state = request.session.get('reddit_oauth_state')
    if state != stored_state:
        messages.error(request, 'Invalid state parameter for Reddit OAuth.')
        return redirect('dashboard')
    if not code:
        messages.error(request, 'No code returned from Reddit.')
        return redirect('dashboard')
    # Exchange code for token
    auth = requests.auth.HTTPBasicAuth(settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET)
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.REDDIT_REDIRECT_URI,
    }
    headers = {'User-Agent': settings.REDDIT_USER_AGENT}
    token_url = 'https://www.reddit.com/api/v1/access_token'
    response = requests.post(token_url, auth=auth, data=data, headers=headers)
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data['access_token']
        refresh_token = token_data.get('refresh_token')
        # Get Reddit user info
        headers['Authorization'] = f'bearer {access_token}'
        user_response = requests.get('https://oauth.reddit.com/api/v1/me', headers=headers)
        if user_response.status_code == 200:
            user_info = user_response.json()
            # Save to SocialAccount
            from .models import SocialAccount
            social_account, created = SocialAccount.objects.get_or_create(
                user=request.user,
                platform='reddit',
                account_username=user_info['name'],
                defaults={
                    'account_id': user_info['id'],
                    'account_name': user_info.get('subreddit', {}).get('title', user_info['name']),
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': token_data.get('token_type', 'bearer'),
                    'expires_at': None,
                }
            )
            social_account.update_tokens(access_token, refresh_token, token_data.get('expires_in'))
            social_account.account_id = user_info['id']
            social_account.account_name = user_info.get('subreddit', {}).get('title', user_info['name'])
            social_account.save()
            social_account.mark_as_used()
            messages.success(request, f'Successfully connected Reddit account u/{user_info["name"]}!')
        else:
            messages.error(request, 'Failed to fetch Reddit user info.')
    else:
        messages.error(request, 'Failed to obtain Reddit access token.')
    request.session.pop('reddit_oauth_state', None)
    return redirect('dashboard')
