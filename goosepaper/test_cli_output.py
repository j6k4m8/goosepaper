import json

from .__main__ import main


def test_main_reports_clean_error_for_missing_output_directory(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"version": 2, "sources": [], "paper": {"title": "T"}})
    )
    output_path = tmp_path / "no-such-dir" / "out.html"

    assert main(["-c", str(config_path), "-o", str(output_path)]) == 1
