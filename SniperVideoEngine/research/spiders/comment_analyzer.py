"""
Comment Analyzer Spider
Analisa comentários de vídeos YouTube.
"""
import re
from typing import List, Dict, Any
from services.obscura_client import obscura_client


class CommentAnalyzerSpider:
    """Spider para analisar comentários de vídeos YouTube."""

    async def analyze(self, video_url: str, limit: int = 50) -> Dict[str, Any]:
        """
        Analisa comentários de um vídeo.

        Args:
            video_url: URL do vídeo
            limit: Limite de comentários para analisar

        Returns:
            Dict com análise dos comentários
        """
        print(f"[CommentAnalyzer] Analisando comentários: {video_url}")

        try:
            html = await asyncio.to_thread(obscura_client.fetch_html, video_url)
            if not html:
                return {"error": "Falha ao buscar página"}

            comments = self._extract_comments(html, limit)

            analysis = {
                "total_comments": len(comments),
                "comments": comments,
                "sentiment": self._analyze_sentiment(comments),
                "common_topics": self._extract_topics(comments),
                "questions": self._extract_questions(comments),
                "feedback_type": self._classify_feedback(comments),
            }

            print(f"[CommentAnalyzer] {len(comments)} comentários analisados")
            return analysis

        except Exception as e:
            print(f"[CommentAnalyzer] Erro: {e}")
            return {"error": str(e)}

    def _extract_comments(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """Extrai comentários da página."""
        comments = []

        author_pattern = r'"authorText":\{"simpleText":"([^"]+)"\}'
        text_pattern = content_text_pattern = r'"contentText":\{"runs":\[\{"text":"([^"]*)"'

        authors = re.findall(author_pattern, html)
        texts = re.findall(text_pattern, html)

        for i in range(min(len(texts), limit)):
            author = authors[i] if i < len(authors) else ""
            text = texts[i]
            if text:
                comments.append({
                    "author": author,
                    "text": text,
                    "likes": "",
                })

        return comments

    def _analyze_sentiment(self, comments: List[Dict]) -> str:
        """Analisa sentimento geral dos comentários."""
        positive_words = ["obrigado", "incrível", "amei", "excelente", "bom", "legal"]
        negative_words = ["ruim", "péssimo", "odeio", "horrível", "lixo"]

        positive_count = 0
        negative_count = 0

        for comment in comments:
            text = comment.get("text", "").lower()
            for word in positive_words:
                if word in text:
                    positive_count += 1
            for word in negative_words:
                if word in text:
                    negative_count += 1

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    def _extract_topics(self, comments: List[Dict]) -> List[str]:
        """Extrai tópicos comuns dos comentários."""
        words = {}
        for comment in comments:
            for word in comment.get("text", "").split():
                word = word.lower()
                if len(word) > 4:
                    words[word] = words.get(word, 0) + 1

        sorted_words = sorted(words.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]

    def _extract_questions(self, comments: List[Dict]) -> List[str]:
        """Extrai perguntas dos comentários."""
        questions = []
        for comment in comments:
            text = comment.get("text", "")
            if "?" in text or "como" in text.lower() or "por que" in text.lower():
                questions.append(text)
        return questions[:10]

    def _classify_feedback(self, comments: List[Dict]) -> Dict[str, int]:
        """Classifica tipo de feedback."""
        feedback = {
            "positive": 0,
            "negative": 0,
            "question": 0,
            "suggestion": 0,
        }

        for comment in comments:
            text = comment.get("text", "").lower()
            if "?" in text:
                feedback["question"] += 1
            elif any(w in text for w in ["deveria", "sugiro", "idea"]):
                feedback["suggestion"] += 1
            elif any(w in text for w in ["bom", "ótimo", "obrigado"]):
                feedback["positive"] += 1
            elif any(w in text for w in ["ruim", "péssimo", "errado"]):
                feedback["negative"] += 1

        return feedback
