"""
Professional Database Module for Telegram YouTube Downloader Bot
Features: Connection pooling, caching, advanced analytics, performance monitoring
"""

import aiosqlite
import asyncio
import logging
import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from contextlib import asynccontextmanager
from functools import wraps
from collections import defaultdict

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path: str = "db/bot_database.db", pool_size: int = 10, cache_size: int = 1000):
        """Initialize professional database with connection pooling and caching"""
        self.db_path = db_path
        self.pool_size = pool_size
        self.cache_size = cache_size
        self.connection_pool = asyncio.Queue(maxsize=pool_size)
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 300  # 5 minutes TTL
        
        # Performance statistics
        self.query_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_query_time = 0.0
        
        # Ensure db directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize flags
        self._initialized = False
        self._initializing = False
    
    async def initialize(self):
        """Initialize the database and connection pool"""
        if self._initialized or self._initializing:
            return
        
        self._initializing = True
        
        # Initialize connection pool
        await self._init_connection_pool()
        
        # Create database schema
        await self._create_schema()
        
        # Start background tasks
        asyncio.create_task(self._cache_cleanup_task())
        asyncio.create_task(self._performance_monitor_task())
        
        self._initialized = True
        self._initializing = False
        logger.info("Database initialized successfully")
    
    async def _init_connection_pool(self):
        """Initialize connection pool with optimized settings"""
        for _ in range(self.pool_size):
            conn = await aiosqlite.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None  # Autocommit mode for better concurrency
            )
            
            # Configure connection for maximum performance
            await conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            await conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety and speed
            await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            await conn.execute("PRAGMA temp_store=memory")  # Store temp data in memory
            await conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
            await conn.execute("PRAGMA optimize")  # Optimize database
            
            await self.connection_pool.put(conn)
    
    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool with context manager"""
        conn = await self.connection_pool.get()
        try:
            yield conn
        finally:
            await self.connection_pool.put(conn)
    
    def _get_cache_key(self, query: str, params: tuple = ()) -> str:
        """Generate cache key for query"""
        cache_data = f"{query}:{params}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is valid"""
        return key in self.cache_timestamps and \
               time.time() - self.cache_timestamps[key] < self.cache_ttl
    
    async def _cache_cleanup_task(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                current_time = time.time()
                expired_keys = [
                    key for key, timestamp in self.cache_timestamps.items()
                    if current_time - timestamp > self.cache_ttl
                ]
                
                for key in expired_keys:
                    self.cache.pop(key, None)
                    self.cache_timestamps.pop(key, None)
                
                # Keep cache size under limit
                if len(self.cache) > self.cache_size:
                    # Remove oldest entries
                    sorted_keys = sorted(
                        self.cache_timestamps.items(),
                        key=lambda x: x[1]
                    )
                    for key, _ in sorted_keys[:len(self.cache) - self.cache_size]:
                        self.cache.pop(key, None)
                        self.cache_timestamps.pop(key, None)
                
                await asyncio.sleep(60)  # Clean every minute
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)
    
    async def _performance_monitor_task(self):
        """Background task to monitor database performance"""
        while True:
            try:
                await asyncio.sleep(300)  # Log every 5 minutes
                
                if self.query_count > 0:
                    avg_query_time = self.total_query_time / self.query_count
                    cache_hit_rate = (self.cache_hits / (self.cache_hits + self.cache_misses)) * 100 if (self.cache_hits + self.cache_misses) > 0 else 0
                    
                    logger.info(f"DB Performance: {self.query_count} queries, "
                              f"avg: {avg_query_time:.3f}s, "
                              f"cache hit rate: {cache_hit_rate:.1f}%")
                
            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
    
    async def initialize(self):
        """Initialize database tables with optimized schema"""
        try:
            async with self.get_connection() as db:
                # Users table with indexes
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_prime BOOLEAN DEFAULT FALSE,
                        prime_expiry DATETIME,
                        downloads_count INTEGER DEFAULT 0,
                        downloads_today INTEGER DEFAULT 0,
                        downloads_this_hour INTEGER DEFAULT 0,
                        last_download DATETIME,
                        hour_reset_time DATETIME,
                        cooldown_until DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                        language_code TEXT DEFAULT 'en',
                        is_blocked BOOLEAN DEFAULT FALSE,
                        referral_code TEXT UNIQUE,
                        referred_by INTEGER,
                        total_referrals INTEGER DEFAULT 0,
                        state TEXT DEFAULT '',
                        temp_data TEXT DEFAULT '{}'
                    )
                """)
                
                # Downloads table with comprehensive tracking  
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        url TEXT NOT NULL,
                        video_id TEXT,
                        title TEXT,
                        quality TEXT,
                        download_type TEXT,
                        file_type TEXT,
                        file_size INTEGER,
                        duration INTEGER,
                        success BOOLEAN,
                        error_message TEXT,
                        download_time REAL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        ip_address TEXT,
                        user_agent TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Download logs table (for compatibility)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS download_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        url TEXT,
                        download_type TEXT,
                        quality TEXT,
                        file_size INTEGER,
                        success BOOLEAN,
                        error_message TEXT,
                        download_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # Admin actions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS admin_actions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INTEGER,
                        action TEXT NOT NULL,
                        target_user_id INTEGER,
                        details TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Admin settings table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS admin_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Bot statistics table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS bot_stats (
                        date TEXT PRIMARY KEY,
                        total_users INTEGER DEFAULT 0,
                        new_users INTEGER DEFAULT 0,
                        total_downloads INTEGER DEFAULT 0,
                        video_downloads INTEGER DEFAULT 0,
                        audio_downloads INTEGER DEFAULT 0,
                        prime_users INTEGER DEFAULT 0,
                        failed_downloads INTEGER DEFAULT 0
                    )
                """)
                
                # User sessions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        session_start DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_end DATETIME,
                        commands_used INTEGER DEFAULT 0,
                        downloads_made INTEGER DEFAULT 0,
                        duration INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
                
                # System logs table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT,
                        message TEXT,
                        module TEXT,
                        function TEXT,
                        line_number INTEGER,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        extra_data TEXT
                    )
                """)
                
                # Create indexes for better performance
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_users_prime ON users(is_prime)",
                    "CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)",
                    "CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)",
                    "CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_downloads_created_at ON downloads(created_at)",
                    "CREATE INDEX IF NOT EXISTS idx_downloads_success ON downloads(success)",
                    "CREATE INDEX IF NOT EXISTS idx_download_logs_user_id ON download_logs(user_id)",
                    "CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id ON admin_actions(admin_id)",
                    "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)"
                ]
                
                for index_sql in indexes:
                    await db.execute(index_sql)
                
                await db.commit()
                logger.info("Database initialized successfully with optimized schema")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    async def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, 
                          fetch_all: bool = False, use_cache: bool = True) -> Any:
        """Execute query with caching and performance monitoring"""
        start_time = time.time()
        self.query_count += 1
        
        # Check cache for SELECT queries
        if query.strip().upper().startswith('SELECT') and use_cache:
            cache_key = self._get_cache_key(query, params)
            if self._is_cache_valid(cache_key):
                self.cache_hits += 1
                self.total_query_time += time.time() - start_time
                return self.cache[cache_key]
            self.cache_misses += 1
        
        try:
            async with self.get_connection() as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    if fetch_one:
                        result = await cursor.fetchone()
                        result = dict(result) if result else None
                    elif fetch_all:
                        rows = await cursor.fetchall()
                        result = [dict(row) for row in rows]
                    else:
                        result = cursor.rowcount
                
                # Cache SELECT results
                if query.strip().upper().startswith('SELECT') and use_cache and (fetch_one or fetch_all):
                    cache_key = self._get_cache_key(query, params)
                    self.cache[cache_key] = result
                    self.cache_timestamps[cache_key] = time.time()
                
                self.total_query_time += time.time() - start_time
                return result
                
        except Exception as e:
            self.total_query_time += time.time() - start_time
            logger.error(f"Database query error: {e}")
            raise
    
    # Legacy compatibility methods
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information by ID"""
        return await self.execute_query(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
            fetch_one=True
        )
    
    async def create_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Create a new user (legacy compatibility)"""
        return await self.add_user(user_id, username, first_name, last_name)
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                      last_name: str = None, language_code: str = 'en') -> bool:
        """Add or update user with comprehensive data"""
        try:
            # Generate referral code
            referral_code = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8].upper()
            
            await self.execute_query("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, language_code, referral_code, 
                 last_seen, last_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?))
            """, (user_id, username, first_name, last_name, language_code, referral_code, 
                  datetime.now(), datetime.now(), user_id, datetime.now()))
            
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
            return False
    
    async def update_user_activity(self, user_id: int):
        """Update user's last activity timestamp"""
        try:
            await self.execute_query(
                "UPDATE users SET last_active = ?, last_seen = ? WHERE user_id = ?",
                (datetime.now(), datetime.now(), user_id)
            )
        except Exception as e:
            logger.error(f"Error updating user activity {user_id}: {e}")
    
    async def set_prime_status(self, user_id: int, is_prime: bool, 
                              expiry_days: int = None, expiry: Optional[datetime] = None, 
                              admin_id: int = None) -> bool:
        """Set user prime status with admin tracking"""
        try:
            expiry_date = None
            if is_prime:
                if expiry:
                    expiry_date = expiry
                elif expiry_days:
                    expiry_date = datetime.now() + timedelta(days=expiry_days)
            
            await self.execute_query("""
                UPDATE users 
                SET is_prime = ?, prime_expiry = ?
                WHERE user_id = ?
            """, (is_prime, expiry_date, user_id))
            
            # Log admin action
            if admin_id:
                action = "grant_prime" if is_prime else "remove_prime"
                details = json.dumps({
                    "user_id": user_id,
                    "expiry": expiry_date.isoformat() if expiry_date else None,
                    "action": action
                })
                
                await self.execute_query("""
                    INSERT INTO admin_actions (admin_id, action, target_user_id, details)
                    VALUES (?, ?, ?, ?)
                """, (admin_id, action, user_id, details))
            
            logger.info(f"Prime status updated for user {user_id}: {is_prime}")
            return True
        except Exception as e:
            logger.error(f"Error setting prime status for user {user_id}: {e}")
            return False
    
    async def check_prime_status(self, user_id: int) -> Dict[str, Any]:
        """Check if user's prime status is valid"""
        user = await self.get_user(user_id)
        if not user:
            return {"is_prime": False, "expired": True}
        
        is_prime = user.get('is_prime', False)
        prime_expiry = user.get('prime_expiry')
        
        if not is_prime:
            return {"is_prime": False, "expired": False}
        
        # Check if prime has expired
        if prime_expiry:
            expiry_dt = datetime.fromisoformat(prime_expiry.replace('Z', '+00:00')) if isinstance(prime_expiry, str) else prime_expiry
            if datetime.now() > expiry_dt:
                # Expire the user
                await self.set_prime_status(user_id, False)
                return {"is_prime": False, "expired": True, "expiry_date": expiry_dt}
        
        return {
            "is_prime": True, 
            "expired": False, 
            "expiry_date": prime_expiry
        }
    
    async def get_download_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's download statistics and limits"""
        user = await self.get_user(user_id)
        if not user:
            return {
                "downloads_this_hour": 0,
                "can_download": False,
                "reset_time": None,
                "in_cooldown": False
            }
        
        now = datetime.now()
        downloads_this_hour = user.get('downloads_this_hour', 0)
        hour_reset_time = user.get('hour_reset_time')
        cooldown_until = user.get('cooldown_until')
        
        # Parse datetime strings
        if isinstance(hour_reset_time, str):
            hour_reset_time = datetime.fromisoformat(hour_reset_time.replace('Z', '+00:00'))
        if isinstance(cooldown_until, str):
            cooldown_until = datetime.fromisoformat(cooldown_until.replace('Z', '+00:00'))
        
        # Check if hour has reset
        if not hour_reset_time or now >= hour_reset_time:
            await self.reset_hourly_downloads(user_id)
            downloads_this_hour = 0
            hour_reset_time = now + timedelta(hours=1)
        
        # Check cooldown
        in_cooldown = cooldown_until and now < cooldown_until
        
        # Check if user can download
        prime_status = await self.check_prime_status(user_id)
        can_download = prime_status['is_prime'] or (downloads_this_hour < 15 and not in_cooldown)
        
        return {
            "downloads_this_hour": downloads_this_hour,
            "can_download": can_download,
            "reset_time": hour_reset_time,
            "in_cooldown": in_cooldown,
            "cooldown_until": cooldown_until
        }
    
    async def increment_download_count(self, user_id: int) -> bool:
        """Increment user's download count and set cooldown if needed"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            downloads_this_hour = user.get('downloads_this_hour', 0) + 1
            now = datetime.now()
            
            # Set cooldown after 15 downloads for non-prime users
            cooldown_until = None
            prime_status = await self.check_prime_status(user_id)
            if not prime_status['is_prime'] and downloads_this_hour >= 15:
                cooldown_until = now + timedelta(minutes=30)
            
            await self.execute_query("""
                UPDATE users 
                SET downloads_this_hour = ?, 
                    downloads_today = downloads_today + 1,
                    downloads_count = downloads_count + 1,
                    last_download = ?,
                    cooldown_until = ?
                WHERE user_id = ?
            """, (downloads_this_hour, now, cooldown_until, user_id))
            
            return True
        except Exception as e:
            logger.error(f"Error incrementing download count for user {user_id}: {e}")
            return False
    
    async def reset_hourly_downloads(self, user_id: int) -> bool:
        """Reset user's hourly download count"""
        try:
            now = datetime.now()
            next_reset = now + timedelta(hours=1)
            
            await self.execute_query("""
                UPDATE users 
                SET downloads_this_hour = 0, 
                    hour_reset_time = ?,
                    cooldown_until = NULL
                WHERE user_id = ?
            """, (next_reset, user_id))
            
            return True
        except Exception as e:
            logger.error(f"Error resetting hourly downloads for user {user_id}: {e}")
            return False
    
    async def log_download(self, user_id: int, url: str = "", video_id: str = "", 
                          title: str = "", quality: str = "", download_type: str = "",
                          file_type: str = "", file_size: int = 0, duration: int = 0, 
                          success: bool = True, error_message: str = "", 
                          download_time: float = 0.0, ip_address: str = "", 
                          user_agent: str = "") -> bool:
        """Log download with comprehensive tracking"""
        try:
            # Insert into both tables for compatibility
            await self.execute_query("""
                INSERT INTO downloads 
                (user_id, url, video_id, title, quality, download_type, file_type, file_size, 
                 duration, success, error_message, download_time, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, url, video_id, title, quality, download_type, file_type, 
                  file_size, duration, success, error_message, download_time, ip_address, user_agent))
            
            # Legacy table for compatibility
            await self.execute_query("""
                INSERT INTO download_logs 
                (user_id, url, download_type, quality, file_size, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, url, download_type, quality, file_size, success, error_message))
            
            # Update user statistics
            await self.execute_query("""
                UPDATE users 
                SET last_download = ?,
                    last_seen = ?,
                    last_active = ?
                WHERE user_id = ?
            """, (datetime.now(), datetime.now(), datetime.now(), user_id))
            
            return True
        except Exception as e:
            logger.error(f"Error logging download for user {user_id}: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics"""
        try:
            stats = {}
            
            # User statistics
            stats['total_users'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM users", fetch_one=True
            )
            stats['total_users'] = stats['total_users']['count'] if stats['total_users'] else 0
            
            stats['prime_users'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE is_prime = TRUE", fetch_one=True
            )
            stats['prime_users'] = stats['prime_users']['count'] if stats['prime_users'] else 0
            
            stats['active_24h'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE last_seen > datetime('now', '-24 hours')", 
                fetch_one=True
            )
            stats['active_24h'] = stats['active_24h']['count'] if stats['active_24h'] else 0
            
            # Download statistics
            stats['total_downloads'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM downloads", fetch_one=True
            )
            stats['total_downloads'] = stats['total_downloads']['count'] if stats['total_downloads'] else 0
            
            stats['successful_downloads'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM downloads WHERE success = TRUE", fetch_one=True
            )
            stats['successful_downloads'] = stats['successful_downloads']['count'] if stats['successful_downloads'] else 0
            
            stats['downloads_24h'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM downloads WHERE created_at > datetime('now', '-24 hours')", 
                fetch_one=True
            )
            stats['downloads_24h'] = stats['downloads_24h']['count'] if stats['downloads_24h'] else 0
            
            # Legacy compatibility - also check download_logs table
            legacy_downloads = await self.execute_query(
                "SELECT COUNT(*) as count FROM download_logs WHERE success = TRUE", fetch_one=True
            )
            if legacy_downloads and legacy_downloads['count'] > stats['successful_downloads']:
                stats['total_downloads'] = max(stats['total_downloads'], legacy_downloads['count'])
            
            # Quality statistics
            quality_stats = await self.execute_query(
                "SELECT quality, COUNT(*) as count FROM downloads WHERE success = TRUE GROUP BY quality",
                fetch_all=True
            )
            stats['quality_distribution'] = {row['quality']: row['count'] for row in quality_stats} if quality_stats else {}
            
            # Video vs Audio downloads
            type_stats = await self.execute_query(
                "SELECT download_type, COUNT(*) as count FROM downloads WHERE success = TRUE GROUP BY download_type",
                fetch_all=True
            )
            stats['video_downloads'] = 0
            stats['audio_downloads'] = 0
            if type_stats:
                for row in type_stats:
                    if 'video' in row['download_type'].lower():
                        stats['video_downloads'] = row['count']
                    elif 'audio' in row['download_type'].lower():
                        stats['audio_downloads'] = row['count']
            
            # Failed downloads
            stats['failed_downloads'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM downloads WHERE success = FALSE", fetch_one=True
            )
            stats['failed_downloads'] = stats['failed_downloads']['count'] if stats['failed_downloads'] else 0
            
            # Performance metrics
            stats['success_rate'] = round(
                (stats['successful_downloads'] / max(stats['total_downloads'], 1)) * 100, 2
            )
            
            avg_download_time = await self.execute_query(
                "SELECT AVG(download_time) as avg_time FROM downloads WHERE success = TRUE AND download_time > 0",
                fetch_one=True
            )
            stats['avg_download_time'] = round(avg_download_time['avg_time'], 2) if avg_download_time and avg_download_time['avg_time'] else 0
            
            # Downloads today from legacy table for compatibility
            today = datetime.now().date()
            today_downloads = await self.execute_query(
                "SELECT COUNT(*) as count FROM download_logs WHERE date(download_time) = ?",
                (today,), fetch_one=True
            )
            stats['downloads_today'] = today_downloads['count'] if today_downloads else 0
            
            # Active users from last_active field
            stats['active_users_24h'] = await self.execute_query(
                "SELECT COUNT(*) as count FROM users WHERE last_active > datetime('now', '-24 hours')",
                fetch_one=True
            )
            stats['active_users_24h'] = stats['active_users_24h']['count'] if stats['active_users_24h'] else stats['active_24h']
            
            # Database performance
            stats['database_performance'] = {
                'query_count': self.query_count,
                'cache_hit_rate': round((self.cache_hits / max(self.cache_hits + self.cache_misses, 1)) * 100, 2),
                'avg_query_time': round(self.total_query_time / max(self.query_count, 1), 4),
                'cache_size': len(self.cache)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_users': 0,
                'prime_users': 0,
                'total_downloads': 0,
                'successful_downloads': 0,
                'active_24h': 0,
                'downloads_24h': 0,
                'downloads_today': 0,
                'success_rate': 0,
                'quality_distribution': {},
                'video_downloads': 0,
                'audio_downloads': 0,
                'failed_downloads': 0,
                'avg_download_time': 0,
                'active_users_24h': 0,
                'database_performance': {}
            }
    
    # Legacy compatibility method
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics (legacy compatibility)"""
        return await self.get_stats()
    
    async def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for broadcasting"""
        try:
            users = await self.execute_query("SELECT user_id FROM users WHERE is_blocked = FALSE", fetch_all=True)
            return [user['user_id'] for user in users] if users else []
        except Exception as e:
            logger.error(f"Error getting all user IDs: {e}")
            return []
    
    async def get_all_users(self, include_blocked: bool = False) -> List[int]:
        """Get all user IDs for broadcasting (new method)"""
        return await self.get_all_user_ids()
    
    async def set_user_state(self, user_id: int, state: str) -> bool:
        """Set user's current state"""
        try:
            await self.execute_query(
                "UPDATE users SET state = ? WHERE user_id = ?",
                (state, user_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error setting user state {user_id}: {e}")
            return False
    
    async def get_user_state(self, user_id: int) -> str:
        """Get user's current state"""
        user = await self.get_user(user_id)
        return user.get('state', '') if user else ''
    
    async def set_user_temp_data(self, user_id: int, key: str, value: str) -> bool:
        """Set temporary user data"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return False
            
            temp_data = json.loads(user.get('temp_data', '{}'))
            temp_data[key] = value
            
            await self.execute_query(
                "UPDATE users SET temp_data = ? WHERE user_id = ?",
                (json.dumps(temp_data), user_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error setting user temp data {user_id}: {e}")
            return False
    
    async def get_user_temp_data(self, user_id: int, key: str) -> Optional[str]:
        """Get temporary user data"""
        try:
            user = await self.get_user(user_id)
            if not user:
                return None
            
            temp_data = json.loads(user.get('temp_data', '{}'))
            return temp_data.get(key)
        except Exception as e:
            logger.error(f"Error getting user temp data {user_id}: {e}")
            return None
    
    async def clear_user_temp_data(self, user_id: int) -> bool:
        """Clear all temporary user data"""
        try:
            await self.execute_query(
                "UPDATE users SET temp_data = '{}' WHERE user_id = ?",
                (user_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error clearing user temp data {user_id}: {e}")
            return False
    
    async def cleanup_expired_prime_users(self) -> int:
        """Clean up expired prime users"""
        try:
            result = await self.execute_query("""
                UPDATE users 
                SET is_prime = FALSE, prime_expiry = NULL
                WHERE is_prime = TRUE AND prime_expiry < datetime('now')
            """)
            return result if result else 0
        except Exception as e:
            logger.error(f"Error cleaning up expired prime users: {e}")
            return 0
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get database health status"""
        try:
            start_time = time.time()
            
            # Test basic query
            test_result = await self.execute_query("SELECT 1 as test", fetch_one=True)
            query_time = time.time() - start_time
            
            # Check pool status
            pool_available = self.connection_pool.qsize()
            
            return {
                'status': 'healthy' if test_result and test_result['test'] == 1 else 'unhealthy',
                'query_response_time': round(query_time * 1000, 2),  # ms
                'connection_pool_available': pool_available,
                'connection_pool_total': self.pool_size,
                'cache_entries': len(self.cache),
                'total_queries': self.query_count,
                'cache_hit_rate': round((self.cache_hits / max(self.cache_hits + self.cache_misses, 1)) * 100, 2)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'query_response_time': 0,
                'connection_pool_available': 0,
                'connection_pool_total': self.pool_size,
                'cache_entries': len(self.cache)
            }

# Compatibility aliases for existing code
Database = DatabaseManager
DatabasePro = DatabaseManager