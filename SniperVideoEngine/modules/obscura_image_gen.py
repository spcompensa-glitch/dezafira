"""
Dezafira Obscura Image Generator v3 — Automação ROBUSTA do Google Flow (GRÁTIS).

Porta as técnicas do ELTON FLOW (extensão Chrome) para o Playwright, que roda
código no MAIN world da página (mesmo contexto do React/Slate), permitindo:

  • Anti-pause shim  — Flow não pausa geração ao minimizar/trocar de aba
  • Keep-alive        — oscilador sub-grave inaudível (30Hz) evita freeze de timers
  • React fiber click — chama onSubmit(true) direto na árvore React (bypass isTrusted)
  • API media fetch   — flow.projectInitialData + getMediaUrlRedirect?name= (funciona
                        minimizado / aba oculta / virtualização do DOM)
  • Fallback DOM      — detecção de <img> labs.google + settle/dedup por name
  • Nome [MM-SS]      — timestamp sincronizável com o áudio (igual ao ELTON FLOW)
  • Retries CDN       — getMediaUrlRedirect pode responder 500 até o CDN servir

Interface mantida (generate_scene_images) para o server.py consumir sem mudanças.
"""
import asyncio
import base64
import hashlib
import json
import os
import time
from pathlib import Path

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "ai_images")
SESSION_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "browser_session")
CHROME_USER_DATA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")

GOOGLE_FLOW_URL = "https://labs.google/fx/tools/flow?from=imagefx"

# ── JS injetado no MAIN world da página (Playwright roda em main world) ──

AWAKE_SHIM_JS = r"""
() => {
  if (window.__dezafiraAwake) return {ok:true, already:true};
  window.__dezafiraAwake = true;
  try {
    Object.defineProperty(document, "hidden", {configurable:true, get:()=>false});
    Object.defineProperty(document, "visibilityState", {configurable:true, get:()=>"visible"});
    Object.defineProperty(document, "webkitHidden", {configurable:true, get:()=>false});
    Object.defineProperty(document, "webkitVisibilityState", {configurable:true, get:()=>"visible"});
  } catch(e) {}
  const swallow = (e)=>e.stopImmediatePropagation();
  ["visibilitychange","webkitvisibilitychange","blur","pagehide","freeze"].forEach(t=>{
    window.addEventListener(t, swallow, true);
    document.addEventListener(t, swallow, true);
  });
  // Keep-alive: oscilador sub-grave inaudível (Flow não congela timers da aba)
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (Ctx) {
      const ctx = new Ctx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      gain.gain.value = 0.0001;
      osc.frequency.value = 30;
      osc.connect(gain); gain.connect(ctx.destination); osc.start();
      if (ctx.state === "suspended") ctx.resume().catch(()=>{});
    }
  } catch(e) {}
  return {ok:true};
}
"""

