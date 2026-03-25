from abc import ABC, abstractmethod
from typing import Any

class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[str | None, list[dict] | None]:
        """
        Send a chat completion request.
        Args:
            messages: List of chat messages
            tools: List of tool schemas to provide to the model
        Returns:
            A tuple of (content_string, tool_calls_list).
            If the model returned text, content_string is not None.
            If the model returned tool calls, tool_calls_list is a list of {"id": str, "function": {"name": str, "arguments": str}}.
        """
        pass
    
    @abstractmethod
    def count_tokens(self, messages: list[dict]) -> int:
        """
        Estimate the token count for a list of messages.
        """
        pass
