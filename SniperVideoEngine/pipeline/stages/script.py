from typing import Dict, Any, Optional


class ScriptStage:
    async def execute(self, theme: str, research_data: Dict[str, Any] = None,
                      channel_id: str = None, video_format: str = "vertical",
                      target_seconds: int = 60, language: str = "pt") -> Dict[str, Any]:
        from modules.scriptwriter import ScriptWriter
        writer = ScriptWriter(channel_id=channel_id or "default")
        result = await writer.write(theme=theme, target_seconds=target_seconds,
                                    video_format=video_format, language=language)
        return result
