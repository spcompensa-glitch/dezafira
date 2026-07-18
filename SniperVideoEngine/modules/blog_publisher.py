"""
BlogPublisher — Publicação automática de artigos em plataformas de blog.

Plataformas suportadas:
  - WordPress (XML-RPC ou REST API)
  - Blogger (Google API)
"""
import asyncio
import base64
import os
from typing import Optional


async def publish_wordpress_xmlrpc(
    api_endpoint: str,
    username: str,
    password: str,
    title: str,
    content_html: str,
    excerpt: str = "",
    slug: str = "",
    keywords: str = "",
    status: str = "publish",
) -> dict:
    """Publica no WordPress via XML-RPC."""
    import httpx

    xml = f"""<?xml version="1.0"?>
<methodCall>
  <methodName>wp.newPost</methodName>
  <params>
    <param><value><int>1</int></value></param>
    <param><value><string>{username}</string></value></param>
    <param><value><string>{password}</string></value></param>
    <param><value><struct>
      <member>
        <name>post_title</name>
        <value><string>{_escape_xml(title)}</string></value>
      </member>
      <member>
        <name>post_content</name>
        <value><string>{_escape_xml(content_html)}</string></value>
      </member>
      <member>
        <name>post_excerpt</name>
        <value><string>{_escape_xml(excerpt)}</string></value>
      </member>
      <member>
        <name>post_status</name>
        <value><string>{status}</string></value>
      </member>
      <member>
        <name>post_name</name>
        <value><string>{slug}</string></value>
      </member>
      <member>
        <name>mt_keywords</name>
        <value><string>{keywords}</string></value>
      </member>
    </struct></value></param>
  </params>
</methodCall>"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(api_endpoint, content=xml, headers={"Content-Type": "text/xml"})
            r.raise_for_status()
            text = r.text

            import re
            m = re.search(r'<int>(\d+)</int>', text)
            if m:
                post_id = m.group(1)
                url = f"{api_endpoint.replace('/xmlrpc.php', '')}/?p={post_id}"
                return {"ok": True, "platform_post_id": post_id, "platform_url": url}
            return {"ok": False, "error": f"Resposta inesperada: {text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def publish_wordpress_rest(
    api_endpoint: str,
    username: str,
    app_password: str,
    title: str,
    content_html: str,
    excerpt: str = "",
    slug: str = "",
    keywords: str = "",
    status: str = "publish",
) -> dict:
    """Publica no WordPress via REST API (Application Password)."""
    import httpx

    auth = base64.b64encode(f"{username}:{app_password}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }
    payload = {
        "title": title,
        "content": content_html,
        "excerpt": excerpt,
        "slug": slug,
        "status": status,
        "meta": {},
    }
    if keywords:
        payload["meta"]["rank_math_keywords"] = keywords

    posts_url = api_endpoint.rstrip("/") + "/wp/v2/posts"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(posts_url, json=payload, headers=headers)
            if r.status_code in (200, 201):
                data = r.json()
                return {
                    "ok": True,
                    "platform_post_id": str(data.get("id", "")),
                    "platform_url": data.get("link", ""),
                }
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def publish_blogger(
    api_key: str,
    blog_id: str,
    title: str,
    content_html: str,
    labels: str = "",
    status: str = "LIVE",
) -> dict:
    """Publica no Blogger via Google API."""
    import httpx

    url = f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/"
    if api_key:
        url += f"?key={api_key}"

    payload = {
        "kind": "blogger#post",
        "title": title,
        "content": content_html,
        "labels": [l.strip() for l in labels.split(",") if l.strip()] if labels else [],
        "status": status,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
            if r.status_code in (200, 201):
                data = r.json()
                return {
                    "ok": True,
                    "platform_post_id": data.get("id", ""),
                    "platform_url": data.get("url", ""),
                }
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def publish_medium(
    api_token: str,
    publication_id: str,
    title: str,
    content_html: str,
    tags: str = "",
    canonical_url: str = "",
    publish_status: str = "public",
) -> dict:
    """Publica no Medium via API."""
    import httpx

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    # Primeiro: pegar info do usuário
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get("https://api.medium.com/v1/me", headers=headers)
            r.raise_for_status()
            user_id = r.json()["data"]["id"]
    except Exception as e:
        return {"ok": False, "error": f"Falha ao autenticar no Medium: {e}"}

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    payload = {
        "title": title,
        "contentFormat": "html",
        "content": content_html,
        "tags": tag_list[:5],
        "publishStatus": publish_status,
    }
    if canonical_url:
        payload["canonicalUrl"] = canonical_url

    post_url = f"https://api.medium.com/v1/users/{user_id}/posts"
    if publication_id:
        post_url = f"https://api.medium.com/v1/publications/{publication_id}/posts"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(post_url, json=payload, headers=headers)
            if r.status_code in (200, 201):
                data = r.json()["data"]
                return {
                    "ok": True,
                    "platform_post_id": data.get("id", ""),
                    "platform_url": data.get("url", ""),
                }
            return {"ok": False, "error": f"Medium HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def publish_devto(
    api_key: str,
    title: str,
    content_markdown: str,
    tags: str = "",
    description: str = "",
    canonical_url: str = "",
    published: bool = True,
    series: str = "",
) -> dict:
    """Publica no Dev.to (forem) via API."""
    import httpx

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
    # Dev.to permite no máximo 4 tags
    tag_list = tag_list[:4]

    payload = {
        "article": {
            "title": title,
            "body_markdown": content_markdown,
            "published": published,
            "tags": tag_list,
        }
    }
    if description:
        payload["article"]["description"] = description
    if canonical_url:
        payload["article"]["canonical_url"] = canonical_url
    if series:
        payload["article"]["series"] = series

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("https://dev.to/api/articles", json=payload, headers=headers)
            if r.status_code in (200, 201):
                data = r.json()
                return {
                    "ok": True,
                    "platform_post_id": str(data.get("id", "")),
                    "platform_url": data.get("url", ""),
                }
            return {"ok": False, "error": f"Dev.to HTTP {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def publish(
    platform: str,
    title: str,
    content_html: str,
    excerpt: str = "",
    slug: str = "",
    keywords: str = "",
    api_endpoint: str = "",
    username: str = "",
    password: str = "",
    app_password: str = "",
    api_token: str = "",
    blog_id: str = "",
    status: str = "publish",
    content_markdown: str = "",
    canonical_url: str = "",
    publication_id: str = "",
    series: str = "",
) -> dict:
    """Publica na plataforma correta baseado no tipo."""
    if platform == "wordpress":
        if app_password:
            return await publish_wordpress_rest(
                api_endpoint, username, app_password,
                title, content_html, excerpt, slug, keywords, status,
            )
        return await publish_wordpress_xmlrpc(
            api_endpoint, username, password,
            title, content_html, excerpt, slug, keywords, status,
        )
    elif platform == "blogger":
        return await publish_blogger(
            api_token, blog_id, title, content_html, keywords, status.upper(),
        )
    elif platform == "medium":
        return await publish_medium(
            api_token, publication_id, title, content_html,
            keywords, canonical_url, status,
        )
    elif platform == "devto":
        return await publish_devto(
            api_token, title, content_markdown,
            keywords, excerpt, canonical_url,
            published=(status == "publish"),
            series=series,
        )
    return {"ok": False, "error": f"Plataforma não suportada: {platform}"}


def _escape_xml(text: str) -> str:
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;"))