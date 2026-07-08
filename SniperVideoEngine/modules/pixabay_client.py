import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "48872726-ef5a56ef323beb31f5cf81aae")


class PixabayClient:
    """Cliente para API do Pixabay — videos stock gratuitos."""

    BASE_URL = "https://pixabay.com/api/videos"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or PIXABAY_API_KEY
        if not self.api_key:
            print("[Pixabay] AVISO: PIXABAY_API_KEY nao configurada.")

    def search_videos(
        self,
        query: str,
        count: int = 5,
        orientation: str = "vertical",
        min_duration: int = 5,
        max_duration: int = 30,
    ) -> List[Dict]:
        if not self.api_key:
            return []
        params = {
            "q": query,
            "per_page": min(count * 2, 50),
            "safesearch": "true",
        }
        if orientation == "vertical":
            params["min_height"] = 1920
            params["min_width"] = 1080
        else:
            params["min_height"] = 1080
            params["min_width"] = 1920
        try:
            resp = requests.get(self.BASE_URL, params={**params, "key": self.api_key}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", [])
            videos = []
            for v in hits:
                duration = v.get("duration", 0)
                if not (min_duration <= duration <= max_duration):
                    continue
                video_files = v.get("videos", {})
                best = self._pick_best_file(video_files, orientation)
                if best:
                    videos.append({
                        "id": v["id"],
                        "duration": duration,
                        "width": best.get("width", 0),
                        "height": best.get("height", 0),
                        "url": v.get("pageURL", ""),
                        "download_url": best["url"],
                        "quality": best.get("quality", "hd"),
                    })
                if len(videos) >= count:
                    break
            return videos
        except requests.RequestException as e:
            print(f"[Pixabay] ERRO na busca: {e}")
            return []

    def download_video(self, video: Dict, output_dir: str = "outputs/temp") -> Optional[str]:
        os.makedirs(output_dir, exist_ok=True)
        download_url = video.get("download_url")
        if not download_url:
            return None
        output_path = os.path.join(output_dir, f"pixabay_{video['id']}.mp4")
        if os.path.exists(output_path):
            return output_path
        try:
            print(f"[Pixabay] Baixando video {video['id']}...")
            resp = requests.get(download_url, timeout=60, stream=True)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"[Pixabay] OK: {output_path} ({size_mb:.1f}MB)")
            return output_path
        except requests.RequestException as e:
            print(f"[Pixabay] ERRO ao baixar: {e}")
            return None

    def search_and_download(
        self, query: str, count: int = 3, output_dir: str = "outputs/temp", orientation: str = "portrait"
    ) -> List[str]:
        videos = self.search_videos(query, count=count, orientation=orientation)
        if not videos:
            print(f"[Pixabay] Nenhum video para: '{query}'")
            return []
        downloaded = []
        for video in videos:
            path = self.download_video(video, output_dir)
            if path:
                downloaded.append(path)
        return downloaded

    @staticmethod
    def _pick_best_file(video_files: Dict, orientation: str) -> Optional[Dict]:
        candidates = []
        for quality_key in ("large", "medium", "small", "tiny"):
            entry = video_files.get(quality_key)
            if entry and isinstance(entry, dict) and entry.get("url"):
                entry["quality"] = quality_key
                candidates.append(entry)
        if not candidates:
            return None
        if orientation == "vertical":
            vert = [c for c in candidates if c.get("height", 0) > c.get("width", 0)]
            if vert:
                return max(vert, key=lambda f: f.get("height", 0))
        else:
            horiz = [c for c in candidates if c.get("width", 0) >= c.get("height", 0)]
            if horiz:
                return max(horiz, key=lambda f: f.get("width", 0))
        return max(candidates, key=lambda f: f.get("width", 0) * f.get("height", 0))
