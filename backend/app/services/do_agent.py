from __future__ import annotations

import json
import os
from typing import Any, Literal, TypedDict

import httpx


class AgentMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class DOAgentClient:
    def __init__(self) -> None:
        endpoint = (os.getenv("DO_AGENT_ENDPOINT") or "").strip().rstrip("/")
        access_key = (os.getenv("DO_AGENT_ACCESS_KEY") or "").strip()

        if not endpoint or not access_key:
            missing = []
            if not endpoint:
                missing.append("DO_AGENT_ENDPOINT")
            if not access_key:
                missing.append("DO_AGENT_ACCESS_KEY")
            raise RuntimeError(f"missing_gradient_agent_config:{','.join(missing)}")

        self._base_url = endpoint + "/api/v1"
        self._access_key = access_key

    async def chat_completions(
        self,
        *,
        messages: list[AgentMessage],
        include_retrieval_info: bool = True,
        include_guardrails_info: bool = True,
        include_functions_info: bool = False,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": "n/a",
            "messages": messages,
            "stream": False,
            "include_retrieval_info": include_retrieval_info,
            "include_guardrails_info": include_guardrails_info,
            "include_functions_info": include_functions_info,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._access_key}"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def extract_content(response_json: dict[str, Any]) -> str:
        try:
            return response_json["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise RuntimeError("unexpected_agent_response_shape") from e

    @staticmethod
    def extract_json_object(response_text: str) -> dict[str, Any]:
        """
        Agents sometimes wrap JSON in prose; we aggressively extract the first JSON object.
        """
        text = response_text.strip()
        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("no_json_object_found")
        return json.loads(text[start : end + 1])

