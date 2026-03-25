import os
import yaml
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    max_context_window: int = 128000
    compact_threshold: float = 0.75
    keep_recent_rounds: int = 5
    multimodal: bool = True

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}. Please copy config.example.yaml to config.yaml and fill it out.")
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        provider = data.get("provider", "openai")
        if provider not in ["openai", "gemini", "anthropic", "openai_compatible"]:
            raise ValueError(f"Unsupported provider: {provider}")
            
        return cls(
            provider=provider,
            api_key=data.get("api_key", ""),
            model=data.get("model", ""),
            base_url=data.get("base_url"),
            max_context_window=data.get("max_context_window", 128000),
            compact_threshold=data.get("compact_threshold", 0.75),
            keep_recent_rounds=data.get("keep_recent_rounds", 5),
            multimodal=data.get("multimodal", True),
        )

def get_desktop_path() -> str:
    """Get the user's actual desktop path for TokenWaster Comment folder, supporting OneDrive."""
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        desktop, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        
        # Resolve any environment variables like %USERPROFILE% in the registry value
        desktop = os.path.expandvars(desktop)
    except Exception:
        # Fallback for non-Windows or if registry read fails
        user_profile = os.environ.get("USERPROFILE")
        if not user_profile:
            user_profile = os.path.expanduser("~")
        desktop = os.path.join(user_profile, "Desktop")
        
    return os.path.join(desktop, "TokenWaster Comment")
