import pytest
import os
from tokenwaster.config import Config, get_desktop_path

def test_config_load_example():
    config = Config.load("d:/HALcode/TokenWaster/config.example.yaml")
    assert config.provider == "openai_compatible"
    assert config.max_context_window == 128000
    assert config.multimodal is True

def test_get_desktop_path():
    path = get_desktop_path()
    assert "Desktop" in path
    assert "TokenWaster Comment" in path
