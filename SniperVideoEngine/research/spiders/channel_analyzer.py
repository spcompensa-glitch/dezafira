"""
Channel Analyzer Spider
Analisa canais YouTube em detalhes.
"""
import re
from typing import List, Dict, Any


class ChannelAnalyzerSpider:
    """Spider para análise detalhada de canais YouTube."""

    async def analyze(self, channel_url: str) -> Dict[str, Any]:
        """
        Analisa um canal YouTube.
        
        Args:
            channel_url: URL do canal
            
        Returns:
            Dict com análise completa do canal
        """
        print(f"[ChannelAnalyzer] Analisando: {channel_url}")
        
        try:
            import asyncio
            from services.obscura_client import obscura_client
            print(f"[ChannelAnalyzer] Buscando via Obscura...")
            html = await asyncio.to_thread(obscura_client.fetch_html, channel_url, "networkidle0", 30, True)

            if not html:
                import urllib.request
                print("[ChannelAnalyzer] Obscura vazio, fallback urllib...")
                req = urllib.request.Request(channel_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")

            name_match = re.search(r'"name":"([^"]+)"', html)
            desc_match = re.search(r'"description":"([^"]*)"', html)
            subs_match = re.search(r'"subscriberCountText":\{"simpleText":"([^"]+)"\}', html)
            
            analysis = {
                "url": channel_url,
                "name": name_match.group(1) if name_match else "",
                "description": desc_match.group(1) if desc_match else "",
                "subscribers": subs_match.group(1) if subs_match else "",
                "total_videos": 0,
                "top_videos": [],
                "recent_videos": [],
                "creation_date": "",
                "country": "",
            }
            
            print(f"[ChannelAnalyzer] Canal analisado: {analysis['name']}")
            return analysis
            
        except Exception as e:
            print(f"[ChannelAnalyzer] Erro: {e}")
            return {"url": channel_url, "error": str(e)}

    def _extract_name(self, response) -> str:
        """Extrai nome do canal."""
        name = response.xpath('//yt-formatted-string[@class="style-scope ytd-channel-name"]/text()').get()
        return name.strip() if name else ""

    def _extract_description(self, response) -> str:
        """Extrai descrição do canal."""
        desc = response.xpath('//yt-formatted-string[@id="channel-tagline"]/text()').get()
        return desc.strip() if desc else ""

    def _extract_subscribers(self, response) -> str:
        """Extrai número de inscritos."""
        subs = response.xpath('//yt-formatted-string[@id="subscriber-count"]/text()').get()
        return subs.strip() if subs else ""

    def _extract_total_videos(self, response) -> int:
        """Extrai total de vídeos."""
        count_text = response.xpath('//span[contains(@class,"videos-count")]/span/text()').get()
        if count_text:
            numbers = re.findall(r'\d+', count_text)
            if numbers:
                return int(numbers[0])
        return 0

    def _extract_top_videos(self, response) -> List[Dict[str, Any]]:
        """Extrai vídeos mais populares."""
        videos = []
        items = response.xpath('//ytd-grid-video-renderer')
        
        for item in items[:12]:
            title = item.xpath('.//a[@id="video-title"]/text()').get()
            link = item.xpath('.//a[@id="video-title"]/@href').get()
            views = item.xpath('.//span[@class="inline-metadata-item"]/text()').get()
            
            if title:
                videos.append({
                    "title": title.strip(),
                    "link": f"https://www.youtube.com{link}" if link else "",
                    "views": views.strip() if views else "",
                })
        
        return videos

    def _extract_recent_videos(self, response) -> List[Dict[str, Any]]:
        """Extrai vídeos recentes."""
        return self._extract_top_videos(response)[:6]

    def _extract_creation_date(self, response) -> str:
        """Extrai data de criação do canal."""
        date = response.xpath('//yt-formatted-string[contains(@class,"join-date")]/text()').get()
        return date.strip() if date else ""

    def _extract_country(self, response) -> str:
        """Extrai país do canal."""
        country = response.xpath('//yt-formatted-string[@id="country"]/text()').get()
        return country.strip() if country else ""
