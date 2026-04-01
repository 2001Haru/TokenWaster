import os
import yaml
from dataclasses import dataclass
from typing import Optional

PROVIDER_ALIASES = {
    "openai": "openai",
    "openai_compatible": "openai_compatible",
    "openai-compatible": "openai_compatible",
    "openai_compat": "openai_compatible",
    "compat": "openai_compatible",
    "gemini": "gemini",
    "google": "gemini",
    "google_gemini": "gemini",
    "anthropic": "anthropic",
    "claude": "anthropic",
}

SUPPORTED_PROVIDERS = sorted(set(PROVIDER_ALIASES.values()))

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
    max_rpm: int | None = None

    @staticmethod
    def normalize_provider(raw_provider: str | None) -> str:
        provider = (raw_provider or "openai").strip().lower()
        normalized = PROVIDER_ALIASES.get(provider)
        if not normalized:
            options = ", ".join(SUPPORTED_PROVIDERS)
            raise ValueError(f"Unsupported provider: {raw_provider}. Supported providers: {options}")
        return normalized

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Config file not found: {path}. Please copy config.example.yaml to config.yaml and fill it out.")
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError(f"Invalid config format in {path}: top-level YAML must be a mapping/object.")

        provider = cls.normalize_provider(data.get("provider", "openai"))
        base_url = data.get("base_url")
        if isinstance(base_url, str):
            base_url = base_url.strip() or None
        if provider == "openai_compatible" and not base_url:
            raise ValueError("provider 'openai_compatible' requires non-empty 'base_url'.")
            
        return cls(
            provider=provider,
            api_key=data.get("api_key", ""),
            model=data.get("model", ""),
            base_url=base_url,
            max_context_window=data.get("max_context_window", 128000),
            compact_threshold=data.get("compact_threshold", 0.75),
            keep_recent_rounds=data.get("keep_recent_rounds", 5),
            multimodal=data.get("multimodal", True),
            max_rpm=data.get("max_rpm"),
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
