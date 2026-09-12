# OpenAI-Rules

面向 **OpenAI / ChatGPT / Codex** 的网络规则集，提供 Clash Party、Mihomo/Clash 和 Surge 三种订阅格式。

规则以 OpenAI 官方网络建议中的 allowlist 为主，并保留少量经过筛选的历史兼容规则。仓库每天自动检查官方清单；发现变化时只创建 Pull Request，**不会自动合并到 `main`**。

## 订阅地址

| 客户端 | 订阅地址 |
| --- | --- |
| Clash Party / text rule-set | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list` |
| Mihomo / Clash classical rule-provider | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.yaml` |
| Surge RULE-SET | `https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list` |

## Clash Party

如果你是在 Clash Party 的“外部资源 / 规则集”界面添加规则，直接使用：

```text
https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list
```

该文件只有规则本身，不包含策略组名称。最终由你的 Clash Party 配置决定命中后走哪个策略组，例如 `PROXY`、`节点选择` 等。

如果通过 Mihomo 配置文件引用文本规则，可以使用类似：

```yaml
rule-providers:
  openai-text:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI.list
    path: ./ruleset/openai.list
    interval: 86400

rules:
  - RULE-SET,openai-text,PROXY
```

请把 `PROXY` 换成你自己的策略组名称。

## Mihomo / Clash

推荐直接使用 YAML rule-provider：

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

## Surge

在 `[Rule]` 中使用：

```ini
RULE-SET,https://raw.githubusercontent.com/sevenday/OpenAI-Rules/main/rules/OpenAI-Surge.list,Proxy
```

将 `Proxy` 替换成你的 Surge 策略名称。

## 这些域名是不是都必须走代理？

不是。OpenAI 官方文档的原意是这些域名应被 **allowlist（不要拦截）**。本仓库只是把它们整理成代理客户端可以订阅的规则，方便需要统一代理 OpenAI 流量的用户使用。

如果你的网络本来就可以正常直连 OpenAI，没有必要仅因为官方列入 allowlist 就强制代理所有相关域名。

## Codex / ChatGPT WebSocket

OpenAI 官方目前明确要求部分 ChatGPT 和 Codex 功能能够通过 **TCP 443** 建立安全 WebSocket：

- ChatGPT：`wss://ws.chatgpt.com`
- Codex：`wss://chatgpt.com/`

本规则中的 `DOMAIN-SUFFIX,chatgpt.com` 已覆盖这两个主机，但你的代理、防火墙或安全网关仍需要允许标准的 `Upgrade: websocket` 握手。

## SSL / TLS 证书错误

如果出现类似：

> Looks like ... is the wrong SSL certificate

OpenAI 官方指出，**SSL inspection / TLS inspection / HTTPS 解密** 可能导致证书错误或连接异常。代理路由本身和 HTTPS 解密不是一回事：正常的 Clash/Surge 转发不应替换 OpenAI 的 TLS 证书。

因此遇到证书问题时，应重点检查网络中是否存在 TLS/SSL inspection、HTTPS 解密、安全网关重签证书等行为，而不是一味增加域名规则。

## 规则来源与筛选原则

- 官方来源：OpenAI Help Center 的 `OpenAI/ChatGPT domains to allowlist`
- 兼容补充：参考 blackmatrix7 `ios_rule_script` 的历史 OpenAI 规则
- 官方规则原始语义保存在 `data/official.txt`
- 人工筛选的兼容项保存在 `data/supplemental.txt`
- 三种最终订阅文件由 `scripts/update.py` 从同一数据源生成

详细来源与排除规则见 [`sources.md`](sources.md)。

## 自动更新机制

GitHub Actions 每天 **UTC 00:20（北京时间约 08:20）** 检查一次，也可以手动运行。

流程如下：

```text
OpenAI 官方 allowlist
        ↓
解析 + 安全校验
        ↓
与当前 data/official.txt 比较
        ↓
无变化 → 结束
有变化 → 重新生成三种规则 → 自动创建/更新 PR
        ↓
人工检查后再 Merge
```

自动化设置了安全保护：如果官方网页标题无法定位、解析出的规则数量异常、核心域名缺失或规则格式异常，脚本会失败，现有规则不会被覆盖。

### 首次启用自动 PR 时

如果 Action 能运行但创建 PR 时提示权限不足，请在仓库：

**Settings → Actions → General → Workflow permissions**

确认 GitHub Actions 有写权限，并启用允许 GitHub Actions 创建 Pull Request 的选项。仓库工作流自身已声明：

```yaml
permissions:
  contents: write
  pull-requests: write
```

## 本地检查

```bash
python -m pip install -r requirements.txt
pytest -q
python scripts/update.py --no-fetch
```

`--no-fetch` 只使用仓库当前的 `data/official.txt` 重建三种规则，不访问 OpenAI 网站。

需要从 OpenAI 官方页面检查更新时：

```bash
python scripts/update.py
```

## 项目结构

```text
data/
├── official.txt
└── supplemental.txt
rules/
├── OpenAI.list
├── OpenAI.yaml
└── OpenAI-Surge.list
scripts/
└── update.py
tests/
└── test_update.py
.github/workflows/
└── check-update.yml
```

## 说明

本项目不是 OpenAI 官方项目。规则用于网络路由和兼容性配置，请根据自己的网络环境和当地要求使用。
