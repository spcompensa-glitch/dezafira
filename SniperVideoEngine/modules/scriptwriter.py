"""
ScriptWriter v2 — Motor de Roteiro Viral para YouTube.

Arquitetura de 3 passes:
  1. Tema + Título (5 opções com análise de tensão)
  2. Roteiro Completo (2ª pessoa, ritmo curto, arco Hook→Reframe→Deep Dive→Twist→Echo)
  3. Timestamps + Prompts Visuais (1 prompt por ~5 segundos, style anchor + lock)

Diferenças do v1:
- Voz em 2ª pessoa ("você") — nunca "nós" ou "eu"
- Ritmo: frase curta (max 12-15 palavras) + pergunta a cada 4-6 frases
- Arco: Hook → Reframe → Deep Dive → Twist → Echo final
- Saída com timestamps[] — cada linha = 1 timestamp com prompt visual
- Prompts visuais com style anchor + style lock fixos
"""
import asyncio
import json
import os
import re
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BRAND_DIR = BASE_DIR / "brand_config"

# ─── Config ───────────────────────────────────────────────────────────────────

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# Intervalo em segundos entre timestamps (1 prompt visual a cada N segundos)
TIMESTAMP_INTERVAL = 5


def _load_file(name: str) -> str:
    """Carrega um arquivo de brand config."""
    path = BRAND_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _load_examples() -> list:
    """Carrega few-shot examples."""
    path = BRAND_DIR / "examples.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _load_channel_memory(channel_id: str = "default") -> str:
    """Carrega contexto de memória do canal."""
    try:
        from services.memory_service import get_channel_context_prompt
        return get_channel_context_prompt(channel_id)
    except Exception:
        return ""


async def _call_llm(system_prompt: str, user_prompt: str,
                     temperature: float = 0.8, max_tokens: int = 4096) -> str:
    """Chama DeepSeek API."""
    import httpx
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY não configurada")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()


def _extract_json(text: str) -> dict:
    """Extrai JSON de uma resposta LLM."""
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def _extract_json_array(text: str) -> list:
    """Extrai array JSON de uma resposta LLM."""
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except Exception:
        pass
    m = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(1))
            if isinstance(result, list):
                return result
        except Exception:
            pass
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return []


def _count_words(text: str) -> int:
    """Conta palavras."""
    return len(text.split())


