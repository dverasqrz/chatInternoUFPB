"""
Centralized media service for handling all media operations.
"""

import logging
import secrets
from pathlib import Path
from typing import BinaryIO, Optional, Tuple

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.exceptions import MediaProcessingError, ValidationError
from app.core.security import generate_secure_filename

logger = logging.getLogger(__name__)


class MediaService:
    """
    Centralized service for handling media uploads, processing, and management.
    
    This service provides a unified interface for all media operations
    with proper validation, security, and error handling.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.storage_path = self.settings.media_storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Define allowed MIME types and extensions
        self.allowed_mime_types = {
            'image': ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/bmp'],
            'audio': ['audio/ogg', 'audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/webm'],
            'video': ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo'],
            'document': [
                'application/pdf', 'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'text/plain', 'text/csv', 'application/zip', 'application/x-rar-compressed'
            ]
        }
        
        self.allowed_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'],
            'audio': ['.ogg', '.mp3', '.wav', '.m4a', '.webm'],
            'video': ['.mp4', '.webm', '.mov', '.avi'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.zip', '.rar']
        }
    
    def validate_media_file(self, file: UploadFile) -> Tuple[str, str]:
        """
        Validate uploaded media file.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Tuple of (media_type, extension)
            
        Raises:
            ValidationError: If file is invalid
        """
        if not file.filename:
            raise ValidationError("No filename provided")
        
        # Get MIME type and extension
        mime_type = (file.content_type or "").lower()
        extension = Path(file.filename).suffix.lower()
        
        # Determine media type
        media_type = self._get_media_type(mime_type, extension)
        
        # Validate MIME type
        if mime_type and not self._is_mime_type_allowed(mime_type, media_type):
            raise ValidationError(f"MIME type not allowed for {media_type}: {mime_type}")
        
        # Validate extension
        if not self._is_extension_allowed(extension, media_type):
            raise ValidationError(f"Extension not allowed for {media_type}: {extension}")
        
        return media_type, extension
    
    def _get_media_type(self, mime_type: str, extension: str) -> str:
        """Determine media type from MIME type or extension."""
        # Try MIME type first
        if mime_type:
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('video/'):
                return 'video'
            elif mime_type.startswith('application/') or mime_type.startswith('text/'):
                return 'document'
        
        # Fall back to extension
        if extension in self.allowed_extensions['image']:
            return 'image'
        elif extension in self.allowed_extensions['audio']:
            return 'audio'
        elif extension in self.allowed_extensions['video']:
            return 'video'
        elif extension in self.allowed_extensions['document']:
            return 'document'
        
        raise ValidationError("Unsupported media type")
    
    def _is_mime_type_allowed(self, mime_type: str, media_type: str) -> bool:
        """Check if MIME type is allowed for the media type."""
        allowed_types = self.allowed_mime_types.get(media_type, [])
        return mime_type in allowed_types
    
    def _is_extension_allowed(self, extension: str, media_type: str) -> bool:
        """Check if extension is allowed for the media type."""
        allowed_exts = self.allowed_extensions.get(media_type, [])
        return extension in allowed_exts
    
    async def upload_media(
        self, 
        file: UploadFile, 
        convert_video: bool = False
    ) -> dict:
        """
        Upload and process media file (image and audio only).
        
        Args:
            file: Uploaded file
            convert_video: No longer used - video conversion disabled
            
        Returns:
            Dictionary with file information
            
        Raises:
            MediaProcessingError: If upload or processing fails
        """
        try:
            # Validate file
            media_type, extension = self.validate_media_file(file)
            
            # Reject video files completely
            if media_type == 'video':
                raise ValidationError("Video files are no longer supported. Please use images or audio only.")
            
            # Read file content
            content = await file.read()
            
            # Validate file size
            if len(content) > self.settings.media_max_file_size:
                raise ValidationError(
                    f"File too large. Maximum size: {self.settings.media_max_file_size} bytes"
                )
            
            # Generate secure filename
            filename = generate_secure_filename(file.filename or "upload") + extension
            file_path = self.storage_path / filename
            
            # Save file
            file_path.write_bytes(content)
            
            # Generate public URL
            complete_public_url = f"/uploads/{filename}"
            
            logger.info(f"✅ File uploaded successfully: {filename}")
            logger.info(f"📏 Size: {len(content)} bytes")
            
            # Return response
            return {
                'filename': filename,
                'media_url': complete_public_url,
                'mime_type': file.content_type,
                'size_bytes': len(content),
                'media_type': media_type
            }
            
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            if isinstance(e, (ValidationError, MediaProcessingError)):
                raise
            raise MediaProcessingError(f"Media upload failed: {e}")
    
    def get_media_info(self, filename: str) -> Optional[dict]:
        """Get information about a media file."""
        try:
            file_path = self.storage_path / filename
            if not file_path.exists():
                return None
            
            # Basic file info
            stat = file_path.stat()
            extension = file_path.suffix.lower()
            
            # Determine media type
            media_type = self._get_media_type("", extension)
            
            info = {
                'filename': filename,
                'size_bytes': stat.st_size,
                'extension': extension,
                'media_type': media_type,
                'media_url': f"/uploads/{filename}"
            }
            
            # Add video-specific info
            if media_type == 'video':
                try:
                    video_info = video_converter.get_video_info_formatted(str(file_path))
                    info.update(video_info)
                except Exception as e:
                    logger.warning(f"Could not get video info: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting media info: {e}")
            return None
    
    def delete_media(self, filename: str) -> bool:
        """Delete a media file."""
        try:
            file_path = self.storage_path / filename
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Media file deleted: {filename}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting media file: {e}")
            return False
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """Clean up old media files."""
        import time
        
        try:
            current_time = time.time()
            cutoff_time = current_time - (days * 24 * 60 * 60)
            deleted_count = 0
            
            for file_path in self.storage_path.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Could not delete old file {file_path}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} old media files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0


# Global instance for dependency injection
media_service = MediaService()
