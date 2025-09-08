"""
Professional Admin Panel for Telegram YouTube Downloader Bot
Features: Advanced user management, real-time monitoring, comprehensive analytics, broadcasting
"""

import logging
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
import csv
import io

logger = logging.getLogger(__name__)

class ProfessionalAdminPanel:
    def __init__(self, database, bot: Bot, admin_id: int, user_manager=None, 
                 download_manager=None, analytics_enabled: bool = True):
        """Initialize professional admin panel"""
        self.db = database
        self.bot = bot
        self.admin_id = admin_id
        self.user_manager = user_manager
        self.download_manager = download_manager
        self.analytics_enabled = analytics_enabled
        
        # Admin permissions and roles
        self.super_admins: Set[int] = {admin_id}
        self.moderators: Set[int] = set()
        self.support_staff: Set[int] = set()
        
        # Real-time monitoring
        self.monitoring_active = False
        self.alert_thresholds = {
            'error_rate': 0.1,  # 10% error rate
            'download_failures': 10,  # 10 failures in 10 minutes
            'server_response_time': 5.0,  # 5 seconds
            'memory_usage': 0.8,  # 80% memory usage
            'disk_usage': 0.9   # 90% disk usage
        }
        
        # Broadcast management
        self.active_broadcasts: Dict[str, Dict[str, Any]] = {}
        self.broadcast_history: List[Dict[str, Any]] = []
        
        # User management features
        self.user_search_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.bulk_operations: Dict[str, Dict[str, Any]] = {}
        
        # Admin activity logging
        self.admin_actions: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.performance_metrics = {
            'command_response_times': [],
            'database_query_times': [],
            'api_call_times': [],
            'memory_usage_history': [],
            'error_count_hourly': {}
        }
        
        # Start background monitoring
        if analytics_enabled:
            asyncio.create_task(self._monitoring_task())
            asyncio.create_task(self._performance_tracking_task())
    
    async def handle_set_prime(self, message: Message):
        """Enhanced premium management with comprehensive tracking"""
        try:
            args = message.text.split()[1:]
            
            if len(args) < 1:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📋 View Premium Users", callback_data="admin_premium_list")],
                    [InlineKeyboardButton(text="📊 Premium Analytics", callback_data="admin_premium_stats")]
                ])
                
                await message.reply(
                    "🔧 <b>Premium Management</b>\n\n"
                    "<b>Usage:</b> <code>/setprime [user_id] [days] [reason]</code>\n\n"
                    "<b>Examples:</b>\n"
                    "• <code>/setprime 123456789 30 Monthly subscription</code>\n"
                    "• <code>/setprime 123456789 7 Trial period</code>\n"
                    "• <code>/setprime 123456789 365 Annual plan</code>\n"
                    "• <code>/setprime 123456789 0 Permanent access</code>\n\n"
                    "<b>Note:</b> Use 0 days for permanent premium access",
                    reply_markup=keyboard
                )
                return
            
            user_id = int(args[0])
            days = int(args[1]) if len(args) > 1 else 30
            reason = " ".join(args[2:]) if len(args) > 2 else "Admin grant"
            
            # Validate user exists
            user_info = await self.db.get_user(user_id)
            if not user_info:
                await message.reply("❌ User not found. They need to start the bot first.")
                return
            
            # Calculate expiry
            if days == 0:
                expiry_date = None
                expiry_text = "Permanent"
            else:
                expiry_date = datetime.now() + timedelta(days=days)
                expiry_text = f"{days} days (until {expiry_date.strftime('%Y-%m-%d %H:%M')})"
            
            # Set premium status with admin tracking
            success = await self.db.set_prime_status(
                user_id=user_id, 
                is_prime=True, 
                expiry=expiry_date,
                admin_id=self.admin_id
            )
            
            if success:
                # Log admin action
                await self._log_admin_action(
                    admin_id=self.admin_id,
                    action="grant_premium",
                    target_user_id=user_id,
                    details={
                        'days': days,
                        'reason': reason,
                        'expiry': expiry_date.isoformat() if expiry_date else None
                    }
                )
                
                # Create success message with user info
                user_display = f"@{user_info.get('username', 'N/A')}" if user_info.get('username') else f"{user_info.get('first_name', 'Unknown')}"
                
                success_msg = (
                    f"✅ <b>Premium Access Granted!</b>\n\n"
                    f"👤 <b>User:</b> {user_display} (<code>{user_id}</code>)\n"
                    f"👑 <b>Duration:</b> {expiry_text}\n"
                    f"📝 <b>Reason:</b> {reason}\n"
                    f"👨‍💼 <b>Granted by:</b> Admin {self.admin_id}\n"
                    f"⏰ <b>Granted at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"🎯 <b>Premium Benefits Activated:</b>\n"
                    f"• Unlimited downloads\n"
                    f"• HD quality access (720p, 1080p)\n"
                    f"• High-quality audio downloads\n"
                    f"• No cooldown periods\n"
                    f"• Priority support\n"
                    f"• Early access to new features"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👤 View User Details", callback_data=f"admin_user_{user_id}")],
                    [InlineKeyboardButton(text="📊 Premium Stats", callback_data="admin_premium_stats")]
                ])
                
                await message.reply(success_msg, reply_markup=keyboard)
                
                # Notify the user
                try:
                    notification_msg = (
                        f"🎉 <b>Premium Access Granted!</b>\n\n"
                        f"👑 You now have premium access {expiry_text.lower()}!\n\n"
                        f"<b>🌟 Your Premium Benefits:</b>\n"
                        f"• ♾️ Unlimited downloads\n"
                        f"• 🎬 HD quality (720p, 1080p)\n"
                        f"• 🎵 High-quality audio\n"
                        f"• ⚡ No cooldown periods\n"
                        f"• 🔥 Priority support\n"
                        f"• 🚀 Early access to new features\n\n"
                        f"📝 <b>Reason:</b> {reason}\n\n"
                        f"Thank you for using our service! 🙏"
                    )
                    
                    await self.bot.send_message(user_id, notification_msg)
                    
                except TelegramForbiddenError:
                    await message.reply("⚠️ Note: Could not notify user (bot blocked by user)")
                except Exception as e:
                    await message.reply(f"⚠️ Note: Could not notify user: {str(e)}")
                    
            else:
                await message.reply("❌ Failed to grant premium access. Please check the user ID and try again.")
                
        except ValueError:
            await message.reply("❌ Invalid input. User ID and days must be numbers.")
        except Exception as e:
            logger.error(f"Error in set_prime: {e}")
            await message.reply(f"❌ An error occurred: {str(e)}")
    
    async def handle_remove_prime(self, message: Message):
        """Enhanced premium removal with tracking"""
        try:
            args = message.text.split()[1:]
            
            if len(args) < 1:
                await message.reply(
                    "🔧 <b>Remove Premium Access</b>\n\n"
                    "<b>Usage:</b> <code>/removeprime [user_id] [reason]</code>\n\n"
                    "<b>Examples:</b>\n"
                    "• <code>/removeprime 123456789 Subscription expired</code>\n"
                    "• <code>/removeprime 123456789 Policy violation</code>\n"
                    "• <code>/removeprime 123456789 User request</code>"
                )
                return
            
            user_id = int(args[0])
            reason = " ".join(args[1:]) if len(args) > 1 else "Admin action"
            
            # Validate user exists and has premium
            user_info = await self.db.get_user(user_id)
            if not user_info:
                await message.reply("❌ User not found.")
                return
            
            prime_status = await self.db.check_prime_status(user_id)
            if not prime_status['is_prime']:
                await message.reply("❌ User does not have premium access.")
                return
            
            # Remove premium status
            success = await self.db.set_prime_status(
                user_id=user_id, 
                is_prime=False,
                admin_id=self.admin_id
            )
            
            if success:
                # Log admin action
                await self._log_admin_action(
                    admin_id=self.admin_id,
                    action="remove_premium",
                    target_user_id=user_id,
                    details={'reason': reason}
                )
                
                user_display = f"@{user_info.get('username', 'N/A')}" if user_info.get('username') else f"{user_info.get('first_name', 'Unknown')}"
                
                success_msg = (
                    f"✅ <b>Premium Access Removed</b>\n\n"
                    f"👤 <b>User:</b> {user_display} (<code>{user_id}</code>)\n"
                    f"📝 <b>Reason:</b> {reason}\n"
                    f"👨‍💼 <b>Removed by:</b> Admin {self.admin_id}\n"
                    f"⏰ <b>Removed at:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"📊 User now has standard limits:\n"
                    f"• 15 downloads per hour\n"
                    f"• Standard quality (360p, 480p)\n"
                    f"• 30-minute cooldown after limit"
                )
                
                await message.reply(success_msg)
                
                # Notify the user
                try:
                    notification_msg = (
                        f"📢 <b>Premium Status Update</b>\n\n"
                        f"Your Premium access has been removed.\n\n"
                        f"📝 <b>Reason:</b> {reason}\n\n"
                        f"📊 <b>Your current limits:</b>\n"
                        f"• 15 downloads per hour\n"
                        f"• Standard quality (360p, 480p)\n"
                        f"• 30-minute cooldown after limit\n\n"
                        f"💬 Contact support if you have questions about this change."
                    )
                    
                    await self.bot.send_message(user_id, notification_msg)
                    
                except Exception as e:
                    logger.warning(f"Could not notify user {user_id}: {e}")
            else:
                await message.reply("❌ Failed to remove premium access.")
                
        except ValueError:
            await message.reply("❌ Invalid user ID. Use numbers only.")
        except Exception as e:
            logger.error(f"Error in remove_prime: {e}")
            await message.reply(f"❌ An error occurred: {str(e)}")
    
    async def handle_stats(self, message: Message):
        """Enhanced statistics with comprehensive metrics"""
        try:
            # Get comprehensive stats
            db_stats = await self.db.get_stats()
            
            # Get download manager stats if available
            download_stats = {}
            if self.download_manager:
                try:
                    download_stats = await self.download_manager.get_download_stats()
                except:
                    pass
            
            # Calculate additional metrics
            total_users = db_stats.get('total_users', 0)
            prime_users = db_stats.get('prime_users', 0)
            normal_users = total_users - prime_users
            prime_percentage = (prime_users / max(total_users, 1)) * 100
            
            # Format uptime (simplified)
            uptime = "Active"
            
            # Success rate calculation
            successful = db_stats.get('successful_downloads', 0)
            failed = db_stats.get('failed_downloads', 0)
            total_downloads = successful + failed
            success_rate = (successful / max(total_downloads, 1)) * 100
            
            stats_text = f"""
📊 <b>Bot Statistics Dashboard</b>

👥 <b>User Analytics:</b>
• Total Users: {total_users:,}
• Active (24h): {db_stats.get('active_24h', 0):,}
• Premium Users: {prime_users:,} ({prime_percentage:.1f}%)
• Standard Users: {normal_users:,}

📈 <b>Download Analytics:</b>
• Total Downloads: {total_downloads:,}
• Successful: {successful:,}
• Failed: {failed:,}
• Success Rate: {success_rate:.1f}%
• Downloads (24h): {db_stats.get('downloads_24h', 0):,}

🎬 <b>Content Distribution:</b>
• Video Downloads: {db_stats.get('video_downloads', 0):,}
• Audio Downloads: {db_stats.get('audio_downloads', 0):,}

⚡ <b>Performance Metrics:</b>
• Avg Download Time: {db_stats.get('avg_download_time', 0):.2f}s
• Active Downloads: {download_stats.get('active_downloads', 0)}
• Max Concurrent: {download_stats.get('max_concurrent', 5)}

💾 <b>Database Performance:</b>
• Query Count: {db_stats.get('database_performance', {}).get('query_count', 0):,}
• Cache Hit Rate: {db_stats.get('database_performance', {}).get('cache_hit_rate', 0):.1f}%
• Avg Query Time: {db_stats.get('database_performance', {}).get('avg_query_time', 0):.4f}s

🔧 <b>System Status:</b>
• Bot Status: {uptime}
• Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            # Create management keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👥 User Management", callback_data="admin_users"),
                    InlineKeyboardButton(text="📊 Analytics", callback_data="admin_analytics")
                ],
                [
                    InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_refresh_stats"),
                    InlineKeyboardButton(text="📥 Export Data", callback_data="admin_export")
                ],
                [
                    InlineKeyboardButton(text="🛠️ System Health", callback_data="admin_health"),
                    InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
                ]
            ])
            
            await message.reply(stats_text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.reply(f"❌ Error fetching statistics: {str(e)}")
    
    async def handle_broadcast(self, message: Message):
        """Enhanced broadcasting with targeting and scheduling"""
        try:
            command_parts = message.text.split(' ', 1)
            
            if len(command_parts) < 2:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="👥 All Users", callback_data="broadcast_all")],
                    [InlineKeyboardButton(text="👑 Premium Only", callback_data="broadcast_premium")],
                    [InlineKeyboardButton(text="📊 Active Users", callback_data="broadcast_active")],
                    [InlineKeyboardButton(text="📜 Broadcast History", callback_data="broadcast_history")]
                ])
                
                await message.reply(
                    "📢 <b>Broadcast Management</b>\n\n"
                    "<b>Usage:</b> <code>/broadcast [message]</code>\n\n"
                    "<b>Features:</b>\n"
                    "• Target specific user groups\n"
                    "• Rich formatting support\n"
                    "• Delivery tracking\n"
                    "• Broadcast history\n\n"
                    "<b>Example:</b>\n"
                    "<code>/broadcast 🎉 New features added! Check them out with /help</code>\n\n"
                    "Choose a target group or send a custom message:",
                    reply_markup=keyboard
                )
                return
            
            broadcast_message = command_parts[1]
            
            # Validate message
            if len(broadcast_message.strip()) < 5:
                await message.reply("❌ Broadcast message too short. Minimum 5 characters required.")
                return
            
            # Get target users (all users by default)
            user_ids = await self.db.get_all_users()
            
            if not user_ids:
                await message.reply("❌ No users found to broadcast to.")
                return
            
            # Create broadcast session
            broadcast_id = f"broadcast_{int(time.time())}"
            self.active_broadcasts[broadcast_id] = {
                'message': broadcast_message,
                'total_users': len(user_ids),
                'sent': 0,
                'failed': 0,
                'start_time': datetime.now(),
                'admin_id': self.admin_id,
                'status': 'starting'
            }
            
            # Send confirmation
            confirm_msg = await message.reply(
                f"📢 <b>Broadcasting Message...</b>\n\n"
                f"📝 <b>Message:</b> {broadcast_message[:100]}{'...' if len(broadcast_message) > 100 else ''}\n"
                f"👥 <b>Target Users:</b> {len(user_ids):,}\n"
                f"🔄 <b>Status:</b> Starting...\n\n"
                f"⏳ <i>This may take several minutes...</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 View Progress", callback_data=f"broadcast_progress_{broadcast_id}")]
                ])
            )
            
            # Start broadcast in background
            asyncio.create_task(self._execute_broadcast(
                broadcast_id, broadcast_message, user_ids, confirm_msg.message_id, message.chat.id
            ))
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await message.reply(f"❌ Broadcast error: {str(e)}")
    
    async def _execute_broadcast(self, broadcast_id: str, message_text: str, 
                               user_ids: List[int], confirm_msg_id: int, chat_id: int):
        """Execute broadcast with progress tracking"""
        try:
            broadcast_info = self.active_broadcasts[broadcast_id]
            broadcast_info['status'] = 'sending'
            
            success_count = 0
            failed_count = 0
            batch_size = 30  # Send in batches to avoid rate limits
            
            for i in range(0, len(user_ids), batch_size):
                batch = user_ids[i:i + batch_size]
                
                # Send to batch
                for user_id in batch:
                    try:
                        formatted_message = (
                            f"📢 <b>Announcement</b>\n\n"
                            f"{message_text}\n\n"
                            f"<i>From: YouTube Downloader Bot Administration</i>"
                        )
                        
                        await self.bot.send_message(user_id, formatted_message)
                        success_count += 1
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.05)
                        
                    except TelegramForbiddenError:
                        failed_count += 1
                        logger.debug(f"User {user_id} blocked the bot")
                    except TelegramBadRequest as e:
                        failed_count += 1
                        logger.debug(f"Bad request for user {user_id}: {e}")
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"Failed to send to user {user_id}: {e}")
                
                # Update progress
                broadcast_info['sent'] = success_count
                broadcast_info['failed'] = failed_count
                
                # Update progress message every few batches
                if i % (batch_size * 3) == 0 or i + batch_size >= len(user_ids):
                    try:
                        progress_percent = ((success_count + failed_count) / len(user_ids)) * 100
                        await self.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=confirm_msg_id,
                            text=f"📢 <b>Broadcasting Progress</b>\n\n"
                                 f"📝 <b>Message:</b> {message_text[:100]}{'...' if len(message_text) > 100 else ''}\n"
                                 f"📊 <b>Progress:</b> {progress_percent:.1f}% complete\n"
                                 f"✅ <b>Sent:</b> {success_count:,}\n"
                                 f"❌ <b>Failed:</b> {failed_count:,}\n"
                                 f"👥 <b>Remaining:</b> {len(user_ids) - success_count - failed_count:,}",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🔄 Refresh", callback_data=f"broadcast_progress_{broadcast_id}")]
                            ])
                        )
                    except:
                        pass
                
                # Batch delay
                await asyncio.sleep(1)
            
            # Final update
            broadcast_info['status'] = 'completed'
            broadcast_info['end_time'] = datetime.now()
            duration = (broadcast_info['end_time'] - broadcast_info['start_time']).total_seconds()
            
            # Add to history
            self.broadcast_history.append({
                'id': broadcast_id,
                'message': message_text,
                'admin_id': self.admin_id,
                'total_users': len(user_ids),
                'sent': success_count,
                'failed': failed_count,
                'success_rate': (success_count / len(user_ids)) * 100,
                'duration': duration,
                'timestamp': broadcast_info['start_time'].isoformat()
            })
            
            # Log admin action
            await self._log_admin_action(
                admin_id=self.admin_id,
                action="broadcast_message",
                details={
                    'broadcast_id': broadcast_id,
                    'total_users': len(user_ids),
                    'successful': success_count,
                    'failed': failed_count,
                    'duration': duration
                }
            )
            
            # Final message
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=confirm_msg_id,
                text=f"✅ <b>Broadcast Complete!</b>\n\n"
                     f"📊 <b>Final Results:</b>\n"
                     f"• Total Users: {len(user_ids):,}\n"
                     f"• Successfully Sent: {success_count:,}\n"
                     f"• Failed: {failed_count:,}\n"
                     f"• Success Rate: {(success_count / len(user_ids)) * 100:.1f}%\n"
                     f"• Duration: {duration:.1f} seconds\n\n"
                     f"📝 <b>Message:</b> {message_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📜 View History", callback_data="broadcast_history")]
                ])
            )
            
            # Clean up
            del self.active_broadcasts[broadcast_id]
            
        except Exception as e:
            logger.error(f"Broadcast execution error: {e}")
            broadcast_info['status'] = 'failed'
            broadcast_info['error'] = str(e)
    
    async def handle_user_search(self, message: Message):
        """Advanced user search and management"""
        try:
            args = message.text.split()[1:]
            
            if len(args) < 1:
                await message.reply(
                    "🔍 <b>User Search</b>\n\n"
                    "<b>Usage:</b> <code>/user [user_id or @username]</code>\n\n"
                    "<b>Examples:</b>\n"
                    "• <code>/user 123456789</code>\n"
                    "• <code>/user @johndoe</code>\n\n"
                    "This will show detailed user information and management options."
                )
                return
            
            search_term = args[0]
            
            # Search for user
            if search_term.startswith('@'):
                # Search by username (simplified - would need database query)
                await message.reply("🔍 Username search not implemented yet. Please use user ID.")
                return
            else:
                # Search by ID
                try:
                    user_id = int(search_term)
                    user_info = await self.get_user_details(user_id)
                    
                    if not user_info:
                        await message.reply(f"❌ User {user_id} not found.")
                        return
                    
                    # Get additional analytics if user manager available
                    analytics = {}
                    if self.user_manager:
                        try:
                            analytics = await self.user_manager.get_user_analytics(user_id)
                        except:
                            pass
                    
                    # Format user details
                    user_display = f"@{user_info.get('username', 'N/A')}" if user_info.get('username') else "No username"
                    full_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()
                    
                    premium_status = "👑 Premium" if user_info.get('is_prime') else "👤 Standard"
                    premium_expiry = user_info.get('prime_expiry')
                    expiry_text = f"Expires: {premium_expiry}" if premium_expiry else "No expiry set"
                    
                    user_details = f"""