def _fmt_timestamp(seconds: float) -> str:
    """Converte segundos para MM:SS."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def _validate_script(script: str, target_words: int) -> dict:
    """Valida qualidade do roteiro v2."""
    errors = []
    warnings = []
    word_count = _count_words(script)

    # Word count (tolerância maior para v2)
    tolerance = target_words * 0.20
    if abs(word_count - target_words) > tolerance:
        warnings.append(f"Word count {word_count} difere do target {target_words}")

    # Greetings check
    lower = script.lower().strip()
    greetings = ["olá pessoal", "olá todos", "hello everyone", "hi guys",
                 "neste vídeo", "neste video", "sejam bem-vindos",
                 "olá", "olá galera"]
    for g in greetings:
        if lower.startswith(g):
            errors.append(f"Roteiro começa com greeting: '{g}'")

    # 2ª pessoa check — procura "eu" no início de frases
    sentences = [s.strip() for s in re.split(r'[.!?]', script) if s.strip()]
    first_person = ["eu ", "eu sou", "eu vou", "eu acho", "eu penso"]
    for s in sentences[:10]:  # só as primeiras 10 frases
        sl = s.lower()
        for fp in first_person:
            if sl.startswith(fp):
                warnings.append(f"Possível 1ª pessoa no início: '{s[:50]}...'")
                break

    # Max sentence length (15 palavras para v2)
    long_count = 0
    for s in sentences:
        wc = len(s.split())
        if wc > 15:
            long_count += 1
    if long_count > len(sentences) * 0.3:
        warnings.append(f"{long_count} frases com mais de 15 palavras (máx 30%)")

    # Pergunta check (deve ter pelo menos 1 pergunta a cada ~10 frases)
    questions = [s for s in sentences if s.strip().endswith('?')]
    if len(sentences) > 5 and len(questions) == 0:
        warnings.append("Nenhuma pergunta no roteiro (meta: 1 a cada 4-6 frases)")

    return {
        "valid": len(errors) == 0,
        "word_count": word_count,
        "target_words": target_words,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_timestamps(timestamps: list, target_seconds: int) -> dict:
    """Valida a lista de timestamps."""
    errors = []
    warnings = []

    if not timestamps:
        errors.append("Nenhum timestamp gerado")
        return {"valid": False, "count": 0, "errors": errors, "warnings": warnings}

    # Check timestamps cobrem todo o vídeo
    expected_count = max(1, target_seconds // TIMESTAMP_INTERVAL)
    if len(timestamps) < expected_count * 0.7:
        warnings.append(f"Poucos timestamps: {len(timestamps)} (esperado ~{expected_count})")

    # Check cada timestamp tem narration e image_prompt
    for i, ts in enumerate(timestamps):
        if not ts.get("narration"):
            errors.append(f"Timestamp {i} sem narração")
        if not ts.get("image_prompt"):
            errors.append(f"Timestamp {i} sem prompt visual")

    # Check ordem cronológica
    for i in range(1, len(timestamps)):
        t_prev = timestamps[i-1].get("time", "00:00")
        t_curr = timestamps[i].get("time", "00:00")
        if t_curr <= t_prev:
            warnings.append(f"Timestamps fora de ordem: {t_prev} -> {t_curr}")

    return {
        "valid": len(errors) == 0,
        "count": len(timestamps),
        "errors": errors,
        "warnings": warnings,
    }


class ScriptWriter:
    """Motor de roteiro viral v2 — 3 passes."""

    def __init__(self, channel_id: str = "default"):
        self.channel_id = channel_id
        self.brand_bible = _load_file("brand_bible.md")
        self.voice_guide = _load_file("voice_guide.md")
        self.target_audience = _load_file("target_audience.md")
        self.examples = _load_examples()
        self.channel_memory = _load_channel_memory(channel_id)
        self.pass_results = {}

    async def write(self, theme: str, target_seconds: int = 60,
                    language: str = "pt", video_format: str = "vertical",
                    on_progress=None) -> dict:
        """
        Gera roteiro completo em 3 passes.

        Returns:
            dict com title, script, timestamps[], word_count, quality, etc
        """
        if on_progress:
            on_progress("script", 0, "Iniciando ScriptWriter v2...")

        # Para vídeos curtos (60s), ~150-200 palavras
        # Para vídeos longos (120s), ~250-350 palavras
        # Fórmula: 2.5 palavras/segundo (ritmo mais lento = mais impacto)
        target_words = int(target_seconds * 2.5)

        # ═══ PASS 1: TÍTULO ═══
        if on_progress:
            on_progress("script", 10, "Pass 1/3: Gerando títulos virais...")
        titles = await self._pass_titles(theme, target_seconds)
        self.pass_results["titles"] = titles

        selected_title = titles.get("options", [{}])[0].get("title", theme)
        self.pass_results["selected_title"] = selected_title

        # ═══ PASS 2: ROTEIRO COMPLETO ═══
        if on_progress:
            on_progress("script", 30, "Pass 2/3: Escrevendo roteiro viral...")
        script_result = await self._pass_script(
            selected_title, theme, target_words, target_seconds
        )
        self.pass_results["script"] = script_result

        full_script = script_result.get("full_script", "")

        # ═══ PASS 3: TIMESTAMPS + PROMPTS VISUAIS ═══
        if on_progress:
            on_progress("script", 65, "Pass 3/3: Gerando timestamps e prompts visuais...")
        timestamps = await self._pass_timestamps(
            full_script, selected_title, theme, target_seconds, video_format
        )
        self.pass_results["timestamps"] = timestamps

        # Consolidação final
        word_count = _count_words(full_script)
        duration_estimate = round(word_count / 2.5, 1)

        # Validação
        script_validation = _validate_script(full_script, target_words)
        ts_validation = _validate_timestamps(timestamps, target_seconds)

        result = {
            "title": selected_title,
            "hook": script_result.get("hook", ""),
            "script": full_script,
            "timestamps": timestamps,
            "visual_prompts": [ts.get("image_prompt", "") for ts in timestamps],
            "music_prompt": script_result.get("music_prompt",
                f"Cinematic mysterious, ancient choir, building tension, revelation moment, {target_seconds}s"),
            "target_duration": target_seconds,
            "word_count": word_count,
            "duration_estimate": duration_estimate,
            "key_references": script_result.get("key_references", []),
            "emotional_arc": script_result.get("emotional_arc", []),
            "cta": script_result.get("cta", {}),
            "quality": script_validation,
            "timestamps_validation": ts_validation,
            "pass_results": self.pass_results,
        }

        if on_progress:
            ok = "OK" if script_validation["valid"] else f"{len(script_validation['errors'])} erros"
            ts_ok = f"{len(timestamps)} timestamps" if ts_validation["valid"] else "timestamps com erro"
            on_progress("script", 100,
                        f"Roteiro pronto: {word_count} palavras, {ts_ok}, {ok}")

        return result

    # ─── PASS 1: TÍTULO ───────────────────────────────────────────────────

    async def _pass_titles(self, theme: str, target_seconds: int) -> dict:
        system = f"""Você é um motor de criação de títulos virais para YouTube educativo.

