# OpenAI-Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a semi-automated OpenAI / ChatGPT / Codex rules repository that keeps one canonical rule data set, generates Clash Party, Mihomo/Clash, and Surge subscriptions, and opens a PR when OpenAI's official allowlist changes.

**Architecture:** `data/official.txt` stores the normalized official allowlist and `data/supplemental.txt` stores manually curated compatibility rules. `scripts/update.py` fetches, parses, validates, merges, minimizes, and renders all three outputs; it computes every new file in memory before performing any replacement so network/parsing/validation/rendering failures cannot overwrite checked-in rules. GitHub Actions runs daily and creates or updates a reviewable PR; it never pushes updates directly to `main`.

**Tech Stack:** Python 3.12, `beautifulsoup4`, `pytest`, GitHub Actions, `peter-evans/create-pull-request@v7`.

**Spec:** `docs/superpowers/specs/2026-09-12-openai-rules-design.md`

## Global Constraints

- Generate all three client outputs from one canonical merged rule set.
- Preserve official source semantics in `data/official.txt`, even when generated outputs omit redundant exact-host rules.
- A fetch, parse, validation, or render failure must not overwrite the current official snapshot or generated outputs.
- Supplemental rules are never deleted by the official-page fetch logic.
- Daily automation may create/update a PR but must never auto-merge it.
- Exclude broad legacy captures by default: `DOMAIN-KEYWORD,openai`, `IP-ASN,20473`, historic fixed IP-CIDRs, `DOMAIN-SUFFIX,auth0.com`, `DOMAIN-SUFFIX,stripe.com`, and `DOMAIN-SUFFIX,sentry.io`.
- Official source: `https://help.openai.com/en/articles/9247338`.
- Daily schedule: UTC 00:20 (approximately Beijing time 08:20).

---

## File Structure

- `scripts/update.py` — fetch, parse, validate, minimize, render, stage, and atomically replace files.
- `tests/test_update.py` — parser, safety, minimization, rendering, and deterministic-generation tests.
- `requirements.txt` — `beautifulsoup4` and `pytest`.
- `data/official.txt` — normalized official snapshot.
- `data/supplemental.txt` — manually curated compatibility rules.
- `rules/OpenAI.list` — Clash Party external rules.
- `rules/OpenAI.yaml` — Mihomo/Clash classical rule-provider.
- `rules/OpenAI-Surge.list` — Surge RULE-SET.
- `.github/workflows/check-update.yml` — daily/manual check and PR creation.
- `README.md` — subscriptions and client examples.
- `sources.md` — provenance and inclusion/exclusion policy.

---

### Task 1: Parser and official-rule safety checks

**Files:**
- Create: `scripts/update.py`
- Create: `tests/test_update.py`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `canonicalize_domain_entry(entry: str) -> str`
- Produces: `extract_allowlist_from_html(html: str) -> list[str]`
- Produces: `validate_official_rules(rules: list[str]) -> None`
- Produces: `OFFICIAL_URL` and `MIN_OFFICIAL_RULES = 20`

- [ ] **Step 1: Add dependencies**

Create `requirements.txt`:

```text
beautifulsoup4>=4.12,<5
pytest>=8,<9
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_update.py`:

```python
from pathlib import Path
import importlib.util
import pytest

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "update.py"
spec = importlib.util.spec_from_file_location("update", MODULE_PATH)
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def test_canonicalize_wildcard_domain():
    assert update.canonicalize_domain_entry("*.chatgpt.com") == "DOMAIN-SUFFIX,chatgpt.com"


def test_canonicalize_exact_domain():
    assert update.canonicalize_domain_entry("challenges.cloudflare.com") == "DOMAIN,challenges.cloudflare.com"


def test_extract_reads_only_allowlist_section():
    html = """
    <h2>OpenAI/ChatGPT domains to allowlist</h2>
    <ul><li>*.openai.com</li><li>*.chatgpt.com</li><li>challenges.cloudflare.com</li></ul>
    <h2>WebSocket requirements for ChatGPT and Codex</h2>
    <p>wss://ws.chatgpt.com</p><p>example.invalid</p>
    """
    assert update.extract_allowlist_from_html(html) == [
        "DOMAIN-SUFFIX,chatgpt.com",
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,challenges.cloudflare.com",
    ]


def test_extract_fails_when_heading_missing():
    with pytest.raises(ValueError, match="allowlist heading"):
        update.extract_allowlist_from_html("<p>*.openai.com</p>")


def test_validate_rejects_suspiciously_small_result():
    with pytest.raises(ValueError, match="too few official rules"):
        update.validate_official_rules(["DOMAIN-SUFFIX,openai.com"])
```

