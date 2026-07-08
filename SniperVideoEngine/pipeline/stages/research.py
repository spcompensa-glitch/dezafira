"""
Research Stage
Estágio de pesquisa do pipeline.
"""
from typing import Dict, Any
from ...research.engine import ResearchEngine


class ResearchStage:
    """Estágio de pesquisa de tendências."""

    def __init__(self):
        self.engine = ResearchEngine()

    async def execute(self, theme: str) -> Dict[str, Any]:
        """
        Executa pesquisa completa do tema.
        
        Args:
            theme: Tema para pesquisar
            
        Returns:
            Dict com resultados da pesquisa
        """
        print(f"[ResearchStage] Pesquisando: {theme}")
        
        result = await self.engine.research_niche(theme)
        
        return {
            "niche_score": result.niche_score,
            "competition": result.competition_level,
            "monetization": result.monetization_potential,
            "trending_videos": len(result.trending_videos),
            "title_patterns": result.title_patterns,
            "recommendations": result.recommendations,
        }
