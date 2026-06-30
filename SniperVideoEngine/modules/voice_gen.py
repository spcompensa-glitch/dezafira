import asyncio
import edge_tts
import os

async def generate_voice(text, output_path, voice="pt-BR-AntonioNeural"):
    """
    Gera um arquivo de áudio a partir de um texto usando Edge-TTS.
    Fallback para gTTS se houver erro 403 do Edge-TTS no servidor.
    """
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        print(f"Áudio gerado com sucesso via Edge-TTS: {output_path}")
    except Exception as e:
        print(f"[Voice-Gen] ⚠️ Falha no Edge-TTS ({e}). Tentando fallback com gTTS...")
        try:
            from gtts import gTTS
            lang = "pt"
            if "en-" in voice.lower():
                lang = "en"
            elif "es-" in voice.lower():
                lang = "es"
                
            def save_gtts():
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(output_path)
            
            await asyncio.to_thread(save_gtts)
            print(f"[Voice-Gen] Áudio gerado com sucesso via gTTS (Google Fallback): {output_path}")
        except Exception as fallback_err:
            raise Exception(f"Ambos os motores de voz falharam. Edge-TTS: {e} | gTTS: {fallback_err}")

if __name__ == "__main__":
    # Teste rápido
    texto_teste = "Olá! Este é o Sniper Video Engine. Estamos criando vídeos incríveis para o um crípten e para a Otto Pinturas."
    saida = "../outputs/teste_voz.mp3"
    
    # Garantir que a pasta de output existe
    os.makedirs("../outputs", exist_ok=True)
    
    asyncio.run(generate_voice(texto_teste, saida))
