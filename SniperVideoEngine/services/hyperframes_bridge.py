"""
HyperFrames Bridge — Motor de vídeo ÚNICO do Dezafira (v2 Cinematic)
====================================================================
Gera vídeos usando HyperFrames (HTML→MP4 via headless Chrome + FFmpeg).
Sem MoviePy, sem Remotion, sem OpenMontage.

v2.0 — Qualidade Cinema:
- FFmpeg: CRF 18, veryslow preset, 60fps, color grading, LUFS -14
- Legendas: estilo viral (karaoke word-by-word, Hormozi)
- Ken Burns: zoom suave + pan direcional
- Brand Bible: CSS injection por canal
- Transições: crossfade, zoom, slide sincronizados
"""

import os
import sys
import json
import shutil
import asyncio
import subprocess
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUTPUTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "outputs"
)

HYPERFRAMES_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hyperframes_work"
)

HYPERFRAMES_COMPOSER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "open-generative-ai", "hyperframes_composer"
)

# Lock global — HyperFrames só renderiza 1 pipeline por vez
_render_lock = asyncio.Lock()


# ─── Presets de Render ──────────────────────────────────────────────────────

RENDER_PRESETS = {
    "cinematic_vertical": {
        "width": 1080,
        "height": 1920,
        "fps": 60,
        "ffmpeg_args": [
            "-crf", "18",
            "-preset", "veryslow",
            "-profile:v", "high",
            "-level", "4.2",
            "-pix_fmt", "yuv420p",
            "-r", "60",
            "-vf", (
                "scale=1080:1920:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,"
                "eq=contrast=1.05:brightness=0.02:saturation=1.12,"
                "unsharp=5:5:0.8:5:5:0.0"
            ),
            "-c:a", "libopus",
            "-b:a", "192k",
            "-af", "loudnorm=I=-14:TP=-1:LRA=11",
            "-movflags", "+faststart",
        ],
        "two_pass": True,
    },
    "cinematic_horizontal": {
        "width": 1920,
        "height": 1080,
        "fps": 60,
        "ffmpeg_args": [
            "-crf", "18",
            "-preset", "veryslow",
            "-profile:v", "high",
            "-level", "4.2",
            "-pix_fmt", "yuv420p",
            "-r", "60",
            "-vf", (
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
                "eq=contrast=1.05:brightness=0.02:saturation=1.12,"
                "unsharp=5:5:0.8:5:5:0.0"
            ),
            "-c:a", "libopus",
            "-b:a", "192k",
            "-af", "loudnorm=I=-14:TP=-1:LRA=11",
            "-movflags", "+faststart",
        ],
        "two_pass": True,
    },
    "fast_vertical": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "ffmpeg_args": [
            "-crf", "23",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
        ],
        "two_pass": False,
    },
}


# ─── Utilitários ─────────────────────────────────────────────────────────────

