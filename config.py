import os
from dotenv import load_dotenv

load_dotenv()


# Default models per provider — override any of these via .env
_DEFAULTS: dict[str, dict[str, str]] = {
    "anthropic": {
        "agent": "claude-sonnet-4-6",
        "hub":   "claude-opus-4-7",
    },
    "openai": {
        "agent": "gpt-4o",
        "hub":   "gpt-4o",
    },
    "gemini": {
        "agent": "gemini/gemini-1.5-pro",
        "hub":   "gemini/gemini-1.5-pro",
    },
}


class Config:
    # ── LLM provider ──────────────────────────────────────────────────────────
    # Set LLM_PROVIDER to: anthropic | openai | gemini
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic").lower()

    # API keys — only the one matching LLM_PROVIDER needs to be set
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str    = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str    = os.getenv("GEMINI_API_KEY", "")

    # Models — defaults come from the table above; override per-agent in .env
    AGENT_MODEL: str = os.getenv(
        "AGENT_MODEL", _DEFAULTS.get(os.getenv("LLM_PROVIDER", "anthropic").lower(), _DEFAULTS["anthropic"])["agent"]
    )
    HUB_MODEL: str = os.getenv(
        "HUB_MODEL", _DEFAULTS.get(os.getenv("LLM_PROVIDER", "anthropic").lower(), _DEFAULTS["anthropic"])["hub"]
    )

    # ── Pipeline ──────────────────────────────────────────────────────────────
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # ── Qdrant ────────────────────────────────────────────────────────────────
    QDRANT_URL: str        = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str    = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION: str = "java_python_patterns"

    # ── GitHub ────────────────────────────────────────────────────────────────
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO: str  = os.getenv("GITHUB_REPO", "")
