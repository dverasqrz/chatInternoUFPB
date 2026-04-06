"""
WhatsApp-specific tools and utilities.
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

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/status-media", response_model=UploadMediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_status_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_password_changed),
    db: Session = Depends(get_db),
) -> UploadMediaResponse:
    """
    Upload media for WhatsApp Status (images and audio only).
    
    This endpoint handles media uploads specifically for WhatsApp Status.
    Video files are not supported - only images and audio are allowed.
    """
    try:
        logger.info(f"📱 User {current_user.email} uploading WhatsApp Status media: {file.filename}")
        
        # Validate file type (no video allowed)
        if not file.content_type:
            raise ValidationError("File type is required")
        
        if file.content_type.startswith('video/'):
            raise ValidationError("Video files are not supported for WhatsApp Status. Please use images or audio only.")
        
        # Upload and process media (no conversion)
        result = await media_service.upload_media(file, convert_video=False)
        
        # Log detailed information
        logger.info(f"✅ WhatsApp Status media uploaded: {result['filename']}")
        logger.info(f"🔗 Public URL: {result['media_url']}")
        
        return UploadMediaResponse(
            filename=result['filename'],
            media_url=result['media_url'],
            mime_type=result['mime_type'],
            size_bytes=result['size_bytes'],
        )
        
    except ValidationError as e:
        logger.warning(f"Validation error for Status media: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except MediaProcessingError as e:
        logger.error(f"Media processing error for Status media: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during Status media upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during Status media upload"
        )


@router.get("/media-info", response_model=Dict[str, Any])
async def get_media_info(
    current_user: User = Depends(get_current_user_password_changed),
) -> Dict[str, Any]:
    """Get information about supported media types."""
    try:
        return {
            "supported_types": {
                "images": True,
                "audio": True,
                "video": False  # Video support disabled
            },
            "allowed_image_formats": [
                "image/jpeg",
                "image/png", 
                "image/webp",
                "image/gif"
            ],
            "allowed_audio_formats": [
                "audio/mpeg",
                "audio/wav",
                "audio/ogg",
                "audio/webm"
            ],
            "max_file_size": "10MB",
            "features": {
                "image_upload": True,
                "audio_upload": True,
                "video_upload": False,  # Disabled
                "conversion": False,      # No conversion
                "whatsapp_status": True
            },
            "message": "Video files are no longer supported. Please use images or audio only."
        }
        
    except Exception as e:
        logger.error(f"Error getting media info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving media information"
        )
