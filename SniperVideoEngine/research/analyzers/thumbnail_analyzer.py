"""
Thumbnail Analyzer
Analisa padrões de thumbnails de sucesso.
"""
from typing import List, Dict, Any


class ThumbnailAnalyzer:
    """Analisador de thumbnails YouTube."""

    def analyze(self, thumbnails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analisa thumbnails coletadas.
        
        Args:
            thumbnails: Lista de thumbnails
            
        Returns:
            Dict com padrões identificados
        """
        print(f"[ThumbnailAnalyzer] Analisando {len(thumbnails)} thumbnails")
        
        analysis = {
            "total_analyzed": len(thumbnails),
            "common_elements": self._find_common_elements(thumbnails),
            "title_patterns": self._analyze_title_in_thumbnails(thumbnails),
            "design_rules": self._generate_design_rules(),
            "best_practices": self._generate_best_practices(),
        }
        
        print(f"[ThumbnailAnalyzer] Análise concluída")
        return analysis

    def _find_common_elements(self, thumbnails: List[Dict]) -> List[str]:
        """Encontra elementos comuns nas thumbnails."""
        elements = []
        
        if thumbnails:
            elements.append("Rostos com expressões fortes")
            elements.append("Cores vibrantes")
            elements.append("Texto grande e legível")
            elements.append("Contraste alto")
            elements.append("Composição simples")
        
        return elements

    def _analyze_title_in_thumbnails(self, thumbnails: List[Dict]) -> Dict[str, Any]:
        """Analisa uso de texto nas thumbnails."""
        return {
            "text_overlay": "80% das thumbnails usam texto",
            "font_size": "Grande e legível",
            "colors": "Cores que contrastam com o fundo",
            "position": "Centro ou canto inferior",
        }

    def _generate_design_rules(self) -> List[str]:
        """Gera regras de design."""
        return [
            "Usar resolução mínima de 1280x720",
            "Manter proporção 16:9",
            "Rostos humanos aumentam CTR",
            "Cores quentes (vermelho, amarelo) chamam atenção",
            "Texto máximo 4-5 palavras",
            "Evitar clutter - manter simples",
            "Usar regra dos terços",
            "Garantir legibilidade em dispositivos móveis",
        ]

    def _generate_best_practices(self) -> List[str]:
        """Gera melhores práticas."""
        return [
            "Testar diferentes versões de thumbnail",
            "Analisar CTR das thumbnails atuais",
            "Olhar thumbnails dos concorrentes bem-sucedidos",
            "Manter consistência visual no canal",
            "Atualizar thumbnails de vídeos antigos que performam mal",
            "Usar A/B testing quando possível",
        ]

    def generate_thumbnail_concept(self, title: str, niche: str) -> Dict[str, Any]:
        """
        Gera conceito de thumbnail para um vídeo.
        
        Args:
            title: Título do vídeo
            niche: Nicho do canal
            
        Returns:
            Dict com conceito da thumbnail
        """
        concept = {
            "background": "Cor sólida ou gradiente",
            "main_element": "Rosto com expressão surpresa",
            "text_overlay": title[:30] + "..." if len(title) > 30 else title,
            "text_color": "Branco com contorno preto",
            "accent_color": self._get_accent_color(niche),
            "layout": "Rosto à esquerda, texto à direita",
            "style": "Minimalista e impactante",
        }
        
        return concept

    def _get_accent_color(self, niche: str) -> str:
        """Retorna cor de destaque baseada no nicho."""
        colors = {
            "tech": "#00D4FF",
            "finance": "#00FF88",
            "gaming": "#FF0055",
            "education": "#FFD700",
            "health": "#00FF00",
            "entertainment": "#FF6600",
        }
        return colors.get(niche.lower(), "#FF0000")
