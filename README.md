# OpenAI-Rules

面向 **OpenAI / ChatGPT / Codex / Claude / MapleStory GMS** 的网络规则集，提供 Clash Party、Mihomo/Clash 和 Surge 三种订阅格式。

仓库同时维护 OpenAI 与 Anthropic 官方网络要求；每天自动检查官方文档，发现变化时只创建 Pull Request，**不会自动合并到 `main`**。MapleStory 规则目前为人工维护。

> 仓库名暂时保留 `OpenAI-Rules`，这样已经在用的 OpenAI 订阅地址不用改；Claude 和 MapleStory 规则直接放在同一仓库中。

## 订阅地址

| 服务 | 客户端 | 订阅地址 |
| --- | --- | --- |
| OpenAI | Clash Party / text rule-set | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list` |
| OpenAI | Mihomo / Clash classical rule-provider | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml` |
| OpenAI | Surge RULE-SET | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list` |
| Claude | Clash Party / text rule-set | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/Claude.list` |
| Claude | Mihomo / Clash classical rule-provider | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/Claude.yaml` |
| Claude | Surge RULE-SET | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/Claude-Surge.list` |
| MapleStory GMS | Clash Party / text rule-set | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/MapleStory.list` |
| MapleStory GMS | Mihomo / Clash classical rule-provider | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/MapleStory.yaml` |
| MapleStory GMS | Surge RULE-SET | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/MapleStory-Surge.list` |

## Clash Party / Mihomo

OpenAI：

```yaml
rule-providers:
  OpenAI:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml
    path: ./ruleset/openai-sevenday.yaml
    interval: 86400

rules:
  - RULE-SET,OpenAI,PROXY
```

Claude：

```yaml
rule-providers:
  Claude:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/Claude.yaml
    path: ./ruleset/claude-sevenday.yaml
    interval: 86400

rules:
  - RULE-SET,Claude,PROXY
```

MapleStory GMS：

```yaml
rule-providers:
  MapleStory:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/MapleStory.yaml
    path: ./ruleset/maplestory-sevenday.yaml
    interval: 86400

rules:
  - RULE-SET,MapleStory,PROXY
