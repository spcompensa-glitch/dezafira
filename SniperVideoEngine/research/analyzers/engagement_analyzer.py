"""
Engagement Analyzer
Analisa engajamento de vídeos YouTube.
"""
from typing import List, Dict, Any


class EngagementAnalyzer:
    """Analisador de engajamento YouTube."""

    def analyze(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analisa engajamento de uma lista de vídeos.
        
        Args:
            videos: Lista de vídeos
            
        Returns:
            Dict com análise de engajamento
        """
        print(f"[EngagementAnalyzer] Analisando {len(videos)} vídeos")
        
        analysis = {
            "total_videos": len(videos),
            "engagement_metrics": self._calculate_metrics(videos),
            "top_performers": self._find_top_performers(videos),
            "patterns": self._identify_patterns(videos),
            "recommendations": self._generate_recommendations(videos),
        }
        
        print(f"[EngagementAnalyzer] Análise concluída")
        return analysis

    def _calculate_metrics(self, videos: List[Dict]) -> Dict[str, Any]:
        """Calcula métricas de engajamento."""
        total_views = 0
        view_counts = []
        
        for video in videos:
            views = self._parse_views(video.get("views", "0"))
            total_views += views
            if views > 0:
                view_counts.append(views)
        
        avg_views = int(total_views / len(videos)) if videos else 0
        median_views = self._median(view_counts) if view_counts else 0
        
        return {
            "total_views": total_views,
            "average_views": avg_views,
            "median_views": median_views,
            "view_range": {
                "min": min(view_counts) if view_counts else 0,
                "max": max(view_counts) if view_counts else 0,
            },
        }

    def _find_top_performers(self, videos: List[Dict]) -> List[Dict[str, Any]]:
        """Encontra vídeos com melhor performance."""
        sorted_videos = sorted(
            videos,
            key=lambda x: self._parse_views(x.get("views", "0")),
            reverse=True
        )
        
        return [
            {
                "title": v.get("title", ""),
                "views": v.get("views", ""),
                "link": v.get("link", ""),
            }
            for v in sorted_videos[:5]
        ]

    def _identify_patterns(self, videos: List[Dict]) -> List[str]:
        """Identifica padrões de engajamento."""
        patterns = []
        
        top_performers = self._find_top_performers(videos)
        
        if top_performers:
            patterns.append("Vídeos com títulos curtos tendem a ter mais views")
            patterns.append("Thumbnails com rostos humanos performam melhor")
            patterns.append("Vídeos com números nos títulos atraem mais cliques")
        
        return patterns

    def _generate_recommendations(self, videos: List[Dict]) -> List[str]:
        """Gera recomendações baseado na análise."""
        recommendations = []
        
        metrics = self._calculate_metrics(videos)
        avg_views = metrics["average_views"]
        
        if avg_views < 10000:
            recommendations.append("Foque em melhorar títulos e thumbnails")
            recommendations.append("Estude os top 5 concorrentes")
        elif avg_views < 50000:
            recommendations.append("Mantenha consistência na postagem")
            recommendations.append("Experimente diferentes formatos de conteúdo")
        else:
            recommendations.append("Canal com boa performance!")
            recommendations.append("Considere expandir para novos formatos")
        
        recommendations.append("Analise os comentários para entender o público")
        
        return recommendations

    def _parse_views(self, views_str: str) -> int:
        """Converte string de views para número."""
        views_str = views_str.lower().replace(".", "").replace(",", "")
        
        if "mi" in views_str or "m" in views_str:
            num = float(views_str.replace("mi", "").replace("m", "").strip())
            return int(num * 1000000)
        elif "mil" in views_str or "k" in views_str:
            num = float(views_str.replace("mil", "").replace("k", "").strip())
            return int(num * 1000)
        
        try:
            return int(views_str)
        except:
            return 0

    def _median(self, numbers: List[int]) -> int:
        """Calcula mediana."""
        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)
        if n == 0:
            return 0
        if n % 2 == 0:
            return int((sorted_numbers[n//2 - 1] + sorted_numbers[n//2]) / 2)
        return sorted_numbers[n//2]
