from tokenwaster.agent import TokenWasterAgent


def test_detects_tool_summary_text():
    assert TokenWasterAgent._is_tool_summary_text("[Tool calls: list_files]")
    assert TokenWasterAgent._is_tool_summary_text("[Tool calls: list_files, list_files]")
    assert not TokenWasterAgent._is_tool_summary_text("normal assistant text")


def test_dedupe_tool_calls_by_name_and_arguments():
    agent = TokenWasterAgent.__new__(TokenWasterAgent)
    tool_calls = [
        {
            "id": "a",
            "type": "function",
            "function": {"name": "list_files", "arguments": "{\"path\": \"D:/\"}"},
        },
        {
            "id": "b",
            "type": "function",
            "function": {"name": "list_files", "arguments": "{\"path\":\"D:/\"}"},
        },
        {
            "id": "c",
            "type": "function",
            "function": {"name": "list_files", "arguments": "{\"path\":\"C:/\"}"},
        },
    ]

    deduped = agent._dedupe_tool_calls(tool_calls)
    assert len(deduped) == 2
    assert deduped[0]["id"] == "a"
    assert deduped[1]["id"] == "c"