- [ ] **Step 3: Run tests to confirm failure**

```bash
pytest tests/test_update.py -v
```

Expected: FAIL because `scripts/update.py` or the functions do not exist.

- [ ] **Step 4: Implement the minimal parser**

Create `scripts/update.py` with:

```python
from __future__ import annotations

import re
from bs4 import BeautifulSoup

OFFICIAL_URL = "https://help.openai.com/en/articles/9247338"
MIN_OFFICIAL_RULES = 20
DOMAIN_RE = re.compile(r"^(?:\*\.)?(?:[a-z0-9-]+\.)+[a-z0-9-]+$", re.I)


def canonicalize_domain_entry(entry: str) -> str:
    value = entry.strip().lower().rstrip(".")
    if not DOMAIN_RE.fullmatch(value):
        raise ValueError(f"invalid domain entry: {entry!r}")
    return (
        f"DOMAIN-SUFFIX,{value[2:]}"
        if value.startswith("*.")
        else f"DOMAIN,{value}"
    )


def extract_allowlist_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            tag for tag in soup.find_all(["h1", "h2", "h3", "h4"])
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
    if not found:
        raise ValueError("allowlist section contained no domains")
    return sorted(set(found))


def validate_official_rules(rules: list[str]) -> None:
    if len(rules) < MIN_OFFICIAL_RULES:
        raise ValueError(f"too few official rules: {len(rules)} < {MIN_OFFICIAL_RULES}")
    for rule in rules:
        kind, sep, value = rule.partition(",")
        if sep != "," or kind not in {"DOMAIN", "DOMAIN-SUFFIX"} or not DOMAIN_RE.fullmatch(value):
            raise ValueError(f"invalid normalized rule: {rule}")
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_update.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt scripts/update.py tests/test_update.py
git commit -m "feat: parse and validate OpenAI allowlist"
```

---

### Task 2: Minimize and render all three formats

**Files:**
- Modify: `scripts/update.py`
- Modify: `tests/test_update.py`

**Interfaces:**
- Produces: `load_rules(path: Path) -> list[str]`
- Produces: `minimize_rules(rules: list[str]) -> list[str]`
- Produces: `render_clash_list(rules: list[str]) -> str`
- Produces: `render_mihomo_yaml(rules: list[str]) -> str`
- Produces: `render_surge_list(rules: list[str]) -> str`

- [ ] **Step 1: Add failing tests**

Append:

```python
def test_minimize_removes_exact_domain_covered_by_suffix():
    assert update.minimize_rules([
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,chat.openai.com",
        "DOMAIN,challenges.cloudflare.com",
    ]) == [
        "DOMAIN-SUFFIX,openai.com",
        "DOMAIN,challenges.cloudflare.com",
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
```

- [ ] **Step 2: Confirm failure**

```bash
pytest tests/test_update.py -k "minimize or render" -v
```

Expected: FAIL because the functions do not exist.

- [ ] **Step 3: Implement loader/minimizer/renderers**

Add:

