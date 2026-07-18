"""
Thumbnail Collector Spider
Coleta thumbnails de vídeos do YouTube.
"""
from typing import List, Dict, Any


class ThumbnailCollectorSpider:
    """Spider para coletar thumbnails de vídeos YouTube."""

    async def collect(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Coleta thumbnails de uma lista de vídeos.
        
        Args:
            videos: Lista de vídeos
            
        Returns:
            Lista de thumbnails coletadas
        """
        print(f"[ThumbnailCollector] Coletando {len(videos)} thumbnails")
        
        thumbnails = []
        
        for video in videos:
            link = video.get("link", "")
            if not link:
                continue
            
            video_id = self._extract_video_id(link)
            if not video_id:
                continue
            
            thumbnail = {
                "video_id": video_id,
                "title": video.get("title", ""),
                "url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                "url_hq": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "url_sd": f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
                "channel": video.get("channel", ""),
                "views": video.get("views", ""),
            }
            thumbnails.append(thumbnail)
        
        print(f"[ThumbnailCollector] {len(thumbnails)} thumbnails coletadas")
        return thumbnails

    def _extract_video_id(self, url: str) -> str:
        """Extrai ID do vídeo da URL."""
        if "v=" in url:
            return url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            return url.split("youtu.be/")[1].split("?")[0]
        return ""
