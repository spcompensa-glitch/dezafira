"""
Title Analyzer
Analisa padrões de títulos de sucesso.
"""
import re
from typing import List, Dict, Any
from collections import Counter


class TitleAnalyzer:
    """Analisador de padrões de títulos YouTube."""

    POWER_WORDS = [
        "como", "por que", "segredo", "incrível", "melhor", "pior",
        "nunca", "sempre", "todo mundo", "ninguém", "descobriu",
        "revelado", "exposto", "verdade", "mudou", "transformou",
    ]

    QUESTION_WORDS = [
        "como", "por que", "qual", "quando", "onde", "quem",
    ]

    NUMBER_PATTERNS = [
        r'\d+\s*(?:dicas|maneiras|formas|motivos|erros)',
        r'(?:top|melhores?|piores?)\s*\d+',
        r'\d+\s*(?:segredos|truques|ideias)',
    ]

    def extract_patterns(self, titles: List[str]) -> List[str]:
        """
        Extrai padrões de uma lista de títulos.
        
        Args:
            titles: Lista de títulos
            
        Returns:
            Lista de padrões identificados
        """
        print(f"[TitleAnalyzer] Analisando {len(titles)} títulos")
        
        patterns = []
        
        patterns.extend(self._find_power_words(titles))
        patterns.extend(self._find_question_patterns(titles))
        patterns.extend(self._find_number_patterns(titles))
        patterns.extend(self._find_emotional_hooks(titles))
        
        unique_patterns = list(dict.fromkeys(patterns))
        
        print(f"[TitleAnalyzer] {len(unique_patterns)} padrões identificados")
        return unique_patterns[:20]

    def _find_power_words(self, titles: List[str]) -> List[str]:
        """Encontra palavras de poder nos títulos."""
        found = []
        for title in titles:
            title_lower = title.lower()
            for word in self.POWER_WORDS:
                if word in title_lower:
                    found.append(f"Usa palavra '{word}'")
        return list(set(found))

    def _find_question_patterns(self, titles: List[str]) -> List[str]:
        """Encontra padrões de pergunta."""
        found = []
        for title in titles:
            title_lower = title.lower()
            for qword in self.QUESTION_WORDS:
                if title_lower.startswith(qword):
                    found.append(f"Começa com '{qword}'")
                    break
            if "?" in title:
                found.append("Contém pergunta (?)")
        return list(set(found))

    def _find_number_patterns(self, titles: List[str]) -> List[str]:
        """Encontra padrões com números."""
        found = []
        for title in titles:
            for pattern in self.NUMBER_PATTERNS:
                if re.search(pattern, title.lower()):
                    found.append("Usa números (listas)")
                    break
        return list(set(found))

    def _find_emotional_hooks(self, titles: List[str]) -> List[str]:
        """Encontra ganchos emocionais."""
        found = []
        emotional_words = [
            "surpreendente", "chocante", "inacreditável", "épico",
            "incrível", "fantástico", "absurdo", "loucura",
        ]
        
        for title in titles:
            title_lower = title.lower()
            for word in emotional_words:
                if word in title_lower:
                    found.append("Usa gatilho emocional")
                    break
        return list(set(found))

    def generate_templates(self, patterns: List[str], niche: str) -> List[str]:
        """
        Gera templates de título baseado nos padrões encontrados.
        
        Args:
            patterns: Padrões identificados
            niche: Nicho do canal
            
        Returns:
            Lista de templates de título
        """
        templates = []
        
        templates.append(f"Como {niche} está mudando tudo em 2026")
        templates.append(f"5 dicas de {niche} que ninguém te conta")
        templates.append(f"O segredo que os especialistas de {niche} escondem")
        templates.append(f"Por que {niche} é mais importante do que você pensa")
        templates.append(f"Top 10 ferramentas de {niche} para iniciantes")
        templates.append(f"{niche} explicado em 5 minutos")
        templates.append(f"O erro mortal que todo mundo comete em {niche}")
        templates.append(f"Descoberta incrível sobre {niche}")
        
        return templates
