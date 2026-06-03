#!/usr/bin/env python3
"""
Script de inicialização de templates do sistema
Executado automaticamente durante o startup da aplicação
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import engine, SessionLocal
from app.models.template import MessageTemplate


async def init_system_templates():
    """Inicializa templates do sistema se não existirem."""
    print("=== INICIALIZANDO TEMPLATES DO SISTEMA ===")
    
    # Criar sessão do banco de dados
    db = SessionLocal()
    
    try:
        # Verificar se já existem templates do sistema
        existing_templates = db.query(MessageTemplate).filter(
            MessageTemplate.is_system == True
        ).all()
        
        if existing_templates:
            print(f"Templates do sistema já existem: {len(existing_templates)}")
            for template in existing_templates:
                print(f"  - {template.title} ({template.category})")
            return
        
        print("Criando templates do sistema...")
        
        # Template LGPD
        lgpd_template = MessageTemplate(
            title="Termo de Consentimento LGPD",
            content="""*Termo de Consentimento para Tratamento de Dados Pessoais*

Precisamos do seu consentimento para coletar e tratar dados pessoais (como nome, e-mail, CPF e informações da solicitação) usados apenas para prestar e aprimorar o atendimento. Seus dados não serão compartilhados sem autorização, e você pode acessá-los, corrigi-los ou solicitar sua exclusão a qualquer momento. Ao prosseguir, você concorda com esses termos.

Deseja continuar o atendimento?""",
            category="LGPD",
            is_system=True,
            is_active=True
        )
        
        # Template Pesquisa
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
        
        # Salvar templates
        db.add_all([lgpd_template, research_template])
        db.commit()
        
        print("Templates do sistema criados com sucesso:")
        print(f"  - {lgpd_template.title} ({lgpd_template.category})")
        print(f"  - {research_template.title} ({research_template.category})")
        
    except Exception as e:
        print(f"Erro ao inicializar templates do sistema: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("=== INICIALIZAÇÃO DE TEMPLATES CONCLUÍDA ===")


if __name__ == "__main__":
    asyncio.run(init_system_templates())