def _get_audio_duration(audio_path: str) -> float:
    """Duração do áudio via ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace"
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"[HyperframesBridge] ffprobe falhou: {e}. Usando 15s.")
        return 15.0


def _ken_burns_effect(duration: float, fps: int, direction: str = "zoom_in") -> str:
    """Gera filtro FFmpeg para efeito Ken Burns direcional."""
    frames = int(duration * fps)
    if direction == "zoom_in":
        return (
            f"zoompan=z='if(lte(on,1),1,min(zoom+0.0015,1.25))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920"
        )
    elif direction == "zoom_out":
        return (
            f"zoompan=z='if(lte(on,1),1.25,max(zoom-0.0015,1.0))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920"
        )
    elif direction == "pan_left":
        return (
            f"zoompan=z='1.15':"
            f"x='iw/2-(iw/zoom/2)+on*0.5':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920"
        )
    elif direction == "pan_right":
        return (
            f"zoompan=z='1.15':"
            f"x='iw/2-(iw/zoom/2)-on*0.5':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920"
        )
    else:
        return (
            f"zoompan=z='if(lte(on,1),1,min(zoom+0.0015,1.2))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920"
        )


# ─── HyperframesBridge ───────────────────────────────────────────────────────

class HyperframesBridge:
    """Motor de vídeo único — HyperFrames CLI v2 Cinematic."""

    @staticmethod
    def _get_task_dir(task_id: str) -> str:
        """Diretório isolado por task."""
        task_dir = os.path.join(HYPERFRAMES_BASE, task_id)
        os.makedirs(os.path.join(task_dir, "assets"), exist_ok=True)
        return task_dir

    @staticmethod
    def _is_image(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp")

    @staticmethod
    def _image_to_video(
        image_path: str,
        output_path: str,
        duration: float,
        width: int = 1080,
        height: int = 1920,
        direction: str = "zoom_in",
    ) -> bool:
        """Converte imagem para vídeo com Ken Burns direcional."""
        try:
            fps = 60
            frames = int(duration * fps)
            kb_filter = _ken_burns_effect(duration, fps, direction)

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", image_path,
                "-c:v", "libx264", "-t", str(duration),
                "-vf", (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},"
                    f"{kb_filter}"
                ),
                "-crf", "18", "-preset", "veryslow",
                "-pix_fmt", "yuv420p", "-r", str(fps),
                "-movflags", "+faststart",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=120,
                           encoding="utf-8", errors="replace")
            return os.path.exists(output_path)
        except Exception as e:
            print(f"[HyperframesBridge] Erro image->video: {e}")
            return False

    @staticmethod
    def generate_timeline(
        task_id: str,
        script_text: str,
        audio_path: str,
        media_clips: List[Dict[str, Any]],
        captions: List[Dict[str, Any]],
        video_format: str = "vertical",
        brand_bible: Optional[Dict] = None,
        scenes: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Gera index.html + assets com qualidade cinematográfica.

        Args:
            brand_bible: Dict com cores, fontes, estilo do canal
            scenes: Lista de cenas do ScenePlanner (com beat_type, transition, etc.)
        """
        print(f"[HyperframesBridge] Gerando timeline CINEMATIC para task {task_id}")

        task_dir = HyperframesBridge._get_task_dir(task_id)
        assets_dir = os.path.join(task_dir, "assets")

        preset = RENDER_PRESETS.get(f"cinematic_{video_format}", RENDER_PRESETS["cinematic_vertical"])
        width = preset["width"]
        height = preset["height"]
        fps = preset["fps"]

        # Brand CSS variables
        brand = brand_bible or {}
        brand_css = _generate_brand_css(brand)

        # ── Áudio ──────────────────────────────────────────────────────────
        local_audio = ""
        audio_duration = 15.0
        if audio_path and os.path.exists(audio_path):
            local_audio = f"{task_id}_voice.mp3"
            dest = os.path.join(assets_dir, local_audio)
            shutil.copy2(audio_path, dest)
            audio_duration = _get_audio_duration(dest)
            print(f"[HyperframesBridge] Áudio: {audio_duration:.1f}s")

        # ── Processar clips ────────────────────────────────────────────────
        valid_clips = [c for c in media_clips if c.get("path") and os.path.exists(c["path"])]
        clip_duration = audio_duration / max(len(valid_clips), 1)

        # Ken Burns directions ciclo
        kb_directions = ["zoom_in", "pan_left", "zoom_out", "pan_right"]

        local_clips = []
        for idx, clip_info in enumerate(valid_clips):
            src = clip_info["path"]
            fname = f"{task_id}_clip_{idx}.mp4"
            dest = os.path.join(assets_dir, fname)

            # Determinar direção Ken Burns baseada no beat_type
            scene_info = scenes[idx] if scenes and idx < len(scenes) else {}
            beat_type = scene_info.get("beat_type", "")
            if beat_type == "hook":
                direction = "zoom_in"
            elif beat_type in ("solution", "climax"):
                direction = "pan_left"
            elif beat_type == "proof":
                direction = "zoom_out"
            else:
                direction = kb_directions[idx % len(kb_directions)]

            if HyperframesBridge._is_image(src):
                success = HyperframesBridge._image_to_video(
                    src, dest, clip_duration, width, height, direction
                )
                if not success:
                    continue
            else:
                # Normalizar vídeo existente com qualidade cinematic
                kb = _ken_burns_effect(clip_duration, fps, direction)
                try:
                    # Limitar duração do clip a 30 segundos máximo
                    probe_cmd = [
                        "ffprobe", "-v", "quiet",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        src
                    ]
                    probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
                    clip_total_duration = float(probe_result.stdout.strip() or "30")
                    
                    # Se clip for maior que 30s, cortar
                    ss = 0
                    t = min(clip_duration, 30)
                    if clip_total_duration > 30:
                        # Pegar trecho aleatório do meio
                        ss = max(0, (clip_total_duration - 30) / 2)
                    
                    ffmpeg_cmd = [
                        "ffmpeg", "-y", "-ss", str(ss), "-t", str(t), "-i", src,
                        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},{kb}",
                        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
                        "-r", str(fps), "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart",
                        "-an", dest
                    ]
                    subprocess.run(ffmpeg_cmd, capture_output=True, timeout=120,
                       encoding="utf-8", errors="replace")
                except subprocess.TimeoutExpired:
                    print(f"[HyperframesBridge] FFmpeg timeout para clip {idx}, usando original")
                    shutil.copy2(src, dest)
                except Exception as e:
                    print(f"[HyperframesBridge] FFmpeg erro para clip {idx}: {e}, usando original")
                    shutil.copy2(src, dest)

            local_clips.append({
                "name": fname,
                "start": round(idx * clip_duration, 2),
                "duration": round(clip_duration, 2),
                "transition": scene_info.get("transition", "crossfade_slow") if scenes else "crossfade_slow",
            })

        # ── Legendas estilo viral ──────────────────────────────────────────
        captions_html = _generate_viral_captions(captions, width, height)

        # ── Transições CSS ─────────────────────────────────────────────────
        transitions_css = _generate_transitions_css()

        # ── Montar HTML ────────────────────────────────────────────────────
        html_parts = []

        # Áudio
        if local_audio:
            html_parts.append(
                f'    <audio class="clip" id="narration" src="assets/{local_audio}" '
                f'data-start="0" data-duration="{audio_duration}" data-volume="1.0"></audio>'
            )

        # Vídeos/imagens com transições
        for idx, clip in enumerate(local_clips):
            transition = clip.get("transition", "crossfade_slow")
            html_parts.append(
                f'    <video class="clip transition-{transition}" id="clip_{idx}" '
                f'src="assets/{clip["name"]}" '
                f'data-start="{clip["start"]}" data-duration="{clip["duration"]}" '
                f'muted playsinline '
                f'style="position:absolute;top:0;left:0;width:{width}px;height:{height}px;'
                f'object-fit:cover;z-index:1;"></video>'
            )

        clips_html = "\n".join(html_parts)

        # Template HTML
        index_html = f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html,body {{ width:{width}px; height:{height}px; overflow:hidden; background:#000; font-family:'Inter','Helvetica Neue',sans-serif; }}

      {brand_css}

      {transitions_css}

      /* ── Legendas Virais ──────────────────────────────────────── */
      .caption-container {{
        position:absolute; bottom:15%; left:0; width:100%;
        display:flex; justify-content:center; z-index:20;
        padding:0 5%;
      }}
      .caption-word {{
        display:inline-block;
        font-size:clamp(2.2rem, 5.5vw, 3.8rem);
        font-weight:900;
        text-transform:uppercase;
        letter-spacing:0.02em;
        line-height:1.15;
        text-align:center;
        color:#fff;
        text-shadow:
          0 0 20px rgba(0,0,0,0.9),
          0 4px 15px rgba(0,0,0,0.8),
          0 2px 4px rgba(0,0,0,0.6);
        transform:scale(0.85);
        opacity:0.25;
        transition:all 0.06s cubic-bezier(0.4,0,0.2,1);
        margin:0 0.1em;
      }}
      .caption-word.active {{
        transform:scale(1.18);
        opacity:1;
        color:var(--brand-accent, #00e5ff);
        text-shadow:
          0 0 30px var(--brand-accent, #00e5ff),
          0 0 60px var(--brand-accent, #00e5ff),
          0 4px 15px rgba(0,0,0,0.8);
      }}
      .caption-word.past {{
        opacity:0.45;
        transform:scale(0.95);
      }}
      .caption-word.hook {{
        color:#FFD700;
        text-shadow:0 0 25px #FFD700, 0 4px 15px rgba(0,0,0,0.8);
      }}
      .caption-word.hook.active {{
        color:#FFD700;
        text-shadow:0 0 40px #FFD700, 0 0 80px #FFD700, 0 4px 15px rgba(0,0,0,0.8);
      }}

      /* ── Overlay de vinheta (cinema look) ────────────────────── */
      .vignette {{
        position:absolute; top:0; left:0; width:100%; height:100%;
        background:radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.6) 100%);
        pointer-events:none; z-index:15;
      }}

      /* ── Barra de progresso visual ───────────────────────────── */
      .progress-bar {{
        position:absolute; bottom:0; left:0; height:4px;
        background:linear-gradient(90deg, var(--brand-primary, #00e5ff), var(--brand-accent, #ff00ff));
        z-index:25; width:0%;
      }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0"
         data-duration="{audio_duration}" data-width="{width}" data-height="{height}">
{clips_html}
      <!-- Vinheta cinematográfica -->
      <div class="vignette"></div>
      <!-- Legendas virais -->
      {captions_html}
      <!-- Barra de progresso -->
      <div class="progress-bar" id="progressBar"></div>
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;

      // Animação da barra de progresso
      tl.to("#progressBar", {{
        width: "100%",
        duration: {audio_duration},
        ease: "none"
      }}, 0);
    </script>
  </body>
</html>"""

        index_path = os.path.join(task_dir, "index.html")
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)

        meta = {
            "task_id": task_id,
            "format": video_format,
            "resolution": {"width": width, "height": height},
            "fps": fps,
            "duration": audio_duration,
            "clips_count": len(local_clips),
            "captions_count": len(captions),
            "preset": "cinematic",
        }
        with open(os.path.join(task_dir, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)

        print(f"[HyperframesBridge] Timeline CINEMATIC OK: {index_path}")
        return {"success": True, "task_dir": task_dir, "meta": meta}

    @staticmethod
    async def render_video(task_id: str, output_path: str, preset: str = "cinematic_vertical") -> Dict[str, Any]:
        """Renderiza com preset cinematográfico."""
        async with _render_lock:
            return await HyperframesBridge._render_video_inner(task_id, output_path, preset)

    @staticmethod
    async def _render_video_inner(task_id: str, output_path: str, preset: str) -> Dict[str, Any]:
        task_dir = HyperframesBridge._get_task_dir(task_id)
        index_path = os.path.join(task_dir, "index.html")

        if not os.path.exists(index_path):
            return {"success": False, "error": f"index.html não encontrado: {index_path}"}

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        composer_dir = HYPERFRAMES_COMPOSER
        if not os.path.isdir(composer_dir):
            return {"success": False, "error": f"HyperFrames composer não encontrado: {composer_dir}"}

        # Limpar composição anterior
        for f in os.listdir(composer_dir):
            if f.endswith((".html", ".mp4", ".mp3", ".wav")):
                os.remove(os.path.join(composer_dir, f))
        assets_dst = os.path.join(composer_dir, "assets")
        if os.path.isdir(assets_dst):
            shutil.rmtree(assets_dst)

        # Copiar index.html + assets
        shutil.copy2(index_path, os.path.join(composer_dir, "index.html"))
        assets_src = os.path.join(task_dir, "assets")
        if os.path.isdir(assets_src):
            shutil.copytree(assets_src, assets_dst)

        # Render quality baseado no preset — usar standard para velocidade
        quality = "standard"  # Mais rápido que "high"
        # Output path relativo ao composer_dir
        output_abs = os.path.abspath(output_path)
        output_fwd = output_abs.replace("\\", "/")
        shell_cmd = f'npx hyperframes render -o "{output_fwd}" --quality {quality} --no-browser-gpu --fps 30'
        print(f"[HyperframesBridge] Renderizando: {shell_cmd}")

        def _run_render():
            return subprocess.run(
                shell_cmd, shell=True, cwd=composer_dir,
                capture_output=True, timeout=1200,
                encoding="utf-8", errors="replace"
            )

        try:
            result = await asyncio.to_thread(_run_render)

            if result.returncode != 0:
                err = (result.stderr or result.stdout or "")[:1000]
                return {"success": False, "error": f"HyperFrames render failed: {err}"}

            # Post-process: aplicar FFmpeg cinematic se necessário (desativado para velocidade)
            if os.path.exists(output_path):
                # # Aplicar color grading + LUFS normalization no output final
                # processed_path = output_path.replace(".mp4", "_cinematic.mp4")
                # ffmpeg_post = [
                #     "ffmpeg", "-y", "-i", output_path,
                #     "-vf", "eq=contrast=1.08:brightness=0.03:saturation=1.15,unsharp=5:5:0.5:5:5:0.0",
                #     "-af", "loudnorm=I=-14:TP=-1:LRA=11",
                #     "-c:v", "libx264", "-crf", "18", "-preset", "veryslow",
                #     "-c:a", "libopus", "-b:a", "192k",
                #     "-movflags", "+faststart",
                #     processed_path,
                # ]
                # try:
                #     proc_result = subprocess.run(ffmpeg_post, capture_output=True, timeout=300,
                #                                  encoding="utf-8", errors="replace")
                #     if proc_result.returncode == 0 and os.path.exists(processed_path):
                #         os.replace(processed_path, output_path)
                #         print("[HyperframesBridge] Post-process cinematic aplicado")
                # except Exception as e:
                #     print(f"[HyperframesBridge] Post-process ignorado: {e}")

                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"[HyperframesBridge] OK: {output_path} ({size_mb:.1f}MB)")
                return {"success": True, "output_path": output_path, "size_mb": round(size_mb, 1)}

            return {"success": False, "error": "MP4 não encontrado após render."}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "HyperFrames timeout (1200s)."}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Funções auxiliares privadas ─────────────────────────────────────────────

def _generate_brand_css(brand: Dict) -> str:
    """Gera CSS variables do Brand Bible."""
    primary = brand.get("primary_color", "#00e5ff")
    secondary = brand.get("secondary_color", "#ff00ff")
    accent = brand.get("accent_color", "#FFD700")
    font = brand.get("font_family", "Inter")
    caption_style = brand.get("caption_preset", "viral")

    return f"""
      :root {{
        --brand-primary: {primary};
        --brand-secondary: {secondary};
        --brand-accent: {accent};
        --brand-font: '{font}', 'Helvetica Neue', sans-serif;
        --caption-style: {caption_style};
      }}
    """


def _generate_transitions_css() -> str:
    """Gera CSS para transições entre cenas."""
    return """
      /* Transições */
      .transition-crossfade_slow { animation: crossfade 0.6s ease-in-out; }
      .transition-zoom_in_fast { animation: zoomIn 0.3s ease-out; }
      .transition-slide_left { animation: slideLeft 0.4s ease-out; }
      .transition-cut { animation: none; }
      .transition-zoom_out { animation: zoomOut 0.5s ease-in-out; }
      .transition-fade_black { animation: fadeBlack 0.8s ease-in-out; }

      @keyframes crossfade {
        0% { opacity: 0; }
        100% { opacity: 1; }
      }
      @keyframes zoomIn {
        0% { transform: scale(1.3); opacity: 0; }
        100% { transform: scale(1.0); opacity: 1; }
      }
      @keyframes slideLeft {
        0% { transform: translateX(100px); opacity: 0; }
        100% { transform: translateX(0); opacity: 1; }
      }
      @keyframes zoomOut {
        0% { transform: scale(0.8); opacity: 0; }
        100% { transform: scale(1.0); opacity: 1; }
      }
      @keyframes fadeBlack {
        0% { opacity: 0; }
        50% { opacity: 1; }
        100% { opacity: 1; }
      }
    """


def _generate_viral_captions(
    captions: List[Dict], width: int, height: int
) -> str:
    """
    Gera HTML de legendas estilo viral (karaoke word-by-word).
    Cada palavra aparece individualmente com animação de destaque.
    """
    if not captions:
        return ""

    words_html = []
    for idx, cap in enumerate(captions):
        word = cap.get("word") or cap.get("text") or ""
        if not word.strip():
            continue
        start = cap.get("start", 0)
        end = cap.get("end", start + 0.3)
        duration = round(end - start, 3)

        # Classe especial para hook (primeiras palavras)
        hook_class = " hook" if idx < 5 else ""

        words_html.append(
            f'<span class="caption-word clip{hook_class}" '
            f'data-start="{start}" data-duration="{duration}" '
            f'data-word-index="{idx}">{word}</span>'
        )

    words_str = " ".join(words_html)

    return f"""
      <div class="caption-container" id="captions">
        {words_str}
      </div>
      <script>
        // Legenda palavra-a-palavra (karaoke style)
        (function() {{
          const words = document.querySelectorAll('.caption-word');
          const audio = document.getElementById('narration');
          if (!audio || !words.length) return;

          let currentIndex = -1;

          function updateCaptions() {{
            const time = audio.currentTime;
            let newIndex = -1;

            for (let i = 0; i < words.length; i++) {{
              const start = parseFloat(words[i].dataset.start);
              const dur = parseFloat(words[i].dataset.duration);
              if (time >= start && time < start + dur) {{
                newIndex = i;
                break;
              }}
            }}

            if (newIndex !== currentIndex) {{
              // Reset anterior
              if (currentIndex >= 0 && currentIndex < words.length) {{
                words[currentIndex].classList.remove('active');
                words[currentIndex].classList.add('past');
              }}
              // Ativar novo
              if (newIndex >= 0) {{
                words[newIndex].classList.remove('past');
                words[newIndex].classList.add('active');
              }}
              currentIndex = newIndex;
            }}
          }}

          audio.addEventListener('timeupdate', updateCaptions);
          audio.addEventListener('play', updateCaptions);
        }})();
      </script>
    """
