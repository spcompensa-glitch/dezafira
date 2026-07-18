"""
SEO Optimizer — Motor de Otimização para Blogs.
Gera automaticamente:
  - Schema JSON-LD (Article, BlogPosting, FAQ, etc)
  - Meta tags Open Graph + Twitter Cards
  - Internal linking suggestions
  - SEO scoring e gaps analysis
"""
import json
import re
from datetime import datetime
from typing import Optional


def build_schema_article(
    title: str,
    description: str,
    url: str = "",
    site_name: str = "Dezafira Blog",
    author: str = "Dezafira",
    published_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    image_url: str = "",
    keywords: str = "",
) -> dict:
    """Gera Schema.org JSON-LD no formato Article/BlogPosting."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": {
            "@type": "Person",
            "name": author,
        },
        "publisher": {
            "@type": "Organization",
            "name": site_name,
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
        "datePublished": published_at or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dateModified": updated_at or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if image_url:
        schema["image"] = image_url
    if keywords:
        schema["keywords"] = keywords
    return schema


def build_schema_faq(questions_answers: list) -> dict:
    """Gera Schema.org FAQPage a partir de pares pergunta/resposta."""
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": qa.get("question", ""),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": qa.get("answer", ""),
                },
            }
            for qa in questions_answers
        ],
    }


def build_schema_breadcrumb(items: list) -> dict:
    """Gera Schema.org BreadcrumbList."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "name": item.get("name", ""),
                "item": item.get("url", ""),
            }
            for i, item in enumerate(items)
        ],
    }


def build_meta_tags(
    title: str,
    description: str,
    url: str = "",
    image_url: str = "",
    site_name: str = "Dezafira Blog",
    keywords: str = "",
    author: str = "Dezafira",
    locale: str = "pt_BR",
) -> str:
    """Gera HTML de meta tags Open Graph + Twitter Cards."""
    tags = [
        f'<meta charset="UTF-8" />',
        f'<title>{_escape_html(title)}</title>',
        f'<meta name="description" content="{_escape_html(description)}" />',
        f'<meta name="author" content="{_escape_html(author)}" />',
    ]
    if keywords:
        tags.append(f'<meta name="keywords" content="{_escape_html(keywords)}" />')

    tags += [
        f'<meta property="og:title" content="{_escape_html(title)}" />',
        f'<meta property="og:description" content="{_escape_html(description)}" />',
        f'<meta property="og:type" content="article" />',
        f'<meta property="og:locale" content="{locale}" />',
        f'<meta property="og:site_name" content="{_escape_html(site_name)}" />',
    ]
    if url:
        tags.append(f'<meta property="og:url" content="{_escape_html(url)}" />')
    if image_url:
        tags.append(f'<meta property="og:image" content="{_escape_html(image_url)}" />')

    tags += [
        f'<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{_escape_html(title)}" />',
        f'<meta name="twitter:description" content="{_escape_html(description)}" />',
    ]
    if image_url:
        tags.append(f'<meta name="twitter:image" content="{_escape_html(image_url)}" />')

    return "\n".join(tags)


def generate_schema_html(schema: dict) -> str:
    """Converte schema dict em tag script JSON-LD."""
    return (
        '<script type="application/ld+json">\n'
        f'{json.dumps(schema, ensure_ascii=False, indent=2)}\n'
        '</script>'
    )


def build_head_html(
    title: str,
    description: str,
    url: str = "",
    image_url: str = "",
    site_name: str = "Dezafira Blog",
    keywords: str = "",
    author: str = "Dezafira",
    canonical_url: str = "",
    schema_extra: Optional[dict] = None,
) -> str:
    """Gera tudo que vai no <head> de uma vez: meta tags + schema."""
    parts = [
        build_meta_tags(title, description, url, image_url, site_name, keywords, author),
    ]
    if canonical_url:
        parts.append(f'<link rel="canonical" href="{_escape_html(canonical_url)}" />')

    schema = build_schema_article(title, description, url, site_name, author, keywords=keywords)
    if schema_extra:
        schema.update(schema_extra)
    parts.append(generate_schema_html(schema))

    return "\n".join(parts)