# Encontra o editor Slate do Flow e injeta o texto (multi-estratégia, igual ELTON)
INJECT_JS = r"""
async (text) => {
  const sleep = (ms)=>new Promise(r=>setTimeout(r,ms));
  const isVisible = (el)=>{ if(!el) return false; const r=el.getBoundingClientRect();
    const s=window.getComputedStyle(el); return r.width>0&&r.height>0&&
    s.visibility!=="hidden"&&s.display!=="none"; };
  function findFlowPromptEditor(){
    const c=[];
    for (const el of document.querySelectorAll('[data-slate-editor="true"][contenteditable="true"]')){
      if(!isVisible(el)) continue; c.push(el);
    }
    if(!c.length) return null;
    const ph=c.filter(el=>{const p=el.querySelector("[data-slate-placeholder]");
      if(!p) return false; const l=(p.textContent||"").toLowerCase();
      return l.includes("what do you want")||l.includes("create")||l.includes("generate");});
    const pool=ph.length?ph:c;
    return pool.sort((a,b)=>b.getBoundingClientRect().bottom-a.getBoundingClientRect().bottom)[0];
  }
  function editorPlainText(el){return (el.innerText||"").replace(/[​﻿]/g,"").replace(/\n+/g," ").trim();}
  function editorSeemsToContain(el,t){const h=t.trim();if(!h)return false;
    const raw=editorPlainText(el); return raw.includes(h)||raw.includes(h.slice(0,48));}
  async function focusLikeUser(el){el.scrollIntoView({block:"center"});await sleep(40);
    el.focus();const r=el.getBoundingClientRect();
    const cx=Math.min(Math.max(r.left+r.width/2,r.left+8),r.right-8);
    const cy=Math.min(Math.max(r.top+r.height/2,r.top+8),r.bottom-8);
    const c={bubbles:true,cancelable:true,view:window,clientX:cx,clientY:cy,button:0,buttons:1};
    el.dispatchEvent(new PointerEvent("pointerdown",{...c,pointerId:1,pointerType:"mouse"}));
    el.dispatchEvent(new MouseEvent("mousedown",c));
    el.dispatchEvent(new PointerEvent("pointerup",{...c,pointerId:1,pointerType:"mouse"}));
    el.dispatchEvent(new MouseEvent("mouseup",c));
    el.dispatchEvent(new MouseEvent("click",c)); await sleep(50);}
  async function selectAll(el){const sel=window.getSelection();const rg=document.createRange();
    rg.selectNodeContents(el);sel.removeAllRanges();sel.addRange(rg);await sleep(30);}
  async function clear(el){await selectAll(el);try{document.execCommand("delete",false,null);}
    catch(e){el.dispatchEvent(new InputEvent("beforeinput",{bubbles:true,cancelable:true,inputType:"deleteContentBackward"}));}await sleep(40);}
  function dispPaste(el,t){const dt=new DataTransfer();dt.setData("text/plain",t);
    const ev=new ClipboardEvent("paste",{bubbles:true,cancelable:true,composed:true});
    try{Object.defineProperty(ev,"clipboardData",{value:dt,enumerable:true,configurable:true});}catch(e){}
    return el.dispatchEvent(ev);}

  const el = findFlowPromptEditor();
  if (!el) return {ok:false, reason:"editor not found"};
  await focusLikeUser(el); await clear(el); await focusLikeUser(el);
  // 1) synthetic paste
  dispPaste(el, text); await sleep(200);
  if (editorSeemsToContain(el, text)) return {ok:true, method:"paste"};
  // 2) beforeinput/input
  el.dispatchEvent(new InputEvent("beforeinput",{bubbles:true,cancelable:true,composed:true,inputType:"insertText",data:text}));
  el.dispatchEvent(new InputEvent("input",{bubbles:true,composed:true,inputType:"insertText",data:text}));
  await sleep(200);
  if (editorSeemsToContain(el, text)) return {ok:true, method:"beforeinput"};
  // 3) execCommand insertText por char
  for (let j=0;j<text.length;j++){try{document.execCommand("insertText",false,text[j]);}catch(e){}}
  await sleep(200);
  if (editorSeemsToContain(el, text)) return {ok:true, method:"execCommand"};
  return {ok:false, reason:"prompt not accepted", current:editorPlainText(el).slice(0,120)};
}
"""

# Submit via React fiber (bypass isTrusted): caminha na árvore e chama onSubmit(true)
REACT_SUBMIT_JS = r"""
async () => {
  function findSubmit(){
    const cands=[];
    for(const b of document.querySelectorAll("button")){
      if(!b.getBoundingClientRect||b.getBoundingClientRect().width===0)continue;
      const s=b.querySelector("i.google-symbols");
      if(s&&s.textContent&&s.textContent.trim()==="arrow_forward") cands.push(b);
    }
    if(cands.length) return cands.sort((a,b)=>b.getBoundingClientRect().bottom-a.getBoundingClientRect().bottom)[0];
    for(const b of document.querySelectorAll("button")){
      const sp=b.querySelectorAll("span");
      for(const s of sp){if(s.textContent&&s.textContent.trim().toLowerCase()==="create")return b;}
    }
    for(const b of document.querySelectorAll("button")){
      if((b.textContent||"").toLowerCase().includes("create")) return b;
    }
    return null;
  }
  const btn=findSubmit();
  if(!btn) return {ok:false, reason:"submit button not found"};
  const key=Object.keys(btn).find(k=>k.startsWith("__reactFiber$")||k.startsWith("__reactInternalInstance$"));
  if(!key) return {ok:false, reason:"no react fiber"};
  let fiber=btn[key], depth=0, onSubmit=null, onClick=null;
  while(fiber&&depth<30){
    const p=fiber.memoizedProps;
    if(p){
      if(!onSubmit&&typeof p.onSubmit==="function") onSubmit=p.onSubmit;
      if(!onClick&&typeof p.onClick==="function") onClick=p.onClick;
    }
    fiber=fiber.return; depth++;
  }
  if(onSubmit){ try{ onSubmit(true); return {ok:true, method:"onSubmit"}; }catch(e){} }
  if(onClick){ try{ onClick({type:"click",target:btn,currentTarget:btn,isTrusted:true,
    preventDefault(){},stopPropagation(){},isPropagationStopped:()=>false,isDefaultPrevented:()=>false,
    nativeEvent:{type:"click",isTrusted:true}}); return {ok:true, method:"onClick"}; }catch(e){
    return {ok:false, reason:"onClick threw: "+e.message}; } }
  return {ok:false, reason:"no handler in fiber"};
}
"""

