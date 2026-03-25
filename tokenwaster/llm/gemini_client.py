import json
from google import genai
from google.genai import types

from .base import BaseLLMClient

class GeminiClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _convert_messages(self, messages: list[dict]) -> list[types.Content]:
        # Convert generic standard OpenAI-style messages to Gemini Content
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg["role"] == "system":
                # System instructions are typically passed separately in Gemini SDK,
                # but for simplicity if we must include them in the chat history,
                # Gemini generally recommends setting it as system_instruction in config.
                continue
            
            parts = []
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(types.Part.from_text(content))
            elif isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        parts.append(types.Part.from_text(item["text"]))
                    elif item.get("type") == "image_url":
                        # Simplistic conversion for base64 images
                        b64_data = item["image_url"]["url"].split("base64,")[-1]
                        mime_type = item["image_url"]["url"].split(";")[0].split(":")[1]
                        
                        import base64
                        data = base64.b64decode(b64_data)
                        parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
                        
            gemini_messages.append(types.Content(role=role, parts=parts))
        return gemini_messages

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        if not tools:
            return None
        
        funcs = []
        for t in tools:
            func_def = t["function"]
            # Convert JSON Schema properties to Gemini format
            props = {}
            if "parameters" in func_def and "properties" in func_def["parameters"]:
                for k, v in func_def["parameters"]["properties"].items():
                    props[k] = types.Schema(
                        type=v.get("type", "STRING").upper(),
                        description=v.get("description", "")
                    )
            
            funcs.append(types.FunctionDeclaration(
                name=func_def["name"],
                description=func_def.get("description", ""),
                parameters=types.Schema(
                    type="OBJECT",
                    properties=props,
                    required=func_def.get("parameters", {}).get("required", [])
                )
            ))
            
        return [types.Tool(function_declarations=funcs)]

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[str | None, list[dict] | None]:
        # Extract system prompt if any
        system_content = None
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg.get("content", "")
                break
                
        gemini_messages = self._convert_messages(messages)
        gemini_tools = self._convert_tools(tools)
        
        config = types.GenerateContentConfig()
        if system_content:
            config.system_instruction = system_content
        if gemini_tools:
            config.tools = gemini_tools
            
        # Due to google-genai current async support limitations, we might need to wrap in executor
        # if the actual async client is not fully featured, but standard generates are usually blocking or use asyncio
        # We will use the synchronous generate_content wrapped in asyncio if necessary, but assume sync SDK for now
        # Actually in google-genai SDK `Client()` returns sync, async is `Client().aio`
        
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=gemini_messages,
            config=config,
        )
        
        if not response.candidates:
            return None, None
            
        candidate = response.candidates[0]
        content = ""
        tool_calls = None
        
        for part in candidate.content.parts:
            if part.text:
                content += part.text
            elif part.function_call:
                if tool_calls is None:
                    tool_calls = []
                # convert struct to dict
                args_dict = type(part.function_call.args).to_dict(part.function_call.args) if hasattr(part.function_call.args, "to_dict") else part.function_call.args
                # Convert back to standard OpenAI format for the rest of our app
                tool_calls.append({
                    "id": f"call_{part.function_call.name}",
                    "type": "function",
                    "function": {
                        "name": part.function_call.name,
                        "arguments": json.dumps(args_dict)
                    }
                })
                
        return content if content else None, tool_calls

    def count_tokens(self, messages: list[dict]) -> int:
        gemini_messages = self._convert_messages(messages)
        # We use standard sync to count for simplicity, but it takes network call
        try:
            resp = self.client.models.count_tokens(model=self.model, contents=gemini_messages)
            return resp.total_tokens
        except:
            return 0
