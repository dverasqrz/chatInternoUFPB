import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.template import MessageTemplate
from app.schemas.template import MessageTemplateCreate, MessageTemplateUpdate

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing message templates."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_templates(self, include_inactive: bool = False) -> List[MessageTemplate]:
        """Get all message templates."""
        try:
            query = select(MessageTemplate)
            
            if not include_inactive:
                query = query.where(MessageTemplate.is_active == True)
            
            query = query.order_by(MessageTemplate.category, MessageTemplate.title)
            
            result = self.db.execute(query)
            templates = result.scalars().all()
            
            logger.info(f"Retrieved {len(templates)} templates")
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving templates: {e}")
            raise
    
    def get_template_by_id(self, template_id: int) -> Optional[MessageTemplate]:
        """Get a specific template by ID."""
        try:
            query = select(MessageTemplate).where(MessageTemplate.id == template_id)
            result = self.db.execute(query)
            template = result.scalar_one_or_none()
            
            if template:
                logger.info(f"Retrieved template {template_id}: {template.title}")
            else:
                logger.warning(f"Template {template_id} not found")
                
            return template
            
        except Exception as e:
            logger.error(f"Error retrieving template {template_id}: {e}")
            raise
    
    def create_template(self, template_data: MessageTemplateCreate, created_by: Optional[int] = None) -> MessageTemplate:
        """Create a new message template."""
        try:
            template = MessageTemplate(
                title=template_data.title,
                content=template_data.content,
                category=template_data.category,
                created_by=created_by,
                is_system=False  # User-created templates are not system templates
            )
            
            self.db.add(template)
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"Created template '{template.title}' (ID: {template.id}) by user {created_by}")
            return template
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            self.db.rollback()
            raise
    
    def update_template(self, template_id: int, template_data: MessageTemplateUpdate, updated_by: Optional[int] = None) -> Optional[MessageTemplate]:
        """Update an existing message template."""
        try:
            template = self.get_template_by_id(template_id)
            
            if not template:
                logger.warning(f"Cannot update template {template_id}: not found")
                return None
            
            # Removed system template update protection by request
            
            # Update fields if provided
            if template_data.title is not None:
                template.title = template_data.title
            if template_data.content is not None:
                template.content = template_data.content
            if template_data.category is not None:
                template.category = template_data.category
            if template_data.is_active is not None:
                template.is_active = template_data.is_active
            
            self.db.commit()
            self.db.refresh(template)
            
            logger.info(f"Updated template '{template.title}' (ID: {template.id}) by user {updated_by}")
            return template
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating template {template_id}: {e}")
            self.db.rollback()
            raise
    
    def delete_template(self, template_id: int, deleted_by: Optional[int] = None) -> bool:
        """Delete a message template."""
        try:
            template = self.get_template_by_id(template_id)
            
            if not template:
                logger.warning(f"Cannot delete template {template_id}: not found")
                return False
            
            # Removed system template deletion protection by request
            
            self.db.delete(template)
            self.db.commit()
            
            logger.info(f"Deleted template '{template.title}' (ID: {template.id}) by user {deleted_by}")
            return True
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            self.db.rollback()
            raise
    
    def get_templates_by_category(self, category: str) -> List[MessageTemplate]:
        """Get templates by category."""
        try:
            query = select(MessageTemplate).where(
                MessageTemplate.category == category,
                MessageTemplate.is_active == True
            ).order_by(MessageTemplate.title)
            
            result = self.db.execute(query)
            templates = result.scalars().all()
            
            logger.info(f"Retrieved {len(templates)} templates for category '{category}'")
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving templates by category '{category}': {e}")
            raise
    
    def initialize_system_templates(self):
        """Initialize system templates (LGPD and Research)."""
        try:
            # Check if system templates already exist
            existing_system_templates = self.db.execute(
                select(MessageTemplate).where(MessageTemplate.is_system == True)
            ).scalars().all()
            
            if existing_system_templates:
                logger.info(f"System templates already exist: {len(existing_system_templates)}")
                return
            
            # LGPD Template
            lgpd_template = MessageTemplate(
                title="Termo de Consentimento LGPD",
                content="""*Termo de Consentimento para Tratamento de Dados Pessoais*

Precisamos do seu consentimento para coletar e tratar dados pessoais (como nome, e-mail, CPF e informações da solicitação) usados apenas para prestar e aprimorar o atendimento. Seus dados não serão compartilhados sem autorização, e você pode acessá-los, corrigi-los ou solicitar sua exclusão a qualquer momento. Ao prosseguir, você concorda com esses termos.

Deseja continuar o atendimento?""",
                category="LGPD",
                is_system=True,
                is_active=True
            )
            
            # Research Template
            research_template = MessageTemplate(
                title="Pesquisa de Satisfação",
                content="""Sua opinião é muito importante para nós. 
Em uma escala de 1 a 5, como você avalia o atendimento que acabou de receber neste canal?

1 estrelas - Muito insatisfeito
2 estrelas - Insatisfeito
3 estrelas - Neutro
4 estrelas - Satisfeito
5 estrelas - Muito satisfeito""",
                category="Pesquisa",
                is_system=True,
                is_active=True
            )
            
            self.db.add_all([lgpd_template, research_template])
            self.db.commit()
            
            logger.info("Initialized 2 system templates (LGPD and Research)")
            
        except Exception as e:
            logger.error(f"Error initializing system templates: {e}")
            self.db.rollback()
            raise
