"""
Professional Download Manager for Telegram YouTube Downloader Bot
Features: Concurrent processing, advanced quality optimization, performance monitoring
"""

import os
import asyncio
import logging
import tempfile
import time
import json
import hashlib
import shutil
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import yt_dlp
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

@dataclass
class DownloadResult:
    """Enhanced download result with comprehensive metadata"""
    success: bool
    type: str  # 'video' or 'audio'
    file: Optional[BufferedInputFile] = None
    quality: str = ""
    title: str = ""
    duration: int = 0
    file_size: int = 0
    download_time: float = 0.0
    video_id: str = ""
    uploader: str = ""
    view_count: int = 0
    error: Optional[str] = None
    format_info: Dict[str, Any] = None

class AdvancedDownloadManager:
    def __init__(self, max_concurrent: int = 5, temp_dir: str = "temp", 
                 cleanup_interval: int = 3600, max_file_size: int = 50 * 1024 * 1024,
                 max_duration: int = 3600):
        """Initialize professional download manager"""
        self.max_concurrent = max_concurrent
        self.temp_dir = temp_dir
        self.cleanup_interval = cleanup_interval
        self.max_file_size = max_file_size
        self.max_duration = max_duration
        
        # Create directories
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs("cookies", exist_ok=True)
        
        # Concurrent download management
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
        # Download tracking
        self.active_downloads: Dict[str, Dict[str, Any]] = {}
        self.download_stats = {
            'total_downloads': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'total_download_time': 0.0,
            'total_file_size': 0
        }
        
        # Quality mappings with optimized formats
        self.quality_formats = {
            'quality_360p': 'best[height<=360][ext=mp4]/best[height<=360]',
            'quality_480p': 'best[height<=480][ext=mp4]/best[height<=480]',
            'quality_720p': 'best[height<=720][ext=mp4]/best[height<=720]',
            'quality_1080p': 'best[height<=1080][ext=mp4]/best[height<=1080]',
            'audio_standard': 'bestaudio[abr<=128][ext=m4a]/bestaudio[ext=m4a]/bestaudio',
            'audio_hq': 'bestaudio[abr>=192][ext=m4a]/bestaudio[ext=m4a]/bestaudio'
        }
        
        # Enhanced error handling
        self.retry_attempts = 3
        self.retry_delay = 5
        self.timeout = 300  # 5 minutes timeout
        
        # Start background tasks
        asyncio.create_task(self._cleanup_task())
        asyncio.create_task(self._stats_monitor_task())
    
    def get_ydl_options(self, quality: str, output_path: str, user_id: int) -> Dict[str, Any]:
        """Get optimized yt-dlp options with advanced configuration"""
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
            'embed_subs': False,
            'concurrent_fragments': 3,
            'http_chunk_size': 10485760,  # 10MB chunks
            'buffer_size': 1024 * 1024,   # 1MB buffer
        }
        
        # Cookies support with multiple sources
        cookie_files = [
            'cookies/cookies.txt',
            'cookies/youtube.txt',
            f'cookies/user_{user_id}.txt'
        ]
        
        for cookie_file in cookie_files:
            if os.path.exists(cookie_file):
                base_opts['cookiefile'] = cookie_file
                break
        
        # Audio-specific options
        if quality.startswith('audio_'):
            base_opts.update({
                'audioformat': 'mp3',
                'audioquality': '0' if quality == 'audio_hq' else '5',
                'extract_flat': False,
                'writethumbnail': False,
                'writeinfojson': False
            })
        
        # Video-specific optimizations
        else:
            base_opts.update({
                'merge_output_format': 'mp4',
                'writesubtitles': False,
                'writeautomaticsub': False
            })
        
        return base_opts
    
    async def download_content(self, url: str, quality: str, user_id: int) -> DownloadResult:
        """Download content with enhanced error handling and monitoring"""
        download_id = hashlib.md5(f"{url}{quality}{user_id}{time.time()}".encode()).hexdigest()[:12]
        start_time = time.time()
        
        self.download_stats['total_downloads'] += 1
        
        # Track active download
        self.active_downloads[download_id] = {
            'user_id': user_id,
            'url': url,
            'quality': quality,
            'start_time': start_time,
            'status': 'starting'
        }
        
        try:
            # Use semaphore for concurrency control
            async with self.semaphore:
                self.active_downloads[download_id]['status'] = 'downloading'
                
                # Validate URL first
                if not await self.is_valid_youtube_url(url):
                    raise ValueError("Invalid YouTube URL")
                
                # Get video info for validation
                info_result = await self.get_video_info(url)
                if not info_result['success']:
                    raise ValueError(f"Cannot get video info: {info_result['error']}")
                
                # Check duration limit
                duration = info_result.get('duration', 0)
                if duration > self.max_duration:
                    raise ValueError(f"Video too long: {duration}s (max: {self.max_duration}s)")
                
                # Determine download type
                download_type = 'audio' if quality.startswith('audio_') else 'video'
                
                # Perform download
                if download_type == 'video':
                    result = await self._download_video_enhanced(url, quality, user_id, download_id, info_result)
                else:
                    result = await self._download_audio_enhanced(url, quality, user_id, download_id, info_result)
                
                # Update statistics
                download_time = time.time() - start_time
                result.download_time = download_time
                self.download_stats['total_download_time'] += download_time
                
                if result.success:
                    self.download_stats['successful_downloads'] += 1
                    self.download_stats['total_file_size'] += result.file_size
                else:
                    self.download_stats['failed_downloads'] += 1
                
                self.active_downloads[download_id]['status'] = 'completed'
                return result
                
        except Exception as e:
            logger.error(f"Download error for {download_id}: {e}")
            self.download_stats['failed_downloads'] += 1
            
            error_result = DownloadResult(
                success=False,
                type=download_type if 'download_type' in locals() else 'unknown',
                error=str(e),
                download_time=time.time() - start_time
            )
            
            self.active_downloads[download_id]['status'] = 'failed'
            return error_result
        
        finally:
            # Clean up tracking
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
    
    async def _download_video_enhanced(self, url: str, quality: str, user_id: int, 
                                     download_id: str, video_info: Dict[str, Any]) -> DownloadResult:
        """Enhanced video download with advanced processing"""
        temp_file = None
        try:
            # Create unique temp file
            temp_file = os.path.join(self.temp_dir, f"video_{download_id}_{user_id}.%(ext)s")
            
            # Configure yt-dlp options
            opts = self.get_ydl_options(quality, temp_file, user_id)
            
            # Perform download in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._download_with_ydl,
                url, opts
            )
            
            if not result['success']:
                return DownloadResult(
                    success=False,
                    type='video',
                    error=result['error']
                )
            
            info = result['info']
            filename = result['filename']
            
            # Validate file exists and size
            if not os.path.exists(filename):
                return DownloadResult(
                    success=False,
                    type='video',
                    error='Downloaded file not found'
                )
            
            file_size = os.path.getsize(filename)
            if file_size > self.max_file_size:
                os.remove(filename)
                return DownloadResult(
                    success=False,
                    type='video',
                    error=f'File too large: {file_size} bytes (max: {self.max_file_size})'
                )
            
            # Read file content
            with open(filename, 'rb') as f:
                file_content = f.read()
            
            # Clean up temp file
            os.remove(filename)
            
            # Extract quality info
            quality_display = quality.replace('quality_', '').upper()
            title = info.get('title', 'Unknown Video')
            
            # Create BufferedInputFile
            safe_filename = self._sanitize_filename(f"{title}.mp4")
            file_obj = BufferedInputFile(file_content, filename=safe_filename)
            
            return DownloadResult(
                success=True,
                type='video',
                file=file_obj,
                quality=quality_display,
                title=title,
                duration=info.get('duration', 0),
                file_size=file_size,
                video_id=info.get('id', ''),
                uploader=info.get('uploader', ''),
                view_count=info.get('view_count', 0),
                format_info={
                    'format_id': info.get('format_id'),
                    'ext': info.get('ext'),
                    'resolution': f"{info.get('width', 0)}x{info.get('height', 0)}"
                }
            )
            
        except Exception as e:
            logger.error(f"Video download error: {e}")
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return DownloadResult(
                success=False,
                type='video',
                error=f'Video download failed: {str(e)}'
            )
    
    async def _download_audio_enhanced(self, url: str, quality: str, user_id: int, 
                                     download_id: str, video_info: Dict[str, Any]) -> DownloadResult:
        """Enhanced audio download with advanced processing"""
        temp_file = None
        try:
            # Create unique temp file
            temp_file = os.path.join(self.temp_dir, f"audio_{download_id}_{user_id}.%(ext)s")
            
            # Configure yt-dlp options
            opts = self.get_ydl_options(quality, temp_file, user_id)
            
            # Perform download in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._download_with_ydl,
                url, opts
            )
            
            if not result['success']:
                return DownloadResult(
                    success=False,
                    type='audio',
                    error=result['error']
                )
            
            info = result['info']
            filename = result['filename']
            
            # Find actual downloaded file (yt-dlp may change extension)
            base_filename = filename.rsplit('.', 1)[0]
            possible_extensions = ['.mp3', '.m4a', '.webm', '.ogg']
            actual_filename = None
            
            for ext in possible_extensions:
                test_filename = base_filename + ext
                if os.path.exists(test_filename):
                    actual_filename = test_filename
                    break
            
            if not actual_filename:
                return DownloadResult(
                    success=False,
                    type='audio',
                    error='Audio file not found after download'
                )
            
            # Validate file size
            file_size = os.path.getsize(actual_filename)
            if file_size > self.max_file_size:
                os.remove(actual_filename)
                return DownloadResult(
                    success=False,
                    type='audio',
                    error=f'File too large: {file_size} bytes (max: {self.max_file_size})'
                )
            
            # Read file content
            with open(actual_filename, 'rb') as f:
                file_content = f.read()
            
            # Clean up temp file
            os.remove(actual_filename)
            
            # Extract quality info
            quality_display = "High Quality" if quality == 'audio_hq' else "Standard Quality"
            title = info.get('title', 'Unknown Audio')
            
            # Create BufferedInputFile with proper extension
            extension = '.mp3'  # Default to mp3
            safe_filename = self._sanitize_filename(f"{title}{extension}")
            file_obj = BufferedInputFile(file_content, filename=safe_filename)
            
            return DownloadResult(
                success=True,
                type='audio',
                file=file_obj,
                quality=quality_display,
                title=title,
                duration=info.get('duration', 0),
                file_size=file_size,
                video_id=info.get('id', ''),
                uploader=info.get('uploader', ''),
                view_count=info.get('view_count', 0),
                format_info={
                    'format_id': info.get('format_id'),
                    'ext': actual_filename.split('.')[-1],
                    'abr': info.get('abr'),
                    'acodec': info.get('acodec')
                }
            )
            
        except Exception as e:
            logger.error(f"Audio download error: {e}")
            if temp_file and os.path.exists(temp_file):
                try:
                    # Try to clean up any created files
                    base_filename = temp_file.rsplit('.', 1)[0]
                    for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                        test_file = base_filename + ext
                        if os.path.exists(test_file):
                            os.remove(test_file)
                except:
                    pass
            
            return DownloadResult(
                success=False,
                type='audio',
                error=f'Audio download failed: {str(e)}'
            )
    
    def _download_with_ydl(self, url: str, opts: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous download function for thread pool execution"""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                return {
                    'success': True,
                    'info': info,
                    'filename': filename
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get comprehensive video information"""
        try:
            opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }
            
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                self.executor,
                self._extract_info_sync,
                url, opts
            )
            
            if not info:
                return {
                    'success': False,
                    'error': 'Could not extract video information'
                }
            
            # Format duration
            duration = info.get('duration', 0)
            duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            
            # Format upload date
            upload_date = info.get('upload_date', '')
            if upload_date:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(upload_date, '%Y%m%d')
                    upload_date = date_obj.strftime('%Y-%m-%d')
                except:
                    pass
            
            # Get available formats
            formats = info.get('formats', [])
            available_qualities = set()
            for fmt in formats:
                height = fmt.get('height')
                if height:
                    if height <= 360:
                        available_qualities.add('360p')
                    elif height <= 480:
                        available_qualities.add('480p')
                    elif height <= 720:
                        available_qualities.add('720p')
                    elif height <= 1080:
                        available_qualities.add('1080p')
            
            return {
                'success': True,
                'title': info.get('title', 'Unknown'),
                'duration': duration,
                'duration_str': duration_str,
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'upload_date': upload_date,
                'description': (info.get('description', '')[:200] + '...') if info.get('description') else '',
                'thumbnail': info.get('thumbnail', ''),
                'video_id': info.get('id', ''),
                'available_qualities': sorted(list(available_qualities)),
                'webpage_url': info.get('webpage_url', url)
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {
                'success': False,
                'error': f'Could not get video info: {str(e)}'
            }
    
    def _extract_info_sync(self, url: str, opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Synchronous info extraction for thread pool"""
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Sync info extraction error: {e}")
            return None
    
    async def is_valid_youtube_url(self, url: str) -> bool:
        """Enhanced YouTube URL validation"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(url.lower())
            
            # Valid YouTube domains
            valid_domains = [
                'youtube.com', 'www.youtube.com', 'm.youtube.com',
                'youtu.be', 'music.youtube.com'
            ]
            
            if parsed.netloc not in valid_domains:
                return False
            
            # Check for valid video ID patterns
            if parsed.netloc == 'youtu.be':
                # youtu.be/VIDEO_ID format
                video_id = parsed.path.lstrip('/')
                return len(video_id) == 11
            
            else:
                # youtube.com/watch?v=VIDEO_ID format
                if '/watch' in parsed.path or '/shorts' in parsed.path:
                    query_params = parse_qs(parsed.query)
                    video_id = query_params.get('v', [None])[0]
                    return video_id and len(video_id) == 11
                
                # Playlist or channel URLs are not supported
                return False
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe use"""
        import re
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Limit length
        if len(filename) > 100:
            name, ext = os.path.splitext(filename)
            filename = name[:95] + ext
        return filename
    
    async def _cleanup_task(self):
        """Background task to clean up temporary files"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                cleaned_count = 0
                
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(file_path):
                        # Remove files older than cleanup interval
                        file_age = os.path.getmtime(file_path)
                        if current_time - file_age > self.cleanup_interval:
                            try:
                                os.remove(file_path)
                                cleaned_count += 1
                            except OSError:
                                pass
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} temporary files")
                
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    async def _stats_monitor_task(self):
        """Background task to monitor download statistics"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                if self.download_stats['total_downloads'] > 0:
                    success_rate = (self.download_stats['successful_downloads'] / 
                                  self.download_stats['total_downloads']) * 100
                    avg_download_time = (self.download_stats['total_download_time'] / 
                                       self.download_stats['successful_downloads']) if self.download_stats['successful_downloads'] > 0 else 0
                    avg_file_size = (self.download_stats['total_file_size'] / 
                                   self.download_stats['successful_downloads']) if self.download_stats['successful_downloads'] > 0 else 0
                    
                    logger.info(f"Download Stats: {self.download_stats['total_downloads']} total, "
                              f"{success_rate:.1f}% success rate, "
                              f"avg time: {avg_download_time:.2f}s, "
                              f"avg size: {avg_file_size / 1024 / 1024:.1f}MB, "
                              f"active: {len(self.active_downloads)}")
                
            except Exception as e:
                logger.error(f"Stats monitor error: {e}")
    
    async def get_download_stats(self) -> Dict[str, Any]:
        """Get comprehensive download statistics"""
        try:
            success_rate = 0
            avg_download_time = 0
            avg_file_size = 0
            
            if self.download_stats['total_downloads'] > 0:
                success_rate = (self.download_stats['successful_downloads'] / 
                              self.download_stats['total_downloads']) * 100
            
            if self.download_stats['successful_downloads'] > 0:
                avg_download_time = (self.download_stats['total_download_time'] / 
                                   self.download_stats['successful_downloads'])
                avg_file_size = (self.download_stats['total_file_size'] / 
                               self.download_stats['successful_downloads'])
            
            return {
                'total_downloads': self.download_stats['total_downloads'],
                'successful_downloads': self.download_stats['successful_downloads'],
                'failed_downloads': self.download_stats['failed_downloads'],
                'success_rate': round(success_rate, 2),
                'avg_download_time': round(avg_download_time, 2),
                'avg_file_size_mb': round(avg_file_size / 1024 / 1024, 2),
                'active_downloads': len(self.active_downloads),
                'max_concurrent': self.max_concurrent,
                'total_download_time': round(self.download_stats['total_download_time'], 2),
                'total_file_size_mb': round(self.download_stats['total_file_size'] / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.error(f"Error getting download stats: {e}")
            return {}
    
    async def get_active_downloads(self) -> List[Dict[str, Any]]:
        """Get information about currently active downloads"""
        return list(self.active_downloads.values())
    
    def cleanup_temp_files(self):
        """Manual cleanup of temporary files (legacy compatibility)"""
        try:
            asyncio.create_task(self._cleanup_temp_files_sync())
        except Exception as e:
            logger.error(f"Manual cleanup error: {e}")
    
    async def _cleanup_temp_files_sync(self):
        """Synchronous cleanup helper"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                if os.path.isfile(file_path):
                    file_age = os.path.getmtime(file_path)
                    if current_time - file_age > 3600:  # 1 hour
                        os.remove(file_path)
        except Exception as e:
            logger.error(f"Sync cleanup error: {e}")

# Compatibility alias for existing code
DownloadManager = AdvancedDownloadManager