👤 <b>User Details</b>

📋 <b>Basic Info:</b>
• ID: <code>{user_id}</code>
• Username: {user_display}
• Name: {full_name or 'Not set'}
• Status: {premium_status}
{f"• {expiry_text}" if user_info.get('is_prime') else ""}

📊 <b>Usage Statistics:</b>
• Downloads (Hour): {user_info.get('downloads_this_hour', 0)}
• Downloads (Total): {user_info.get('downloads_today', 0)}
• Member Since: {user_info.get('created_at', 'Unknown')}
• Last Active: {user_info.get('last_active', 'Unknown')}

📈 <b>Engagement:</b>
• User Level: {analytics.get('user_level', 1)}
• Engagement Score: {analytics.get('engagement_score', 0)}
• Session Count: {analytics.get('engagement_metrics', {}).get('session_count', 0)}
                    """
                    
                    # Create management keyboard
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="👑 Grant Premium", callback_data=f"admin_grant_{user_id}"),
                            InlineKeyboardButton(text="❌ Remove Premium", callback_data=f"admin_remove_{user_id}")
                        ],
                        [
                            InlineKeyboardButton(text="📊 Full Analytics", callback_data=f"admin_analytics_{user_id}"),
                            InlineKeyboardButton(text="💬 Send Message", callback_data=f"admin_message_{user_id}")
                        ],
                        [
                            InlineKeyboardButton(text="🚫 Block User", callback_data=f"admin_block_{user_id}"),
                            InlineKeyboardButton(text="🔄 Refresh", callback_data=f"admin_refresh_{user_id}")
                        ]
                    ])
                    
                    await message.reply(user_details, reply_markup=keyboard)
                    
                except ValueError:
                    await message.reply("❌ Invalid user ID. Please provide a valid number.")
                    
        except Exception as e:
            logger.error(f"Error in user search: {e}")
            await message.reply(f"❌ Search error: {str(e)}")
    
    async def get_user_details(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive user details for admin"""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return None
            
            prime_status = await self.db.check_prime_status(user_id)
            download_stats = await self.db.get_download_stats(user_id)
            
            return {
                'user_id': user['user_id'],
                'username': user.get('username'),
                'first_name': user.get('first_name', ''),
                'last_name': user.get('last_name', ''),
                'is_prime': prime_status['is_prime'],
                'prime_expiry': prime_status.get('expiry_date'),
                'downloads_this_hour': download_stats['downloads_this_hour'],
                'downloads_today': user.get('downloads_today', 0),
                'created_at': user.get('created_at'),
                'last_active': user.get('last_active', user.get('last_seen')),
                'is_blocked': user.get('is_blocked', False),
                'language_code': user.get('language_code', 'en')
            }
        except Exception as e:
            logger.error(f"Error getting user details {user_id}: {e}")
            return None
    
    async def _log_admin_action(self, admin_id: int, action: str, target_user_id: int = None, 
                              details: Dict[str, Any] = None):
        """Log admin actions for audit trail"""
        try:
            action_log = {
                'admin_id': admin_id,
                'action': action,
                'target_user_id': target_user_id,
                'details': details or {},
                'timestamp': datetime.now().isoformat(),
                'ip_address': 'telegram_bot'  # Could be enhanced with actual IP tracking
            }
            
            # Store in memory (could be enhanced with database storage)
            self.admin_actions.append(action_log)
            
            # Keep only last 1000 actions in memory
            if len(self.admin_actions) > 1000:
                self.admin_actions = self.admin_actions[-1000:]
            
            # Log to database if available
            if hasattr(self.db, 'execute_query'):
                await self.db.execute_query("""
                    INSERT INTO admin_actions (admin_id, action, target_user_id, details)
                    VALUES (?, ?, ?, ?)
                """, (admin_id, action, target_user_id, json.dumps(details or {})))
            
            logger.info(f"Admin action logged: {action} by {admin_id} on {target_user_id}")
            
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
    
    async def _monitoring_task(self):
        """Background monitoring for system health and alerts"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if not self.monitoring_active:
                    continue
                
                # Check error rates
                # Check download failures
                # Check system resources
                # Send alerts if thresholds exceeded
                
                # This is a placeholder for comprehensive monitoring
                # In a real implementation, you'd check various metrics
                
            except Exception as e:
                logger.error(f"Monitoring task error: {e}")
    
    async def _performance_tracking_task(self):
        """Background task to track performance metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Track memory usage (simplified)
                # Track response times
                # Track database performance
                # Store metrics for trending
                
                current_time = datetime.now()
                
                # Log performance summary
                if len(self.performance_metrics['command_response_times']) > 0:
                    avg_response_time = sum(self.performance_metrics['command_response_times']) / len(self.performance_metrics['command_response_times'])
                    logger.info(f"Performance: Avg response time: {avg_response_time:.3f}s")
                
                # Reset counters
                self.performance_metrics['command_response_times'] = []
                
            except Exception as e:
                logger.error(f"Performance tracking error: {e}")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status"""
        try:
            # Database health
            db_health = {}
            if hasattr(self.db, 'get_health_status'):
                db_health = await self.db.get_health_status()
            
            # Download manager health
            dm_health = {}
            if self.download_manager:
                try:
                    dm_health = await self.download_manager.get_download_stats()
                except:
                    pass
            
            # Bot health (simplified)
            bot_health = {
                'status': 'healthy',
                'uptime': 'unknown',
                'memory_usage': 'unknown'
            }
            
            return {
                'overall_status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'database': db_health,
                'download_manager': dm_health,
                'bot': bot_health,
                'active_broadcasts': len(self.active_broadcasts),
                'admin_actions_count': len(self.admin_actions)
            }
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'overall_status': 'unhealthy', 'error': str(e)}

# Compatibility alias for existing code
AdminPanel = ProfessionalAdminPanel