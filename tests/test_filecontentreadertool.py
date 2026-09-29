import json

from tools.filecontentreadertool import FileContentReaderTool


def test_directory_read_is_bounded(tmp_path):
    for index in range(35):
        (tmp_path / f"{index:02}.txt").write_text(
            f"file {index}",
            encoding="utf-8",
        )

    result = json.loads(
        FileContentReaderTool().execute(file_paths=[str(tmp_path)])
    )

    file_results = [
        key for key in result if not key.startswith("__truncated__:")
    ]
    assert len(file_results) == 30
    assert result[f"__truncated__:{tmp_path}"] == (
        "Stopped after 30 files. Increase max_files to read more."
    )


def test_large_file_is_skipped_before_reading(tmp_path):
    file_path = tmp_path / "large.txt"
    file_path.write_text("x" * 32, encoding="utf-8")

    result = json.loads(
        FileContentReaderTool().execute(
            file_paths=[str(file_path)],
            max_file_size_bytes=16,
        )
    )

    assert result[str(file_path)] == (
        "Skipped: File exceeds size limit (32 > 16 bytes)"
    )
