import requests
import logging

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

SOCIAL_AUTH_TWITTER_KEY = 'your-twitter-api-key'
SOCIAL_AUTH_TWITTER_SECRET = 'your-twitter-api-secret'
# For Instagram, you may need a custom backend or use a package like django-allauth for Instagram Basic Display API. 

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/' 