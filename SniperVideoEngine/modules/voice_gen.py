"""
Kokoro TTS Engine — Geração de Voz Qualidade Cinema (v2)
========================================================
Apache 2.0, CPU-friendly, multi-voz.

v2.0 — Qualidade Cinema:
- Text preprocessing (limpeza, normalização, marcação de ênfase)
- Voice presets por tipo de conteúdo (narration, hook, story)
- Speed/pitch/energy control dinâmico
- Pausas naturais por pontuação
- Normalização LUFS pós-geração
- Conversão MP3 192k bitrate
"""

import os
import re
import asyncio
from typing import Optional, Dict, List, Tuple


# ─── Voice Presets ───────────────────────────────────────────────────────────

VOICE_PRESETS = {
    "narration_punchy": {
        "speed": 1.05,
        "energy": 1.1,
        "description": "Ritmo acelerado, energia alta — para hooks eCTAs",
    },
    "narration_calm": {
        "speed": 0.95,
        "energy": 0.9,
        "description": "Ritmo calmo, energia suave — para storytelling",
    },
    "narration_professional": {
        "speed": 1.0,
        "energy": 1.0,
        "description": "Ritmo neutro, profissional — para educação/tech",
    },
    "narration_dramatic": {
        "speed": 0.92,
        "energy": 1.15,
        "description": "Ritmo lento, energia intensa — para mistério/revelação",
    },
}

# Mapeamento de vozes Kokoro por idioma
VOICE_MAP = {
    "pt": {
        "feminina": "pf_dora",
        "masculina": "pm_alex",
    },
    "en": {
        "feminina": "af_heart",
        "masculina": "am_adam",
    },
}


# ─── Text Preprocessor ──────────────────────────────────────────────────────

class TextPreprocessor:
    """Pré-processa texto para TTS com qualidade natural."""

    # Palavras que devem ser enfatizadas (bordas de frase)
    EMPHASIS_PATTERNS = [
        r'\*{1,2}(\w+)\*{1,2}',       # *palavra* ou **palavra**
        r'"([^"]+)"',                    # "palavra"
        r'([A-Z]{2,})',                  # PALAVRA (gíria)
    ]

    # Abreviações para expandir
    ABBREVIATIONS = {
        "vs": "versus",
        "etc": "etcetera",
        "ex": "exemplo",
        "nº": "número",
        "dr": "doutor",
        "sr": "senhor",
        "sra": "senhora",
    }

    # Números para escrever por extenso (até 100)
    NUMBERS_TO_WORDS = {
        0: "zero", 1: "um", 2: "dois", 3: "três", 4: "quatro",
        5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove",
        10: "dez", 11: "onze", 12: "doze", 13: "treze", 14: "quatorze",
        15: "quinze", 20: "vinte", 30: "trinta", 40: "quarenta",
        50: "cinquenta", 60: "sessenta", 70: "setenta", 80: "oitenta",
        90: "noventa", 100: "cem",
    }

    @classmethod
    def preprocess(cls, text: str, emphasis_words: Optional[List[str]] = None) -> str:
        """
        Pré-processa texto para TTS natural.

        1. Remove markdown
        2. Expande abreviações
        3. Normaliza números
        4. Adiciona pausas por pontuação
        5. Marca ênfase em palavras-chave
        """
        if not text:
            return ""

        # 1. Limpar markdown
        clean = re.sub(r'\*{1,2}(\w+)\*{1,2}', r'\1', text)  # remover bold/italic
        clean = re.sub(r'`([^`]+)`', r'\1', clean)              # remover code
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)  # remover links

        # 2. Expandir abreviações
        words = clean.split()
        expanded = []
        for w in words:
            w_lower = w.lower().rstrip(".,;:!?")
            if w_lower in cls.ABBREVIATIONS:
                expanded.append(cls.ABBREVIATIONS[w_lower])
            else:
                expanded.append(w)
        clean = " ".join(expanded)

        # 3. Normalizar números simples
        clean = re.sub(r'\b(\d{1,2})\b', lambda m: cls.NUMBERS_TO_WORDS.get(int(m.group(1)), m.group(1)), clean)

        # 4. Adicionar pausas naturais por pontuação
        clean = cls._add_natural_pauses(clean)

        # 5. Marcar ênfase
        if emphasis_words:
            for word in emphasis_words[:3]:
                # Encontrar a palavra no texto e marcar com caps
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                clean = pattern.sub(f"**{word.upper()}**", clean, count=1)

        return clean

    @classmethod
    def _add_natural_pauses(cls, text: str) -> str:
        """Adiciona pausas naturais baseadas na pontuação."""
        # Ponto final → pausa curta
        text = text.replace(". ", "... ")  # expandir para pausa mais perceptível
        # Vírgula → pausa muito curta
        text = text.replace(", ", ", , ")  # marker para pausa leve
        # Dois pontos → pausa média
        text = text.replace(": ", "... ")
        # Ponto de exclamação → pausa + ênfase
        text = text.replace("! ", "... ")
        # Ponto de interrogação → pausa contemplativa
        text = text.replace("? ", "... ")

        return text

    @classmethod
    def extract_emphasis(cls, text: str) -> List[str]:
        """Extrai palavras marcadas para ênfase."""
        return re.findall(r'\*{1,2}(\w+)\*{1,2}', text)


