import json
import tiktoken
from openai import AsyncOpenAI
from typing import Any

from .base import BaseLLMClient

class OpenAIClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            
        self.client = AsyncOpenAI(**kwargs)
        self.model = model
        
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[str | None, list[dict] | None]:
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            # Convert generic tools schema directly to OpenAI format
            # Our generic tool schema matches OpenAI's almost exactly
            kwargs["tools"] = tools
            
        response = await self.client.chat.completions.create(**kwargs)
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
