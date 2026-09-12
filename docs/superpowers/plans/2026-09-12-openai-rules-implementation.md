# OpenAI-Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a semi-automated OpenAI / ChatGPT / Codex rules repository that maintains one canonical data set, generates Clash Party, Mihomo/Clash, and Surge outputs, and opens a PR when the official OpenAI allowlist changes.

**Architecture:** `data/official.txt` stores the normalized official OpenAI allowlist, while `data/supplemental.txt` stores manually curated compatibility rules. A single Python generator/parser in `scripts/update.py` fetches and validates the official page, preserves the official semantic source set, merges and minimizes output rules, and renders three client-specific files. GitHub Actions runs the parser daily and uses a PR-only workflow so `main` is never changed automatically.

**Tech Stack:** Python 3.12, `beautifulsoup4`, `pytest`, GitHub Actions, `peter-evans/create-pull-request@v7`.

**Spec:** `docs/superpowers/specs/2026-09-12-openai-rules-design.md`

## Global Constraints

- Generate all three client outputs from one canonical merged rule set.
- Preserve official source semantics in `data/official.txt`, even when output minimization removes redundant exact-host rules.
- Never let a parsing failure overwrite the current official rules or generated outputs.
- Daily automation may create or update a PR, but must never auto-merge it.
- Supplemental rules must never be deleted by the official-page fetch logic.
- Default output must exclude overly broad legacy rules such as `DOMAIN-KEYWORD,openai`, `IP-ASN,20473`, historic fixed IP-CIDRs, `DOMAIN-SUFFIX,auth0.com`, `DOMAIN-SUFFIX,stripe.com`, and `DOMAIN-SUFFIX,sentry.io`.
- The official source URL is `https://help.openai.com/en/articles/9247338`.
- Scheduled check time is UTC 00:20 daily, approximately Beijing time 08:20.

---

## File Structure

- `scripts/update.py` — fetch, parse, validate, normalize, minimize, render, and write rules.
- `tests/test_update.py` — parser, normalization, minimization, rendering, and safety tests.
- `requirements.txt` — runtime/test dependencies for local and CI use.
- `data/official.txt` — checked-in normalized snapshot of the current official allowlist.
- `data/supplemental.txt` — checked-in manually curated compatibility rules.
- `rules/OpenAI.list` — Clash Party external rule-set output.
- `rules/OpenAI.yaml` — Mihomo/Clash classical rule-provider output.
- `rules/OpenAI-Surge.list` — Surge RULE-SET output.
- `.github/workflows/check-update.yml` — daily/manual check and PR creation workflow.
- `README.md` — subscription URLs, configuration examples, SSL/WebSocket notes, maintenance model.
- `sources.md` — source provenance, inclusion/exclusion policy, current curated supplemental list.

---

### Task 1: Create parser, normalization, and safety validation

**Files:**
- Create: `scripts/update.py`
- Create: `tests/test_update.py`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `canonicalize_domain_entry(entry: str) -> str`
- Produces: `extract_allowlist_from_html(html: str) -> list[str]`
- Produces: `validate_official_rules(rules: list[str]) -> None`
- Produces: constants `OFFICIAL_URL`, `MIN_OFFICIAL_RULES = 20`

- [ ] **Step 1: Add dependencies**

Create `requirements.txt`:

```text
beautifulsoup4>=4.12,<5
pytest>=8,<9
```

- [ ] **Step 2: Write failing parser and normalization tests**

Create `tests/test_update.py` with:

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


