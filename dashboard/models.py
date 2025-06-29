from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    
    # Twitter OAuth 2.0 fields
    twitter_username = models.CharField(max_length=100, blank=True, null=True)
    twitter_id = models.CharField(max_length=100, blank=True, null=True)
    twitter_access_token = models.TextField(blank=True, null=True)
    twitter_refresh_token = models.TextField(blank=True, null=True)
    twitter_token_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Legacy fields (keeping for backward compatibility)
    twitter_token = models.CharField(max_length=255, blank=True, null=True)
    facebook_token = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"
    
    @property
    def is_twitter_connected(self):
        """Check if user has a valid Twitter connection."""
        return bool(self.twitter_access_token and self.twitter_username)
