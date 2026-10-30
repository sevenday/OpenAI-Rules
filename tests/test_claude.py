from pathlib import Path
import importlib.util
import textwrap

import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "update_claude.py"
spec = importlib.util.spec_from_file_location("update_claude", MODULE_PATH)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def test_extract_network_requirements_from_table():
    html = """
    <html><body>
      <h2>Network access requirements</h2>
      <table>
        <tr><th>URL</th><th>Required for</th></tr>
        <tr><td><code>api.anthropic.com</code></td><td>API</td></tr>
        <tr><td><code>*.frame.claudeusercontent.com</code></td><td>Artifacts</td></tr>
        <tr><td><code>raw.githubusercontent.com</code></td><td>Release notes</td></tr>
      </table>
      <h2>Next section</h2>
      <p><code>not-a-rule.example.com</code></p>
    </body></html>
    """
    assert update.extract_network_requirements_from_html(html) == [
        "DOMAIN-SUFFIX,frame.claudeusercontent.com",
        "DOMAIN,api.anthropic.com",
        "DOMAIN,raw.githubusercontent.com",
    ]


def test_extract_desktop_network_requirements_from_code_blocks():
    html = """
    <html><body>
      <h2>Network access requirements</h2>
      <p>Allow Anthropic hosts.</p>
      <pre><code>anthropic.com
*.anthropic.com
claude.app
*.claude.app
*.claudeusercontent.com
*.claudemcpcontent.com</code></pre>
      <pre><code>assets-proxy.anthropic.com
sso.claude.com
*.livepreview.claude.app</code></pre>
      <h2>Authentication and SSO</h2>
      <pre><code>must-not-be-included.example.com</code></pre>
    </body></html>
    """
    assert update.extract_desktop_network_requirements_from_html(html) == [
        "DOMAIN-SUFFIX,anthropic.com",
        "DOMAIN-SUFFIX,claude.app",
        "DOMAIN-SUFFIX,claudemcpcontent.com",
        "DOMAIN-SUFFIX,claudeusercontent.com",
        "DOMAIN-SUFFIX,livepreview.claude.app",
        "DOMAIN,anthropic.com",
        "DOMAIN,assets-proxy.anthropic.com",
        "DOMAIN,claude.app",
        "DOMAIN,sso.claude.com",
    ]


def test_extract_ignores_known_gerrit_pattern():
    html = """
    <h2>Network access requirements</h2>
    <table>
      <tr><th>URL</th><th>Required for</th></tr>
      <tr><td><code>api.anthropic.com</code></td><td>API</td></tr>
      <tr><td><code>*-review.googlesource.com</code></td><td>Gerrit</td></tr>
    </table>
    """
    assert update.extract_network_requirements_from_html(html) == [
        "DOMAIN,api.anthropic.com"
    ]


def test_extract_rejects_unknown_nonportable_pattern():
    html = """
    <h2>Network access requirements</h2>
    <table>
      <tr><th>URL</th><th>Required for</th></tr>
      <tr><td><code>*-new.example.com</code></td><td>Unknown</td></tr>
    </table>
    """
    with pytest.raises(ValueError, match="unsupported official domain pattern"):
        update.extract_network_requirements_from_html(html)


def test_extract_fails_when_heading_missing():
    with pytest.raises(ValueError, match="network requirements heading"):
        update.extract_network_requirements_from_html("<p>api.anthropic.com</p>")


def test_validate_requires_core_domains():
    rules = [f"DOMAIN,host{i}.example.com" for i in range(update.MIN_CLAUDE_OFFICIAL_RULES)]
    with pytest.raises(ValueError, match="missing required Claude core rule"):
        update.validate_claude_official_rules(rules)


