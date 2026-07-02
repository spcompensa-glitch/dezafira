"""
Dezafira OpenMontage Bridge — Integração com o Motor de Renderização OpenMontage
=================================================================================
Este módulo conecta a pipeline da Dezafira ao OpenMontage, que é o motor de
renderização oficial de vídeos. O OpenMontage usa:
  - NVIDIA API (Hermes como orquestrador principal)
  - DeepSeek como fallback
  - Remotion (Node.js/React) para composição final
  - Pexels como fonte de mídia stock

O bridge oferece 3 modos de operação:
  1. FULL_PIPELINE: Chama o OpenMontage via subprocess (pipeline completa)
  2. TOOLS_DIRECT: Usa as ferramentas Python do OpenMontage diretamente
  3. REMOTION_ONLY: Usa apenas o Remotion para renderização final
"""

import os
import sys
import subprocess
import json
import asyncio
from typing import Optional, List, Dict, Any
from pathlib import Path

# Garantir que podemos importar do diretório pai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── CONFIGURAÇÃO ──────────────────────────────────────────────────────

OPEN_MONTAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "OpenMontage"
)
REMOTION_COMPOSER_DIR = os.path.join(OPEN_MONTAGE_DIR, "remotion-composer")
TOOLS_DIR = os.path.join(OPEN_MONTAGE_DIR, "tools")

OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "outputs"
)


def is_open_montage_available() -> bool:
    """Verifica se o OpenMontage está instalado."""
    return os.path.isdir(OPEN_MONTAGE_DIR) and os.path.isfile(
        os.path.join(OPEN_MONTAGE_DIR, "setup.py")
    )


def get_open_montage_status() -> Dict[str, Any]:
    """Retorna o status detalhado da instalação do OpenMontage."""
    return {
        "installed": is_open_montage_available(),
        "path": OPEN_MONTAGE_DIR,
        "remotion_available": os.path.isdir(os.path.join(REMOTION_COMPOSER_DIR, "node_modules")),
        "tools_count": len(os.listdir(TOOLS_DIR)) if os.path.isdir(TOOLS_DIR) else 0,
        "nvidia_configured": bool(os.getenv("NVIDIA_API_KEY")),
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        "pexels_configured": bool(os.getenv("PEXELS_API_KEY")),
    }


# ─── MODO 1: PIPELINE COMPLETA VIA SUBPROCESS ─────────────────────────

