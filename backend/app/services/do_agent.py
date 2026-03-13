from __future__ import annotations

import json
import os
from typing import Any, Literal, TypedDict

import httpx


class AgentMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


# Maps case_id slug → env-var prefix so each case can have its own DO agent.
# Falls back to the generic DO_AGENT_ENDPOINT / DO_AGENT_ACCESS_KEY if a
# case-specific pair is not configured.
#
# Case slugs must match the keys used in cases.py.
_CASE_ENV_PREFIXES: dict[str, str] = {
    "zodiac-killer": "DO_AGENT_ZODIAC",
    "aarushi-talwar": "DO_AGENT_AARUSHI",
    "oj-simpson": "DO_AGENT_OJ",
}


class DOAgentClient:
    def __init__(self, case_id: str | None = None) -> None:
        # Try case-specific env vars first, then fall back to generic ones.
        prefix = _CASE_ENV_PREFIXES.get(case_id or "", "") if case_id else ""

        endpoint = ""
        access_key = ""

        if prefix:
            endpoint = (os.getenv(f"{prefix}_ENDPOINT") or "").strip().rstrip("/")
            access_key = (os.getenv(f"{prefix}_ACCESS_KEY") or "").strip()

        # Fall back to generic vars
        if not endpoint:
            endpoint = (os.getenv("DO_AGENT_ENDPOINT") or "").strip().rstrip("/")
        if not access_key:
            access_key = (os.getenv("DO_AGENT_ACCESS_KEY") or "").strip()

        if not endpoint or not access_key:
            missing = []
            if not endpoint:
                missing.append("DO_AGENT_ENDPOINT (or case-specific variant)")
            if not access_key:
                missing.append("DO_AGENT_ACCESS_KEY (or case-specific variant)")
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
    def _repair_and_parse(text: str) -> Any:
        """
        Primary JSON parser: uses json_repair to fix all common LLM JSON issues
        (trailing commas, missing commas, single quotes, unescaped chars, markdown fences).
        Falls back to stdlib json if json_repair is not installed.
        """
        import re
        t = text.strip()
        # Strip markdown code fences
        t = re.sub(r"^```(?:json)?\s*\n?", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\n?```\s*$", "", t)
        t = t.strip()

        try:
            from json_repair import repair_json
            result = repair_json(t, return_objects=True)
            return result
        except ImportError:
            # Fallback: stdlib with basic trailing-comma fix
            t = re.sub(r",\s*([\}\]])", r"\1", t)
            return json.loads(t)

    @staticmethod
    def extract_json_object(response_text: str) -> dict[str, Any]:
        """
        Aggressively extract and repair a JSON object from agent output.
        """
        import logging
        import re
        text = response_text.strip()

        # Find the outermost { ... }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        try:
            result = DOAgentClient._repair_and_parse(text)
            if not isinstance(result, dict):
                raise ValueError(f"expected_dict_got_{type(result).__name__}")
            return result
        except Exception as e:
            logging.error("JSON object parse failed. Raw:\n%s", response_text[:2000])
            raise ValueError(str(e)) from e

    @staticmethod
    def extract_json_array(response_text: str) -> list[Any]:
        """
        Aggressively extract and repair a JSON array from agent output.
        """
        import logging
        text = response_text.strip()

        # Find the outermost [ ... ]
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        elif "{" in text:
            # Agent returned an object — let caller handle it
            raise ValueError("no_json_array_found")

        try:
            result = DOAgentClient._repair_and_parse(text)
            if not isinstance(result, list):
                raise ValueError(f"expected_list_got_{type(result).__name__}")
            return result
        except Exception as e:
            logging.error("JSON array parse failed. Raw:\n%s", response_text[:2000])
            raise ValueError(str(e)) from e
