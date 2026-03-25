import argparse
import asyncio
from rich.console import Console

from tokenwaster.config import Config
from tokenwaster.llm.openai_client import OpenAIClient
from tokenwaster.llm.gemini_client import GeminiClient
from tokenwaster.llm.anthropic_client import AnthropicClient
from tokenwaster.agent import TokenWasterAgent
from tokenwaster.cli import CLIManager

def create_llm_client(config: Config):
    if config.provider in ["openai", "openai_compatible"]:
        return OpenAIClient(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url
        )
    elif config.provider == "gemini":
        return GeminiClient(
            api_key=config.api_key,
            model=config.model
        )
    elif config.provider == "anthropic":
        return AnthropicClient(
            api_key=config.api_key,
            model=config.model
        )
    else:
        raise ValueError(f"Unknown provider {config.provider}")

async def async_main():
    parser = argparse.ArgumentParser(description="TokenWaster: A useless personal agent.")
    parser.add_argument("command", nargs="?", default="agent", help="Command to run (e.g. agent)")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    console = Console()
    
    if args.command == "agent" or args.command is None:
        console.print("[bold cyan]Loading TokenWaster Config...[/bold cyan]")

    
    try:
        config = Config.load(args.config)
    except FileNotFoundError as e:
        console.print(f"[bold red]Configuration error:[/bold red] {str(e)}")
        return
        
    client = create_llm_client(config)
    agent = TokenWasterAgent(config, client, console)
    cli_manager = CLIManager(agent, console)
    
    try:
        await cli_manager.run()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]TokenWaster interrupted by user. Goodbye![/bold yellow]")

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
