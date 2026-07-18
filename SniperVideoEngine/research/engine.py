"""
Dezafira Research Engine
Motor principal de pesquisa para canais YouTube lucrativos.
"""
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .spiders import (
    YouTubeSearchSpider,
    ChannelAnalyzerSpider,
    VideoAnalyzerSpider,
    TrendingTrackerSpider,
    ThumbnailCollectorSpider,
    CommentAnalyzerSpider,
    YouTubeDocsSpider,
)
from .analyzers import (
    NicheAnalyzer,
    TitleAnalyzer,
    ThumbnailAnalyzer,
    EngagementAnalyzer,
    SEOAnalyzer,
)


@dataclass
class ResearchResult:
    """Resultado de uma pesquisa completa."""
    niche: str
    channels: List[Dict[str, Any]] = field(default_factory=list)
    trending_videos: List[Dict[str, Any]] = field(default_factory=list)
    title_patterns: List[str] = field(default_factory=list)
    thumbnail_patterns: Dict[str, Any] = field(default_factory=dict)
    seo_insights: Dict[str, Any] = field(default_factory=dict)
    competitor_analysis: List[Dict[str, Any]] = field(default_factory=list)
    niche_score: float = 0.0
    competition_level: str = "unknown"
    monetization_potential: str = "unknown"
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ResearchEngine:
    """
    Motor principal de pesquisa para identificar nichos lucrativos
    e padrões de sucesso no YouTube.
    """

    def __init__(self):
        self.youtube_search = YouTubeSearchSpider()
        self.channel_analyzer = ChannelAnalyzerSpider()
        self.video_analyzer = VideoAnalyzerSpider()
        self.trending_tracker = TrendingTrackerSpider()
        self.thumbnail_collector = ThumbnailCollectorSpider()
        self.comment_analyzer = CommentAnalyzerSpider()
        self.youtube_docs = YouTubeDocsSpider()

        self.niche_analyzer = NicheAnalyzer()
        self.title_analyzer = TitleAnalyzer()
        self.thumbnail_analyzer = ThumbnailAnalyzer()
        self.engagement_analyzer = EngagementAnalyzer()
        self.seo_analyzer = SEOAnalyzer()

    async def research_niche(self, keyword: str) -> ResearchResult:
        """
        Realiza pesquisa completa de um nicho.
        
        Args:
            keyword: Palavra-chave ou nicho para pesquisar
            
        Returns:
            ResearchResult com todos os dados coletados e analisados
        """
        print(f"[ResearchEngine] Iniciando pesquisa para: {keyword}")

        result = ResearchResult(niche=keyword)

        # Fase 1: Coleta de dados
        print(f"[ResearchEngine] Fase 1: Coleta de dados...")
        
        trending_videos = await self.trending_tracker.track(keyword)
        result.trending_videos = trending_videos

        channels = await self.youtube_search.search(f"{keyword} canal")
        result.channels = channels

        # Fase 2: Análise de concorrentes
        print(f"[ResearchEngine] Fase 2: Análise de concorrentes...")
        
        if channels:
            top_channels = channels[:5]
            for channel_data in top_channels:
                channel_url = channel_data.get("channel_url", "")
                if channel_url:
                    analysis = await self.channel_analyzer.analyze(channel_url)
                    result.competitor_analysis.append(analysis)

        # Fase 3: Análise de padrões
        print(f"[ResearchEngine] Fase 3: Análise de padrões...")
        
        result.title_patterns = self.title_analyzer.extract_patterns(
            [v.get("title", "") for v in trending_videos]
        )

        thumbnails = await self.thumbnail_collector.collect(trending_videos)
        result.thumbnail_patterns = self.thumbnail_analyzer.analyze(thumbnails)

        result.seo_insights = await self.seo_analyzer.analyze(trending_videos)

        # Fase 4: Análise de nicho
        print(f"[ResearchEngine] Fase 4: Análise de nicho...")
        
        niche_analysis = self.niche_analyzer.analyze({
            "videos": trending_videos,
            "channels": channels,
            "competitors": result.competitor_analysis,
        })
        
        result.niche_score = niche_analysis.get("score", 0)
        result.competition_level = niche_analysis.get("competition", "unknown")
        result.monetization_potential = niche_analysis.get("monetization", "unknown")
        result.recommendations = niche_analysis.get("recommendations", [])

        print(f"[ResearchEngine] Pesquisa concluída. Score: {result.niche_score}")
        return result

    async def analyze_channel(self, channel_url: str) -> Dict[str, Any]:
        """
        Analisa um canal específico em detalhes.
        
        Args:
            channel_url: URL do canal no YouTube
            
        Returns:
            Dict com análise completa do canal
        """
        print(f"[ResearchEngine] Analisando canal: {channel_url}")
        
        analysis = await self.channel_analyzer.analyze(channel_url)
        
        # Analisar vídeos populares
        videos = analysis.get("top_videos", [])
        if videos:
            analysis["title_patterns"] = self.title_analyzer.extract_patterns(
                [v.get("title", "") for v in videos]
            )
            
            thumbnails = await self.thumbnail_collector.collect(videos)
            analysis["thumbnail_patterns"] = self.thumbnail_analyzer.analyze(thumbnails)
            
            analysis["engagement_analysis"] = self.engagement_analyzer.analyze(videos)

        return analysis

    async def research_competitors(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pesquisa concorrentes para uma palavra-chave.
        
        Args:
            keyword: Palavra-chave para pesquisar
            limit: Limite de concorrentes para analisar
            
        Returns:
            Lista de análises de concorrentes
        """
        print(f"[ResearchEngine] Pesquisando concorrentes para: {keyword}")
        
        channels = await self.youtube_search.search(f"{keyword} canal")
        
        competitors = []
        for channel_data in channels[:limit]:
            channel_url = channel_data.get("channel_url", "")
            if channel_url:
                analysis = await self.channel_analyzer.analyze(channel_url)
                competitors.append(analysis)

        return competitors

    async def get_trending_topics(self, category: str = "general") -> List[Dict[str, Any]]:
        """
        Obtém têndencias atuais do YouTube.
        
        Args:
            category: Categoria para pesquisar (general, tech, finance, etc)
            
        Returns:
            Lista de têndencias
        """
        print(f"[ResearchEngine] Buscando têndencias: {category}")
        return await self.trending_tracker.get_trending(category)

    async def learn_youtube_rules(self) -> Dict[str, Any]:
        """
        Estuda documentação oficial do YouTube.
        
        Returns:
            Dict com regras e melhores práticas
        """
        print("[ResearchEngine] Estudando documentação YouTube...")
        return await self.youtube_docs.learn()

    def generate_channel_ideas(self, research_results: List[ResearchResult]) -> List[Dict[str, Any]]:
        """
        Gera ideias de canais baseado em múltiplas pesquisas.
        
        Args:
            research_results: Lista de resultados de pesquisa
            
        Returns:
            Lista de ideias de canais com score e justificativa
        """
        ideas = []
        
        for result in research_results:
            idea = {
                "niche": result.niche,
                "score": result.niche_score,
                "competition": result.competition_level,
                "monetization": result.monetization_potential,
                "title_patterns": result.title_patterns[:3],
                "recommendations": result.recommendations[:5],
                "channel_name_suggestion": self._generate_channel_name(result),
            }
            ideas.append(idea)
        
        ideas.sort(key=lambda x: x["score"], reverse=True)
        return ideas

    def _generate_channel_name(self, result: ResearchResult) -> str:
        """Gera sugestão de nome de canal baseado no nicho."""
        niche = result.niche.lower()
        
        name_templates = [
            f"{niche} Explicado",
            f"Canal do {niche.title()}",
            f"{niche.title()} Hub",
            f"Descobrindo {niche.title()}",
            f"{niche.title()} Total",
        ]
        
        import random
        return random.choice(name_templates)
