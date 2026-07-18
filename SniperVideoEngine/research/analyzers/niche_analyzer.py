"""
Niche Analyzer
Analisa nichos para identificar potencial de lucro.
"""
from typing import Dict, List, Any


class NicheAnalyzer:
    """Analisador de nichos YouTube."""

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa um nicho baseado nos dados coletados.
        
        Args:
            data: Dict com vídeos, canais e concorrentes
            
        Returns:
            Dict com análise do nicho
        """
        print("[NicheAnalyzer] Analisando nicho...")
        
        videos = data.get("videos", [])
        channels = data.get("channels", [])
        competitors = data.get("competitors", [])
        
        score = self._calculate_score(videos, channels, competitors)
        competition = self._analyze_competition(channels, competitors)
        monetization = self._estimate_monetization(videos, channels)
        recommendations = self._generate_recommendations(score, competition, monetization)
        
        return {
            "score": score,
            "competition": competition,
            "monetization": monetization,
            "recommendations": recommendations,
        }

    def _calculate_score(self, videos: List, channels: List, competitors: List) -> float:
        """Calcula score do nicho (0-100)."""
        score = 50.0
        
        if videos:
            avg_views = self._average_views(videos)
            if avg_views > 100000:
                score += 20
            elif avg_views > 50000:
                score += 15
            elif avg_views > 10000:
                score += 10
        
        if channels:
            if len(channels) < 20:
                score += 15
            elif len(channels) < 50:
                score += 10
            else:
                score += 5
        
        if competitors:
            avg_subs = self._average_subscribers(competitors)
            if avg_subs < 100000:
                score += 15
            elif avg_subs < 500000:
                score += 10
        
        return min(score, 100)

    def _analyze_competition(self, channels: List, competitors: List) -> str:
        """Analisa nível de concorrência."""
        total_channels = len(channels) + len(competitors)
        
        if total_channels < 10:
            return "low"
        elif total_channels < 30:
            return "medium"
        return "high"

    def _estimate_monetization(self, videos: List, channels: List) -> str:
        """Estima potencial de monetização."""
        avg_views = self._average_views(videos)
        
        if avg_views > 100000:
            return "high"
        elif avg_views > 30000:
            return "medium"
        return "low"

    def _average_views(self, videos: List) -> int:
        """Calcula média de views."""
        views_list = []
        for v in videos:
            views_str = v.get("views", "0")
            views_num = self._parse_views(views_str)
            if views_num > 0:
                views_list.append(views_num)
        
        return int(sum(views_list) / len(views_list)) if views_list else 0

    def _average_subscribers(self, channels: List) -> int:
        """Calcula média de inscritos."""
        subs_list = []
        for c in channels:
            subs_str = c.get("subscribers", "0")
            subs_num = self._parse_views(subs_str)
            if subs_num > 0:
                subs_list.append(subs_num)
        
        return int(sum(subs_list) / len(subs_list)) if subs_list else 0

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

    def _generate_recommendations(self, score: float, competition: str, monetization: str) -> List[str]:
        """Gera recomendações baseado na análise."""
        recommendations = []
        
        if score >= 70:
            recommendations.append("Nicho com alto potencial! Recomendado para canais novos.")
        
        if competition == "low":
            recommendations.append("Baixa concorrência - ótima oportunidade para entrar.")
        elif competition == "high":
            recommendations.append("Alta concorrência - foque em diferenciais únicos.")
        
        if monetization == "high":
            recommendations.append("Alto potencial de monetização com views significativas.")
        elif monetization == "low":
            recommendations.append("Foque em crescer a base de espectadores primeiro.")
        
        recommendations.append("Analise os top 5 canais para identificar padrões de sucesso.")
        
        return recommendations
