import json
import re
import os
import sys

# Garante que podemos importar do diretório pai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.brain import SniperBrain
from modules.database import create_db_deliverable_app, get_db_deliverable_app_by_slug

def generate_pwa_content(nicho: str) -> dict:
    """Usa o SniperBrain para gerar toda a cópia, perguntas, estilo e depoimentos de um quiz viral."""
    brain = SniperBrain()
    
    system_prompt = """
    Você é um Engenheiro de Growth e Especialista em Funis de Conversão (Quiz Funnels).
    Sua missão é gerar um JSON completo e válido para um Web App PWA interativo do nicho fornecido pelo usuário.
    Este aplicativo é um Quiz Diagnóstico de alta conversão. Ele ajuda o usuário a identificar um problema e, no final, cobra um valor baixo (R$ 9,90) para destravar um plano de ação completo.
    
    Você deve retornar APENAS o objeto JSON, sem markdown extras, sem blocos de código ```json e sem conversas explicativas. O JSON deve ser perfeitamente parseável por json.loads() em Python.
    
    O JSON deve seguir EXATAMENTE esta estrutura de chaves:
    {
        "title": "Título magnético do App (ex: Avaliação de Estresse Canino)",
        "subtitle": "Subtítulo persuasivo focado no problema e solução rápida",
        "primaryColor": "Código HEX de cor primária elegante baseada no nicho (ex: '#10B981')",
        "secondaryColor": "Código HEX de cor secundária elegante (ex: '#059669')",
        "questions": [
            {
                "id": "q1",
                "questionText": "Texto da primeira pergunta do quiz",
                "options": [
                    {"text": "Opção A", "points": 1},
                    {"text": "Opção B", "points": 2},
                    {"text": "Opção C", "points": 3}
                ]
            }
        ],
        "testimonials": [
            {
                "name": "Nome e sobrenome fictício do cliente (ex: Mariana Souza)",
                "role": "Perfil (ex: Dona do Toby, 3 anos)",
                "text": "Depoimento convincente sobre como o relatório ajudou a resolver o problema",
                "rating": 5
            }
        ],
        "free_results": {
            "title": "Seu Diagnóstico Parcial está Pronto!",
            "description": "Uma breve descrição do diagnóstico geral que o usuário ganha de graça, gerando curiosidade para o plano de ação completo."
        },
        "premium_results_preview": {
            "title": "Plano de Ação Personalizado (12 Meses)",
            "description": "Texto descrevendo o que está bloqueado (ex: O cronograma completo de 52 semanas de enriquecimento ambiental para curar a ansiedade do seu pet)."
        },
        "pricing": {
            "price_cents": 990,
            "currency": "BRL",
            "button_text": "Liberar Plano de Ação Completo por R$ 9,90"
        }
    }
    
    Gere exatamente de 6 a 8 perguntas interessantes, que engajem o usuário e o façam responder com atenção.
    """
    
    user_prompt = f"Gere o quiz completo de alta conversão para o seguinte nicho: {nicho}."
    
    fallback_data = {
        "title": f"Quiz de Diagnóstico: {nicho}",
        "subtitle": "Descubra o diagnóstico completo em poucos minutos.",
        "primaryColor": "#3B82F6",
        "secondaryColor": "#2563EB",
        "questions": [
            {
                "id": "q1",
                "questionText": "Você sente que este problema afeta sua rotina diariamente?",
                "options": [
                    {"text": "Sim, muito", "points": 3},
                    {"text": "Às vezes", "points": 2},
                    {"text": "Raramente", "points": 1}
                ]
            }
        ],
        "testimonials": [
            {
                "name": "Alex Silva",
                "role": "Usuário verificado",
                "text": "Muito bom! O diagnóstico me deu uma clareza incrível sobre o que fazer.",
                "rating": 5
            }
        ],
        "free_results": {
            "title": "Resultado Inicial Calculado!",
            "description": "Identificamos padrões importantes nas suas respostas."
        },
        "premium_results_preview": {
            "title": "Plano de Ação Completo",
            "description": "O guia passo a passo detalhado de 12 meses."
        },
        "pricing": {
            "price_cents": 990,
            "currency": "BRL",
            "button_text": "Liberar Plano Completo por R$ 9,90"
        }
    }

    try:
        raw_response = brain._call_llm(system_prompt, user_prompt, temperature=0.7)
        # Limpa possíveis blocos de código markdown que a IA possa ter retornado por engano
        cleaned = raw_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        config = json.loads(cleaned)
        return config
    except Exception as e:
        print(f"[Deliverables] Erro ao obter/decodificar conteúdo do LLM: {e}. Usando fallback...")
        return fallback_data

def create_deliverable_app_for_channel(channel_id: str, name: str, nicho: str, slug: str) -> dict:
    """Gera o conteúdo da IA e salva no banco de dados."""
    import uuid
    # Gera slug limpo se não fornecido
    if not slug:
        slug = re.sub(r'[^a-zA-Z0-9-]', '', name.lower().replace(" ", "-"))
        
    # Evita duplicados
    existing = get_db_deliverable_app_by_slug(slug)
    if existing:
        slug = f"{slug}-{channel_id[:4]}"
        
    config = generate_pwa_content(nicho)
    
    app_data = create_db_deliverable_app(
        channel_id=channel_id,
        name=name,
        slug=slug,
        nicho=nicho,
        app_type="quiz_diagnostico",
        config_json=config
    )
    return app_data
