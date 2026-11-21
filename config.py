import os

# Sab kuch free + local: Ollama (https://ollama.com) par open-source model chalta hai
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("CONTENT_MODEL", "qwen2.5:7b-instruct")   # laptop weak ho to: qwen2.5:3b-instruct
NUM_CTX = int(os.getenv("NUM_CTX", "12288"))
MAX_REVIEW_LOOPS = int(os.getenv("MAX_REVIEW_LOOPS", "2"))   # reviewer kitni baar fix karwa sakta hai
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