Nicho: {self.brand_bible.split(chr(10))[0] if self.brand_bible else "mistérios bíblicos"}

REGRAS:
1. Gere 5 opções de título
2. Fórmula: [Curiosity Trigger] + [Unexpected Fact]
3. Máximo 60 caracteres
4. NUNCA comece com "Você sabia que 90% das pessoas"
5. Analise tensão emocional de cada título (1-10)
6. Retorne APENAS JSON válido

FORMATO DE SAÍDA:
{{
  "options": [
    {{"title": "...", "tension_score": 8, "why": "..."}}
  ]
}}"""

        user = f"""Gere 5 títulos virais para um vídeo de {target_seconds} segundos sobre: {theme}

O título deve gerar curiosidade imediata e fazer a pessoa parar de scroll.
Seja específico e surpreendente. Use dados reais quando possível."""

        response = await _call_llm(system, user, temperature=0.85)
        return _extract_json(response) or {
            "options": [{"title": theme, "tension_score": 5, "why": "fallback"}]
        }

    # ─── PASS 2: ROTEIRO COMPLETO ─────────────────────────────────────────

    async def _pass_script(self, title: str, theme: str,
                           target_words: int, target_seconds: int) -> dict:
        system = f"""Você é um escritor de roteiro viral para YouTube educativo.
Seu estilo é idêntico aos maiores canais de stick figure animation do YouTube.

REGRAS DE ESCRITA (INVIOLÁVEIS):

1. VOZ: 2ª pessoa o tempo todo — "você", "seu cérebro", "seus olhos", "seus ancestrais".
   NUNCA "nós", "eu", "a gente". Direto ao ponto.

2. RITMO: Frases curtas. Máximo 12-15 palavras por frase. Uma ideia por frase.
   Exemplo: "A Bíblia escondeu um número no Dilúvio que muda tudo."
   NÃO: "Existe um número escondido no relato do Dilúvio que tem o poder de mudar completamente a forma como você enxerga essa história."

3. PERGUNTA: Uma pergunta a cada 4-6 frases. Gera pausa mental no espectador.
   Exemplo: "Mas espera. Por que sete?"

4. DADOS: Números específicos, versículos exatos (livro, capítulo, versículo),
   nomes de pesquisadores/estudos reais. NUNCA "muitas pessoas" — use "apenas 3 das 12 tribos".
   Inclua NO MÍNIMO 3 referências a pesquisadores, estudos ou dados reais.

5. TOM: Curioso e revelador. Como alguém compartilhando uma descoberta que fez.
   NÃO religioso, NÃO professor, NÃO coach. Um amigo que encontrou algo incrível.

