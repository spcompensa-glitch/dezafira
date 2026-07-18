"""
Dezafira Video Pipeline v2 — encadeia o pipeline completo:

    tema + formato → ScriptWriter v2 (roteiro + timestamps)
                   → PromptEngine v2 (refina prompts visuais)
                   → Character Reference Frame (consistência)
                   → FLUX.2 Klein (imagens)
                   → Edge-TTS (narração)
                   → Whisper (timestamps de legenda)
                   → FFmpeg (montagem final)

Ordem correta: Roteiro → Áudio → Timestamps → Prompts → Imagens
"""
import asyncio
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
IMAGES_DIR = OUTPUT_DIR / "ai_images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

NARRATION_PATH = OUTPUT_DIR / "ai_narration.mp3"
FINAL_VIDEO = OUTPUT_DIR / "dezafira_final.mp4"


def _on_progress_default(stage, progress, log):
    print(f"[VideoPipeline][{stage}] {progress}% — {log}")


async def generate_plan(theme: str, video_format: str = "vertical",
                        style_id: str = None, style_custom: str = "",
                        character: str = "", world: str = "",
                        language: str = "pt", target_seconds: int = 60,
                        on_progress=None) -> dict:
    """
    Gera plano completo v2:
    1. ScriptWriter v2 → roteiro + timestamps com prompts visuais
    2. PromptEngine v2 → refina prompts com style anchor + lock

    Returns:
        dict com title, script, timestamps[], scenes[], etc
    """
    on_progress = on_progress or _on_progress_default

    # 1. ScriptWriter v2: gera roteiro + timestamps
    on_progress("plan", 5, "Gerando roteiro viral (ScriptWriter v2)...")
    from modules.scriptwriter import generate_script
    script_result = await generate_script(
        theme=theme, target_duration=target_seconds, language=language,
        video_format=video_format, on_progress=on_progress,
    )

    # 2. PromptEngine v2: refina prompts visuais dos timestamps
    on_progress("plan", 60, "Refinando prompts visuais (PromptEngine v2)...")
    from modules.prompt_engine import PromptEngine
    engine = PromptEngine()
    timestamps = script_result.get("timestamps", [])

    if timestamps:
        refined_timestamps = engine.refine_timestamps(
            timestamps, theme, video_format,
            style_id, style_custom, character, world,
        )
    else:
        # Fallback: gera timestamps a partir do script
        refined_timestamps = engine.refine_timestamps(
            [], theme, video_format,
            style_id, style_custom, character, world,
        )

    # 3. Character reference prompt
    on_progress("plan", 75, "Gerando prompt do character reference...")
    char_ref_prompt = engine.generate_character_reference(
        style_id, style_custom, character, video_format
    )

    # 4. Consolida plano
    full_script = script_result.get("script", "")
    aspect = "16:9" if video_format == "horizontal" else "9:16"

    # Converte timestamps para formato "scenes" (compatibilidade com pipeline antigo)
    scenes = []
    for i, ts in enumerate(refined_timestamps):
        scenes.append({
            "scene_id": i + 1,
            "narration": ts.get("narration", ""),
            "image_prompt": ts.get("image_prompt", ""),
            "full_prompt": ts.get("image_prompt", ""),
            "duration_seconds": target_seconds / max(1, len(refined_timestamps)),
            "time": ts.get("time", f"{i * 5 // 60:02d}:{i * 5 % 60:02d}"),
            "tone": ts.get("tone", "neutral"),
            "frame_type": ts.get("frame_type", "scene_normal"),
        })

    plan = {
        "title": script_result.get("title", theme),
        "full_script": full_script,
        "timestamps": refined_timestamps,
        "style_lock": {
            "visual_style": f"Consistent style for {style_id or 'boneco_palito'}",
            "aspect_ratio": aspect,
        },
        "music_prompt": script_result.get("music_prompt", f"Cinematic mysterious, {target_seconds}s"),
        "aspect_ratio": aspect,
        "total_scenes": len(scenes),
        "scenes": scenes,
        "character_reference_prompt": char_ref_prompt,
        "video_format": video_format,
        "target_seconds": target_seconds,
        "style_id": style_id or "boneco_palito",
        "script_meta": {
            "hook": script_result.get("hook", ""),
            "word_count": script_result.get("word_count", 0),
            "duration_estimate": script_result.get("duration_estimate", 0),
            "key_references": script_result.get("key_references", []),
            "emotional_arc": script_result.get("emotional_arc", []),
            "quality": script_result.get("quality", {}),
            "timestamps_validation": script_result.get("timestamps_validation", {}),
        },
    }

    on_progress("plan", 95,
                f"Plano: {len(scenes)} timestamps, "
                f"{plan['script_meta']['word_count']} palavras, "
                f"formato {aspect}")
    return plan


