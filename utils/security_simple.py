"""
Simple Security module for input validation and protection
"""

import re
import time
import logging
from typing import Dict, Set
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self):
        """Initialize security manager"""
        self.failed_attempts: Dict[int, int] = {}
        self.blocked_users: Set[int] = set()
        self.rate_limits: Dict[int, Dict[str, int]] = {}
    
    def is_valid_youtube_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com']
        except:
            return False
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return user_id in self.blocked_users
    
    def block_user(self, user_id: int):
        """Block a user"""
        self.blocked_users.add(user_id)
        logger.warning(f"User {user_id} has been blocked")
    
    def unblock_user(self, user_id: int):
        """Unblock a user"""
        self.blocked_users.discard(user_id)
        logger.info(f"User {user_id} has been unblocked")