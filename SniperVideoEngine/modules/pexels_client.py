import os
import requests
from typing import List, Dict, Optional

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")


class PexelsClient:
    """Cliente para a API do Pexels - busca e download de videos stock verticais."""

    BASE_URL = "https://api.pexels.com/v1/videos/search"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or PEXELS_API_KEY
        if not self.api_key:
            print("[Pexels] AVISO: PEXELS_API_KEY nao configurada. Videos stock indisponiveis.")

    def search_videos(
        self,
        query: str,
        count: int = 5,
        orientation: str = "portrait",
        min_width: int = 1080,
        min_duration: int = 5,
        max_duration: int = 30,
    ) -> List[Dict]:
        """Busca videos verticais no Pexels."""
        if not self.api_key:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": min(count * 2, 15),
            "min_width": min_width,
        }

        try:
            response = requests.get(self.BASE_URL, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            videos = []
            for v in data.get("videos", []):
                duration = v.get("duration", 0)
                if min_duration <= duration <= max_duration:
                    best_file = self._pick_best_file(v.get("video_files", []))
                    if best_file:
                        videos.append(
                            {
                                "id": v["id"],
                                "duration": duration,
                                "width": v.get("width", 0),
                                "height": v.get("height", 0),
                                "url": v.get("url", ""),
                                "download_url": best_file["link"],
                                "quality": best_file.get("quality", "hd"),
                                "file_width": best_file.get("width", 0),
                                "file_height": best_file.get("height", 0),
                            }
                        )

                if len(videos) >= count:
                    break

            return videos

        except requests.RequestException as e:
            print("[Pexels] ERRO na busca: {}".format(e))
            return []

    def download_video(self, video: Dict, output_dir: str = "outputs/temp") -> Optional[str]:
        """Baixa um video do Pexels."""
        os.makedirs(output_dir, exist_ok=True)

        download_url = video.get("download_url")
        if not download_url:
            return None

        output_path = os.path.join(output_dir, "stock_{}.mp4".format(video["id"]))

        if os.path.exists(output_path):
            return output_path

        try:
            print("[Pexels] Baixando video {}...".format(video["id"]))
            response = requests.get(download_url, timeout=60, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print("[Pexels] OK baixado: {} ({:.1f}MB)".format(output_path, file_size_mb))
            return output_path

        except requests.RequestException as e:
            print("[Pexels] ERRO ao baixar: {}".format(e))
            return None

    def search_and_download(
        self, query: str, count: int = 3, output_dir: str = "outputs/temp", orientation: str = "portrait"
    ) -> List[str]:
        """Busca e baixa videos de uma so vez.
        
        Args:
            query: Termo de busca
            count: Numero de videos
            output_dir: Diretorio de destino
            orientation: 'portrait' (9:16), 'landscape' (16:9), ou 'any'
        """
        videos = self.search_videos(query, count=count, orientation=orientation)
        if not videos:
            print("[Pexels] Nenhum video encontrado para: '{}'".format(query))
            return []

        downloaded = []
        for video in videos:
            path = self.download_video(video, output_dir)
            if path:
                downloaded.append(path)

        return downloaded

    def _pick_best_file(self, video_files: List[Dict]) -> Optional[Dict]:
        """Seleciona o melhor arquivo de video (prioriza HD e resolucao vertical)."""
        if not video_files:
            return None

        candidates = [
            f for f in video_files
            if f.get("quality") in ("hd", "sd") and f.get("width", 0) >= 720
        ]

        if not candidates:
            candidates = video_files

        hd_files = [f for f in candidates if f.get("quality") == "hd"]
        if hd_files:
            return max(hd_files, key=lambda f: f.get("width", 0) * f.get("height", 0))

        return max(candidates, key=lambda f: f.get("width", 0) * f.get("height", 0))


pexels = PexelsClient()


if __name__ == "__main__":
    client = PexelsClient()
    videos = client.search_videos("technology abstract", count=3)
    for v in videos:
        print("  ID: {} | {}s | {}x{} | {}".format(v["id"], v["duration"], v["file_width"], v["file_height"], v["quality"]))
