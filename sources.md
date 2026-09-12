# Sources and rule policy

## 1. OpenAI primary source

Official network guidance:

- https://help.openai.com/en/articles/9247338

The OpenAI updater reads only the **OpenAI/ChatGPT domains to allowlist** section. It does not turn unrelated text, WebSocket URLs, firewall ports, Voice IP ranges, or troubleshooting examples into domain rules.

The checked-in official snapshot is stored in `data/official.txt` so every automatic change remains reviewable in Git history and in generated Pull Requests.

### OpenAI supplemental reference

Historical reference:

- https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Surge/OpenAI/OpenAI.list

That upstream file reports `UPDATED: 2025-06-06 09:20:00`. This repository does **not** copy it wholesale. Only relatively specific historical OpenAI/ChatGPT dependencies are kept in `data/supplemental.txt`.

The repository intentionally excludes broad legacy captures such as:

```text
DOMAIN-KEYWORD,openai
IP-ASN,20473,no-resolve
IP-CIDR,24.199.123.28/32,no-resolve
IP-CIDR,64.23.132.171/32,no-resolve
DOMAIN-SUFFIX,auth0.com
DOMAIN-SUFFIX,stripe.com
DOMAIN-SUFFIX,sentry.io
```

It also avoids broad shared third-party suffixes such as `algolia.net`, `identrust.com`, `launchdarkly.com`, `observeit.net` and `segment.io` unless there is a strong OpenAI-specific reason to include them.

## 2. Anthropic / Claude primary source

Official Claude Code enterprise network guidance:

- https://code.claude.com/docs/en/corporate-proxy

The Claude updater parses the **Network access requirements** table and stores every portable `DOMAIN` / `DOMAIN-SUFFIX` entry in `data/claude/official.txt`.

As of the initial Claude integration, that official table includes both Claude-owned hosts and shared third-party infrastructure, including examples such as:

- `api.anthropic.com`
- `claude.ai`
- `claude.com`
- `platform.claude.com`
- `mcp-proxy.anthropic.com`
- `downloads.claude.ai`
- `bridge.claudeusercontent.com`
- `*.frame.claudeusercontent.com`
- `raw.githubusercontent.com`
- `registry.npmjs.org`
- `storage.googleapis.com`
- Datadog intake hosts
- `formulae.brew.sh`
- `code.claude.com`

The official table also contains the optional Gerrit pattern `*-review.googlesource.com`. That pattern is intentionally not converted into the maintained client rule files because it is not portable across the repository's minimal `DOMAIN` / `DOMAIN-SUFFIX` output model and only applies to a specific Gerrit checkout scenario.

### Claude default routing policy

The default generated Claude rule sets deliberately route only Anthropic / Claude-owned domain roots:

```text
DOMAIN-SUFFIX,anthropic.com
DOMAIN-SUFFIX,claude.ai
DOMAIN-SUFFIX,claude.com
DOMAIN-SUFFIX,claudeusercontent.com
```

This keeps Claude routing narrow. Shared official dependencies such as GitHub Raw, npm, Google Storage, Datadog and Homebrew are preserved in the official snapshot for auditing and change detection, but are not added to the Claude-specific output by default because doing so could proxy substantial unrelated traffic.

If a user's network requires those shared services to use a proxy, they should generally be handled by the user's broader GitHub / Google / npm rules. Narrow exceptions can also be added to `data/claude/supplemental.txt` after review.

## 3. Output minimization

Official snapshots preserve normalized source semantics. Generated client files are allowed to remove redundant exact-host or narrower suffix rules when a broader `DOMAIN-SUFFIX` rule already covers them.

For example:

```text
DOMAIN-SUFFIX,openai.com
DOMAIN,chat.openai.com
```

only needs the suffix rule in a generated subscription. The same applies to Claude, where `DOMAIN-SUFFIX,claude.com` covers `platform.claude.com` and `code.claude.com`.

## 4. Automation safety

Before writing any live OpenAI update, the updater requires:

- the allowlist heading to be found;
- at least 20 normalized official rules;
- valid `DOMAIN` / `DOMAIN-SUFFIX` syntax;
- the core `openai.com` and `chatgpt.com` suffix rules.

Before writing any live Claude update, the updater requires:

- the `Network access requirements` heading and table to be found;
- at least 12 normalized official entries;
- valid `DOMAIN` / `DOMAIN-SUFFIX` syntax;
- required Claude core hosts such as `api.anthropic.com`, `claude.ai`, `claude.com`, `platform.claude.com`, `downloads.claude.ai` and `bridge.claudeusercontent.com`;
- any newly introduced non-portable wildcard pattern to fail loudly instead of being silently ignored.

Both updaters build complete new contents before replacement and use same-directory temporary files plus `os.replace`, so a fetch/parse/validation/render failure does not partially overwrite maintained rule files.