6. ARCO NARRATIVO (seguir estritamente):
   a) HOOK (primeiras 4 linhas): Frase impossível de parar de ler. Pico de tensão.
   b) REFRAME: Muda tudo o que o espectador pensava sobre o tema.
   c) DEEP DIVE: Dados reais, estudos, nomes, versículos. Profundidade.
   d) TWIST: A verdade é mais estranha do que parece. Virada counterintuitiva.
   e) ECHO FINAL: A última frase ECOA a primeira linha, completamente reenquadrada.

7. PROIBIDO:
   - Começar com "Olá", "Neste vídeo", "Você sabia que 90%"
   - Frases de impacto vazias ("Isso é incrível!", "Você não vai acreditar")
   - Repetir o mesmo conceito com palavras diferentes
   - Explicações acadêmicas/teológicas densas
   - Tom de sermão/pregação

BRAND:
{self.brand_bible}

VOICE GUIDE:
{self.voice_guide}

PÚBLICO:
{self.target_audience}

EXEMPLOS DE ROTEIROS DE SUCESSO (use como referência de estilo):
{json.dumps(self.examples[:2], ensure_ascii=False, indent=2)}

FORMATO DE SAÍDA (JSON):
{{
  "full_script": "texto completo do roteiro — apenas narração, sem headers, sem bullets",
  "hook": "a primeira frase do roteiro (o hook)",
  "key_references": ["pesquisador/estudo 1", "pesquisador/estudo 2", "pesquisador/estudo 3"],
  "emotional_arc": ["hook", "reframe", "deep_dive", "twist", "echo"],
  "music_prompt": "estilo musical para BGM"
}}"""

        user = f"""Título: {title}
Tema: {theme}
Target: {target_words} palavras ({target_seconds}s de vídeo)

Escreva o roteiro completo. Apenas o texto narrativo — sem headers, sem markdown, sem stage directions.
Siga estritamente o arco: Hook → Reframe → Deep Dive → Twist → Echo.
O script DEVE ter cerca de {target_words} palavras.
Inclua NO MÍNIMO 3 referências reais (pesquisadores, estudos, versículos bíblicos)."""

        response = await _call_llm(system, user, temperature=0.7, max_tokens=4096)
        result = _extract_json(response)

        if not result or not result.get("full_script"):
            # Fallback: usa resposta como texto puro
            lines = [l.strip() for l in response.strip().split('\n') if l.strip()]
            result = {
                "full_script": response.strip(),
                "hook": lines[0] if lines else title,
                "key_references": [],
                "emotional_arc": ["hook", "reframe", "deep_dive", "twist", "echo"],
                "music_prompt": f"Cinematic mysterious, {target_seconds}s",
            }

        result["word_count"] = _count_words(result.get("full_script", ""))
        return result

    # ─── PASS 3: TIMESTAMPS + PROMPTS VISUAIS ─────────────────────────────

    async def _pass_timestamps(self, full_script: str, title: str,
                                theme: str, target_seconds: int,
                                video_format: str) -> list:
        """
        Gera timestamps com prompts visuais para cada intervalo.
        Cada prompt segue o formato:
        [STYLE_ANCHOR] + [CENA CONCRETA] + [STYLE_LOCK]
        """
        aspect = "16:9" if video_format == "horizontal" else "9:16"

        # Style anchor para boneco palito (padrão)
        style_anchor = (
            "Hand-drawn 2D doodle cartoon animation, flat colors, "
            "bold black outlines, slightly imperfect sketchy marker lines"
        )
        style_lock = (
            f"no gradients, no shadows, no textures, no photorealism, no 3D, "
            f"{aspect} aspect ratio, educational YouTube explainer doodle style"
        )

        # Conta quantos timestamps precisamos
        expected_timestamps = max(1, target_seconds // TIMESTAMP_INTERVAL)

        system = f"""Você é um tradutor visual. Para cada linha do roteiro, gere um prompt de imagem.

ESTILO VISUAL PADRÃO (boneco palito / doodle):
{style_anchor}