```

请把 `PROXY` 换成你自己的策略组名称。

如果不同服务需要不同出口，可分别使用独立策略组。同一服务的登录、API、内容或游戏连接应使用一致的出口。把对应 `RULE-SET` 放在会提前命中的通用代理规则、直连规则和最终 `MATCH` 之前。

使用 `.list` 作为 Mihomo rule-provider 时，设置 `behavior: classical`、`format: text`；使用 `.yaml` 时设置 `behavior: classical`、`format: yaml`。这些文件是规则订阅，不是包含节点的完整代理配置。

## Surge

```ini
RULE-SET,https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list,Proxy
RULE-SET,https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/Claude-Surge.list,Proxy
RULE-SET,https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/MapleStory-Surge.list,Proxy
```

MapleStory 的 Surge 版本按 **iOS 使用场景**维护为纯域名规则，不包含 `PROCESS-NAME`。Surge iOS 无法使用 Windows/macOS 进程名识别远端电脑上的游戏进程；需要进程分流时请使用 Clash/Mihomo 版本。

## MapleStory GMS 规则策略

MapleStory 的 Clash/Mihomo 规则优先使用游戏和启动器进程匹配，并以 Nexon 域名作为补充：

```text
PROCESS-NAME,MapleStory.exe
PROCESS-NAME,nexon_launcher.exe
PROCESS-NAME,MapleStory
PROCESS-NAME,MapleStory Launcher
PROCESS-NAME,Nexon Launcher
DOMAIN-SUFFIX,nexon.com
DOMAIN-SUFFIX,nexon.net
```

Surge iOS 版本只保留：

```text
DOMAIN-SUFFIX,nexon.com
DOMAIN-SUFFIX,nexon.net
```

`nexon.com` 和 `nexon.net` 的后缀规则同时覆盖 MapleStory 官网、Nexon 登录、支持站、`download2.nexon.net`、`nxcache.nexon.net` 等 Nexon 子域名，因此不重复维护大量子域名。游戏服务器若直接连接 IP，则 Clash/Mihomo 主要依赖 `MapleStory` 进程规则完成分流；Surge iOS 无法通过进程名补足这类直接 IP 连接。

Steam 版不默认加入 `steam.exe` 进程规则，避免把整个 Steam 商店、好友和游戏下载流量都送入 MapleStory 策略组。Windows 以 `MapleStory.exe` 和 `nexon_launcher.exe` 为主要匹配；无扩展名的进程条目用于兼容 macOS/不同客户端显示名称。

## Claude 默认规则的覆盖范围

本仓库同时跟踪 Anthropic 官方的 [Claude Code 企业网络配置](https://code.claude.com/docs/en/corporate-proxy) 和 [Claude Desktop 网络访问要求](https://code.claude.com/docs/en/desktop)。Desktop 文档明确列出 `claude.app` 及其子域名、`*.claudeusercontent.com` 和 `*.claudemcpcontent.com`；Claude Code 文档还列出 `sso.claude.com`、GitHub、npm、Google Storage、Datadog 和 Homebrew 等依赖。

为避免把大量与 Claude 无关的 GitHub、npm、Google Storage 等流量也送进 Claude 策略组，本仓库：

- 在 `data/claude/official.txt` 中保存官方两份文档里可移植的域名，便于审计和自动发现变化；
- 默认生成的 Claude 规则覆盖核心域名与经过筛选的专属兼容依赖；
- 使用后缀规则覆盖同根子域名，对共享 CDN 只匹配具体租户主机：

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

`claude.app` 来自 Anthropic 官方 Desktop 网络要求；`claude.dev` 是 Claude 官方开发者博客，属于相关站点，但不是 Claude Code 必需的 API 端点。官方文档中的 `sso.claude.com` 已由 `claude.com` 后缀覆盖；`assets-proxy.anthropic.com` 已由 `anthropic.com` 后缀覆盖。

GitHub、GitHub Raw、npm、Google Storage、Datadog 和 Homebrew 是官方文档列出的共享依赖，不默认塞进 Claude 专属规则，避免代理大量无关流量。它们通常应由通用 GitHub / Google / npm 规则处理。

`claudemcpclient.com` 和精确的 Bunny CDN 租户主机属于人工筛选的社区兼容补充，不是官方网络表中的条目。来源与证据强度见[规则对比记录](docs/rule-comparison-2026-09-13.md)。

### 网络依赖与账号风险说明

官方文档中的“需要允许访问”不等于“所有域名都必须写入 Claude 专属代理规则”。当前核心规则已通过 Anthropic / Claude 域名后缀覆盖 API、登录、SSO、下载更新、MCP、Artifacts 和 Desktop CDN 等第一方主机。Claude Code 的插件市场与安装流程还可能访问共享服务：

| 官方列出的主机 | 用途 | 建议 |
|---|---|---|
| `github.com`、`raw.githubusercontent.com` | 插件/Marketplace、release notes | 优先由通用 GitHub 规则处理 |
| `registry.npmjs.org` | npm 插件及依赖安装 | 由通用 npm 规则处理；需要时再代理 |
| `storage.googleapis.com` | 插件元数据、旧版原生安装器更新 | 由通用 Google 规则处理；按安装方式决定 |
| `formulae.brew.sh` | Homebrew 安装的版本检查 | 仅 Homebrew 安装场景需要 |
| `http-intake.logs.us5.datadoghq.com`、`browser-intake-us5-datadoghq.com` | 可选遥测/错误报告 | 不是核心连接所必需，不应为了“防封号”强行加入 |
| `fonts.googleapis.com`、`fonts.gstatic.com` | Artifact 字体 | 可选；阻断后回退字体 |
| `cdnjs.cloudflare.com`、`cdn.jsdelivr.net`、`cdn.tailwindcss.com`、`code.jquery.com`、`unpkg.com` | Artifact 使用的前端库 | 仅在相关 Artifact 需要时处理 |

这些共享依赖应在需要时通过通用规则或按功能启用，不建议直接扩大为 `github.com`、`googleapis.com`、`cloudflare.com` 等大范围后缀并全部送进 Claude 专属策略组。官方文档也明确区分了必需主机、可选遥测和 Artifact 的可选第三方依赖。

**账号风险边界：** 没有可信的域名列表可以保证避免封号。代理规则解决的是连接和分流问题，不会改变账号是否符合 Anthropic 的支持地区、使用条款和自动化使用要求。不要把社区收录的域名或固定出口 IP 当作规避封禁/地区限制的保证；请以 [Anthropic Consumer Terms](https://www.anthropic.com/legal/consumer-terms) 和 [Supported Regions Policy](https://www.anthropic.com/legal/supported-regions) 为准。
## OpenAI 规则策略

OpenAI 部分继续以官方 `OpenAI/ChatGPT domains to allowlist` 为主，并保留少量经过筛选的历史兼容规则。官方列表的原始语义保存在 `data/official.txt`，兼容补充保存在 `data/supplemental.txt`。

OpenAI 官方 allowlist 的原意是“不要拦截”，并不代表所有域名在所有网络中都必须强制代理。本仓库只是把它们整理成方便代理客户端使用的规则集。

官方列表中的 `intercom.io`、`js.stripe.com`、`challenges.cloudflare.com` 等共享依赖会让其他网站访问相同主机时也命中 OpenAI 策略组。这是保留官方覆盖的取舍；默认不进一步扩大到整个 `stripe.com`、`auth0.com` 或 `sentry.io`。

本仓库比较了 VPSDance、v2fly、MetaCubeX 和 blackmatrix7 的 OpenAI / Claude 规则，只采纳范围明确、证据可追溯的补充，详见[2026-09-13 对比与优化记录](docs/rule-comparison-2026-09-13.md)。不通过默认进程规则、域名关键词或历史 IP 网段兜底整个应用的流量。

## Codex / ChatGPT WebSocket

OpenAI 官方要求部分 ChatGPT 和 Codex 功能能通过 **TCP 443** 建立安全 WebSocket。规则只能决定路由；代理、防火墙或安全网关仍需要允许标准 WebSocket 握手。

ChatGPT 语音还涉及 UDP 3478 和官方维护的 [语音 IP 列表](https://openai.com/chatgpt-voice.json)。本仓库的域名订阅不替代 UDP、防火墙和 IP 路由配置；出现“文字可用、语音不通”时应单独检查这些条件。

验证实际效果时，在客户端连接日志中确认登录、流式回复、上传/下载分别命中预期规则和出口；Claude 的 MCP Apps、插件安装和 ChatGPT 语音再按使用情况测试。比较两套规则时保持节点、DNS、客户端版本相同。规则数量、仓库热度和自动更新频率都不能证明速度更快或连接更稳定。

## SSL / TLS 证书错误

OpenAI 和 Claude 的企业网络文档都涉及企业代理、CA 与 TLS 场景。正常的 Clash/Surge 路由不应替换服务端证书；如果出现证书异常，应重点排查 HTTPS 解密、TLS inspection、安全网关重签证书等行为。

## 自动更新机制

GitHub Actions 每天 **UTC 00:20（北京时间约 08:20）** 检查一次，也支持手动运行。

```text
OpenAI 官方 allowlist ─┐
                       ├─ 解析 + 校验 ─→ 有变化 ─→ 自动创建/更新 PR
