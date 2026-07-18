"""
FlowAgent — dono da integração Google Flow no Dezafira.

Responsabilidades:
- Sessão Chromium persistente, serializada (1 browser por vez, com lock em
  arquivo) para nunca abrir perfil temporário/guest nem deixar processos zumbis.
- Health-check real: confirma se está logado (cookies) e qual a conta.
- Contador diário de imagens geradas (persistido), com detecção de teto do Flow.
- Fallback gracioso para Pollinations (grátis, sem chave) quando o Flow falta
  ou estoura a cota.
- Geração idempotente por chamada: preenche cenas que faltaram via fallback.
"""
import asyncio
import json
import os
import time
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"
STATE_PATH = OUTPUT_DIR / "flow_agent_state.json"
LOCK_PATH = OUTPUT_DIR / "browser_session" / ".flow_agent.lock"
IMAGES_DIR = OUTPUT_DIR / "ai_images"


def _pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


class FlowAgent:
    def __init__(self):
        self.state = self._load_state()
        self._lock_held = False

    def _load_state(self):
        if STATE_PATH.exists():
            try:
                return json.loads(STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"date": "", "generated": 0, "cap": int(os.getenv("FLOW_DAILY_CAP", "0")) or 0,
                "mode": "adapted", "account_email": "", "expected_email": os.getenv("FLOW_ACCOUNT_EMAIL", ""),
                "last_ok": None, "last_error": None, "fallbacks": 0}

    def _save_state(self):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(self.state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _rollover_day(self):
        today = date.today().isoformat()
        if self.state.get("date") != today:
            self.state["date"] = today
            self.state["generated"] = 0
            self._save_state()

    def usage(self):
        self._rollover_day()
        gen = self.state.get("generated", 0)
        cap = self.state.get("cap", 0)
        per_video = int(os.getenv("FLOW_IMAGES_PER_VIDEO", "8")) or 8
        remaining = (cap - gen) if cap else None
        return {"date": self.state.get("date"), "generated": gen, "cap": cap,
                "remaining": remaining,
                "videos_remaining_estimate": (remaining // per_video) if remaining is not None else None}

    def can_generate(self, n=1):
        self._rollover_day()
        cap = self.state.get("cap", 0)
        if cap and self.state.get("generated", 0) + n > cap:
            return False
        return True

    def record(self, n):
        self._rollover_day()
        self.state["generated"] = self.state.get("generated", 0) + n
        self._save_state()

    def _acquire_lock(self, timeout=60):
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if LOCK_PATH.exists():
                try:
                    data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
                    if _pid_alive(data.get("pid")) and time.time() - data.get("ts", 0) < 1800:
                        time.sleep(2)
                        continue
                except Exception:
                    pass
            LOCK_PATH.write_text(json.dumps({"pid": os.getpid(), "ts": time.time()}))
            self._lock_held = True
            return True
        raise RuntimeError("FlowAgent: sessão do Flow ocupada por outro processo")

    def _release_lock(self):
        if self._lock_held and LOCK_PATH.exists():
            try:
                LOCK_PATH.unlink()
            except Exception:
                pass
        self._lock_held = False

    async def _get_account_email(self, page):
        try:
            await page.goto("https://myaccount.google.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4)
            return await page.evaluate("""() => {
                const m = (document.body.innerText||'').match(/[a-z0-9._%+-]+@[a-z0-9.-]+\\.[a-z]{2,}/i);
                if (m) return m[0];
                const av = document.querySelector('img[alt*="@"]');
                return av ? av.alt : '';
            }""")
        except Exception:
            return ""

    async def health(self, deep=False):
        self._rollover_day()
        if not deep:
            return {"logged_in": bool(self.state.get("account_email")),
                    "account_email": self.state.get("account_email"),
                    "expected_email": self.state.get("expected_email"),
                    "mode": self.state.get("mode"),
                    "usage": self.usage(),
                    "last_ok": self.state.get("last_ok"),
                    "last_error": self.state.get("last_error"),
                    "fallbacks": self.state.get("fallbacks", 0)}
        self._acquire_lock()
        info = {"logged_in": False, "account_email": "", "mode": "adapted", "usage": self.usage()}
        try:
            from modules.obscura_image_gen import ObscuraImageGen
            gen = ObscuraImageGen()
            await gen.start()
            authed = (await gen._check_signed_in()).get("signedIn")
            email = await self._get_account_email(gen._page)
            await gen.stop()
            info["logged_in"] = authed
            info["account_email"] = email
            self.state["account_email"] = email
            self.state["mode"] = "adapted"
            if self.state.get("expected_email") and email and email.lower() != self.state["expected_email"].lower():
                info["account_mismatch"] = True
            self._save_state()
        except Exception as e:
            info["last_error"] = str(e)
        finally:
            self._release_lock()
        return info

    def _flow_exhausted(self, results):
        for r in results:
            err = (r.get("error") or "").lower()
            if any(k in err for k in ("limit", "limite", "quota", "429", "rate",
                                       "too many", "tente novamente", "try again",
                                       "esgotad", "exceeded", "unavailable")):
                return True
        return False

    async def _fallback(self, scenes, on_progress, reason):
        """Fallback em cascata: Pollinations (grátis) → OpenRouter/Gemini (~$0.04/img)."""
        # Passo 1: Tenta Pollinations (grátis)
        out = await self._fallback_pollinations(scenes, on_progress)

        # Passo 2: Preenche falhas com OpenRouter/Gemini
        missing = [i for i, r in enumerate(out) if not r.get("path")]
        if missing:
            out = await self._fallback_gemini([scenes[i] for i in missing], out,
                                              missing, on_progress)

        self.state["fallbacks"] = self.state.get("fallbacks", 1)
        self._save_state()
        return out

    async def _fallback_pollinations(self, scenes, on_progress):
        """Gera imagens via Pollinations (grátis, sem quota)."""
        from modules.pollinations_client import PollinationsClient
        client = PollinationsClient()
        out = []
        for i, s in enumerate(scenes):
            sid = s.get("scene_id", i + 1)
            prompt = s.get("full_prompt") or s.get("pollinations_prompt") or s.get("visual_prompt", "")
            path = os.path.join(str(IMAGES_DIR), f"scene_{sid:03d}_pollinations.png")
            if on_progress:
                on_progress(sid, len(scenes), "fallback-pollinations")
            try:
                res = await asyncio.to_thread(
                    client.generate, prompt, path, 1080, 1920, None, "curiosity", 42, 1)
            except Exception as e:
                res = None
            out.append({"scene_id": sid, "path": res, "model": "pollinations",
                        "cost": 0.0, "prompt": prompt,
                        "size_kb": round(os.path.getsize(res) / 1024) if res and os.path.exists(res) else 0})
        return out

    async def _fallback_gemini(self, scenes, existing, missing_idx, on_progress):
        """Gera imagens via OpenRouter/Gemini (~$0.04/img, alta qualidade)."""
        try:
            from modules.image_gen import ImageGenerator
            gen = ImageGenerator()
        except Exception as e:
            print(f"[FlowAgent] Gemini fallback indisponível: {e}")
            return existing

        for i, s in enumerate(scenes):
            sid = s.get("scene_id", missing_idx[i] + 1)
            prompt = s.get("full_prompt") or s.get("visual_prompt", "")
            if on_progress:
                on_progress(sid, len(existing), "fallback-gemini")
            try:
                result = await gen.generate_image(prompt, scene_id=sid)
                existing[missing_idx[i]] = {
                    "scene_id": sid, "path": result.get("path"),
                    "model": "gemini-flash", "cost": result.get("cost", 0.04),
                    "prompt": prompt,
                    "size_kb": result.get("size_kb", 0),
                }
                print(f"[FlowAgent] Gemini OK cena {sid}: ${result.get('cost', 0.04):.4f}")
            except Exception as e:
                print(f"[FlowAgent] Gemini falhou cena {sid}: {e}")
        return existing

    async def generate_images(self, plan, method="imagefx", on_progress=None):
        self._rollover_day()
        scenes = plan.get("scenes", [])

        if not self.can_generate(len(scenes)):
            return await self._fallback(scenes, on_progress, reason="quota")

        self._acquire_lock()
        try:
            from modules.obscura_image_gen import ObscuraImageGen
            gen = ObscuraImageGen()
            await gen.start()
            try:
                results = await gen.generate_scene_images(scenes, method=method, on_progress=on_progress)
            finally:
                await gen.stop()

            ok = sum(1 for r in results if r.get("path"))
            self.record(ok)
            self.state["last_ok"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            self.state["last_error"] = None

            if self._flow_exhausted(results) and not self.state.get("cap"):
                self.state["cap"] = self.state.get("generated", 0)

            missing_idx = [i for i, r in enumerate(results) if not r.get("path")]
            if missing_idx:
                fb = await self._fallback([scenes[i] for i in missing_idx], on_progress, reason="fill")
                for j, i in enumerate(missing_idx):
                    results[i] = fb[j]

            self._save_state()
            return results
        except Exception as e:
            self.state["last_error"] = str(e)
            self._save_state()
            return await self._fallback(scenes, on_progress, reason=f"error:{e}")
        finally:
            self._release_lock()
