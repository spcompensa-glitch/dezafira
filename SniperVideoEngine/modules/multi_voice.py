"""
Multi-Voice — Geração de voz via VoiceBOX API (Kokoro local)
============================================================
Gera áudio para múltiplos personagens usando VoiceBOX REST API.
Cada personagem tem sua voz Kokoro configurada no VoiceBOX.
"""
import os
import json
import time
import httpx
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

VOICEBOX_URL = os.getenv("VOICEBOX_URL", "http://127.0.0.1:17493")


@dataclass
class VoiceSegment:
    """Segmento de áudio gerado."""
    character_id: str
    text: str
    audio_path: str
    duration_seconds: float
    profile_id: str


class MultiVoiceGenerator:
    """Gerador de voz multi-personagem via VoiceBOX."""

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or Path(__file__).parent.parent / "outputs" / "voices")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profiles = self._load_profiles()

    def _load_profiles(self) -> Dict[str, Dict]:
        """Carrega profiles do VoiceBOX."""
        try:
            resp = httpx.get(f"{VOICEBOX_URL}/api/profiles", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                profiles = {}
                for p in data.get("profiles", []):
                    profiles[p["id"]] = p
                print(f"[MultiVoice] {len(profiles)} profiles carregados do VoiceBOX")
                return profiles
        except Exception as e:
            print(f"[MultiVoice] Aviso: Não foi possível conectar ao VoiceBOX: {e}")
            print("[MultiVoice] Usando profiles padrão do characters.json")

        # Fallback: profiles do characters.json
        return {
            "Adan-Test01": {"id": "Adan-Test01", "engine": "kokoro", "voice": "pm_alex"},
            "Dora PT-BR": {"id": "Dora PT-BR", "engine": "kokoro", "voice": "pf_dora"},
        }

    def generate_line(
        self,
        character_id: str,
        text: str,
        profile_id: str,
        speed: float = 1.0,
        pitch: int = 0,
        output_filename: Optional[str] = None,
    ) -> Optional[str]:
        """Gera áudio para uma fala de personagem.

        Args:
            character_id: ID do personagem (jesus, pedrinho, livia)
            text: Texto para sintetizar
            profile_id: ID do profile no VoiceBOX
            speed: Velocidade (0.5-2.0)
            pitch: Pitch (-20 a 20)
            output_filename: Nome do arquivo de saída

        Returns:
            Caminho do arquivo de áudio ou None
        """
        if not output_filename:
            timestamp = int(time.time() * 1000)
            output_filename = f"{character_id}_{timestamp}.wav"

        output_path = str(self.output_dir / output_filename)

        try:
            payload = {
                "text": text,
                "profileId": profile_id,
                "speed": speed,
                "pitch": pitch,
            }

            print(f"[MultiVoice] Gerando: {character_id} ({profile_id}) -> {text[:50]}...")
            resp = httpx.post(
                f"{VOICEBOX_URL}/api/generate",
                json=payload,
                timeout=60,
            )

            if resp.status_code != 200:
                print(f"[MultiVoice] Erro HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            audio_base64 = data.get("audio")
            duration = data.get("duration", 0)

            if not audio_base64:
                print("[MultiVoice] Resposta sem áudio")
                return None

            # Salvar áudio
            import base64
            audio_bytes = base64.b64decode(audio_base64)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            print(f"[MultiVoice] OK: {output_path} ({duration:.1f}s)")
            return output_path

        except httpx.ConnectError:
            print("[MultiVoice] VoiceBOX não está rodando! Inicie o app VoiceBOX.")
            return None
        except Exception as e:
            print(f"[MultiVoice] Erro: {e}")
            return None

    def generate_dialogue(
        self,
        dialogue_lines: List[Dict],
        character_configs: Dict[str, Dict],
    ) -> List[VoiceSegment]:
        """Gera áudio para todas as falas de um dialogo.

        Args:
            dialogue_lines: Lista de {"character_id": str, "text": str}
            character_configs: Config de voz por personagem:
                {character_id: {"profile_id": str, "speed": float, "pitch": int}}

        Returns:
            Lista de VoiceSegment com áudios gerados
        """
        segments = []

        for i, line in enumerate(dialogue_lines):
            char_id = line["character_id"]
            text = line["text"]
            config = character_configs.get(char_id, {})

            profile_id = config.get("profile_id", "Adan-Test01")
            speed = config.get("speed", 1.0)
            pitch = config.get("pitch", 0)

            filename = f"{char_id}_{i:03d}.wav"
            audio_path = self.generate_line(
                character_id=char_id,
                text=text,
                profile_id=profile_id,
                speed=speed,
                pitch=pitch,
                output_filename=filename,
            )

            if audio_path:
                # Estimar duração (baseado no número de palavras)
                word_count = len(text.split())
                estimated_duration = word_count * 0.4 / speed

                segments.append(VoiceSegment(
                    character_id=char_id,
                    text=text,
                    audio_path=audio_path,
                    duration_seconds=estimated_duration,
                    profile_id=profile_id,
                ))
            else:
                print(f"[MultiVoice] AVISO: Fala {i} falhou ({char_id})")

        return segments

    def concatenate_segments(
        self,
        segments: List[VoiceSegment],
        gap_ms: int = 500,
        output_filename: str = "full_dialogue.wav",
    ) -> Optional[str]:
        """Concatena todos os segmentos em um único áudio.

        Args:
            segments: Lista de VoiceSegment
            gap_ms: Pausa entre falas (milissegundos)
            output_filename: Nome do arquivo final

        Returns:
            Caminho do áudio concatenado ou None
        """
        try:
            import subprocess
            output_path = str(self.output_dir / output_filename)

            # Criar arquivo de lista para ffmpeg
            list_file = self.output_dir / "concat_list.txt"
            silence_file = self.output_dir / "silence.wav"

            # Gerar silêncio
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", f"anullsrc=r=24000:cl=mono",
                "-t", f"{gap_ms / 1000}",
                str(silence_file),
            ], capture_output=True, check=True)

            # Montar lista de concatenação
            with open(list_file, "w") as f:
                for i, seg in enumerate(segments):
                    f.write(f"file '{seg.audio_path}'\n")
                    if i < len(segments) - 1:
                        f.write(f"file '{silence_file}'\n")

            # Concatenar
            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c", "copy", output_path,
            ], capture_output=True, check=True)

            # Limpar temporários
            list_file.unlink(missing_ok=True)
            silence_file.unlink(missing_ok=True)

            print(f"[MultiVoice] Concatenado: {output_path}")
            return output_path

        except Exception as e:
            print(f"[MultiVoice] Erro ao concatenar: {e}")
            return None


# Mapeamento de personagens do canal Jesus na Lua
JESUS_LUA_VOICE_CONFIG = {
    "jesus": {
        "profile_id": "Adan-Test01",
        "speed": 0.85,
        "pitch": 0,
    },
    "pedrinho": {
        "profile_id": "Adan-Test01",
        "speed": 1.1,
        "pitch": 3,
    },
    "livia": {
        "profile_id": "Dora PT-BR",
        "speed": 1.15,
        "pitch": 5,
    },
}
