"""
Dezafira Shared Memory Engine — Módulo de Memória Centralizada de Longo Prazo
==============================================================================
Permite que o Hermes (NVIDIA), Roteirista (DeepSeek) e Agente de Mídia (OpenMontage/Pexels)
compartilhem aprendizados, regras de tom de voz por canal e otimizem o consumo de tokens
evitando redundâncias.

Baseado no conceito de "Shared Brain" (Cérebro Compartilhado) adaptado para a arquitetura
relacional da Dezafira (FastAPI + SQLAlchemy + SQLite/PostgreSQL).
"""

import os
import sys
from typing import Optional, List, Dict, Any

# Garantir que podemos importar do diretório pai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.database import SessionLocal, ChannelKnowledge


# ─── CATEGORIAS DE CONHECIMENTO ───────────────────────────────────────

CATEGORY_STYLE_GUIDE = "style_guide"        # Tom de voz, regras de estilo
CATEGORY_SEO_BLACKLIST = "seo_blacklist"    # Palavras/padrões SEO a evitar
CATEGORY_PEXELS_FALLBACK = "pexels_fallback"  # Keywords que falharam no Pexels
CATEGORY_AUDIENCE_INSIGHT = "audience_insight"  # Insights sobre o público
CATEGORY_GROWTH_HACK = "growth_hack"        # Táticas de growth hacking
CATEGORY_SUCCESS_PATTERN = "success_pattern"  # Padrões de vídeos de sucesso


# ─── CRUD DA MEMÓRIA ──────────────────────────────────────────────────

