import requests
import logging
from django.conf import settings
from .models import Post, PostShare, PostAnalytics, AccountAnalytics
from django.utils import timezone

def fetch_twitter_posts():
    try:
        response = requests.get('https://jsonplaceholder.typicode.com/posts?userId=1', timeout=5)
        response.raise_for_status()
        return response.json()[:5]
    except requests.RequestException as e:
        logging.error(f"Twitter API error: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in fetch_twitter_posts: {e}")
        return []

def fetch_instagram_posts():
    try:
        response = requests.get('https://jsonplaceholder.typicode.com/photos?albumId=1', timeout=5)
        response.raise_for_status()
        return response.json()[:5]
    except requests.RequestException as e:
        logging.error(f"Instagram API error: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in fetch_instagram_posts: {e}")
        return []

def post_to_twitter(content, access_token, media_url=None):
    """
    Post content to Twitter using Twitter API v2
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare tweet data
        tweet_data = {
            "text": content
        }
        
        # If media URL is provided, we would need to upload media first
        # For now, we'll just post text
        if media_url:
            logging.info(f"Media upload not implemented yet for URL: {media_url}")
        
        response = requests.post(
            "https://api.twitter.com/2/tweets",
            headers=headers,
            json=tweet_data
        )
        
        if response.status_code == 201:
            result = response.json()
            return {
                'success': True,
                'tweet_id': result['data']['id'],
                'tweet_url': f"https://twitter.com/user/status/{result['data']['id']}"
            }
        else:
            logging.error(f"Twitter API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"Twitter API error: {response.status_code}"
            }
            
    except Exception as e:
        logging.error(f"Error posting to Twitter: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def get_twitter_post_analytics(tweet_id, access_token):
    """
    Get live analytics for a specific tweet
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Get tweet with public metrics
        url = f"https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=public_metrics,created_at"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            tweet_data = data.get('data', {})
            metrics = tweet_data.get('public_metrics', {})
            
            return {
                'success': True,
                'likes': metrics.get('like_count', 0),
                'retweets': metrics.get('retweet_count', 0),
                'replies': metrics.get('reply_count', 0),
                'quotes': metrics.get('quote_count', 0),
                'impressions': metrics.get('impression_count', 0),
                'created_at': tweet_data.get('created_at'),
                'collected_at': timezone.now()
            }
        else:
            logging.error(f"Twitter analytics API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"API error: {response.status_code}"
            }
            
    except Exception as e:
        logging.error(f"Error fetching Twitter analytics: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def get_twitter_account_analytics(access_token):
    """
    Get live account-level analytics for Twitter
    """
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # Get user info with public metrics
        url = "https://api.twitter.com/2/users/me?user.fields=public_metrics,created_at"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            user_data = data.get('data', {})
            metrics = user_data.get('public_metrics', {})
            
            return {
                'success': True,
                'followers_count': metrics.get('followers_count', 0),
                'following_count': metrics.get('following_count', 0),
                'tweet_count': metrics.get('tweet_count', 0),
                'listed_count': metrics.get('listed_count', 0),
                'collected_at': timezone.now()
            }
        else:
            logging.error(f"Twitter account analytics API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f"API error: {response.status_code}"
            }
            
    except Exception as e:
        logging.error(f"Error fetching Twitter account analytics: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def store_analytics_snapshot(post_share, analytics_data):
    """
    Store analytics snapshot in database for historical tracking
    """
    try:
        # Create or update PostAnalytics
        analytics, created = PostAnalytics.objects.get_or_create(
            post_share=post_share,
            defaults={
                'likes': analytics_data.get('likes', 0),
                'comments': analytics_data.get('replies', 0),
                'shares': analytics_data.get('retweets', 0) + analytics_data.get('quotes', 0),
                'views': analytics_data.get('impressions', 0),
                'impressions': analytics_data.get('impressions', 0),
            }
        )
        
        if not created:
            # Update existing analytics
            analytics.likes = analytics_data.get('likes', 0)
            analytics.comments = analytics_data.get('replies', 0)
            analytics.shares = analytics_data.get('retweets', 0) + analytics_data.get('quotes', 0)
            analytics.views = analytics_data.get('impressions', 0)
            analytics.impressions = analytics_data.get('impressions', 0)
            analytics.updated_at = timezone.now()
        
        analytics.calculate_engagement_rate()
        analytics.save()
        
        return True
        
    except Exception as e:
        logging.error(f"Error storing analytics snapshot: {e}")
        return False

def store_account_analytics_snapshot(social_account, analytics_data):
    """
    Store account-level analytics snapshot
    """
    try:
        analytics = AccountAnalytics.objects.create(
            social_account=social_account,
            followers_count=analytics_data.get('followers_count', 0),
            following_count=analytics_data.get('following_count', 0),
            total_posts=analytics_data.get('tweet_count', 0),
        )
        
        return True
        
    except Exception as e:
        logging.error(f"Error storing account analytics snapshot: {e}")
        return False

def fetch_reddit_posts(social_account):
    """
    Fetch recent Reddit posts (submissions) for the connected account.
    Returns a list of dicts: title, score, num_comments, permalink, created_utc
    """
    headers = {
        'Authorization': f'bearer {social_account.access_token}',
        'User-Agent': 'django-social-dashboard by /u/Livid_Woodpecker4008',
    }
    url = f'https://oauth.reddit.com/user/{social_account.account_username}/submitted'
    response = requests.get(url, headers=headers, params={'limit': 20})
    posts = []
    if response.status_code == 200:
        data = response.json()
        for item in data.get('data', {}).get('children', []):
            post = item['data']
            posts.append({
                'id': post['id'],
                'title': post.get('title', ''),
                'selftext': post.get('selftext', ''),
                'score': post.get('score', 0),
                'num_comments': post.get('num_comments', 0),
                'permalink': f"https://reddit.com{post.get('permalink', '')}",
                'created_utc': post.get('created_utc'),
                'platform': 'reddit',
            })
    return posts

SOCIAL_AUTH_TWITTER_KEY = 'your-twitter-api-key'
SOCIAL_AUTH_TWITTER_SECRET = 'your-twitter-api-secret'
# For Instagram, you may need a custom backend or use a package like django-allauth for Instagram Basic Display API. 

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/' 