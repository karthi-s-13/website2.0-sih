from pathlib import Path

from app.services.ingestion.profiling import profile_directory, render_markdown

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"


def test_profile_directory_covers_all_files() -> None:
    report = profile_directory(RAW_DIR)
    assert report["file_count"] == 5
    for file_report in report["files"]:
        assert file_report["row_count"] > 0
        assert "project_code" in file_report["columns"]
        assert file_report["columns"]["project_code"]["missing_count"] == 0


def test_render_markdown_produces_output() -> None:
    report = profile_directory(RAW_DIR)
    markdown = render_markdown(report)
    assert "# Flash Report data profile" in markdown
    assert "project_code" in markdown
