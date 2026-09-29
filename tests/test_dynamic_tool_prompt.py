from ce3 import Assistant


def make_assistant(tools):
    assistant = Assistant.__new__(Assistant)
    assistant.tools = tools
    return assistant


def test_system_prompt_lists_only_loaded_tools():
    assistant = make_assistant(
        [
            {
                "name": "customtool",
                "description": "Does one custom task.",
                "input_schema": {"type": "object"},
            }
        ]
    )

    prompt = assistant._build_system_prompt()

    assert "customtool: Does one custom task." in prompt
    assert "BrowserTool" not in prompt
    assert "FileCreatorTool" not in prompt


def test_system_prompt_explicitly_disables_tools_when_none_are_loaded():
    assistant = make_assistant([])

    prompt = assistant._build_system_prompt()

    assert "Currently available tools: none." in prompt
    assert "Do not attempt tool calls." in prompt
