"""Explicit file-queue bridge provider for Codex-assisted LDR runs."""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from ..base import BaseLLMProvider


SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token"}


class CodexBridgeTimeout(TimeoutError):
    """Raised when the bridge responder does not write a response in time."""


def _setting_value(settings_snapshot: Any, key: str, default: Any = None) -> Any:
    if not isinstance(settings_snapshot, dict) or key not in settings_snapshot:
        return default
    value = settings_snapshot[key]
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in SECRET_KEYS or any(secret in key.lower() for secret in SECRET_KEYS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    return value


def message_role(message: BaseMessage) -> str:
    kind = getattr(message, "type", "")
    if kind == "system":
        return "system"
    if kind in {"ai", "assistant"}:
        return "assistant"
    if kind in {"human", "user"}:
        return "user"
    return kind or "user"


class CodexBridgeChatModel(BaseChatModel):
    """LangChain chat model that exchanges JSON files with a Codex responder."""

    bridge_dir: str
    model: str = "gpt-5.5"
    temperature: float = 0.7
    timeout_seconds: float = 300.0
    poll_interval_seconds: float = 1.0
    max_prompt_chars: int = 200_000
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def _llm_type(self) -> str:
        return "codex_bridge"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "bridge_dir": self.bridge_dir,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def request_dir(self) -> Path:
        return Path(self.bridge_dir).expanduser() / "requests"

    @property
    def response_dir(self) -> Path:
        return Path(self.bridge_dir).expanduser() / "responses"

    def _serialize_messages(self, messages: list[BaseMessage]) -> list[dict[str, str]]:
        serialized: list[dict[str, str]] = []
        remaining = max(0, int(self.max_prompt_chars))
        for message in messages:
            content = message.content
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            if remaining <= 0:
                content = ""
            elif len(content) > remaining:
                content = content[:remaining]
            remaining -= len(content)
            serialized.append({"role": message_role(message), "content": content})
        return serialized

    def _write_request(self, messages: list[BaseMessage], **kwargs: Any) -> str:
        self.request_dir.mkdir(parents=True, exist_ok=True)
        self.response_dir.mkdir(parents=True, exist_ok=True)
        request_id = str(uuid.uuid4())
        metadata = {**self.metadata, **kwargs.get("metadata", {})}
        payload = {
            "id": request_id,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "messages": self._serialize_messages(messages),
            "model": self.model,
            "temperature": self.temperature,
            "metadata": redact_secrets(metadata),
        }
        request_path = self.request_dir / f"{request_id}.json"
        request_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        return request_id

    def _wait_for_response(self, request_id: str) -> tuple[str, dict[str, Any]]:
        response_path = self.response_dir / f"{request_id}.json"
        deadline = time.monotonic() + float(self.timeout_seconds)
        while time.monotonic() <= deadline:
            if response_path.exists():
                payload = json.loads(response_path.read_text(encoding="utf-8"))
                if payload.get("id") not in {None, request_id}:
                    raise ValueError(
                        f"Codex bridge response id mismatch: expected {request_id}, got {payload.get('id')}"
                    )
                content = payload.get("content")
                if not isinstance(content, str):
                    raise ValueError(
                        f"Codex bridge response {request_id} must contain string content"
                    )
                usage = payload.get("usage") or {}
                return content, usage if isinstance(usage, dict) else {}
            time.sleep(float(self.poll_interval_seconds))
        raise CodexBridgeTimeout(
            f"Timed out waiting for Codex bridge response {request_id} in {self.response_dir}"
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        request_id = self._write_request(messages, stop=stop, **kwargs)
        content, usage = self._wait_for_response(request_id)
        generation = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(
            generations=[generation],
            llm_output={"request_id": request_id, "usage": usage},
        )


class CodexBridgeProvider(BaseLLMProvider):
    """Experimental opt-in provider that routes LDR prompts through Codex."""

    provider_name = "Codex Bridge"
    provider_key = "CODEX_BRIDGE"
    company_name = "OpenAI Codex"
    is_cloud = False

    @classmethod
    def is_discoverable(cls) -> bool:
        return os.environ.get("LDR_ENABLE_CODEX_BRIDGE") == "1"

    @classmethod
    def is_available(cls, settings_snapshot=None) -> bool:
        return cls.is_discoverable()

    @classmethod
    def requires_auth_for_models(cls) -> bool:
        return False

    @classmethod
    def create_llm(cls, model_name=None, temperature=0.7, **kwargs):
        if not cls.is_discoverable():
            raise ValueError(
                "Codex bridge is experimental and disabled. Set "
                "LDR_ENABLE_CODEX_BRIDGE=1 and run a responder process before "
                "selecting provider 'codex_bridge'."
            )
        if not model_name or not str(model_name).strip():
            raise ValueError("Codex bridge requires an explicit model name.")

        settings_snapshot = kwargs.get("settings_snapshot")
        bridge_dir = (
            kwargs.get("bridge_dir")
            or _setting_value(settings_snapshot, "llm.codex_bridge.bridge_dir")
            or os.environ.get("LDR_CODEX_BRIDGE_DIR")
            or ".codex_bridge"
        )
        timeout_seconds = float(
            kwargs.get("timeout_seconds")
            or _setting_value(settings_snapshot, "llm.codex_bridge.timeout_seconds", 300)
        )
        poll_interval_seconds = float(
            kwargs.get("poll_interval_seconds")
            or _setting_value(settings_snapshot, "llm.codex_bridge.poll_interval_seconds", 1)
        )
        max_prompt_chars = int(
            kwargs.get("max_prompt_chars")
            or _setting_value(settings_snapshot, "llm.codex_bridge.max_prompt_chars", 200_000)
        )
        metadata = {
            "provider": "codex_bridge",
            "research_id": kwargs.get("research_id"),
        }
        return CodexBridgeChatModel(
            bridge_dir=str(bridge_dir),
            model=str(model_name).strip(),
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            max_prompt_chars=max_prompt_chars,
            metadata=metadata,
        )
