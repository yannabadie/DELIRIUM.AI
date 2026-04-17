import os
import re
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from src.persona.gag_contract import normalize_contract_key_parts
from src.persona.state import PERSONA_PHASES

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
DELIRIUM_DECAY_MODE = os.getenv("DELIRIUM_DECAY_MODE", "normal")
DELIRIUM_FORGETTING_STRATEGY = os.getenv("DELIRIUM_FORGETTING_STRATEGY", "decay")

# Prompts
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
S1_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "s1_system.txt"
S2_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "s2_system.txt"
VISION_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "vision_system.txt"
_S2_REQUIRED_TOKENS = (
    "intention",
    "defensiveness_score",
    "defensiveness_markers",
    "danger_level",
    "danger_signals",
    "themes_latents",
    "loop_detected",
    "loop_theme",
    "loop_count",
    "correlation",
    "ipc_position",
    "axis_crossing",
    "sycophancy_risk",
    "fanfaronade_score",
    "cold_weaver_topics",
    "recommended_H_delta",
    "recurring_minor_elements",
    "trigger_description",
    "recommended_phase",
)
_S2_INTENTION_REQUIRED_TOKENS = (
    "label",
    "confidence",
)
_S2_IPC_POSITION_REQUIRED_TOKENS = (
    "agency",
    "communion",
)
_S2_RECURRING_MINOR_ELEMENT_REQUIRED_TOKENS = (
    "content",
    "type",
    "count",
    "importance",
    "user_reaction",
)
_S2_RECURRING_MINOR_ELEMENT_ENUM_TOKENS = (
    "in_joke",
    "object_callback",
    "ritual",
    "theme",
    "neutral",
    "engaged",
    "amused",
    "callback",
)
_S2_DANGER_LEVEL_REQUIRED_TOKENS = ("0", "1", "2", "3")
_S2_RECOMMENDED_PHASE_ENUM_TOKENS = PERSONA_PHASES
_S2_RECOMMENDED_PHASE_REQUIRED_TOKENS = ("null",)
_S2_CORRELATION_REQUIRED_TOKENS = ("null", "hypothesis", "confidence")
_S2_INTENTION_CONTRACT_WINDOW_PARTS = 24
_S2_IPC_POSITION_CONTRACT_WINDOW_PARTS = 24
_S2_RECURRING_MINOR_ELEMENTS_CONTRACT_WINDOW_PARTS = 48
_S2_DANGER_LEVEL_CONTRACT_WINDOW_PARTS = 24
_S2_CORRELATION_CONTRACT_WINDOW_PARTS = 24
_S2_RECOMMENDED_PHASE_CONTRACT_WINDOW_PARTS = 24
_S2_RECOMMENDED_H_DELTA_CONTRACT_WINDOW_CHARS = 160


def _read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalize_contract_token(value: str) -> tuple[str, ...]:
    return normalize_contract_key_parts(value)


def _contains_contract_token_parts(
    content_parts: tuple[str, ...],
    token_parts: tuple[str, ...],
) -> bool:
    window = len(token_parts)
    return any(
        tuple(content_parts[index:index + window]) == token_parts
        for index in range(len(content_parts) - window + 1)
    )


def _find_contract_token_positions(
    content_parts: tuple[str, ...],
    token_parts: tuple[str, ...],
) -> list[int]:
    window = len(token_parts)
    return [
        index
        for index in range(len(content_parts) - window + 1)
        if tuple(content_parts[index:index + window]) == token_parts
    ]


def _missing_grouped_contract_tokens(
    content_parts: tuple[str, ...],
    anchor_parts: tuple[str, ...],
    required_tokens: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    search_window_parts: int | None = None,
) -> list[str]:
    if not anchor_parts:
        return []

    anchor_positions = _find_contract_token_positions(content_parts, anchor_parts)
    if not anchor_positions:
        return [token for token, _token_parts in required_tokens]

    best_missing = [token for token, _token_parts in required_tokens]
    for anchor_position in anchor_positions:
        trailing_parts = content_parts[anchor_position:]
        if search_window_parts is not None:
            trailing_parts = trailing_parts[:search_window_parts]
        missing = [
            token
            for token, token_parts in required_tokens
            if token_parts and not _contains_contract_token_parts(trailing_parts, token_parts)
        ]
        if not missing:
            return []
        if len(missing) < len(best_missing):
            best_missing = missing
    return best_missing


