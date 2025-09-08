"""
Simple Admin Panel for Telegram YouTube Downloader Bot
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)

class ProfessionalAdminPanel:
    def __init__(self, database, bot: Bot, admin_id: int, analytics_enabled: bool = True):
        """Initialize admin panel"""
        self.db = database
        self.bot = bot
        self.admin_id = admin_id
        self.analytics_enabled = analytics_enabled
    
    async def handle_set_prime(self, message: Message):
        """Handle set prime command"""
        try:
            parts = message.text.split()
            if len(parts) < 3:
                await message.reply("Usage: /setprime [user_id] [days] [reason]")
                return
            
            user_id = int(parts[1])
            days = int(parts[2])
            reason = " ".join(parts[3:]) if len(parts) > 3 else "Admin grant"
            
            # Calculate expiry date
            expiry_date = datetime.now() + timedelta(days=days)
            expiry_str = expiry_date.isoformat()
            
            # Set prime status
            await self.db.set_prime_status(user_id, True, expiry_str)
            
            # Send confirmation
            await message.reply(f"✅ Premium access granted to user {user_id} for {days} days.\nExpiry: {expiry_date.strftime('%Y-%m-%d %H:%M')}\nReason: {reason}")
            
            # Notify user
            try:
                await self.bot.send_message(
                    user_id,
                    f"🎉 <b>Premium Access Granted!</b>\n\n👑 You now have premium access for {days} days!\n\n<b>Premium Benefits:</b>\n• Unlimited downloads\n• HD quality (720p, 1080p)\n• High-quality audio\n• No cooldowns\n\n📅 Expires: {expiry_date.strftime('%Y-%m-%d %H:%M')}"
                )
            except:
                pass  # User might have blocked bot
                
        except ValueError:
            await message.reply("❌ Invalid user ID or days value. Please use numbers only.")
        except Exception as e:
            logger.error(f"Error setting prime: {e}")
            await message.reply(f"❌ Error setting premium access: {e}")
    
    async def handle_remove_prime(self, message: Message):
        """Handle remove prime command"""
        try:
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply("Usage: /removeprime [user_id] [reason]")
                return
            
            user_id = int(parts[1])
            reason = " ".join(parts[2:]) if len(parts) > 2 else "Admin removal"
            
            # Remove prime status
            await self.db.set_prime_status(user_id, False, None)
            
            # Send confirmation
            await message.reply(f"✅ Premium access removed from user {user_id}.\nReason: {reason}")
            
            # Notify user
            try:
                await self.bot.send_message(
                    user_id,
                    f"📢 <b>Premium Access Update</b>\n\nYour premium access has been removed.\n\nYou can still use the bot with standard features:\n• 15 downloads per hour\n• 360p and 480p quality\n\nContact @chhinhlong for premium upgrade."
                )
            except:
                pass  # User might have blocked bot
                
        except ValueError:
            await message.reply("❌ Invalid user ID. Please use numbers only.")
        except Exception as e:
            logger.error(f"Error removing prime: {e}")
            await message.reply(f"❌ Error removing premium access: {e}")
    
    async def handle_stats(self, message: Message):
        """Handle stats command"""
        try:
            stats = await self.db.get_stats()
            
            stats_text = f"""
📊 <b>Bot Statistics</b>

👥 <b>Users:</b>
• Total Users: {stats['total_users']}
• Premium Users: {stats['prime_users']}
• Active (24h): {stats['active_24h']}

📁 <b>Downloads:</b>
• Total Downloads: {stats['total_downloads']}
• Successful: {stats['successful_downloads']}
• Success Rate: {stats['success_rate']}%

📅 <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await message.reply(stats_text)
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            await message.reply(f"❌ Error getting statistics: {e}")
    
    async def handle_broadcast(self, message: Message):
        """Handle broadcast command"""
        try:
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                await message.reply("Usage: /broadcast [message]")
                return
            
            broadcast_message = parts[1]
            users = await self.db.get_all_users()
            
            if not users:
                await message.reply("❌ No users found to broadcast to.")
                return
            
            # Send initial status
            status_msg = await message.reply(f"📢 Starting broadcast to {len(users)} users...")
            
            sent_count = 0
            failed_count = 0
            
            for user_id in users:
                try:
                    await self.bot.send_message(user_id, broadcast_message)
                    sent_count += 1
                    
                    # Update status every 10 messages
                    if sent_count % 10 == 0:
                        await status_msg.edit_text(f"📢 Broadcast progress: {sent_count}/{len(users)} sent...")
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
            
            # Final status
            await status_msg.edit_text(
                f"✅ <b>Broadcast Complete!</b>\n\n"
                f"📊 <b>Results:</b>\n"
                f"• Sent: {sent_count}\n"
                f"• Failed: {failed_count}\n"
                f"• Total: {len(users)}"
            )
            
        except Exception as e:
            logger.error(f"Error broadcasting: {e}")
            await message.reply(f"❌ Error broadcasting message: {e}")