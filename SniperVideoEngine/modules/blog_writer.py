"""
BlogWriter — Motor de Geração de Artigos para Blog.
Gera artigos completos e otimizados para SEO usando LLM.

Pipeline:
  1. Geração de ideias baseada em nicho + tendências
  2. Artigo completo (~1500 palavras) com seções, headings, meta
  3. Slug, excerpt, keywords para SEO
  4. Prompt visual para imagem de destaque (Google Flow)
"""
import asyncio
import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BRAND_DIR = BASE_DIR / "brand_config"

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"


def _load_brand_file(name: str) -> str:
    path = BRAND_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _load_channel_brand(channel_id: str) -> dict:
    """Carrega config de marca do canal específico ou default.
    Prefere versão blog quando disponível."""
    brand = {
        "bible": _load_brand_file("brand_bible.md"),
        "audience": _load_brand_file("target_audience.md"),
        "voice": _load_brand_file("voice_guide.md"),
        "ctas": _load_brand_file("ctas.md"),
    }
    # Tenta carregar versão blog primeiro
    blog_dir = BRAND_DIR / "blog"
    if blog_dir.is_dir():
        for fname in ["brand_bible.md"]:
            fpath = blog_dir / fname
            if fpath.exists():
                brand["bible"] = fpath.read_text(encoding="utf-8")
    # Canal específico
    channel_dir = BRAND_DIR / f"canal_{channel_id}"
    if channel_dir.is_dir():
        for fname in ["brand_bible.md", "target_audience.md", "voice_guide.md", "ctas.md"]:
            fpath = channel_dir / fname
            if fpath.exists():
                brand[fname.replace(".md", "")] = fpath.read_text(encoding="utf-8")
    return brand


async def _call_llm(system_prompt: str, user_prompt: str,
                    temperature: float = 0.8, max_tokens: int = 4096) -> str:
    """Chama Nvidia NIM (fallback DeepSeek)."""
    import httpx
    api_key = os.getenv("NVIDIA_API_KEY", "") or os.getenv("NVAPI_KEY", "")
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY não configurada")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(NVIDIA_API_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        pass

    # Fallback DeepSeek via OpenRouter
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    if deepseek_key:
        headers["Authorization"] = f"Bearer {deepseek_key}"
        payload["model"] = "deepseek-chat"
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                json=payload, headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()

    raise RuntimeError("Todos os LLMs falharam")


def _extract_json(text: str) -> dict:
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
    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"error": "Falha ao extrair JSON", "raw": text[:500]}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text[:100]


async def generate_ideas(nicho: str, count: int = 5, language: str = "pt") -> list:
    """Gera ideias de posts para um nicho."""
    system_prompt = (
        f"Você é um estrategista de conteúdo SEO. Gere {count} ideias de posts "
        f"para blogs no nicho: {nicho}. "
        "Cada ideia deve incluir: título gancho, palavra-chave principal, "
        "e uma breve descrição do que o post abordará. "
        "Retorne APENAS JSON array: [{\"title\": \"...\", \"keyword\": \"...\", \"description\": \"...\"}]"
    )
    user_prompt = f"Gere {count} ideias de posts para blog sobre {nicho} em {language}."
    raw = await _call_llm(system_prompt, user_prompt, temperature=0.9, max_tokens=2048)

    try:
        ideas = json.loads(raw) if raw.startswith("[") else json.loads(re.search(r'\[.*\]', raw, re.DOTALL).group())
        return ideas[:count]
    except Exception:
        return [{"title": nicho, "keyword": nicho, "description": f"Artigo sobre {nicho}"}]


async def generate_full_article(
    topic: str,
    channel_id: str = "default",
    language: str = "pt",
    target_words: int = 1500,
    keywords: str = "",
) -> dict:
    """
    Gera artigo completo para blog.

    Returns:
        dict com title, slug, content (HTML), excerpt, keywords, featured_image_prompt
    """
    brand = _load_channel_brand(channel_id)
    brand_context = "\n".join([
        f"=== BRAND BIBLE ===\n{brand['bible']}" if brand['bible'] else "",
        f"=== TARGET AUDIENCE ===\n{brand['audience']}" if brand['audience'] else "",
        f"=== VOICE GUIDE ===\n{brand['voice']}" if brand['voice'] else "",
    ]).strip()

    blog_examples = _load_brand_file("blog/examples.json")
    examples_str = ""
    if blog_examples:
        try:
            ex_list = json.loads(blog_examples)
            examples_str = "\n\nExemplos de referência:\n" + "\n".join(
                [f"- Título: {e['title']}\n  Meta: {e['meta_description']}\n  Estrutura: headings H2 + parágrafos curtos\n  Keywords: {e['keywords']}" for e in ex_list[:2]]
            )
        except Exception:
            pass

    system_prompt = f"""Você é um redator SEO especializado em artigos para blog.
{brand_context}
{examples_str}

Diretrizes:
- Tom: direto ao ponto, curioso, revelador (mesmo tom dos vídeos)
- Escreva em 2ª pessoa ("você")
- Parágrafos curtos (2-4 frases)
- Headings H2/H3 para organizar
- Introdução com gancho forte
- Conclusão com CTA sutil
- {target_words} palavras no total
- Use subtítulos H2 para cada seção, e H3 para subseções
- Se for o nicho da marca, use as CTAs definidas naturalmente
- Idioma: {language}

Retorne APENAS JSON:
{{
  "title": "Título SEO amigável (máx 60 chars)",
  "slug": "url-friendly-slug",
  "meta_description": "Meta descrição para SEO (máx 160 chars)",
  "keywords": "palavra-chave1, palavra-chave2, palavra-chave3",
  "content_html": "<h2>Seção 1</h2><p>Conteúdo...</p><h2>Seção 2</h2><p>Conteúdo...</p>",
  "excerpt": "Resumo curto para home page",
  "featured_image_prompt": "Prompt em inglês para gerar imagem de destaque no Google Flow sobre {topic}",
  "word_count": número_estimado
}}"""

    user_prompt = f"""Escreva um artigo completo e original sobre:

TÓPICO: {topic}
PALAVRAS-CHAVE: {keywords if keywords else topic}
IDIOMA: {language}
PALAVRAS: ~{target_words}

O artigo precisa ser útil, original e com profundidade real. Nada de conteúdo genérico."""
    raw = await _call_llm(system_prompt, user_prompt, temperature=0.75, max_tokens=8192)
    result = _extract_json(raw)

    if "error" in result:
        return result

    result["slug"] = result.get("slug", _slugify(result.get("title", topic)))
    result["topic"] = topic
    result["channel_id"] = channel_id
    result["language"] = language
    return result


async def write(topic: str, channel_id: str = "default", language: str = "pt",
                target_words: int = 1500, keywords: str = "") -> dict:
    """Interface principal — gera e salva o artigo no banco."""
    from .database import create_db_blog_post

    article = await generate_full_article(
        topic=topic,
        channel_id=channel_id,
        language=language,
        target_words=target_words,
        keywords=keywords,
    )

    if "error" in article:
        return {"success": False, "error": article["error"]}

    saved = create_db_blog_post(
        channel_id=channel_id,
        title=article["title"],
        slug=article["slug"],
        content=article.get("content_html", ""),
        excerpt=article.get("excerpt", ""),
        keywords=article.get("keywords", keywords),
        topic=topic,
    )

    return {
        "success": True,
        "post_id": saved["id"],
        "title": article["title"],
        "slug": article["slug"],
        "word_count": article.get("word_count", 0),
        "featured_image_prompt": article.get("featured_image_prompt", ""),
        "article": article,
    }