```python
from pathlib import Path


def load_rules(path: Path) -> list[str]:
    return sorted({
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    })


def _covered(domain: str, suffix: str) -> bool:
    return domain == suffix or domain.endswith("." + suffix)


def minimize_rules(rules: list[str]) -> list[str]:
    unique = sorted(set(rules))
    suffixes = {
        r.split(",", 1)[1]
        for r in unique
        if r.startswith("DOMAIN-SUFFIX,")
    }
    return [
        r for r in unique
        if not (
            r.startswith("DOMAIN,")
            and any(_covered(r.split(",", 1)[1], suffix) for suffix in suffixes)
        )
    ]


def render_clash_list(rules: list[str]) -> str:
    return "".join(f"{rule}\n" for rule in rules)


def render_mihomo_yaml(rules: list[str]) -> str:
    return "payload:\n" + "".join(f"  - {rule}\n" for rule in rules)


def render_surge_list(rules: list[str]) -> str:
    return "".join(f"{rule}\n" for rule in rules)
```

- [ ] **Step 4: Run tests and commit**

```bash
pytest tests/test_update.py -v
git add scripts/update.py tests/test_update.py
git commit -m "feat: render Clash Mihomo and Surge rules"
```

Expected: tests PASS before commit.

---

### Task 3: Seed current data and implement safe deterministic updates

**Files:**
- Create: `data/official.txt`
- Create: `data/supplemental.txt`
- Create: `rules/OpenAI.list`
- Create: `rules/OpenAI.yaml`
- Create: `rules/OpenAI-Surge.list`
- Modify: `scripts/update.py`
- Modify: `tests/test_update.py`

**Interfaces:**
- Produces: `fetch_official_html(url: str = OFFICIAL_URL) -> str`
- Produces: `render_official_snapshot(rules: list[str]) -> str`
- Produces: `build_update_contents(repo_root: Path, official_rules: list[str], include_official: bool) -> dict[Path, str]`
- Produces: `apply_updates(contents: dict[Path, str]) -> list[Path]`
- CLI: `python scripts/update.py` fetches/validates/builds everything before replacing files.
- CLI: `python scripts/update.py --no-fetch` regenerates outputs from checked-in data only.

- [ ] **Step 1: Seed the current official snapshot**

As of 2026-09-12, OpenAI's allowlist section contains **29** normalized entries. Create `data/official.txt`:

```text
# Source: https://help.openai.com/en/articles/9247338
# Section: OpenAI/ChatGPT domains to allowlist
DOMAIN-SUFFIX,auth.openai.com
DOMAIN-SUFFIX,chatgpt.com
DOMAIN-SUFFIX,ct.sendgrid.net
DOMAIN-SUFFIX,intercom.io
DOMAIN-SUFFIX,intercomcdn.com
DOMAIN-SUFFIX,oaistatic.com
DOMAIN-SUFFIX,oaistatsig.com
DOMAIN-SUFFIX,oaiusercontent.com
DOMAIN-SUFFIX,openai.com
DOMAIN,android.chat.openai.com
DOMAIN,auth0.openai.com
DOMAIN,cdn.openaimerge.com
DOMAIN,cdn.workos.com
DOMAIN,challenges.cloudflare.com
DOMAIN,chat.openai.com
DOMAIN,desktop.chat.openai.com
DOMAIN,forwarder.workos.com
DOMAIN,humb.apple.com
DOMAIN,images.workoscdn.com
DOMAIN,ios.chat.openai.com
DOMAIN,js.intercomcdn.com
DOMAIN,js.stripe.com
DOMAIN,o207216.ingest.sentry.io
DOMAIN,o33249.ingest.sentry.io
DOMAIN,rum.browser-intake-datadoghq.com
DOMAIN,setup.auth.openai.com
DOMAIN,setup.workos.com
DOMAIN,tcr9i.chat.openai.com
DOMAIN,workos.imgix.net
```

At implementation time, run the live fetch before final commit; if OpenAI has changed the list, commit the newly validated live snapshot instead of forcing this dated snapshot.

- [ ] **Step 2: Seed curated supplemental rules**

Create `data/supplemental.txt`:

