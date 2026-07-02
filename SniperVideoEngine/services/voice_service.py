"""
Dezafira Voice Service — Kokoro TTS (Motor Único)
===================================================
Wrapper unificado de geração de voz via Kokoro TTS.

Licença: Apache 2.0
Performance: 3-5x real-time em CPU
Suporte PT-BR: Nativo (lang_code='p')
"""

from typing import List

# Delega toda a lógica para modules/voice_gen.py (única fonte de verdade)
from modules.voice_gen import generate_voice


# ─── UTILITÁRIOS ─────────────────────────────────────────────────────

def get_available_voices() -> List[dict]:
    """Lista as vozes disponíveis do Kokoro para PT-BR."""
    return [
        {"id": "pt_br_female1", "name": "Feminina PT-BR", "engine": "Kokoro"},
        {"id": "pt_br_male1", "name": "Masculina PT-BR", "engine": "Kokoro"},
    ]


if __name__ == "__main__":
    print("=== Teste Voice Service (Kokoro) ===")
    print(f"Vozes: {get_available_voices()}")
