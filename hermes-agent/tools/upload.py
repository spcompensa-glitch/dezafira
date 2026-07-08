#!/usr/bin/env python3
"""
Dezafira Tool: Upload to YouTube
Executado pelo Nous Hermes Agent via Shell.
"""
import sys
import os
import json

sys.path.insert(0, '/app')

def main():
    if len(sys.argv) < 3:
        print("Uso: python upload.py <video_path> <channel_id> [title] [description]")
        print("  video_path: caminho do vídeo")
        print("  channel_id: ID do canal")
        print("  title: título do vídeo (opcional)")
        print("  description: descrição (opcional)")
        sys.exit(1)

    video_path = sys.argv[1]
    channel_id = sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else None
    description = sys.argv[4] if len(sys.argv) > 4 else None

    if not os.path.exists(video_path):
        print(f"[Dezafira] ERRO: Vídeo não encontrado: {video_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[Dezafira] Fazendo upload: {video_path}")
    print(f"[Dezafira] Canal: {channel_id}")

    try:
        from modules.uploader import YouTubeUploader

        uploader = YouTubeUploader()
        result = uploader.upload(
            video_path=video_path,
            channel_id=channel_id,
            title=title,
            description=description,
        )

        print(f"[Dezafira] Upload concluído!")
        output = {
            "success": True,
            "video_path": video_path,
            "channel_id": channel_id,
            "result": str(result)
        }
        print(json.dumps(output))

    except Exception as e:
        print(f"[Dezafira] ERRO: {e}", file=sys.stderr)
        output = {"success": False, "error": str(e)}
        print(json.dumps(output))
        sys.exit(1)

if __name__ == "__main__":
    main()
