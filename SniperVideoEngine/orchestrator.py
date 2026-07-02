import os
import whisper_timestamped as whisper
try:
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.audio.AudioClip import CompositeAudioClip
        from moviepy.video.VideoClip import CompositeVideoClip, TextClip
    except ImportError:
        from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip, CompositeVideoClip, TextClip

def set_clip_duration(clip, duration):
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)

def set_clip_volume(clip, volume):
    if hasattr(clip, "with_volume_scaled"):
        return clip.with_volume_scaled(volume)
    if hasattr(clip, "volumex"):
        return clip.volumex(volume)
    return clip

def set_clip_audio(clip, audio):
    if hasattr(clip, "with_audio"):
        return clip.with_audio(audio)
    return clip.set_audio(audio)

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

def assemble_video(video_path, voice_path, output_path, music_path=None, music_volume=0.1, add_subtitles=True, video_clips=None, target_format="vertical"):
    """
    Une clips de video com uma narracao e, opcionalmente, uma trilha sonora.
    Gera e queima legendas dinamicas palavra por palavra no video final.

    Args:
        video_path: Caminho do clipe principal de video
        voice_path: Caminho do audio narrado
        output_path: Caminho de saida do MP4
        music_path: Caminho opcional de musica de fundo
        music_volume: Volume da musica (0.0 a 1.0)
        add_subtitles: Se True, gera legendas dinamicas
        video_clips: Lista de caminhos de clips para concatenar (opcional)
    """
    print(f"[Orchestrator] Iniciando montagem")
    
    voice = AudioFileClip(voice_path)
    
    # 1. Montar o video base
    if video_clips and len(video_clips) > 1:
        # Concatenar multiplos clips do Pexels
        print(f"[Orchestrator] Concatenando {len(video_clips)} clips...")
        clips = []
        for clip_path in video_clips:
            try:
                clip = VideoFileClip(clip_path)
                clips.append(clip)
            except Exception as e:
                print(f"[Orchestrator] Aviso: erro ao carregar {clip_path}: {e}")
        
        if clips:
            from moviepy import concatenate_videoclips
            # Redimensionar todos os clips para o formato alvo
            if target_format == "vertical":
                target_w, target_h = 1080, 1920  # 9:16
            else:
                target_w, target_h = 1920, 1080  # 16:9
            
            resized_clips = []
            for clip in clips:
                try:
                    if target_format == "vertical" and clip.w > clip.h:
                        # Landscape -> crop + resize para vertical
                        clip = clip.cropped(x1=(clip.w - clip.h * 9/16) / 2, x2=(clip.w + clip.h * 9/16) / 2)
                        clip = clip.resized(height=target_h)
                    elif target_format == "horizontal" and clip.h > clip.w:
                        # Portrait -> crop + resize para horizontal
                        clip = clip.cropped(y1=(clip.h - clip.w * 9/16) / 2, y2=(clip.h + clip.w * 9/16) / 2)
                        clip = clip.resized(width=target_w)
                    else:
                        # Crop to target aspect ratio, then resize
                        target_ratio = target_w / target_h
                        if clip.w / clip.h > target_ratio:
                            new_w = int(clip.h * target_ratio)
                            clip = clip.cropped(x1=(clip.w - new_w) / 2, x2=(clip.w + new_w) / 2)
                        elif clip.w / clip.h < target_ratio:
                            new_h = int(clip.w / target_ratio)
                            clip = clip.cropped(y1=(clip.h - new_h) / 2, y2=(clip.h + new_h) / 2)
                        clip = clip.resized(width=target_w, height=target_h)
                    resized_clips.append(clip)
                except Exception as e:
                    print("[Orchestrator] Aviso: erro ao redimensionar clip: {}".format(e))
            if resized_clips:
                video = concatenate_videoclips(resized_clips, method="compose")
            else:
                print("[Orchestrator] AVISO: Nenhum clip valido apos redimensionamento")
                video = VideoFileClip(video_path)
        else:
            video = VideoFileClip(video_path)
    else:
        video = VideoFileClip(video_path)
    
    # Ajustar duracao do video para bater com a voz
    if video.duration < voice.duration:
        from moviepy import concatenate_videoclips
        n_repeats = int(voice.duration / video.duration) + 1
        video = concatenate_videoclips([video] * n_repeats)
        video = set_clip_duration(video, voice.duration)
    else:
        video = set_clip_duration(video, voice.duration)
    
    # 2. Mesclar faixas de áudio
    audio_tracks = [voice]
    if music_path and os.path.exists(music_path):
        music = AudioFileClip(music_path)
        music = set_clip_volume(music, music_volume)
        music = set_clip_duration(music, voice.duration)
        audio_tracks.append(music)
    
    final_audio = CompositeAudioClip(audio_tracks)
    video = set_clip_audio(video, final_audio)
    
    # 3. Gerar e queimar legendas dinâmicas (Estilo TikTok/Shorts)
    if add_subtitles:
        try:
            words = transcribe_audio_to_words(voice_path)
            subtitle_clips = []
            
            # Fonte limpa e grossa, ideal para videos curtos
            # Usar caminho absoluto da fonte para compatibilidade com Windows
            font_candidates = [
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf'),
                os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arialbd.ttf'),
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            ]
            font_to_use = 'Arial'
            for fc in font_candidates:
                if os.path.exists(fc):
                    font_to_use = fc
                    break
            
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
            print(f"[Orchestrator] AVISO: Falha ao gerar legendas: {e}. Gerando video sem legendas.")
            
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
