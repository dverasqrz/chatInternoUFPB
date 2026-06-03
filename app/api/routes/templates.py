from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.template import (
    MessageTemplateCreate,
    MessageTemplateList,
    MessageTemplateResponse,
    MessageTemplateUpdate
)
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])


def get_template_service(db: Session = Depends(get_db)) -> TemplateService:
    """Get template service instance."""
    return TemplateService(db)


@router.get("/", response_model=MessageTemplateList)
def get_templates(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> MessageTemplateList:
    """
    Get all message templates.
    
    Available to all authenticated users.
    """
    try:
        templates = template_service.get_templates(include_inactive=include_inactive)
        return MessageTemplateList(
            templates=[MessageTemplateResponse.model_validate(t) for t in templates],
            total=len(templates)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving templates: {str(e)}"
        )


@router.get("/{template_id}", response_model=MessageTemplateResponse)
def get_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> MessageTemplateResponse:
    """
    Get a specific message template by ID.
    
    Available to all authenticated users.
    """
    try:
        template = template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        return MessageTemplateResponse.model_validate(template)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving template: {str(e)}"
        )


@router.post("/", response_model=MessageTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: MessageTemplateCreate,
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> MessageTemplateResponse:
    """
    Create a new message template.
    
    **ADMIN ONLY** - Only administrators can create templates.
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create templates"
        )
    
    try:
        template = template_service.create_template(
            template_data=template_data,
            created_by=current_user.id
        )
        return MessageTemplateResponse.model_validate(template)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating template: {str(e)}"
        )


@router.put("/{template_id}", response_model=MessageTemplateResponse)
def update_template(
    template_id: int,
    template_data: MessageTemplateUpdate,
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> MessageTemplateResponse:
    """
    Update an existing message template.
    
    **ADMIN ONLY** - Only administrators can update templates.
    System templates cannot be modified.
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update templates"
        )
    
    try:
        template = template_service.update_template(
            template_id=template_id,
            template_data=template_data,
            updated_by=current_user.id
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return MessageTemplateResponse.model_validate(template)
        
    except ValueError as e:
        # Handle system template protection
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating template: {str(e)}"
        )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> None:
    """
    Delete a message template.
    
    **ADMIN ONLY** - Only administrators can delete templates.
    System templates cannot be deleted.
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete templates"
        )
    
    try:
        success = template_service.delete_template(
            template_id=template_id,
            deleted_by=current_user.id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
    except ValueError as e:
        # Handle system template protection
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting template: {str(e)}"
        )


@router.get("/category/{category}", response_model=List[MessageTemplateResponse])
def get_templates_by_category(
    category: str,
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> List[MessageTemplateResponse]:
    """
    Get templates by category.
    
    Available to all authenticated users.
    """
    try:
        templates = template_service.get_templates_by_category(category)
        return [MessageTemplateResponse.model_validate(t) for t in templates]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving templates by category: {str(e)}"
        )


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
def initialize_system_templates(
    current_user: User = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
) -> dict:
    """
    Initialize system templates (LGPD and Research).
    
    **ADMIN ONLY** - Only administrators can initialize system templates.
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can initialize system templates"
        )
    
    try:
        template_service.initialize_system_templates()
        return {"message": "System templates initialized successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing system templates: {str(e)}"
        )
