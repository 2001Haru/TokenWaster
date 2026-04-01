import pytest
import os
from tokenwaster.config import Config, get_desktop_path

def test_config_load_example():
    config = Config.load("d:/HALcode/TokenWaster/config.example.yaml")
    assert config.provider == "openai_compatible"
    assert config.max_context_window == 128000
    assert config.multimodal is True
    assert config.max_rpm == 18

def test_get_desktop_path():
    path = get_desktop_path()
    assert "Desktop" in path
    assert "TokenWaster Comment" in path

def test_provider_alias_normalization():
    assert Config.normalize_provider("OpenAI-Compatible") == "openai_compatible"
    assert Config.normalize_provider("google") == "gemini"
    assert Config.normalize_provider("claude") == "anthropic"

def test_provider_normalization_rejects_unknown():
    with pytest.raises(ValueError):
        Config.normalize_provider("mystery_provider")

def test_openai_compatible_requires_base_url():
    cfg_path = "d:/HALcode/TokenWaster/tests/_tmp_bad_config.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(
            'provider: "openai_compatible"\napi_key: "x"\nmodel: "y"\n',
        )
    try:
        with pytest.raises(ValueError, match="base_url"):
            Config.load(cfg_path)
    finally:
        if os.path.exists(cfg_path):
            os.remove(cfg_path)
