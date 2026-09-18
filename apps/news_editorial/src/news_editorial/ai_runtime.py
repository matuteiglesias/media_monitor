"""Provider-neutral structured AI execution primitives.

This module is deliberately editorial-agnostic.  It owns bounded concurrency,
per-item retry/error isolation, and execution provenance.  Provider adapters
implement StructuredAIBackend; editorial workflows consume StructuredAINode.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol, Sequence

from pydantic import BaseModel


@dataclass(frozen=True)
class AIWorkItem:
    work_id: str
    task: str
    instructions: str
    prompt: str
    response_model: type[BaseModel]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BackendResponse:
    value: BaseModel | dict[str, Any]
    raw_text: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    provider_response_id: str | None = None


class StructuredAIBackend(Protocol):
    backend_name: str
    provider_name: str
    model_name: str

    async def invoke(self, item: AIWorkItem) -> BackendResponse:
        """Execute one structured model request."""


@dataclass(frozen=True)
class AIWorkResult:
    work_id: str
    task: str
    status: str
    backend: str
    provider: str
    model: str
    attempts: int
    duration_ms: int
    output: dict[str, Any] | None
    usage: dict[str, Any]
    provider_response_id: str | None
    raw_text: str
    error_type: str | None
    error_message: str | None
    metadata: dict[str, Any]

    @property
    def ok(self) -> bool:
        return self.status == "ok"


class StructuredAINode:
    """A bounded-concurrency DAG node over one structured AI backend."""

    def __init__(
        self,
        backend: StructuredAIBackend,
        *,
        concurrency: int = 4,
        max_attempts: int = 2,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.backend = backend
        self.concurrency = concurrency
        self.max_attempts = max_attempts

    async def run_one(self, item: AIWorkItem) -> AIWorkResult:
        started = perf_counter()
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = await self.backend.invoke(item)
                value = response.value
                if isinstance(value, BaseModel):
                    output = value.model_dump(mode="json")
                elif isinstance(value, dict):
                    output = value
                else:
                    raise TypeError(
                        f"backend returned unsupported structured value {type(value).__name__}"
                    )
                # Re-validate at our boundary so provider adapters cannot silently
                # downgrade structured-output guarantees.
                validated = item.response_model.model_validate(output)
                return AIWorkResult(
                    work_id=item.work_id,
                    task=item.task,
                    status="ok",
                    backend=self.backend.backend_name,
                    provider=self.backend.provider_name,
                    model=self.backend.model_name,
                    attempts=attempt,
                    duration_ms=max(0, int((perf_counter() - started) * 1000)),
                    output=validated.model_dump(mode="json"),
                    usage=dict(response.usage or {}),
                    provider_response_id=response.provider_response_id,
                    raw_text=response.raw_text,
                    error_type=None,
                    error_message=None,
                    metadata=dict(item.metadata),
                )
            except Exception as exc:  # provider/validation failure is item-scoped
                last_error = exc
                if attempt < self.max_attempts:
                    await asyncio.sleep(0)

        assert last_error is not None
        return AIWorkResult(
            work_id=item.work_id,
            task=item.task,
            status="failed",
            backend=self.backend.backend_name,
            provider=self.backend.provider_name,
            model=self.backend.model_name,
            attempts=self.max_attempts,
            duration_ms=max(0, int((perf_counter() - started) * 1000)),
            output=None,
            usage={},
            provider_response_id=None,
            raw_text="",
            error_type=type(last_error).__name__,
            error_message=str(last_error),
            metadata=dict(item.metadata),
        )

    async def run_many(self, items: Sequence[AIWorkItem]) -> list[AIWorkResult]:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def bounded(item: AIWorkItem) -> AIWorkResult:
            async with semaphore:
                return await self.run_one(item)

        return list(await asyncio.gather(*(bounded(item) for item in items)))