```text
# Curated compatibility rules based on historical OpenAI dependencies.
# Reference: blackmatrix7 ios_rule_script OpenAI.list
DOMAIN,browser-intake-datadoghq.com
DOMAIN,chat.openai.com.cdn.cloudflare.net
DOMAIN,openai-api.arkoselabs.com
DOMAIN,openaicom-api-bdcpf8c6d2e9atf6.z01.azurefd.net
DOMAIN,openaicomproductionae4b.blob.core.windows.net
DOMAIN,production-openaicom-storage.azureedge.net
DOMAIN,static.cloudflareinsights.com
DOMAIN-SUFFIX,api.statsig.com
DOMAIN-SUFFIX,chatgpt.livekit.cloud
DOMAIN-SUFFIX,client-api.arkoselabs.com
DOMAIN-SUFFIX,events.statsigapi.net
DOMAIN-SUFFIX,featuregates.org
DOMAIN-SUFFIX,host.livekit.cloud
DOMAIN-SUFFIX,openaiapi-site.azureedge.net
DOMAIN-SUFFIX,openaicom.imgix.net
DOMAIN-SUFFIX,turn.livekit.cloud
```

- [ ] **Step 3: Add failing safety tests**

Append:

```python
def test_build_contents_does_not_write_before_apply(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "supplemental.txt").write_text(
        "DOMAIN,openai-api.arkoselabs.com\n", encoding="utf-8"
    )
    contents = update.build_update_contents(
        tmp_path,
        ["DOMAIN-SUFFIX,openai.com", "DOMAIN-SUFFIX,chatgpt.com"],
        include_official=True,
    )
    assert not (tmp_path / "data" / "official.txt").exists()
    assert not (tmp_path / "rules" / "OpenAI.list").exists()
    assert tmp_path / "data" / "official.txt" in contents


def test_apply_updates_is_idempotent(tmp_path):
    target = tmp_path / "rules" / "OpenAI.list"
    contents = {target: "DOMAIN-SUFFIX,openai.com\n"}
    assert update.apply_updates(contents) == [target]
    assert update.apply_updates(contents) == []
```

- [ ] **Step 4: Confirm failure**

```bash
pytest tests/test_update.py -k "build_contents or apply_updates" -v
```

Expected: FAIL because the functions do not exist.

- [ ] **Step 5: Implement fetch/build/apply/CLI**

Add to `scripts/update.py`:

```python
import argparse
import os
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def fetch_official_html(url: str = OFFICIAL_URL) -> str:
    req = Request(
        url,
        headers={"User-Agent": "OpenAI-Rules/1.0 (+https://github.com/sevenday/OpenAI-Rules)"},
    )
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def render_official_snapshot(rules: list[str]) -> str:
    return (
        "# Source: https://help.openai.com/en/articles/9247338\n"
        "# Section: OpenAI/ChatGPT domains to allowlist\n"
        + "".join(f"{rule}\n" for rule in sorted(set(rules)))
    )


def build_update_contents(
    repo_root: Path,
    official_rules: list[str],
    include_official: bool,
) -> dict[Path, str]:
    validate_official_rules(official_rules)
    supplemental = load_rules(repo_root / "data" / "supplemental.txt")
    merged = minimize_rules(official_rules + supplemental)
    contents = {
        repo_root / "rules" / "OpenAI.list": render_clash_list(merged),
        repo_root / "rules" / "OpenAI.yaml": render_mihomo_yaml(merged),
        repo_root / "rules" / "OpenAI-Surge.list": render_surge_list(merged),
    }
    if include_official:
        contents[repo_root / "data" / "official.txt"] = render_official_snapshot(official_rules)
    return contents


def apply_updates(contents: dict[Path, str]) -> list[Path]:
    changed: list[Path] = []
    staged: list[tuple[Path, Path]] = []
    try:
        for target, text in contents.items():
            if target.exists() and target.read_text(encoding="utf-8") == text:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", dir=target.parent)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            staged.append((Path(temp_name), target))
        for temp_path, target in staged:
            os.replace(temp_path, target)
            changed.append(target)
        return changed
    finally:
        for temp_path, _ in staged:
            if temp_path.exists():
                temp_path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)

    if args.no_fetch:
        official = load_rules(ROOT / "data" / "official.txt")
        contents = build_update_contents(ROOT, official, include_official=False)
    else:
        official = extract_allowlist_from_html(fetch_official_html())
        validate_official_rules(official)
        contents = build_update_contents(ROOT, official, include_official=True)

    apply_updates(contents)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

This stages all changed files only after fetch/parse/validation/rendering succeeds. Each replacement uses `os.replace`, so an individual file replacement is atomic.

- [ ] **Step 6: Run tests and generate outputs**

```bash
pytest tests/test_update.py -v
python scripts/update.py --no-fetch
python scripts/update.py --no-fetch
git diff --check
```

Expected: tests PASS; the second generation produces no additional diff; no whitespace errors.

- [ ] **Step 7: Run one live fetch and inspect it**

```bash
python scripts/update.py
git diff -- data/official.txt rules/
```

Expected: no suspicious mass deletion; at least 20 official entries remain; `chatgpt.com`, `openai.com`, `oaistatic.com`, `oaiusercontent.com`, and `oaistatsig.com` remain present.

- [ ] **Step 8: Commit**

```bash
git add data/ rules/ scripts/update.py tests/test_update.py
git commit -m "feat: generate maintained OpenAI rule sets"
```

---

### Task 4: Daily GitHub Actions check with PR-only updates

**Files:**
- Create: `.github/workflows/check-update.yml`

**Interfaces:**
- Schedule: `20 0 * * *`
- Manual trigger: `workflow_dispatch`
- Update branch: `automation/openai-network-rules`
- PR title: `chore: update OpenAI network rules`

- [ ] **Step 1: Create the workflow**

```yaml
name: Check OpenAI network rules