# Lista de mídias do projeto via API (mesmo-origin, cookie da sessão)
MEDIA_LIST_JS = r"""
async () => {
  const m = location.pathname.match(/\/project\/([0-9a-f-]{36})/i);
  if(!m) return {ok:false, reason:"not a /project/<id> url"};
  const projectId = m[1];
  const input = encodeURIComponent(JSON.stringify({json:{projectId}}));
  const resp = await fetch("/fx/api/trpc/flow.projectInitialData?input="+input,{credentials:"same-origin"});
  if(!resp.ok) return {ok:false, reason:"projectInitialData HTTP "+resp.status};
  const data = await resp.json();
  const pc = data?.result?.data?.json?.projectContents || {};
  const media = Array.isArray(pc.media)?pc.media:[];
  return {ok:true, media: media.map(mm=>{
    const req = mm.mediaMetadata?.requestData||{};
    const isImage = !!mm.image || !!req.imageGenerationRequestData;
    return {name:mm.name, kind:isImage?"image":"video",
      prompt: mm.image?.generatedImage?.prompt||mm.video?.generatedVideo?.prompt||
        (Array.isArray(req.promptInputs)&&req.promptInputs[0]?.textInput)||"",
      url:"https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name="+mm.name};
  })};
}
"""

# Captura as <img> geradas no DOM (fallback quando não há /project/<id>)
GENERATED_IMGS_JS = r"""
() => {
  const BLOCK=/logo|twitter|instagram|avatar|icon|gstatic|flag|badge/i;
  return Array.from(document.querySelectorAll("img")).filter(img=>{
    const alt=(img.getAttribute("alt")||"");
    const src=img.src||"";
    if(!src || BLOCK.test(alt) || BLOCK.test(src)) return false;
    const r=img.getBoundingClientRect();
    return r.width>=120 && r.height>=120;
  }).map(img=>({src:img.src||"", name:(img.src||"").split("name=")[1]||img.src||""}));
}
"""

# Detecta se a conta Google está autenticada NA PRÓPRIA PÁGINA (sem input() no terminal).
# Quando logado, o topo mostra o chip/avatar da Conta do Google; quando deslogado,
# aparece o botão "Fazer login / Sign in".
IS_SIGNED_IN_JS = r"""
() => {
  try {
    // Tela de login tem campo de e-mail/identificador => NÃO está logado
    // (mesmo que apareça o avatar de uma conta "lembrada" na telha de escolha).
    const loginField = document.querySelector(
      'input[type=email], input[name=identifier], input[autocomplete=email]'
    );
    if (loginField) return { signedIn: false, reason: 'login-field' };
    const url = location.href;
    // Após login o Google redireciona para essas páginas => logado com certeza
    if (/myaccount\.google\.com|mail\.google\.com|account\.google\.com\/welcome|accounts\.google\.com\/u\//.test(url))
      return { signedIn: true, viaUrl: true };
    const acct = document.querySelector(
      '[aria-label*="Conta do Google"],[aria-label*="Google Account"],' +
      'img[alt="Conta do Google"],img[alt="Google Account"]'
    );
    const avatar = document.querySelector('img[src*="googleusercontent.com"]');
    return { signedIn: !!(acct || avatar), reason: 'chip' };
  } catch(e) { return { signedIn: false }; }
}
"""

