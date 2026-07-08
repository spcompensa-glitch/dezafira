import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()
COVERR_API_KEY = os.getenv("COVERR_API_KEY", "")


class CoverrClient:
    """Cliente para API do Coverr — videos stock gratuitos (maioria landscape)."""

    BASE_URL = "https://coverr.co/api/videos"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or COVERR_API_KEY
        if not self.api_key:
            print("[Coverr] AVISO: COVERR_API_KEY nao configurada. Usando sem chave (taxa limitada).")

    def search_videos(
        self,
        query: str,
        count: int = 5,
        orientation: str = "landscape",
        min_duration: int = 5,
        max_duration: int = 30,
    ) -> List[Dict]:
        params = {
            "q": query,
            "per_page": min(count * 2, 30),
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            resp = requests.get(self.BASE_URL, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", data.get("videos", []))
            videos = []
            for v in items:
                duration = v.get("duration", 0)
                if not (min_duration <= duration <= max_duration):
                    continue
                best_url = self._pick_best_url(v, orientation)
                if best_url:
                    videos.append({
                        "id": v.get("id", hash(best_url)),
                        "duration": duration,
                        "width": v.get("width", 1920),
                        "height": v.get("height", 1080),
                        "url": v.get("url", v.get("pageURL", "")),
                        "download_url": best_url,
                        "quality": "hd",
                    })
                if len(videos) >= count:
                    break
            return videos
        except requests.RequestException as e:
            print(f"[Coverr] ERRO na busca: {e}")
            return []

    def download_video(self, video: Dict, output_dir: str = "outputs/temp") -> Optional[str]:
        os.makedirs(output_dir, exist_ok=True)
        download_url = video.get("download_url")
        if not download_url:
            return None
        output_path = os.path.join(output_dir, f"coverr_{video['id']}.mp4")
        if os.path.exists(output_path):
            return output_path
        try:
            print(f"[Coverr] Baixando video {video['id']}...")
            resp = requests.get(download_url, timeout=60, stream=True)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"[Coverr] OK: {output_path} ({size_mb:.1f}MB)")
            return output_path
        except requests.RequestException as e:
            print(f"[Coverr] ERRO ao baixar: {e}")
            return None

    def search_and_download(
        self, query: str, count: int = 3, output_dir: str = "outputs/temp", orientation: str = "landscape"
    ) -> List[str]:
        videos = self.search_videos(query, count=count, orientation=orientation)
        if not videos:
            print(f"[Coverr] Nenhum video para: '{query}'")
            return []
        downloaded = []
        for video in videos:
            path = self.download_video(video, output_dir)
            if path:
                downloaded.append(path)
        return downloaded

    @staticmethod
    def _pick_best_url(video: Dict, orientation: str) -> Optional[str]:
        urls = video.get("urls", video.get("files", []))
        if isinstance(urls, dict):
            candidates = sorted(urls.values(), key=lambda u: abs(len(str(u)) - 50))
            for u in candidates:
                if isinstance(u, str) and u.startswith("http"):
                    return u
            return None
        if isinstance(urls, list):
            for entry in urls:
                if isinstance(entry, dict):
                    url = entry.get("url", "")
                elif isinstance(entry, str):
                    url = entry
                else:
                    continue
                if url and url.startswith("http"):
                    return url
        url = video.get("url", video.get("video_url", ""))
        return url if url.startswith("http") else None
