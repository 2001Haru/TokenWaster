import json
from typing import Optional, Awaitable, Callable
from rich.console import Console
from .config import Config, get_desktop_path
from .memory import Memory
from .prompts import SYSTEM_PROMPT_TEMPLATE, COMPACT_PROMPT
from .llm.base import BaseLLMClient
from .tools.registry import ToolRegistry
from .tools import read_files, list_files, edit_file, read_picture

class TokenWasterAgent:
    def __init__(self, config: Config, llm_client: BaseLLMClient, console: Console):
        self.config = config
        self.llm_client = llm_client
        self.console = console
        self.memory = Memory(get_desktop_path())
        
        # Setup tools
        self.registry = ToolRegistry()
        self.registry.register(read_files.SCHEMA, read_files.execute)
        self.registry.register(list_files.SCHEMA, list_files.execute)
        self.registry.register(edit_file.SCHEMA, edit_file.execute)
        if self.config.multimodal:
            self.registry.register(read_picture.SCHEMA, lambda p: read_picture.execute(p, True))
            
        self.messages = []
        
        # CLI interjection queue
        self.user_message_queue = []

    def get_system_prompt(self) -> str:
        # Format the system prompt with current state
        read_files_str = "\n".join(f"- {f}" for f in list(self.memory.read_files_set)[:100])
        if not read_files_str:
            read_files_str = "(None yet)"
            
        return SYSTEM_PROMPT_TEMPLATE.format(
            total_tokens=self.memory.total_tokens_used,
            compact_history=self.memory.compact_history or "(No history yet)",
            read_files=read_files_str,
            desktop_comment_path=get_desktop_path()
        )

    def _reset_messages(self, system_content: str):
        self.messages = [{"role": "system", "content": system_content}]

    def add_user_interjection(self, text: str):
        self.user_message_queue.append(text)

    async def _handle_compaction(self):
        self.console.print("\n[bold yellow]⚠️ Reached Context Limit! Compacting memory...[/bold yellow]")
        
        # Inject compaction prompt
        compaction_msg = {"role": "user", "content": COMPACT_PROMPT}
        temp_messages = self.messages + [compaction_msg]
        
        content, _ = await self.llm_client.chat(temp_messages, tools=None)
        if content:
            self.console.print(f"[dim]Compact Result: {content[:200]}...[/dim]")
            self.memory.set_compact_history(content)
            
        # Clear context, keep latest N rounds
        system_content = self.get_system_prompt()
        blocks_to_keep = self.config.keep_recent_rounds * 2
        recent_messages = self.messages[-blocks_to_keep:] if len(self.messages) > blocks_to_keep else []
        
        # Ensure we don't start with a 'tool' message without a 'assistant' message that called it
        # Safest is just wipe them if it's too complex, but for simplicity let's just wipe everything but recent assistant/user chats
        safe_recent = [m for m in recent_messages if m["role"] in ["user", "assistant"] and m.get("content")]
        
        self.messages = [{"role": "system", "content": system_content}] + safe_recent

    async def step(self):
        # 1. Check if we need to inject user interjections
        while self.user_message_queue:
            msg = self.user_message_queue.pop(0)
            self.messages.append({"role": "user", "content": msg})
            
        # 2. Build system prompt if not present
        if not self.messages or self.messages[0]["role"] != "system":
            self._reset_messages(self.get_system_prompt())
        else:
            # Update system prompt dynamically to reflect tokens/files
            self.messages[0]["content"] = self.get_system_prompt()

        # Ensure there is at least one non-system message, as some API providers require it
        if len(self.messages) == 1 and self.messages[0]["role"] == "system":
            self.messages.append({"role": "user", "content": "Wake up and start your working loop! Explore the file system and write comments."})

        # 3. Check tokens and compact if necessary
        current_tokens = self.llm_client.count_tokens(self.messages)
        self.memory.add_tokens(current_tokens) # roughly
        
        threshold = self.config.max_context_window * self.config.compact_threshold
        if current_tokens >= threshold:
            await self._handle_compaction()

        # 4. Call LLM
        schemas = self.registry.get_schemas()
        
        content, tool_calls = await self.llm_client.chat(self.messages, schemas)
        
        # 5. Handle response
        assistant_msg = {"role": "assistant"}
        if content:
            assistant_msg["content"] = content
            self.console.print(f"\n[bold magenta]TokenWaster:[/bold magenta] {content}")
            
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
            if not content:
                # Some APIs require content to be present even if null, some require it not to be
                # We normalize to avoiding empty content
                assistant_msg["content"] = None
                
        self.messages.append(assistant_msg)
        
        # 6. Execute tools
        if tool_calls:
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                args_str = tc["function"]["arguments"]
                
                try:
                    args_dict = json.loads(args_str)
                except json.JSONDecodeError:
                    args_dict = {}
                    
                self.console.print(f"[dim cyan]>[/dim cyan] [cyan]Tool Call:[/cyan] {func_name}({args_str})")
                
                result = await self.registry.execute(func_name, args_dict)
                
                # Intercept image results
                if isinstance(result, str) and '"__type__": "image"' in result:
                    try:
                        res_dict = json.loads(result)
                        if res_dict.get("__type__") == "image":
                            mime = res_dict["mime_type"]
                            b64 = res_dict["base64_data"]
                            info = res_dict["info"]
                            
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "name": func_name,
                                "content": info # Just plain text info for the tool result itself
                            })
                            # Append user message with image to actually feed it
                            self.messages.append({
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": f"Here is the image you requested from {args_dict.get('path')}:"},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{mime};base64,{b64}"}
                                    }
                                ]
                            })
                            continue
                    except:
                        pass

                # If it's a file read, mark memory
                if func_name == "read_files" and "path" in args_dict:
                    self.memory.mark_file_read(args_dict["path"])
                    
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": func_name,
                    "content": str(result)
                })

    async def run_loop(self):
        self.console.print("\n[bold green]TokenWaster has awakened. I am here to waste your tokens![/bold green]")
        self.console.print("[dim]Type something to interject, or press Ctrl+C to stop.[/dim]\n")
        
        while True:
            try:
                await self.step()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[bold red]Error in agent loop:[/bold red] {str(e)}")
                import traceback
                traceback.print_exc()
                import asyncio
                await asyncio.sleep(5) # Pause briefly before retry so it doesn't spin loop on hard error