def test_extract_allowlist_only_reads_allowlist_section():
    html = """
    <html><body>
      <h2>OpenAI/ChatGPT domains to allowlist</h2>
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
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
pytest tests/test_update.py -v
```

Expected: FAIL because `scripts/update.py` does not exist or required functions are missing.

- [ ] **Step 4: Implement minimal parser and validation**

Create `scripts/update.py` with these core pieces:

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

    values: list[str] = []
    node = heading.find_next_sibling()
    while node is not None:
        if getattr(node, "name", None) in {"h1", "h2", "h3", "h4"}:
            break
        for text in node.stripped_strings:
            candidate = text.strip().lower().rstrip(".")
            if DOMAIN_RE.fullmatch(candidate):
                values.append(canonicalize_domain_entry(candidate))
        node = node.find_next_sibling()

    rules = sorted(set(values))
    if not rules:
        raise ValueError("allowlist section contained no domains")
    return rules


def validate_official_rules(rules: list[str]) -> None:
    if len(rules) < MIN_OFFICIAL_RULES:
        raise ValueError(
            f"too few official rules: {len(rules)} < {MIN_OFFICIAL_RULES}"
        )
    for rule in rules:
        kind, _, value = rule.partition(",")
        if kind not in {"DOMAIN", "DOMAIN-SUFFIX"} or not DOMAIN_RE.fullmatch(value):
            raise ValueError(f"invalid normalized rule: {rule}")
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
pytest tests/test_update.py -v
```

Expected: all Task 1 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt scripts/update.py tests/test_update.py
git commit -m "feat: parse and validate OpenAI allowlist"
```

---

### Task 2: Add rule loading, minimization, and three renderers

**Files:**
- Modify: `scripts/update.py`
- Modify: `tests/test_update.py`

**Interfaces:**
- Consumes: normalized rules in `TYPE,value` format.
- Produces: `load_rules(path: Path) -> list[str]`
- Produces: `minimize_rules(rules: list[str]) -> list[str]`
- Produces: `render_clash_list(rules: list[str]) -> str`
- Produces: `render_mihomo_yaml(rules: list[str]) -> str`
- Produces: `render_surge_list(rules: list[str]) -> str`

- [ ] **Step 1: Write failing minimization and renderer tests**

Append to `tests/test_update.py`:

```python
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


def test_render_clash_list():
    rules = ["DOMAIN-SUFFIX,openai.com", "DOMAIN,challenges.cloudflare.com"]
    assert update.render_clash_list(rules) == (
        "DOMAIN-SUFFIX,openai.com\n"
        "DOMAIN,challenges.cloudflare.com\n"
    )


def test_render_mihomo_yaml():
    rules = ["DOMAIN-SUFFIX,openai.com", "DOMAIN,challenges.cloudflare.com"]
    assert update.render_mihomo_yaml(rules) == (
        "payload:\n"
        "  - DOMAIN-SUFFIX,openai.com\n"
        "  - DOMAIN,challenges.cloudflare.com\n"
    )


def test_render_surge_list_matches_plain_rule_set_format():
    rules = ["DOMAIN-SUFFIX,openai.com", "DOMAIN,challenges.cloudflare.com"]
    assert update.render_surge_list(rules) == (
        "DOMAIN-SUFFIX,openai.com\n"
        "DOMAIN,challenges.cloudflare.com\n"
    )
```

- [ ] **Step 2: Run targeted tests and verify they fail**

Run:

```bash
pytest tests/test_update.py -k "minimize or render" -v
```

Expected: FAIL because the functions do not exist.

- [ ] **Step 3: Implement loader, minimizer, and renderers**

Add to `scripts/update.py`:

```python
from pathlib import Path


def load_rules(path: Path) -> list[str]:
    rules = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(line)
    return sorted(set(rules))


def _domain_is_covered(domain: str, suffix: str) -> bool:
    return domain == suffix or domain.endswith("." + suffix)


def minimize_rules(rules: list[str]) -> list[str]:
    unique = sorted(set(rules))
    suffixes = {
        rule.split(",", 1)[1]
        for rule in unique
        if rule.startswith("DOMAIN-SUFFIX,")
    }
    result = []
    for rule in unique:
        if rule.startswith("DOMAIN,"):
            domain = rule.split(",", 1)[1]
            if any(_domain_is_covered(domain, suffix) for suffix in suffixes):
                continue
        result.append(rule)
    return result


def render_clash_list(rules: list[str]) -> str:
    return "".join(f"{rule}\n" for rule in rules)


def render_mihomo_yaml(rules: list[str]) -> str:
    return "payload:\n" + "".join(f"  - {rule}\n" for rule in rules)


def render_surge_list(rules: list[str]) -> str:
    return "".join(f"{rule}\n" for rule in rules)
```

- [ ] **Step 4: Run full tests**

Run:

```bash
pytest tests/test_update.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/update.py tests/test_update.py
git commit -m "feat: render Clash Mihomo and Surge rules"
```

---

### Task 3: Add current official snapshot, curated supplemental data, and safe file generation

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
- Produces: `write_if_changed(path: Path, content: str) -> bool`
- Produces: `generate_outputs(repo_root: Path, official_rules: list[str]) -> list[Path]`
- Produces CLI: `python scripts/update.py` fetches official page, validates it, then updates official snapshot and generated files only after all checks pass.
- Produces CLI: `python scripts/update.py --no-fetch` regenerates outputs only from checked-in data.

- [ ] **Step 1: Seed the current official snapshot from OpenAI's current allowlist**

Create `data/official.txt` with comments followed by the current 26 normalized rules:

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

Note: the implementation must verify the live count before committing; if the official page differs at execution time, use the live validated list instead of blindly preserving this plan snapshot.

- [ ] **Step 2: Seed curated supplemental rules**

Create `data/supplemental.txt`:

```text
# Curated compatibility rules based on historical OpenAI dependencies.
# Source reference: blackmatrix7 ios_rule_script OpenAI.list
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

- [ ] **Step 3: Write failing safety and generation tests**

Append to `tests/test_update.py`:

```python
def test_write_if_changed_is_idempotent(tmp_path):
    path = tmp_path / "rules.txt"
    assert update.write_if_changed(path, "a\n") is True
    assert update.write_if_changed(path, "a\n") is False


def test_generate_outputs_keeps_supplemental_rules(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "rules").mkdir()
    (tmp_path / "data" / "supplemental.txt").write_text(
        "DOMAIN,openai-api.arkoselabs.com\n", encoding="utf-8"
    )
    update.generate_outputs(
        tmp_path,
        ["DOMAIN-SUFFIX,openai.com", "DOMAIN-SUFFIX,chatgpt.com"],
    )
    text = (tmp_path / "rules" / "OpenAI.list").read_text(encoding="utf-8")
    assert "DOMAIN,openai-api.arkoselabs.com" in text


def test_generate_outputs_minimizes_redundant_official_exact_hosts(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "rules").mkdir()
    (tmp_path / "data" / "supplemental.txt").write_text("", encoding="utf-8")
    update.generate_outputs(
        tmp_path,
        ["DOMAIN-SUFFIX,openai.com", "DOMAIN,chat.openai.com"],
    )
    text = (tmp_path / "rules" / "OpenAI.list").read_text(encoding="utf-8")
    assert "DOMAIN-SUFFIX,openai.com" in text
    assert "DOMAIN,chat.openai.com" not in text
```

- [ ] **Step 4: Run tests and verify new tests fail**

Run:

```bash
pytest tests/test_update.py -k "write_if_changed or generate_outputs" -v
```

Expected: FAIL because the functions are not implemented.

- [ ] **Step 5: Implement safe fetch, write, generation, and CLI**

Extend `scripts/update.py` with:

```python
import argparse
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def fetch_official_html(url: str = OFFICIAL_URL) -> str:
    request = Request(
        url,
        headers={"User-Agent": "OpenAI-Rules/1.0 (+https://github.com/sevenday/OpenAI-Rules)"},
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def write_if_changed(path: Path, content: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def render_official_snapshot(rules: list[str]) -> str:
    header = (
        "# Source: https://help.openai.com/en/articles/9247338\n"
        "# Section: OpenAI/ChatGPT domains to allowlist\n"
    )
    return header + "".join(f"{rule}\n" for rule in sorted(set(rules)))


def generate_outputs(repo_root: Path, official_rules: list[str]) -> list[Path]:
    supplemental = load_rules(repo_root / "data" / "supplemental.txt")
    merged = minimize_rules(official_rules + supplemental)
    outputs = {
        repo_root / "rules" / "OpenAI.list": render_clash_list(merged),
        repo_root / "rules" / "OpenAI.yaml": render_mihomo_yaml(merged),
        repo_root / "rules" / "OpenAI-Surge.list": render_surge_list(merged),
    }
    changed = []
    for path, content in outputs.items():
        if write_if_changed(path, content):
            changed.append(path)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)

    if args.no_fetch:
        official = load_rules(ROOT / "data" / "official.txt")
    else:
        html = fetch_official_html()
        official = extract_allowlist_from_html(html)
        validate_official_rules(official)
        # Only write after fetch + parse + validation all succeed.
        write_if_changed(
            ROOT / "data" / "official.txt",
            render_official_snapshot(official),
        )

    validate_official_rules(official)
    generate_outputs(ROOT, official)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run full unit tests**

Run:

```bash
pytest tests/test_update.py -v
```

Expected: PASS.

- [ ] **Step 7: Run local generation without network**

Run:

```bash
python scripts/update.py --no-fetch
```

Expected: creates all three `rules/` files without changing `data/official.txt`.

- [ ] **Step 8: Run live fetch once and inspect the official diff**

Run:

```bash
python scripts/update.py
git diff -- data/official.txt rules/
```

Expected: no unexpected large deletion; official rules remain at or above 20 entries; current OpenAI domains such as `chatgpt.com`, `openai.com`, `oaistatic.com`, `oaiusercontent.com`, and `oaistatsig.com` are present.

- [ ] **Step 9: Commit**

```bash
git add data/ rules/ scripts/update.py tests/test_update.py
git commit -m "feat: generate maintained OpenAI rule sets"
```

---

### Task 4: Add the semi-automatic GitHub Actions PR workflow

**Files:**
- Create: `.github/workflows/check-update.yml`
- Modify: `README.md` only if workflow-permission troubleshooting text is needed during implementation.

**Interfaces:**
- Schedule: `20 0 * * *`
- Manual trigger: `workflow_dispatch`
- Branch: `automation/openai-network-rules`
- PR title: `chore: update OpenAI network rules`
- No auto-merge.

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/check-update.yml`:

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
          labels: automated-update
```

- [ ] **Step 2: Validate YAML structure locally**

Run:

```bash
python - <<'PY'
from pathlib import Path
text = Path('.github/workflows/check-update.yml').read_text()
for required in ['schedule:', 'workflow_dispatch:', 'pull-requests: write', 'python scripts/update.py', 'create-pull-request@v7']:
    assert required in text, required
print('workflow structure OK')
PY
```

Expected: `workflow structure OK`.

- [ ] **Step 3: Run tests and generator again**

Run:

```bash
pytest -q
python scripts/update.py --no-fetch
git diff --check
```

Expected: tests pass, generator is idempotent, `git diff --check` reports no whitespace errors.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/check-update.yml
git commit -m "ci: check OpenAI rules daily and open PR"
```

---

### Task 5: Write user-facing documentation and source policy

**Files:**
- Modify: `README.md`
- Create: `sources.md`

**Interfaces:**
- Subscription URL for Clash Party: `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list`
- Subscription URL for Mihomo: `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml`
- Subscription URL for Surge: `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list`

- [ ] **Step 1: Replace README with complete usage documentation**

README must include these exact sections and examples:

```markdown
# OpenAI-Rules

Maintained OpenAI / ChatGPT / Codex network rule sets for Clash Party, Mihomo/Clash, and Surge.

## Subscription URLs

### Clash Party
`https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list`

### Mihomo / Clash
`https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml`

### Surge
`https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list`

## Clash Party / classical rule-set example

Use the `.list` URL as an external rule set and assign your own proxy policy group in the client. The rule file intentionally does not hard-code `PROXY`.

## Mihomo example

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

## Surge example

```ini
[Rule]
RULE-SET,https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list,PROXY
```

## Important network notes

- OpenAI's official list is an allowlist: it means the listed destinations should not be blocked or rewritten. It does not mean every network must proxy every destination.
- ChatGPT and Codex use secure WebSocket connections. OpenAI currently requires WebSocket upgrades over TCP 443 for `ws.chatgpt.com` and `chatgpt.com`.
- TLS/SSL inspection or HTTPS decryption can cause wrong-certificate errors and WebSocket failures. OpenAI recommends not rewriting or decrypting public OpenAI-domain traffic where possible.

## Maintenance model

A GitHub Actions workflow checks the official OpenAI network guidance every day. If the official domain list changes, the workflow regenerates all three formats and opens a Pull Request. Nothing is automatically merged into `main`.
```

- [ ] **Step 2: Create source policy documentation**

Create `sources.md` containing:

```markdown
# Sources and rule policy

## Primary source

OpenAI Help Center — Network recommendations for ChatGPT errors on web and apps:
https://help.openai.com/en/articles/9247338

The `OpenAI/ChatGPT domains to allowlist` section is the authoritative source for `data/official.txt`.

## Supplemental reference

blackmatrix7 / ios_rule_script OpenAI Surge list:
https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/OpenAI/OpenAI.list

The upstream file reports its last update as 2025-06-06. This repository does not blindly mirror it. Only narrow rules with a clear OpenAI/ChatGPT compatibility purpose are kept in `data/supplemental.txt`.

## Excluded broad legacy rules

The following are intentionally excluded by default because they can capture unrelated traffic or are stale infrastructure-specific entries:

- `DOMAIN-KEYWORD,openai`
- `IP-ASN,20473`
- historic fixed `IP-CIDR` entries
- `DOMAIN-SUFFIX,auth0.com`
- `DOMAIN-SUFFIX,stripe.com`
- `DOMAIN-SUFFIX,sentry.io`
- broad shared-service suffixes such as `algolia.net`, `launchdarkly.com`, `segment.io`, `observeit.net`, and `identrust.com`

## Review policy

Official-source changes are proposed through a Pull Request and require human review before merge. Supplemental rules are edited manually and are never deleted by the automatic official-source checker.
```

- [ ] **Step 3: Verify README subscription targets exist and files are non-empty**

Run:

```bash
python - <<'PY'
from pathlib import Path
for p in ['rules/OpenAI.list', 'rules/OpenAI.yaml', 'rules/OpenAI-Surge.list']:
    path = Path(p)
    assert path.exists(), p
    assert path.stat().st_size > 0, p
print('subscription targets OK')
PY
```

Expected: `subscription targets OK`.

- [ ] **Step 4: Commit**

```bash
git add README.md sources.md
git commit -m "docs: document OpenAI rule subscriptions and sources"
```

---

### Task 6: End-to-end verification and first workflow readiness check

**Files:**
- Verify all files; modify only if a verification failure exposes a real defect.

**Interfaces:**
- Final repository must be reproducible with `python scripts/update.py --no-fetch`.
- Live update must be safe with `python scripts/update.py`.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Verify deterministic generation**

Run:

```bash
python scripts/update.py --no-fetch
git diff --exit-code -- data/ rules/
```

Expected: exit code 0, proving checked-in outputs match the generator.

- [ ] **Step 3: Verify live official parsing**

Run:

```bash
python scripts/update.py
python - <<'PY'
from pathlib import Path
rules = [
    line.strip()
    for line in Path('data/official.txt').read_text().splitlines()
    if line.strip() and not line.startswith('#')
]
assert len(rules) >= 20
required = {
    'DOMAIN-SUFFIX,chatgpt.com',
    'DOMAIN-SUFFIX,openai.com',
    'DOMAIN-SUFFIX,oaistatic.com',
    'DOMAIN-SUFFIX,oaiusercontent.com',
    'DOMAIN-SUFFIX,oaistatsig.com',
}
assert required.issubset(set(rules)), required - set(rules)
print(f'official rules validated: {len(rules)}')
PY
```

Expected: validation succeeds and reports at least 20 official rules.

- [ ] **Step 4: Inspect generated rules for intentionally excluded broad legacy entries**

Run:

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

- [ ] **Step 5: Check formatting and repository diff**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only expected implementation files are changed if any live source difference was found.

- [ ] **Step 6: If the live official source changed during implementation, commit the validated snapshot update**

Only if `git status --short` shows validated changes in `data/official.txt` or generated files:

```bash
git add data/official.txt rules/
git commit -m "chore: sync current OpenAI network rules"
```

- [ ] **Step 7: Verify GitHub Actions repository permission requirement**

After pushing `.github/workflows/check-update.yml`, manually run **Check OpenAI network rules** from the Actions tab. If GitHub reports that `GITHUB_TOKEN` cannot create a pull request, enable the repository setting that allows GitHub Actions to create pull requests, then re-run the workflow. Do not replace the PR workflow with direct pushes to `main`.

- [ ] **Step 8: Final commit/status check**

Run:

```bash
git status --short
```

Expected: clean working tree.
