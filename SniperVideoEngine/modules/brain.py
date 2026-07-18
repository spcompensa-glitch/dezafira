import os
import json
import requests
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

class SniperBrain:
    def __init__(self):
        self.nvidia_key = (os.getenv("NVIDIA_API_KEY") or "").strip()
        self.deepseek_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brand_config")
        self.last_provider_used = "none"

    def _read_config_file(self, filename):
        file_path = os.path.join(self.config_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"[Arquivo {filename} não configurado. Por favor, adicione as diretrizes.]"

    def _call_llm(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4000):
        """Chama o LLM com fallback: Hermes Agent → NVIDIA → DeepSeek."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 0. Nous Hermes Agent (se disponível)
        hermes_url = os.getenv("HERMES_API_URL", "").strip()
        hermes_key = os.getenv("HERMES_API_KEY", "").strip()
        if hermes_url and hermes_key:
            try:
                resp = requests.post(
                    f"{hermes_url}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {hermes_key}", "Content-Type": "application/json"},
                    json={"messages": messages, "model": "nvidia"},
                    timeout=30.0
                )
                if resp.status_code == 200:
                    self.last_provider_used = "hermes-agent"
                    return resp.json()["choices"][0]["message"]["content"]
            except Exception:
                pass
        
        # 1. NVIDIA (Primary)
        if self.nvidia_key:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.nvidia_key}"
                }
                payload = {
                    "model": "meta/llama-3.1-8b-instruct",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                response = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=90.0)
                if response.status_code == 200:
                    self.last_provider_used = "nvidia"
                    print("[LLM] NVIDIA respondeu com sucesso!")
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[LLM] NVIDIA retornou status {response.status_code}: {response.text[:200]}")
            except Exception as e:
                print(f"[LLM] Erro ao chamar NVIDIA: {e}")
        
        # 2. DeepSeek (Fallback)
        if self.deepseek_key:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.deepseek_key}"
                }
                payload = {
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=payload, timeout=60.0)
                if response.status_code == 200:
                    self.last_provider_used = "deepseek"
                    print("[LLM] DeepSeek respondeu com sucesso!")
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[LLM] DeepSeek retornou status {response.status_code}")
            except Exception as e:
                print(f"[LLM] Erro ao chamar DeepSeek: {e}")
        
        raise Exception("Todos os provedores LLM falharam (NVIDIA, DeepSeek)")

    def generate_script(self, theme, brand="Geral", trends_context="", channel_context="", target_duration=45):
        """Gera o roteiro, titulo, prompts visuais e clima musical unificados para a Dezafira em JSON

        Args:
            theme: Tema do vídeo
            brand: Nicho/marca
            trends_context: Contexto de tendências do YouTube
            channel_context: Contexto do Shared Memory (channel_knowledge) para personalização
            target_duration: Duração alvo em segundos (default 45s para Shorts)
        """
        brand_bible = self._read_config_file("brand_bible.md")
        target_audience = self._read_config_file("target_audience.md")
        voice_guide = self._read_config_file("voice_guide.md")
        
        # Calcular palavras necessárias baseado na duração
        # Português: ~150 palavras/minuto = ~2.5 palavras/segundo
        words_needed = int(target_duration * 2.5)
        # Adicionar margem de 20% para garantir
        words_target = int(words_needed * 1.2)
        
        # Determinar tipo de vídeo baseado na duração
        if target_duration <= 60:
            video_type = "Shorts/TikTok (40-60 segundos)"
            max_words = 150
        elif target_duration <= 180:
            video_type = "Vídeo curto (2-3 minutos)"
            max_words = 450
        elif target_duration <= 300:
            video_type = "Vídeo médio (5 minutos)"
            max_words = 750
        else:
            video_type = "Vídeo longo (10+ minutos)"
            max_words = 1500
        
        system_prompt = """
        Voce e o Roteirista e Diretor Executivo da Dezafira, especialista em criar videos de alta conversao para YouTube.

        === REGRAS DE GROWTH HACKING (OBRIGATÓRIAS) ===
        1. HOOK IMPLACÁVEL: Os primeiros 3 segundos DEVEM prender a atenção. 
           NUNCA comece com "Olá pessoal", "Bem-vindos", "Neste vídeo vou mostrar" ou introduções lentas.
           Comece direto no ápice do assunto: um fato intrigante, uma pergunta provocativa ou uma quebra de expectativa.

        2. RITMO VISUAL: Nenhuma cena deve durar mais de 3 segundos.
           Alterne palavras-chave visuais para manter o ritmo.

        3. TÍTULO MAGNÉTICO: Use a fórmula [Gatilho de Curiosidade] + [Fato Inesperado].
           Ex: "A mentira que te contaram sobre..." ao invés de "História de..."
           Evite títulos meramente informativos ou descritivos.

        4. ESTRUTURA: Uma ideia por frase. Sem repetir o mesmo conceito.
           Cada frase deve obrigar o espectador a querer ouvir a próxima.

        5. EXTENSÃO DO ROTEIRO: O roteiro DEVE ter EXATAMENTE {words_target} palavras (±10%).
           NÃO gere scripts curtos! Se precisar, adicione mais detalhes, exemplos, dados, histórias.
           Um vídeo de {target_duration} segundos precisa de MUITO texto para preencher o tempo.

        === DIRETRIZES DO CANAL ===
        Use as diretrizes abaixo para formatar o tom de voz e estilo do roteiro:

        [BRAND BIBLE]
        {}

        [TARGET AUDIENCE]
        {}

        [VOICE GUIDE]
        {}
        """.format(brand_bible, target_audience, voice_guide, words_target=words_target, target_duration=target_duration)
        
        # Adicionar contexto do Shared Memory se disponível
        memory_block = ""
        if channel_context:
            memory_block = "\n[MEMORIA DE LONGO PRAZO DO CANAL]\n{}\n".format(channel_context)
        
        trends_block = ""
        if trends_context:
            trends_block = "\n[TENDENCIAS ATUAIS NO YOUTUBE]\n{}\n".format(trends_context)
        
        user_prompt = """
        Gere um plano de video completo em formato JSON para o tema: "{}" (Nicho: {}).
        {}
        {}
        
        IMPORTANTE: Este é um {video_type}.
        O roteiro DEVE ter EXATAMENTE {words_target} palavras (±10%).
        Duração alvo: {target_duration} segundos ({minutes} minutos).

        LEMBRE-SE: 
        - NUNCA comece com saudações
        - Uma ideia por frase
        - Título com gatilho de curiosidade (< 60 chars)
        - O script deve ser LONGO o suficiente para preencher {target_duration} segundos de narração
        - Se o script ficar curto, adicione mais exemplos, dados, histórias, detalhes

        Retorne estritamente um objeto JSON com o seguinte formato, sem blocos de texto explicativos adicionais antes ou depois:
        {{
            "title": "Titulo com gatilho de curiosidade e menos de 60 caracteres",
            "script": "Texto corrido que sera narrado com EXATAMENTE {words_target} palavras. Comece direto no assunto, sem introduções. Adicione detalhes, exemplos, dados para preencher o tempo.",
            "visual_prompts": ["Keyword visual em ingles para cena 1", "Keyword visual em ingles para cena 2", "Keyword visual em ingles para cena 3", "Keyword visual em ingles para cena 4", "Keyword visual em ingles para cena 5"],
            "music_prompt": "Clima musical sugerido (ex: dark techno, epic motivation, ambient tech)",
            "target_duration": {target_duration}
        }}
        """.format(theme, brand, trends_block, memory_block,
                   video_type=video_type, words_target=words_target,
                   target_duration=target_duration, minutes=target_duration//60)
        
        try:
            res_text = self._call_llm(system_prompt, user_prompt, temperature=0.7)
            # Limpar o texto se a IA colocar marcações de markdown ```json
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()
            
            plan = json.loads(res_text.strip())

            # Validação pós-geração: Rejeitar se começar com saudação
            script = plan.get("script", "")
            forbidden_starts = ["olá", "oi", "bem-vindo", "bem vindo", "neste vídeo", "nesse vídeo", "e aí", "fala galera"]
            if script:
                first_words = script.lower().strip()[:30]
                for forbidden in forbidden_starts:
                    if first_words.startswith(forbidden):
                        print(f"[Brain] Roteiro rejeitado: começa com '{forbidden}'. Regenerando...")
                        # Ajustar o script removendo a saudação
                        sentences = script.split(". ")
                        if len(sentences) > 1:
                            plan["script"] = ". ".join(sentences[1:])
                        break

            return plan
        except Exception as e:
            print(f"[Brain] Falha ao processar resposta estruturada do LLM: {e}")
            # Fallback em caso de erro de parsing JSON
            return {
                "title": f"O erro que destruiu {theme}",  # Título com gatilho
                "script": f"Você sabia que 90% das pessoas erram feio ao tentar {theme[:30]}? Pois é. A verdade é bem mais simples do que parece. E é exatamente isso que vou te mostrar agora.",
                "visual_prompts": ["person looking surprised at screen", "abstract technology concept", "person achieving success"],
                "music_prompt": "epic motivation",
                "target_duration": 30
            }

    def generate_youtube_titles(self, theme, key_points):
        """Skill 1 - Títulos com alta tensão emocional"""
        brand_bible = self._read_config_file("brand_bible.md")
        target_audience = self._read_config_file("target_audience.md")

        system_prompt = f"""
        Você é um especialista em títulos de alta retenção e conversão do YouTube.
        Use as informações de marca e público-alvo para contextualizar os títulos:
        
        [BRAND BIBLE]
        {brand_bible}
        
        [TARGET AUDIENCE]
        {target_audience}
        """

        user_prompt = f"""
        Gere 5 opções de títulos com ângulos diferentes para o seguinte conteúdo:
        - Tema: {theme}
        - Pontos chave: {key_points}

        Regras:
        1. Busque um ângulo que gere tensão — não descreva o vídeo, prometa resolver um medo.
        2. Use frameworks de títulos validados do nicho.
        3. Evite títulos clichês como "Como fazer X em Y passos".
        4. Máximo de 60 caracteres.

        Retorne as 5 opções. Para cada uma, explique em uma linha qual medo específico ativa no viewer.
        No final, recomende qual você considera o melhor e o porquê.
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.8)

    def generate_intro(self, selected_title):
        """Skill 2 - Intros magnéticas (3 variações)"""
        brand_bible = self._read_config_file("brand_bible.md")
        target_audience = self._read_config_file("target_audience.md")
        voice_guide = self._read_config_file("voice_guide.md")

        system_prompt = f"""
        Você é um especialista em introduções magnéticas para YouTube (Ganchos de 10 a 15 segundos).
        A intro deve confirmar a expectativa do clique no título imediatamente e abrir um loop de curiosidade.
        
        Siga rigorosamente estas configurações do canal:
        [BRAND BIBLE]
        {brand_bible}
        [TARGET AUDIENCE]
        {target_audience}
        [VOICE GUIDE]
        {voice_guide}
        """

        user_prompt = f"""
        Escreva 3 variações de introdução para o título: "{selected_title}"
        Cada variação deve ter no máximo 100 palavras.
        Variantes com ângulos emocionais diferentes: medo / ironia / dado surpreendente.
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.7)

    def verify_intro_quality(self, intro_text):
        """Skill 2 - Controle de qualidade da Intro"""
        system_prompt = "Você é um revisor de roteiros extremamente rigoroso e focado em retenção."
        user_prompt = f"""
        Revise esta introdução segundo os seguintes critérios:
        1. Confirma o clique nos primeiros 10 segundos?
        2. Abre um loop de curiosidade claro?
        3. Estabelece autoridade sem parecer anúncio?
        4. A primeira frase obriga a ler a segunda?
        5. Tem alguma frase genérica ou enrolação?
        6. Repete a mesma ideia?

        Para cada critério responda: ✅ passa / ❌ não passa + correção específica.
        No final, dê a versão melhorada consolidada.

        INTRODUÇÃO A SER AVALIADA:
        {intro_text}
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.3)

    def generate_outline(self, title, brain_dump):
        """Skill 3 - Estrutura narrativa (Outline)"""
        target_audience = self._read_config_file("target_audience.md")

        system_prompt = f"""
        Você é um estrategista de narrativa de vídeo para YouTube.
        
        [TARGET AUDIENCE]
        {target_audience}
        """

        user_prompt = f"""
        Com base nas ideias abaixo, organize um outline narrativo de 5 a 10 seções.
        - Título: {title}
        
        Ideias brutas (Brain Dump):
        {brain_dump}

        Critérios do Outline:
        1. Cada seção abre um problema novo antes de fechar o anterior para reter o público.
        2. O segundo ponto mais interessante vai no início. O mais interessante vai por último.
        3. Cada seção deve ter um Payoff (entrega de valor) claro.
        4. Não repita ideias.

        Retorne o outline listando para cada seção:
        - Número da seção
        - Título da seção
        - O payoff da seção em uma frase
        - O loop que se abre para a próxima seção
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.7)

    def generate_section_body(self, title, section_name, previous_section_last_line, this_section_theme, next_section_theme):
        """Skill 4 - Redação de Seção Individual seguindo estrutura psicológica"""
        brand_bible = self._read_config_file("brand_bible.md")
        target_audience = self._read_config_file("target_audience.md")
        voice_guide = self._read_config_file("voice_guide.md")

        system_prompt = f"""
        Você é um redator de roteiros de altíssima conversão.
        Siga as regras de marca, público e tom do canal:
        
        [BRAND BIBLE]
        {brand_bible}
        [TARGET AUDIENCE]
        {target_audience}
        [VOICE GUIDE]
        {voice_guide}
        """

        user_prompt = f"""
        Escreva a seção "{section_name}" deste roteiro seguindo a estrutura psicológica exata:

        1. MEDO ESPECÍFICO: Abra com o problema concreto do público referente a este tema.
        2. PERGUNTA SEM RESPOSTA: Termine o bloco do medo com uma questão que gere desconforto.
        3. INFORMAÇÃO: Desenvolva o conteúdo (uma ideia por frase, sem enrolação).
        4. MINI-PAYOFF: Entregue a resposta para a pergunta aberta no início.
        5. REHOOK: Última frase da seção. Feche o loop atual e abra o próximo loop com urgência.

        Contexto:
        - Título do vídeo: {title}
        - Última frase da seção anterior: "{previous_section_last_line}"
        - Tema desta seção: {this_section_theme}
        - Tema da próxima seção: {next_section_theme}

        Escreva 2 variações dessa seção.
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.7)

    def generate_ctas(self, full_script):
        """Skill 6 - Alocação natural de chamados para ação (CTAs)"""
        ctas_config = self._read_config_file("ctas.md")

        system_prompt = f"""
        Você é um especialista em conversão no YouTube.
        Insira os CTAs de forma nativa e sem quebrar a narrativa do vídeo.
        
        [CTAS CONFIG]
        {ctas_config}
        """

        user_prompt = f"""
        Leia o roteiro completo abaixo e determine onde colocar os CTAs nativos:
        
        [ROTEIRO COMPLETO]
        {full_script}

        Regras:
        - Primeiro CTA: após a primeira seção.
        - Segundo CTA: entre os 40% e 60% do vídeo.
        - End Screen CTA: no encerramento.
        
        Retorne a lista com o posicionamento exato, o texto sugerido (máximo 3 frases) e a justificativa psicológica do momento.
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.5)

    def run_collaboration_report(self, generated_script, edited_script):
        """Parte 3 - Feedback Loop: Aprende com as correções do usuário"""
        voice_guide = self._read_config_file("voice_guide.md")

        system_prompt = "Você é um analista linguístico e diretor editorial de canais do YouTube."
        user_prompt = f"""
        Compare a versão do roteiro que o sistema gerou com a versão final que eu editei.
        Identifique o que mudei, os padrões e crie regras concretas para que nas próximas gerações eu não precise repetir essas edições.

        [VERSÃO ORIGINAL DO SISTEMA]
        {generated_script}

        [VERSÃO EDITADA POR MIM]
        {edited_script}

        [GUIDE ATUAL]
        {voice_guide}

        Devolva:
        1. MUDANÇAS ESTRUTURAIS (O que cortei, reorganizei ou movi)
        2. MUDANÇAS DE ESTILO (Frases que mudei, palavras proibidas novas, ajustes de ritmo)
        3. ATUALIZAÇÕES PARA O VOICE GUIDE (Reescreva apenas os trechos do Voice Guide que precisam ser modificados)
        """
        return self._call_llm(system_prompt, user_prompt, temperature=0.5)

    # ══════════════════════════════════════════════════════════════
    # NOVAS SKILLS — 6 Prompts do Sistema Dezafira v2 (Gringa)
    # ══════════════════════════════════════════════════════════════

    def generate_niche_ideas(self, focus_market="Estados Unidos, Canadá, Reino Unido, Austrália"):
        """
        PROMPT #1 — Encontre um nicho que realmente dá dinheiro
        Lista 20 nichos evergreen com alto CPM para o mercado gringo.
        """
        system_prompt = """Você é um estrategista de canais YouTube especializado em monetização internacional.
        Seu foco é encontrar nichos com alto CPM (Cost Per Mille) nos mercados de língua inglesa.
        Você nunca sugere nichos onde o criador precisa aparecer."""
        user_prompt = f"""Liste 20 nichos para canais no YouTube onde eu não precise aparecer.
        Priorize nichos evergreen, com alta demanda nos {focus_market},
        alto potencial de CPM, possibilidade de produzir vídeos utilizando Inteligência Artificial
        e baixa dificuldade para monetizar.

        Para cada nicho, informe:
        - Nome do nicho
        - CPM médio estimado (USD)
        - Público-alvo
        - Facilidade de produção (1-10)
        - Nota de potencial de crescimento (1-10)

        Retorne em formato JSON com uma lista de 20 itens."""
        return self._call_llm(system_prompt, user_prompt, temperature=0.7)

    def generate_viral_ideas(self, niche: str, target_audience: str = "American audience"):
        """
        PROMPT #2 — Descubra vídeos que já provaram funcionar
        Gera 30 ideias de vídeos virais para um nicho específico.
        """
        system_prompt = """Você é um estrategista especialista em YouTube que entende profundamente
        o algoritmo e os gatilhos psicológicos que geram milhões de visualizações.
        Você nunca copia títulos — você entende o formato e cria algo original."""
        user_prompt = f"""Liste 30 ideias de vídeos inspiradas nos formatos que mais viralizam no nicho: "{niche}".

        Não copie títulos. Para cada ideia, explique:
        1. Por que tem potencial para gerar milhões de visualizações
        2. Qual emoção desperta no espectador
        3. Como deixá-la mais interessante para o {target_audience}

        Retorne em formato JSON com lista de 30 ideias."""
        return self._call_llm(system_prompt, user_prompt, temperature=0.8)

    def generate_english_script(
        self,
        theme: str,
        duration_minutes: int = 10,
        brand: str = "Geral",
        trends_context: str = "",
    ):
        """
        PROMPT #3 — Crie um roteiro com alta retenção (em INGLÊS)
        Gera roteiro de ~10 minutos em inglês americano com técnicas de retenção.
        """
        system_prompt = """You are a top YouTube retention scriptwriter.
        You write in American English with natural, easy-to-understand language.
        Your scripts have extreme hooks in the first 10 seconds.
        You maintain curiosity throughout using questions and gradual revelations.
        You avoid long introductions.
        You end by encouraging the viewer to watch another video."""
        user_prompt = f"""Write a {duration_minutes}-minute retention script about: "{theme}" (Niche: {brand}).
        {trends_context}

        RULES:
        - Start with an extremely strong hook in the first 10 seconds
        - Maintain curiosity throughout using questions and gradual revelations
        - Avoid long introductions
        - End by encouraging the viewer to watch another video from the channel
        - Write in American English, natural and easy to understand
        - Target approximately {duration_minutes * 150} words

        Return a JSON object:
        {{
            "title": "Clickable title with curiosity gap (max 60 chars)",
            "script": "Full script text in English",
            "visual_keywords": ["keyword1", "keyword2", ...],
            "target_duration_seconds": {duration_minutes * 60},
            "hook": "The first 10-second hook"
        }}"""
        return self._call_llm(system_prompt, user_prompt, temperature=0.7)

    def generate_scene_guide(self, script_text: str, title: str):
        """
        PROMPT #4 — Transforme o roteiro em um vídeo pronto
        Cria um guia de edição cena-por-cena com classificação PEXELS ou AI_IMAGE.
        """
        system_prompt = """You are a video production director.
        You break down scripts into individual scenes.
        For each scene, you decide if it needs:
        - PEXELS: Generic stock footage that exists on Pexels (nature, city, people working, etc.)
        - AI_IMAGE: A specific visual concept that needs AI generation (abstract concepts, specific illustrations)

        You organize everything in chronological order with exact timestamps."""
        user_prompt = f"""Take this script and create a complete scene-by-scene editing guide.
        Title: "{title}"

        Script:
        {script_text}

        For each segment, indicate:
        1. Timestamp (start-end in seconds)
        2. Narration text for this segment
        3. Scene type: "PEXELS" or "AI_IMAGE"
        4. Visual prompt (for Pexels search or AI image generation)
        5. Duration in seconds

        Return a JSON object with a list of scenes in chronological order:
        {{
            "scenes": [
                {{
                    "scene_id": 1,
                    "start_time": 0,
                    "end_time": 8,
                    "narration": "text for this segment",
                    "type": "PEXELS",
                    "visual_prompt": "search keywords",
                    "duration": 8
                }}
            ]
        }}"""
        return self._call_llm(system_prompt, user_prompt, temperature=0.5)

    def generate_titles_thumbnails(self, script_text: str, title: str):
        """
        PROMPT #5 — Crie um vídeo impossível de ignorar
        Gera 20 títulos clicáveis + 10 ideias de miniaturas.
        """
        system_prompt = """You are a YouTube CTR optimization specialist.
        You create curiosity-gap titles and emotion-driven thumbnails
        that maximize click-through rate in the YouTube algorithm."""
        user_prompt = f"""Based on this script, create:

        SCRIPT TITLE: {title}

        SCRIPT:
        {script_text}

        1. 20 highly clickable titles using curiosity triggers
        2. 10 thumbnail ideas that spark emotion and increase CTR

        For each title, explain why it performs well in the algorithm.
        For each thumbnail, describe the visual composition, colors, and text overlay.

        Return as JSON:
        {{
            "titles": [
                {{"title": "...", "reason": "...", "expected_ctr_boost": "high/medium/low"}}
            ],
            "thumbnails": [
                {{"description": "...", "emotion": "...", "composition": "..."}}
            ]
        }}"""
        return self._call_llm(system_prompt, user_prompt, temperature=0.8)

    def generate_monetization_plan(self, niche: str, target_market: str = "USA/UK/CA/AU"):
        """
        PROMPT #6 — Monte um plano para monetizar rápido
        Cria um plano de 90 dias para monetizar um canal com IA.
        """
        system_prompt = """You are a YouTube growth strategist specialized in helping creators
        reach monetization requirements as fast as possible using AI tools.
        You create detailed daily action plans."""
        user_prompt = f"""Create a 90-day monetization plan for a YouTube channel in the niche: "{niche}".
        Target market: {target_market}
        Constraint: Use AI tools, no face appearing.

        Include:
        1. Daily production routine
        2. Ideal number of videos per week
        3. View goals and milestones
        4. Strategies to increase retention, CTR, and watch time
        5. Common mistakes to avoid
        6. Actionable checklist for each week

        Return as a structured JSON object with weekly breakdowns."""
        return self._call_llm(system_prompt, user_prompt, temperature=0.7)


if __name__ == "__main__":
    # Teste rápido de integração com LLM
    brain = SniperBrain()
    print("Testando conexão com Nvidia NIM...")
    try:
        res = brain.generate_youtube_titles("Como sair do zero no dropshipping em 2026", "Não precisa de estoque, focar em tráfego orgânico com TikTok, perigos de mineração errada.")
        print(res)
    except Exception as e:
        print(f"Erro no teste: {e}")
