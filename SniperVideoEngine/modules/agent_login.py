import time
import json
from playwright.sync_api import sync_playwright
from modules.database import SessionLocal, Channel, save_db_channel_cookies

def run_agent_login_stealth(channel_id: str, email: str, password: str):
    """
    Executa o login simulado com Playwright de forma silenciosa e assistida por banco
    para contornar a Verificação de Duas Etapas (2FA) do Google.
    """
    print(f"[Agent-Login] 🤖 Iniciando agente de login simulado para o canal: {channel_id}")
    
    # Helper para atualizar o status do login no banco
    def update_status(status: str, error_msg: str = None, clear_code: bool = False):
        db = SessionLocal()
        try:
            chan = db.query(Channel).filter(Channel.id == channel_id).first()
            if chan:
                chan.connection_status = status
                if error_msg:
                    chan.connection_error = error_msg
                if clear_code:
                    chan.verification_code = None
                db.commit()
        finally:
            db.close()

    # Helper para buscar o código 2FA digitado pelo usuário na UI
    def get_verification_code() -> str:
        db = SessionLocal()
        try:
            chan = db.query(Channel).filter(Channel.id == channel_id).first()
            return chan.verification_code if chan else None
        finally:
            db.close()

    update_status("typing_email")
    
    with sync_playwright() as p:
        try:
            # Lançamos o Chromium com argumentos stealth avançados para evitar detecção de robô
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
            page = context.new_page()
            
            print("[Agent-Login] Acessando página de login do Google...")
            page.goto("https://accounts.google.com/signin/v2/identifier?service=youtube")
            
            # 1. Preencher E-mail
            print(f"[Agent-Login] Digitando e-mail: {email}")
            page.locator("input[type='email']").fill(email)
            page.locator("input[type='email']").press("Enter")
            
            # Aguarda a tela de senha carregar ou ver se deu erro
            page.wait_for_timeout(3000)
            
            if page.locator("input[type='password']").is_visible() == False:
                # Caso o e-mail não tenha sido reconhecido
                update_status("failed", "E-mail não reconhecido pelo Google.")
                browser.close()
                return

            # 2. Preencher Senha
            update_status("typing_password")
            print("[Agent-Login] Digitando senha...")
            page.locator("input[type='password']").fill(password)
            page.locator("input[type='password']").press("Enter")
            
            page.wait_for_timeout(5000) # Tempo para processar o login ou pedir 2FA
            
            # 3. Detectar se o Google exige Verificação em Duas Etapas (2FA)
            # Geralmente o Google exibe telas com ID de verificação ou campos de SMS
            is_2fa = False
            for selector in ["#idvPreregisteredPhoneNext", "input[type='tel']", "div[data-send-method]", "div#authZenNext", "div#challenge"]:
                try:
                    if page.locator(selector).is_visible():
                        is_2fa = True
                        break
                except:
                    pass
            
            if is_2fa:
                print("[Agent-Login] ⚠️ Verificação em Duas Etapas (2FA) detectada!")
                update_status("awaiting_2fa", clear_code=True)
                
                # Fica num loop aguardando o Jonatas digitar o código no frontend por até 2 minutos (120 segundos)
                code_found = None
                for _ in range(120):
                    time.sleep(1)
                    code = get_verification_code()
                    if code and len(code.strip()) >= 4:
                        code_found = code.strip()
                        print(f"[Agent-Login] Código 2FA recebido da UI: {code_found}")
                        break
                
                if not code_found:
                    update_status("failed", "Tempo limite de 2FA expirado. Tente novamente.")
                    browser.close()
                    return
                
                # Preencher o código de verificação recebido da UI
                # Tenta localizar o campo de input de telefone/SMS
                input_field = page.locator("input[type='tel']")
                if input_field.is_visible():
                    input_field.fill(code_found)
                    input_field.press("Enter")
                else:
                    # Se for outro tipo de campo de desafio de texto
                    text_input = page.locator("input[type='text']")
                    if text_input.is_visible():
                        text_input.fill(code_found)
                        text_input.press("Enter")
                    else:
                        update_status("failed", "Não foi possível localizar o campo para preencher o código 2FA.")
                        browser.close()
                        return
                
                page.wait_for_timeout(5000)

            # 4. Verificar se o login foi concluído com sucesso
            # Se logou com sucesso, a URL deve redirecionar para youtube ou conter cookies ativos
            cookies_list = context.cookies()
            has_sid = any(c['name'] == 'SID' for c in cookies_list)
            
            if has_sid:
                print("[Agent-Login] 🟢 Login concluído com absoluto sucesso!")
                # Exportar os cookies como string JSON
                cookies_json = json.dumps(cookies_list)
                save_db_channel_cookies(channel_id, cookies_json)
            else:
                # Ver se o Google exibiu alguma mensagem de erro na tela
                error_elem = page.locator("div[jsname='B34EJ']")
                error_text = error_elem.text_content() if error_elem.is_visible() else "Senha ou código 2FA incorretos."
                print(f"[Agent-Login] ❌ Login falhou: {error_text}")
                update_status("failed", error_text)
                
            browser.close()
            
        except Exception as e:
            print(f"[Agent-Login] ❌ Exceção no login do agente: {str(e)}")
            update_status("failed", f"Erro interno do agente: {str(e)}")
            try:
                browser.close()
            except:
                pass