Anthropic 网络要求 ───┘                         ↓
                                      人工确认后再 Merge
```

Pull Request 还会自动执行测试，但不会在 PR 流程里访问官方网站或自动修改规则。

### 安全保护

自动化会检查：

- OpenAI 官方 allowlist 标题与最低规则数量；
- OpenAI 核心域名是否仍然存在；
- Anthropic `Network access requirements` 表格是否仍然可解析；
- Claude 核心域名是否仍然存在；
- 遇到新的、不兼容的通配符格式时直接失败，而不是静默生成错误规则；
- 所有输出先完整生成，再原子替换文件。

## 本地检查

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/update.py --no-fetch
python scripts/update_claude.py --no-fetch
```

需要主动检查官方页面时：

```bash
python scripts/update.py
python scripts/update_claude.py
```

## 项目结构

```text
data/
├── official.txt                 # OpenAI 官方快照
├── supplemental.txt             # OpenAI 人工补充
└── claude/
    ├── official.txt             # Anthropic 官方网络要求快照
    └── supplemental.txt         # Claude 路由根域名
rules/
├── OpenAI.list
├── OpenAI.yaml
├── OpenAI-Surge.list
├── Claude.list
├── Claude.yaml
├── Claude-Surge.list
├── MapleStory.list
├── MapleStory.yaml
└── MapleStory-Surge.list
scripts/
├── update.py
└── update_claude.py
tests/
├── test_update.py
├── test_integration.py
└── test_claude.py
.github/workflows/
└── check-update.yml
```

详细来源与筛选规则见 [`sources.md`](sources.md)。

## 说明

本项目不是 OpenAI、Anthropic 或 Nexon 官方项目。规则用于网络路由和兼容性配置，请根据自己的网络环境和当地要求使用。
