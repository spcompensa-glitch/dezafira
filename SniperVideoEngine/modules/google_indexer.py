"""
Google Indexing API — Submete URLs ao Google para indexação instantânea.

Suporta dois métodos de autenticação:
  1. Service Account (chave JSON) — GOOGLE_INDEXING_KEY_PATH ou GOOGLE_INDEXING_KEY_JSON
  2. OAuth 2.0 (Desktop App) — GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET + GOOGLE_OAUTH_REFRESH_TOKEN

Use `python modules/google_oauth_setup.py` para configurar o OAuth 2.0.
"""
import json
import os
import time
from typing import Optional

SCOPES = ["https://www.googleapis.com/auth/indexing"]


def _get_credentials():
    """Tenta Service Account primeiro, depois OAuth 2.0."""
    creds = _get_service_account_credentials()
    if creds:
        return creds
    creds = _get_oauth_credentials()
    if creds:
        return creds
    return None


def _get_service_account_credentials():
    """Carrega credentials de Service Account do .env ou arquivo JSON."""
    key_path = os.getenv("GOOGLE_INDEXING_KEY_PATH", "")
    key_json = os.getenv("GOOGLE_INDEXING_KEY_JSON", "")

    if key_json:
        from google.oauth2.service_account import Credentials
        creds_info = json.loads(key_json)
        creds = Credentials.from_service_account_info(creds_info)
        return creds.with_scopes(SCOPES)

    if key_path and os.path.exists(key_path):
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(key_path)
        return creds.with_scopes(SCOPES)

    return None


def _get_oauth_credentials():
    """Carrega credentials via OAuth 2.0 (refresh token)."""
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    refresh_token = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", "")

    if not (client_id and client_secret and refresh_token):
        return None

    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        # Força refresh do access token
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        return creds
    except Exception:
        return None


async def notify_url_update(url: str) -> dict:
    return await _indexing_request(url, "URL_UPDATED")


async def notify_url_delete(url: str) -> dict:
    return await _indexing_request(url, "URL_DELETED")


async def notify_batch(urls: list, action: str = "URL_UPDATED") -> list:
    import asyncio
    tasks = [notify_url_update(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        {"url": url, "status": "ok" if isinstance(r, dict) and r.get("ok") else "error", "detail": str(r)}
        for url, r in zip(urls, results)
    ]


async def _indexing_request(url: str, action_type: str) -> dict:
    creds = _get_credentials()
    if not creds:
        return {"ok": False, "error": "Nenhuma credencial configurada. Configure Service Account ou OAuth 2.0."}

    try:
        from google.auth.transport.requests import AuthorizedSession

        session = AuthorizedSession(creds)
        payload = {"url": url, "type": action_type}

        response = session.post(
            "https://indexing.googleapis.com/v3/urlNotifications:publish",
            json=payload,
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "ok": True,
                "url": url,
                "action": action_type,
                "notification_type": result.get("urlNotificationMetadata", {}).get("latestUpdate", {}).get("type", ""),
            }
        elif response.status_code == 429:
            time.sleep(2)
            return {"ok": False, "error": "Rate limit (429). Re-tente em alguns segundos."}
        else:
            return {"ok": False, "error": f"HTTP {response.status_code}: {response.text[:500]}"}

    except ImportError:
        return {"ok": False, "error": "google-auth não instalado. pip install google-auth google-auth-httplib2"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_ownership(site_url: str) -> dict:
    creds = _get_credentials()
    if not creds:
        return {"ok": False, "error": "Credentials não configuradas"}

    try:
        from google.auth.transport.requests import AuthorizedSession

        session = AuthorizedSession(creds)
        response = session.get(
            f"https://searchconsole.googleapis.com/v1/sites/{site_url}",
        )
        if response.status_code == 200:
            return {"ok": True, "site": site_url, "verified": True}
        return {"ok": False, "error": f"Site não verificado: HTTP {response.status_code}", "site": site_url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def get_quota() -> dict:
    creds = _get_credentials()
    if not creds:
        return {"ok": False, "error": "Credentials não configuradas"}

    try:
        from google.auth.transport.requests import AuthorizedSession

        session = AuthorizedSession(creds)
        response = session.get("https://indexing.googleapis.com/v3/urlNotifications/metadata")
        if response.status_code == 200:
            data = response.json()
            return {"ok": True, "quota": data}
        return {"ok": False, "error": f"HTTP {response.status_code}: {response.text[:300]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
