from io import StringIO

from rich.console import Console

from ce3 import Assistant


def test_tool_usage_renders_paths_and_brackets_as_literal_text():
    output = StringIO()
    assistant = Assistant.__new__(Assistant)
    assistant.console = Console(file=output, force_terminal=False, color_system=None)

    assistant._display_tool_usage(
        "filecontentreadertool",
        {"file_paths": ["/home/yoan"]},
        "contents include [/not-a-rich-tag] and [/?#]",
    )

    rendered = output.getvalue()
    assert "/home/yoan" in rendered
    assert "[/not-a-rich-tag]" in rendered
    assert "[/?#]" in rendered