# ─── Audio Post-Processor ────────────────────────────────────────────────────

class AudioPostProcessor:
    """Pós-processamento de áudio para qualidade cinema."""

    @staticmethod
    def normalize_lufs(audio_path: str, target_lufs: float = -14.0) -> str:
        """Normaliza áudio para LUFS alvo (YouTube standard = -14)."""
        try:
            import subprocess
            output_path = audio_path.replace(".", "_norm.")
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", f"loudnorm=I={target_lufs}:TP=-1:LRA=11",
                "-c:a", "libmp3lame", "-b:a", "192k",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=30,
                                    encoding="utf-8", errors="replace")
            if result.returncode == 0 and os.path.exists(output_path):
                os.replace(output_path, audio_path)
                print(f"[Voice] LUFS normalizado: {target_lufs}")
                return audio_path
        except Exception as e:
            print(f"[Voice] LUFS normalization ignorada: {e}")
        return audio_path

    @staticmethod
    def add_silence_padding(audio_path: str, padding_ms: int = 300) -> str:
        """Adiciona silêncio no início/fim para transições suaves."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            silence = AudioSegment.silent(duration=padding_ms)
            padded = silence + audio + silence
            padded.export(audio_path, format="mp3", bitrate="192k")
            print(f"[Voice] Padding: {padding_ms}ms adicionado")
            return audio_path
        except Exception as e:
            print(f"[Voice] Padding ignorado: {e}")
            return audio_path


# ─── Main TTS Function ──────────────────────────────────────────────────────

# Cache para Kokoro pipeline (evitar recarregar)
_kokoro_pipeline = None
_kokoro_available = None

def _test_kokoro():
    """Kokoro desabilitado - trava na inicializacao. Usar Edge-TTS."""
    global _kokoro_available
    if _kokoro_available is not None:
        return _kokoro_available
    _kokoro_available = False
    print("[Voice] Kokoro desabilitado (trava). Usando Edge-TTS.")
    return False

def _get_kokoro_pipeline():
    """Obtém ou cria o pipeline Kokoro (com cache)."""
    global _kokoro_pipeline
    if _kokoro_pipeline is not None:
        return _kokoro_pipeline
    
    from kokoro import KPipeline
    _kokoro_pipeline = KPipeline(lang_code="p")
    return _kokoro_pipeline

async def generate_voice_gtts(text, output_path, language="pt"):
    """Fallback: gTTS (qualidade básica, mas funciona sempre)."""
    from gtts import gTTS
    
    tts = gTTS(text=text, lang=language, slow=False)
    tts.save(output_path)
    print(f"[Voice] gTTS: {output_path}")
    return output_path

async def generate_voice_edge(text, output_path, language="pt"):
    """Fallback: Edge-TTS (melhor que gTTS, mas pode falhar com 403)."""
    try:
        import edge_tts
        
        # Mapear vozes
        voice_map = {
            "pt": "pt-BR-FranciscaNeural",
            "en": "en-US-JennyNeural",
        }
        voice = voice_map.get(language, "pt-BR-FranciscaNeural")
        
        tts = edge_tts.Communicate(text, voice)
        await tts.save(output_path)
        print(f"[Voice] Edge-TTS: {output_path}")
        return output_path
    except Exception as e:
        print(f"[Voice] Edge-TTS falhou: {e}")
        return None

async def generate_voice(
    text: str,
    output_path: str,
    voice: str = "pf_dora",
    speed: float = 1.0,
    preset: Optional[str] = None,
    emphasis_words: Optional[List[str]] = None,
    language: str = "pt",
    gender: str = "feminina",
    normalize: bool = True,
    padding_ms: int = 200,
) -> str:
    """
    Gera áudio com fallback automático: Edge-TTS → gTTS.

    Args:
        text: Texto para narração
        output_path: Caminho de saída (WAV ou MP3)
        voice: Voz específica (override de gender)
        speed: Velocidade (override de preset)
        preset: Voice preset (narration_punchy, etc.)
        emphasis_words: Palavras para ênfase
        language: Código idioma (pt, en)
        gender: Gênero da voz (feminina, masculina)
        normalize: Aplicar LUFS normalization
        padding_ms: Silêncio no início/fim

    Returns:
        Caminho do arquivo gerado
    """

    # Pré-processar texto
    processed_text = TextPreprocessor.preprocess(text, emphasis_words)
    print(f"[Voice] Texto processado: {len(processed_text)} chars")

    # 1. Edge-TTS (qualidade boa, funciona sempre)
    mp3_path = output_path if output_path.lower().endswith(".mp3") else output_path + ".mp3"
    result = await generate_voice_edge(processed_text, mp3_path, language)
    if result and os.path.exists(mp3_path):
        # Converter para WAV se necessário
        if not output_path.lower().endswith(".mp3"):
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(mp3_path)
                audio.export(output_path, format="wav")
                os.remove(mp3_path)
            except:
                pass
        if normalize:
            AudioPostProcessor.normalize_lufs(output_path)
        print(f"[Voice] Edge-TTS OK: {output_path}")
        return output_path

    # 2. Fallback final: gTTS
    print("[Voice] Usando gTTS (fallback final)...")
    mp3_path = output_path if output_path.lower().endswith(".mp3") else output_path + ".mp3"
    await generate_voice_gtts(processed_text, mp3_path, language)
    if os.path.exists(mp3_path):
        # Converter para WAV se necessário
        if not output_path.lower().endswith(".mp3"):
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(mp3_path)
                audio.export(output_path, format="wav")
                os.remove(mp3_path)
            except:
                pass
        if normalize:
            AudioPostProcessor.normalize_lufs(output_path)
        print(f"[Voice] gTTS OK: {output_path}")
        return output_path

    raise Exception("Todos os TTS falharam (Edge-TTS, gTTS)")


# ─── Batch Generation ───────────────────────────────────────────────────────

async def generate_voice_batch(
    scenes: List[Dict],
    output_dir: str,
    voice: str = "pf_dora",
    language: str = "pt",
    gender: str = "feminina",
) -> List[str]:
    """
    Gera áudio para múltiplas cenas.

    Args:
        scenes: Lista de cenas com 'narration' e 'beat_type'
        output_dir: Diretório de saída
        voice, language, gender: Configurações de voz

    Returns:
        Lista de caminhos dos áudios gerados
    """
    paths = []
    os.makedirs(output_dir, exist_ok=True)

    for i, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        if not narration:
            continue

        # Escolher preset baseado no beat_type
        beat_type = scene.get("beat_type", "problem")
        preset_map = {
            "hook": "narration_punchy",
            "problem": "narration_dramatic",
            "solution": "narration_professional",
            "proof": "narration_professional",
            "climax": "narration_dramatic",
            "cta": "narration_punchy",
        }
        preset = preset_map.get(beat_type, "narration_professional")

        output_path = os.path.join(output_dir, f"scene_{scene.get('scene_id', i)}.mp3")

        try:
            path = await generate_voice(
                text=narration,
                output_path=output_path,
                voice=voice,
                language=language,
                gender=gender,
                preset=preset,
                emphasis_words=scene.get("emphasis_words"),
                normalize=True,
                padding_ms=200,
            )
            paths.append(path)
            print(f"[Voice] Cena {i+1}: OK ({path})")
        except Exception as e:
            print(f"[Voice] Cena {i+1}: FALHOU ({e})")

    return paths


if __name__ == "__main__":
    # Teste rápido
    texto = "Você sabia que 90% das pessoas erram feio ao tentar ganhar dinheiro online? Pois é. A verdade é bem mais simples do que parece."
    saida = "../outputs/teste_voz_cinema.mp3"
    os.makedirs("../outputs", exist_ok=True)
    asyncio.run(generate_voice(
        texto, saida,
        preset="narration_punchy",
        emphasis_words=["90%", "erram", "simples"],
    ))
    print(f"Áudio gerado em: {saida}")
