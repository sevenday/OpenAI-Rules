#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tempfile
import urllib.error
import urllib.request

from bs4 import BeautifulSoup

OFFICIAL_URL = "https://help.openai.com/en/articles/9247338"
MIN_OFFICIAL_RULES = 20
DOMAIN_RE = re.compile(r"^(?:\*\.)?(?:[a-z0-9-]+\.)+[a-z0-9-]+$", re.I)
VALID_RULE_RE = re.compile(r"^(DOMAIN|DOMAIN-SUFFIX),((?:[a-z0-9-]+\.)+[a-z0-9-]+)$", re.I)
REQUIRED_CORE_RULES = {
    "DOMAIN-SUFFIX,openai.com",
    "DOMAIN-SUFFIX,chatgpt.com",
}


def rule_sort_key(rule: str) -> tuple[int, str]:
    kind, value = rule.split(",", 1)
    priority = {"DOMAIN-SUFFIX": 0, "DOMAIN": 1}
    return (priority[kind], value)


def canonicalize_domain_entry(entry: str) -> str:
    value = entry.strip().lower().rstrip(".")
    if not DOMAIN_RE.fullmatch(value):
        raise ValueError(f"invalid domain entry: {entry!r}")
    if value.startswith("*."):
        return f"DOMAIN-SUFFIX,{value[2:]}"
    return f"DOMAIN,{value}"


def extract_allowlist_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            tag
            for tag in soup.find_all(["h1", "h2", "h3", "h4"])
            if "domains to allowlist" in tag.get_text(" ", strip=True).lower()
        ),
        None,
    )
    if heading is None:
        raise ValueError("allowlist heading not found")

    found: list[str] = []
    node = heading.find_next_sibling()
    while node is not None:
        if getattr(node, "name", None) in {"h1", "h2", "h3", "h4"}:
            break
        for text in node.stripped_strings:
            candidate = text.strip().lower().rstrip(".")
            if DOMAIN_RE.fullmatch(candidate):
                found.append(canonicalize_domain_entry(candidate))
        node = node.find_next_sibling()

    rules = sorted(set(found), key=rule_sort_key)
    if not rules:
        raise ValueError("allowlist section contained no domains")
    return rules


def validate_official_rules(rules: list[str]) -> None:
    if len(rules) < MIN_OFFICIAL_RULES:
        raise ValueError(f"too few official rules: {len(rules)} < {MIN_OFFICIAL_RULES}")
    for rule in rules:
        if not VALID_RULE_RE.fullmatch(rule):
            raise ValueError(f"invalid normalized rule: {rule}")
    missing = REQUIRED_CORE_RULES.difference(rules)
    if missing:
        raise ValueError(f"missing required core rule(s): {', '.join(sorted(missing))}")


def load_rules(path: Path) -> list[str]:
    rules = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for rule in rules:
        if not VALID_RULE_RE.fullmatch(rule):
            raise ValueError(f"invalid rule in {path}: {rule}")
    return sorted(rules, key=rule_sort_key)


def _covered(domain: str, suffix: str) -> bool:
    return domain == suffix or domain.endswith("." + suffix)


def minimize_rules(rules: list[str]) -> list[str]:
    unique = sorted(set(rules), key=rule_sort_key)
    suffixes = {
        rule.split(",", 1)[1]
        for rule in unique
        if rule.startswith("DOMAIN-SUFFIX,")
    }
    result: list[str] = []
    for rule in unique:
        kind, domain = rule.split(",", 1)
        if kind == "DOMAIN" and any(_covered(domain, suffix) for suffix in suffixes):
            continue
        if kind == "DOMAIN-SUFFIX" and any(
            other != domain and _covered(domain, other) for other in suffixes
        ):
            continue
        result.append(rule)
    return result


def render_clash_list(rules: list[str]) -> str:
    return "".join(f"{rule}\n" for rule in rules)


def render_mihomo_yaml(rules: list[str]) -> str:
    return "payload:\n" + "".join(f"  - {rule}\n" for rule in rules)


def render_surge_list(rules: list[str]) -> str:
    return "".join(f"{rule}\n" for rule in rules)


def render_official_snapshot(rules: list[str]) -> str:
    header = (
        f"# Source: {OFFICIAL_URL}\n"
        "# Section: OpenAI/ChatGPT domains to allowlist\n"
    )
    return header + "".join(
        f"{rule}\n" for rule in sorted(set(rules), key=rule_sort_key)
    )


def fetch_official_html(url: str = OFFICIAL_URL) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "sevenday/OpenAI-Rules updater (+https://github.com/sevenday/OpenAI-Rules)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="strict")
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"failed to fetch official allowlist: {exc}") from exc


def build_update_contents(
    repo_root: Path,
    official_rules: list[str],
    *,
    include_official: bool,
) -> dict[Path, str]:
    supplemental_path = repo_root / "data" / "supplemental.txt"
    supplemental_rules = load_rules(supplemental_path) if supplemental_path.exists() else []
    merged = minimize_rules([*official_rules, *supplemental_rules])

    contents: dict[Path, str] = {
        repo_root / "rules" / "OpenAI.list": render_clash_list(merged),
        repo_root / "rules" / "OpenAI.yaml": render_mihomo_yaml(merged),
        repo_root / "rules" / "OpenAI-Surge.list": render_surge_list(merged),
    }
    if include_official:
        contents[repo_root / "data" / "official.txt"] = render_official_snapshot(
            official_rules
        )
    return contents


def apply_updates(contents: dict[Path, str]) -> list[Path]:
    changed: list[Path] = []
    for path, content in sorted(contents.items(), key=lambda item: str(item[0])):
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent, text=True
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.replace(temp_name, path)
        except Exception:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            raise
        changed.append(path)
    return changed


def prepare_live_update(repo_root: Path, official_rules: list[str]) -> dict[Path, str]:
    validate_official_rules(official_rules)
    return build_update_contents(repo_root, official_rules, include_official=True)


def update_from_live(repo_root: Path) -> list[Path]:
    html = fetch_official_html()
    official_rules = extract_allowlist_from_html(html)
    contents = prepare_live_update(repo_root, official_rules)
    return apply_updates(contents)


def regenerate_from_snapshot(repo_root: Path) -> list[Path]:
    official_path = repo_root / "data" / "official.txt"
    official_rules = load_rules(official_path)
    validate_official_rules(official_rules)
    contents = build_update_contents(repo_root, official_rules, include_official=False)
    return apply_updates(contents)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update OpenAI network allowlist and generated rule sets."
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Regenerate outputs from checked-in data/official.txt without network access.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    changed = (
        regenerate_from_snapshot(repo_root)
        if args.no_fetch
        else update_from_live(repo_root)
    )
    if changed:
        print("Updated:")
        for path in changed:
            print(f"- {path.relative_to(repo_root)}")
    else:
        print("No changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