_S2_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_REQUIRED_TOKENS
)
_S2_INTENTION_ANCHOR_PARTS = _normalize_contract_token("intention")
_S2_INTENTION_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_INTENTION_REQUIRED_TOKENS
)
_S2_IPC_POSITION_ANCHOR_PARTS = _normalize_contract_token("ipc_position")
_S2_IPC_POSITION_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_IPC_POSITION_REQUIRED_TOKENS
)
_S2_RECURRING_MINOR_ELEMENTS_ANCHOR_PARTS = _normalize_contract_token(
    "recurring_minor_elements"
)
_S2_RECURRING_MINOR_ELEMENT_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_RECURRING_MINOR_ELEMENT_REQUIRED_TOKENS
)
_S2_RECURRING_MINOR_ELEMENT_ENUM_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_RECURRING_MINOR_ELEMENT_ENUM_TOKENS
)
_S2_DANGER_LEVEL_ANCHOR_PARTS = _normalize_contract_token("danger_level")
_S2_DANGER_LEVEL_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_DANGER_LEVEL_REQUIRED_TOKENS
)
_S2_CORRELATION_ANCHOR_PARTS = _normalize_contract_token("correlation")
_S2_CORRELATION_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_CORRELATION_REQUIRED_TOKENS
)
_S2_RECOMMENDED_H_DELTA_ANCHOR_PATTERN = re.compile(
    r"recommended[\W_]*h[\W_]*delta",
    re.IGNORECASE,
)
_S2_RECOMMENDED_H_DELTA_REQUIRED_PATTERNS = (
    ("-0.5", re.compile(r"[-\u2212\u2010-\u2015]\s*0\.5")),
    ("+0.5", re.compile(r"(?<![-\u2212\u2010-\u2015])\+?\s*0\.5")),
)
_S2_RECOMMENDED_PHASE_ANCHOR_PARTS = _normalize_contract_token("recommended_phase")
_S2_RECOMMENDED_PHASE_ENUM_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_RECOMMENDED_PHASE_ENUM_TOKENS
)
_S2_RECOMMENDED_PHASE_REQUIRED_TOKEN_PARTS = tuple(
    (token, _normalize_contract_token(token))
    for token in _S2_RECOMMENDED_PHASE_REQUIRED_TOKENS
)
_S2_GROUPED_CONTRACT_RULES = (
    (
        _S2_INTENTION_ANCHOR_PARTS,
        _S2_INTENTION_REQUIRED_TOKEN_PARTS,
        _S2_INTENTION_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_IPC_POSITION_ANCHOR_PARTS,
        _S2_IPC_POSITION_REQUIRED_TOKEN_PARTS,
        _S2_IPC_POSITION_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_RECURRING_MINOR_ELEMENTS_ANCHOR_PARTS,
        _S2_RECURRING_MINOR_ELEMENT_REQUIRED_TOKEN_PARTS,
        _S2_RECURRING_MINOR_ELEMENTS_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_RECURRING_MINOR_ELEMENTS_ANCHOR_PARTS,
        _S2_RECURRING_MINOR_ELEMENT_ENUM_TOKEN_PARTS,
        _S2_RECURRING_MINOR_ELEMENTS_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_DANGER_LEVEL_ANCHOR_PARTS,
        _S2_DANGER_LEVEL_REQUIRED_TOKEN_PARTS,
        _S2_DANGER_LEVEL_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_CORRELATION_ANCHOR_PARTS,
        _S2_CORRELATION_REQUIRED_TOKEN_PARTS,
        _S2_CORRELATION_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_RECOMMENDED_PHASE_ANCHOR_PARTS,
        _S2_RECOMMENDED_PHASE_REQUIRED_TOKEN_PARTS,
        _S2_RECOMMENDED_PHASE_CONTRACT_WINDOW_PARTS,
    ),
    (
        _S2_RECOMMENDED_PHASE_ANCHOR_PARTS,
        _S2_RECOMMENDED_PHASE_ENUM_TOKEN_PARTS,
        _S2_RECOMMENDED_PHASE_CONTRACT_WINDOW_PARTS,
    ),
)


