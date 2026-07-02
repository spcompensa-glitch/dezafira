"""
Dezafira OpenMontage Bridge — Motor Principal de Renderização de Vídeo
======================================================================
Este módulo é o motor OFICIAL de produção de vídeos da Dezafira.

Hierarquia de produção:
  1. OpenMontage + Remotion (motor principal — pipeline completa)
  2. MoviePy + Pexels (fallback garantido — funciona sem OpenMontage)

O bridge detecta automaticamente o OpenMontage e usa-o como prioridade.
"""

import os
import sys
import subprocess
import json
import asyncio
import shutil
from typing import Optional, List, Dict, Any

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

# Cache de disponibilidade (evita checks repetidos no disco)
_om_available_cache: Optional[bool] = None


def is_open_montage_available() -> bool:
    """
    Verifica se o OpenMontage está instalado e funcional.
    Cacheia o resultado para evitar I/O repetido.
    """
    global _om_available_cache
    if _om_available_cache is not None:
        return _om_available_cache

    has_dir = os.path.isdir(OPEN_MONTAGE_DIR)
    has_setup = os.path.isfile(os.path.join(OPEN_MONTAGE_DIR, "setup.py"))
    has_tools = os.path.isdir(TOOLS_DIR)

    _om_available_cache = has_dir and (has_setup or has_tools)

    if _om_available_cache:
        print("[OpenMontage] Motor principal detectado")
    else:
        print("[OpenMontage] Nao detectado - usando MoviePy+Pexels como motor")

    return _om_available_cache


def get_open_montage_status() -> Dict[str, Any]:
    """Retorna o status detalhado da instalação do OpenMontage."""
    available = is_open_montage_available()
    remotion_dir = os.path.join(REMOTION_COMPOSER_DIR, "node_modules")
    has_remotion = os.path.isdir(remotion_dir)
    tools_count = len(os.listdir(TOOLS_DIR)) if os.path.isdir(TOOLS_DIR) else 0

    npx_path = _find_command("npx", "npx.cmd")

    return {
        "installed": available,
        "path": OPEN_MONTAGE_DIR,
        "remotion_available": has_remotion,
        "tools_count": tools_count,
        "npx_available": npx_path is not None,
        "nvidia_configured": bool(os.getenv("NVIDIA_API_KEY")),
        "pexels_configured": bool(os.getenv("PEXELS_API_KEY")),
        "mode": "open_montage" if available and has_remotion else "moviepy_fallback",
    }


# ─── MODO 1: PIPELINE OPENMONTAGE + REMOTION (PRINCIPAL) ──────────────

