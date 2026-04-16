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
VISION_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "vision_system.txt"


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def validate_prompt_files() -> None:
    missing = [path for path in (
        S1_SYSTEM_PROMPT_PATH,
        S2_SYSTEM_PROMPT_PATH,
        VISION_SYSTEM_PROMPT_PATH,
    ) if not path.exists()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(f"Missing prompt file(s): {names}")


def get_s1_prompt() -> str:
    return _read_prompt(S1_SYSTEM_PROMPT_PATH)


def get_s2_prompt() -> str:
    return _read_prompt(S2_SYSTEM_PROMPT_PATH)


def get_vision_prompt() -> str:
    return _read_prompt(VISION_SYSTEM_PROMPT_PATH)
