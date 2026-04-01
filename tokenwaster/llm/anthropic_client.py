import json
from anthropic import AsyncAnthropic

from .base import BaseLLMClient

class AnthropicClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    @staticmethod
    def _parse_tool_args(raw_args) -> dict:
        if isinstance(raw_args, dict):
            return raw_args
        if isinstance(raw_args, str):
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                return {"raw": raw_args}
        return {}

    @staticmethod
    def _to_text_blocks(content) -> list[dict]:
        blocks = []
        if isinstance(content, str):
            blocks.append({"type": "text", "text": content})
        elif isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    blocks.append({"type": "text", "text": item["text"]})
                elif item.get("type") == "image_url":
                    b64_data = item["image_url"]["url"].split("base64,")[-1]
                    mime_type = item["image_url"]["url"].split(";")[0].split(":")[1]
                    blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_data,
                        },
                    })
        return blocks

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        system_prompt = ""
        anthropic_messages = []
        
        for msg in messages:
            role = msg.get("role")
            if role == "system":
                system_prompt += msg.get("content", "") + "\n"
                continue

            # Convert OpenAI-style assistant tool calls to Anthropic tool_use blocks.
            if role == "assistant":
                blocks = self._to_text_blocks(msg.get("content"))
                for tc in msg.get("tool_calls", []) or []:
                    if not isinstance(tc, dict):
                        continue
                    func = tc.get("function") or {}
                    name = func.get("name")
                    if not name:
                        continue
                    blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", f"call_{name}"),
                        "name": name,
                        "input": self._parse_tool_args(func.get("arguments", "{}")),
                    })
                if blocks:
                    anthropic_messages.append({"role": "assistant", "content": blocks})
                continue

            # Convert OpenAI-style tool result messages to Anthropic user tool_result blocks.
            if role == "tool":
                tool_id = msg.get("tool_call_id")
                tool_content = msg.get("content", "")
                blocks = []
                if tool_id:
                    blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": str(tool_content),
                    })
                else:
                    # Fallback for malformed history without tool_call_id.
                    blocks.append({"type": "text", "text": f"[tool_result] {tool_content}"})
                anthropic_messages.append({"role": "user", "content": blocks})
                continue

            # user/unknown roles are mapped as user.
            blocks = self._to_text_blocks(msg.get("content"))
            if blocks:
                anthropic_messages.append({"role": "user", "content": blocks})
                    
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
            content = m.get("content")
            if isinstance(content, str):
                total_text += content
                continue
            for part in content or []:
                part_type = part.get("type")
                if part_type == "text":
                    total_text += part.get("text", "")
                elif part_type == "tool_use":
                    total_text += part.get("name", "") + json.dumps(part.get("input", {}), ensure_ascii=False)
                elif part_type == "tool_result":
                    total_text += str(part.get("content", ""))
                        
        # rough estimate: 4 chars per token
        return len(total_text) // 4
