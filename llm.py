import json
import re
import requests
from config import OLLAMA_URL, MODEL, NUM_CTX


def chat(system, user, temperature=0.4, json_mode=False, model=None):
    """Local Ollama model ko call karta hai. Koi paid API nahi."""
    payload = {
        "model": model or MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": NUM_CTX},
    }
    if json_mode:
        payload["format"] = "json"
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=1800)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama chal nahi raha. Pehle 'ollama serve' chalao aur model pull karo.")
    return r.json()["message"]["content"].strip()


def parse_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None
