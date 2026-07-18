"""
Audio Mixer — Combinação de Voz + SFX + Música
================================================
Mixa áudio de voz (VoiceBOX) com efeitos sonoros e música de fundo.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

ASSETS_DIR = Path(__file__).parent.parent / "assets"
SFX_DIR = ASSETS_DIR / "sfx"
MUSIC_DIR = ASSETS_DIR / "music"


class AudioMixer:
    """Mixer de áudio para episódios do canal."""

    def __init__(self):
        self.sfx_dir = SFX_DIR
        self.music_dir = MUSIC_DIR

    def get_available_sfx(self) -> List[str]:
        """Lista SFX disponíveis."""
        if not self.sfx_dir.exists():
            return []
        return [f.stem for f in self.sfx_dir.glob("*.mp3")] + \
               [f.stem for f in self.sfx_dir.glob("*.wav")]

    def get_available_music(self) -> List[str]:
        """Lista músicas disponíveis."""
        if not self.music_dir.exists():
            return []
        return [f.stem for f in self.music_dir.rglob("*.mp3")] + \
               [f.stem for f in self.music_dir.rglob("*.wav")]

    def mix_dialogue(
        self,
        voice_path: str,
        output_path: str,
        bgm_track: Optional[str] = None,
        bgm_volume: float = 0.15,
        sfx_events: Optional[List[Dict]] = None,
        fade_in_ms: int = 500,
        fade_out_ms: int = 1000,
    ) -> Optional[str]:
        """Mixa voz com BGM e SFX.

        Args:
            voice_path: Caminho do áudio de voz (WAV/MP3)
            output_path: Caminho de saída
            bgm_track: Nome da faixa de música de fundo
            bgm_volume: Volume do BGM (0.0-1.0, padrão 0.15)
            sfx_events: Lista de {"time": float, "sfx": str, "volume": float}
            fade_in_ms: Fade in no início (ms)
            fade_out_ms: Fade out no final (ms)

        Returns:
            Caminho do áudio mixado ou None
        """
        if not os.path.exists(voice_path):
            print(f"[AudioMixer] Voz não encontrada: {voice_path}")
            return None

        try:
            # Obter duração do áudio de voz
            probe = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", voice_path],
                capture_output=True, text=True
            )
            duration = float(probe.stdout.strip() or "60")

            # Construir filtro FFmpeg
            inputs = ["-i", voice_path]
            filters = []

            # Adicionar BGM se especificado
            if bgm_track:
                bgm_path = self._find_music(bgm_track)
                if bgm_path:
                    inputs.extend(["-i", bgm_path])
                    # BGM: loop, volume baixo, fade in/out
                    filters.append(
                        f"[1:a]aloop=loop=-1:size=2e+09, "
                        f"volume={bgm_volume}, "
                        f"afade=t=in:st=0:d={fade_in_ms/1000}, "
                        f"afade=t=out:st={duration - fade_out_ms/1000}:d={fade_out_ms/1000}, "
                        f"atrim=0:{duration} [bgm]"
                    )

            # Adicionar SFX
            sfx_labels = []
            for i, event in enumerate(sfx_events or []):
                sfx_path = self._find_sfx(event["sfx"])
                if sfx_path:
                    inputs.extend(["-i", sfx_path])
                    vol = event.get("volume", 0.3)
                    t = event.get("time", 0)
                    label = f"sfx{i}"
                    filters.append(
                        f"[{i+1}:a]volume={vol}, "
                        f"adelay={int(t*1000)}|{int(t*1000)} [{label}]"
                    )
                    sfx_labels.append(f"[{label}]")

            # Mixar
            if bgm_track and sfx_labels:
                filters.append(
                    f"[0:a]{sfx_labels[0]} [voice_sfx]"
                )
                mix_inputs = "[voice_sfx][bgm]"
                filters.append(
                    f"{mix_inputs}amix=inputs=2:duration=first:dropout_transition=2 [out]"
                )
            elif bgm_track:
                filters.append(
                    f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2 [out]"
                )
            elif sfx_labels:
                filters.append(
                    f"[0:a]{sfx_labels[0]}amix=inputs=2:duration=first [out]"
                )
            else:
                filters.append(f"[0:a]acopy [out]")

            # Executar FFmpeg
            cmd = [
                "ffmpeg", "-y",
                *inputs,
                "-filter_complex", "; ".join(filters),
                "-map", "[out]",
                "-ar", "24000",
                "-ac", "1",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[AudioMixer] FFmpeg erro: {result.stderr[:300]}")
                return None

            print(f"[AudioMixer] Mixado: {output_path}")
            return output_path

        except Exception as e:
            print(f"[AudioMixer] Erro: {e}")
            return None

    def _find_music(self, name: str) -> Optional[str]:
        """Busca arquivo de música por nome."""
        for ext in [".mp3", ".wav"]:
            path = self.music_dir / f"{name}{ext}"
            if path.exists():
                return str(path)
            # Busca recursiva
            for f in self.music_dir.rglob(f"*{name}*{ext}"):
                return str(f)
        return None

    def _find_sfx(self, name: str) -> Optional[str]:
        """Busca arquivo de SFX por nome."""
        for ext in [".mp3", ".wav"]:
            path = self.sfx_dir / f"{name}{ext}"
            if path.exists():
                return str(path)
            for f in self.sfx_dir.rglob(f"*{name}*{ext}"):
                return str(f)
        return None


# SFX padrão para o canal "Com Jesus na Lua"
JESUS_LUA_SFX = {
    "wind_ambient": "vento_ambiental",
    "fire_crackling": "fogueira",
    "celestial_shimmer": "brilho_celestial",
    "page_turn": "página_biblia",
    "crowd_ancient": "multidão_antiga",
    "thunder": "trovão",
    "water_flow": "água",
    "birds": "pássaros",
}
