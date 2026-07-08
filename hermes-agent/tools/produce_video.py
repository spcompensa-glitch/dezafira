#!/usr/bin/env python3
"""
Dezafira Tool: Produce Video
Executado pelo Nous Hermes Agent via Shell.
"""
import sys
import os
import asyncio
import json

# Adicionar path do Dezafira Backend
sys.path.insert(0, '/app')

def main():
    if len(sys.argv) < 2:
        print("Uso: python produce_video.py <theme> [channel_id] [format]")
        print("  theme: tema do vídeo")
        print("  channel_id: ID do canal (default: 'default')")
        print("  format: 'vertical' ou 'horizontal' (default: 'vertical')")
        sys.exit(1)

    theme = sys.argv[1]
    channel_id = sys.argv[2] if len(sys.argv) > 2 else "default"
    video_format = sys.argv[3] if len(sys.argv) > 3 else "vertical"

    print(f"[Dezafira] Iniciando produção: {theme}")
    print(f"[Dezafira] Canal: {channel_id} | Formato: {video_format}")

    try:
        from pipeline.orchestrator import HermesOrchestrator
        from pipeline.websocket import WebSocketHub

        class StubHub:
            async def broadcast(self, event_type, data): pass
            async def send_to_task(self, task_id, event_type, data): pass

        orchestrator = HermesOrchestrator(StubHub())

        # Rodar pipeline
        task_id = asyncio.run(orchestrator.start_pipeline(
            theme=theme,
            channel_id=channel_id,
            video_format=video_format,
        ))

        print(f"[Dezafira] Pipeline iniciada: task_id={task_id}")
        print(f"[Dezafira] Status: running")

        # Resultado para Nous Hermes
        result = {
            "success": True,
            "task_id": task_id,
            "theme": theme,
            "channel_id": channel_id,
            "video_format": video_format,
            "status": "running"
        }
        print(json.dumps(result))

    except Exception as e:
        print(f"[Dezafira] ERRO: {e}", file=sys.stderr)
        result = {"success": False, "error": str(e)}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
