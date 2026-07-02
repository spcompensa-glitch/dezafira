import os
import re
import json
import time
import urllib.request
import urllib.parse
from typing import List, Dict, Any


class DezafiraTrendHunter:
    """
    Motor principal de Trend Hunting via Scrapling.
    
    Hierarquia de extração:
    1. Scrapling (parser nativo, anti-detecção)
    2. HTTP + Regex (fallback robusto)
    3. Dados estáticos inteligentes (último recurso)
    """

    MAX_RETRIES = 2
    RETRY_DELAY = 1.0

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self._scrapling_available = None  # Cache do status de disponibilidade

    # ─── MÉTODO PRINCIPAL ──────────────────────────────────────────

    def fetch_youtube_trends(self, query: str) -> List[Dict[str, Any]]:
        """
        Busca vídeos em alta no YouTube para um nicho/query.
        
        Retorna lista de dicts: [{title, link, metric, view_count?}]
        """
        query = query.strip()
        if not query:
            print("[TrendHunter] Query vazia. Retornando fallback.")
            return self._static_fallback(query)

        # ── NÍVEL 1: Scrapling (motor principal) ──────────────────
        trends = self._try_scrapling(query)
        if trends:
            return trends

        # ── NÍVEL 2: HTTP + Regex (fallback robusto) ─────────────
        trends = self._try_http_regex(query)
        if trends:
            return trends

        # ── NÍVEL 3: Dados estáticos inteligentes ────────────────
        print("[TrendHunter] Todos os motores falharam. Usando sugestões estáticas.")
        return self._static_fallback(query)

    # ─── NÍVEL 1: SCRAPLING ───────────────────────────────────────

    def _try_scrapling(self, query: str) -> List[Dict[str, Any]]:
        """Tenta extrair tendências usando Scrapling (motor principal)."""
        # Verificar se Scrapling está disponível (cache)
        if self._scrapling_available is False:
            return []

        try:
            from scrapling import Fetcher
            self._scrapling_available = True
        except ImportError:
            self._scrapling_available = False
            print("[TrendHunter] Scrapling não instalado. pip install scrapling")
            return []
        except Exception as e:
            self._scrapling_available = False
            print(f"[TrendHunter] Scrapling indisponível: {e}")
            return []

        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

        for attempt in range(self.MAX_RETRIES):
            try:
                fetcher = Fetcher(auto_match=True)
                response = fetcher.get(url)

                # Extrair títulos
                titles = response.xpath('//a[@id="video-title"]/text()').getall()
                links = response.xpath('//a[@id="video-title"]/@href').getall()

                # Extrair views (se disponíveis)
                views = re.findall(
                    r'"viewCountText":\{"simpleText":"([^"]+)"\}',
                    response.text if hasattr(response, 'text') else '',
                )

                trends = []
                seen = set()
                for i, title in enumerate(titles[:8]):
                    clean_title = title.strip()
                    if not clean_title or clean_title in seen:
                        continue
                    seen.add(clean_title)

                    link = ""
                    if i < len(links):
                        href = links[i]
                        if href.startswith("/watch"):
                            link = f"https://www.youtube.com{href}"

                    view_count = views[i] if i < len(views) else ""

                    trends.append({
                        "title": clean_title,
                        "link": link,
                        "metric": f"Scrapling • {view_count}" if view_count else "Scrapling",
                        "view_count": view_count,
                    })

                if trends:
                    print(f"[TrendHunter] Scrapling: {len(trends)} tendências encontradas")
                    return trends[:5]

            except Exception as e:
                print(f"[TrendHunter] Scrapling tentativa {attempt + 1}/{self.MAX_RETRIES}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        return []

    # ─── NÍVEL 2: HTTP + REGEX ────────────────────────────────────

    def _try_http_regex(self, query: str) -> List[Dict[str, Any]]:
        """Fallback robusto usando HTTP direto + regex."""
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"

        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    html = response.read().decode("utf-8", errors="ignore")

                # Extrair IDs e títulos do JSON embutido do YouTube
                video_ids = re.findall(r'"videoId":"([^"]+)"', html)
                titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)

                # Extrair views
                views = re.findall(r'"viewCountText":\{"simpleText":"([^"]+)"\}', html)

                trends = []
                seen = set()
                for i, title in enumerate(titles[:8]):
                    clean_title = (
                        title.encode("utf-8", "ignore").decode("utf-8").strip()
                    )
                    if not clean_title or clean_title in seen:
                        continue
                    seen.add(clean_title)

                    vid_id = video_ids[i] if i < len(video_ids) else ""
                    link = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""
                    view_count = views[i] if i < len(views) else ""

                    trends.append({
                        "title": clean_title,
                        "link": link,
                        "metric": f"HTTP+Crawler • {view_count}" if view_count else "HTTP+Crawler",
                        "view_count": view_count,
                    })

                if trends:
                    print(f"[TrendHunter] HTTP+Regex: {len(trends)} tendências encontradas")
                    return trends[:5]

            except Exception as e:
                print(f"[TrendHunter] HTTP tentativa {attempt + 1}/{self.MAX_RETRIES}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        return []

    # ─── NÍVEL 3: FALLBACK ESTÁTICO ───────────────────────────────

    def _static_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Gera sugestões inteligentes baseadas no tema."""
        templates = [
            ("Segredos que ninguém te conta sobre {}", "Alta retenção estimada"),
            ("O erro mortal que {} comete todo dia", "Gatilho de curiosidade"),
            ("Como {} está mudando tudo em 2026", "Tendência futura"),
            ("{} explicado em 30 segundos", "Formato Shorts viral"),
            ("Por que {} é mais importante do que você pensa", "Engajamento alto"),
        ]

        trends = []
        for title_tpl, metric in templates:
            title = title_tpl.format(query)
            trends.append({
                "title": title,
                "link": "",
                "metric": f"Dezafira AI • {metric}",
                "view_count": "",
            })

        print(f"[TrendHunter] Sugestões estáticas: {len(trends)} opções geradas")
        return trends


if __name__ == "__main__":
    hunter = DezafiraTrendHunter()
    test_query = "Inteligencia Artificial"
    print("Buscando tendencias para '{}'...\n".format(test_query))
    results = hunter.fetch_youtube_trends(test_query)
    for idx, item in enumerate(results, 1):
        print("  {}. {}".format(idx, item["title"]))
        print("     {}".format(item["metric"]))
        if item.get("link"):
            print("     {}".format(item["link"]))
        print()