def _collect_grouped_contract_missing_tokens(
    content_parts: tuple[str, ...],
    grouped_rules: tuple[
        tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...], int | None],
        ...,
    ],
) -> list[str]:
    missing: list[str] = []
    seen: set[str] = set()
    for anchor_parts, required_tokens, search_window_parts in grouped_rules:
        for token in _missing_grouped_contract_tokens(
            content_parts,
            anchor_parts,
            required_tokens,
            search_window_parts=search_window_parts,
        ):
            if token in seen:
                continue
            seen.add(token)
            missing.append(token)
    return missing


def _missing_local_literal_tokens(
    content: str,
    anchor_pattern: re.Pattern[str],
    required_patterns: tuple[tuple[str, re.Pattern[str]], ...],
    *,
    search_window_chars: int,
) -> list[str]:
    anchor_matches = list(anchor_pattern.finditer(content))
    if not anchor_matches:
        return [token for token, _pattern in required_patterns]

    best_missing = [token for token, _pattern in required_patterns]
    for anchor_match in anchor_matches:
        trailing = content[anchor_match.start():anchor_match.start() + search_window_chars]
        missing = [
            token
            for token, pattern in required_patterns
            if pattern.search(trailing) is None
        ]
        if not missing:
            return []
        if len(missing) < len(best_missing):
            best_missing = missing
    return best_missing


def _validate_prompt_content(path: Path, content: str) -> None:
    if not content.strip():
        raise ValueError(f"Prompt file is empty: {path.name}")

    if path == S2_SYSTEM_PROMPT_PATH:
        content_parts = _normalize_contract_token(content)
        missing = [
            token
            for token, token_parts in _S2_REQUIRED_TOKEN_PARTS
            if token_parts and not _contains_contract_token_parts(content_parts, token_parts)
        ]
        missing.extend(
            token
            for token in _collect_grouped_contract_missing_tokens(
                content_parts,
                _S2_GROUPED_CONTRACT_RULES,
            )
            if token not in missing
        )
        missing.extend(
            token
            for token in _missing_local_literal_tokens(
                content,
                _S2_RECOMMENDED_H_DELTA_ANCHOR_PATTERN,
                _S2_RECOMMENDED_H_DELTA_REQUIRED_PATTERNS,
                search_window_chars=_S2_RECOMMENDED_H_DELTA_CONTRACT_WINDOW_CHARS,
            )
            if token not in missing
        )
        if missing:
            raise ValueError(
                f"Invalid S2 prompt {path.name}: missing required contract token(s): "
                f"{', '.join(missing)}"
            )


@lru_cache(maxsize=None)
def _get_prompt(path: Path) -> str:
    content = _read_prompt(path)
    _validate_prompt_content(path, content)
    return content


def clear_prompt_cache() -> None:
    _get_prompt.cache_clear()


def validate_prompt_files() -> None:
    missing = [path for path in (
        S1_SYSTEM_PROMPT_PATH,
        S2_SYSTEM_PROMPT_PATH,
        VISION_SYSTEM_PROMPT_PATH,
    ) if not path.exists()]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise FileNotFoundError(f"Missing prompt file(s): {names}")

    clear_prompt_cache()
    for path in (S1_SYSTEM_PROMPT_PATH, S2_SYSTEM_PROMPT_PATH, VISION_SYSTEM_PROMPT_PATH):
        _get_prompt(path)


def get_s1_prompt() -> str:
    return _get_prompt(S1_SYSTEM_PROMPT_PATH)


def get_s2_prompt() -> str:
    return _get_prompt(S2_SYSTEM_PROMPT_PATH)


def get_vision_prompt() -> str:
    return _get_prompt(VISION_SYSTEM_PROMPT_PATH)
