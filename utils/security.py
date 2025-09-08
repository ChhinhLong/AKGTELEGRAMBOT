"""
Professional Security Module for Telegram YouTube Downloader Bot
Features: Rate limiting, input validation, threat detection, security monitoring
"""

import re
import time
import logging
import hashlib
import ipaddress
from typing import Dict, Set, List, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs
from collections import defaultdict, deque
from datetime import datetime, timedelta
import asyncio
import json

logger = logging.getLogger(__name__)

class SecurityManager:
    def __init__(self, database=None, enable_monitoring: bool = True):
        """Initialize comprehensive security manager"""
        self.db = database
        self.enable_monitoring = enable_monitoring
        
        # Rate limiting
        self.rate_limits: Dict[int, deque] = defaultdict(lambda: deque(maxlen=100))
        self.global_rate_limit: deque = deque(maxlen=1000)
        self.rate_limit_windows = {
            'user_requests': {'window': 60, 'limit': 30},  # 30 requests per minute per user
            'user_downloads': {'window': 3600, 'limit': 20},  # 20 downloads per hour per user (non-premium)
            'global_requests': {'window': 60, 'limit': 1000},  # 1000 global requests per minute
            'admin_commands': {'window': 300, 'limit': 50}   # 50 admin commands per 5 minutes
        }
        
        # Security tracking
        self.blocked_users: Set[int] = set()
        self.suspicious_users: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            'violations': 0,
            'first_violation': None,
            'last_violation': None,
            'violation_types': set(),
            'trust_score': 100
        })
        
        # Threat detection
        self.failed_attempts: Dict[int, int] = defaultdict(int)
        self.attack_patterns: Dict[str, int] = defaultdict(int)
        self.ip_tracking: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'requests': deque(maxlen=100),
            'users': set(),
            'blocked': False
        })
        
        # Content validation
        self.malicious_patterns = [
            r'(?i)(javascript|vbscript|onload|onerror|onclick)',
            r'(?i)(<script|</script>|<iframe|</iframe>)',
            r'(?i)(eval\s*\(|setTimeout\s*\(|setInterval\s*\()',
            r'(?i)(document\.|window\.|location\.)',
            r'(?i)(union\s+select|drop\s+table|delete\s+from)'
        ]
        
        # URL validation
        self.allowed_domains = {
            'youtube.com', 'www.youtube.com', 'm.youtube.com',
            'youtu.be', 'music.youtube.com'
        }
        
        self.blocked_domains = {
            'malicious-site.com',  # Example blocked domains
            'phishing-site.net',
            'spam-site.org'
        }
        
        # Security events
        self.security_events: List[Dict[str, Any]] = []
        self.security_metrics = {
            'blocked_requests': 0,
            'rate_limited_users': 0,
            'malicious_content_detected': 0,
            'suspicious_activity_detected': 0,
            'total_security_events': 0
        }
        
        # Auto-ban thresholds
        self.auto_ban_thresholds = {
            'violations_per_hour': 10,
            'failed_attempts': 20,
            'trust_score_minimum': 20,
            'rate_limit_violations': 5
        }
        
        # Start background security tasks
        if enable_monitoring:
            asyncio.create_task(self._security_monitoring_task())
            asyncio.create_task(self._cleanup_task())
    
    async def check_user_permission(self, user_id: int, action: str, 
                                  ip_address: str = None) -> Dict[str, Any]:
        """Comprehensive user permission and security check"""
        try:
            # Check if user is blocked
            if user_id in self.blocked_users:
                await self._log_security_event(
                    event_type='blocked_user_attempt',
                    user_id=user_id,
                    details={'action': action, 'ip': ip_address}
                )
                return {
                    'allowed': False,
                    'reason': 'User is blocked',
                    'security_level': 'high_risk',
                    'action_required': 'contact_admin'
                }
            
            # Check rate limits
            rate_check = await self._check_rate_limits(user_id, action, ip_address)
            if not rate_check['allowed']:
                return rate_check
            
            # Check trust score
            trust_score = self._calculate_trust_score(user_id)
            if trust_score < self.auto_ban_thresholds['trust_score_minimum']:
                await self._flag_suspicious_user(user_id, 'low_trust_score')
                return {
                    'allowed': False,
                    'reason': 'Low trust score',
                    'security_level': 'high_risk',
                    'trust_score': trust_score
                }
            
            # IP-based checks
            if ip_address:
                ip_check = await self._check_ip_security(ip_address, user_id)
                if not ip_check['allowed']:
                    return ip_check
            
            # Action-specific checks
            action_check = await self._check_action_permission(user_id, action)
            if not action_check['allowed']:
                return action_check
            
            # Log successful security check
            await self._log_security_event(
                event_type='permission_granted',
                user_id=user_id,
                details={'action': action, 'trust_score': trust_score}
            )
            
            return {
                'allowed': True,
                'trust_score': trust_score,
                'security_level': self._get_security_level(trust_score),
                'rate_limit_remaining': self._get_remaining_requests(user_id),
                'recommendations': self._get_security_recommendations(user_id)
            }
            
        except Exception as e:
            logger.error(f"Security check error for user {user_id}: {e}")
            # Fail securely - deny on error
            return {
                'allowed': False,
                'reason': 'Security check failed',
                'security_level': 'unknown',
                'error': str(e)
            }
    
    async def _check_rate_limits(self, user_id: int, action: str, 
                               ip_address: str = None) -> Dict[str, Any]:
        """Advanced rate limiting with multiple dimensions"""
        current_time = time.time()
        
        # User-specific rate limiting
        user_requests = self.rate_limits[user_id]
        window = self.rate_limit_windows['user_requests']
        
        # Clean old requests
        cutoff_time = current_time - window['window']
        while user_requests and user_requests[0] < cutoff_time:
            user_requests.popleft()
        
        # Check user rate limit
        if len(user_requests) >= window['limit']:
            await self._flag_rate_limit_violation(user_id, 'user_rate_limit')
            return {
                'allowed': False,
                'reason': f'Rate limit exceeded: {len(user_requests)}/{window["limit"]} requests per {window["window"]}s',
                'security_level': 'medium_risk',
                'retry_after': window['window']
            }
        
        # Global rate limiting
        global_cutoff = current_time - self.rate_limit_windows['global_requests']['window']
        while self.global_rate_limit and self.global_rate_limit[0] < global_cutoff:
            self.global_rate_limit.popleft()
        
        if len(self.global_rate_limit) >= self.rate_limit_windows['global_requests']['limit']:
            return {
                'allowed': False,
                'reason': 'Global rate limit exceeded',
                'security_level': 'high_risk',
                'retry_after': self.rate_limit_windows['global_requests']['window']
            }
        
        # Add current request
        user_requests.append(current_time)
        self.global_rate_limit.append(current_time)
        
        return {'allowed': True}
    
    async def _check_ip_security(self, ip_address: str, user_id: int) -> Dict[str, Any]:
        """IP-based security checks"""
        try:
            # Validate IP format
            try:
                ip_obj = ipaddress.ip_address(ip_address)
            except ValueError:
                await self._log_security_event(
                    event_type='invalid_ip',
                    user_id=user_id,
                    details={'ip': ip_address}
                )
                return {
                    'allowed': False,
                    'reason': 'Invalid IP address format',
                    'security_level': 'high_risk'
                }
            
            # Check if IP is blocked
            ip_info = self.ip_tracking[ip_address]
            if ip_info['blocked']:
                return {
                    'allowed': False,
                    'reason': 'IP address is blocked',
                    'security_level': 'high_risk'
                }
            
            # Check for suspicious IP activity
            current_time = time.time()
            recent_requests = [req for req in ip_info['requests'] if current_time - req < 3600]
            
            if len(recent_requests) > 200:  # More than 200 requests per hour from single IP
                await self._flag_suspicious_ip(ip_address, 'high_request_volume')
                return {
                    'allowed': False,
                    'reason': 'Suspicious IP activity detected',
                    'security_level': 'high_risk'
                }
            
            # Track this request
            ip_info['requests'].append(current_time)
            ip_info['users'].add(user_id)
            
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"IP security check error: {e}")
            return {'allowed': True}  # Allow on error, but log it
    
    async def _check_action_permission(self, user_id: int, action: str) -> Dict[str, Any]:
        """Action-specific permission checks"""
        try:
            # Download action checks
            if action == 'download':
                # Check for download abuse patterns
                recent_violations = self.suspicious_users[user_id]['violations']
                if recent_violations > 5:
                    return {
                        'allowed': False,
                        'reason': 'Too many recent violations',
                        'security_level': 'medium_risk'
                    }
            
            # Admin action checks
            elif action.startswith('admin_'):
                admin_window = self.rate_limit_windows['admin_commands']
                # Additional admin-specific checks would go here
                pass
            
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"Action permission check error: {e}")
            return {'allowed': True}
    
    def is_valid_youtube_url(self, url: str) -> Tuple[bool, str]:
        """Enhanced YouTube URL validation with security checks"""
        try:
            if not url or not isinstance(url, str):
                return False, "Invalid URL format"
            
            # Basic format validation
            if len(url) > 2000:  # Extremely long URLs are suspicious
                return False, "URL too long"
            
            # Check for malicious patterns
            for pattern in self.malicious_patterns:
                if re.search(pattern, url):
                    self.security_metrics['malicious_content_detected'] += 1
                    return False, "Malicious content detected in URL"
            
            # Parse URL
            try:
                parsed = urlparse(url.lower())
            except Exception:
                return False, "URL parsing failed"
            
            # Check domain
            if not parsed.netloc:
                return False, "No domain in URL"
            
            # Remove www. prefix for consistency
            domain = parsed.netloc.replace('www.', '')
            
            # Check against blocked domains
            if domain in self.blocked_domains:
                return False, "Domain is blocked"
            
            # Check against allowed YouTube domains
            if domain not in self.allowed_domains:
                return False, "Not a valid YouTube domain"
            
            # YouTube-specific validation
            if domain == 'youtu.be':
                # youtu.be/VIDEO_ID format
                video_id = parsed.path.lstrip('/')
                if not video_id or len(video_id) != 11:
                    return False, "Invalid YouTube video ID"
                # Check for valid video ID characters
                if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                    return False, "Invalid video ID format"
            else:
                # youtube.com format
                if not parsed.path.startswith(('/watch', '/shorts')):
                    return False, "Not a valid YouTube video URL"
                
                # Extract video ID
                query_params = parse_qs(parsed.query)
                video_id = query_params.get('v', [None])[0]
                
                if not video_id:
                    return False, "No video ID found"
                
                if len(video_id) != 11:
                    return False, "Invalid video ID length"
                
                if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                    return False, "Invalid video ID characters"
            
            return True, "Valid YouTube URL"
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def validate_input(self, text: str, input_type: str = 'general') -> Tuple[bool, str]:
        """Comprehensive input validation and sanitization"""
        try:
            if not text or not isinstance(text, str):
                return False, "Invalid input format"
            
            # Length checks
            max_lengths = {
                'general': 1000,
                'message': 4000,
                'url': 2000,
                'username': 50,
                'command': 100
            }
            
            max_length = max_lengths.get(input_type, 1000)
            if len(text) > max_length:
                return False, f"Input too long (max {max_length} characters)"
            
            # Check for malicious patterns
            for pattern in self.malicious_patterns:
                if re.search(pattern, text):
                    self.security_metrics['malicious_content_detected'] += 1
                    return False, "Malicious content detected"
            
            # Type-specific validation
            if input_type == 'url':
                return self.is_valid_youtube_url(text)
            
            elif input_type == 'username':
                if not re.match(r'^[a-zA-Z0-9_]{1,50}$', text.replace('@', '')):
                    return False, "Invalid username format"
            
            elif input_type == 'command':
                if not re.match(r'^/[a-zA-Z0-9_]{1,50}(\s.*)?$', text):
                    return False, "Invalid command format"
            
            # Check for SQL injection patterns
            sql_patterns = [
                r'(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)',
                r'(?i)(or\s+1\s*=\s*1|and\s+1\s*=\s*1)',
                r'(?i)(exec\s*\(|execute\s*\()'
            ]
            
            for pattern in sql_patterns:
                if re.search(pattern, text):
                    return False, "Potentially malicious SQL detected"
            
            return True, "Input validated"
            
        except Exception as e:
            logger.error(f"Input validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _calculate_trust_score(self, user_id: int) -> int:
        """Calculate user trust score based on behavior"""
        try:
            user_info = self.suspicious_users[user_id]
            base_score = user_info['trust_score']
            
            # Reduce score based on violations
            violations = user_info['violations']
            score = max(0, base_score - (violations * 10))
            
            # Time-based recovery (trust increases over time without violations)
            if user_info['last_violation']:
                last_violation = user_info['last_violation']
                if isinstance(last_violation, str):
                    last_violation = datetime.fromisoformat(last_violation)
                
                days_since_violation = (datetime.now() - last_violation).days
                recovery_bonus = min(20, days_since_violation * 2)  # Max 20 points recovery
                score = min(100, score + recovery_bonus)
            
            return int(score)
            
        except Exception as e:
            logger.error(f"Trust score calculation error: {e}")
            return 50  # Default neutral score
    
    def _get_security_level(self, trust_score: int) -> str:
        """Get security level based on trust score"""
        if trust_score >= 80:
            return 'low_risk'
        elif trust_score >= 50:
            return 'medium_risk'
        elif trust_score >= 20:
            return 'high_risk'
        else:
            return 'critical_risk'
    
    def _get_remaining_requests(self, user_id: int) -> int:
        """Get remaining requests in current window"""
        try:
            user_requests = self.rate_limits[user_id]
            window = self.rate_limit_windows['user_requests']
            
            current_time = time.time()
            cutoff_time = current_time - window['window']
            
            # Count recent requests
            recent_requests = sum(1 for req_time in user_requests if req_time > cutoff_time)
            
            return max(0, window['limit'] - recent_requests)
        except Exception:
            return 0
    
    def _get_security_recommendations(self, user_id: int) -> List[str]:
        """Get security recommendations for user"""
        recommendations = []
        trust_score = self._calculate_trust_score(user_id)
        
        if trust_score < 70:
            recommendations.append("Improve account security by following usage guidelines")
        
        if user_id in self.suspicious_users and self.suspicious_users[user_id]['violations'] > 3:
            recommendations.append("Recent violations detected - please review terms of service")
        
        remaining_requests = self._get_remaining_requests(user_id)
        if remaining_requests < 5:
            recommendations.append("Approaching rate limit - consider upgrading to premium")
        
        return recommendations
    
    async def _flag_suspicious_user(self, user_id: int, violation_type: str, 
                                  details: Dict[str, Any] = None):
        """Flag user for suspicious activity"""
        try:
            user_info = self.suspicious_users[user_id]
            user_info['violations'] += 1
            user_info['last_violation'] = datetime.now()
            user_info['violation_types'].add(violation_type)
            
            if not user_info['first_violation']:
                user_info['first_violation'] = datetime.now()
            
            # Reduce trust score
            user_info['trust_score'] = max(0, user_info['trust_score'] - 15)
            
            # Check for auto-ban
            if (user_info['violations'] >= self.auto_ban_thresholds['violations_per_hour'] or
                user_info['trust_score'] <= self.auto_ban_thresholds['trust_score_minimum']):
                await self._auto_ban_user(user_id, violation_type)
            
            # Log security event
            await self._log_security_event(
                event_type='suspicious_activity',
                user_id=user_id,
                details={
                    'violation_type': violation_type,
                    'total_violations': user_info['violations'],
                    'trust_score': user_info['trust_score'],
                    'details': details or {}
                }
            )
            
            self.security_metrics['suspicious_activity_detected'] += 1
            
        except Exception as e:
            logger.error(f"Error flagging suspicious user: {e}")
    
    async def _flag_rate_limit_violation(self, user_id: int, violation_type: str):
        """Handle rate limit violations"""
        try:
            await self._flag_suspicious_user(user_id, violation_type)
            self.security_metrics['rate_limited_users'] += 1
            
            # Track failed attempts
            self.failed_attempts[user_id] += 1
            
            if self.failed_attempts[user_id] >= self.auto_ban_thresholds['failed_attempts']:
                await self._auto_ban_user(user_id, 'excessive_rate_limit_violations')
                
        except Exception as e:
            logger.error(f"Error handling rate limit violation: {e}")
    
    async def _flag_suspicious_ip(self, ip_address: str, reason: str):
        """Flag IP address for suspicious activity"""
        try:
            ip_info = self.ip_tracking[ip_address]
            
            # For now, just log it - could implement IP blocking
            await self._log_security_event(
                event_type='suspicious_ip',
                details={
                    'ip_address': ip_address,
                    'reason': reason,
                    'request_count': len(ip_info['requests']),
                    'user_count': len(ip_info['users'])
                }
            )
            
        except Exception as e:
            logger.error(f"Error flagging suspicious IP: {e}")
    
    async def _auto_ban_user(self, user_id: int, reason: str):
        """Automatically ban user for security violations"""
        try:
            self.blocked_users.add(user_id)
            
            # Log to database if available
            if self.db and hasattr(self.db, 'execute_query'):
                await self.db.execute_query(
                    "UPDATE users SET is_blocked = TRUE WHERE user_id = ?",
                    (user_id,)
                )
            
            await self._log_security_event(
                event_type='user_auto_banned',
                user_id=user_id,
                details={
                    'reason': reason,
                    'violations': self.suspicious_users[user_id]['violations'],
                    'trust_score': self.suspicious_users[user_id]['trust_score']
                }
            )
            
            logger.warning(f"Auto-banned user {user_id} for {reason}")
            
        except Exception as e:
            logger.error(f"Error auto-banning user: {e}")
    
    async def _log_security_event(self, event_type: str, user_id: int = None, 
                                details: Dict[str, Any] = None):
        """Log security events for monitoring and analysis"""
        try:
            event = {
                'event_type': event_type,
                'user_id': user_id,
                'timestamp': datetime.now().isoformat(),
                'details': details or {}
            }
            
            # Store in memory (keep last 1000 events)
            self.security_events.append(event)
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-1000:]
            
            # Log to database if available
            if self.db and hasattr(self.db, 'execute_query'):
                try:
                    await self.db.execute_query("""
                        INSERT INTO system_logs (level, message, module, extra_data)
                        VALUES (?, ?, ?, ?)
                    """, ('SECURITY', f"Security event: {event_type}", 'security', json.dumps(event)))
                except:
                    pass  # Don't fail security logging on database errors
            
            self.security_metrics['total_security_events'] += 1
            
            logger.info(f"Security event: {event_type} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    async def _security_monitoring_task(self):
        """Background task for security monitoring and alerts"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                # Monitor for attack patterns
                current_time = time.time()
                
                # Check for DDoS patterns
                recent_global_requests = sum(1 for req_time in self.global_rate_limit 
                                           if current_time - req_time < 60)
                
                if recent_global_requests > 500:  # High request volume
                    await self._log_security_event(
                        event_type='potential_ddos',
                        details={'requests_per_minute': recent_global_requests}
                    )
                
                # Monitor trust score trends
                low_trust_users = sum(1 for user_id in self.suspicious_users 
                                    if self._calculate_trust_score(user_id) < 30)
                
                if low_trust_users > 10:
                    await self._log_security_event(
                        event_type='high_risk_user_surge',
                        details={'low_trust_user_count': low_trust_users}
                    )
                
                # Log security metrics
                logger.info(f"Security metrics: {self.security_metrics}")
                
            except Exception as e:
                logger.error(f"Security monitoring error: {e}")
    
    async def _cleanup_task(self):
        """Background cleanup of old security data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                current_time = time.time()
                
                # Clean old rate limit data
                for user_id in list(self.rate_limits.keys()):
                    user_requests = self.rate_limits[user_id]
                    # Remove requests older than 24 hours
                    cutoff = current_time - 86400
                    while user_requests and user_requests[0] < cutoff:
                        user_requests.popleft()
                    
                    # Remove empty deques
                    if not user_requests:
                        del self.rate_limits[user_id]
                
                # Clean old IP tracking data
                for ip_address in list(self.ip_tracking.keys()):
                    ip_info = self.ip_tracking[ip_address]
                    # Remove requests older than 24 hours
                    cutoff = current_time - 86400
                    ip_info['requests'] = deque(
                        [req for req in ip_info['requests'] if req > cutoff],
                        maxlen=100
                    )
                    
                    # Remove empty tracking
                    if not ip_info['requests'] and not ip_info['blocked']:
                        del self.ip_tracking[ip_address]
                
                # Reset failed attempts for users not recently active
                for user_id in list(self.failed_attempts.keys()):
                    # Reset if no activity in 24 hours
                    if user_id not in self.rate_limits:
                        del self.failed_attempts[user_id]
                
                logger.debug("Security data cleanup completed")
                
            except Exception as e:
                logger.error(f"Security cleanup error: {e}")
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get comprehensive security metrics"""
        try:
            current_time = time.time()
            
            # Calculate active metrics
            active_users = len(self.rate_limits)
            blocked_user_count = len(self.blocked_users)
            suspicious_user_count = len(self.suspicious_users)
            
            # Trust score distribution
            trust_scores = [self._calculate_trust_score(user_id) for user_id in self.suspicious_users.keys()]
            avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 100
            
            # Recent activity
            recent_events = [event for event in self.security_events 
                           if (current_time - datetime.fromisoformat(event['timestamp']).timestamp()) < 3600]
            
            return {
                'metrics': self.security_metrics,
                'active_users': active_users,
                'blocked_users': blocked_user_count,
                'suspicious_users': suspicious_user_count,
                'average_trust_score': round(avg_trust_score, 2),
                'recent_events_count': len(recent_events),
                'global_request_rate': len(self.global_rate_limit),
                'ip_addresses_tracked': len(self.ip_tracking),
                'security_level': 'healthy' if avg_trust_score > 70 else 'monitoring_required'
            }
        except Exception as e:
            logger.error(f"Error getting security metrics: {e}")
            return {'error': str(e)}
    
    # User management methods
    def block_user(self, user_id: int, reason: str = "Admin action"):
        """Manually block a user"""
        self.blocked_users.add(user_id)
        asyncio.create_task(self._log_security_event(
            event_type='user_manually_blocked',
            user_id=user_id,
            details={'reason': reason}
        ))
    
    def unblock_user(self, user_id: int, reason: str = "Admin action"):
        """Manually unblock a user"""
        self.blocked_users.discard(user_id)
        # Reset suspicious activity
        if user_id in self.suspicious_users:
            self.suspicious_users[user_id]['trust_score'] = 75  # Give them a second chance
        asyncio.create_task(self._log_security_event(
            event_type='user_manually_unblocked',
            user_id=user_id,
            details={'reason': reason}
        ))
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if user is blocked"""
        return user_id in self.blocked_users
    
    def get_user_security_info(self, user_id: int) -> Dict[str, Any]:
        """Get security information for a specific user"""
        try:
            return {
                'user_id': user_id,
                'is_blocked': user_id in self.blocked_users,
                'trust_score': self._calculate_trust_score(user_id),
                'security_level': self._get_security_level(self._calculate_trust_score(user_id)),
                'violations': self.suspicious_users[user_id]['violations'],
                'violation_types': list(self.suspicious_users[user_id]['violation_types']),
                'failed_attempts': self.failed_attempts[user_id],
                'remaining_requests': self._get_remaining_requests(user_id),
                'recommendations': self._get_security_recommendations(user_id)
            }
        except Exception as e:
            logger.error(f"Error getting user security info: {e}")
            return {'error': str(e)}