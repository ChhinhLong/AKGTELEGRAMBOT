# 🤖 Telegram YouTube Downloader Bot

A feature-rich Telegram bot for downloading YouTube videos and audio with premium features, user management, and admin controls.

## 🌟 Features

### Core Features
- 🎬 **Video Download** - Download YouTube videos in multiple qualities
- 🎵 **Audio Download** - Extract audio from YouTube videos
- 👑 **Premium System** - Unlimited downloads and HD quality for premium users
- 📊 **Usage Limits** - 15 downloads/hour for normal users with cooldown
- ⚡ **Fast Processing** - Optimized download with yt-dlp
- 🔒 **Admin Panel** - Complete admin control system

### Quality Options
- **Normal Users**: 360p, 480p, Standard Audio
- **Premium Users**: 360p, 480p, 720p, 1080p, High Quality Audio

### Admin Features
- User management (grant/revoke premium)
- Bot statistics and analytics
- Broadcast messages to all users
- Cookie management for YouTube bypass
- User activity monitoring

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Telegram Bot Token (from @BotFather)

### Local Development
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables:
   - `BOT_TOKEN=your_telegram_bot_token`
   - `ADMIN_ID=your_telegram_user_id`
4. Run the bot: `python bot/main.py`

### Deploy to Render.com
1. Fork this repository
2. Connect to Render.com
3. Use the provided `deploy/render.yaml` configuration
4. Set environment variables in Render dashboard
5. Deploy!

## 📱 Bot Commands

### User Commands
- `/start` - Start the bot and show welcome message
- `/help` - Display help and support information
- `/limit` - Check your download usage and limits
- `/upgrade` - Learn about premium features

### Admin Commands
- `/setprime [user_id] [days]` - Grant premium access to user
- `/removeprime [user_id]` - Remove premium access from user
- `/stats` - View detailed bot statistics
- `/broadcast [message]` - Send message to all bot users
- `/addcookies` - Upload YouTube cookies file
- `/fixcode` - Bot maintenance and restart

## 💎 Premium Benefits
- ♾️ Unlimited downloads (or custom admin-set limit)
- 🎬 HD Video quality (720p, 1080p)
- 🎵 High-quality audio downloads
- ⚡ No cooldown periods
- 🚀 Priority support

## 🛠️ Technical Details

### Built With
- **aiogram** - Modern Telegram Bot framework
- **yt-dlp** - YouTube download engine
- **aiosqlite** - Async SQLite database
- **python-dotenv** - Environment management

### Database Schema
- Users table with premium status and usage tracking
- Download logs for analytics
- Admin settings storage
- Bot statistics tracking

### File Structure
```
bot/main.py           # Main bot application
utils/database.py     # Database operations
utils/download_manager.py # YouTube download handling
utils/user_manager.py # User management and limits
utils/admin_panel.py  # Admin commands
```

## 📊 Usage Limits
- **Normal Users**: 15 downloads per hour
- **Cooldown**: 30 minutes after reaching limit
- **File Size**: Maximum 50MB per download
- **Duration**: Maximum 1 hour per video
- **Premium Users**: Unlimited (customizable by admin)

## 🤝 Support
- **Telegram**: @chhinhlong
- **Email**: chhinhlong2008@gmail.com
- **Bot Credit**: @AKGDownloaderBot

## 📜 License
This project is created for educational purposes. Please respect YouTube's Terms of Service and copyright laws.

## 🔧 Configuration
Bot behavior can be customized through environment variables:
- `BOT_TOKEN` - Telegram bot token
- `ADMIN_ID` - Admin user ID
- `LOG_LEVEL` - Logging level (default: INFO)

---

**Created with ❤️ for the YouTube downloading community**