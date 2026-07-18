"""
Dezafira CapCut Exporter — gera um draft EDITÁVEL do CapCut a partir das imagens
geradas pelo Google Flow (ELTON FLOW) + a narração do pipeline.

Reusa os geradores validados do ELTON VIDEO MAKER (modules.capcut_draft /
capcut_draft_images), que produzem um projeto real abrível no CapCut Desktop
(Windows). O agente de finalização (ETAPA B do plano) só precisa abrir o app,
carregar esse draft e clicar em Export.

Uso:
    from modules.capcut_exporter import build_capcut_draft
    r = build_capcut_draft(images_folder="outputs/ai_images",
                           audio_path="outputs/ai_narration.mp3")
"""
import os
import re
import subprocess
from pathlib import Path

from .capcut_draft_images import criar_draft_imagens

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
VID_EXT = (".mp4", ".mov", ".webm", ".mkv", ".m4v")


def _capcut_drafts_dir(cfg_path: str = "") -> str:
    """Pasta de projetos do CapCut do usuário (portátil entre máquinas)."""
    if cfg_path and os.path.isdir(cfg_path):
        return cfg_path
    local = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")
    candidatos = []
    for raiz in (local, appdata):
        if not raiz:
            continue
        candidatos += [
            os.path.join(raiz, "CapCut", "User Data", "Projects", "com.lveditor.draft"),
            os.path.join(raiz, "JianyingPro", "User Data", "Projects", "com.lveditor.draft"),
        ]
    for c in candidatos:
        if os.path.isdir(c):
            return c
    return ""


def scan_media(folder: str, media_type: str = "image") -> list:
    """
    (ts_segundos, caminho) ordenado. Lê o [MM-SS] do nome do arquivo.
    Variações _1/_2 da mesma cena são colapsadas (mantém a primeira).
    """
    pat = re.compile(r'\[(\d{1,2})-(\d{2})\]')
    suf = re.compile(r'_(\d+)(\.[^.]+)$')
    exts = VID_EXT if media_type == "video" else IMG_EXT
    grupos = {}
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(exts):
            continue
        m = pat.search(f)
        if not m:
            continue
        ts = int(m.group(1)) * 60 + int(m.group(2))
        base = suf.sub(r"\2", f)
        sm = suf.search(f)
        num = int(sm.group(1)) if sm else 0
        key = (ts, base)
        if key not in grupos or num < grupos[key][2]:
            grupos[key] = (ts, os.path.join(folder, f), num)
    res = [(ts, path) for (ts, path, _) in grupos.values()]
    res.sort(key=lambda x: (x[0], os.path.basename(x[1])))
    return res


def audio_duration(path: str) -> float:
    """Duração do áudio em segundos (PyAV; fallback ffmpeg)."""
    try:
        import av
        with av.open(path) as c:
            if c.duration:
                return float(c.duration) / 1_000_000
    except Exception:
        pass
    try:
        proc = subprocess.run(["ffmpeg", "-i", path], capture_output=True, text=True)
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr)
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mi * 60 + s
    except Exception:
        pass
    return 0.0


def transcribe_captions(audio_path: str, model: str = "tiny") -> list:
    """
    Transcreve o áudio e devolve legendas word-level:
    lista de {start, end, text} em SEGUNDOS.

    Usa whisper_timestamped (word-level) se disponível; senão cai no
    whisper padrão (legenda por segmento). Retorna [] se nenhum estiver instalado.
    """
    try:
        import whisper_timestamped as wh  # noqa
        import whisper  # base compartilhada
        audio = whisper.load_audio(audio_path)
        result = wh.transcribe(audio, model=model, verbose=False)
        caps = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                caps.append({
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                    "text": w["word"].strip(),
                })
        if caps:
            return caps
        # fallback: segmentos inteiros
        return [{"start": float(s["start"]), "end": float(s["end"]),
                 "text": s["text"].strip()} for s in result.get("segments", [])]
    except Exception as e:
        print(f"[CapCutExporter] transcribe_captions falhou ({e}); sem legendas.")
        return []


def build_capcut_draft(images_folder: str, audio_path: str,
                       drafts_dir: str = "", nome_projeto: str = "Dezafira_Auto",
                       media_type: str = "image",
                       largura: int = 1080, altura: int = 1920, fps: int = 30,
                       captions: list = None, use_whisper: bool = False) -> dict:
    """
    Gera o draft do CapCut a partir de imagens [MM-SS] + áudio de narração.

    Args:
        images_folder: pasta com as imagens nomeadas cena_XXX_[MM-SS].png
        audio_path: trilha de narração (MP3/WAV)
        drafts_dir: pasta de projetos do CapCut (auto-detectada se vazia)
        nome_projeto: nome da pasta do draft
        media_type: 'image' (padrão) ou 'video'
        largura/altura/fps: dimensões do canvas (default 1080x1920 = Short vertical)
        captions: lista de {start, end, text} em segundos (legendas word-level)
        use_whisper: se True, transcreve o áudio com Whisper p/ gerar as legendas

    Returns:
        {ok, path, scenes, captions, error}
    """
    pasta_drafts = drafts_dir or _capcut_drafts_dir()
    if not pasta_drafts:
        return {"ok": False,
                "error": "Pasta de projetos do CapCut não encontrada. Abra o CapCut ao menos uma vez."}

    midias = scan_media(images_folder, media_type)
    if not midias:
        return {"ok": False,
                "error": f"Nenhuma {media_type} com timestamp [MM-SS] na pasta {images_folder}"}

    if not audio_path or not os.path.isfile(audio_path):
        return {"ok": False, "error": f"Áudio não encontrado: {audio_path}"}

    dur = audio_duration(audio_path)
    if dur <= 0:
        return {"ok": False, "error": "Não consegui ler a duração do áudio."}

    if captions is None and use_whisper:
        captions = transcribe_captions(audio_path)

    try:
        pasta = criar_draft_imagens(
            imagens=midias,
            audio_path=audio_path,
            audio_dur_seg=dur,
            pasta_destino=pasta_drafts,
            nome_projeto=nome_projeto,
            largura=largura,
            altura=altura,
            fps=fps,
            media_type=media_type,
            captions=captions or None,
        )
        return {"ok": True, "path": pasta, "scenes": len(midias),
                "captions": len(captions or []), "drafts_dir": pasta_drafts}
    except Exception as e:
        return {"ok": False, "error": str(e)}
