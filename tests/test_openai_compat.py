from tokenwaster.llm.openai_client import OpenAIClient


def test_detects_string_content_error():
    assert OpenAIClient._needs_string_content("Invalid value for content: expected a string, got null")


def test_detects_tool_role_unsupported_error():
    assert OpenAIClient._tool_role_unsupported("Unsupported role 'tool' in messages")


def test_detects_retry_without_tools():
    assert OpenAIClient._should_retry_without_tools("tools are not supported by this model")


def test_detects_reasoning_content_missing_for_tool_calls():
    text = "thinking is enabled but reasoning_content is missing in assistant tool call message at index 2"
    assert OpenAIClient._reasoning_content_missing_for_tool_calls(text)


def test_extracts_retry_after_seconds():
    text = "request reached organization max RPM: 20, please try again after 1 seconds"
    assert OpenAIClient._extract_retry_after_seconds(text) == 1.0


def test_compat_message_sanitization_for_tool_role():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    messages = [
        {"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]},
        {"role": "tool", "name": "read_files", "content": "ok", "tool_call_id": "1"},
    ]
    sanitized = client._sanitize_messages(messages, mode="compat")

    assert "[Tool calls]" in sanitized[0]["content"]
    assert sanitized[1]["role"] == "user"
    assert "[Tool:read_files]" in sanitized[1]["content"]


def test_compat_message_sanitization_flattens_assistant_tool_calls():
    client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {"id": "1", "type": "function", "function": {"name": "list_files", "arguments": "{}"}}
            ],
        }
    ]
    sanitized = client._sanitize_messages(messages, mode="compat")

    assert "tool_calls" not in sanitized[0]
    assert sanitized[0]["role"] == "assistant"
    assert "[Tool calls: list_files]" in sanitized[0]["content"]
