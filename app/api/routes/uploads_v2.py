"""
Refactored uploads API with improved architecture and security.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_password_changed
from app.core.exceptions import ValidationError, MediaProcessingError
from app.db.session import get_db
from app.models.user import User
from app.schemas.upload import UploadMediaResponse
from app.services.media import media_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/media", response_model=UploadMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_password_changed),
    db: Session = Depends(get_db),
) -> UploadMediaResponse:
    """
    Upload and process media files (images and audio only).
    
    This endpoint handles file uploads with proper validation, security checks.
    Video files are no longer supported - only images and audio are allowed.
    """
    try:
        logger.info(f"� User {current_user.email} uploading file: {file.filename}")
        
        # Video conversion disabled - only images and audio allowed
        convert_video = False  # Video conversion completely disabled
        
        # Upload and process media (no video conversion)
        result = await media_service.upload_media(file, convert_video=convert_video)
        
        # Log information
        logger.info(f"✅ File uploaded successfully: {result['filename']}")
        logger.info(f"🔗 Public URL: {result['media_url']}")
        logger.info(f" Size: {result['size_bytes']} bytes")
        
        return UploadMediaResponse(
            filename=result['filename'],
            media_url=result['media_url'],
            mime_type=result['mime_type'],
            size_bytes=result['size_bytes'],
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error for upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except MediaProcessingError as e:
        logger.error(f"Media processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )


@router.get("/media/{filename}", response_model=Dict[str, Any])
async def get_media_info(
    filename: str,
    current_user: User = Depends(get_current_user_password_changed),
) -> Dict[str, Any]:
    """Get information about a media file."""
    try:
        info = media_service.get_media_info(filename)
        
        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media file not found"
            )
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting media info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving media information"
        )


@router.delete("/media/{filename}")
async def delete_media(
    filename: str,
    current_user: User = Depends(get_current_user_password_changed),
) -> Dict[str, Any]:
    """Delete a media file."""
    try:
        success = media_service.delete_media(filename)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media file not found"
            )
        
        return {"message": "Media file deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting media: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting media file"
        )


@router.post("/cleanup")
async def cleanup_old_media(
    days: int = 30,
    current_user: User = Depends(get_current_user_password_changed),
) -> Dict[str, Any]:
    """Clean up old media files (admin only)."""
    try:
        # Check if user is admin
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        deleted_count = media_service.cleanup_old_files(days)
        
        return {
            "message": f"Cleaned up {deleted_count} old media files",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error during cleanup"
        )