async def run_open_montage_pipeline(
    prompt: str,
    output_path: str,
    provider: str = "nvidia",
    duration_seconds: int = 45,
    style: str = "documentary_montage",
) -> Dict[str, Any]:
    """
    Executa a pipeline completa do OpenMontage via chamada de script Python.

    O OpenMontage foi projetado para ser orquestrado por um agente de IA,
    então esta função atua como o "agente" que comanda a pipeline localmente.

    Args:
        prompt: Tema do vídeo (ex: "Como a IA está transformando o mundo")
        output_path: Caminho de saída do vídeo MP4
        provider: 'nvidia' (padrão) ou 'deepseek'
        duration_seconds: Duração alvo em segundos
        style: Estilo da pipeline ('documentary_montage', 'animated_explainer', etc.)

    Returns:
        Dict com status da operação
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Construir ambiente com as chaves de API
    env = os.environ.copy()
    env["OPEN_MONTAGE_PROVIDER"] = provider

    # --- Pipeline usando Remotion ---
    # O OpenMontage usa remotion-composer para renderização.
    # Vamos usar o render_demo.py como referência e adaptar para nosso caso.

    return await _run_remotion_pipeline(
        prompt=prompt,
        output_path=output_path,
        duration_seconds=duration_seconds,
        provider=provider,
        env=env,
    )


# ─── MODO 2: REMOTION COMPOSER ───────────────────────────────────────

async def _run_remotion_pipeline(
    prompt: str,
    output_path: str,
    duration_seconds: int = 45,
    provider: str = "nvidia",
    env: Dict[str, str] = None,
) -> Dict[str, Any]:
    """
    Usa o Remotion (remotion-composer) para renderizar o vídeo final.

    Como o OpenMontage é agentic e não tem uma CLI programática tradicional,
    esta função:
    1. Gera um arquivo de props JSON para o Remotion
    2. Chama o Remotion CLI para renderizar
    """
    env = env or os.environ.copy()

    # Preparar props para o Remotion baseado no prompt
    props = {
        "cuts": [
            {
                "durationInFrames": duration_seconds * 30,  # 30fps
                "title": prompt[:60],
                "subtitle": "Gerado pela Dezafira Factory",
                "primaryColor": "#1ed760",
                "backgroundColor": "#0a0a0a",
            }
        ]
    }

    props_path = os.path.join(
        REMOTION_COMPOSER_DIR,
        "public",
        "demo-props",
        "dezafira_props.json"
    )
    os.makedirs(os.path.dirname(props_path), exist_ok=True)
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    print(f"[OpenMontageBridge] Props salvos em: {props_path}")

    # Verificar se o Remotion está configurado
    npx_path = _find_command("npx", "npx.cmd", "npx.exe")
    if not npx_path:
        return {
            "success": False,
            "error": "npx não encontrado. Instale Node.js para usar o Remotion.",
            "output_path": None,
        }

    try:
        # Executar Remotion render
        cmd = [
            npx_path,
            "remotion",
            "render",
            "src/index.tsx",
            "Explainer",
            str(output_path),
            "--props",
            str(props_path),
            "--codec",
            "h264",
        ]

        print(f"[OpenMontageBridge] Executando: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=REMOTION_COMPOSER_DIR,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=300.0
        )

        if process.returncode != 0:
            return {
                "success": False,
                "error": f"Remotion falhou: {stderr.decode()[:500]}",
                "output_path": None,
            }

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"[OpenMontageBridge] Vídeo renderizado: {output_path} ({size_mb:.1f}MB)")
            return {
                "success": True,
                "output_path": output_path,
                "size_mb": round(size_mb, 1),
                "duration_seconds": duration_seconds,
            }
        else:
            return {
                "success": False,
                "error": "Renderização concluída mas arquivo não encontrado.",
                "output_path": None,
            }

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Remotion excedeu o tempo limite de 300 segundos.",
            "output_path": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output_path": None,
        }


# ─── MODO 3: FERRAMENTAS DIRETAS (FALLBACK) ──────────────────────────

async def run_fallback_pipeline(
    script_text: str,
    visual_keywords: List[str],
    voice_path: str,
    output_path: str,
    provider: str = "nvidia",
) -> Dict[str, Any]:
    """
    Pipeline fallback que usa MoviePy + Pexels diretamente
    (sem depender do Remotion/OpenMontage).

    Este modo é usado quando o OpenMontage não está disponível ou
    quando o Remotion falha.
    """
    try:
        # Importa os módulos existentes da Dezafira
        from modules.pexels_client import PexelsClient
        from orchestrator import assemble_video

        pexels = PexelsClient()

        # Baixar clipes do Pexels
        downloaded_clips = []
        if pexels.api_key and visual_keywords:
            for keyword in visual_keywords[:3]:
                clips = pexels.search_and_download(
                    query=keyword,
                    count=2,
                    output_dir=os.path.join(OUTPUTS_DIR, "temp"),
                    orientation="portrait",
                )
                downloaded_clips.extend(clips)

        # Montar vídeo com MoviePy
        if downloaded_clips:
            assemble_video(
                video_path=downloaded_clips[0],
                voice_path=voice_path,
                output_path=output_path,
                add_subtitles=True,
                video_clips=downloaded_clips,
                target_format="vertical",
            )
        else:
            assemble_video(
                video_path=voice_path,  # fallback: só áudio
                voice_path=voice_path,
                output_path=output_path,
                add_subtitles=True,
            )

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            return {
                "success": True,
                "output_path": output_path,
                "size_mb": round(size_mb, 1),
                "mode": "fallback",
            }
        else:
            return {
                "success": False,
                "error": "Falha na montagem do vídeo fallback.",
                "output_path": None,
                "mode": "fallback",
            }

    except Exception as e:
        return {
            "success": False,
            "error": f"Fallback pipeline falhou: {str(e)}",
            "output_path": None,
            "mode": "fallback",
        }


# ─── FUNÇÃO PRINCIPAL ─────────────────────────────────────────────────

async def produce_video(
    task_id: int,
    prompt: str,
    script_text: str,
    visual_keywords: List[str],
    voice_path: str,
    channel_id: str = "default",
    provider: str = "nvidia",
    video_format: str = "vertical",
) -> Dict[str, Any]:
    """
    Função principal de produção de vídeo.

    1. Tenta OpenMontage + Remotion primeiro (modo FULL_PIPELINE)
    2. Se falhar, tenta MoviePy + Pexels (fallback)

    Args:
        task_id: ID da task no banco
        prompt: Tema do vídeo
        script_text: Texto do roteiro
        visual_keywords: Palavras-chave visuais
        voice_path: Caminho do áudio gerado
        channel_id: ID do canal
        provider: 'nvidia' ou 'deepseek'
        video_format: 'vertical' ou 'horizontal'

    Returns:
        Dict com resultado da operação
    """
    project_id = f"task_{task_id}"
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUTS_DIR, "temp"), exist_ok=True)

    output_path = os.path.join(OUTPUTS_DIR, f"{project_id}_preview.mp4")

    print(f"\n[OpenMontageBridge] Produzindo vídeo para task {task_id}")
    print(f"[OpenMontageBridge] Prompt: {prompt}")
    print(f"[OpenMontageBridge] Provider: {provider}")

    # ── TENTATIVA 1: OpenMontage Pipeline ──────────────
    if is_open_montage_available():
        print("[OpenMontageBridge] OpenMontage disponível. Tentando pipeline Remotion...")

        montage_result = await run_open_montage_pipeline(
            prompt=prompt,
            output_path=output_path,
            provider=provider,
            duration_seconds=45,
        )

        if montage_result.get("success"):
            montage_result["mode"] = "open_montage"
            return montage_result

        print(f"[OpenMontageBridge] Remotion falhou: {montage_result.get('error')}")

    # ── TENTATIVA 2: Fallback MoviePy + Pexels ─────────
    print("[OpenMontageBridge] Usando pipeline fallback (MoviePy + Pexels)...")
    return await run_fallback_pipeline(
        script_text=script_text,
        visual_keywords=visual_keywords,
        voice_path=voice_path,
        output_path=output_path,
        provider=provider,
    )


# ─── UTILITÁRIOS ──────────────────────────────────────────────────────

def _find_command(*names: str) -> Optional[str]:
    """Encontra um comando no PATH."""
    import shutil
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    return None


def ensure_output_dirs() -> None:
    """Garante que os diretórios de saída existam."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUTS_DIR, "temp"), exist_ok=True)


if __name__ == "__main__":
    # Teste rápido
    print("=== OpenMontage Bridge - Status ===\n")
    status = get_open_montage_status()
    for k, v in status.items():
        print(f"  {k}: {v}")

    print(f"\nOpenMontage instalado: {status['installed']}")
    print(f"Remotion configurado: {status['remotion_available']}")
