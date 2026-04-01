import json
import asyncio
import random
import re
import time
import tiktoken
from openai import AsyncOpenAI
from typing import Any

from .base import BaseLLMClient

class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None, max_rpm: int | None = None):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            
        self.client = AsyncOpenAI(**kwargs)
        self.model = model
        self.max_rpm = max_rpm if isinstance(max_rpm, int) and max_rpm > 0 else None
        self.min_request_interval = (60.0 / self.max_rpm) if self.max_rpm else 0.0
        self._last_request_time = 0.0
        self.max_rate_limit_retries = 6
        
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    @staticmethod
    def _stringify_content(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            texts = []
            for item in value:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(str(item.get("text", "")))
            return "\n".join(t for t in texts if t)
        return str(value)

    def _sanitize_messages(self, messages: list[dict], mode: str) -> list[dict]:
        sanitized = []
        for msg in messages:
            role = msg.get("role")
            new_msg = dict(msg)

            if mode in {"string_content", "compat"} and new_msg.get("content") is None:
                new_msg["content"] = ""

            if mode == "compat" and role == "assistant" and isinstance(new_msg.get("tool_calls"), list):
                tool_names = []
                for tc in new_msg.get("tool_calls", []):
                    if isinstance(tc, dict):
                        fn = tc.get("function") or {}
                        if isinstance(fn, dict):
                            name = fn.get("name")
                            if name:
                                tool_names.append(str(name))
                base_content = self._stringify_content(new_msg.get("content"))
                call_summary = f"[Tool calls: {', '.join(tool_names)}]" if tool_names else "[Tool calls]"
                new_msg["content"] = f"{base_content}\n{call_summary}".strip()
                new_msg.pop("tool_calls", None)

            if mode == "compat" and role == "tool":
                content = self._stringify_content(new_msg.get("content"))
                tool_name = new_msg.get("name", "tool")
                new_msg = {
                    "role": "user",
                    "content": f"[Tool:{tool_name}] {content}",
                }

            sanitized.append(new_msg)
        return sanitized

    @staticmethod
    def _should_retry_without_tools(error_text: str) -> bool:
        hints = [
            "tools",
            "tool_calls",
            "function call",
            "function calling",
            "functions are not supported",
            "unsupported parameter",
        ]
        lowered = error_text.lower()
        return any(h in lowered for h in hints)

    @staticmethod
    def _needs_string_content(error_text: str) -> bool:
        lowered = error_text.lower()
        return "content" in lowered and ("string" in lowered or "null" in lowered or "none" in lowered)

    @staticmethod
    def _tool_role_unsupported(error_text: str) -> bool:
        lowered = error_text.lower()
        return "role" in lowered and "tool" in lowered and ("unsupported" in lowered or "invalid" in lowered)

    @staticmethod
    def _is_rate_limit_error(error_text: str) -> bool:
        lowered = error_text.lower()
        return "429" in lowered or "rate limit" in lowered or "rate_limit" in lowered or "rpm" in lowered

    @staticmethod
    def _extract_retry_after_seconds(error_text: str) -> float | None:
        m = re.search(r"after\s+(\d+(?:\.\d+)?)\s*seconds?", error_text, re.IGNORECASE)
        if not m:
            return None
        try:
            return float(m.group(1))
        except (ValueError, TypeError):
            return None

    async def _wait_for_proactive_rate_limit(self) -> None:
        if self.min_request_interval <= 0:
            return
        now = time.monotonic()
        wait_for = self.min_request_interval - (now - self._last_request_time)
        if wait_for > 0:
            await asyncio.sleep(wait_for)
        self._last_request_time = time.monotonic()

    async def _create_with_retry(self, kwargs: dict) -> Any:
        last_error = None
        for retry_idx in range(self.max_rate_limit_retries + 1):
            await self._wait_for_proactive_rate_limit()
            try:
                return await self.client.chat.completions.create(**kwargs)
            except Exception as e:
                last_error = e
                err_text = str(e)
                if not self._is_rate_limit_error(err_text) or retry_idx >= self.max_rate_limit_retries:
                    raise
                retry_after = self._extract_retry_after_seconds(err_text)
                backoff = retry_after if retry_after is not None else min(2 ** retry_idx, 10)
                await asyncio.sleep(backoff + random.uniform(0, 0.25))
        raise last_error

    @staticmethod
    def _reasoning_content_missing_for_tool_calls(error_text: str) -> bool:
        lowered = error_text.lower()
        return (
            "reasoning_content" in lowered
            and "assistant tool call message" in lowered
            and ("missing" in lowered or "required" in lowered)
        )

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[str | None, list[dict] | None]:
        attempts = [
            {"messages": messages, "tools": tools},
        ]

        last_error = None
        for attempt in attempts:
            kwargs = {"model": self.model, "messages": attempt["messages"]}
            if attempt["tools"]:
                # Convert generic tools schema directly to OpenAI format
                # Our generic tool schema matches OpenAI's almost exactly
                kwargs["tools"] = attempt["tools"]
            try:
                response = await self._create_with_retry(kwargs)
                break
            except Exception as e:
                last_error = e
                err_text = str(e)

                extra_attempts = []
                if self._needs_string_content(err_text):
                    extra_attempts.append({
                        "messages": self._sanitize_messages(messages, mode="string_content"),
                        "tools": tools,
                    })
                if self._tool_role_unsupported(err_text):
                    extra_attempts.append({
                        "messages": self._sanitize_messages(messages, mode="compat"),
                        "tools": tools,
                    })
                if self._reasoning_content_missing_for_tool_calls(err_text):
                    extra_attempts.append({
                        "messages": self._sanitize_messages(messages, mode="compat"),
                        "tools": tools,
                    })
                if tools and self._should_retry_without_tools(err_text):
                    extra_attempts.append({
                        "messages": self._sanitize_messages(messages, mode="compat"),
                        "tools": None,
                    })

                # Deduplicate attempts by simple JSON signature to avoid loops.
                seen = {
                    json.dumps({"m": a["messages"], "t": a["tools"]}, ensure_ascii=False, default=str)
                    for a in attempts
                }
                for candidate in extra_attempts:
                    sig = json.dumps({"m": candidate["messages"], "t": candidate["tools"]}, ensure_ascii=False, default=str)
                    if sig not in seen:
                        attempts.append(candidate)
                        seen.add(sig)
                continue
        else:
            raise last_error

        choice = response.choices[0].message
        
        content = choice.content
        tool_calls = None
        
        if choice.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in choice.tool_calls
            ]
            
        return content, tool_calls

    def count_tokens(self, messages: list[dict]) -> int:
        num_tokens = 0
        for message in messages:
            num_tokens += 3  # every message follows <|start|>{role/name}\n{content}<|end|>\n
            for key, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(self.encoding.encode(value))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get("type") == "text":
                            num_tokens += len(self.encoding.encode(item.get("text", "")))
                        # We ignore image tokens for simple estimation
            num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens
