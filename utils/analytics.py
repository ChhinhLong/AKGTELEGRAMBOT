"""
Professional Analytics Module for Telegram YouTube Downloader Bot
Features: Comprehensive tracking, performance metrics, user behavior analysis, reporting
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, deque
import json
import statistics
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class UserEvent:
    """User event data structure"""
    user_id: int
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    session_id: str = ""
    ip_address: str = ""

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    metric_name: str
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = None

class AnalyticsManager:
    def __init__(self, database, enable_detailed_tracking: bool = True,
                 retention_days: int = 30, aggregation_interval: int = 300):
        """Initialize comprehensive analytics manager"""
        self.db = database
        self.enable_detailed_tracking = enable_detailed_tracking
        self.retention_days = retention_days
        self.aggregation_interval = aggregation_interval
        
        # Event tracking
        self.user_events: deque = deque(maxlen=10000)  # Keep last 10k events in memory
        self.event_counters: Dict[str, int] = defaultdict(int)
        self.hourly_events: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        
        # Performance tracking
        self.performance_metrics: deque = deque(maxlen=5000)
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.error_tracking: Dict[str, int] = defaultdict(int)
        
        # User behavior analytics
        self.user_sessions: Dict[int, Dict[str, Any]] = {}
        self.user_journeys: Dict[int, List[str]] = defaultdict(list)
        self.command_sequences: List[List[str]] = []
        
        # Download analytics
        self.download_metrics = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'quality_distribution': defaultdict(int),
            'format_distribution': defaultdict(int),
            'duration_stats': [],
            'file_size_stats': [],
            'download_times': deque(maxlen=1000)
        }
        
        # Business metrics
        self.business_metrics = {
            'daily_active_users': defaultdict(set),
            'weekly_active_users': defaultdict(set),
            'monthly_active_users': defaultdict(set),
            'retention_rates': {},
            'conversion_funnel': defaultdict(int),
            'premium_conversion_rate': 0,
            'user_lifetime_value': defaultdict(float)
        }
        
        # Real-time dashboard data
        self.real_time_stats = {
            'active_users_now': set(),
            'downloads_last_hour': 0,
            'errors_last_hour': 0,
            'avg_response_time': 0,
            'server_load': 0,
            'last_updated': datetime.now()
        }
        
        # Alerts and monitoring
        self.alert_thresholds = {
            'error_rate': 0.05,  # 5% error rate
            'response_time': 2.0,  # 2 seconds
            'download_failure_rate': 0.1,  # 10% failure rate
            'user_drop_rate': 0.3  # 30% session drop rate
        }
        
        # Cohort analysis
        self.user_cohorts: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # A/B testing framework
        self.ab_tests: Dict[str, Dict[str, Any]] = {}
        
        # Start background tasks
        if enable_detailed_tracking:
            asyncio.create_task(self._aggregation_task())
            asyncio.create_task(self._performance_monitoring_task())
            asyncio.create_task(self._cleanup_task())
            asyncio.create_task(self._real_time_dashboard_task())
    
    async def track_user_event(self, user_id: int, event_type: str, 
                             data: Dict[str, Any] = None, session_id: str = "",
                             ip_address: str = "") -> bool:
        """Track comprehensive user events"""
        try:
            if not self.enable_detailed_tracking:
                return True
            
            current_time = datetime.now()
            
            # Create event
            event = UserEvent(
                user_id=user_id,
                event_type=event_type,
                timestamp=current_time,
                data=data or {},
                session_id=session_id,
                ip_address=ip_address
            )
            
            # Store event
            self.user_events.append(event)
            
            # Update counters
            self.event_counters[event_type] += 1
            current_hour = current_time.hour
            self.hourly_events[event_type][current_hour] += 1
            
            # Track user journey
            self.user_journeys[user_id].append(event_type)
            if len(self.user_journeys[user_id]) > 50:  # Keep last 50 events per user
                self.user_journeys[user_id] = self.user_journeys[user_id][-50:]
            
            # Update real-time stats
            self.real_time_stats['active_users_now'].add(user_id)
            
            # Business intelligence tracking
            await self._update_business_metrics(user_id, event_type, data)
            
            # Session tracking
            await self._update_user_session(user_id, event_type, session_id)
            
            # Funnel analysis
            await self._update_conversion_funnel(user_id, event_type)
            
            logger.debug(f"Tracked event: {event_type} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking user event: {e}")
            return False
    
    async def track_performance_metric(self, metric_name: str, value: float,
                                     metadata: Dict[str, Any] = None) -> bool:
        """Track performance metrics"""
        try:
            metric = PerformanceMetric(
                metric_name=metric_name,
                value=value,
                timestamp=datetime.now(),
                metadata=metadata or {}
            )
            
            self.performance_metrics.append(metric)
            
            # Update specific tracking
            if metric_name.endswith('_response_time'):
                self.response_times[metric_name].append(value)
            
            logger.debug(f"Tracked performance metric: {metric_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error tracking performance metric: {e}")
            return False
    
    async def track_download_event(self, user_id: int, success: bool, 
                                 quality: str = "", file_type: str = "",
                                 duration: int = 0, file_size: int = 0,
                                 download_time: float = 0.0, error: str = "") -> bool:
        """Track download-specific analytics"""
        try:
            # Update download metrics
            self.download_metrics['total_downloads'] += 1
            
            if success:
                self.download_metrics['successful_downloads'] += 1
                
                if quality:
                    self.download_metrics['quality_distribution'][quality] += 1
                
                if file_type:
                    self.download_metrics['format_distribution'][file_type] += 1
                
                if duration > 0:
                    self.download_metrics['duration_stats'].append(duration)
                    if len(self.download_metrics['duration_stats']) > 1000:
                        self.download_metrics['duration_stats'] = self.download_metrics['duration_stats'][-1000:]
                
                if file_size > 0:
                    self.download_metrics['file_size_stats'].append(file_size)
                    if len(self.download_metrics['file_size_stats']) > 1000:
                        self.download_metrics['file_size_stats'] = self.download_metrics['file_size_stats'][-1000:]
                
                if download_time > 0:
                    self.download_metrics['download_times'].append(download_time)
            else:
                self.download_metrics['failed_downloads'] += 1
                if error:
                    self.error_tracking[f"download_error_{error}"] += 1
            
            # Track as user event
            await self.track_user_event(user_id, 'download_attempt', {
                'success': success,
                'quality': quality,
                'file_type': file_type,
                'duration': duration,
                'file_size': file_size,
                'download_time': download_time,
                'error': error
            })
            
            # Update real-time stats
            if success:
                self.real_time_stats['downloads_last_hour'] += 1
            else:
                self.real_time_stats['errors_last_hour'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error tracking download event: {e}")
            return False
    
    async def _update_business_metrics(self, user_id: int, event_type: str, 
                                     data: Dict[str, Any]):
        """Update business intelligence metrics"""
        try:
            current_date = datetime.now().date()
            current_week = current_date.isocalendar()[1]
            current_month = current_date.month
            
            # Update DAU/WAU/MAU
            self.business_metrics['daily_active_users'][current_date].add(user_id)
            self.business_metrics['weekly_active_users'][current_week].add(user_id)
            self.business_metrics['monthly_active_users'][current_month].add(user_id)
            
            # Track premium conversions
            if event_type == 'premium_granted':
                self.business_metrics['conversion_funnel']['premium_conversion'] += 1
            
            # Track user value events
            if event_type == 'download_completed':
                self.business_metrics['user_lifetime_value'][user_id] += 0.1  # Arbitrary value per download
            
        except Exception as e:
            logger.error(f"Error updating business metrics: {e}")
    
    async def _update_user_session(self, user_id: int, event_type: str, session_id: str):
        """Update user session tracking"""
        try:
            if session_id and session_id not in self.user_sessions:
                self.user_sessions[session_id] = {
                    'user_id': user_id,
                    'start_time': datetime.now(),
                    'last_activity': datetime.now(),
                    'events': [],
                    'commands_used': 0,
                    'downloads_attempted': 0
                }
            elif session_id:
                session = self.user_sessions[session_id]
                session['last_activity'] = datetime.now()
                session['events'].append(event_type)
                
                if event_type.startswith('command_'):
                    session['commands_used'] += 1
                elif event_type == 'download_attempt':
                    session['downloads_attempted'] += 1
            
        except Exception as e:
            logger.error(f"Error updating user session: {e}")
    
    async def _update_conversion_funnel(self, user_id: int, event_type: str):
        """Update conversion funnel metrics"""
        try:
            funnel_events = [
                'user_started_bot',
                'first_command_used',
                'first_download_attempt',
                'first_successful_download',
                'premium_upgrade_viewed',
                'premium_granted'
            ]
            
            if event_type in funnel_events:
                self.business_metrics['conversion_funnel'][event_type] += 1
            
        except Exception as e:
            logger.error(f"Error updating conversion funnel: {e}")
    
    async def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary"""
        try:
            current_time = datetime.now()
            
            # Calculate time-based metrics
            last_24h = current_time - timedelta(hours=24)
            last_hour = current_time - timedelta(hours=1)
            
            # Filter recent events
            recent_events = [e for e in self.user_events if e.timestamp > last_24h]
            hourly_events = [e for e in self.user_events if e.timestamp > last_hour]
            
            # User analytics
            unique_users_24h = len(set(e.user_id for e in recent_events))
            unique_users_1h = len(set(e.user_id for e in hourly_events))
            
            # Event analytics
            event_distribution = defaultdict(int)
            for event in recent_events:
                event_distribution[event.event_type] += 1
            
            # Performance analytics
            if self.response_times:
                avg_response_times = {}
                for endpoint, times in self.response_times.items():
                    if times:
                        avg_response_times[endpoint] = statistics.mean(times)
            else:
                avg_response_times = {}
            
            # Download analytics
            download_success_rate = 0
            if self.download_metrics['total_downloads'] > 0:
                download_success_rate = (
                    self.download_metrics['successful_downloads'] / 
                    self.download_metrics['total_downloads']
                ) * 100
            
            # Calculate error rates
            total_events = len(recent_events)
            error_events = sum(1 for e in recent_events if 'error' in e.event_type.lower())
            error_rate = (error_events / max(total_events, 1)) * 100
            
            return {
                'timestamp': current_time.isoformat(),
                'time_range': '24 hours',
                
                # User metrics
                'user_metrics': {
                    'unique_users_24h': unique_users_24h,
                    'unique_users_1h': unique_users_1h,
                    'active_sessions': len(self.user_sessions),
                    'daily_active_users': len(self.business_metrics['daily_active_users'].get(current_time.date(), set())),
                },
                
                # Event metrics
                'event_metrics': {
                    'total_events_24h': len(recent_events),
                    'total_events_1h': len(hourly_events),
                    'event_distribution': dict(event_distribution),
                    'events_per_user': len(recent_events) / max(unique_users_24h, 1)
                },
                
                # Performance metrics
                'performance_metrics': {
                    'avg_response_times': avg_response_times,
                    'error_rate': round(error_rate, 2),
                    'total_errors': error_events
                },
                
                # Download metrics
                'download_metrics': {
                    'total_downloads': self.download_metrics['total_downloads'],
                    'successful_downloads': self.download_metrics['successful_downloads'],
                    'failed_downloads': self.download_metrics['failed_downloads'],
                    'success_rate': round(download_success_rate, 2),
                    'quality_distribution': dict(self.download_metrics['quality_distribution']),
                    'format_distribution': dict(self.download_metrics['format_distribution'])
                },
                
                # Business metrics
                'business_metrics': {
                    'conversion_funnel': dict(self.business_metrics['conversion_funnel']),
                    'premium_conversion_rate': self.business_metrics['premium_conversion_rate']
                },
                
                # Real-time stats
                'real_time_stats': {
                    **self.real_time_stats,
                    'active_users_now': len(self.real_time_stats['active_users_now'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    async def get_user_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get analytics for a specific user"""
        try:
            # Filter user events
            user_events = [e for e in self.user_events if e.user_id == user_id]
            
            if not user_events:
                return {'user_id': user_id, 'events': 0, 'message': 'No events found'}
            
            # Sort by timestamp
            user_events.sort(key=lambda x: x.timestamp)
            
            # Calculate metrics
            first_seen = user_events[0].timestamp
            last_seen = user_events[-1].timestamp
            total_events = len(user_events)
            
            # Event distribution
            event_counts = defaultdict(int)
            for event in user_events:
                event_counts[event.event_type] += 1
            
            # Session analysis
            user_sessions = [s for s in self.user_sessions.values() if s.get('user_id') == user_id]
            
            # Download analysis
            download_events = [e for e in user_events if e.event_type == 'download_attempt']
            successful_downloads = sum(1 for e in download_events if e.data.get('success', False))
            
            # Calculate engagement score
            engagement_score = self._calculate_user_engagement_score(user_id, user_events)
            
            # User journey analysis
            journey = self.user_journeys.get(user_id, [])
            
            return {
                'user_id': user_id,
                'first_seen': first_seen.isoformat() if first_seen else None,
                'last_seen': last_seen.isoformat() if last_seen else None,
                'total_events': total_events,
                'event_distribution': dict(event_counts),
                'session_count': len(user_sessions),
                'download_attempts': len(download_events),
                'successful_downloads': successful_downloads,
                'download_success_rate': (successful_downloads / max(len(download_events), 1)) * 100,
                'engagement_score': engagement_score,
                'user_journey': journey[-10:],  # Last 10 events
                'account_age_days': (datetime.now() - first_seen).days if first_seen else 0,
                'last_activity_hours': (datetime.now() - last_seen).total_seconds() / 3600 if last_seen else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user analytics: {e}")
            return {'user_id': user_id, 'error': str(e)}
    
    def _calculate_user_engagement_score(self, user_id: int, user_events: List[UserEvent]) -> int:
        """Calculate user engagement score (0-100)"""
        try:
            if not user_events:
                return 0
            
            # Factors for engagement
            total_events = len(user_events)
            unique_event_types = len(set(e.event_type for e in user_events))
            
            # Time span
            if len(user_events) > 1:
                time_span = (user_events[-1].timestamp - user_events[0].timestamp).days
                events_per_day = total_events / max(time_span, 1)
            else:
                events_per_day = 1
            
            # Downloads
            download_events = [e for e in user_events if e.event_type == 'download_attempt']
            successful_downloads = sum(1 for e in download_events if e.data.get('success', False))
            
            # Calculate score
            event_score = min(total_events * 2, 40)  # Max 40 points for events
            variety_score = min(unique_event_types * 5, 20)  # Max 20 points for variety
            frequency_score = min(events_per_day * 10, 20)  # Max 20 points for frequency
            download_score = min(successful_downloads * 2, 20)  # Max 20 points for downloads
            
            total_score = event_score + variety_score + frequency_score + download_score
            return min(int(total_score), 100)
            
        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return 50  # Default score
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            current_time = datetime.now()
            
            # Response time analysis
            response_time_stats = {}
            for endpoint, times in self.response_times.items():
                if times:
                    response_time_stats[endpoint] = {
                        'mean': statistics.mean(times),
                        'median': statistics.median(times),
                        'p95': statistics.quantiles(sorted(times), n=20)[18] if len(times) >= 20 else max(times),
                        'p99': statistics.quantiles(sorted(times), n=100)[98] if len(times) >= 100 else max(times),
                        'min': min(times),
                        'max': max(times)
                    }
            
            # Download performance
            download_times = list(self.download_metrics['download_times'])
            download_stats = {}
            if download_times:
                download_stats = {
                    'mean': statistics.mean(download_times),
                    'median': statistics.median(download_times),
                    'p95': statistics.quantiles(sorted(download_times), n=20)[18] if len(download_times) >= 20 else max(download_times),
                    'min': min(download_times),
                    'max': max(download_times)
                }
            
            # Error analysis
            total_errors = sum(self.error_tracking.values())
            error_distribution = dict(self.error_tracking)
            
            # Performance metrics over time
            recent_metrics = [m for m in self.performance_metrics 
                            if (current_time - m.timestamp).total_seconds() < 3600]
            
            return {
                'timestamp': current_time.isoformat(),
                'report_period': '1 hour',
                'response_time_analysis': response_time_stats,
                'download_performance': download_stats,
                'error_analysis': {
                    'total_errors': total_errors,
                    'error_distribution': error_distribution,
                    'error_rate': (total_errors / max(len(recent_metrics), 1)) * 100
                },
                'system_health': {
                    'metrics_collected': len(recent_metrics),
                    'avg_response_time': self.real_time_stats['avg_response_time'],
                    'server_load': self.real_time_stats['server_load']
                },
                'recommendations': self._generate_performance_recommendations(response_time_stats, download_stats)
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}
    
    def _generate_performance_recommendations(self, response_stats: Dict, download_stats: Dict) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        try:
            # Check response times
            for endpoint, stats in response_stats.items():
                if stats['mean'] > 2.0:
                    recommendations.append(f"High response time for {endpoint} (avg: {stats['mean']:.2f}s)")
                
                if stats['p95'] > 5.0:
                    recommendations.append(f"P95 response time too high for {endpoint} (p95: {stats['p95']:.2f}s)")
            
            # Check download performance
            if download_stats and download_stats['mean'] > 30.0:
                recommendations.append(f"Download times are high (avg: {download_stats['mean']:.2f}s)")
            
            # Check error rates
            total_events = sum(self.event_counters.values())
            total_errors = sum(self.error_tracking.values())
            if total_events > 0:
                error_rate = (total_errors / total_events) * 100
                if error_rate > 5.0:
                    recommendations.append(f"Error rate is high ({error_rate:.1f}%)")
            
            if not recommendations:
                recommendations.append("System performance is within acceptable thresholds")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append("Unable to generate recommendations due to analysis error")
        
        return recommendations
    
    async def _aggregation_task(self):
        """Background task to aggregate analytics data"""
        while True:
            try:
                await asyncio.sleep(self.aggregation_interval)
                
                # Aggregate hourly data
                current_hour = datetime.now().hour
                
                # Calculate metrics for current hour
                hourly_summary = {
                    'hour': current_hour,
                    'timestamp': datetime.now().isoformat(),
                    'events': dict(self.hourly_events),
                    'unique_users': len(self.real_time_stats['active_users_now']),
                    'downloads': self.real_time_stats['downloads_last_hour'],
                    'errors': self.real_time_stats['errors_last_hour']
                }
                
                # Store to database if available
                if self.db and hasattr(self.db, 'execute_query'):
                    try:
                        await self.db.execute_query("""
                            INSERT INTO analytics_hourly (hour, data, created_at)
                            VALUES (?, ?, ?)
                        """, (current_hour, json.dumps(hourly_summary), datetime.now()))
                    except:
                        pass  # Don't fail on database errors
                
                logger.debug(f"Aggregated analytics for hour {current_hour}")
                
            except Exception as e:
                logger.error(f"Analytics aggregation error: {e}")
    
    async def _performance_monitoring_task(self):
        """Background task to monitor performance and generate alerts"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check alert thresholds
                await self._check_performance_alerts()
                
                # Update real-time stats
                await self._update_real_time_stats()
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
    
    async def _check_performance_alerts(self):
        """Check if any performance metrics exceed alert thresholds"""
        try:
            # Check error rate
            total_events = sum(self.event_counters.values())
            total_errors = sum(self.error_tracking.values())
            
            if total_events > 100:  # Only check if we have sufficient data
                error_rate = total_errors / total_events
                if error_rate > self.alert_thresholds['error_rate']:
                    await self.track_user_event(
                        user_id=0,  # System event
                        event_type='alert_error_rate_high',
                        data={'error_rate': error_rate, 'threshold': self.alert_thresholds['error_rate']}
                    )
            
            # Check download failure rate
            if self.download_metrics['total_downloads'] > 50:
                failure_rate = self.download_metrics['failed_downloads'] / self.download_metrics['total_downloads']
                if failure_rate > self.alert_thresholds['download_failure_rate']:
                    await self.track_user_event(
                        user_id=0,
                        event_type='alert_download_failure_rate_high',
                        data={'failure_rate': failure_rate, 'threshold': self.alert_thresholds['download_failure_rate']}
                    )
            
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")
    
    async def _update_real_time_stats(self):
        """Update real-time dashboard statistics"""
        try:
            current_time = datetime.now()
            last_hour = current_time - timedelta(hours=1)
            
            # Count recent events
            recent_events = [e for e in self.user_events if e.timestamp > last_hour]
            
            # Update stats
            self.real_time_stats.update({
                'downloads_last_hour': sum(1 for e in recent_events if e.event_type == 'download_attempt'),
                'errors_last_hour': sum(1 for e in recent_events if 'error' in e.event_type.lower()),
                'last_updated': current_time
            })
            
            # Calculate average response time
            if self.response_times:
                all_times = []
                for times in self.response_times.values():
                    all_times.extend(list(times))
                
                if all_times:
                    self.real_time_stats['avg_response_time'] = statistics.mean(all_times)
            
            # Clean up active users (remove inactive)
            self.real_time_stats['active_users_now'] = {
                user_id for user_id in self.real_time_stats['active_users_now']
                if any(e.user_id == user_id and e.timestamp > last_hour for e in recent_events)
            }
            
        except Exception as e:
            logger.error(f"Error updating real-time stats: {e}")
    
    async def _cleanup_task(self):
        """Background task to clean up old analytics data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                cutoff_time = datetime.now() - timedelta(days=self.retention_days)
                
                # Clean old events
                old_count = len(self.user_events)
                self.user_events = deque(
                    [e for e in self.user_events if e.timestamp > cutoff_time],
                    maxlen=10000
                )
                new_count = len(self.user_events)
                
                # Clean old performance metrics
                self.performance_metrics = deque(
                    [m for m in self.performance_metrics if m.timestamp > cutoff_time],
                    maxlen=5000
                )
                
                # Clean old user sessions
                active_sessions = {}
                for session_id, session in self.user_sessions.items():
                    if session['last_activity'] > cutoff_time:
                        active_sessions[session_id] = session
                self.user_sessions = active_sessions
                
                logger.info(f"Analytics cleanup: removed {old_count - new_count} old events")
                
            except Exception as e:
                logger.error(f"Analytics cleanup error: {e}")
    
    async def _real_time_dashboard_task(self):
        """Background task to maintain real-time dashboard data"""
        while True:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # This would update a real-time dashboard
                # For now, just log key metrics
                if len(self.real_time_stats['active_users_now']) > 0:
                    logger.info(f"Real-time: {len(self.real_time_stats['active_users_now'])} active users, "
                              f"{self.real_time_stats['downloads_last_hour']} downloads/hour")
                
            except Exception as e:
                logger.error(f"Real-time dashboard error: {e}")
    
    def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'active_users': len(self.real_time_stats['active_users_now']),
                'downloads_last_hour': self.real_time_stats['downloads_last_hour'],
                'errors_last_hour': self.real_time_stats['errors_last_hour'],
                'avg_response_time': round(self.real_time_stats['avg_response_time'], 3),
                'server_load': self.real_time_stats['server_load'],
                'system_health': 'healthy' if self.real_time_stats['errors_last_hour'] < 10 else 'degraded',
                'total_events': len(self.user_events),
                'total_downloads': self.download_metrics['total_downloads'],
                'success_rate': round((
                    self.download_metrics['successful_downloads'] / 
                    max(self.download_metrics['total_downloads'], 1)
                ) * 100, 1)
            }
        except Exception as e:
            logger.error(f"Error getting real-time dashboard: {e}")
            return {'error': str(e)}
    
    # Export and reporting methods
    async def export_analytics_data(self, start_date: datetime, end_date: datetime, 
                                  format_type: str = 'json') -> str:
        """Export analytics data for external analysis"""
        try:
            # Filter events by date range
            filtered_events = [
                e for e in self.user_events 
                if start_date <= e.timestamp <= end_date
            ]
            
            if format_type == 'json':
                export_data = {
                    'export_info': {
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'total_events': len(filtered_events),
                        'exported_at': datetime.now().isoformat()
                    },
                    'events': [asdict(event) for event in filtered_events],
                    'summary': await self.get_analytics_summary()
                }
                return json.dumps(export_data, indent=2, default=str)
            
            elif format_type == 'csv':
                # Simple CSV export
                import io
                output = io.StringIO()
                output.write('timestamp,user_id,event_type,data\n')
                
                for event in filtered_events:
                    output.write(f'{event.timestamp},{event.user_id},{event.event_type},"{json.dumps(event.data)}"\n')
                
                return output.getvalue()
            
            else:
                return json.dumps({'error': f'Unsupported format: {format_type}'})
                
        except Exception as e:
            logger.error(f"Error exporting analytics data: {e}")
            return json.dumps({'error': str(e)})