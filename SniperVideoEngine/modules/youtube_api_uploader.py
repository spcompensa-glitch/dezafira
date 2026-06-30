import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configurações do App OAuth do Google (cadastrados no Console de Desenvolvedores do Google Cloud)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

class YouTubeApiUploader:
    def __init__(self, refresh_token: str):
        self.refresh_token = refresh_token

    def upload_video(self, video_path: str, title: str, description: str) -> bool:
        """
        Realiza o upload do vídeo vertical de forma 100% oficial e silenciosa na nuvem
        utilizando o token OAuth autenticado pelo usuário final.
        """
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            print("[YouTube-API] ⚠️ GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET não configurados no servidor. Upload cancelado.")
            return False

        if not self.refresh_token:
            print("[YouTube-API] ⚠️ Canal não possui token de autorização. Upload cancelado.")
            return False

        try:
            print(f"[YouTube-API] Renovando token de acesso para o upload de: {title}")
            
            # 1. Instanciar credenciais usando o Refresh Token
            credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/youtube.upload"]
            )

            # 2. Construir o cliente da API do YouTube
            youtube = build("youtube", "v3", credentials=credentials)

            # 3. Preparar metadados do vídeo
            body = {
                "snippet": {
                    "title": title[:95],
                    "description": description,
                    "tags": ["shorts", "dezafira", "viral"],
                    "categoryId": "22"  # Pessoas e Blogs
                },
                "status": {
                    "privacyStatus": "public",  # Publicação direta como público
                    "selfDeclaredMadeForKids": False
                }
            }

            # 4. Upload Multipart do Arquivo MP4
            media = MediaFileUpload(
                video_path,
                mimetype="video/mp4",
                chunksize=1024 * 1024,
                resumable=True
            )

            print(f"[YouTube-API] Enviando arquivo {video_path} para o YouTube...")
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"[YouTube-API] Progresso do upload: {int(status.progress() * 100)}%")

            print(f"[YouTube-API] ✅ Upload concluído com sucesso! Video ID: {response.get('id')}")
            return True

        except Exception as e:
            print(f"[YouTube-API] ❌ Erro durante o upload oficial: {str(e)}")
            return False
