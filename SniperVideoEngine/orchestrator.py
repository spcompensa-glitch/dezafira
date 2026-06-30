import os
import whisper_timestamped as whisper
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip
except ImportError:
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip

def transcribe_audio_to_words(audio_path):
    """
    Transcreve o áudio e retorna timestamps detalhados palavra por palavra.
    Retorna uma lista de dicionários: [{'word': 'exemplo', 'start': 0.1, 'end': 0.5}]
    """
    print(f"[Orchestrator] Transcrevendo áudio com Whisper local para legendagem: {audio_path}")
    # Usamos o modelo 'tiny' por padrão para ser super leve e rápido no processamento
    model = whisper.load_model("tiny")
    audio = whisper.load_audio(audio_path)
    result = whisper.transcribe(model, audio, language="pt")
    
    words_data = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            words_data.append({
                "word": word_info["text"].strip().upper(), # Legendas em caixa alta para estilo dinâmico
                "start": word_info["start"],
                "end": word_info["end"]
            })
    return words_data

def assemble_video(video_path, voice_path, output_path, music_path=None, music_volume=0.1, add_subtitles=True):
    """
    Une um clip de vídeo com uma narração e, opcionalmente, uma trilha sonora.
    Gera e queima legendas dinâmicas palavra por palavra no vídeo final.
    """
    print(f"[Orchestrator] Iniciando montagem: {video_path}")
    
    # 1. Carregar clips de mídia
    video = VideoFileClip(video_path)
    voice = AudioFileClip(voice_path)
    
    # Ajustar duração do vídeo para bater com a voz
    if video.duration < voice.duration:
        video = video.loop(duration=voice.duration)
    else:
        video = video.with_duration(voice.duration)
    
    # 2. Mesclar faixas de áudio
    audio_tracks = [voice]
    if music_path and os.path.exists(music_path):
        music = AudioFileClip(music_path).with_volume_scaled(music_volume).with_duration(voice.duration)
        audio_tracks.append(music)
    
    final_audio = CompositeAudioClip(audio_tracks)
    video = video.with_audio(final_audio)
    
    # 3. Gerar e queimar legendas dinâmicas (Estilo TikTok/Shorts)
    if add_subtitles:
        try:
            words = transcribe_audio_to_words(voice_path)
            subtitle_clips = []
            
            # Fonte limpa e grossa, ideal para vídeos curtos
            font_to_use = "Arial-Bold"
            
            for w in words:
                word_text = w["word"]
                start_time = w["start"]
                end_time = w["end"]
                
                # Criando um TextClip para cada palavra com sombra preta
                txt_clip = (TextClip(
                    text=word_text,
                    font=font_to_use,
                    font_size=75,
                    color='yellow',       # Texto amarelo chamativo
                    stroke_color='black',  # Contorno preto grosso
                    stroke_width=3,
                    duration=(end_time - start_time)
                )
                .with_start(start_time)
                .with_position(('center', 'center')) # Centralizado na tela
                )
                subtitle_clips.append(txt_clip)
            
            # Se gerou legendas, junta todas por cima do vídeo
            if subtitle_clips:
                print(f"[Orchestrator] Aplicando {len(subtitle_clips)} legendas palavra por palavra no vídeo.")
                video = CompositeVideoClip([video] + subtitle_clips)
        except Exception as e:
            print(f"[Orchestrator] ⚠️ Falha ao gerar legendas dinâmicas: {e}. Gerando vídeo sem legendas.")
            
    # 4. Exportar o vídeo final
    print(f"[Orchestrator] Renderizando vídeo em: {output_path}...")
    video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=24,
        logger='bar' # Mostra progresso no terminal
    )
    print(f"[Orchestrator] Vídeo finalizado com sucesso: {output_path}")

if __name__ == "__main__":
    # Caminhos para teste (ajuste conforme necessário)
    video_teste = "assets/placeholder_video.mp4" 
    voz_teste = "outputs/teste_voz.mp3"
    saida_teste = "outputs/resultado_final.mp4"
    
    if os.path.exists(voz_teste) and os.path.exists(video_teste):
        print("Rodando teste real de união com legendagem dinâmica...")
        assemble_video(video_teste, voz_teste, saida_teste)
    else:
        print("Aviso: Para rodar o teste, garanta que os arquivos 'outputs/teste_voz.mp3' e 'assets/placeholder_video.mp4' existam.")