# Baixa mídia no MAIN world (same-origin: cookie+Referer+Sec-Fetch) -> data URL, com retries
FETCH_MEDIA_JS = r"""
async (opts) => {
  const url = opts.url, isVideo = opts.isVideo;
  const tentativas = isVideo?12:5;
  let espera=4000, ultimo="";
  for(let t=1;t<=tentativas;t++){
    try{
      const resp=await fetch(url,{credentials:"same-origin"});
      if(resp.ok){
        const blob=await resp.blob();
        if(/text\/html/i.test(blob.type)){ultimo="Flow retornou HTML";}
        else if(blob.size===0){ultimo="0 bytes";}
        else{
          const dataUrl=await new Promise((res,rej)=>{const fr=new FileReader();
            fr.onload=()=>res(fr.result);fr.onerror=()=>rej(fr.error||new Error("FileReader"));
            fr.readAsDataURL(blob);});
          return {ok:true, dataUrl, sizeKB:Math.round(blob.size/1024), type:blob.type};
        }
      } else { ultimo="HTTP "+resp.status; }
    }catch(e){ultimo=String(e&&e.message||e);}
    if(t<tentativas){ await new Promise(r=>setTimeout(r,espera)); espera=Math.min(espera*1.4,12000); }
  }
  return {ok:false, error:`mídia não servível após ${tentativas} tentativas (${ultimo})`};
}
"""