def extract_keywords_from_html(html: str, max_keywords: int = 10) -> list:
    """Extrai palavras-chave relevantes do conteúdo HTML."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'[^\w\s]', ' ', text.lower())

    stopwords = {
        "a", "an", "the", "e", "em", "um", "uma", "de", "da", "do", "das",
        "dos", "para", "com", "por", "que", "é", "não", "se", "mais", "os",
        "as", "ao", "aos", "na", "no", "nas", "nos", "como", "mas", "ou",
        "isso", "este", "esta", "isto", "esse", "essa", "você", "ele", "ela",
        "eles", "elas", "meu", "seu", "sua", "nosso", "nossa",
    }

    words = text.split()
    word_freq = {}
    for w in words:
        if w not in stopwords and len(w) > 3:
            word_freq[w] = word_freq.get(w, 0) + 1

    sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:max_keywords]]


def compute_seo_score(article: dict) -> dict:
    """Calcula score SEO (0-100) e retorna gaps."""
    score = 50
    gaps = []

    title = article.get("title", "")
    content = article.get("content_html", "") or article.get("content", "")
    excerpt = article.get("excerpt", "")
    keywords = article.get("keywords", "")

    # Título
    if len(title) < 30:
        gaps.append("Título muito curto (<30 chars)")
    elif len(title) > 60:
        gaps.append("Título muito longo (>60 chars)")
    else:
        score += 10

    # Meta description
    if not excerpt:
        gaps.append("Meta description ausente")
    elif len(excerpt) < 50:
        gaps.append("Meta description muito curta (<50 chars)")
    elif len(excerpt) > 160:
        gaps.append("Meta description muito longa (>160 chars)")
    else:
        score += 10

    # Conteúdo
    word_count = len(content.split()) if content else 0
    if word_count < 300:
        gaps.append("Conteúdo muito curto (<300 palavras)")
        score -= 5
    elif word_count > 500:
        score += 5

    # Headings
    h2_count = len(re.findall(r'<h2[^>]*>', content, re.IGNORECASE))
    h3_count = len(re.findall(r'<h3[^>]*>', content, re.IGNORECASE))
    if h2_count == 0:
        gaps.append("Sem headings H2 (SEO prejudicado)")
    else:
        score += min(h2_count * 3, 10)
    if h3_count == 0:
        gaps.append("Sem headings H3 (baixa profundidade)")
    else:
        score += min(h3_count * 2, 5)

    # Keywords
    if keywords:
        kw_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        content_lower = content.lower()
        matched = sum(1 for kw in kw_list if kw in content_lower)
        if matched < len(kw_list):
            gaps.append(f"Keywords não aparecem no conteúdo ({matched}/{len(kw_list)})")
        else:
            score += 10

    # Imagens
    img_count = len(re.findall(r'<img[^>]+>', content, re.IGNORECASE))
    if img_count == 0:
        gaps.append("Sem imagens no conteúdo")
    else:
        score += min(img_count * 3, 5)

    # Links
    internal_links = len(re.findall(r'<a[^>]+href=["\']/', content, re.IGNORECASE))
    external_links = len(re.findall(r'<a[^>]+href=["\']https?://', content, re.IGNORECASE))
    total_links = internal_links + external_links
    if total_links == 0:
        gaps.append("Sem links internos ou externos")

    score = max(0, min(100, score))

    return {
        "score": score,
        "word_count": word_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "img_count": img_count,
        "total_links": total_links,
        "gaps": gaps,
        "grade": "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D",
    }


def optimize_html(
    html: str,
    title: str,
    description: str,
    url: str = "",
    site_name: str = "Dezafira Blog",
    image_url: str = "",
    keywords: str = "",
) -> str:
    """Adiciona meta tags + schema + canonical a um HTML completo."""
    head_extra = build_head_html(title, description, url, image_url, site_name, keywords)

    if "<head>" in html:
        html = html.replace("<head>", f"<head>\n{head_extra}\n", 1)
    else:
        html = f"<!DOCTYPE html>\n<html>\n<head>\n{head_extra}\n</head>\n<body>\n{html}\n</body>\n</html>"

    return html


def _escape_html(text: str) -> str:
    return (text
        .replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))


def generate_internal_links(current_title: str, all_posts: list, max_links: int = 3) -> list:
    """Sugere links internos baseado em similaridade de título."""
    current_words = set(current_title.lower().split())
    scored = []
    for post in all_posts:
        if post.get("title") == current_title:
            continue
        post_words = set(post.get("title", "").lower().split())
        overlap = len(current_words & post_words)
        if overlap > 0:
            scored.append((overlap, post))
    scored.sort(key=lambda x: -x[0])
    return scored[:max_links]