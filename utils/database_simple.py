"""
Simple Database module for Telegram YouTube Downloader Bot
"""

import aiosqlite
import logging
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DatabasePro:
    def __init__(self, db_path: str = "db/bot_database.db", pool_size: int = 10, cache_size: int = 1000):
        """Initialize database"""
        self.db_path = db_path
        self.pool_size = pool_size
        self.cache_size = cache_size
        
        # Ensure db directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def initialize(self):
        """Initialize database tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create users table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        is_prime BOOLEAN DEFAULT FALSE,
                        prime_expiry TEXT,
                        downloads_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        last_seen TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create downloads table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        url TEXT,
                        quality TEXT,
                        success BOOLEAN,
                        error_message TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Create admin_actions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS admin_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INTEGER,
                        action TEXT,
                        target_user_id INTEGER,
                        details TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    async def add_user(self, user_id: int, username: str):
        """Add or update user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO users (user_id, username)
                    VALUES (?, ?)
                """, (user_id, username))
                await db.commit()
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def set_prime_status(self, user_id: int, is_prime: bool, expiry: Optional[str] = None):
        """Set user prime status"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users 
                    SET is_prime = ?, prime_expiry = ?
                    WHERE user_id = ?
                """, (is_prime, expiry, user_id))
                await db.commit()
        except Exception as e:
            logger.error(f"Error setting prime status for user {user_id}: {e}")
    
    async def log_download(self, user_id: int, url: str = "", quality: str = "", success: bool = True, error_message: str = ""):
        """Log download attempt"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO downloads (user_id, url, quality, success, error_message)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, url, quality, success, error_message))
                
                # Update user downloads count
                await db.execute("""
                    UPDATE users 
                    SET downloads_count = downloads_count + 1, last_seen = ?
                    WHERE user_id = ?
                """, (datetime.now().isoformat(), user_id))
                
                await db.commit()
        except Exception as e:
            logger.error(f"Error logging download for user {user_id}: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Get user counts
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    total_users = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT COUNT(*) FROM users WHERE is_prime = TRUE") as cursor:
                    prime_users = (await cursor.fetchone())[0]
                
                # Get download counts
                async with db.execute("SELECT COUNT(*) FROM downloads") as cursor:
                    total_downloads = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT COUNT(*) FROM downloads WHERE success = TRUE") as cursor:
                    successful_downloads = (await cursor.fetchone())[0]
                
                # Get recent activity
                async with db.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE last_seen > datetime('now', '-24 hours')
                """) as cursor:
                    active_24h = (await cursor.fetchone())[0]
                
                return {
                    'total_users': total_users,
                    'prime_users': prime_users,
                    'total_downloads': total_downloads,
                    'successful_downloads': successful_downloads,
                    'active_24h': active_24h,
                    'success_rate': round((successful_downloads / max(total_downloads, 1)) * 100, 2)
                }
                
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_users': 0,
                'prime_users': 0,
                'total_downloads': 0,
                'successful_downloads': 0,
                'active_24h': 0,
                'success_rate': 0
            }
    
    async def get_all_users(self):
        """Get all users for broadcasting"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT user_id FROM users") as cursor:
                    users = await cursor.fetchall()
                    return [user['user_id'] for user in users]
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []