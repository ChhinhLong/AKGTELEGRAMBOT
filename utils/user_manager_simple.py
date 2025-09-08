"""
Simple User Manager for Telegram YouTube Downloader Bot
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class ProfessionalUserManager:
    def __init__(self, database, cache_ttl: int = 300, analytics_enabled: bool = True):
        """Initialize user manager"""
        self.db = database
        self.cache_ttl = cache_ttl
        self.analytics_enabled = analytics_enabled
        
        # In-memory caches
        self.user_cache = {}
        self.cache_timestamps = {}
        
        # User state management
        self.user_states: Dict[int, str] = {}
        self.user_temp_data: Dict[int, Dict[str, Any]] = defaultdict(dict)
        
        # Rate limiting
        self.user_downloads: Dict[int, list] = defaultdict(list)
        self.blocked_users = set()
    
    async def initialize_user(self, user_id: int, username: str):
        """Initialize user in database"""
        try:
            await self.db.add_user(user_id, username)
        except Exception as e:
            logger.error(f"Error initializing user {user_id}: {e}")
    
    async def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get user status including download limits"""
        try:
            user_data = await self.db.get_user(user_id)
            if not user_data:
                return {
                    'can_download': True,
                    'downloads_remaining': 15,
                    'is_prime': False,
                    'prime_expiry': None,
                    'reset_time': 'Next hour'
                }
            
            is_prime = user_data.get('is_prime', False)
            
            if is_prime:
                return {
                    'can_download': True,
                    'downloads_remaining': 999,
                    'is_prime': True,
                    'prime_expiry': user_data.get('prime_expiry'),
                    'reset_time': 'N/A'
                }
            
            # Check download limits for normal users
            current_hour = int(time.time() // 3600)
            downloads_this_hour = self.user_downloads[user_id]
            
            # Clean old downloads
            cutoff_time = time.time() - 3600  # 1 hour ago
            self.user_downloads[user_id] = [t for t in downloads_this_hour if t > cutoff_time]
            
            downloads_remaining = max(0, 15 - len(self.user_downloads[user_id]))
            can_download = downloads_remaining > 0
            
            next_reset = datetime.fromtimestamp((current_hour + 1) * 3600)
            
            return {
                'can_download': can_download,
                'downloads_remaining': downloads_remaining,
                'is_prime': False,
                'prime_expiry': None,
                'reset_time': next_reset.strftime('%H:%M')
            }
            
        except Exception as e:
            logger.error(f"Error getting user status: {e}")
            return {
                'can_download': True,
                'downloads_remaining': 15,
                'is_prime': False,
                'prime_expiry': None,
                'reset_time': 'Next hour'
            }
    
    async def update_usage(self, user_id: int):
        """Update user download usage"""
        try:
            current_time = time.time()
            self.user_downloads[user_id].append(current_time)
            await self.db.log_download(user_id)
        except Exception as e:
            logger.error(f"Error updating usage for user {user_id}: {e}")
    
    async def get_downloads_remaining(self, user_id: int) -> int:
        """Get remaining downloads for user"""
        status = await self.get_user_status(user_id)
        return status['downloads_remaining']
    
    async def set_user_state(self, user_id: int, state: str):
        """Set user state"""
        self.user_states[user_id] = state
    
    async def get_user_state(self, user_id: int) -> Optional[str]:
        """Get user state"""
        return self.user_states.get(user_id)
    
    async def clear_user_state(self, user_id: int):
        """Clear user state"""
        self.user_states.pop(user_id, None)
    
    async def set_user_data(self, user_id: int, key: str, value: Any):
        """Set temporary user data"""
        self.user_temp_data[user_id][key] = value
    
    async def get_user_data(self, user_id: int, key: str) -> Any:
        """Get temporary user data"""
        return self.user_temp_data[user_id].get(key)
    
    async def clear_user_data(self, user_id: int):
        """Clear temporary user data"""
        self.user_temp_data[user_id].clear()