#!/bin/bash
# Professional Telegram YouTube Downloader Bot - Production Startup Script

set -e  # Exit on any error

echo "🚀 Starting Professional Telegram YouTube Downloader Bot..."
echo "📅 Startup time: $(date)"
echo "🏗️  Environment: ${NODE_ENV:-production}"
echo "📊 Python version: $(python --version)"

# Create necessary directories with proper structure
echo "📁 Creating directory structure..."
mkdir -p logs temp db cookies
mkdir -p temp/downloads temp/processing

# Set proper permissions
echo "🔐 Setting permissions..."
chmod +x bot/main.py
chmod -R 755 temp/
chmod -R 755 logs/

# Verify critical environment variables
echo "🔍 Verifying environment variables..."
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ ERROR: BOT_TOKEN environment variable is not set!"
    echo "Please set your Telegram bot token in the environment variables."
    exit 1
fi

if [ -z "$ADMIN_ID" ]; then
    echo "⚠️  WARNING: ADMIN_ID not set, using default: 7352192536"
    export ADMIN_ID="7352192536"
fi

echo "✅ Environment variables verified"
echo "👨‍💼 Admin ID: $ADMIN_ID"
echo "🎯 Log level: ${LOG_LEVEL:-INFO}"
echo "⚡ Max concurrent downloads: ${MAX_CONCURRENT_DOWNLOADS:-5}"
echo "🔒 Security enabled: ${ENABLE_SECURITY:-true}"
echo "📊 Analytics enabled: ${ENABLE_ANALYTICS:-true}"

# System health check
echo "🏥 Performing system health check..."
echo "💾 Disk space:"
df -h .
echo "🧠 Memory usage:"
free -h 2>/dev/null || echo "Memory info not available"

# Verify dependencies
echo "📦 Verifying Python dependencies..."
python -c "import aiogram, yt_dlp, aiosqlite; print('✅ Core dependencies verified')"

# Initialize database
echo "🗄️  Initializing database..."
python -c "
import asyncio
import sys
sys.path.append('.')
from utils.database import ProfessionalDatabase

async def init_db():
    db = ProfessionalDatabase('db/bot_database.db')
    await db.initialize()
    print('✅ Database initialized successfully')
    await db.close()

if __name__ == '__main__':
    asyncio.run(init_db())
" || echo "⚠️  Database initialization skipped (will initialize on first run)"

# Final system check
echo "🔧 Final system check..."
if [ ! -d "utils" ]; then
    echo "❌ ERROR: utils directory not found!"
    exit 1
fi

if [ ! -f "bot/main.py" ]; then
    echo "❌ ERROR: bot/main.py not found!"
    exit 1
fi

echo "✅ All system checks passed"
echo "🎉 Starting bot with professional configuration..."
echo "📡 Bot will be available 24/7 for users"
echo "🔗 Enterprise technology by AKG"
echo "" # Empty line for readability

# Start the bot with error handling
exec python bot/main.py