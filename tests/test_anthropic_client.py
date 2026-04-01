from tokenwaster.llm.anthropic_client import AnthropicClient
from tokenwaster.__main__ import create_llm_client
from tokenwaster.config import Config
from tokenwaster.llm.openai_client import OpenAIClient


def test_anthropic_converts_openai_tool_flow():
    client = AnthropicClient(api_key="test-key", model="claude-3-5-sonnet-latest")
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "list files"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "list_files", "arguments": "{\"path\":\"D:/\"}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "name": "list_files", "content": "[]"},
    ]

    system, converted = client._convert_messages(messages)
    assert system == "sys"
    assert converted[0]["role"] == "user"
    assert converted[1]["role"] == "assistant"
    assert converted[1]["content"][0]["type"] == "tool_use"
    assert converted[1]["content"][0]["name"] == "list_files"
    assert converted[2]["role"] == "user"
    assert converted[2]["content"][0]["type"] == "tool_result"
    assert converted[2]["content"][0]["tool_use_id"] == "call_1"


def test_anthropic_never_emits_invalid_roles():
    client = AnthropicClient(api_key="test-key", model="claude-3-5-sonnet-latest")
    messages = [
        {"role": "assistant", "content": "hello"},
        {"role": "tool", "tool_call_id": "x", "content": "ok"},
        {"role": "user", "content": "next"},
    ]
    _, converted = client._convert_messages(messages)
    assert all(m["role"] in {"user", "assistant"} for m in converted)


def test_create_llm_client_openai_and_anthropic():
    openai_cfg = Config(provider="openai", api_key="k", model="gpt-4o-mini")
    anthropic_cfg = Config(provider="anthropic", api_key="k", model="claude-3-5-sonnet-latest")

    openai_client = create_llm_client(openai_cfg)
    anthropic_client = create_llm_client(anthropic_cfg)

    assert isinstance(openai_client, OpenAIClient)
    assert isinstance(anthropic_client, AnthropicClient)
