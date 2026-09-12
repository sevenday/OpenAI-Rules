from pathlib import Path
import importlib.util

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "update.py"
spec = importlib.util.spec_from_file_location("update", MODULE_PATH)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def test_checked_in_generated_files_match_sources():
    repo_root = Path(__file__).parents[1]
    official = update.load_rules(repo_root / "data" / "official.txt")
    update.validate_official_rules(official)
    contents = update.build_update_contents(repo_root, official, include_official=False)
    for path, expected in contents.items():
        assert path.read_text(encoding="utf-8") == expected, f"stale generated file: {path}"
