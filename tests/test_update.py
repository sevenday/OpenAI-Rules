from pathlib import Path
import importlib.util
import textwrap
import urllib.error

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "update.py"
spec = importlib.util.spec_from_file_location("update", MODULE_PATH)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def test_canonicalize_wildcard_domain():
    assert update.canonicalize_domain_entry("*.chatgpt.com") == "DOMAIN-SUFFIX,chatgpt.com"


def test_canonicalize_exact_domain():
    assert update.canonicalize_domain_entry("challenges.cloudflare.com") == "DOMAIN,challenges.cloudflare.com"


def test_canonicalize_rejects_urls():
    with pytest.raises(ValueError, match="invalid domain entry"):
        update.canonicalize_domain_entry("https://chatgpt.com")


def test_extract_reads_only_allowlist_section():
    html = """
    <html><body>
      <h2>OpenAI/ChatGPT domains to allowlist</h2>
      <p>OpenAI uses the following domains:</p>
      <ul>
        <li>*.openai.com</li>
        <li>*.chatgpt.com</li>
        <li>challenges.cloudflare.com</li>
      </ul>
      <h2>WebSocket requirements for ChatGPT and Codex</h2>
      <p>wss://ws.chatgpt.com</p>
      <p>example.invalid</p>
    </body></html>
    """
    assert update.extract_allowlist_from_html(html) == [
        "DOMAIN-SUFFIX,chatgpt.com",
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,challenges.cloudflare.com",
    ]


def test_extract_fails_when_heading_missing():
    with pytest.raises(ValueError, match="allowlist heading"):
        update.extract_allowlist_from_html("<html><body><p>*.openai.com</p></body></html>")


def test_validate_rejects_suspiciously_small_result():
    with pytest.raises(ValueError, match="too few official rules"):
        update.validate_official_rules(["DOMAIN-SUFFIX,openai.com"])


def test_validate_requires_core_openai_domains():
    rules = [f"DOMAIN,host{i}.example.com" for i in range(update.MIN_OFFICIAL_RULES)]
    with pytest.raises(ValueError, match="missing required core rule"):
        update.validate_official_rules(rules)


def test_minimize_removes_exact_domain_covered_by_suffix():
    rules = [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,chat.openai.com",
        "DOMAIN,challenges.cloudflare.com",
    ]
    assert update.minimize_rules(rules) == [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,challenges.cloudflare.com",
    ]


def test_minimize_does_not_remove_unrelated_exact_domain():
    rules = [
        "DOMAIN-SUFFIX,chatgpt.com",
        "DOMAIN,challenges.cloudflare.com",
    ]
    assert update.minimize_rules(rules) == [
        "DOMAIN-SUFFIX,chatgpt.com",
        "DOMAIN,challenges.cloudflare.com",
    ]


def test_minimize_removes_nested_suffixes_without_mutating_source():
    rules = [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN-SUFFIX,auth.openai.com",
        "DOMAIN-SUFFIX,setup.auth.openai.com",
        "DOMAIN,setup.auth.openai.com",
    ]
    original = rules.copy()
    assert update.minimize_rules(rules) == ["DOMAIN-SUFFIX,openai.com"]
    assert rules == original


def test_minimize_preserves_domain_label_boundaries():
    rules = [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN-SUFFIX,notopenai.com",
        "DOMAIN-SUFFIX,openai.com.cdn.cloudflare.net",
        "DOMAIN,openai.com.example.net",
    ]
    assert update.minimize_rules(rules) == [
        "DOMAIN-SUFFIX,notopenai.com",
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN-SUFFIX,openai.com.cdn.cloudflare.net",
        "DOMAIN,openai.com.example.net",
    ]


def test_renderers():
    rules = ["DOMAIN-SUFFIX,openai.com", "DOMAIN,challenges.cloudflare.com"]
    plain = "DOMAIN-SUFFIX,openai.com\nDOMAIN,challenges.cloudflare.com\n"
    assert update.render_clash_list(rules) == plain
    assert update.render_surge_list(rules) == plain
    assert update.render_mihomo_yaml(rules) == (
        "payload:\n"
        "  - DOMAIN-SUFFIX,openai.com\n"
        "  - DOMAIN,challenges.cloudflare.com\n"
    )


def test_load_rules_ignores_comments_and_duplicates(tmp_path):
    path = tmp_path / "rules.txt"
    path.write_text(
        "# comment\nDOMAIN-SUFFIX,openai.com\n\nDOMAIN-SUFFIX,openai.com\nDOMAIN,foo.example.com\n",
        encoding="utf-8",
    )
    assert update.load_rules(path) == [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,foo.example.com",
    ]


def test_build_contents_does_not_write_before_apply(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "supplemental.txt").write_text(
        "DOMAIN,openai-api.arkoselabs.com\n", encoding="utf-8"
    )
    official = [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN-SUFFIX,chatgpt.com",
    ]
    contents = update.build_update_contents(
        tmp_path, official, include_official=True
    )
    assert not (tmp_path / "data" / "official.txt").exists()
    assert not (tmp_path / "rules" / "OpenAI.list").exists()
    assert tmp_path / "data" / "official.txt" in contents


def test_apply_updates_is_idempotent(tmp_path):
    target = tmp_path / "rules" / "OpenAI.list"
    contents = {target: "DOMAIN-SUFFIX,openai.com\n"}
    changed = update.apply_updates(contents)
    assert changed == [target]
    changed_again = update.apply_updates(contents)
    assert changed_again == []


def test_apply_updates_creates_all_parent_directories(tmp_path):
    target = tmp_path / "deep" / "nested" / "file.txt"
    update.apply_updates({target: "ok\n"})
    assert target.read_text(encoding="utf-8") == "ok\n"


def test_render_official_snapshot_is_deterministic():
    rules = ["DOMAIN,foo.example.com", "DOMAIN-SUFFIX,openai.com"]
    expected = textwrap.dedent(
        """\
        # Source: https://help.openai.com/en/articles/9247338
        # Section: OpenAI/ChatGPT domains to allowlist
        DOMAIN-SUFFIX,openai.com
        DOMAIN,foo.example.com
        """
    )
    assert update.render_official_snapshot(rules) == expected


def test_fetch_official_html_wraps_network_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(update.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="failed to fetch official allowlist"):
        update.fetch_official_html()


def test_failed_validation_does_not_overwrite_existing_files(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "rules").mkdir()
    official_path = tmp_path / "data" / "official.txt"
    rule_path = tmp_path / "rules" / "OpenAI.list"
    official_path.write_text("old official\n", encoding="utf-8")
    rule_path.write_text("old rules\n", encoding="utf-8")

    bad_rules = ["DOMAIN-SUFFIX,openai.com"]
    with pytest.raises(ValueError):
        update.prepare_live_update(tmp_path, bad_rules)

    assert official_path.read_text(encoding="utf-8") == "old official\n"
    assert rule_path.read_text(encoding="utf-8") == "old rules\n"


def test_build_outputs_minimizes_redundant_exact_openai_hosts(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "supplemental.txt").write_text(
        "DOMAIN,openai-api.arkoselabs.com\n", encoding="utf-8"
    )
    official = [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN-SUFFIX,chatgpt.com",
        "DOMAIN,chat.openai.com",
    ]
    contents = update.build_update_contents(tmp_path, official, include_official=False)
    clash = contents[tmp_path / "rules" / "OpenAI.list"]
    assert "DOMAIN,chat.openai.com\n" not in clash
    assert "DOMAIN-SUFFIX,openai.com\n" in clash
    assert "DOMAIN,openai-api.arkoselabs.com\n" in clash
