from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    
    # Legacy fields (keeping for backward compatibility)
    twitter_token = models.CharField(max_length=255, blank=True, null=True)
    facebook_token = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"

class SocialAccount(models.Model):
    """
    Model to handle multiple social media accounts per user
    """
    PLATFORM_CHOICES = [
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('facebook', 'Facebook'),
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('reddit', 'Reddit'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    account_username = models.CharField(max_length=100)
    account_id = models.CharField(max_length=100, blank=True, null=True)
    account_name = models.CharField(max_length=200, blank=True, null=True)
    
    # OAuth tokens
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_type = models.CharField(max_length=50, default='bearer')
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        unique_together = ['user', 'platform', 'account_username']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.platform} (@{self.account_username})"
    
    @property
    def is_token_expired(self):
        """Check if the access token is expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_token_expiring_soon(self):
        """Check if token expires within 1 hour"""
        if not self.expires_at:
            return False
        return timezone.now() > (self.expires_at - timedelta(hours=1))
    
    def update_tokens(self, access_token, refresh_token=None, expires_in=None):
        """Update tokens and calculate expiration"""
        self.access_token = access_token
        if refresh_token:
            self.refresh_token = refresh_token
        
        if expires_in:
            self.expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        self.updated_at = timezone.now()
        self.save()
    
    def mark_as_used(self):
        """Mark account as recently used"""
        self.last_used = timezone.now()
        self.save()

class Post(models.Model):
    """
    Model to store posts shared across social media platforms
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.content[:50]}..."

class PostShare(models.Model):
    """
    Model to track individual platform shares of a post
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE)
    platform_post_id = models.CharField(max_length=100, blank=True, null=True)  # ID from the platform
    platform_url = models.URLField(blank=True, null=True)  # URL of the post on the platform
    shared_at = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['post', 'social_account']
    
    def __str__(self):
        return f"{self.post.user.username} - {self.social_account.platform} - {self.shared_at}"

class PostAnalytics(models.Model):
    """
    Model to store analytics data for posts
    """
    post_share = models.OneToOneField(PostShare, on_delete=models.CASCADE, related_name='analytics')
    
    # Engagement metrics
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    
    # Engagement rate (calculated field)
    engagement_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Timestamps
    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.post_share} - {self.collected_at}"
    
    def calculate_engagement_rate(self):
        """Calculate engagement rate based on platform"""
        if self.views > 0:
            total_engagement = self.likes + self.comments + self.shares
            self.engagement_rate = (total_engagement / self.views) * 100
        elif self.impressions > 0:
            total_engagement = self.likes + self.comments + self.shares
            self.engagement_rate = (total_engagement / self.impressions) * 100
        else:
            self.engagement_rate = 0.00
        self.save()

class AccountAnalytics(models.Model):
    """
    Model to store account-level analytics
    """
    social_account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE, related_name='analytics')
    
    # Follower metrics
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    
    # Post metrics
    total_posts = models.IntegerField(default=0)
    total_likes = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    total_shares = models.IntegerField(default=0)
    
    # Growth metrics
    followers_growth = models.IntegerField(default=0)  # Change since last collection
    
    # Timestamps
    collected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-collected_at']
    
    def __str__(self):
        return f"Analytics for {self.social_account} - {self.collected_at}"
