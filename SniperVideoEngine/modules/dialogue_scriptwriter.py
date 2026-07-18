"""
Dialogue ScriptWriter — Gerador de Roteiros em Diálogo para "Com Jesus na Lua"
============================================================================
Gera roteiros em formato de diálogo entre Jesus, Pedrinho e Lívia.
Usa DeepSeek 3-pass para criar conteúdo consistente e envolvente.
"""
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
BRAND_DIR = BASE_DIR / "brand_config" / "canal_jesus_lua"
OUTPUT_DIR = BASE_DIR / "outputs" / "scripts"

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def _load_file(name: str) -> str:
    path = BRAND_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


async def _call_llm(system_prompt: str, user_prompt: str,
                     temperature: float = 0.8, max_tokens: int = 4096) -> str:
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

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(DEEPSEEK_API_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek erro {resp.status_code}: {resp.text[:300]}")
        return resp.json()["choices"][0]["message"]["content"]


# ─── SYSTEM PROMPTS ──────────────────────────────────────────────────────────

SYSTEM_PASS1 = """Voce e um roteirista criativo para o canal "Com Jesus na Lua".
Canal: Jesus, sentado na Lua com duas criancas (Pedrinho, 12 anos, e Livia, 4 anos), olhando para a Terra e conversando.

PERSONAGENS:
- JESUS: Calmo, profundo, sabio. Fala com pausa e segurança. Usa historias e exemplos.
- PEDRINHO (12): Curioso, direto, sem filtro. Faz perguntas que todo mundo quer fazer.
- LIVIA (4): Inocente, curiosa, faz perguntas simples que revelam verdades profundas.

REGRAS:
1. Cada fala de Jesus deve ter uma REACAO de uma das criancas
2. Perguntas das criancas devem ser GENUINAS
3. Jesus nunca responde com sermão — responde com HISTORIA ou EXEMPLO
4. Usar referencias visuais: "Imagina que voce esta ali..."
5. Dados especificos: livro, capitulo, versiculo
6. Tom carinhoso, sabio, surpreendente
7. NUNCA usar: "Ola pessoal", "Neste video", "Fique ate o final", "Deixe seu like"

FORMATO DE SAIDA (JSON):
{
  "title": "titulo do episodio",
  "topic": "tema principal",
  "duration_estimate": "X-Y minutos",
  "biblical_reference": "livro cap:versiculo",
  "dialogue": [
    {"character": "livia", "text": "fala da Livia"},
    {"character": "jesus", "text": "fala de Jesus"},
    {"character": "pedrinho", "text": "fala do Pedrinho"}
  ],
  "visual_inserts": [
    {"after_line": 2, "description": "descricao da cena visual para gerar imagem"}
  ],
  "closing_reflection": "reflexao final de Jesus"
}"""


SYSTEM_PASS2 = """Voce e um editor de roteiro especializado em dialogo para video.
Analise o roteiro fornecido e melhore:
1. Ritmo — alternancia rapida entre personagens, sem falas longas demais
2. Naturalidade — as criancas falam como criancas reais
3. Impacto — cada secao deve ter um "aha moment"
4. Visual — sugira inserts visuais para cenas bibliicas
5. Tempo — ajuste para duracao alvo (2-5 minutos)

Mantenha a estrutura JSON. Apenas melhore as falas."""


SYSTEM_PASS3 = """Voce e um prompt engineer para geração de imagens.
Para cada INSERT VISUAL do roteiro, gere um prompt detalhado para FLUX.2 Klein 4B.

PROMPTS DEVEM SER:
- Em ingles
- Descriptivos e concretos
- Incluir: estilo (photorealistic, cinematic, 8K), iluminacao, composicao
- NAO incluir: texto, legendas, marcas d'agua

Personagens:
- Jesus: Middle Eastern man, 30s, olive skin, dark brown wavy shoulder-length hair, short beard, white tunic, beige mantle
- Pedrinho: Brazilian boy age 12, brown skin, short messy dark brown hair, navy blue t-shirt, jeans
- Livia: Brazilian girl age 4, brown skin, long dark brown ponytail, purple star dress

Adicione os prompts ao JSON sob a chave "image_prompts"."""


# ─── PASSO 1: Gerar_dialogue ────────────────────────────────────────────────

async def pass1_generate_dialogue(
    topic: str,
    template: str = "pergunta_simples",
    biblical_reference: str = "",
) -> Dict:
    """Passo 1: Gera o diálogo base."""
    user_prompt = f"""Gere um episodio para o canal "Com Jesus na Lua".

TEMA: {topic}
TEMPLATE: {template}
REFERENCIA BIBLICA: {biblical_reference or 'a definir pelo modelo'}

Gere o dialogue completo em JSON."""

    response = await _call_llm(SYSTEM_PASS1, user_prompt, temperature=0.85)
    try:
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {
            "title": topic,
            "topic": topic,
            "dialogue": [],
            "error": "Falha ao parsear resposta do LLM",
            "raw_response": response,
        }


# ─── PASSO 2: Refinar Ritmo ────────────────────────────────────────────────

async def pass2_refine_rhythm(script: Dict, target_minutes: float = 3.0) -> Dict:
    """Passo 2: Refina ritmo e naturalidade."""
    user_prompt = f"""Roteiro para refinar (alvo: {target_minutes} minutos):

{json.dumps(script, ensure_ascii=False, indent=2)}

Melhore o ritmo, naturalidade e impacto. Mantenha JSON."""

    response = await _call_llm(SYSTEM_PASS2, user_prompt, temperature=0.7)
    try:
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(json_str)
    except json.JSONDecodeError:
        return script


# ─── PASSO 3: Gerar Prompts Visuais ────────────────────────────────────────

async def pass3_generate_visual_prompts(script: Dict) -> Dict:
    """Passo 3: Gera prompts de imagem para inserts visuais."""
    user_prompt = f"""Roteiro com inserts visuais:

{json.dumps(script, ensure_ascii=False, indent=2)}

Gere prompts de imagem para cada insert."""

    response = await _call_llm(SYSTEM_PASS3, user_prompt, temperature=0.6)
    try:
        json_str = response.strip()
        if json_str.startswith("```"):
            json_str = json_str.split("\n", 1)[1].rsplit("```", 1)[0]
        enhanced = json.loads(json_str)
        script["image_prompts"] = enhanced.get("image_prompts", [])
        return script
    except json.JSONDecodeError:
        return script


# ─── PIPELINE COMPLETO ──────────────────────────────────────────────────────

async def generate_episode(
    topic: str,
    template: str = "pergunta_simples",
    biblical_reference: str = "",
    target_minutes: float = 3.0,
) -> Dict:
    """Gera episodio completo em 3 passos.

    Args:
        topic: Tema/pergunta principal do episodio
        template: Template de estrutura (pergunta_simples, profecia, comparacao)
        biblical_reference: Referencia biblica especifica
        target_minutes: Duracao alvo em minutos

    Returns:
        Dict com roteiro completo, prompts visuais e metadados
    """
    print(f"[DialogueScript] Passo 1: Gerando dialogo para '{topic}'...")
    script = await pass1_generate_dialogue(topic, template, biblical_reference)

    print(f"[DialogueScript] Passo 2: Refinando ritmo...")
    script = await pass2_refine_rhythm(script, target_minutes)

    print(f"[DialogueScript] Passo 3: Gerando prompts visuais...")
    script = await pass3_generate_visual_prompts(script)

    # Salvar resultado
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = int(time.time())
    filename = f"ep_{timestamp}.json"
    output_path = OUTPUT_DIR / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"[DialogueScript] Salvo: {output_path}")
    script["output_path"] = str(output_path)

    return script


def format_dialogue_for_display(script: Dict) -> str:
    """Formata dialogue para exibicao amigavel."""
    lines = []
    title = script.get("title", "Sem titulo")
    topic = script.get("topic", "")
    duration = script.get("duration_estimate", "")
    ref = script.get("biblical_reference", "")

    lines.append(f"=== {title} ===")
    lines.append(f"Tema: {topic}")
    lines.append(f"Duracao: {duration}")
    if ref:
        lines.append(f"Ref: {ref}")
    lines.append("")

    for i, line in enumerate(script.get("dialogue", [])):
        char = line.get("character", "").capitalize()
        text = line.get("text", "")
        lines.append(f"{char}: {text}")
        lines.append("")

    if script.get("closing_reflection"):
        lines.append(f"Jesus (reflexao): {script['closing_reflection']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "Por que a Terra e redonda?"
    result = asyncio.run(generate_episode(topic))
    print(format_dialogue_for_display(result))
