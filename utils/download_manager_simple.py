"""
Simple Download Manager for Telegram YouTube Downloader Bot
"""

import os
import asyncio
import logging
import tempfile
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
import yt_dlp
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

@dataclass
class DownloadResult:
    """Download result with metadata"""
    success: bool
    type: str  # 'video' or 'audio'
    file: Optional[BufferedInputFile] = None
    quality: str = ""
    title: str = ""
    duration: int = 0
    file_size: int = 0
    error: Optional[str] = None

class AdvancedDownloadManager:
    def __init__(self, max_concurrent: int = 5, temp_dir: str = "temp", cleanup_interval: int = 3600):
        """Initialize download manager"""
        self.max_concurrent = max_concurrent
        self.temp_dir = temp_dir
        self.cleanup_interval = cleanup_interval
        
        # Create directories
        os.makedirs(temp_dir, exist_ok=True)
        
        # Concurrent download management
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Quality mappings
        self.quality_formats = {
            'quality_360p': 'best[height<=360][ext=mp4]',
            'quality_480p': 'best[height<=480][ext=mp4]',
            'quality_720p': 'best[height<=720][ext=mp4]',
            'quality_1080p': 'best[height<=1080][ext=mp4]',
            'audio_standard': 'bestaudio[ext=m4a]/bestaudio',
            'audio_hq': 'bestaudio[abr>=128][ext=m4a]/bestaudio'
        }
        
        # Error handling
        self.retry_attempts = 3
        self.retry_delay = 5
    
    def get_ydl_options(self, quality: str, output_path: str) -> Dict[str, Any]:
        """Get optimized yt-dlp options"""
        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractaudio': quality.startswith('audio_'),
            'format': self.quality_formats.get(quality, 'best'),
            'outtmpl': output_path,
            'writeinfojson': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'retries': self.retry_attempts,
            'fragment_retries': self.retry_attempts,
            'socket_timeout': 30,
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'embed_subs': False
        }
        
        # Cookies support
        cookies_path = 'cookies/cookies.txt'
        if os.path.exists(cookies_path):
            base_opts['cookiefile'] = cookies_path
        
        # Audio-specific options
        if quality.startswith('audio_'):
            base_opts.update({
                'audioformat': 'mp3',
                'audioquality': '0' if quality == 'audio_hq' else '5',
                'embed_thumbnail': False
            })
        
        return base_opts
    
    async def download_content(self, url: str, quality: str, user_id: int) -> DownloadResult:
        """Download content with progress tracking"""
        try:
            # Use semaphore for concurrent download limiting
            async with self.semaphore:
                return await self._perform_download(url, quality, user_id)
        except Exception as e:
            logger.error(f"Download error for user {user_id}: {e}")
            return DownloadResult(
                success=False,
                type='unknown',
                error=str(e)
            )
    
    async def _perform_download(self, url: str, quality: str, user_id: int) -> DownloadResult:
        """Perform the actual download"""
        timestamp = int(time.time())
        
        if quality.startswith('audio_'):
            filename = f"audio_{user_id}_{timestamp}.%(ext)s"
            download_type = 'audio'
        else:
            filename = f"video_{user_id}_{timestamp}.%(ext)s"
            download_type = 'video'
        
        output_path = os.path.join(self.temp_dir, filename)
        
        # Get yt-dlp options
        ydl_opts = self.get_ydl_options(quality, output_path)
        
        try:
            # Download using yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                
                # Find the downloaded file
                downloaded_file = ydl.prepare_filename(info)
                
                # Handle audio extraction case
                if quality.startswith('audio_'):
                    # Check for various audio formats
                    for ext in ['.mp3', '.m4a', '.webm', '.opus']:
                        audio_file = os.path.splitext(downloaded_file)[0] + ext
                        if os.path.exists(audio_file):
                            downloaded_file = audio_file
                            break
                
                if not os.path.exists(downloaded_file):
                    return DownloadResult(
                        success=False,
                        type=download_type,
                        error="Downloaded file not found"
                    )
                
                # Check file size
                file_size = os.path.getsize(downloaded_file)
                if file_size > 50 * 1024 * 1024:  # 50MB limit
                    os.remove(downloaded_file)
                    return DownloadResult(
                        success=False,
                        type=download_type,
                        error="File too large (max 50MB)"
                    )
                
                # Read file and create BufferedInputFile
                with open(downloaded_file, 'rb') as f:
                    file_data = f.read()
                
                # Clean up downloaded file
                try:
                    os.remove(downloaded_file)
                except:
                    pass
                
                # Create appropriate input file
                title = info.get('title', 'download')
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
                
                if download_type == 'video':
                    filename = f"{safe_title}.mp4"
                else:
                    filename = f"{safe_title}.mp3"
                
                buffered_file = BufferedInputFile(file_data, filename)
                
                return DownloadResult(
                    success=True,
                    type=download_type,
                    file=buffered_file,
                    quality=quality,
                    title=info.get('title', 'Unknown'),
                    duration=info.get('duration', 0),
                    file_size=file_size
                )
                
        except Exception as e:
            logger.error(f"Download error: {e}")
            return DownloadResult(
                success=False,
                type=download_type,
                error=str(e)
            )