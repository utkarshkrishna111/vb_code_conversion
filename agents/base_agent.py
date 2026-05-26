from abc import ABC
from typing import Optional
import json
import os

import litellm
from litellm import ModelResponse

from config import Config
from utils.logger import get_logger

# Suppress LiteLLM's verbose startup banner
litellm.suppress_debug_info = True

# Inject whichever API key is active so LiteLLM can find it
os.environ.setdefault("ANTHROPIC_API_KEY", Config.ANTHROPIC_API_KEY)
os.environ.setdefault("OPENAI_API_KEY",    Config.OPENAI_API_KEY)
os.environ.setdefault("GEMINI_API_KEY",    Config.GEMINI_API_KEY)


class BaseAgent(ABC):
    """Abstract base for every spoke agent in the pipeline."""

    def __init__(self, name: str, model: Optional[str] = None):
        self.name   = name
        self.model  = model or Config.AGENT_MODEL
        self.logger = get_logger(name)

    # ── LLM helpers ──────────────────────────────────────────────────────────

    def _call_llm(
        self,
        system: str,
        messages: list[dict],
        max_tokens: int = 4096,
        tools: Optional[list] = None,
    ) -> ModelResponse:
        """Single LLM call — works with Anthropic, OpenAI, and Gemini."""
        all_messages = [{"role": "system", "content": system}] + messages

        kwargs: dict = {
            "model":      self.model,
            "messages":   all_messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        response = litellm.completion(**kwargs)
        usage = response.usage
        self.logger.debug(
            f"tokens — input: {usage.prompt_tokens}, output: {usage.completion_tokens}"
        )
        return response

    def _text(self, response: ModelResponse) -> str:
        """Extract the text content from a LiteLLM response."""
        return response.choices[0].message.content or ""

    def _parse_json(self, response: ModelResponse) -> dict:
        """Extract and parse JSON from a response, stripping markdown fences."""
        raw = self._text(response).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
