import asyncio
import sys
from rich.console import Console
import threading

def _listen_for_input(loop: asyncio.AbstractEventLoop, callback):
    """Run in a separate thread to listen for stdin without blocking the async loop."""
    for line in sys.stdin:
        line = line.strip()
        if line:
            # We schedule the callback on the main event loop
            loop.call_soon_threadsafe(callback, line)

class CLIManager:
    def __init__(self, agent, console: Console):
        self.agent = agent
        self.console = console
        self._input_thread = None

    def _handle_input(self, text: str):
        self.console.print(f"\n[bold yellow]User Interjected:[/bold yellow] {text}")
        self.agent.add_user_interjection(text)

    async def run(self):
        loop = asyncio.get_running_loop()
        
        # Start a daemon thread to read stdin
        self._input_thread = threading.Thread(
            target=_listen_for_input, 
            args=(loop, self._handle_input),
            daemon=True
        )
        self._input_thread.start()
        
        # Run agent
        await self.agent.run_loop()
