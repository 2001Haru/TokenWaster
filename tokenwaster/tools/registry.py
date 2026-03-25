from typing import Callable, Any

class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._schemas = []

    def register(self, schema: dict, func: Callable):
        self._tools[schema["name"]] = func
        self._schemas.append({"type": "function", "function": schema})

    def get_schemas(self) -> list[dict]:
        return self._schemas

    async def execute(self, name: str, kwargs: dict) -> Any:
        if name not in self._tools:
            return f"Error: Tool '{name}' not found."
            
        try:
            func = self._tools[name]
            import inspect
            if inspect.iscoroutinefunction(func):
                return await func(**kwargs)
            else:
                return func(**kwargs)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"
