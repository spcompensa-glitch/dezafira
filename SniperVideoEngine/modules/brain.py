import os
import json
import requests
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

class SniperBrain:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.nvidia_key = os.getenv("NVIDIA_API_KEY")
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brand_config")

    def _read_config_file(self, filename):
        file_path = os.path.join(self.config_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"[Arquivo {filename} não configurado. Por favor, adicione as diretrizes.]"

    def _call_deepseek(self, system_prompt, user_prompt, temperature=0.7):
        # 1. Tentar Nvidia NIM API (Llama 3.3 70b)
        if self.nvidia_key:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.nvidia_key}"
                }
                payload = {
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 1500
                }
                response = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=25.0)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[LLM-Nvidia] Falha no status ({response.status_code}): {response.text}")
            except Exception as e:
                print(f"[LLM-Nvidia] Erro na chamada: {e}")

        # 2. Fallback para Deepseek API
        if self.api_key:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature
                }
                response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload, timeout=25.0)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[LLM-Deepseek] Erro na chamada: {e}")
                raise e

        raise ValueError("Nenhuma chave válida encontrada (NVIDIA_API_KEY ou DEEPSEEK_API_KEY) no arquivo .env para processar a inteligência do roteiro.")

    def generate_script(self, theme, brand="Geral"):
        """Gera o roteiro, título, prompts visuais e clima musical unificados para a Dezafira em JSON"""
        brand_bible = self._read_config_file("brand_bible.md")
        target_audience = self._read_config_file("target_audience.md")
        voice_guide = self._read_config_file("voice_guide.md")
        
        system_prompt = f"""
        Você é o Roteirista e Diretor Executivo da Dezafira, especialista em criar vídeos curtos altamente virais de alta conversão (para YouTube Shorts/TikTok).
        Use as diretrizes abaixo para formatar o tom de voz e estilo do roteiro:
        
        [BRAND BIBLE]
        {brand_bible}
        
        [TARGET AUDIENCE]
        {target_audience}
        
        [VOICE GUIDE]
        {voice_guide}
        """
        
        user_prompt = f"""
        Gere um plano de vídeo completo em formato JSON para o tema: "{theme}" (Nicho: {brand}).
        O vídeo deve ter alta retenção nos primeiros 3 segundos e seguir as diretrizes do YouTube contra conteúdo reutilizado (crie um roteiro profundo, autoral e com forte storytelling).
        
        Retorne estritamente um objeto JSON com o seguinte formato, sem blocos de texto explicativos adicionais antes ou depois:
        {{
            "title": "Título com alta tensão emocional e menos de 60 caracteres",
            "script": "Texto corrido que será narrado de forma com excelente entonação (máximo 120 palavras para um vídeo de 40-50 segundos). Escreva de forma fluida.",
            "visual_prompts": ["Prompt visual detalhado em inglês para o clipe 1", "Prompt visual detalhado em inglês para o clipe 2", "Prompt visual detalhado em inglês para o clipe 3"],
            "music_prompt": "Clima musical sugerido (ex: dark techno, epic motivation, ambient tech)",
            "target_duration": 45
        }}
        """
        
        try:
            res_text = self._call_deepseek(system_prompt, user_prompt, temperature=0.7)
            # Limpar o texto se a IA colocar marcações de markdown ```json
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()
            
            return json.loads(res_text.strip())
        except Exception as e:
            print(f"[Brain] Falha ao processar resposta estruturada do LLM: {e}")
            # Fallback em caso de erro de parsing JSON
            return {
                "title": f"Segredo do {brand}: {theme}",
                "script": f"Você já se perguntou sobre {theme}? A maioria das pessoas erra feio tentando fazer isso sozinho. Mas a verdade é bem mais simples. Se você focar no método correto, os resultados aparecem de verdade.",
                "visual_prompts": ["High quality cinematic shot of a person thinking about success, dark ambient lighting"],
                "music_prompt": "ambient tech",
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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.8)

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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.7)

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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.3)

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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.7)

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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.7)

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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.5)

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
        return self._call_deepseek(system_prompt, user_prompt, temperature=0.5)

if __name__ == "__main__":
    # Teste rápido de integração com DeepSeek
    brain = SniperBrain()
    print("Testando conexão com a API DeepSeek...")
    try:
        res = brain.generate_youtube_titles("Como sair do zero no dropshipping em 2026", "Não precisa de estoque, focar em tráfego orgânico com TikTok, perigos de mineração errada.")
        print(res)
    except Exception as e:
        print(f"Erro no teste: {e}")
