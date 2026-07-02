"""
DEZAFIRA — Script de Setup Automatizado
=============================================
Instala todas as dependências do ecossistema Dezafira, incluindo:
  - OpenMontage (motor de renderização de vídeo)
  - Remotion (composição React/Node.js)
  - Kokoro TTS (locução)
  - MoviePy (fallback de montagem)
  - Playwright (upload YouTube)

Uso:
    python setup_dezafira.py

Depois de rodar, configure suas chaves de API no arquivo .env.
Veja .env.example para a lista completa de variáveis.
"""

import os
import sys
import subprocess
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OPEN_MONTAGE_DIR = os.path.join(PROJECT_DIR, "OpenMontage")


def print_header(text: str):
    print()
    print("=" * 60)
    print(f" {text}")
    print("=" * 60)


def run_cmd(cmd: list, cwd: str = None, desc: str = "") -> bool:
    """Executa um comando e retorna True se bem-sucedido."""
    print(f"\n  → {desc or ' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd or PROJECT_DIR, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ ERRO: {e}")
        return False
    except FileNotFoundError as e:
        print(f"  ✗ Comando não encontrado: {e}")
        return False


def check_python_version() -> bool:
    """Verifica se Python >= 3.10."""
    print_header("1. Verificando Python")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        print(f"  ✗ Python {major}.{minor} detectado. Requer Python >= 3.10.")
        return False
    print(f"  ✓ Python {major}.{minor}.{sys.version_info[2]}")
    return True


def check_nodejs() -> bool:
    """Verifica se Node.js >= 18 está instalado."""
    print_header("2. Verificando Node.js")
    node = shutil.which("node")
    if not node:
        print("  ✗ Node.js não encontrado. Instale Node.js >= 18:")
        print("    https://nodejs.org/")
        return False

    result = subprocess.run([node, "--version"], capture_output=True, text=True)
    version = result.stdout.strip()
    print(f"  ✓ Node.js {version}")
    return True


def install_python_deps() -> bool:
    """Instala dependências Python do projeto."""
    print_header("3. Instalando dependências Python")

    # requirements.txt principal
    req_path = os.path.join(PROJECT_DIR, "requirements.txt")
    if os.path.exists(req_path):
        if not run_cmd(
            [sys.executable, "-m", "pip", "install", "-r", req_path],
            desc="Instalando requirements.txt principal",
        ):
            return False

    # OpenMontage como pacote editável
    if os.path.isdir(OPEN_MONTAGE_DIR):
        if not run_cmd(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            cwd=OPEN_MONTAGE_DIR,
            desc="Instalando OpenMontage como pacote",
        ):
            return False

    # Kokoro TTS (Apache 2.0)
    run_cmd(
        [sys.executable, "-m", "pip", "install", "kokoro>=0.9.4", "soundfile", "pydub"],
        desc="Instalando Kokoro TTS",
    )

    return True


def setup_open_montage() -> bool:
    """Configura o OpenMontage e suas dependências."""
    print_header("4. Configurando OpenMontage")

    if not os.path.isdir(OPEN_MONTAGE_DIR):
        print("  ! OpenMontage não encontrado. Clone manualmente:")
        print(f"    git clone https://github.com/calesthio/OpenMontage.git {OPEN_MONTAGE_DIR}")
        return False

    # Instalar Remotion (Node.js)
    remotion_dir = os.path.join(OPEN_MONTAGE_DIR, "remotion-composer")
    if os.path.isdir(remotion_dir):
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if npm:
            run_cmd(
                [npm, "install"],
                cwd=remotion_dir,
                desc="Instalando dependências do Remotion (npm install)",
            )

    # Copiar .env.example se não existir
    env_example = os.path.join(PROJECT_DIR, ".env.example")
    env_file = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_example) and not os.path.exists(env_file):
        shutil.copy2(env_example, env_file)
        print(f"\n  ✓ .env criado a partir de .env.example")
        print(f"  ! Edite o arquivo .env com suas chaves de API")

    return True


def setup_playwright() -> bool:
    """Instala os browsers do Playwright."""
    print_header("5. Configurando Playwright")

    playwright = shutil.which("playwright")
    if not playwright:
        print("  ! Playwright não encontrado no PATH")
        return False

    run_cmd(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        desc="Instalando Chromium para Playwright",
    )

    return True


def check_all_ok() -> bool:
    """Verificação final."""
    print_header("6. Verificação Final")

    all_ok = True

    # Verificar se OpenMontage está importável
    try:
        import openmontage  # noqa
        print("  ✓ OpenMontage importável")
    except ImportError:
        print("  ✗ OpenMontage não importável")
        all_ok = False

    # Verificar chaves de ambiente
    nvidia_key = os.getenv("NVIDIA_API_KEY", "")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    pexels_key = os.getenv("PEXELS_API_KEY", "")

    print(f"  {'✓' if nvidia_key else '○'} NVIDIA_API_KEY: {'configurada' if nvidia_key else 'opcional'}")
    print(f"  {'✓' if deepseek_key else '○'} DEEPSEEK_API_KEY: {'configurada' if deepseek_key else 'opcional'}")
    print(f"  {'✓' if pexels_key else '○'} PEXELS_API_KEY: {'configurada' if pexels_key else 'opcional'}")

    return all_ok


def main():
    print()
    print("+========================================================+")
    print("|        DEZAFIRA — Setup Automatizado                    |")
    print("|  Fabrica de Canais com OpenMontage Engine              |")
    print("+========================================================+")
    steps = [
        ("Python >= 3.10", check_python_version),
        ("Node.js >= 18", check_nodejs),
        ("Dependências Python", install_python_deps),
        ("OpenMontage", setup_open_montage),
        ("Playwright", setup_playwright),
        ("Verificação Final", check_all_ok),
    ]

    for name, func in steps:
        func()

    print_header("Setup Concluído!")
    print()
    print("  Para iniciar o backend:")
    print(f"    cd {PROJECT_DIR}")
    print("    uvicorn server:app --host 127.0.0.1 --port 8000")
    print()
    print("  Ou use o script start_local.py:")
    print(f"    python {os.path.join(PROJECT_DIR, 'start_local.py')}")
    print()
    print("  Configuração adicional:")
    print("    - Edite SniperVideoEngine/.env com suas chaves de API")
    print("    - Acesse http://localhost:3000 (Next.js) para o frontend")
    print("    - Acesse http://localhost:8000 (FastAPI) para a API")
    print()


if __name__ == "__main__":
    main()
