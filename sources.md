# Sources and rule policy

## 1. Primary source: OpenAI

Official network guidance:

- https://help.openai.com/en/articles/9247338

The updater reads only the **OpenAI/ChatGPT domains to allowlist** section. It does not turn unrelated text, WebSocket URLs, firewall ports, Voice IP ranges, or troubleshooting examples into domain rules.

The checked-in official snapshot is stored in `data/official.txt` so every automatic change remains reviewable in Git history and in the generated Pull Request.

## 2. Supplemental reference

Historical reference:

- https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Surge/OpenAI/OpenAI.list

That upstream file reports `UPDATED: 2025-06-06 09:20:00`. This repository does **not** copy it wholesale. Only relatively specific historical OpenAI/ChatGPT dependencies are kept in `data/supplemental.txt`.

Currently curated supplemental groups include:

- OpenAI-specific Arkose Labs verification hosts
- ChatGPT/LiveKit hosts
- Statsig hosts historically used by the service
- OpenAI-specific Azure CDN / Blob / Imgix hosts
- Specific Cloudflare Insights / Datadog hosts present in the historical rules

## 3. Intentionally excluded broad legacy rules

The following blackmatrix7-style rules are intentionally not included by default because they can capture substantial traffic unrelated to OpenAI:

```text
DOMAIN-KEYWORD,openai
IP-ASN,20473,no-resolve
IP-CIDR,24.199.123.28/32,no-resolve
IP-CIDR,64.23.132.171/32,no-resolve
DOMAIN-SUFFIX,auth0.com
DOMAIN-SUFFIX,stripe.com
DOMAIN-SUFFIX,sentry.io
```

The repository also avoids broad shared third-party suffixes unless there is a strong OpenAI-specific reason to include them, including historical entries such as:

```text
DOMAIN-SUFFIX,algolia.net
DOMAIN-SUFFIX,identrust.com
DOMAIN-SUFFIX,launchdarkly.com
DOMAIN-SUFFIX,observeit.net
DOMAIN-SUFFIX,segment.io
```

`DOMAIN-SUFFIX,ai.com` is also omitted because the current OpenAI official allowlist does not require it and the domain-wide match is not needed for current ChatGPT/Codex routing.

If connection logs later demonstrate that an excluded dependency is still required, it should be added as narrowly as possible and documented here.

## 4. Output minimization

`data/official.txt` preserves the normalized semantics of the official list. Generated client files are allowed to remove redundant exact-host rules when a broader `DOMAIN-SUFFIX` rule already covers the same host.

For example, when both of these exist in source data:

```text
DOMAIN-SUFFIX,openai.com
DOMAIN,chat.openai.com
```

the generated rule-set only needs the suffix rule. This keeps subscriptions smaller while preserving the official source snapshot for auditing.

## 5. Automation safety

Before writing any live update, the updater requires:

- the allowlist heading to be found;
- at least 20 normalized official rules;
- valid `DOMAIN` / `DOMAIN-SUFFIX` syntax;
- the core `openai.com` and `chatgpt.com` suffix rules.

The complete new official snapshot and all three outputs are built before any file is replaced. The final replacement uses same-directory temporary files and `os.replace`, so a fetch/parse/validation/render failure does not partially overwrite the repository's maintained rule files.
