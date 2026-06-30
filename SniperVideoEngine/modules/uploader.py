import os
import time
from playwright.sync_api import sync_playwright

class YouTubeUploader:
    def __init__(self, user_data_dir=None, channel_id="default"):
        """
        user_data_dir: Diretório que armazena os dados do seu navegador (cookies, logins, etc).
        Se você já fez login no YouTube uma vez nesse diretório, não precisará fazer de novo (evita a verificação em duas etapas).
        """
        self.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Salva o perfil do Chrome com subpastas por canal para isolar cookies e logins
        self.user_data_dir = user_data_dir or os.path.join(self.project_dir, "temp", f"session_{channel_id}")
        os.makedirs(self.user_data_dir, exist_ok=True)

    def upload_video(self, video_path, title, description, is_short=True, cookies_json=None):
        """
        Faz upload automático do vídeo para o YouTube Studio utilizando Playwright.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Vídeo não encontrado no caminho: {video_path}")

        print(f"[Uploader] Iniciando processo de upload para: {video_path}")
        
        import json
        with sync_playwright() as p:
            if cookies_json:
                print("[Uploader] Injetando cookies de sessão salvos no banco de dados...")
                browser = p.chromium.launch(
                    headless=True,  # Na nuvem roda 100% invisível!
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox"
                    ]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                context.add_cookies(json.loads(cookies_json))
                page = context.new_page()
            else:
                # Lança o navegador Chromium persistindo o perfil de usuário (cookies, histórico)
                # headless=False permite ver o navegador agindo na tela se desejar (ou debugar)
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=False,  # Em ambiente de teste é melhor ver o fluxo
                    args=[
                        "--disable-blink-features=AutomationControlled", # Dificulta a detecção como bot
                        "--start-maximized"
                    ],
                    no_viewport=True
                )
                page = browser.pages[0] if browser.pages else browser.new_page()
            
            # Vai para o YouTube Studio
            print("[Uploader] Acessando YouTube Studio...")
            page.goto("https://studio.youtube.com")
            
            # Espera carregar a página principal do painel do YouTube Studio
            time.sleep(5)
            
            # Verifica se o usuário está logado
            if "login" in page.url or "signin" in page.url:
                print("[Uploader] ⚠️ ATENÇÃO: Você não está logado no YouTube Studio.")
                print("[Uploader] Realize o login manualmente no navegador que acabou de abrir.")
                print("[Uploader] O robô aguardará até 3 minutos para que você faça o login...")
                try:
                    # Aguarda até que o painel de controle carregue
                    page.wait_for_selector("a#logo", timeout=180000) 
                    print("[Uploader] Login detectado com sucesso!")
                except Exception:
                    print("[Uploader] ❌ Limite de tempo de login excedido. Abortando upload.")
                    browser.close()
                    return False

            print("[Uploader] Acessando painel. Clicando no botão de Upload...")
            # Clica no botão "Criar" ou "Enviar Vídeos"
            try:
                page.click("a#logo", timeout=5000) # Só para garantir foco
            except Exception:
                pass
                
            # Clica no botão de Upload ("Criar" -> "Enviar vídeo")
            page.wait_for_selector("#create-icon", timeout=15000)
            page.click("#create-icon")
            
            page.wait_for_selector("#text-item-0", timeout=10000) # Enviar vídeo
            page.click("#text-item-0")
            
            print("[Uploader] Modal de upload aberto. Carregando arquivo do vídeo...")
            # Espera o seletor de arquivos do modal de upload
            page.wait_for_selector("input[type='file']")
            
            # Envia o arquivo do vídeo
            file_input = page.locator("input[type='file']")
            file_input.set_input_files(video_path)
            
            print("[Uploader] Vídeo carregado! Preenchendo metadados...")
            time.sleep(5) # Aguarda inicializar os campos de texto
            
            # 1. Título
            title_input = page.locator("div#title-textarea div#textbox")
            title_input.wait_for(timeout=20000)
            title_input.clear()
            title_input.fill(title)
            print(f"[Uploader] Título definido: {title}")
            
            # 2. Descrição
            desc_input = page.locator("div#description-textarea div#textbox")
            desc_input.wait_for(timeout=10000)
            desc_input.clear()
            desc_input.fill(description)
            print("[Uploader] Descrição definida.")
            
            # 3. Audiência (Definir como "Não é conteúdo para crianças" - obrigatório do YT)
            # Procura o botão de rádio correspondente
            not_kids_radio = page.locator("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MADE_FOR_KIDS']")
            not_kids_radio.wait_for(timeout=10000)
            not_kids_radio.click()
            
            # Clica em "Próximo" 3 vezes até a tela de Visibilidade
            for step in range(3):
                print(f"[Uploader] Avançando etapa {step+1}/3...")
                next_button = page.locator("ytcp-button#next-button")
                next_button.wait_for(timeout=10000)
                next_button.click()
                time.sleep(3)
            
            # 4. Visibilidade (Público ou Rascunho/Privado para aprovação)
            print("[Uploader] Definindo visibilidade para Público...")
            # Clica na opção "Público"
            public_radio = page.locator("tp-yt-paper-radio-button[name='PUBLIC']")
            if not public_radio.is_visible():
                # Tenta alternativa se o ID mudar
                public_radio = page.locator("tp-yt-paper-radio-button:has-text('Público')")
            
            public_radio.wait_for(timeout=10000)
            public_radio.click()
            
            # Aguarda upload terminar (se for curto, processa rápido)
            print("[Uploader] Aguardando o processamento do vídeo no YouTube...")
            time.sleep(10)
            
            # Clica em "Salvar" / "Publicar"
            print("[Uploader] Clicando no botão Publicar!")
            done_button = page.locator("ytcp-button#done-button")
            done_button.wait_for(timeout=10000)
            done_button.click()
            
            time.sleep(5)
            print("[Uploader] 🎉 Upload concluído com sucesso!")
            browser.close()
            return True

if __name__ == "__main__":
    # Teste rápido
    uploader = YouTubeUploader()
    # Para testar, precisaremos de um vídeo de verdade gerado
    video_teste = "../outputs/resultado_final.mp4"
    if os.path.exists(video_teste):
        print("Vídeo encontrado. Iniciando teste de upload automático...")
        uploader.upload_video(video_teste, "Vídeo Teste Automação", "Vídeo gerado de forma 100% automatizada pelo SniperVideoEngine!")
    else:
        print("Aviso: Gere o vídeo de teste primeiro para rodar o upload.")
