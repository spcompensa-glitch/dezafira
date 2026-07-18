"""
Channel Manager
Gerencia criação e documentação de canais.
"""
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class ChannelManager:
    """
    Gerencia criação e documentação de canais YouTube.
    
    Responsabilidades:
    1. Criar documentação completa de canais
    2. Gerar templates de vídeos
    3. Gerenciar ciclo de vida dos canais
    """

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(__file__), "generated")
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    async def create_channel(
        self,
        niche: str,
        channel_name: str,
        research_data: Dict[str, Any],
    ) -> str:
        """
        Cria documentação completa de um canal.
        
        Args:
            niche: Nicho do canal
            channel_name: Nome do canal
            research_data: Dados da pesquisa
            
        Returns:
            ID do canal criado
        """
        import uuid
        channel_id = f"canal_{str(uuid.uuid4())[:8]}"
        
        channel_dir = os.path.join(self.base_dir, channel_id)
        os.makedirs(channel_dir, exist_ok=True)
        
        await self._create_identity(channel_dir, channel_name, niche, research_data)
        await self._create_strategy(channel_dir, niche, research_data)
        await self._create_content_plan(channel_dir, niche, research_data)
        await self._create_video_templates(channel_dir, niche, 10)
        
        print(f"[ChannelManager] Canal criado: {channel_id}")
        return channel_id

    async def _create_identity(
        self,
        channel_dir: str,
        name: str,
        niche: str,
        research_data: Dict
    ):
        """Cria documento de identidade do canal."""
        identity = f"""# Identidade do Canal

## Nome
{name}

## Nicho
{niche}

## Slogan
"Conteúdo que transforma"

## Tom de Voz
- Educador amigo
- Direto ao ponto
- Usando linguagem acessível
- Sem jargões desnecessários

## Cores da Marca
- Primária: #00D4FF (Azul tecnologia)
- Secundária: #FF6B6B (Vermelho destaque)
- Fundo: #1A1A2E (Escuro moderno)

## Público-Alvo
- Idade: 18-35 anos
- Interesse: {niche}
- Nível: Iniciante a Intermediário

## Proposta de Valor
Conteúdo de {niche} que ensina de forma simples e prática.
"""
        
        with open(os.path.join(channel_dir, "IDENTIDADE.md"), "w", encoding="utf-8") as f:
            f.write(identity)

    async def _create_strategy(
        self,
        channel_dir: str,
        niche: str,
        research_data: Dict
    ):
        """Cria documento de estratégia."""
        score = research_data.get("niche_score", 0)
        competition = research_data.get("competition_level", "medium")
        
        strategy = f"""# Estratégia do Canal

## Análise de Nicho
- **Score do Nicho:** {score}/100
- **Nível de Competição:** {competition}
- **Potencial de Monetização:** Alto

## Diferencial Competitivo
1. Conteúdo mais acessível que a concorrência
2. Visual moderno e profissional
3. Postagem consistente
4. Engajamento ativo com a comunidade

## Meta de Crescimento
- **Mês 1:** 100 inscritos
- **Mês 3:** 500 inscritos
- **Mês 6:** 2.000 inscritos
- **Mês 12:** 10.000 inscritos

## Calendário de Postagem
- **Frequência:** 3 vídeos por semana
- **Melhores Horários:** 18h e 20h
- **Dias:** Terça, Quinta, Sábado

## Formatos de Vídeo
1. **Long-form (8-15 min):** Tutoriais e explicações
2. **Shorts (60s):** Dicas rápidas e curiosidades
3. **Listas:** Top 10, 5 dicas, etc.
"""
        
        with open(os.path.join(channel_dir, "ESTRATEGIA.md"), "w", encoding="utf-8") as f:
            f.write(strategy)

    async def _create_content_plan(
        self,
        channel_dir: str,
        niche: str,
        research_data: Dict
    ):
        """Cria plano de conteúdo."""
        title_patterns = research_data.get("title_patterns", [])
        
        content = f"""# Plano de Conteúdo

## Pilares de Conteúdo
1. **Educação:** Ensinar conceitos de {niche}
2. **Dicas:** Práticas e tutoriais
3. **Tendências:** Novidades do mercado
4. **Análises:** Comparativos e reviews

## Hierarquia de Vídeos (1-10)
1. **Vídeo 1:** Introdução ao nicho
2. **Vídeo 2:** Conceitos básicos
3. **Vídeo 3:** Ferramentas essenciais
4. **Vídeo 4:** Primeiro projeto prático
5. **Vídeo 5:** Erros comuns
6. **Vídeo 6:** Dicas avançadas
7. **Vídeo 7:** Casos de sucesso
8. **Vídeo 8:** Tendências 2026
9. **Vídeo 9:** Comparativo de ferramentas
10. **Vídeo 10:** Roadmap completo

## Padrões de Título Identificados
{chr(10).join(f"- {p}" for p in title_patterns[:5]) if title_patterns else "- Títulos curtos e chamativos"}

## Formatos comuns
- Como [FAZER ALGO] em [TEMPO]
- [NÚMERO] Dicas para [BENEFÍCIO]
- O Segredo que [GRUPO] Não Conta
"""
        
        with open(os.path.join(channel_dir, "CONTEUDO.md"), "w", encoding="utf-8") as f:
            f.write(content)

    async def _create_video_templates(
        self,
        channel_dir: str,
        niche: str,
        count: int
    ):
        """Cria templates de vídeos."""
        for i in range(1, count + 1):
            video_template = f"""# Vídeo {i}

## Título
Título Otimizado para o Vídeo {i}

## Descrição
Descrição completa do vídeo com mais de 200 caracteres para SEO.

## Tags
- tag1
- tag2
- tag3
- {niche}
- tutorial
- dicas

## Hashtags
#{niche.replace(' ', '')}
#tutorial
#dicas

## Roteiro
### Introdução (0:00 - 0:30)
Gancho forte para prender atenção.

### Conteúdo Principal (0:30 - 7:00)
Desenvolvimento do tema.

### Conclusão (7:00 - 8:00)
Resumo e call-to-action.

## Thumbnail
- Rosto com expressão surpresa
- Texto grande: "TÍTULO DO VÍDEO"
- Cores vibrantes

## Timestamps
0:00 - Introdução
0:30 - O que é {niche}
3:00 - Como funciona
5:00 - Dicas práticas
7:00 - Conclusão
"""
            
            filename = f"VIDEO_{i:02d}.md"
            with open(os.path.join(channel_dir, filename), "w", encoding="utf-8") as f:
                f.write(video_template)

    def list_channels(self) -> List[Dict[str, Any]]:
        """Lista todos os canais criados."""
        channels = []
        
        if not os.path.exists(self.base_dir):
            return channels
        
        for channel_id in os.listdir(self.base_dir):
            channel_dir = os.path.join(self.base_dir, channel_id)
            if os.path.isdir(channel_dir):
                identity_path = os.path.join(channel_dir, "IDENTIDADE.md")
                if os.path.exists(identity_path):
                    with open(identity_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        name = content.split("## Nome")[1].split("##")[0].strip() if "## Nome" in content else channel_id
                        channels.append({
                            "id": channel_id,
                            "name": name,
                            "path": channel_dir,
                        })
        
        return channels

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Retorna dados de um canal específico."""
        channel_dir = os.path.join(self.base_dir, channel_id)
        
        if not os.path.exists(channel_dir):
            return None
        
        result = {"id": channel_id}
        
        for doc in ["IDENTIDADE.md", "ESTRATEGIA.md", "CONTEUDO.md"]:
            doc_path = os.path.join(channel_dir, doc)
            if os.path.exists(doc_path):
                with open(doc_path, "r", encoding="utf-8") as f:
                    result[doc.replace(".md", "").lower()] = f.read()
        
        videos = []
        for i in range(1, 11):
            video_path = os.path.join(channel_dir, f"VIDEO_{i:02d}.md")
            if os.path.exists(video_path):
                with open(video_path, "r", encoding="utf-8") as f:
                    videos.append(f.read())
        result["videos"] = videos
        
        return result