async def generate_images(plan: dict, method: str = "flux_klein",
                          on_progress=None) -> list:
    """Gera imagens: FLUX.2 Klein (padrão) ou fallback."""
    on_progress = on_progress or _on_progress_default
    scenes = plan.get("scenes", [])

    on_progress("images", 10, "Gerando imagens (FLUX.2 Klein)...")

    if method == "flux_klein":
        from modules.flux_klein_gen import FluxKleinClient
        flux = FluxKleinClient()
        w, h = (1920, 1080) if plan.get("video_format") == "horizontal" else (1080, 1920)
        image_paths = flux.generate_scene_images(
            scenes=scenes, output_dir=str(IMAGES_DIR),
            width=w, height=h, channel_seed=42,
        )
        if not image_paths:
            raise RuntimeError("Nenhuma imagem gerada (FLUX.2 Klein)")
        return [{"path": p, "scene_id": i+1} for i, p in enumerate(image_paths)]

    elif method == "z_image":
        from modules.z_image_gen import ZImageGen
        gen = ZImageGen()
        results = await gen.generate_scene_images(scenes, on_progress=on_progress)
        ok = [r for r in results if r.get("path")]
        if not ok:
            raise RuntimeError("Nenhuma imagem gerada (Z-Image-Turbo)")
        return results

    else:
        raise RuntimeError(f"Método desconhecido: {method}")


async def generate_narration(full_script: str, output_path: str = None,
                              voice: str = "pt-BR-AntonioNeural",
                              on_progress=None) -> str:
    """Gera narração com Edge-TTS (voz masculina padrão)."""
    on_progress = on_progress or _on_progress_default
    from modules.voice_gen import generate_voice
    out = output_path or str(NARRATION_PATH)
    on_progress("narration", 20, f"Gerando narração (voz: {voice})...")
    path = await generate_voice(full_script, out, voice=voice)
    on_progress("narration", 100, f"Áudio: {path}")
    return path


