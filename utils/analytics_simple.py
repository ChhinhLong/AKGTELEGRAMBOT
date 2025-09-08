"""
Simple Analytics module for basic monitoring
"""

import logging
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

class AnalyticsManager:
    def __init__(self, database):
        """Initialize analytics manager"""
        self.db = database
        self.counters = defaultdict(int)
    
    async def track_user_event(self, user_id: int, event_type: str, data: Dict[str, Any] = None):
        """Track user event"""
        try:
            self.counters[f"event_{event_type}"] += 1
            self.counters[f"user_{user_id}_events"] += 1
            logger.debug(f"Tracked event {event_type} for user {user_id}")
        except Exception as e:
            logger.error(f"Error tracking event: {e}")
    
    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Get analytics summary"""
        try:
            stats = await self.db.get_stats()
            return {
                'timestamp': datetime.now().isoformat(),
                'database_stats': stats,
                'event_counters': dict(self.counters)
            }
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {'error': str(e)}