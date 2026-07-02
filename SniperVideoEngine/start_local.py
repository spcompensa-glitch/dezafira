"""
Dezafira - Startup Local
- Seeds SQLite with existing videos from outputs/
- Starts FastAPI server on port 8000
"""
import os, sys, sqlite3, socket
from datetime import datetime, timedelta

# Ensure correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print(" DEZAFIRA - INICIALIZACAO LOCAL")
print("=" * 60)

# -- STEP 1: Seed DB --
db_path = os.path.join(os.getcwd(), "dezafira.db")
print("[DB] Caminho: {}".format(db_path))

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'starting',
        prompt TEXT NOT NULL,
        error TEXT,
        video_url TEXT,
        channel_id TEXT DEFAULT 'default',
        approval_status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

cur.execute("SELECT count(*) FROM predictions")
existing = cur.fetchone()[0]
print("[DB] Registros existentes: {}".format(existing))

if existing == 0:
    outputs_dir = os.path.join(os.getcwd(), "outputs")
    video_files = {
        "sniper_ff5ecf7e_preview.mp4": ("sniper_ff5ecf7e", "Como a IA esta transformando o mundo em 2026", "approved"),
        "sniper_6cdc3ad5_preview.mp4": ("sniper_6cdc3ad5", "3 Segredos do Dropshipping com IA", "pending"),
        "test_vertical_9x16.mp4": ("test_vertical", "Teste vertical 9x16 - Shorts/TikTok", "pending"),
        "test_horizontal_16x9.mp4": ("test_horizontal", "Teste horizontal 16x9 - YouTube", "pending"),
    }
    
    now = datetime.now()
    i = 0
    for filename, (pid, prompt, approval) in video_files.items():
        filepath = os.path.join(outputs_dir, filename)
        if os.path.exists(filepath):
            cur.execute(
                "INSERT INTO predictions (id, status, prompt, video_url, channel_id, approval_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, "completed", prompt, "/outputs/{}".format(filename), "default", approval, (now - timedelta(days=i)).isoformat())
            )
            print("  [OK] {} -> {}".format(filename, pid))
            i += 1
    conn.commit()
    print("[DB] {} registros inseridos.".format(i))
else:
    print("[DB] Banco ja populado.")

cur.execute("SELECT id, status, prompt, video_url, approval_status FROM predictions ORDER BY created_at DESC")
print("\n=== VIDEOS NO BANCO ===")
for row in cur.fetchall():
    print("  {} | {} | {} | {} | approval={}".format(row[0], row[1], row[2][:50], row[3], row[4]))
conn.close()

# -- STEP 2: Check API keys --
from dotenv import load_dotenv
load_dotenv()
nvidia = os.getenv("NVIDIA_API_KEY", "")
deepseek = os.getenv("DEEPSEEK_API_KEY", "")
pexels = os.getenv("PEXELS_API_KEY", "")
print("\n=== API KEYS ===")
print("  NVIDIA_API_KEY: {}".format("OK" if nvidia else "MISSING"))
print("  DEEPSEEK_API_KEY: {}".format("OK" if deepseek else "MISSING"))
print("  PEXELS_API_KEY: {}".format("OK" if pexels else "MISSING"))

# -- STEP 3: Check outputs --
print("\n=== VIDEOS EM OUTPUTS ===")
outputs_dir = os.path.join(os.getcwd(), "outputs")
for f in os.listdir(outputs_dir):
    if f.endswith(('.mp4', '.mp3', '.wav')):
        size = os.path.getsize(os.path.join(outputs_dir, f)) / (1024 * 1024)
        print("  {} ({:.1f}MB)".format(f, size))

# -- STEP 4: Check port --
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('127.0.0.1', 8000))
    s.close()
    print("\n[OK] Porta 8000 disponivel")
except OSError:
    print("\n[!] Porta 8000 em uso - tentando liberar...")
    s.close()

# -- STEP 5: Set DATABASE_URL so database.py uses the file, not :memory: --
db_abs = os.path.join(os.getcwd(), "dezafira.db")
# SQLAlchemy needs forward slashes on Windows
db_url = "sqlite:///" + db_abs.replace("\\", "/")
os.environ["DATABASE_URL"] = db_url
print("\n[DB] DATABASE_URL set to: {}".format(db_url))

print("\n" + "=" * 60)
print(" Iniciando FastAPI em http://127.0.0.1:8000")
print(" API History: http://127.0.0.1:8000/api/v1/predictions/history")
print(" Outputs: http://127.0.0.1:8000/outputs/")
print("=" * 60 + "\n")

# -- STEP 6: Start server --
import uvicorn
uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