def save_knowledge(
    channel_id: str,
    category: str,
    meta_key: str,
    meta_value: str,
    source: str = "hermes"
) -> bool:
    """
    Salva um conhecimento/insight no Shared Brain.

    Args:
        channel_id: ID do canal
        category: Categoria (ex: 'style_guide', 'growth_hack')
        meta_key: Chave do conhecimento (ex: 'tom_de_voz', 'failed_keyword_X')
        meta_value: Valor do conhecimento
        source: Quem está salvando ('hermes', 'deepseek', 'user_feedback')

    Returns:
        True se salvou com sucesso
    """
    db = SessionLocal()
    try:
        # Evitar duplicatas — atualiza se já existir
        existing = db.query(ChannelKnowledge).filter(
            ChannelKnowledge.channel_id == channel_id,
            ChannelKnowledge.category == category,
            ChannelKnowledge.meta_key == meta_key
        ).first()

        if existing:
            existing.meta_value = meta_value
            existing.source = source
        else:
            new_knowledge = ChannelKnowledge(
                channel_id=channel_id,
                category=category,
                meta_key=meta_key,
                meta_value=meta_value,
                source=source
            )
            db.add(new_knowledge)

        db.commit()
        return True
    except Exception as e:
        print(f"[MemoryService] Erro ao salvar conhecimento: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def get_knowledge(
    channel_id: str,
    category: Optional[str] = None,
    meta_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Recupera conhecimentos salvos, com filtros opcionais.

    Args:
        channel_id: ID do canal
        category: Filtrar por categoria (opcional)
        meta_key: Filtrar por chave (opcional)

    Returns:
        Lista de dicionários com os conhecimentos
    """
    db = SessionLocal()
    try:
        query = db.query(ChannelKnowledge).filter(
            ChannelKnowledge.channel_id == channel_id
        )

        if category:
            query = query.filter(ChannelKnowledge.category == category)
        if meta_key:
            query = query.filter(ChannelKnowledge.meta_key == meta_key)

        records = query.order_by(ChannelKnowledge.updated_at.desc()).all()

        return [
            {
                "id": r.id,
                "category": r.category,
                "meta_key": r.meta_key,
                "meta_value": r.meta_value,
                "source": r.source,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in records
        ]
    finally:
        db.close()


def get_channel_context_prompt(channel_id: str) -> str:
    """
    Gera um prompt de contexto com todas as regras de estilo, tom de voz
    e growth hacks salvos para o canal. Este prompt é injetado nas chamadas
    ao LLM para contextualizar o roteirista.

    Args:
        channel_id: ID do canal

    Returns:
        String formatada para usar como contexto no prompt do LLM
    """
    db = SessionLocal()
    try:
        records = db.query(ChannelKnowledge).filter(
            ChannelKnowledge.channel_id == channel_id
        ).all()

        if not records:
            return ""

        lines = []
        for r in records:
            lines.append(f"- {r.category}/{r.meta_key}: {r.meta_value}")

        return "Memória de Longo Prazo do Canal:\n" + "\n".join(lines)
    finally:
        db.close()


def log_failed_keyword(channel_id: str, keyword: str) -> bool:
    """
    Registra que uma keyword falhou na busca de mídia (Pexels/OpenMontage).
    Útil para que o agente de prompts não tente usá-la novamente.

    Args:
        channel_id: ID do canal
        keyword: Palavra-chave que falhou

    Returns:
        True se registrou com sucesso
    """
    return save_knowledge(
        channel_id=channel_id,
        category=CATEGORY_PEXELS_FALLBACK,
        meta_key=f"failed_keyword_{keyword.lower().replace(' ', '_')}",
        meta_value=f"Evitar. Essa busca retornou zero resultados na API de mídia.",
        source="media_agent"
    )


def log_success_pattern(
    channel_id: str,
    keyword: str,
    engagement_note: str = ""
) -> bool:
    """
    Registra um padrão de sucesso (ex: keyword que gerou bom engajamento).

    Args:
        channel_id: ID do canal
        keyword: Palavra-chave que funcionou bem
        engagement_note: Nota sobre o engajamento (opcional)

    Returns:
        True se registrou com sucesso
    """
    return save_knowledge(
        channel_id=channel_id,
        category=CATEGORY_SUCCESS_PATTERN,
        meta_key=f"success_keyword_{keyword.lower().replace(' ', '_')}",
        meta_value=f"Keyword '{keyword}' gerou bom resultado. {engagement_note}",
        source="media_agent"
    )


def log_growth_hack(channel_id: str, hack_name: str, hack_description: str) -> bool:
    """
    Registra uma tática de growth hacking para o canal.

    Args:
        channel_id: ID do canal
        hack_name: Nome da tática (ex: 'hook_3_segundos')
        hack_description: Descrição detalhada da tática

    Returns:
        True se registrou com sucesso
    """
    return save_knowledge(
        channel_id=channel_id,
        category=CATEGORY_GROWTH_HACK,
        meta_key=hack_name,
        meta_value=hack_description,
        source="hermes"
    )


def get_failed_keywords(channel_id: str) -> List[str]:
    """
    Recupera lista de keywords que falharam para este canal.

    Args:
        channel_id: ID do canal

    Returns:
        Lista de keywords que falharam
    """
    records = get_knowledge(
        channel_id=channel_id,
        category=CATEGORY_PEXELS_FALLBACK
    )
    keywords = []
    for r in records:
        key = r["meta_key"]
        if key.startswith("failed_keyword_"):
            keywords.append(key.replace("failed_keyword_", "").replace("_", " "))
    return keywords


# ─── FACTORY DEFAULTS ─────────────────────────────────────────────────

def seed_default_knowledge(channel_id: str) -> None:
    """
    Popula conhecimento padrão para um novo canal.
    Chamado automaticamente quando um canal é criado.
    """
    defaults = [
        (CATEGORY_STYLE_GUIDE, "tom_de_voz", "Direto, objetivo, sem enrolação. Uma ideia por frase."),
        (CATEGORY_STYLE_GUIDE, "hook_rule", "Nunca começar com saudações. Começar direto no ápice do assunto."),
        (CATEGORY_STYLE_GUIDE, "max_script_words", "120"),
        (CATEGORY_GROWTH_HACK, "primeiros_3_segundos", "O vídeo deve prender a atenção nos primeiros 3 segundos com um fato intrigante ou pergunta provocativa."),
        (CATEGORY_GROWTH_HACK, "ritmo_visual", "Nenhuma cena deve durar mais de 2.5 segundos. Alternar palavras-chave dinâmicas."),
        (CATEGORY_GROWTH_HACK, "titulo_curiosity_gap", "Usar fórmula: [Gatilho de Curiosidade] + [Fato Inesperado]. Evitar títulos meramente informativos."),
    ]

    for category, key, value in defaults:
        save_knowledge(channel_id, category, key, value, source="system")


if __name__ == "__main__":
    # Teste rápido
    print("=== Teste do Shared Memory System ===\n")

    # Seed para canal default
    seed_default_knowledge("default")

    # Recuperar
    ctx = get_channel_context_prompt("default")
    print("Contexto gerado:")
    print(ctx)

    # Log de keyword falha
    log_failed_keyword("default", "alien technology abstract")
    print("\nKeywords que falharam:", get_failed_keywords("default"))
