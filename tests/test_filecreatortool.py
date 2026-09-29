import json

from tools.filecreatortool import FileCreatorTool


def test_redundant_files_wrapper_is_unwrapped(tmp_path):
    file_path = tmp_path / "nested.txt"

    result = json.loads(
        FileCreatorTool().execute(
            files={
                "files": [
                    {
                        "path": str(file_path),
                        "content": "hello",
                    }
                ]
            }
        )
    )

    assert result["created_files"] == 1
    assert result["failed_files"] == 0
    assert file_path.read_text(encoding="utf-8") == "hello"


def test_invalid_files_input_returns_clear_error():
    result = json.loads(FileCreatorTool().execute(files="not-a-file-spec"))

    assert result["created_files"] == 0
    assert result["failed_files"] == 1
    assert "'files' must be a file object" in result["results"][0]["error"]
