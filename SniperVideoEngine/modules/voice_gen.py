import os
import asyncio
from typing import Optional


async def generate_voice(
    text: str,
    output_path: str,
    voice: str = "pt_br_female1",
    speed: float = 1.0,
) -> str:
    """
    Gera um arquivo de áudio a partir de um texto usando Kokoro TTS.

    Args:
        text: Texto para narração
        output_path: Caminho de saída (WAV ou MP3)
        voice: Voz a usar (ex: 'pt_br_female1', 'pt_br_male1')
        speed: Velocidade da fala (1.0 = normal)

    Returns:
        Caminho do arquivo gerado
    """

    def _generate():
        try:
            from kokoro import KPipeline
            import soundfile as sf

            pipeline = KPipeline(lang_code="p")  # 'p' = Portuguese

            generator = pipeline(text, voice=voice, speed=speed)

            # Se for salvar como MP3, salvar WAV temporário primeiro
            is_mp3 = output_path.lower().endswith(".mp3")
            wav_path = output_path if not is_mp3 else output_path + ".tmp.wav"

            for i, (gs, ps, audio) in enumerate(generator):
                sf.write(wav_path, audio, 24000)

            print(f"[Voice-Kokoro] Audio gerado: {wav_path}")

            # Converter para MP3 se necessário
            if is_mp3:
                try:
                    from pydub import AudioSegment
                    audio_segment = AudioSegment.from_wav(wav_path)
                    audio_segment.export(output_path, format="mp3", bitrate="192k")
                    os.remove(wav_path)  # Remover WAV temporário
                    print(f"[Voice-Kokoro] Convertido para MP3: {output_path}")
                except Exception as e:
                    print(f"[Voice-Kokoro] Erro ao converter MP3 ({e}). Mantendo WAV.")
                    if os.path.exists(wav_path):
                        os.rename(wav_path, output_path)

            return output_path

        except ImportError:
            raise Exception(
                "Kokoro TTS nao instalado. Instale com: pip install kokoro soundfile"
            )
        except Exception as e:
            raise Exception(f"Erro no Kokoro TTS: {e}")

    return await asyncio.to_thread(_generate)


if __name__ == "__main__":
    # Teste rápido
    texto = "Olá! Esta é a Dezafira. Estamos criando vídeos incríveis de forma automática."
    saida = "../outputs/teste_voz.mp3"
    os.makedirs("../outputs", exist_ok=True)
    asyncio.run(generate_voice(texto, saida))
    print(f"Áudio gerado em: {saida}")
