import json
from anthropic import AsyncAnthropic

from .base import BaseLLMClient

class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        system_prompt = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg.get("content", "") + "\n"
            else:
                content = msg.get("content")
                if isinstance(content, str):
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": content
                    })
                elif isinstance(content, list):
                    parts = []
                    for item in content:
                        if item.get("type") == "text":
                            parts.append({"type": "text", "text": item["text"]})
                        elif item.get("type") == "image_url":
                            b64_data = item["image_url"]["url"].split("base64,")[-1]
                            mime_type = item["image_url"]["url"].split(";")[0].split(":")[1]
                            parts.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": mime_type,
                                    "data": b64_data,
                                }
                            })
                    anthropic_messages.append({
                        "role": msg["role"],
                        "content": parts
                    })
                    
        return system_prompt.strip(), anthropic_messages

    def _convert_tools(self, tools: list[dict]) -> list[dict]:
        if not tools:
            return None
            
        anth_tools = []
        for t in tools:
            func = t["function"]
            anth_tools.append({
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}})
            })
        return anth_tools

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[str | None, list[dict] | None]:
        system_prompt, anthropic_messages = self._convert_messages(messages)
        anthropic_tools = self._convert_tools(tools)
        
        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if anthropic_tools:
            kwargs["tools"] = anthropic_tools
            
        response = await self.client.messages.create(**kwargs)
        
        content = ""
        tool_calls = None
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input)
                    }
                })
                
        return content if content else None, tool_calls

    def count_tokens(self, messages: list[dict]) -> int:
        system, msg_list = self._convert_messages(messages)
        # Using anthropic counter locally if available, or rough estimate
        total_text = system
        for m in msg_list:
            if isinstance(m["content"], str):
                total_text += m["content"]
            else:
                for part in m["content"]:
                    if part["type"] == "text":
                        total_text += part["text"]
                        
        # rough estimate: 4 chars per token
        return len(total_text) // 4