STYLE LOCK (deve aparecer no FINAL de CADA prompt):
{style_lock}

ANATOMIA DO BONECO (SEMPRE INCLUIR EM CADA PROMPT):
"single stick figure character with exactly 2 arms, 2 legs, 1 large circular head, 2 dot eyes, 1 mouth, expressive thick brow lines, thick black outlines"

NEGATIVE LOCK (SEMPRE INCLUIR NO FINAL ANTES DO STYLE LOCK):
"no extra arms, no extra legs, no extra eyes, no extra heads, no deformed body, no floating limbs, no duplicate character"

FORMATO DE CADA PROMPT:
[MM:SS] {style_anchor}, [DESCRIÇÃO CONCRETA DA CENA com ação específica], character: single stick figure with exactly 2 arms, 2 legs, 1 large circular head, [COR DO BACKGROUND], no extra arms, no extra legs, no extra eyes, no extra heads, no deformed body, {style_lock}

REGRAS:
1. 1 prompt a cada {TIMESTAMP_INTERVAL} segundos (aproximadamente)
2. TOTAL esperado: ~{expected_timestamps} timestamps para {target_seconds}s de vídeo
3. Traduza abstrato em concreto:
   - "seu corpo não sabe a diferença" → stick figure confuso olhando dois objetos idênticos
   - "milhões de anos" → ampulheta gigante com texto ALL CAPS "MILHÕES DE ANOS" no topo
   - "a verdade escondida" → stick figure abrindo uma porta secreta
   - "o amor entre irmãos" → two stick figures hugging warmly
4. Segure cenas: 3+ linhas sobre o mesmo momento = mesmo cenário, só mude expressão/elemento
5. Cores por tom:
   - Antigo/pré-histórico → tan background
   - Perigo/ameaça → white background with red accents
   - Feliz/triunfo → bright white or yellow background
   - Água/ciência → solid blue background
   - Natureza/evolução → green ground + blue sky
   - Fogo/noite/ritual → solid orange background
   - Amor/carinho → soft pink background
   - Tristeza → light gray background
6. Frame types (quando apropriado):
   - Concept text: objeto grande centralizado + texto ALL CAPS no topo
   - Evolution sequence: progressão esquerda→direita com seta
   - Labeled diagram: seta amarela + palavra ALL CAPS
   - Stick figure reaction: thought bubble com "?", "HMMMM", "!"
   - Villain personified: conceito abstrato com cara de raiva
   - Globe + creatures: Terra ao centro, criaturas ao redor
   - Duo scene: two stick figures together, interacting
7. NUNCA inclua: texto ilegível, logos, marcas d'água, pessoas extras
8. O character DEVE ser o mesmo em todas as cenas (stick figure consistente)
9. CADA prompt DEVE ter exatamente 1 stick figure (ou 2 se for cena de duo)
10. NUNCA descreva "multiple people", "crowd", "group" — sempre stick figure(s) específico(s)

RETORNE APENAS UM ARRAY JSON:
[
  {{"time": "00:00", "narration": "primeira frase da narração", "image_prompt": "prompt completo em inglês"}},
  ...
]"""

        user = f"""Título: {title}
Tema: {theme}

Roteiro completo:
{full_script}