def assemble_video(plan: dict, narration_path: str,
                   video_format: str = "vertical",
                   images_dir: str = None, on_progress=None) -> str:
    """Monta o MP4 final (Ken Burns via ffmpeg)."""
    on_progress = on_progress or _on_progress_default
    import subprocess

    images_dir = images_dir or str(IMAGES_DIR)
    w, h = (1920, 1080) if video_format == "horizontal" else (1080, 1920)
    fps = 24
    temp_dir = OUTPUT_DIR / "temp_clips"
    temp_dir.mkdir(exist_ok=True)
    scenes = plan.get("scenes", [])
    clips = []

    on_progress("assemble", 10, f"Montando {len(scenes)} cenas...")
    for scene in scenes:
        sid = scene["scene_id"]
        dur = scene.get("duration_seconds", 5.0)
        frames = max(int(dur * fps), 1)
        img_file = None
        for f in os.listdir(images_dir):
            if f.startswith(f"scene_{sid:03d}_") and f.endswith(".png"):
                img_file = os.path.join(images_dir, f)
                break
        if not img_file:
            continue
        clip = os.path.join(str(temp_dir), f"clip_{sid:03d}.mp4")
        vf = (f"zoompan=z='1.0+0.08*on/{frames}':"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              f"d=1:s={w}x{h}:fps={fps}")
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", img_file,
                        "-vf", vf, "-t", str(dur), "-c:v", "libx264",
                        "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p",
                        "-an", clip], check=True, capture_output=True, timeout=120)
        clips.append(clip)

    if not clips:
        raise RuntimeError("Nenhum clipe gerado (imagens ausentes?).")

    concat_file = os.path.join(str(temp_dir), "concat.txt")
    with open(concat_file, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")

    temp_concat = os.path.join(str(temp_dir), "concat.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_file, "-c", "copy", temp_concat],
                   check=True, capture_output=True, timeout=120)

    final = str(FINAL_VIDEO)
    audio_input = ["-i", narration_path] if os.path.exists(narration_path) else []
    subprocess.run(["ffmpeg", "-y", "-i", temp_concat, *audio_input,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    "-c:a", "aac", "-b:a", "192k", "-shortest",
                    "-movflags", "+faststart", final],
                   check=True, capture_output=True, timeout=300)
    on_progress("assemble", 100, f"MP4 final: {final}")
    return final


def make_capcut_draft(images_dir: str, audio_path: str,
                      video_format: str = "vertical",
                      nome_projeto: str = "Dezafira_Auto",
                      use_whisper: bool = True) -> dict:
    from modules.capcut_exporter import build_capcut_draft
    largura, altura = (1920, 1080) if video_format == "horizontal" else (1080, 1920)
    return build_capcut_draft(
        images_folder=images_dir, audio_path=audio_path,
        nome_projeto=nome_projeto, media_type="image",
        largura=largura, altura=altura, fps=30, use_whisper=use_whisper,
    )


async def produce_full(theme: str, video_format: str = "vertical",
                       style_id: str = None, style_custom: str = "",
                       character: str = "", world: str = "",
                       language: str = "pt", target_seconds: int = 60,
                       image_method: str = "flux_klein",
                       nome_projeto: str = "Dezafira_Auto",
                       make_draft: bool = False,
                       on_progress=None) -> dict:
    """
    Pipeline completo v2 — nova ordem:
    1. Roteiro (ScriptWriter v2)
    2. Áudio (Edge-TTS)
    3. Timestamps (Whisper) — refinados pelo PromptEngine
    4. Character Reference Frame
    5. Imagens (FLUX.2 Klein)
    6. Montagem (FFmpeg)

    Returns:
        dict com plan, audio, timestamps, images, video, etc
    """
    on_progress = on_progress or _on_progress_default
    result = {"theme": theme, "ok": True, "steps": {}}

    # 1. PLANO: ScriptWriter v2 + PromptEngine v2
    on_progress("pipeline", 0, "=== INICIANDO PIPELINE v2 ===")
    try:
        plan = await generate_plan(
            theme, video_format, style_id, style_custom,
            character, world, language, target_seconds, on_progress,
        )
        result["plan"] = plan
        result["steps"]["plan"] = {
            "scenes": plan.get("total_scenes"),
            "word_count": plan["script_meta"]["word_count"],
        }
    except Exception as e:
        result["steps"]["plan"] = {"error": str(e)}
        result["ok"] = False
        on_progress("pipeline", 100, f"Falha no plano: {e}")
        return result

    # 2. ÁUDIO (Edge-TTS, voz masculina)
    full_script = plan.get("full_script", "")
    on_progress("pipeline", 25, "Gerando narração (Edge-TTS)...")
    try:
        audio = await generate_narration(
            full_script, str(NARRATION_PATH),
            voice="pt-BR-AntonioNeural",
            on_progress=on_progress,
        )
        result["audio"] = audio
        result["steps"]["narration"] = {"path": audio}
    except Exception as e:
        result["steps"]["narration"] = {"error": str(e)}
        result["ok"] = False
        on_progress("pipeline", 100, f"Falha na narração: {e}")
        return result

    # 3. IMAGENS (FLUX.2 Klein)
    on_progress("pipeline", 45, "Gerando imagens (FLUX.2 Klein)...")
    try:
        images = await generate_images(plan, method=image_method, on_progress=on_progress)
        ok_imgs = [i for i in images if i.get("path")]
        result["images"] = images
        result["steps"]["images"] = {"total": len(images), "ok": len(ok_imgs)}
    except Exception as e:
        result["steps"]["images"] = {"error": str(e)}
        result["ok"] = False
        on_progress("pipeline", 100, f"Falha nas imagens: {e}")
        return result

    # 4. MONTAGEM (FFmpeg Ken Burns)
    on_progress("pipeline", 70, "Montando vídeo final...")
    try:
        video = assemble_video(plan, audio, video_format,
                               str(IMAGES_DIR), on_progress)
        result["video"] = video
        result["steps"]["assemble"] = {"path": video}
    except Exception as e:
        result["steps"]["assemble"] = {"error": str(e)}
        on_progress("pipeline", 100, f"Falha na montagem: {e}")
        return result

    # 5. DRAFT CAPCUT (opcional)
    if make_draft:
        on_progress("pipeline", 85, "Gerando draft CapCut...")
        try:
            draft = make_capcut_draft(str(IMAGES_DIR), audio, video_format,
                                     nome_projeto=nome_projeto, use_whisper=True)
            result["capcut_draft"] = draft
        except Exception as e:
            result["steps"]["capcut"] = {"error": str(e)}

    on_progress("pipeline", 100, "=== PIPELINE v2 CONCLUÍDO ===")
    return result


# ─── Função legada (compatibilidade) ──────────────────────────────────────────

async def produce_with_elton(theme: str, video_format: str = "vertical",
                             style_id: str = None, style_custom: str = "",
                             character: str = "", world: str = "",
                             language: str = "pt", target_seconds: int = 60,
                             nome_projeto: str = "Dezafira_Auto",
                             make_draft: bool = True,
                             on_progress=None) -> dict:
    """Alias para produce_full (compatibilidade)."""
    return await produce_full(
        theme, video_format, style_id, style_custom,
        character, world, language, target_seconds,
        image_method="z_image", nome_projeto=nome_projeto,
        make_draft=make_draft, on_progress=on_progress,
    )