def test_select_routing_rules_excludes_shared_infrastructure():
    rules = [
        "DOMAIN,api.anthropic.com",
        "DOMAIN,platform.claude.com",
        "DOMAIN,bridge.claudeusercontent.com",
        "DOMAIN,raw.githubusercontent.com",
        "DOMAIN,registry.npmjs.org",
        "DOMAIN,storage.googleapis.com",
    ]
    assert update.select_claude_routing_rules(rules) == [
        "DOMAIN,api.anthropic.com",
        "DOMAIN,bridge.claudeusercontent.com",
        "DOMAIN,platform.claude.com",
    ]


def test_build_claude_outputs_uses_curated_suffixes(tmp_path):
    data_dir = tmp_path / "data" / "claude"
    data_dir.mkdir(parents=True)
    (data_dir / "supplemental.txt").write_text(
        "\n".join([
            "DOMAIN-SUFFIX,anthropic.com",
            "DOMAIN-SUFFIX,claude.ai",
            "DOMAIN-SUFFIX,claude.com",
            "DOMAIN-SUFFIX,claudeusercontent.com",
            "",
        ]),
        encoding="utf-8",
    )
    official = [
        "DOMAIN,api.anthropic.com",
        "DOMAIN,claude.ai",
        "DOMAIN,claude.com",
        "DOMAIN,platform.claude.com",
        "DOMAIN,downloads.claude.ai",
        "DOMAIN,bridge.claudeusercontent.com",
        "DOMAIN-SUFFIX,frame.claudeusercontent.com",
        "DOMAIN,raw.githubusercontent.com",
        "DOMAIN,registry.npmjs.org",
        "DOMAIN,storage.googleapis.com",
        "DOMAIN,code.claude.com",
        "DOMAIN,mcp-proxy.anthropic.com",
    ]
    contents = update.build_claude_update_contents(
        tmp_path, official, include_official=True
    )
    clash = contents[tmp_path / "rules" / "Claude.list"]
    assert clash == (
        "DOMAIN-SUFFIX,anthropic.com\n"
        "DOMAIN-SUFFIX,claude.ai\n"
        "DOMAIN-SUFFIX,claude.com\n"
        "DOMAIN-SUFFIX,claudeusercontent.com\n"
    )
    assert "raw.githubusercontent.com" not in clash
    assert tmp_path / "data" / "claude" / "official.txt" in contents


def test_render_claude_official_snapshot_is_deterministic():
    rules = [
        "DOMAIN,raw.githubusercontent.com",
        "DOMAIN-SUFFIX,frame.claudeusercontent.com",
        "DOMAIN,api.anthropic.com",
    ]
    expected = textwrap.dedent(
        """\
        # Source: https://code.claude.com/docs/en/corporate-proxy
        # Section: Network access requirements
        # Source: https://code.claude.com/docs/en/desktop
        # Section: Network access requirements
        DOMAIN-SUFFIX,frame.claudeusercontent.com
        DOMAIN,api.anthropic.com
        DOMAIN,raw.githubusercontent.com
        """
    )
    assert update.render_claude_official_snapshot(rules) == expected


def test_generated_claude_rules_include_desktop_app_and_official_dev_blog():
    repo_root = Path(__file__).parents[1]
    official = update.load_rules(repo_root / "data" / "claude" / "official.txt")
    update.validate_claude_official_rules(official)
    contents = update.build_claude_update_contents(
        repo_root, official, include_official=False
    )
    for rendered in contents.values():
        assert "DOMAIN-SUFFIX,claude.app" in rendered
        assert "DOMAIN-SUFFIX,claude.dev" in rendered
        assert "DOMAIN,github.com" not in rendered


def test_checked_in_claude_generated_files_match_sources():
    repo_root = Path(__file__).parents[1]
    official = update.load_rules(repo_root / "data" / "claude" / "official.txt")
    update.validate_claude_official_rules(official)
    contents = update.build_claude_update_contents(
        repo_root, official, include_official=False
    )
    for path, expected in contents.items():
        assert path.read_text(encoding="utf-8") == expected, f"stale generated file: {path}"