async def run_open_montage_pipeline(
    prompt: str,
    output_path: str,
    provider: str = "nvidia",
    duration_seconds: int = 45,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Executa a pipeline completa do OpenMontage via Remotion.
    
    Tenta até max_retries vezes antes de declarar falha.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    env = os.environ.copy()
    env["OPEN_MONTAGE_PROVIDER"] = provider

    for attempt in range(max_retries):
        try:
            print(f"[OpenMontage] Tentativa {attempt + 1}/{max_retries}")
            result = await _run_remotion_pipeline(
                prompt=prompt,
                output_path=output_path,
                duration_seconds=duration_seconds,
                provider=provider,
                env=env,
            )
            if result.get("success"):
                return result
            print(f"[OpenMontage] Falha na tentativa {attempt + 1}: {result.get('error')}")
        except Exception as e:
            print(f"[OpenMontage] Erro na tentativa {attempt + 1}: {e}")

    return {
        "success": False,
        "error": f"OpenMontage falhou após {max_retries} tentativas",
        "output_path": None,
    }


async def _run_remotion_pipeline(
    prompt: str,
    output_path: str,
    duration_seconds: int = 45,
    provider: str = "nvidia",
    env: Dict[str, str] = None,
) -> Dict[str, Any]:
    """Renderiza via Remotion (OpenMontage)."""
    env = env or os.environ.copy()

    # Preparar props para o Remotion
    props = {
        "cuts": [
            {
                "durationInFrames": duration_seconds * 30,
                "title": prompt[:60],
                "subtitle": "Gerado pela Dezafira Factory",
                "primaryColor": "#1ed760",
                "backgroundColor": "#0a0a0a",
            }
        ]
    }

    props_path = os.path.join(
        REMOTION_COMPOSER_DIR, "public", "demo-props", "dezafira_props.json"
    )
    os.makedirs(os.path.dirname(props_path), exist_ok=True)
    with open(props_path, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)

    npx_path = _find_command("npx", "npx.cmd", "npx.exe")
    if not npx_path:
        return {
            "success": False,
            "error": "npx não encontrado. Instale Node.js para usar Remotion.",
            "output_path": None,
        }

    cmd = [
        npx_path, "remotion", "render",
        "src/index.tsx", "Explainer",
        str(output_path),
        "--props", str(props_path),
        "--codec", "h264",
    ]

    print(f"[OpenMontage] Executando Remotion: {' '.join(cmd[:5])}...")
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
        error_msg = stderr.decode(errors="ignore")[:500]
        return {
            "success": False,
            "error": f"Remotion retornou código {process.returncode}: {error_msg}",
            "output_path": None,
        }

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print("[OpenMontage] Video renderizado: {} ({:.1f}MB)".format(output_path, size_mb))
        return {
            "success": True,
            "output_path": output_path,
            "size_mb": round(size_mb, 1),
            "duration_seconds": duration_seconds,
        }

    return {
        "success": False,
        "error": "Remotion concluiu mas arquivo não encontrado.",
        "output_path": None,
    }


# ─── MODO 2: FALLBACK MOVIEPY + PEXELS (GARANTIDO) ───────────────────

async def run_fallback_pipeline(
    script_text: str,
    visual_keywords: List[str],
    voice_path: str,
    output_path: str,
    provider: str = "nvidia",
    video_format: str = "vertical",
) -> Dict[str, Any]:
    """
    Pipeline fallback que usa MoviePy + Pexels.
    Funciona sem OpenMontage — é a garantia de que algo sempre será produzido.
    """
    try:
        from modules.pexels_client import PexelsClient
        from orchestrator import assemble_video

        pexels = PexelsClient()
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Baixar clipes do Pexels
        orientation = "portrait" if video_format == "vertical" else "landscape"
        downloaded_clips = []
        if pexels.api_key and visual_keywords:
            for keyword in visual_keywords[:3]:
                clips = pexels.search_and_download(
                    query=keyword,
                    count=2,
                    output_dir=os.path.join(OUTPUTS_DIR, "temp"),
                    orientation=orientation,
                )
                downloaded_clips.extend(clips)
                if len(downloaded_clips) >= 4:
                    break

        print(f"[Fallback] {len(downloaded_clips)} clipes baixados do Pexels")

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
            # Sem clipes — criar vídeo apenas com áudio + legendas
            print("[Fallback] Sem clipes disponíveis. Gerando vídeo com áudio apenas.")
            assemble_video(
                video_path=voice_path,
                voice_path=voice_path,
                output_path=output_path,
                add_subtitles=True,
            )

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print("[Fallback] Video produzido: {} ({:.1f}MB)".format(output_path, size_mb))
            return {
                "success": True,
                "output_path": output_path,
                "size_mb": round(size_mb, 1),
                "mode": "moviepy_fallback",
            }

        return {
            "success": False,
            "error": "Montagem concluída mas arquivo não encontrado.",
            "output_path": None,
            "mode": "moviepy_fallback",
        }

    except Exception as e:
        print("[Fallback] Erro: {}".format(e))
        return {
            "success": False,
            "error": f"Fallback pipeline falhou: {str(e)}",
            "output_path": None,
            "mode": "moviepy_fallback",
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
    
    1. Tenta OpenMontage + Remotion (motor principal)
    2. Se falhar, usa MoviePy + Pexels (fallback garantido)
    """
    project_id = f"task_{task_id}"
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUTS_DIR, "temp"), exist_ok=True)

    output_path = os.path.join(OUTPUTS_DIR, f"{project_id}_preview.mp4")

    print(f"\n{'='*50}")
    print(f"[OpenMontageBridge] Produzindo vídeo para task {task_id}")
    print(f"[OpenMontageBridge] Prompt: {prompt[:60]}...")
    print(f"[OpenMontageBridge] Keywords: {visual_keywords[:3]}")
    print(f"{'='*50}")

    # ── TENTATIVA 1: OpenMontage Pipeline (MOTOR PRINCIPAL) ──────
    if is_open_montage_available():
        print("\n[1/2] Tentando OpenMontage + Remotion...")
        result = await run_open_montage_pipeline(
            prompt=prompt,
            output_path=output_path,
            provider=provider,
            duration_seconds=45,
        )
        if result.get("success"):
            result["mode"] = "open_montage"
            return result
        print("[1/2] OpenMontage falhou: {}".format(result.get('error')))

    # ── TENTATIVA 2: MoviePy + Pexels (FALLBACK GARANTIDO) ──────
    print("\n[2/2] Usando MoviePy + Pexels (fallback)...")
    result = await run_fallback_pipeline(
        script_text=script_text,
        visual_keywords=visual_keywords,
        voice_path=voice_path,
        output_path=output_path,
        provider=provider,
        video_format=video_format,
    )
    return result


# ─── UTILITÁRIOS ──────────────────────────────────────────────────────

def _find_command(*names: str) -> Optional[str]:
    """Encontra um comando no PATH."""
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
    print("=== OpenMontage Bridge — Status ===\n")
    status = get_open_montage_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
    print(f"\nModo ativo: {status['mode']}")
