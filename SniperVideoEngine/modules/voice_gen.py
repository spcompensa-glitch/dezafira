import asyncio
import edge_tts
import os

async def generate_voice(text, output_path, voice="pt-BR-AntonioNeural"):
    """
    Gera um arquivo de áudio a partir de um texto usando Edge-TTS.
    Vozes recomendadas: 
    - pt-BR-AntonioNeural (Masculina)
    - pt-BR-FranciscaNeural (Feminina)
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    print(f"Áudio gerado com sucesso: {output_path}")

if __name__ == "__main__":
    # Teste rápido
    texto_teste = "Olá! Este é o Sniper Video Engine. Estamos criando vídeos incríveis para o um crípten e para a Otto Pinturas."
    saida = "../outputs/teste_voz.mp3"
    
    # Garantir que a pasta de output existe
    os.makedirs("../outputs", exist_ok=True)
    
    asyncio.run(generate_voice(texto_teste, saida))
