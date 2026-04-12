import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# LLM
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
MINIMAX_MODEL_FAST = os.getenv("MINIMAX_MODEL_FAST", "MiniMax-M2.7-highspeed")

# Database
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(_project_root / "data" / "delirium.db"))

# Prompts
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
S1_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "s1_system.txt"
S2_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "s2_system.txt"


def get_s1_prompt() -> str:
    return S1_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def get_s2_prompt() -> str:
    return S2_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
