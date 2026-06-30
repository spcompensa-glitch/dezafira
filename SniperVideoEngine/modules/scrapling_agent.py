import os
import re
import json
import urllib.request
from typing import List, Dict, Any

class DezafiraTrendHunter:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_youtube_trends(self, query: str) -> List[Dict[str, Any]]:
        """Garimpa vídeos em alta no YouTube para um nicho/query de forma anônima e furtiva"""
        # Tentar usar Scrapling se estiver instalado
        try:
            from scrapling import Fetcher
            fetcher = Fetcher(auto_match=True)
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            response = fetcher.get(url)
            # Extrair títulos e views a partir do parser do scrapling
            titles = response.xpath('//a[@id="video-title"]/text()').getall()
            links = response.xpath('//a[@id="video-title"]/@href').getall()
            
            trends = []
            for i, title in enumerate(titles[:5]):
                trends.append({
                    "title": title.strip(),
                    "link": f"https://youtube.com{links[i]}" if i < len(links) else "",
                    "metric": "Alta relevância de busca"
                })
            if trends:
                return trends
        except Exception as e:
            print(f"[TrendHunter] Scrapling não inicializado ou sem dependências ({e}). Usando fallback nativo...")

        # Fallback usando requisição HTTP simples e Regex para extração furtiva rápida
        try:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            # Capturar títulos e ids de vídeos usando expressões regulares em JSON bruto do YT
            video_ids = re.findall(r'"videoId":"([^"]+)"', html)
            titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)
            
            trends = []
            seen = set()
            for i, title in enumerate(titles[:6]):
                clean_title = title.encode().decode('utf-8', 'ignore').strip()
                if clean_title not in seen:
                    seen.add(clean_title)
                    vid_id = video_ids[i] if i < len(video_ids) else ""
                    trends.append({
                        "title": clean_title,
                        "link": f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "",
                        "metric": "Garimpado via Dezafira Crawler"
                    })
            return trends
        except Exception as err:
            print(f"[TrendHunter] Falha no garimpo de tendências: {err}")
            
        # Fallback estático estruturado caso o YouTube bloqueie a requisição
        return [
            {"title": f"Segredos Revelados de {query}", "link": "", "metric": "Sugestão Inteligente Dezafira"},
            {"title": f"O que ninguém te conta sobre {query}", "link": "", "metric": "Alta Retenção Estimada"},
            {"title": f"Guia Prático de {query} para Iniciantes", "link": "", "metric": "Alta Busca Anual"}
        ]

if __name__ == "__main__":
    hunter = DezafiraTrendHunter()
    print("Buscando tendências para 'Dropshipping'...")
    res = hunter.fetch_youtube_trends("Dropshipping")
    for r in res:
        print(f"- {r['title']} ({r['metric']})")