class ObscuraImageGen:
    """
    Gera imagens gratuitamente automatizando o Google Flow via Playwright,
    usando as técnicas robustas do ELTON FLOW.
    """

    def __init__(self, output_dir=None, project_url=None):
        self.output_dir = output_dir or OUTPUT_DIR
        self.session_dir = SESSION_DIR
        self.project_url = project_url
        self.generated = []
        self.total_cost = 0.0
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.session_dir, exist_ok=True)

    # ─── Lifecycle ──────────────────────────────────────────────────────

    async def start(self, timeout_login: int = 600, initial_url: str = None):
        from playwright.async_api import async_playwright

        # Remove lock de execução anterior — se existir, o Chrome cai num perfil
        # TEMP/guest em vez do perfil persistente, e aí não dá pra logar.
        for lf in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            lock = os.path.join(self.session_dir, lf)
            if os.path.exists(lock):
                try:
                    os.remove(lock)
                except Exception:
                    pass

        print("[Obscura] Abrindo navegador com perfil persistente do Chrome...")
        self._pw = await async_playwright().start()

        self._context = await self._pw.chromium.launch_persistent_context(
            user_data_dir=self.session_dir,
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled",
                  "--no-first-run", "--no-default-browser-check"],
        )

        self._page = await self._context.new_page()
        target = initial_url or self.project_url or GOOGLE_FLOW_URL
        print(f"[Obscura] Navegando para {target}")
        await self._page.goto(target, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(4)

        # Anti-pause shim + keep-alive (ELTON FLOW)
        try:
            await self._page.evaluate(AWAKE_SHIM_JS)
        except Exception as e:
            print(f"[Obscura] aviso shim: {e}")

        # Garante sessão Google autenticada (detecta no navegador, sem input()).
        await self._wait_until_logged_in(timeout=timeout_login)

        print("[Obscura] Navegador aberto e autenticado")

    async def stop(self):
        if self._context:
            try:
                await self._context.storage_state(path=os.path.join(self.session_dir, "state.json"))
            except Exception:
                pass
            await self._context.close()
        if self._pw:
            await self._pw.stop()
        print("[Obscura] Navegador fechado")

    # ─── Google Flow Automation ─────────────────────────────────────────

    async def _check_signed_in(self) -> dict:
        """
        Detecta autenticação REAL via cookies de sessão do Google
        (1PSID / __Secure-1PSID / OSID / SAPISID / APISID). Esses cookies só
        existem após login completo — não dão falso positivo na tela
        'Escolher conta' nem falso negativo no Flow.
        """
        try:
            cookies = await self._context.cookies()
            names = {c.get("name") for c in cookies}
            authed = bool(names & {"1PSID", "__Secure-1PSID", "OSID",
                                   "SAPISID", "APISID"})
            return {"signedIn": authed, "reason": "cookies" if authed else "no-auth-cookie"}
        except Exception:
            return {"signedIn": False}

    async def _wait_until_logged_in(self, timeout: int = 600):
        """
        Aguarda o login NA JANELA DO CHROME (sem input() no terminal).
        O usuário faz login manualmente na conta Google; assim que o chip/avatar
        da conta aparece, o sistema detecta e segue. Timeout -> erro claro.
        """
        if (await self._check_signed_in()).get("signedIn"):
            print("[Obscura] Sessão Google já autenticada (perfil reutilizado).")
            return

        print("\n" + "=" * 64)
        print("LOGIN GOOGLE NECESSÁRIO")
        print("=> Na janela do Chrome que abriu, faça login na sua CONTA GOOGLE")
        print("   (a mesma do YouTube/Flow). NÃO use 'Navegar como convidado'.")
        print("=> O sistema detecta sozinho quando você entrar — não digite nada")
        print("   no terminal. Se não aparecer a tela de login, clique em")
        print("   'Fazer login' / 'Sign in' no canto superior direito do Flow.")
        print("=" * 64)

        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(3)
            if (await self._check_signed_in()).get("signedIn"):
                print("[Obscura] Login detectado! Sessão autenticada.")
                # Recarrega o Flow já autenticado e confirma que está logado LÁ também
                try:
                    await self._page.goto(self.project_url or GOOGLE_FLOW_URL,
                                          wait_until="domcontentloaded", timeout=60000)
                    await asyncio.sleep(4)
                    await self._page.evaluate(AWAKE_SHIM_JS)
                    flow_ok = (await self._check_signed_in()).get("signedIn")
                    print(f"[Obscura] Flow autenticado: {flow_ok}")
                except Exception as e:
                    print(f"[Obscura] aviso ao confirmar Flow: {e}")
                return
            print(f"[Obscura] Aguardando login... ainda desconectado "
                  f"({int(deadline - time.time())}s restantes)")
        raise RuntimeError(
            "Timeout de login Google. Abra o Chrome, faça login na Conta do Google e "
            "rode novamente (ou use: python scripts/seed_google_flow.py)."
        )

    async def _enter_flow_editor(self):
        """Entra no editor de IMAGEM do Flow: fecha modais, abre um projeto
        existente (ou cria um novo) e espera o editor Slate."""
        url = self._page.url or ""
        if "tools/flow" not in url:
            await self._page.goto(self.project_url or GOOGLE_FLOW_URL,
                                  wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5)
        # Fecha modais de boas-vindas
        for label in ["Dispensar", "Entendi", "Got it", "Fechar", "close",
                       "Comece a usar o Flow"]:
            try:
                els = self._page.get_by_text(label, exact=False)
                for i in range(await els.count()):
                    try:
                        await els.nth(i).click(timeout=2000, force=True, no_wait_after=True)
                    except Exception:
                        pass
            except Exception:
                pass
        await asyncio.sleep(2)
        # Se já estamos num projeto, só espera o editor
        if "/project/" in (self._page.url or ""):
            await self._wait_slate()
            return
        # Tenta navegar para um projeto existente via link <a>
        project_url = await self._find_project_link()
        if project_url:
            print(f"[Obscura] abrindo projeto existente: {project_url}")
            await self._page.goto(project_url, wait_until="commit", timeout=60000)
            await self._wait_slate()
            return
        # Se não achou link, clica "Novo projeto" (sem force para disparar React)
        print("[Obscura] nenhum projeto encontrado, tentando 'Novo projeto'...")
        try:
            btn = self._page.get_by_role("button", name="Novo projeto")
            await btn.click(timeout=10000)
            await asyncio.sleep(5)
        except Exception:
            try:
                await self._page.get_by_text("Novo projeto", exact=False).first.click(
                    timeout=10000)
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[Obscura] aviso criar projeto: {e}")
        # Se criou um projeto, pode ter redirecionado para /project/
        if "/project/" in (self._page.url or ""):
            await self._wait_slate()
            return
        # Último recurso: tenta achar link de projeto de novo
        project_url = await self._find_project_link()
        if project_url:
            await self._page.goto(project_url, wait_until="commit", timeout=60000)
            await self._wait_slate()
            return
        print("[Obscura] FALHA: não conseguiu entrar num projeto")

    async def _find_project_link(self):
        """Busca o primeiro link <a> para /project/ na página atual."""
        try:
            href = await self._page.locator('a[href*="/project/"]').first.get_attribute(
                "href", timeout=5000)
            if href:
                return href if href.startswith("http") else "https://labs.google" + href
        except Exception:
            pass
        # Fallback: tenta via JavaScript
        try:
            return await self._page.evaluate("""() => {
                const a = document.querySelector('a[href*="/project/"]');
                return a ? a.href : '';
            }""")
        except Exception:
            return ""

    async def _wait_slate(self):
        """Espera o editor Slate (data-slate-editor) aparecer e ficar visível."""
        try:
            await self._page.wait_for_selector(
                '[data-slate-editor="true"][contenteditable="true"]', timeout=45000)
        except Exception as e:
            print(f"[Obscura] editor não apareceu: {e}")
        await asyncio.sleep(2)

    def _scene_timestamp(self, scene_id: int) -> str:
        """Nome [MM-SS] por cena para sincronizar com o áudio."""
        mm = (scene_id * 5) // 60
        ss = (scene_id * 5) % 60
        return f"{mm:02d}-{ss:02d}"

    async def _submit_prompt(self, prompt: str) -> bool:
        """Foca no editor Slate, digita o prompt via keyboard (que atualiza o
        estado interno do React/Slate) e pressiona Enter para submeter."""
        try:
            editor = self._page.locator(
                '[data-slate-editor="true"][contenteditable="true"]').first
            await editor.click()
            await asyncio.sleep(0.3)
            await self._page.keyboard.press("Control+a")
            await asyncio.sleep(0.1)
            await self._page.keyboard.press("Delete")
            await asyncio.sleep(0.3)
            await self._page.keyboard.type(prompt, delay=5)
            await asyncio.sleep(1.5)
            state = await self._page.evaluate("""() => {
                const el = document.querySelector('[data-slate-editor="true"][contenteditable="true"]');
                for(const b of document.querySelectorAll('button')){
                    const s=b.querySelector('i.google-symbols');
                    if(s && s.textContent.trim()==='arrow_forward'){
                        return {len: (el?.innerText||'').length, ariaDisabled: b.getAttribute('aria-disabled')};
                    }
                }
                return null;
            }""")
            print(f"[Obscura] typed: len={state.get('len') if state else '?'} btn={state.get('ariaDisabled') if state else '?'}")
            if state and state.get("ariaDisabled") == "true":
                print("[Obscura] botao desabilitado apos typing, pulando")
                return False
        except Exception as e:
            print(f"[Obscura] erro ao digitar prompt: {e}")
            return False
        try:
            await self._page.keyboard.press("Enter")
            print("[Obscura] submit: Enter")
            return True
        except Exception as e:
            print(f"[Obscura] falha ao submeter: {e}")
            return False

    async def _fetch_media_bytes(self, url: str, is_video: bool,
                                 seen_names: set) -> dict:
        """Tenta API projectInitialData; senão cai no fetch direto da URL."""
        # 1) Se a URL já é o endpoint de redirect, baixa direto no main world
        if "getMediaUrlRedirect" in url or url.startswith("http"):
            r = await self._page.evaluate(FETCH_MEDIA_JS, {"url": url, "isVideo": is_video})
            if r.get("ok"):
                return r
        return {"ok": False, "error": r.get("error", "no media") if 'r' in dir() else "skip"}

    async def _wait_and_grab(self, scene_id: int, seen: set,
                             timeout_ms: int = 180000) -> dict:
        """
        Aguarda uma mídia NOVA (não vista) e devolve seus bytes.
        Estratégia: API projectInitialData (se em /project/<id>) → fallback DOM.
        """
        start = time.time()
        last_count = -1
        settle_until = 0

        async def current_candidates():
            # API primeiro
            try:
                api = await self._page.evaluate(MEDIA_LIST_JS)
                if api.get("ok") and api.get("media"):
                    cands = []
                    for m in api["media"]:
                        name = m.get("name", "")
                        if name in seen:
                            continue
                        cands.append({"name": name, "url": m.get("url", ""),
                                      "kind": m.get("kind", "image")})
                    return cands
            except Exception:
                pass
            # Fallback DOM
            try:
                imgs = await self._page.evaluate(GENERATED_IMGS_JS)
                return [{"name": (i.get("name") or "").split("?")[0],
                         "src": i.get("src", ""), "kind": "image"}
                        for i in imgs if i.get("src")]
            except Exception:
                return []

        while (time.time() - start) * 1000 < timeout_ms:
            cands = await current_candidates()
            # filtra já vistos (DOM fallback pode não trazer name estável)
            new = [c for c in cands
                   if c.get("name") and c["name"] not in seen]
            if not new and cands:
                # DOM fallback: pega a última imagem visível se ainda não baixamos nada
                new = [cands[-1]]
            if new:
                if len(new) != last_count:
                    last_count = len(new)
                    settle_until = time.time() + 2.5
                    await asyncio.sleep(0.7)
                    continue
                if time.time() >= settle_until:
                    c = new[0]
                    url = c.get("url") or c.get("src")
                    if url:
                        is_vid = c.get("kind") == "video"
                        res = await self._fetch_media_bytes(url, is_vid, seen)
                        if res.get("ok"):
                            return {"ok": True, "name": c.get("name", ""), **res}
            await asyncio.sleep(0.8)

        return {"ok": False, "error": "timeout aguardando mídia da cena " + str(scene_id)}

    async def _save_dataurl(self, data_url: str, scene_id: int, kind: str) -> str:
        ext = "mp4" if kind == "video" else "png"
        b64 = data_url.split(",", 1)[1] if "," in data_url else ""
        raw = base64.b64decode(b64)
        ts = self._scene_timestamp(scene_id)
        filename = f"scene_{scene_id:03d}_{ts}.{ext}"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(raw)
        return filepath

    # ─── Batch Generation ───────────────────────────────────────────────

    async def generate_scene_images(self, scenes: list, method: str = "imagefx",
                                    on_progress=None) -> list:
        total = len(scenes)
        results = []
        if method != "imagefx":
            print("[Obscura] método só suporta 'imagefx' (Google Flow)")
        print(f"[Obscura] Gerando {total} imagens via Google Flow (GRÁTIS)...")

        if not (await self._check_signed_in()).get("signedIn"):
            raise RuntimeError(
                "Não autenticado no Google. Rode 'python scripts/seed_google_flow.py', "
                "faça login na Conta do Google na janela do Chrome e tente de novo."
            )

        # Entra no editor de imagem do Flow (cria projeto se preciso)
        await self._enter_flow_editor()

        seen = set()
        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            prompt = scene.get("full_prompt", "")
            if on_progress:
                on_progress(scene_id, total, "generating")
            try:
                await self._submit_prompt(prompt)
                grab = await self._wait_and_grab(scene_id, seen)
                if grab.get("ok"):
                    seen.add(grab.get("name", ""))
                    kind = "video" if grab.get("type", "").startswith("video") else "image"
                    filepath = await self._save_dataurl(grab["dataUrl"], scene_id, kind)
                    size_kb = os.path.getsize(filepath) / 1024
                    result = {
                        "scene_id": scene_id, "path": filepath,
                        "filename": os.path.basename(filepath),
                        "prompt": prompt, "model": "google_flow",
                        "cost": 0.0, "size_kb": round(size_kb, 1),
                    }
                    results.append(result)
                    print(f"[Obscura] Cena {scene_id} OK | {size_kb:.0f}KB | $0.00")
                else:
                    raise RuntimeError(grab.get("error"))
                if on_progress:
                    on_progress(scene_id, total, "done")
                if i < total - 1:
                    await asyncio.sleep(3)
            except Exception as e:
                print(f"[Obscura] FALHA cena {scene_id}: {e}")
                results.append({
                    "scene_id": scene_id, "path": None, "error": str(e),
                    "narration": scene.get("narration", ""),
                    "duration_seconds": scene.get("duration_seconds", 5.0),
                })

        ok = sum(1 for r in results if r.get("path"))
        print(f"[Obscura] {ok}/{total} imagens | Custo: $0.00")
        return results
