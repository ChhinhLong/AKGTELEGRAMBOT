"""
Professional User Manager for Telegram YouTube Downloader Bot
Features: Enhanced user management, analytics tracking, premium features, session management
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from collections import defaultdict
import json
import hashlib

logger = logging.getLogger(__name__)

class ProfessionalUserManager:
    def __init__(self, database, cache_ttl: int = 300, analytics_enabled: bool = True,
                 rate_limit_window: int = 3600, max_requests_per_window: int = 100):
        """Initialize professional user manager"""
        self.db = database
        self.cache_ttl = cache_ttl
        self.analytics_enabled = analytics_enabled
        self.rate_limit_window = rate_limit_window
        self.max_requests_per_window = max_requests_per_window
        
        # In-memory caches and state management
        self.user_cache = {}
        self.cache_timestamps = {}
        self.user_states: Dict[int, str] = {}
        self.user_temp_data: Dict[int, Dict[str, Any]] = defaultdict(dict)
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        
        # Rate limiting and security
        self.user_requests: Dict[int, List[float]] = defaultdict(list)
        self.blocked_users: Set[int] = set()
        self.suspicious_activity: Dict[int, int] = defaultdict(int)
        
        # Analytics tracking
        self.user_events: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.command_usage: Dict[str, int] = defaultdict(int)
        self.download_analytics: Dict[str, int] = defaultdict(int)
        
        # Premium management
        self.premium_benefits = {
            'unlimited_downloads': True,
            'hd_quality_access': True,
            'no_cooldowns': True,
            'priority_support': True,
            'advanced_analytics': True,
            'early_features': True
        }
        
        # User engagement tracking
        self.user_engagement: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            'first_seen': None,
            'last_active': None,
            'total_commands': 0,
            'total_downloads': 0,
            'session_count': 0,
            'average_session_duration': 0,
            'preferred_quality': None,
            'most_used_command': None
        })
        
        # Start background tasks
        asyncio.create_task(self._cache_cleanup_task())
        asyncio.create_task(self._analytics_aggregation_task())
        asyncio.create_task(self._session_cleanup_task())
    
    async def initialize_user(self, user_id: int, username: str = None, 
                            first_name: str = None, last_name: str = None,
                            language_code: str = 'en') -> bool:
        """Initialize comprehensive user profile"""
        try:
            # Check if user exists
            user = await self.get_user_cached(user_id)
            if not user:
                # Create new user with full profile
                success = await self.db.add_user(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    language_code=language_code
                )
                
                if success:
                    # Initialize user engagement tracking
                    current_time = datetime.now()
                    self.user_engagement[user_id].update({
                        'first_seen': current_time,
                        'last_active': current_time,
                        'registration_date': current_time
                    })
                    
                    # Start user session
                    await self.start_user_session(user_id)
                    
                    # Track analytics
                    await self.track_user_event(user_id, 'user_registered', {
                        'username': username,
                        'language_code': language_code
                    })
                    
                    logger.info(f"New user initialized: {user_id} (@{username})")
                    return True
            else:
                # Update existing user
                await self.db.update_user_activity(user_id)
                
                # Update engagement tracking
                self.user_engagement[user_id]['last_active'] = datetime.now()
                
                # Resume or start session
                if user_id not in self.user_sessions:
                    await self.start_user_session(user_id)
                
                return True
            
        except Exception as e:
            logger.error(f"Error initializing user {user_id}: {e}")
            return False
    
    async def get_user_cached(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data with intelligent caching"""
        try:
            # Check cache first
            if user_id in self.user_cache:
                if time.time() - self.cache_timestamps[user_id] < self.cache_ttl:
                    return self.user_cache[user_id]
            
            # Fetch from database
            user_data = await self.db.get_user(user_id)
            
            # Update cache
            if user_data:
                self.user_cache[user_id] = user_data
                self.cache_timestamps[user_id] = time.time()
            
            return user_data
        except Exception as e:
            logger.error(f"Error getting cached user {user_id}: {e}")
            return None
    
    async def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user status with enhanced features"""
        try:
            # Ensure user is initialized
            await self.initialize_user(user_id)
            
            # Get user data
            user = await self.get_user_cached(user_id)
            if not user:
                return self._default_user_status()
            
            # Check premium status
            prime_status = await self.db.check_prime_status(user_id)
            
            # Get download statistics
            download_stats = await self.db.get_download_stats(user_id)
            
            # Calculate remaining downloads
            if prime_status['is_prime']:
                downloads_remaining = float('inf')
                can_download = True
                reset_time_str = 'N/A (Premium)'
            else:
                downloads_remaining = max(0, 15 - download_stats['downloads_this_hour'])
                can_download = download_stats['can_download']
                reset_time = download_stats.get('reset_time')
                reset_time_str = reset_time.strftime('%H:%M:%S') if reset_time else 'Unknown'
            
            # Format premium expiry
            prime_expiry_str = None
            if prime_status.get('expiry_date'):
                try:
                    expiry_date = prime_status['expiry_date']
                    if isinstance(expiry_date, str):
                        expiry_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                    prime_expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    prime_expiry_str = str(prime_status['expiry_date'])
            
            # Get user engagement metrics
            engagement = self.user_engagement[user_id]
            
            # Calculate user level and tier
            user_level = self._calculate_user_level(user_id)
            user_tier = self._get_user_tier(user_id, prime_status['is_prime'])
            
            return {
                'user_id': user_id,
                'username': user.get('username', 'Unknown'),
                'first_name': user.get('first_name', ''),
                'is_prime': prime_status['is_prime'],
                'prime_expiry': prime_expiry_str,
                'user_tier': user_tier,
                'user_level': user_level,
                'downloads_this_hour': download_stats['downloads_this_hour'],
                'downloads_remaining': downloads_remaining,
                'can_download': can_download,
                'reset_time': reset_time_str,
                'in_cooldown': download_stats.get('in_cooldown', False),
                'cooldown_until': download_stats.get('cooldown_until'),
                'total_downloads': user.get('downloads_count', 0),
                'member_since': user.get('created_at', ''),
                'last_active': engagement.get('last_active'),
                'session_active': user_id in self.user_sessions,
                'language_code': user.get('language_code', 'en'),
                'is_blocked': user_id in self.blocked_users,
                'premium_benefits': self.premium_benefits if prime_status['is_prime'] else {},
                'engagement_score': self._calculate_engagement_score(user_id)
            }
        except Exception as e:
            logger.error(f"Error getting user status {user_id}: {e}")
            return self._default_user_status()
    
    def _default_user_status(self) -> Dict[str, Any]:
        """Return default user status for error cases"""
        return {
            'user_id': 0,
            'username': 'Unknown',
            'first_name': '',
            'is_prime': False,
            'prime_expiry': None,
            'user_tier': 'Free',
            'user_level': 1,
            'downloads_this_hour': 0,
            'downloads_remaining': 15,
            'can_download': True,
            'reset_time': 'Unknown',
            'in_cooldown': False,
            'cooldown_until': None,
            'total_downloads': 0,
            'member_since': '',
            'last_active': None,
            'session_active': False,
            'language_code': 'en',
            'is_blocked': False,
            'premium_benefits': {},
            'engagement_score': 0
        }
    
    async def update_usage(self, user_id: int, download_type: str = '', quality: str = '') -> bool:
        """Enhanced usage tracking with analytics"""
        try:
            # Update database
            success = await self.db.increment_download_count(user_id)
            
            if success:
                # Track analytics
                await self.track_user_event(user_id, 'download_completed', {
                    'download_type': download_type,
                    'quality': quality,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Update engagement metrics
                self.user_engagement[user_id]['total_downloads'] += 1
                if quality:
                    self.user_engagement[user_id]['preferred_quality'] = quality
                
                # Track download analytics
                self.download_analytics[f"{download_type}_{quality}"] += 1
                self.download_analytics['total'] += 1
                
                # Invalidate cache
                if user_id in self.user_cache:
                    del self.user_cache[user_id]
                
                logger.info(f"Updated usage for user {user_id}: {download_type} ({quality})")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error updating usage for user {user_id}: {e}")
            return False
    
    async def can_user_download(self, user_id: int) -> Dict[str, Any]:
        """Enhanced download permission checking with detailed reasoning"""
        try:
            # Check if user is blocked
            if user_id in self.blocked_users:
                return {
                    'can_download': False,
                    'reason': 'User is blocked due to suspicious activity',
                    'recommendation': 'Contact support for assistance'
                }
            
            # Check rate limiting
            if not await self._check_rate_limit(user_id):
                return {
                    'can_download': False,
                    'reason': 'Rate limit exceeded. Too many requests in short time',
                    'recommendation': 'Please wait before making another request'
                }
            
            # Get user status
            status = await self.get_user_status(user_id)
            
            if status['is_prime']:
                return {
                    'can_download': True,
                    'reason': f"Premium user ({status['user_tier']}) - unlimited downloads",
                    'remaining_downloads': 'Unlimited',
                    'premium_benefits': list(self.premium_benefits.keys())
                }
            
            if status['in_cooldown']:
                return {
                    'can_download': False,
                    'reason': f"In cooldown period until {status['cooldown_until']}",
                    'recommendation': 'Upgrade to Premium for no cooldowns'
                }
            
            if status['downloads_this_hour'] >= 15:
                return {
                    'can_download': False,
                    'reason': f"Download limit reached (15/hour). Resets at {status['reset_time']}",
                    'recommendation': 'Upgrade to Premium for unlimited downloads'
                }
            
            return {
                'can_download': True,
                'reason': f"Downloads remaining: {status['downloads_remaining']}/15",
                'reset_time': status['reset_time'],
                'upgrade_suggestion': 'Consider Premium for unlimited downloads'
            }
            
        except Exception as e:
            logger.error(f"Error checking user download permission {user_id}: {e}")
            return {
                'can_download': False,
                'reason': 'Error checking permissions',
                'recommendation': 'Please try again later'
            }
    
    async def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        try:
            current_time = time.time()
            user_requests = self.user_requests[user_id]
            
            # Clean old requests
            cutoff_time = current_time - self.rate_limit_window
            self.user_requests[user_id] = [req_time for req_time in user_requests if req_time > cutoff_time]
            
            # Check limit
            if len(self.user_requests[user_id]) >= self.max_requests_per_window:
                # Log suspicious activity
                self.suspicious_activity[user_id] += 1
                if self.suspicious_activity[user_id] > 5:
                    self.blocked_users.add(user_id)
                    await self.track_user_event(user_id, 'user_blocked', {
                        'reason': 'excessive_rate_limit_violations'
                    })
                return False
            
            # Add current request
            self.user_requests[user_id].append(current_time)
            return True
        except Exception as e:
            logger.error(f"Rate limit check error for user {user_id}: {e}")
            return True  # Allow on error
    
    async def start_user_session(self, user_id: int) -> str:
        """Start a new user session with tracking"""
        try:
            session_id = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:16]
            
            self.user_sessions[user_id] = {
                'session_id': session_id,
                'start_time': datetime.now(),
                'commands_used': 0,
                'downloads_made': 0,
                'last_activity': datetime.now()
            }
            
            # Track analytics
            await self.track_user_event(user_id, 'session_started', {
                'session_id': session_id
            })
            
            return session_id
        except Exception as e:
            logger.error(f"Error starting session for user {user_id}: {e}")
            return ""
    
    async def end_user_session(self, user_id: int) -> bool:
        """End user session and save analytics"""
        try:
            if user_id not in self.user_sessions:
                return False
            
            session = self.user_sessions[user_id]
            session_duration = (datetime.now() - session['start_time']).total_seconds()
            
            # Update engagement metrics
            engagement = self.user_engagement[user_id]
            engagement['session_count'] += 1
            engagement['total_commands'] += session['commands_used']
            
            # Calculate average session duration
            if engagement['session_count'] > 1:
                engagement['average_session_duration'] = (
                    (engagement['average_session_duration'] * (engagement['session_count'] - 1) + session_duration) /
                    engagement['session_count']
                )
            else:
                engagement['average_session_duration'] = session_duration
            
            # Track analytics
            await self.track_user_event(user_id, 'session_ended', {
                'session_id': session['session_id'],
                'duration': session_duration,
                'commands_used': session['commands_used'],
                'downloads_made': session['downloads_made']
            })
            
            # Remove session
            del self.user_sessions[user_id]
            
            return True
        except Exception as e:
            logger.error(f"Error ending session for user {user_id}: {e}")
            return False
    
    async def track_command_usage(self, user_id: int, command: str) -> bool:
        """Track command usage for analytics"""
        try:
            # Update global command stats
            self.command_usage[command] += 1
            
            # Update user session
            if user_id in self.user_sessions:
                self.user_sessions[user_id]['commands_used'] += 1
                self.user_sessions[user_id]['last_activity'] = datetime.now()
            
            # Update engagement
            self.user_engagement[user_id]['total_commands'] += 1
            self.user_engagement[user_id]['most_used_command'] = command
            
            # Track event
            await self.track_user_event(user_id, 'command_used', {
                'command': command
            })
            
            return True
        except Exception as e:
            logger.error(f"Error tracking command usage: {e}")
            return False
    
    async def track_user_event(self, user_id: int, event_type: str, data: Dict[str, Any] = None) -> bool:
        """Track user events for analytics"""
        try:
            if not self.analytics_enabled:
                return True
            
            event = {
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            }
            
            # Store in memory (limited history)
            self.user_events[user_id].append(event)
            if len(self.user_events[user_id]) > 100:  # Keep last 100 events
                self.user_events[user_id] = self.user_events[user_id][-100:]
            
            logger.debug(f"Tracked event {event_type} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error tracking user event: {e}")
            return False
    
    def _calculate_user_level(self, user_id: int) -> int:
        """Calculate user level based on activity"""
        engagement = self.user_engagement[user_id]
        total_downloads = engagement.get('total_downloads', 0)
        total_commands = engagement.get('total_commands', 0)
        session_count = engagement.get('session_count', 0)
        
        # Level calculation based on activity
        level = 1
        level += total_downloads // 10  # 1 level per 10 downloads
        level += total_commands // 20   # 1 level per 20 commands
        level += session_count // 5     # 1 level per 5 sessions
        
        return min(level, 100)  # Cap at level 100
    
    def _get_user_tier(self, user_id: int, is_prime: bool) -> str:
        """Determine user tier based on status and activity"""
        if is_prime:
            return 'Premium'
        
        level = self._calculate_user_level(user_id)
        if level >= 50:
            return 'Expert'
        elif level >= 25:
            return 'Advanced'
        elif level >= 10:
            return 'Intermediate'
        else:
            return 'Beginner'
    
    def _calculate_engagement_score(self, user_id: int) -> int:
        """Calculate user engagement score (0-100)"""
        try:
            engagement = self.user_engagement[user_id]
            
            # Factors for engagement score
            downloads = min(engagement.get('total_downloads', 0), 100)
            commands = min(engagement.get('total_commands', 0), 200) // 2
            sessions = min(engagement.get('session_count', 0), 50) * 2
            avg_session = min(engagement.get('average_session_duration', 0), 600) // 10
            
            # Recent activity bonus
            last_active = engagement.get('last_active')
            recency_bonus = 0
            if last_active:
                days_since = (datetime.now() - last_active).days
                if days_since <= 1:
                    recency_bonus = 20
                elif days_since <= 7:
                    recency_bonus = 10
                elif days_since <= 30:
                    recency_bonus = 5
            
            score = downloads * 0.3 + commands * 0.2 + sessions * 0.2 + avg_session * 0.1 + recency_bonus * 0.2
            return min(int(score), 100)
        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return 0
    
    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user analytics"""
        try:
            engagement = self.user_engagement[user_id]
            user_status = await self.get_user_status(user_id)
            recent_events = self.user_events[user_id][-10:]  # Last 10 events
            
            return {
                'user_id': user_id,
                'engagement_metrics': engagement,
                'user_level': user_status['user_level'],
                'user_tier': user_status['user_tier'],
                'engagement_score': user_status['engagement_score'],
                'recent_events': recent_events,
                'session_active': user_id in self.user_sessions,
                'current_session': self.user_sessions.get(user_id, {}),
                'total_events': len(self.user_events[user_id]),
                'is_premium': user_status['is_prime'],
                'account_age_days': self._calculate_account_age(user_id)
            }
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {}
    
    def _calculate_account_age(self, user_id: int) -> int:
        """Calculate account age in days"""
        try:
            first_seen = self.user_engagement[user_id].get('first_seen')
            if first_seen:
                return (datetime.now() - first_seen).days
            return 0
        except:
            return 0
    
    async def _cache_cleanup_task(self):
        """Background task to clean up expired cache entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                current_time = time.time()
                expired_keys = [
                    user_id for user_id, timestamp in self.cache_timestamps.items()
                    if current_time - timestamp > self.cache_ttl
                ]
                
                for user_id in expired_keys:
                    self.user_cache.pop(user_id, None)
                    self.cache_timestamps.pop(user_id, None)
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    async def _analytics_aggregation_task(self):
        """Background task to aggregate analytics data"""
        while True:
            try:
                await asyncio.sleep(600)  # Every 10 minutes
                
                # Log aggregate statistics
                total_users = len(self.user_engagement)
                active_sessions = len(self.user_sessions)
                total_commands = sum(self.command_usage.values())
                total_downloads = self.download_analytics.get('total', 0)
                
                if total_users > 0:
                    logger.info(f"Analytics: {total_users} users, {active_sessions} active sessions, "
                              f"{total_commands} commands, {total_downloads} downloads")
                
            except Exception as e:
                logger.error(f"Analytics aggregation error: {e}")
    
    async def _session_cleanup_task(self):
        """Background task to clean up inactive sessions"""
        while True:
            try:
                await asyncio.sleep(900)  # Every 15 minutes
                
                current_time = datetime.now()
                inactive_sessions = []
                
                for user_id, session in self.user_sessions.items():
                    last_activity = session.get('last_activity', session['start_time'])
                    if (current_time - last_activity).total_seconds() > 1800:  # 30 minutes inactive
                        inactive_sessions.append(user_id)
                
                for user_id in inactive_sessions:
                    await self.end_user_session(user_id)
                
                if inactive_sessions:
                    logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
                    
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
    
    # Legacy compatibility methods
    async def get_downloads_remaining(self, user_id: int) -> int:
        """Get number of downloads remaining for user (legacy compatibility)"""
        try:
            status = await self.get_user_status(user_id)
            if status['is_prime']:
                return float('inf')
            return max(0, status['downloads_remaining'])
        except Exception as e:
            logger.error(f"Error getting downloads remaining for user {user_id}: {e}")
            return 0
    
    async def set_user_state(self, user_id: int, state: str) -> bool:
        """Set user's current interaction state"""
        try:
            self.user_states[user_id] = state
            return await self.db.set_user_state(user_id, state)
        except Exception as e:
            logger.error(f"Error setting user state {user_id}: {e}")
            return False
    
    async def get_user_state(self, user_id: int) -> str:
        """Get user's current interaction state"""
        try:
            # Check memory first
            if user_id in self.user_states:
                return self.user_states[user_id]
            # Fall back to database
            return await self.db.get_user_state(user_id)
        except Exception as e:
            logger.error(f"Error getting user state {user_id}: {e}")
            return ""
    
    async def clear_user_state(self, user_id: int) -> bool:
        """Clear user's current interaction state"""
        try:
            self.user_states.pop(user_id, None)
            return await self.db.set_user_state(user_id, "")
        except Exception as e:
            logger.error(f"Error clearing user state {user_id}: {e}")
            return False
    
    async def set_user_data(self, user_id: int, key: str, value: str) -> bool:
        """Set temporary user data"""
        try:
            self.user_temp_data[user_id][key] = value
            return await self.db.set_user_temp_data(user_id, key, value)
        except Exception as e:
            logger.error(f"Error setting user data {user_id}: {e}")
            return False
    
    async def get_user_data(self, user_id: int, key: str) -> Optional[str]:
        """Get temporary user data"""
        try:
            # Check memory first
            if user_id in self.user_temp_data and key in self.user_temp_data[user_id]:
                return self.user_temp_data[user_id][key]
            # Fall back to database
            return await self.db.get_user_temp_data(user_id, key)
        except Exception as e:
            logger.error(f"Error getting user data {user_id}: {e}")
            return None
    
    async def clear_user_data(self, user_id: int) -> bool:
        """Clear all temporary user data"""
        try:
            self.user_temp_data.pop(user_id, None)
            return await self.db.clear_user_temp_data(user_id)
        except Exception as e:
            logger.error(f"Error clearing user data {user_id}: {e}")
            return False
    
    async def grant_prime(self, user_id: int, days: int = None, admin_id: int = None) -> bool:
        """Grant premium status to user"""
        try:
            expiry = None
            if days:
                expiry = datetime.now() + timedelta(days=days)
            
            success = await self.db.set_prime_status(user_id, True, expiry=expiry, admin_id=admin_id)
            
            if success:
                # Invalidate cache
                self.user_cache.pop(user_id, None)
                
                # Track event
                await self.track_user_event(user_id, 'premium_granted', {
                    'days': days,
                    'admin_id': admin_id,
                    'expiry': expiry.isoformat() if expiry else None
                })
                
                logger.info(f"Premium granted to user {user_id} for {days} days" if days else f"Premium granted to user {user_id} (permanent)")
            
            return success
        except Exception as e:
            logger.error(f"Error granting premium to user {user_id}: {e}")
            return False
    
    async def revoke_prime(self, user_id: int, admin_id: int = None) -> bool:
        """Revoke premium status from user"""
        try:
            success = await self.db.set_prime_status(user_id, False, admin_id=admin_id)
            
            if success:
                # Invalidate cache
                self.user_cache.pop(user_id, None)
                
                # Track event
                await self.track_user_event(user_id, 'premium_revoked', {
                    'admin_id': admin_id
                })
                
                logger.info(f"Premium revoked from user {user_id}")
            
            return success
        except Exception as e:
            logger.error(f"Error revoking premium from user {user_id}: {e}")
            return False
    
    async def get_user_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed user information"""
        try:
            user_status = await self.get_user_status(user_id)
            analytics = await self.get_user_analytics(user_id)
            
            if not user_status:
                return None
            
            return {
                **user_status,
                'analytics': analytics,
                'premium_benefits': self.premium_benefits if user_status['is_prime'] else {},
                'system_info': {
                    'cache_hit': user_id in self.user_cache,
                    'session_active': user_id in self.user_sessions,
                    'rate_limited': user_id in self.blocked_users
                }
            }
        except Exception as e:
            logger.error(f"Error getting user info {user_id}: {e}")
            return None

# Compatibility alias for existing code
UserManager = ProfessionalUserManager