on:
  schedule:
    - cron: "20 0 * * *"
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: python -m pip install -r requirements.txt

      - name: Run tests
        run: pytest -q

      - name: Fetch official allowlist and regenerate rules
        run: python scripts/update.py

      - name: Create or update pull request
        uses: peter-evans/create-pull-request@v7
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          branch: automation/openai-network-rules
          delete-branch: true
          commit-message: "chore: update OpenAI network rules"
          title: "chore: update OpenAI network rules"
          body: |
            OpenAI's official network allowlist or generated rule output has changed.

            Please review the diff before merging. This repository intentionally does not auto-merge network-rule changes.
```

- [ ] **Step 2: Verify workflow text and project tests**

```bash
python - <<'PY'
from pathlib import Path
text = Path('.github/workflows/check-update.yml').read_text()
for required in [
    '20 0 * * *',
    'workflow_dispatch:',
    'pull-requests: write',
    'python scripts/update.py',
    'create-pull-request@v7',
]:
    assert required in text, required
print('workflow structure OK')
PY
pytest -q
python scripts/update.py --no-fetch
git diff --check
```

Expected: structure check PASS, tests PASS, deterministic generation, no whitespace errors.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/check-update.yml
git commit -m "ci: check OpenAI rules daily and open PR"
```

---

### Task 5: README and source policy

**Files:**
- Modify: `README.md`
- Create: `sources.md`

**Interfaces:**
- Clash Party: `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list`
- Mihomo: `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml`
- Surge: `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list`

- [ ] **Step 1: Replace README with complete usage documentation**

The README must include the three URLs above plus these executable examples:

```yaml
rule-providers:
  openai:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml
    path: ./ruleset/openai.yaml
    interval: 86400

rules:
  - RULE-SET,openai,PROXY
```

```ini
[Rule]
RULE-SET,https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list,PROXY
```

It must also state:

- OpenAI's published list is an **allowlist**, not a statement that every destination must be proxied on every network.
- Clash Party's `.list` file intentionally contains no hard-coded `PROXY`; the client assigns the policy group.
- ChatGPT currently uses `wss://ws.chatgpt.com` and Codex uses `wss://chatgpt.com/`; WebSocket upgrades must be allowed over TCP 443.
- TLS/SSL inspection or HTTPS decryption can cause wrong-certificate errors and WebSocket failures; OpenAI advises avoiding such rewriting for public OpenAI domains where possible.
- Daily automation opens a PR and never auto-merges.

- [ ] **Step 2: Create `sources.md`**

Use this content:

