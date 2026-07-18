"""
Setup OAuth 2.0 — Gera refresh token para Google Indexing API.

Uso: python modules/google_oauth_setup.py

Fluxo:
  1. Lê o client_id/client_secret do arquivo credentials/oauth_client.json
  2. Abre o navegador para autorização
  3. Você faz login na sua conta Google
  4. Salva o refresh_token no .env como GOOGLE_OAUTH_REFRESH_TOKEN
"""
import json
import os
import sys

# Caminhos
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(PROJECT_DIR, "credentials", "oauth_client.json")
ENV_FILE = os.path.join(PROJECT_DIR, "..", ".env")
DOTENV_FILE = os.path.join(PROJECT_DIR, "..", ".env")

SCOPES = ["https://www.googleapis.com/auth/indexing"]


def main():
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"Arquivo não encontrado: {CREDENTIALS_FILE}")
        print("Crie o arquivo com o JSON do OAuth Client ID.")
        sys.exit(1)

    with open(CREDENTIALS_FILE) as f:
        client_config = json.load(f)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Instalando google-auth-oauthlib...")
        os.system(f"{sys.executable} -m pip install google-auth-oauthlib google-auth-httplib2")
        from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    if not creds.refresh_token:
        print("Nenhum refresh_token retornado. Pode ser conta já autorizada antes.")
        print("Tente revogar o acesso em: https://myaccount.google.com/permissions")
        sys.exit(1)

    # Salvar no .env
    env_path = _find_env_file()
    _set_env_var(env_path, "GOOGLE_OAUTH_REFRESH_TOKEN", creds.refresh_token)
    _set_env_var(env_path, "GOOGLE_OAUTH_CLIENT_ID", client_config["installed"]["client_id"])
    _set_env_var(env_path, "GOOGLE_OAUTH_CLIENT_SECRET", client_config["installed"]["client_secret"])

    print()
    print("=" * 60)
    print("✅ OAuth configurado com sucesso!")
    print(f"   Refresh token salvo em: {env_path}")
    print(f"   Cliente ID: {client_config['installed']['client_id']}")
    print()
    print("Agora é só usar o Google Indexing API normalmente.")
    print("=" * 60)


def _find_env_file():
    candidates = [
        os.path.join(PROJECT_DIR, "..", ".env"),
        os.path.join(PROJECT_DIR, ".env"),
        os.path.join(os.path.dirname(PROJECT_DIR), ".env"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return os.path.abspath(path)
    # Fallback: criar no diretório do projeto
    fallback = os.path.join(PROJECT_DIR, ".env")
    print(f"[Aviso] .env não encontrado. Criando em: {fallback}")
    open(fallback, "a").close()
    return fallback


def _set_env_var(env_path, key, value):
    with open(env_path, "r") as f:
        lines = f.readlines()

    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\n# Google OAuth 2.0 (Indexing API)\n")
        new_lines.append(f"{key}={value}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    print(f"  {key} = {'...' + value[-8:] if len(value) > 8 else value}")


if __name__ == "__main__":
    main()
