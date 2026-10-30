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

## 2. Anthropic / Claude primary sources

Official Claude Code and Claude Desktop network guidance:

- https://code.claude.com/docs/en/corporate-proxy
- https://code.claude.com/docs/en/desktop

The Claude updater parses the **Network access requirements** table in the Claude Code page and the **Network access requirements** section in the Desktop page. It stores normalized portable `DOMAIN` / `DOMAIN-SUFFIX` entries from both sources in `data/claude/official.txt`. The Desktop page contains two host lists; both are parsed so the more specific host list and the wildcard form remain auditable. Known non-portable Gerrit patterns remain excluded.

The current official sources include:

- `api.anthropic.com`, `platform.claude.com`, and `sso.claude.com`
- `claude.ai`, `claude.com`, and `claude.app` / their documented subdomains
- `assets-proxy.anthropic.com`, `a-api.anthropic.com`, `a-cdn.anthropic.com`, and `s-cdn.anthropic.com`
- `bridge.claudeusercontent.com`, `*.frame.claudeusercontent.com`, and `*.claudemcpcontent.com`
- `github.com`, `raw.githubusercontent.com`, `registry.npmjs.org`, and `storage.googleapis.com`
- Datadog intake hosts, `formulae.brew.sh`, and `code.claude.com`

The official Desktop documentation says `assets-proxy.anthropic.com` is one of the hosts serving app code and user content. It is already covered by the broader `anthropic.com` suffix in the generated output. Likewise, `sso.claude.com` is covered by `claude.com`, and Claude Desktop's artifact/MCP content hosts are covered by `claudeusercontent.com` and `claudemcpcontent.com`.

### Claude default routing policy

The default generated Claude rule sets route core domain roots and narrowly scoped, manually reviewed compatibility dependencies:

```text
DOMAIN-SUFFIX,anthropic.com
DOMAIN-SUFFIX,clau.de
DOMAIN-SUFFIX,claude.ai
DOMAIN-SUFFIX,claude.app
DOMAIN-SUFFIX,claude.com
DOMAIN-SUFFIX,claude.dev
DOMAIN-SUFFIX,claudemcpclient.com
DOMAIN-SUFFIX,claudemcpcontent.com
DOMAIN-SUFFIX,claudeusercontent.com
DOMAIN,servd-anthropic-website.b-cdn.net
```

`clau.de` is an official Claude short-link domain. `claude.app` is listed in Anthropic's current Desktop network requirements. `claude.dev` is the official Claude developer blog, included as a related first-party site rather than a claim that it is required for API connectivity. `claudemcpcontent.com` is used by Claude-hosted MCP Apps content frames; see Anthropic's MCP Apps cross-compatibility documentation at https://claude.com/docs/connectors/building/mcp-apps/cross-compatibility.

`claudemcpclient.com` and the exact Bunny CDN tenant host are community compatibility entries reviewed on 2026-09-13, not claims of official allowlist status. The October 2026 v2fly list added several more Claude-named domains, but they are not included by default without stronger first-party documentation or specific traffic evidence. See the pinned sources and limitations in the [comparison record](docs/rule-comparison-2026-09-13.md).

Shared official dependencies such as GitHub, GitHub Raw, npm, Google Storage, Datadog and Homebrew are preserved in the official snapshot for auditing and change detection, but are not added to the Claude-specific output by default because doing so could proxy substantial unrelated traffic. If a user's network requires those shared services to use a proxy, they should generally be handled by the broader GitHub / Google / npm rules. Narrow exceptions can also be added to `data/claude/supplemental.txt` after review.
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

## 5. Community comparison and maintenance

The [2026-09-13 comparison](docs/rule-comparison-2026-09-13.md) records pinned revisions of VPSDance, v2fly, MetaCubeX and blackmatrix7, accepted entries, deferred candidates and rejected broad matches. OpenAI additions are `chat.com`, the exact Azure Blob host `openaiassets.blob.core.windows.net`, and the scoped `openai.com.cdn.cloudflare.net` suffix (replacing its narrower legacy chat host).

Community sources are discovery inputs, never automatically unioned into subscriptions. Curated compatibility entries stay in `data/supplemental.txt` and `data/claude/supplemental.txt`; official snapshots preserve the official source semantics. Periodic review should check both additions and whether older dependencies are still needed. Shared upstream agreement alone is not proof of current domain ownership, connectivity improvement, or independent verification.
