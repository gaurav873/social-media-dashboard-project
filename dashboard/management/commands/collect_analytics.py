from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import SocialAccount, PostShare
from dashboard.api_utils import (
    get_twitter_post_analytics, 
    get_twitter_account_analytics,
    store_analytics_snapshot,
    store_account_analytics_snapshot
)
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Collect analytics data from all connected social media accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--accounts-only',
            action='store_true',
            help='Only collect account-level analytics',
        )
        parser.add_argument(
            '--posts-only',
            action='store_true',
            help='Only collect post-level analytics',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting analytics collection...')
        )
        
        # Get all active social accounts
        social_accounts = SocialAccount.objects.filter(is_active=True)
        
        if not social_accounts.exists():
            self.stdout.write(
                self.style.WARNING('No active social accounts found.')
            )
            return
        
        success_count = 0
        error_count = 0
        
        # Collect account-level analytics
        if not options['posts_only']:
            self.stdout.write('Collecting account-level analytics...')
            for account in social_accounts:
                try:
                    if account.platform == 'twitter':
                        analytics_data = get_twitter_account_analytics(account.access_token)
                        if analytics_data['success']:
                            store_account_analytics_snapshot(account, analytics_data)
                            success_count += 1
                            self.stdout.write(
                                f'✓ Collected analytics for {account.platform} account @{account.account_username}'
                            )
                        else:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'✗ Failed to collect analytics for {account.platform} account @{account.account_username}: {analytics_data.get("error")}'
                                )
                            )
                    # Add other platforms here
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error collecting account analytics for {account}: {e}")
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Error collecting analytics for {account.platform} account @{account.account_username}: {str(e)}'
                        )
                    )
        
        # Collect post-level analytics
        if not options['accounts_only']:
            self.stdout.write('Collecting post-level analytics...')
            post_shares = PostShare.objects.filter(
                is_successful=True,
                platform_post_id__isnull=False
            )
            
            for share in post_shares:
                try:
                    if share.social_account.platform == 'twitter':
                        analytics_data = get_twitter_post_analytics(
                            share.platform_post_id,
                            share.social_account.access_token
                        )
                        if analytics_data['success']:
                            store_analytics_snapshot(share, analytics_data)
                            success_count += 1
                            self.stdout.write(
                                f'✓ Collected analytics for post {share.platform_post_id} on {share.social_account.platform}'
                            )
                        else:
                            error_count += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'✗ Failed to collect analytics for post {share.platform_post_id}: {analytics_data.get("error")}'
                                )
                            )
                    # Add other platforms here
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error collecting post analytics for {share}: {e}")
                    self.stdout.write(
                        self.style.ERROR(
                            f'✗ Error collecting analytics for post {share.platform_post_id}: {str(e)}'
                        )
                    )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'Analytics collection completed!')
        )
        self.stdout.write(f'Successful collections: {success_count}')
        self.stdout.write(f'Errors: {error_count}')
        self.stdout.write(f'Timestamp: {timezone.now()}')
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    'Some collections failed. Check the logs for details.'
                )
            ) 