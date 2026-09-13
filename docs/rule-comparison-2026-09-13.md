# OpenAI / Claude 规则对比与优化

检查日期：2026-09-13。基线：本仓库 `eccc7648f9ac268f77fd6c39748c2ca20f3ad79c`。

## 结论与验证边界

保留“官方网络要求 + 人工筛选的专属兼容依赖”的策略。VPSDance 适合发现候选域名，v2fly / MetaCubeX 适合交叉检查域名范围；不直接合并上游全部条目。

本次验证规则覆盖、匹配范围、生成器行为和输出一致性。没有使用用户账号、固定代理节点做登录、流式回复、上传下载、MCP Apps 或语音的前后对照测试，因此不声称某规则库更快、更稳定或可以规避账号限制。

## 固定版本比较

规则数排除空行、注释与 YAML 的 `payload:`。进程、IP、关键词、正则也各计一条；它们的覆盖范围不同，数量不能直接比较质量。

| 来源 | OpenAI | Claude / Anthropic | 本次判断 |
| --- | ---: | ---: | --- |
| 本仓库修改前 | 37 | 6 | 官方覆盖充分；缺少部分社区兼容条目，OpenAI 有冗余后缀 |
| 本仓库修改后 | 38 | 8 | 保留官方覆盖，补充范围较窄的条目 |
| [VPSDance](https://github.com/VPSDance/ai-proxy-rules/tree/942592770736b2b134fda8d13a2c6ce9a2a79910) | 51 | 49 | 多源汇总、客户端格式丰富；包含宽泛共享域名、进程规则、IP 网段及需复核的历史域名 |
| [v2fly](https://github.com/v2fly/domain-list-community/tree/5d939545c84e2a534f8e85ba6ffb2b51fa18fb76) | 23 | 8 | 域名范围相对集中；OpenAI 含正则以及部分待确认用途的域名 |
| [MetaCubeX](https://github.com/MetaCubeX/meta-rules-dat/tree/32f11ae6b233e34cfec618dc4ba546f80d454053) | 23 | 8 | 有 Mihomo classical 输出；与 v2fly 条目高度重合，不能作为独立实测证据 |
| [blackmatrix7](https://github.com/blackmatrix7/ios_rule_script/tree/0087bb74e91b335e17a79fd07a8514277f7d77b4) | 35 | 3 | 本次读取的两个文件内更新时间均为 2025-06-06，不能用仓库其他目录的活跃度证明这两份规则新鲜 |

对应文件：

- VPSDance：[OpenAI](https://github.com/VPSDance/ai-proxy-rules/blob/942592770736b2b134fda8d13a2c6ce9a2a79910/rules/surge/openai.list)、[Anthropic](https://github.com/VPSDance/ai-proxy-rules/blob/942592770736b2b134fda8d13a2c6ce9a2a79910/rules/surge/anthropic.list)。
- v2fly：[OpenAI](https://github.com/v2fly/domain-list-community/blob/5d939545c84e2a534f8e85ba6ffb2b51fa18fb76/data/openai)、[Anthropic](https://github.com/v2fly/domain-list-community/blob/5d939545c84e2a534f8e85ba6ffb2b51fa18fb76/data/anthropic)。
- MetaCubeX：[OpenAI](https://github.com/MetaCubeX/meta-rules-dat/blob/32f11ae6b233e34cfec618dc4ba546f80d454053/geo/geosite/classical/openai.yaml)、[Anthropic](https://github.com/MetaCubeX/meta-rules-dat/blob/32f11ae6b233e34cfec618dc4ba546f80d454053/geo/geosite/classical/anthropic.yaml)。
- blackmatrix7：[OpenAI](https://github.com/blackmatrix7/ios_rule_script/blob/0087bb74e91b335e17a79fd07a8514277f7d77b4/rule/Surge/OpenAI/OpenAI.list)、[Claude](https://github.com/blackmatrix7/ios_rule_script/blob/0087bb74e91b335e17a79fd07a8514277f7d77b4/rule/Surge/Claude/Claude.list)。

## 采纳的调整

| 服务 | 调整 | 依据与限制 |
| --- | --- | --- |
| OpenAI | 新增 `DOMAIN-SUFFIX,chat.com` | 本次网页检索访问 [chat.com](https://chat.com/) 跳转到 ChatGPT；v2fly、MetaCubeX、VPSDance 均收录。解决短域名入口未匹配的问题 |
| OpenAI | 新增 `DOMAIN,openaiassets.blob.core.windows.net` | v2fly、MetaCubeX、VPSDance 收录的 Azure Blob 精确主机；社区兼容补充，未验证具体资源请求，不扩大为整个 Azure Blob 后缀 |
| OpenAI | 将 `DOMAIN,chat.openai.com.cdn.cloudflare.net` 替换为 `DOMAIN-SUFFIX,openai.com.cdn.cloudflare.net` | 三个社区来源收录的限定 CDN 后缀；仍覆盖原有主机及该命名空间，未扩大至整个 Cloudflare CDN |
| OpenAI | 生成器删除已被上级覆盖的 `DOMAIN-SUFFIX,auth.openai.com` | `openai.com` 后缀已覆盖它。官方快照保留原始条目；修复的是输出去重，匹配范围不减少 |
| Claude | 新增 `DOMAIN-SUFFIX,claudemcpclient.com` | v2fly、MetaCubeX、VPSDance 均收录；作为社区兼容域名接受。本次未找到官方网络表中的该条目，也未完成登录后的 MCP 请求验证 |
| Claude | 新增 `DOMAIN,servd-anthropic-website.b-cdn.net` | 三个社区来源收录的专属 CDN 主机；仅精确匹配，未收录整个 `b-cdn.net`。本次 Anthropic 首页文本抓取未发现引用，因此保留为社区兼容条目，不宣称当前核心请求必需 |

这些社区来源存在继承关系。“三个列表都有”不等于三个独立网络抓包。所有补充记录在 supplemental 文件，后续可按真实连接日志复核或撤销。

Claude 官方快照本次重新抓取成功，只修正 `bridge...` 与 `browser...` 的排序，没有新增/删除域名。OpenAI 官方页已通过网页检索核对，但本机 Python 实时抓取遇到 TLS 连接中断；本次生成仍使用已提交的官方快照，不能把它称为本机实时更新成功。

## 不默认采纳的条目

| 候选类别 | 示例 | 原因与后续处理 |
| --- | --- | --- |
| 已不适合按历史关系归类 | `ai.com` | 当前 [ai.com](https://ai.com/) 展示独立 AI agent 服务，不能继续仅凭历史重定向关系分给 OpenAI |
| 已停止的独立产品 | `sora.com` | [OpenAI 官方页面](https://openai.com/index/sora/)说明 Sora 产品已于 2026-04-26 停止提供；不为当前 ChatGPT / Codex 分流默认扩展历史产品根域名 |
| 当前用途未充分验证 | `chatgpt.site`、`crixet.com`，VPSDance 中额外 Claude 名称域名及 MCP 生态网站 | 域名名字和社区收录不能证明属于服务必需流量；先核实归属与实际请求，保持候选状态 |
| 整个共享服务后缀 | `auth0.com`、`stripe.com`、`sentry.io`、`statsigapi.net`、`algolia.net` | 会把其他产品的认证、支付、遥测等流量一起送到 AI 出口；保留现有官方要求的更具体主机 |
| 共享开发工具与遥测 | `storage.googleapis.com`、GitHub、npm、Homebrew、通用 Datadog 主机 | 由通用规则处理；官方 Claude 快照仍保留这些要求用于审计 |
| 宽泛关键词 | `openai`、`datadog`、`sentry`、`sift` | 子串匹配会命中非目标服务的域名；不作为默认兜底 |
| 进程规则 | `Codex.exe`、`Claude.exe`、`cowork-svc.exe` | 应用访问的第三方网站也会被整体分流，且依赖平台和进程识别能力；只在明确需要应用全部流量同出口时单独配置 |
| 历史固定 IP / ASN / 大网段 | `24.199.123.28/32`、`64.23.132.171/32`、`IP-ASN,20473`，其他上游服务网段 | 不凭历史值或注册归属推断当前服务流量；如有直连 IP 或语音需求，另按官方当前网络要求验证 |
| 动态 WebPubSub | v2fly 的 `^chatgpt-async-webps-prod-\S+-\d+\.webpubsub\.azure\.com$` | 本仓库的跨客户端输出仅支持 DOMAIN / DOMAIN-SUFFIX；不能退化成整个 `webpubsub.azure.com` 或未锚定关键词。若日志证明确实需要，再新增有客户端范围说明和测试的可选规则 |
| 可选问卷 / 监控 | `openai.qualtrics.com` 及新增第三方遥测 | 没有改善核心连接的实测证据，暂不增加默认覆盖 |

## 验证与维护

本次已完成：现有 28 项测试通过，新增回归测试修复后完整 30 项通过；两份离线生成器重复运行均输出 `No changes.`；六份输出格式内容一致，修改前的全部域名匹配覆盖保留。Clash Party 附带的 Mihomo Meta v1.19.29（Windows amd64）配置检查通过，且在独立临时进程中实际加载全部六份 file provider，API 返回 OpenAI 各 38 条、Claude 各 8 条；检查后停止该临时进程。没有修改正在使用的 Clash Party 配置，也没有在 Surge 原生客户端执行验证。

1. 修复前运行现有测试；为嵌套后缀去重增加回归测试，先确认失败，再修复。同时检查相似字符串不跨域名标签误删。
2. 运行完整测试与两份 `--no-fetch` 生成命令；重复生成必须没有文件变化，三种格式内容一致。
3. 保持所有原有域名匹配覆盖；官方快照不因输出去重而删减。
4. 将两条服务规则放在可能提前命中的通用规则之前；按客户端连接日志检查真正使用的出口。
5. 后续排查保持同一节点、DNS 和客户端版本，分别对照登录、流式回复、上传下载、MCP 和语音。HTTP 403、DNS 能解析、TLS 能连接都不能单独证明完整服务可用。
6. 自动更新继续只追踪官方文档并创建待审 PR。社区补充需要定期人工复核；本次未新增社区自动合并或任何定时任务。
