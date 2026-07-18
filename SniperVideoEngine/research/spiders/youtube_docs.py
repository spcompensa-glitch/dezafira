"""
YouTube Docs Spider
Estuda documentação oficial do YouTube.
"""
from typing import Dict, Any
from services.obscura_client import obscura_client


class YouTubeDocsSpider:
    """Spider para estudar documentação oficial do YouTube."""

    DOCS_URLS = [
        "https://support.google.com/youtube/answer/2801986",
        "https://support.google.com/youtube/answer/2801973",
        "https://support.google.com/youtube/answer/1722171",
        "https://support.google.com/youtube/answer/13812692",
        "https://support.google.com/youtube/answer/2645418",
        "https://support.google.com/youtube/answer/6020285",
    ]

    async def learn(self) -> Dict[str, Any]:
        """
        Estuda documentação oficial do YouTube.

        Returns:
            Dict com regras e melhores práticas
        """
        print("[YouTubeDocs] Estudando documentação oficial...")

        knowledge = {
            "monetization_rules": await self._learn_monetization(),
            "seo_best_practices": await self._learn_seo(),
            "content_guidelines": await self._learn_content_guidelines(),
            "algorithm_tips": await self._learn_algorithm(),
            "thumbnail_rules": await self._learn_thumbnail_rules(),
            "title_rules": await self._learn_title_rules(),
        }

        print("[YouTubeDocs] Documentação estudada com sucesso")
        return knowledge

    async def _learn_monetization(self) -> Dict[str, Any]:
        """Aprende sobre regras de monetização."""
        return {
            "min_subscribers": 1000,
            "min_watch_hours": 4000,
            "min_shorts_views": 1000000,
            "ad_revenue_share": 0.55,
            "requirements": [
                "Seguir as diretrizes da comunidade",
                "Ter mais de 1.000 inscritos",
                "Ter mais de 4.000 horas de exibição públicas nos últimos 12 meses",
                "OU ter mais de 10 milhões de exibições de Shorts nos últimos 90 dias",
                "Ter uma conta do AdSense vinculada",
            ],
            "tips": [
                "Consistência na postagem",
                "Conteúdo de alta qualidade",
                "Engajamento com a comunidade",
                "Evitar copyright",
            ],
        }

    async def _learn_seo(self) -> Dict[str, Any]:
        """Aprende sobre SEO no YouTube."""
        return {
            "title_optimization": [
                "Máximo 60 caracteres",
                "Palavra-chave no início",
                "Títulos chamativos mas relevantes",
                "Evitar clickbait excessivo",
            ],
            "description_optimization": [
                "Primeiras 2-3 linhas são cruciais",
                "Incluir links relevantes",
                "Usar timestamps",
                "Máximo 5.000 caracteres",
                "Incluir palavras-chave naturalmente",
            ],
            "tags_best_practices": [
                "Usar 15-30 tags",
                "Começar com tags específicas",
                "Inuir variações da palavra-chave",
                "Usar tags de trending quando relevante",
            ],
            "hashtag_rules": [
                "Máximo 15 hashtags",
                "Primeiras 3 aparecem acima do título",
                "Usar hashtags relevantes e populares",
            ],
        }

    async def _learn_content_guidelines(self) -> Dict[str, Any]:
        """Aprende sobre diretrizes de conteúdo."""
        return {
            "community_guidelines": [
                "Não promover violência",
                "Não conter conteúdo sexual explícito",
                "Não conter discurso de ódio",
                "Não conter spam ou enganação",
                "Respeitar direitos autorais",
            ],
            "copyright_rules": [
                "Usar conteúdo royalty-free",
                "Obter licenças quando necessário",
                "Usar Creative Commons quando possível",
                "Fair use tem limites específicos",
            ],
            "best_practices": [
                "Criar conteúdo original",
                "Agregar valor ao espectador",
                "Ser autêntico",
                "Manter consistência",
            ],
        }

    async def _learn_algorithm(self) -> Dict[str, Any]:
        """Aprende sobre o algoritmo do YouTube."""
        return {
            "key_factors": [
                "Taxa de cliques (CTR)",
                "Taxa de retenção",
                "Engajamento (likes, comentários, compartilhamentos)",
                "Horário de postagem",
                "Consistência",
            ],
            "tips_for_viral": [
                "Títulos chamativos",
                "Thumbnails atraentes",
                "Gancho forte nos primeiros 5 segundos",
                "Conteúdo que gera engajamento",
                "Postar nos horários de pico",
            ],
            "retention_tips": [
                "Intro curta e direta",
                "Mudanças de ritmo a cada 30-60 segundos",
                "Cliffhangers antes de cortes",
                "Call-to-action estratégicos",
                "Duração ideal: 8-15 minutos para long-form",
            ],
        }

    async def _learn_thumbnail_rules(self) -> Dict[str, Any]:
        """Aprende sobre regras de thumbnail."""
        return {
            "technical_specs": [
                "Resolução: 1280x720 pixels",
                "Formato: JPG, GIF ou PNG",
                "Tamanho máximo: 2MB",
                "Proporção: 16:9",
            ],
            "design_tips": [
                "Rostos com expressões fortes funcionam",
                "Cores vibrantes chamam atenção",
                "Texto grande e legível",
                "Contraste alto",
                "Evitar clutter",
            ],
            "proven_patterns": [
                "Rosto surpreso + texto grande",
                "Antes/Depois",
                "Setas e círculos destacando algo",
                "Número no título (Top 10, 5 dicas)",
            ],
        }

    async def _learn_title_rules(self) -> Dict[str, Any]:
        """Aprende sobre regras de título."""
        return {
            "best_practices": [
                "Máximo 60 caracteres",
                "Palavra-chave nos primeiros 40 caracteres",
                "Evitar ALL CAPS excessivo",
                "Usar números quando relevante",
                "Criar curiosidade",
            ],
            "power_words": [
                "Como", "Por que", "Segredo", "Revelado",
                "Incrível", "Melhor", "Pior", "Nunca",
                "Sempre", "Todo mundo", "Ninguém",
            ],
            "formulas_that_work": [
                "Como [FAZER ALGO] em [TEMPO]",
                "[NÚMERO] Dicas para [BENEFÍCIO]",
                "O Segredo que [GRUPO] Não Conta",
                "[BENEFÍCIO] Sem [DOR]",
                "Por que [ACONTECIMENTO] Muda Tudo",
            ],
        }
