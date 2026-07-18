"""
Dezafira CapCut Agent — ETAPA B do plano: agente de finalização que abre o
CapCut, carrega o draft editável e clica em **Export** para renderizar o MP4 final.

Estratégia: o CapCut Desktop é Electron, então conectamos via
`chromium.connect_over_cdp` (mesma técnica do ELTON FLOW no main world) ao
processo do app iniciado com `--remote-debugging-port`. Os seletores exatos do
CapCut podem mudar entre versões — por isso TODA a interação é feita por
texto visível ("Export"/"Exportar") com fallback, e o render é detectado
polling a pasta de saída.

Uso:
    from modules.capcut_agent import CapcutAgent
    agent = CapcutAgent()
    agent.launch()              # abre o CapCut com porta de debug
    page = agent.connect()      # conecta no Electron
    agent.export("saida.mp4")   # clica Export e espera o render
"""
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

DEFAULT_DEBUG_PORT = 9222


def find_capcut_exe() -> str:
    """Localiza o executável do CapCut (Windows)."""
    candidatos = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "CapCut", "Apps",
                     "CapCut", "CapCut.exe"),
        os.path.join(os.environ.get("PROGRAMFILES", ""), "CapCut", "Apps",
                     "CapCut", "CapCut.exe"),
        r"C:\Program Files\CapCut\Apps\CapCut\CapCut.exe",
        r"C:\Program Files (x86)\CapCut\Apps\CapCut\CapCut.exe",
    ]
    for c in candidatos:
        if c and os.path.isfile(c):
            return c
    return ""


def default_export_dir() -> str:
    """Pasta padrão onde o CapCut salva os renders (Windows)."""
    videos = os.path.join(os.environ.get("USERPROFILE", ""), "Videos", "CapCut")
    return videos if os.path.isdir(videos) else os.path.join(
        os.environ.get("USERPROFILE", ""), "Videos")


