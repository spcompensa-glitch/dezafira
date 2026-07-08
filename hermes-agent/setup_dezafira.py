#!/usr/bin/env python3
"""
Dezafira Setup Script — Configura Nous Hermes Agent
Executar no primeiro boot para criar skills e memória inicial.
"""
import os
import json

HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")

def setup_memory():
    """Cria memória inicial do Dezafira."""
    memory_dir = os.path.join(HERMES_HOME, "skills")
    os.makedirs(memory_dir, exist_ok=True)

    # Skill: Produzir vídeo
    skill_produce = {
        "name": "produzir_video",
        "description": "Produz um vídeo completo no Dezafira",
        "command": "python /workspace/tools/produce_video.py {theme} {channel_id} {format}",
        "parameters": {
            "theme": "Tema do vídeo",
            "channel_id": "ID do canal (default: 'default')",
            "format": "vertical ou horizontal (default: 'vertical')"
        }
    }

    # Skill: Pesquisar nicho
    skill_research = {
        "name": "pesquisar_nicho",
        "description": "Pesquisa tendências de um nicho no YouTube",
        "command": "python /workspace/tools/research.py {theme}",
        "parameters": {
            "theme": "Nicho/tema para pesquisar"
        }
    }

    # Skill: Gerenciar canais
    skill_channels = {
        "name": "gerenciar_canais",
        "description": "Lista, cria ou deleta canais",
        "commands": {
            "list": "python /workspace/tools/manage_channels.py list",
            "create": "python /workspace/tools/manage_channels.py create {name} {niche}",
            "delete": "python /workspace/tools/manage_channels.py delete {channel_id}"
        }
    }

    # Skill: Upload YouTube
    skill_upload = {
        "name": "upload_youtube",
        "description": "Faz upload de vídeo para o YouTube",
        "command": "python /workspace/tools/upload.py {video_path} {channel_id} {title}",
        "parameters": {
            "video_path": "Caminho do vídeo",
            "channel_id": "ID do canal",
            "title": "Título do vídeo"
        }
    }

    # Skill: Analisar performance
    skill_analyze = {
        "name": "analisar_performance",
        "description": "Analisa performance dos vídeos produzidos",
        "command": "python /workspace/tools/analyze_performance.py {period}",
        "parameters": {
            "period": "week ou month"
        }
    }

    skills = [skill_produce, skill_research, skill_channels, skill_upload, skill_analyze]

    for skill in skills:
        skill_path = os.path.join(memory_dir, f"{skill['name']}.json")
        with open(skill_path, "w") as f:
            json.dump(skill, f, indent=2, ensure_ascii=False)
        print(f"[Setup] Skill criada: {skill['name']}")

    # Memória inicial
    memory_file = os.path.join(HERMES_HOME, "MEMORY.md")
    if not os.path.exists(memory_file):
        memory_content = """# Dezafira — Memória do Agente

## Sobre o Projeto
- Dezafira é uma fábrica automatizada de canais YouTube
- Objetivo: 50 canais monetizados com vídeos 100% autônomos
- Budget: $0 (usar ferramentas gratuitas)

## Ferramentas Disponíveis
- `produce_video.py` — Produz vídeo completo
- `research.py` — Pesquisa tendências de nicho
- `upload.py` — Faz upload para YouTube
- `manage_channels.py` — Gerencia canais
- `analyze_performance.py` — Analisa métricas

## Preferências do Usuário
- Formato padrão: vertical (Shorts/Reels)
- Canal padrão: "default"
- LLM: NVIDIA NIM (Llama 3.1 8B)
- TTS: Edge-TTS (qualidade boa, funciona sempre)
"""
        with open(memory_file, "w") as f:
            f.write(memory_content)
        print("[Setup] Memória inicial criada: MEMORY.md")

    # Perfil do usuário
    user_file = os.path.join(HERMES_HOME, "USER.md")
    if not os.path.exists(user_file):
        user_content = """# Perfil do Usuário

## Identidade
- Nome: Christian
- Projeto: Dezafira Factory
- Meta: 50 canais YouTube monetizados

## Preferências
- Formato: vertical (Shorts/Reels)
- Idioma: Português
- Estilo: Direto, sem enrolação
- Horário preferido: Manhã (9h)

## Histórico
- Já produziu vídeos de teste
- Usa NVIDIA LLM para roteiros
- Canal principal: tech_converter
"""
        with open(user_file, "w") as f:
            f.write(user_content)
        print("[Setup] Perfil do usuário criado: USER.md")

def main():
    print("=" * 60)
    print(" DEZAFIRA — Setup do Nous Hermes Agent")
    print("=" * 60)
    print()

    print("[1/2] Configurando memória...")
    setup_memory()

    print()
    print("[2/2] Skills e memória prontos!")
    print()
    print("Nous Hermes Agent está configurado para Dezafira.")
    print("Skills disponíveis:")
    print("  - produzir_video")
    print("  - pesquisar_nicho")
    print("  - gerenciar_canais")
    print("  - upload_youtube")
    print("  - analisar_performance")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()
