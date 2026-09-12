# OpenAI-Rules 设计说明

日期：2026-09-12

## 目标

建立一个长期维护的 OpenAI / ChatGPT / Codex 网络规则仓库，统一维护一份标准规则数据，并自动生成以下三种订阅格式：

1. Clash Party 外部资源：`rules/OpenAI.list`
2. Mihomo / Clash rule-provider：`rules/OpenAI.yaml`
3. Surge RULE-SET：`rules/OpenAI-Surge.list`

仓库采用“半自动维护”模式：每天检查 OpenAI 官方网络建议页面；如果官方域名发生变化，自动生成更新分支和 Pull Request，但不自动合并到 `main`。

## 数据来源

### 官方来源

主来源：

- https://help.openai.com/en/articles/9247338

脚本只解析页面中 `OpenAI/ChatGPT domains to allowlist` 区域的域名。官方页面当前同时明确要求 ChatGPT / Codex 的 WebSocket 通过 TCP 443，并提示 TLS/SSL inspection 不应重写或中断连接；这些要求会在 README 中说明，但它们不是域名规则本身，因此不会被错误转换成 DOMAIN 规则。

### 补充来源

参考：

- https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/OpenAI/OpenAI.list

补充规则仅用于弥补官方 allowlist 未明确列出的历史依赖或第三方基础设施，并由人工维护，不会因为官方页面未出现就自动删除。

## 规则分层

### `data/official.txt`

保存从 OpenAI 官方页面解析到的原始域名语义：

- `*.example.com` 规范化为 `DOMAIN-SUFFIX,example.com`
- `host.example.com` 规范化为 `DOMAIN,host.example.com`

排序稳定、去重，并保留来源说明。该文件由自动检查流程更新。

### `data/supplemental.txt`

保存人工筛选的兼容补充规则。初始只纳入相对明确、范围可控的 OpenAI 相关依赖，例如：

- Arkose Labs 的 OpenAI 验证相关域名
- ChatGPT / LiveKit 相关域名
- Statsig 相关域名
- OpenAI 专用 Azure CDN / Blob / Imgix 域名
- 明确的 Cloudflare / Datadog 单主机依赖

以下过宽规则默认不纳入正式规则：

- `DOMAIN-KEYWORD,openai`
- `IP-ASN,20473`
- blackmatrix7 中的固定历史 IP-CIDR
- `DOMAIN-SUFFIX,auth0.com`
- `DOMAIN-SUFFIX,stripe.com`
- `DOMAIN-SUFFIX,sentry.io`

此外，对 `algolia.net`、`launchdarkly.com`、`segment.io`、`observeit.net`、`identrust.com` 这类可能被大量其他服务共用的宽泛第三方后缀，默认不加入；如后续通过实际连接日志证明必要，再单独评估。

## 生成逻辑

`scripts/update.py` 同时承担两项职责：

1. 抓取并解析 OpenAI 官方 allowlist，生成或更新 `data/official.txt`
2. 合并 `official.txt` 与 `supplemental.txt`，生成三个客户端格式

### Clash Party

`rules/OpenAI.list` 使用纯规则行：

```text
DOMAIN-SUFFIX,openai.com
DOMAIN-SUFFIX,chatgpt.com
DOMAIN,challenges.cloudflare.com
```

不包含策略组名，交由 Clash Party 的 RULE-SET 引用处指定策略。

### Mihomo / Clash

`rules/OpenAI.yaml`：

```yaml
payload:
  - DOMAIN-SUFFIX,openai.com
  - DOMAIN-SUFFIX,chatgpt.com
  - DOMAIN,challenges.cloudflare.com
```

### Surge

`rules/OpenAI-Surge.list` 使用 Surge RULE-SET 可直接订阅的纯规则行格式，与 Clash Party 文件独立生成，避免未来客户端语法差异互相影响。

## 去重与最小化

生成器进行两级处理：

1. 完全相同规则去重
2. 对明显被更宽 `DOMAIN-SUFFIX` 覆盖的同域精确 `DOMAIN` 规则，可在输出文件中省略，但 `data/official.txt` 仍保留官方原始语义

这样既能保持官方变化可审计，又避免订阅文件无意义膨胀。

## 安全保护

自动化必须防止网页结构变化导致规则被清空或大规模误删：

- 如果官方 allowlist 标题无法定位，脚本直接失败
- 如果解析出的域名数量低于安全阈值，脚本直接失败
- 如果解析结果出现异常格式，脚本直接失败
- 任何失败都不得覆盖现有 `data/official.txt` 或输出规则
- supplemental 规则永不由抓取逻辑自动删除

## GitHub Actions

`.github/workflows/check-update.yml`：

- 每天定时运行一次
- 支持 `workflow_dispatch` 手动运行
- 安装 Python 依赖
- 执行 `scripts/update.py`
- 如果没有文件变化，正常结束且不创建 PR
- 如果有变化，使用独立分支创建或更新一个 Pull Request
- PR 标题固定为类似 `chore: update OpenAI network rules`
- PR 正文列出官方规则变化摘要，并注明需要人工确认后合并
- 不开启 auto-merge

建议定时为每天北京时间上午约 08:20（UTC 00:20）。

## README

README 需要包含：

- 三种订阅地址
- Clash Party、Mihomo、Surge 的最小配置示例
- 官方来源与补充来源说明
- “官方 allowlist 不等于所有域名都必须代理”的说明
- ChatGPT / Codex WebSocket TCP 443 要求
- SSL/TLS inspection 可能导致证书错误的提示
- 半自动 PR 更新机制说明

## 仓库结构

```text
OpenAI-Rules/
├── data/
│   ├── official.txt
│   └── supplemental.txt
├── rules/
│   ├── OpenAI.list
│   ├── OpenAI.yaml
│   └── OpenAI-Surge.list
├── scripts/
│   └── update.py
├── .github/
│   └── workflows/
│       └── check-update.yml
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-09-12-openai-rules-design.md
├── README.md
└── sources.md
```

## 验收标准

实施完成后应满足：

1. 三个规则文件均可由同一份数据稳定生成
2. 三种格式语法正确且可被对应客户端订阅
3. 当前 OpenAI 官方 allowlist 全部被 `data/official.txt` 表达
4. 选定的补充规则独立可审计
5. 脚本重复运行结果稳定，不产生无意义 diff
6. 官方无变化时 GitHub Actions 不创建 PR
7. 官方有变化时只创建 PR，不自动合并
8. 解析失败时不覆盖旧规则
9. README 提供可直接复制使用的订阅地址和配置示例
10. 仓库中清楚记录规则来源、筛选原则和已排除的宽泛旧规则
