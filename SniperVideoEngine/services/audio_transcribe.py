"""
Audio Transcription — Whisper timestamped (v2)
================================================
Usado para gerar legendas palavra por palavra.
v2.0 — Modelo base para melhor accuracy, normalização de texto.
"""

import re
import whisper_timestamped as whisper


# Modelo Whisper a usar (tiny=rápido, base=balanceado, small=preciso)
WHISPER_MODEL = "base"


def transcribe_audio_to_words(audio_path: str) -> list:
    """
    Transcreve áudio e retorna timestamps palavra por palavra.
    Retorna: [{'word': 'EXEMPLO', 'start': 0.1, 'end': 0.5}]
    """
    print(f"[Transcribe] Transcrevendo: {audio_path} (modelo: {WHISPER_MODEL})")
    model = whisper.load_model(WHISPER_MODEL)
    audio = whisper.load_audio(audio_path)
    result = whisper.transcribe(model, audio, language="pt")

    words_data = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            word = word_info["text"].strip()
            # Normalizar: uppercase, remover pontuação solta
            word_clean = re.sub(r'[^\w\s]', '', word).upper()
            if word_clean:
                words_data.append({
                    "word": word_clean,
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                })

    print(f"[Transcribe] {len(words_data)} palavras transcritas")
    return words_data