Gere um prompt visual para cada {TIMESTAMP_INTERVAL} segundos do vídeo.
TOTAL: ~{expected_timestamps} timestamps.
Um prompt por objeto no array. Comece em 00:00.
Cada image_prompt DEVE começar com o style anchor e terminar com o style lock."""

        response = await _call_llm(system, user, temperature=0.75, max_tokens=8192)

        # Tenta extrair array JSON
        timestamps = _extract_json_array(response)

        if not timestamps:
            # Fallback: tenta extraiar de linha por linha
            timestamps = self._parse_timestamps_from_text(response, style_anchor, style_lock)

        # Se ainda não tem timestamps, gera a partir do script
        if not timestamps:
            timestamps = self._generate_fallback_timestamps(
                full_script, target_seconds, style_anchor, style_lock
            )

        # Valida e ajusta timestamps
        timestamps = self._normalize_timestamps(timestamps, target_seconds)

        return timestamps

    def _parse_timestamps_from_text(self, text: str, style_anchor: str,
                                     style_lock: str) -> list:
        """Tenta extrair timestamps de texto formatado (não-JSON)."""
        timestamps = []
        # Padrão: [MM:SS] seguido de texto
        pattern = r'\[(\d{2}:\d{2})\]\s*(.*?)(?=\[\d{2}:\d{2}\]|$)'
        matches = re.findall(pattern, text, re.DOTALL)

        for time_str, content in matches:
            content = content.strip()
            if not content:
                continue

            # Se já tem style anchor, usa como está
            if style_anchor[:20] in content:
                prompt = content
            else:
                prompt = f"{style_anchor}, {content}, {style_lock}"

            timestamps.append({
                "time": time_str,
                "narration": "",
                "image_prompt": prompt,
            })

        return timestamps

    def _generate_fallback_timestamps(self, script: str, target_seconds: int,
                                       style_anchor: str, style_lock: str) -> list:
        """Gera timestamps fallback dividindo o script em partes iguais."""
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', script) if s.strip()]
        if not sentences:
            return []

        count = max(1, target_seconds // TIMESTAMP_INTERVAL)
        timestamps = []
        sentences_per_ts = max(1, len(sentences) // count)

        anatomy = (
            "single stick figure with exactly 2 arms, 2 legs, "
            "1 large circular head, 2 dot eyes, thick black outlines"
        )
        negative = (
            "no extra arms, no extra legs, no extra eyes, no extra heads, "
            "no deformed body, no floating limbs"
        )

        for i in range(count):
            start_idx = i * sentences_per_ts
            end_idx = min(start_idx + sentences_per_ts, len(sentences))
            chunk = ' '.join(sentences[start_idx:end_idx])

            time_sec = i * TIMESTAMP_INTERVAL
            time_str = _fmt_timestamp(time_sec)

            # Detecta tom básico para cor
            lower = chunk.lower()
            if any(w in lower for w in ["amor", "abraço", "carinho", "irmão", "família"]):
                bg = "soft pink background"
            elif any(w in lower for w in ["perigo", "morte", "medo", "ameaça"]):
                bg = "white background with red accents"
            elif any(w in lower for w in ["ciência", "estudo", "pesquisa"]):
                bg = "solid blue background"
            elif any(w in lower for w in ["natureza", "evolução", "céu"]):
                bg = "green ground with blue sky"
            else:
                bg = "white background"

            prompt = (
                f"{style_anchor}, {anatomy}, "
                f"character performing action in a scene, {bg}, "
                f"{negative}, {style_lock}"
            )

            timestamps.append({
                "time": time_str,
                "narration": chunk,
                "image_prompt": prompt,
            })

        return timestamps

    def _normalize_timestamps(self, timestamps: list, target_seconds: int) -> list:
        """Normaliza timestamps para garantir cobertura do vídeo inteiro."""
        if not timestamps:
            return timestamps

        # Garante que o último timestamp cobre o fim do vídeo
        last_time = timestamps[-1].get("time", "00:00")
        last_seconds = int(last_time.split(':')[0]) * 60 + int(last_time.split(':')[1])

        if last_seconds < target_seconds - TIMESTAMP_INTERVAL:
            timestamps.append({
                "time": _fmt_timestamp(target_seconds - 5),
                "narration": "",
                "image_prompt": timestamps[-1].get("image_prompt", ""),
            })

        return timestamps


# ─── Função de conveniência (compatibilidade com pipeline) ─────────────────

async def generate_script(theme: str, channel_id: str = "default",
                          target_duration: int = 60,
                          video_format: str = "vertical",
                          language: str = "pt",
                          on_progress=None) -> dict:
    """Função principal de geração de roteiro. Compatível com o pipeline."""
    writer = ScriptWriter(channel_id=channel_id)
    result = await writer.write(
        theme=theme,
        target_seconds=target_duration,
        language=language,
        video_format=video_format,
        on_progress=on_progress,
    )
    return result
