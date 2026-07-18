"""
SEO Analyzer
Analisa SEO de vídeos YouTube.
"""
from typing import List, Dict, Any


class SEOAnalyzer:
    """Analisador de SEO YouTube."""

    async def analyze(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analisa SEO de uma lista de vídeos.
        
        Args:
            videos: Lista de vídeos
            
        Returns:
            Dict com insights de SEO
        """
        print(f"[SEOAnalyzer] Analisando SEO de {len(videos)} vídeos")
        
        insights = {
            "title_optimization": self._analyze_titles(videos),
            "tag_patterns": self._analyze_tags(videos),
            "description_patterns": self._analyze_descriptions(videos),
            "hashtag_usage": self._analyze_hashtags(videos),
            "seo_score": self._calculate_seo_score(videos),
            "recommendations": self._generate_seo_recommendations(videos),
        }
        
        print(f"[SEOAnalyzer] Análise concluída")
        return insights

    def _analyze_titles(self, videos: List[Dict]) -> Dict[str, Any]:
        """Analisa otimização de títulos."""
        title_lengths = []
        power_words_found = []
        
        power_words = [
            "como", "por que", "dicas", "melhor", "incrível",
            "segredo", "verdade", "top", "novo",
        ]
        
        for video in videos:
            title = video.get("title", "")
            title_lengths.append(len(title))
            
            title_lower = title.lower()
            for word in power_words:
                if word in title_lower:
                    power_words_found.append(word)
        
        return {
            "average_length": int(sum(title_lengths) / len(title_lengths)) if title_lengths else 0,
            "optimal_length": "50-60 caracteres",
            "power_words_frequency": len(set(power_words_found)),
            "recommendations": [
                "Manter título entre 50-60 caracteres",
                "Incluir palavra-chave no início",
                "Usar palavras de poder para aumentar CTR",
            ],
        }

    def _analyze_tags(self, videos: List[Dict]) -> Dict[str, Any]:
        """Analisa uso de tags."""
        return {
            "common_patterns": [
                "Tags específicas do nicho",
                "Variações da palavra-chave",
                "Tags de concorrentes",
                "Tags trending",
            ],
            "best_practices": [
                "Usar 15-30 tags por vídeo",
                "Começar com tags mais específicas",
                "Incluir tags de longa cauda",
                "Atualizar tags baseado em tendências",
            ],
        }

    def _analyze_descriptions(self, videos: List[Dict]) -> Dict[str, Any]:
        """Analisa padrões de descrição."""
        return {
            "best_practices": [
                "Primeiras 2-3 linhas são cruciais",
                "Incluir links relevantes",
                "Usar timestamps para vídeos longos",
                "Adicionar links para outros vídeos",
                "Inuir call-to-action",
            ],
            "structure": [
                "Hook nos primeiros 150 caracteres",
                "Descrição detalhada do conteúdo",
                "Links relevantes",
                "Redes sociais",
                "Hashtags",
            ],
        }

    def _analyze_hashtags(self, videos: List[Dict]) -> Dict[str, Any]:
        """Analisa uso de hashtags."""
        return {
            "rules": [
                "Máximo 15 hashtags",
                "Primeiras 3 aparecem acima do título",
                "Usar hashtags relevantes e populares",
                "Não exagerar - parece spam",
            ],
            "strategy": [
                "1 hashtag do nicho",
                "1 hashtag trending",
                "1 hashtag de marca",
            ],
        }

    def _calculate_seo_score(self, videos: List[Dict]) -> float:
        """Calcula score de SEO geral."""
        score = 50.0
        
        title_analysis = self._analyze_titles(videos)
        if title_analysis["average_length"] >= 50:
            score += 15
        
        score += min(title_analysis["power_words_frequency"] * 2, 15)
        
        score += 20
        
        return min(score, 100)

    def _generate_seo_recommendations(self, videos: List[Dict]) -> List[str]:
        """Gera recomendações de SEO."""
        return [
            "Otimizar títulos com palavras-chave no início",
            "Usar 15-30 tags relevantes por vídeo",
            "Escrever descrições detalhadas com timestamps",
            "Adicionar hashtags relevantes",
            "Criar thumbnails que aumentem CTR",
            "Postar consistentemente nos horários de pico",
            "Engajar com comentários nos primeiros 30 minutos",
            "Compartilhar em redes sociais após publicar",
        ]
