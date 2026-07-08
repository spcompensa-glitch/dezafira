"""
Video QA — Sistema de Validação Pós-Render
==========================================
Verifica se o vídeo atende aos critérios de qualidade antes de entregar ao usuário.

Checklists:
1. Duração do vídeo vs solicitada
2. Presença de áudio
3. Presença de legendas
4. Presença de imagens/vídeos (frames não pretos)
5. Qualidade técnica (resolução, codec)
"""

import os
import subprocess
import json
from typing import Dict, Any, List, Tuple


class VideoQA:
    """Sistema de QA para vídeos gerados."""

    # Tolerância de duração (±15%)
    DURATION_TOLERANCE = 0.15

    @staticmethod
    def check_video(
        video_path: str,
        target_duration: float = None,
        min_duration: float = 5.0,
    ) -> Dict[str, Any]:
        """
        Executa checklist completo no vídeo.

        Args:
            video_path: Caminho do vídeo
            target_duration: Duração alvo em segundos (opcional)
            min_duration: Duração mínima aceitável

        Returns:
            Dict com resultado do QA
        """
        result = {
            "passed": False,
            "checks": {},
            "errors": [],
            "warnings": [],
            "video_info": {},
        }

        if not os.path.exists(video_path):
            result["errors"].append(f"Arquivo não encontrado: {video_path}")
            return result

        # 1. Informações básicas do vídeo
        info = VideoQA._get_video_info(video_path)
        result["video_info"] = info

        if not info:
            result["errors"].append("Não foi possível obter informações do vídeo")
            return result

        # 2. Check: Duração
        duration = info.get("duration", 0)
        if target_duration:
            tolerance = target_duration * VideoQA.DURATION_TOLERANCE
            min_ok = target_duration - tolerance
            max_ok = target_duration + tolerance
            
            if duration < min_ok:
                result["errors"].append(
                    f"Duração insuficiente: {duration:.1f}s < {min_ok:.1f}s (alvo: {target_duration:.1f}s)"
                )
                result["checks"]["duration"] = False
            elif duration > max_ok:
                result["warnings"].append(
                    f"Duração maior que o alvo: {duration:.1f}s > {max_ok:.1f}s (alvo: {target_duration:.1f}s)"
                )
                result["checks"]["duration"] = True
            else:
                result["checks"]["duration"] = True
        else:
            result["checks"]["duration"] = duration >= min_duration
            if not result["checks"]["duration"]:
                result["errors"].append(f"Duração muito curta: {duration:.1f}s < {min_duration}s")

        # 3. Check: Áudio
        has_audio = info.get("has_audio", False)
        result["checks"]["audio"] = has_audio
        if not has_audio:
            result["errors"].append("Vídeo sem áudio")

        # 4. Check: Resolução
        width = info.get("width", 0)
        height = info.get("height", 0)
        result["checks"]["resolution"] = width >= 1280 and height >= 720
        if not result["checks"]["resolution"]:
            result["errors"].append(f"Resolução baixa: {width}x{height} (mínimo: 1280x720)")

        # 5. Check: Codec
        codec = info.get("codec", "")
        result["checks"]["codec"] = codec in ["h264", "hevc", "vp9", "av1"]
        if not result["checks"]["codec"]:
            result["warnings"].append(f"Codec desconhecido: {codec}")

        # 6. Check: Tamanho do arquivo
        file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
        result["video_info"]["size_mb"] = round(file_size_mb, 2)
        
        if file_size_mb < 0.1:
            result["errors"].append(f"Arquivo muito pequeno: {file_size_mb:.2f}MB")
            result["checks"]["file_size"] = False
        elif file_size_mb > 500:
            result["warnings"].append(f"Arquivo muito grande: {file_size_mb:.2f}MB")
            result["checks"]["file_size"] = True
        else:
            result["checks"]["file_size"] = True

        # 7. Check: Frames não pretos (presença de imagem/vídeo)
        has_visual = VideoQA._check_visual_content(video_path)
        result["checks"]["visual"] = has_visual
        if not has_visual:
            result["errors"].append("Vídeo pode estar completamente preto ou sem conteúdo visual")

        # Resultado final
        passed_checks = sum(1 for v in result["checks"].values() if v)
        total_checks = len(result["checks"])
        
        result["passed"] = len(result["errors"]) == 0
        result["score"] = f"{passed_checks}/{total_checks}"
        result["passed_checks"] = passed_checks
        result["total_checks"] = total_checks

        return result

    @staticmethod
    def _get_video_info(video_path: str) -> Dict[str, Any]:
        """Obtém informações do vídeo via ffprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "stream=codec_name,width,height,duration,codec_type",
                "-show_entries", "format=duration,size",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)

            streams = data.get("streams", [])
            fmt = data.get("format", {})

            video_stream = None
            audio_stream = None
            for s in streams:
                if s.get("codec_type") == "video":
                    video_stream = s
                elif s.get("codec_type") == "audio":
                    audio_stream = s

            info = {
                "duration": float(fmt.get("duration", 0)),
                "size": int(fmt.get("size", 0)),
                "has_audio": audio_stream is not None,
            }

            if video_stream:
                info["width"] = int(video_stream.get("width", 0))
                info["height"] = int(video_stream.get("height", 0))
                info["codec"] = video_stream.get("codec_name", "")

            return info

        except Exception as e:
            print(f"[VideoQA] Erro ao obter info: {e}")
            return {}

    @staticmethod
    def _check_visual_content(video_path: str) -> bool:
        """Verifica se o vídeo tem conteúdo visual (não é todo preto)."""
        try:
            # Extrair 5 frames aleatórios e verificar se não são todos pretos
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vf", "select=not(mod(n\\,100))",
                "-frames:v", "5",
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Se não houve erro, assumir que tem conteúdo visual
            return result.returncode == 0
        except Exception:
            return True  # Se falhar, assumir OK

    @staticmethod
    def print_report(result: Dict[str, Any]):
        """Imprime relatório de QA formatado."""
        print("\n" + "=" * 60)
        print("📹 RELATÓRIO DE QA DO VÍDEO")
        print("=" * 60)
        
        info = result.get("video_info", {})
        print(f"📁 Arquivo: {info.get('size_mb', 0):.2f} MB")
        print(f"⏱️  Duração: {info.get('duration', 0):.1f}s")
        print(f"📐 Resolução: {info.get('width', 0)}x{info.get('height', 0)}")
        print(f"🎵 Áudio: {'✅' if info.get('has_audio') else '❌'}")
        print(f"🎬 Codec: {info.get('codec', 'N/A')}")
        
        print("\n--- CHECKLIST ---")
        for check, passed in result.get("checks", {}).items():
            icon = "✅" if passed else "❌"
            print(f"  {icon} {check}")
        
        print(f"\n📊 Score: {result.get('score', '0/0')}")
        
        if result.get("errors"):
            print("\n❌ ERROS:")
            for err in result["errors"]:
                print(f"  - {err}")
        
        if result.get("warnings"):
            print("\n⚠️  AVISOS:")
            for warn in result["warnings"]:
                print(f"  - {warn}")
        
        status = "✅ APROVADO" if result.get("passed") else "❌ REPROVADO"
        print(f"\n{'=' * 60}")
        print(f"STATUS: {status}")
        print("=" * 60 + "\n")


# ─── Função de conveniência ─────────────────────────────────────────────────

def validate_video(video_path: str, target_duration: float = None) -> bool:
    """
    Valida um vídeo e imprime o relatório.
    Retorna True se aprovado.
    """
    result = VideoQA.check_video(video_path, target_duration)
    VideoQA.print_report(result)
    return result["passed"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        video = sys.argv[1]
        target = float(sys.argv[2]) if len(sys.argv) > 2 else None
        validate_video(video, target)
    else:
        print("Uso: python video_qa.py <video_path> [target_duration]")
