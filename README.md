# Social Media Dashboard with Hybrid Analytics

A Django-based social media management platform that allows users to share content across multiple platforms and track analytics using a hybrid approach (live API + stored snapshots).

## 🚀 Features

### Core Functionality
- **Multi-Platform Posting**: Share content to Twitter, Instagram, Facebook, LinkedIn, and more
- **OAuth 2.0 Integration**: Secure authentication with social media platforms
- **Post Management**: Create, schedule, and track posts across platforms
- **Account Management**: Connect and manage multiple social media accounts

### Hybrid Analytics Approach
- **Live Data**: Real-time analytics fetched from platform APIs
- **Stored Snapshots**: Historical data stored in database for trends and fallback
- **Smart Caching**: Automatic fallback to cached data when APIs are unavailable
- **Scheduled Collection**: Background tasks to collect analytics data periodically

## 🏗️ Architecture

### Database Models
- `Post`: Stores post content and metadata
- `PostShare`: Tracks individual platform shares of posts
- `PostAnalytics`: Stores engagement metrics for posts
- `AccountAnalytics`: Stores account-level metrics
- `SocialAccount`: Manages OAuth tokens and account info

### API Integration
- **Twitter API v2**: Full posting and analytics support
- **Instagram Basic Display API**: Ready for implementation
- **Facebook Graph API**: Ready for implementation
- **LinkedIn API**: Ready for implementation

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd social-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   TWITTER_CLIENT_ID=your-twitter-client-id
   TWITTER_CLIENT_SECRET=your-twitter-client-secret
   TWITTER_REDIRECT_URI=http://localhost:8000/twitter/callback/
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## 📊 Analytics Implementation

### Hybrid Approach Benefits

| Feature | Live API | Stored Data | Hybrid |
|---------|----------|-------------|--------|
| Real-time data | ✅ | ❌ | ✅ |
| Historical trends | ❌ | ✅ | ✅ |
| Fast dashboard | ❌ | ✅ | ✅ |
| API rate limit safe | ❌ | ✅ | ✅ |
| Offline capability | ❌ | ✅ | ✅ |

### Data Collection Strategy

1. **Live Analytics**: When users view analytics, fetch fresh data from APIs
2. **Snapshot Storage**: Store periodic snapshots for historical analysis
3. **Fallback Mechanism**: Use cached data when APIs are unavailable
4. **Background Collection**: Scheduled tasks collect data every hour

### Management Commands

```bash
# Collect all analytics data
python manage.py collect_analytics

# Collect only account-level analytics
python manage.py collect_analytics --accounts-only

# Collect only post-level analytics
python manage.py collect_analytics --posts-only
```

## 🔧 Usage

### 1. Connect Social Media Accounts
- Navigate to the dashboard
- Click "Connect Twitter" (or other platforms)
- Complete OAuth flow
- Account will be available for posting

### 2. Create and Share Posts
- Go to "Create Post" page
- Write your content
- Select target platforms
- Add optional media URL
- Click "Share Post"

### 3. View Analytics
- **Live Analytics**: Real-time data from platform APIs
- **Historical Data**: Stored snapshots for trend analysis
- **Post Performance**: Individual post engagement metrics
- **Account Growth**: Follower and engagement trends

### 4. Post History
- View all shared posts
- See platform-specific analytics
- Track engagement over time
- Identify best-performing content

## 📈 Analytics Metrics

### Post-Level Metrics
- **Likes/Reactions**: User engagement
- **Comments/Replies**: User interaction
- **Shares/Retweets**: Content virality
- **Impressions**: Content reach
- **Engagement Rate**: Overall performance

### Account-Level Metrics
- **Follower Count**: Audience size
- **Following Count**: Network connections
- **Post Count**: Content volume
- **Growth Rate**: Audience expansion

## 🔄 Scheduled Tasks

Set up cron jobs for automated analytics collection:

```bash
# Collect analytics every hour
0 * * * * cd /path/to/project && python manage.py collect_analytics

# Collect account analytics daily
0 0 * * * cd /path/to/project && python manage.py collect_analytics --accounts-only
```

## 🚀 Production Deployment

### Environment Variables
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=your-database-url
```

### Database Setup
```bash
# PostgreSQL (recommended)
pip install psycopg2-binary

# Redis for caching
pip install redis
```

### Static Files
```bash
python manage.py collectstatic
```

## 🔒 Security Features

- **OAuth 2.0 PKCE**: Secure authentication flow
- **Token Encryption**: Encrypted storage of access tokens
- **CSRF Protection**: Cross-site request forgery protection
- **Session Management**: Secure user sessions
- **Rate Limiting**: API rate limit handling

## 📝 API Documentation

### Twitter API Integration
- **Posting**: Create tweets with text and media
- **Analytics**: Fetch engagement metrics
- **Account Data**: Get follower counts and profile info

### Extending to Other Platforms
1. Add platform to `PLATFORM_CHOICES` in `SocialAccount` model
2. Implement OAuth flow in views
3. Add posting function in `api_utils.py`
4. Add analytics functions for the platform
5. Update templates with platform-specific UI

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the code comments

## 🔮 Future Enhancements

- [ ] Instagram Basic Display API integration
- [ ] Facebook Graph API integration
- [ ] LinkedIn API integration
- [ ] Advanced scheduling features
- [ ] Content calendar view
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard
- [ ] Mobile app support 