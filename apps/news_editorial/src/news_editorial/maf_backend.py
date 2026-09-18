"""Microsoft Agent Framework provider adapter for structured AI work."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
import os
import re
from typing import Any

from pydantic import BaseModel

from .ai_runtime import AIWorkItem, BackendResponse


def _safe_agent_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return (cleaned or "media_monitor_agent")[:80]


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "model_dump"):
        try:
            mapped = value.model_dump(mode="json")
            return mapped if isinstance(mapped, dict) else {}
        except Exception:
            return {}
    return {}


class MAFOpenAIBackend:
    """Structured OpenAI Responses calls through Microsoft Agent Framework.

    A single OpenAIChatClient is safe to share across concurrent async calls on
    one event loop.  Each invocation creates a fresh Agent so mutable run state
    is never shared between work items.
    """

    backend_name = "microsoft_agent_framework"
    provider_name = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model is required")
        self.model_name = model.strip()
        if client is None:
            from agent_framework.openai import OpenAIChatClient

            client = OpenAIChatClient(
                model=self.model_name,
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
            )
        self.client = client

    async def invoke(self, item: AIWorkItem) -> BackendResponse:
        agent = self.client.as_agent(
            name=_safe_agent_name(f"mm_{item.task}_{item.work_id[-16:]}"),
            instructions=item.instructions,
        )
        response = await agent.run(
            item.prompt,
            options={"response_format": item.response_model},
        )
        value = getattr(response, "value", None)
        if value is None:
            raise ValueError(
                f"MAF response for {item.task} did not contain structured value"
            )
        raw_text = str(getattr(response, "text", "") or "")
        usage = _mapping(getattr(response, "usage", None))
        response_id = (
            getattr(response, "response_id", None)
            or getattr(response, "id", None)
        )
        return BackendResponse(
            value=value,
            raw_text=raw_text,
            usage=usage,
            provider_response_id=str(response_id) if response_id else None,
        )