```markdown
# Sources and rule policy

## Primary source

OpenAI Help Center — Network recommendations for ChatGPT errors on web and apps:
https://help.openai.com/en/articles/9247338

The `OpenAI/ChatGPT domains to allowlist` section is authoritative for `data/official.txt`.

## Supplemental reference

blackmatrix7 / ios_rule_script OpenAI Surge list:
https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/OpenAI/OpenAI.list

The referenced upstream file reports `UPDATED: 2025-06-06 09:20:00`. This repository does not blindly mirror it; only narrow compatibility rules are retained in `data/supplemental.txt`.

## Intentionally excluded broad legacy rules

- `DOMAIN-KEYWORD,openai`
- `IP-ASN,20473`
- historic fixed `IP-CIDR` entries
- `DOMAIN-SUFFIX,auth0.com`
- `DOMAIN-SUFFIX,stripe.com`
- `DOMAIN-SUFFIX,sentry.io`
- broad shared-service suffixes such as `algolia.net`, `launchdarkly.com`, `segment.io`, `observeit.net`, and `identrust.com`

## Review policy

Official-source changes are proposed through a Pull Request and require human review. Supplemental rules are edited manually and are never deleted by the official-source checker.
```

- [ ] **Step 3: Verify subscription targets and commit**

```bash
python - <<'PY'
from pathlib import Path
for name in ['rules/OpenAI.list', 'rules/OpenAI.yaml', 'rules/OpenAI-Surge.list']:
    path = Path(name)
    assert path.exists() and path.stat().st_size > 0, name
print('subscription targets OK')
PY
git add README.md sources.md
git commit -m "docs: document OpenAI rule subscriptions and sources"
```

Expected: `subscription targets OK` before commit.

---

### Task 6: End-to-end verification

**Files:**
- Verify all implementation files; modify only when a verification failure identifies a concrete defect.

- [ ] **Step 1: Run the full suite**

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Prove deterministic local generation**

```bash
python scripts/update.py --no-fetch
git diff --exit-code -- data/ rules/
```

Expected: exit code 0.

- [ ] **Step 3: Verify the live official source**

```bash
python scripts/update.py
python - <<'PY'
from pathlib import Path
rules = {
    line.strip()
    for line in Path('data/official.txt').read_text().splitlines()
    if line.strip() and not line.startswith('#')
}
assert len(rules) >= 20
required = {
    'DOMAIN-SUFFIX,chatgpt.com',
    'DOMAIN-SUFFIX,openai.com',
    'DOMAIN-SUFFIX,oaistatic.com',
    'DOMAIN-SUFFIX,oaiusercontent.com',
    'DOMAIN-SUFFIX,oaistatsig.com',
}
assert required <= rules, required - rules
print(f'official rules validated: {len(rules)}')
PY
```

Expected: validation succeeds with at least 20 official entries.

- [ ] **Step 4: Verify broad legacy rules stay excluded**

```bash
python - <<'PY'
from pathlib import Path
text = Path('rules/OpenAI.list').read_text()
for forbidden in [
    'DOMAIN-KEYWORD,openai',
    'IP-ASN,20473',
    'DOMAIN-SUFFIX,auth0.com',
    'DOMAIN-SUFFIX,stripe.com',
    'DOMAIN-SUFFIX,sentry.io',
]:
    assert forbidden not in text, forbidden
print('broad legacy exclusions OK')
PY
```

Expected: `broad legacy exclusions OK`.

- [ ] **Step 5: Check repository cleanliness and workflow readiness**

```bash
git diff --check
git status --short
```

If the live source legitimately changed, commit only the validated `data/official.txt` and regenerated `rules/` files with:

```bash
git add data/official.txt rules/
git commit -m "chore: sync current OpenAI network rules"
```

Then manually run **Check OpenAI network rules** once in the GitHub Actions tab. If GitHub reports that `GITHUB_TOKEN` is not allowed to create pull requests, enable the repository setting that allows GitHub Actions to create pull requests and run it again. Do not replace this with a workflow that pushes directly to `main`.

- [ ] **Step 6: Final clean-state check**

```bash
git status --short
```

Expected: no uncommitted changes.