class CapcutAgent:
    """Agente de UI para finalizar o draft do CapCut (render → MP4)."""

    def __init__(self, debug_port: int = DEFAULT_DEBUG_PORT, exe_path: str = ""):
        self.debug_port = debug_port
        self.exe_path = exe_path or find_capcut_exe()
        self._process = None
        self._pw = None
        self._browser = None
        self._page = None

    # ─── Launch / Connect ────────────────────────────────────────────

    def launch(self, extra_args=None):
        """Abre o CapCut com a porta de debug remoto habilitada."""
        if not self.exe_path:
            raise RuntimeError(
                "Executável do CapCut não encontrado. Informe exe_path ou "
                "instale o CapCut Desktop."
            )
        args = [self.exe_path, f"--remote-debugging-port={self.debug_port}"]
        if extra_args:
            args += extra_args
        print(f"[CapcutAgent] Abrindo CapCut: {self.exe_path} (porta {self.debug_port})")
        self._process = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL)
        # Espera o Electron subir o endpoint de debug
        for _ in range(30):
            if self._devtools_up():
                break
            time.sleep(1)
        else:
            raise RuntimeError("CapCut não subiu a porta de debug em 30s.")

    def _devtools_up(self) -> bool:
        import urllib.request
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.debug_port}/json/version", timeout=1
            ):
                return True
        except Exception:
            return False

    def connect(self):
        """Conecta no processo Electron do CapCut via CDP (Playwright)."""
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(
            f"http://127.0.0.1:{self.debug_port}"
        )
        # Pega a primeira página de conteúdo (renderer principal do app)
        contexts = self._browser.contexts
        page = None
        for ctx in contexts:
            if ctx.pages:
                page = ctx.pages[0]
                break
        if page is None:
            page = self._browser.new_page()
        self._page = page
        print("[CapcutAgent] Conectado ao CapCut.")
        return page

    # ─── Helpers de clique por texto ──────────────────────────────────

    def _click_by_text(self, *texts, timeout=15):
        """Clica no primeiro botão/elemento clicável cujo texto bate."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for txt in texts:
                try:
                    el = self._page.locator(f"text={txt}").first
                    if el.count() and el.is_visible():
                        el.click()
                        print(f"[CapcutAgent] Clicou em: {txt}")
                        return True
                except Exception:
                    pass
            time.sleep(1)
        return False

    def focus_app(self):
        """Traz o CapCut pra frente (melhora a estabilidade dos cliques)."""
        try:
            self._page.bring_to_front()
        except Exception:
            pass

    # ─── Ações ───────────────────────────────────────────────────────

    def open_draft(self, draft_path: str):
        """
        Leva o draft pra frente. O draft já está na pasta de projetos do CapCut
        (o exporter registrou no root_meta_info), então ele aparece nos
        'Projetos recentes'. Se o CapCut já estiver aberto no draft, ótimo;
        caso contrário o usuário pode abrir à mão (degradação graciosa).
        """
        self.focus_app()
        print(f"[CapcutAgent] Draft alvo: {draft_path}")
        # O CapCut normalmente abre o último projeto editado ao iniciar.
        # Não há URL estável p/ abrir um draft específico via CDP; confiamos
        # no 'recentes'. Se precisar, o humano abre 1x.
        return True

    def export(self, output_path: str, resolution: str = "1080x1920",
               fps: int = 30, timeout: int = 600) -> dict:
        """
        Clica em Export, ajusta resolução/FPS e espera o MP4 aparecer.

        CapCut salva no diretório de export do usuário; fazemos polling da
        pasta de saída por um .mp4 novo.
        """
        if not self._page:
            raise RuntimeError("Conecte no CapCut antes de exportar (connect()).")

        out_dir = os.path.dirname(os.path.abspath(output_path))
        os.makedirs(out_dir, exist_ok=True)
        out_name = os.path.basename(output_path)

        before = {f for f in os.listdir(out_dir)} if os.path.isdir(out_dir) else set()

        self.focus_app()
        # 1) Abrir o painel de exportação
        clicked = self._click_by_text("Export", "Exportar", "导出")
        if not clicked:
            return {"ok": False, "error": "Botão Export não encontrado."}

        # 2) (best-effort) ajustar resolução/fps nos campos — seletores variam
        try:
            self._page.fill('input[placeholder*="1080"], input[placeholder*="resolution"]',
                            resolution, timeout=3)
        except Exception:
            pass

        # 3) Clicar no botão final de exportar (mesmo rótulo, 2ª aparição)
        self._click_by_text("Export", "Exportar", "导出")
        time.sleep(2)
        self._click_by_text("Export", "Exportar", "导出")

        # 4) Esperar o render aparecer na pasta de saída
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.isdir(out_dir):
                novos = [f for f in os.listdir(out_dir)
                         if f.lower().endswith(".mp4") and f not in before]
                if novos:
                    src = os.path.join(out_dir, novos[0])
                    # Se o nome não bate, renomeia/copia p/ output_path
                    if src != output_path:
                        try:
                            shutil.copy2(src, output_path)
                        except Exception:
                            output_path = src
                    return {"ok": True, "path": output_path}
            time.sleep(3)
        return {"ok": False,
                "error": f"Render não apareceu em {out_dir} após {timeout}s."}

    def apply_actions(self, actions: list = None):
        """
        ETAPA 8 (opcional): ações extras de UI. Por enquanto best-effort:
        'auto_caption' tenta clicar no auto-caption do CapCut.
        """
        actions = actions or []
        for a in actions:
            if a == "auto_caption":
                self._click_by_text("Legendas automáticas", "Auto caption",
                                    "自动字幕")
            elif a == "remove_silence":
                self._click_by_text("Remover silêncio", "Remove silence")

    def finalize(self, draft_path: str, output_path: str,
                 resolution: str = "1080x1920", fps: int = 30,
                 actions: list = None, launch: bool = True,
                 connect: bool = True) -> dict:
        """Orquestra: abre CapCut → carrega draft → (ações) → Export → MP4."""
        try:
            if launch:
                self.launch()
            if connect:
                self.connect()
            self.open_draft(draft_path)
            if actions:
                self.apply_actions(actions)
            return self.export(output_path, resolution=resolution, fps=fps)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            self.close()

    def close(self):
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        # Não mata o CapCut (pode estar sendo usado); apenas desconecta.
