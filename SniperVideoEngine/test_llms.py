"""Test all 3 LLM providers"""
import os
import requests
from dotenv import load_dotenv
load_dotenv()

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
NVIDIA_KEY = os.getenv("NVIDIA_API_KEY", "")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")

MESSAGES = [
    {"role": "system", "content": "Responda apenas com 'OK'."},
    {"role": "user", "content": "Teste"}
]

def test_openrouter():
    if not OPENROUTER_KEY:
        print("[OPENROUTER] Chave NAO configurada")
        return False
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek/deepseek-chat", "messages": MESSAGES, "max_tokens": 10},
            timeout=60)
        if r.status_code == 200:
            print(f"[OPENROUTER] OK - {r.json()['choices'][0]['message']['content'][:50]}")
            return True
        print(f"[OPENROUTER] FALHOU Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"[OPENROUTER] FALHOU Erro: {e}")
    return False

def test_nvidia():
    if not NVIDIA_KEY:
        print("[NVIDIA] Chave NAO configurada")
        return False
    try:
        r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {NVIDIA_KEY}", "Content-Type": "application/json"},
            json={"model": "meta/llama-3.1-8b-instruct", "messages": MESSAGES, "max_tokens": 10},
            timeout=90)
        if r.status_code == 200:
            print(f"[NVIDIA] OK - {r.json()['choices'][0]['message']['content'][:50]}")
            return True
        print(f"[NVIDIA] FALHOU Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"[NVIDIA] FALHOU Erro: {e}")
    return False

def test_deepseek():
    if not DEEPSEEK_KEY:
        print("[DEEPSEEK] Chave NAO configurada")
        return False
    try:
        r = requests.post("https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": MESSAGES, "max_tokens": 10},
            timeout=60)
        if r.status_code == 200:
            print(f"[DEEPSEEK] OK - {r.json()['choices'][0]['message']['content'][:50]}")
            return True
        print(f"[DEEPSEEK] FALHOU Status {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"[DEEPSEEK] FALHOU Erro: {e}")
    return False

if __name__ == "__main__":
    print("=== Teste dos 3 provedores LLM ===\n")
    o = test_openrouter()
    n = test_nvidia()
    d = test_deepseek()
    print(f"\n=== Resultado: {sum([o,n,d])}/3 provedores funcionando ===")
