import os
from typing import Dict, Any, Optional


class ProduceStage:
    async def execute(self, script: Dict[str, Any], seo_data: Dict[str, Any] = None,
                      video_format: str = "vertical", channel_id: str = None,
                      task_id: str = None, provider: str = "nvidia") -> Dict[str, Any]:
        from modules.voice_gen import generate_voice
        from services.open_montage_bridge import produce_video

        project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        audio_path = os.path.join(project_dir, "outputs", "temp", f"{task_id}_voice.wav")
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        voice_text = script.get("script", "")
        audio_path = await generate_voice(voice_text, audio_path)

        visual_keywords = script.get("visual_prompts", [script.get("title", "video")])
        if isinstance(visual_keywords, str):
            visual_keywords = [visual_keywords]

        result = await produce_video(
            task_id=hash(task_id) % 100000 if task_id else 0,
            prompt=script.get("title", ""),
            script_text=voice_text,
            visual_keywords=visual_keywords,
            voice_path=audio_path,
            channel_id=channel_id or "default",
            provider=provider,
            video_format=video_format,
        )

        return {
            "success": result.get("success", False),
            "output_path": result.get("output_path"),
            "mode": result.get("mode", "unknown"),
            "size_mb": result.get("size_mb", 0),
            "error": result.get("error"),
            "audio_path": audio_path,
        }
