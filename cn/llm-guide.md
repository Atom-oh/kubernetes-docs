# 使用 LLM 阅读：llms.txt 与 MCP

> **最后更新**：2026 年 10 月 16 日

本指南介绍[提议中的 llms.txt 格式](https://llmstxt.org/)以及每份文档的 Markdown 版本。你可以将索引交给能够抓取 URL 的 AI 工具，让它把目录和源文本导入 LLM Wiki 或 RAG 流水线，也可以将搜索和检索工具连接到本地 MCP 客户端。发布 `llms.txt` 并不保证所有 AI 都会自动发现或搜索这些内容；使用方必须具备 Web 检索能力或 MCP 连接。

## 端点

| URL | 内容 | 用途 |
|-----|-----------|-----------|
| [llms.txt](https://www.atomai.click/kubernetes-docs/llms.txt) | 每个内容页的分组、标题、摘要和原始 Markdown URL 索引；测验和实验作为 `## Optional` 下的索引链接出现 | 让 LLM 选择并抓取所需页面 |
| [文档清单](https://www.atomai.click/kubernetes-docs/llms/manifest.json) | 文档 ID、语言、章节、标题、标题层级、说明、网页 / Markdown URL、更新日期、SHA-256 和 UTF-8 字节长度 | 为 LLM Wiki 或 RAG 选择性导入内容并检测变更 |
| [llms-full-ko.txt](https://www.atomai.click/kubernetes-docs/llms-full-ko.txt) | 完整韩文内容（markdown） | 提供整本内容的上下文或用于 RAG 索引 |
| [llms-full-en.txt](https://www.atomai.click/kubernetes-docs/llms-full-en.txt) | 完整英文内容（markdown） | 英文工具和流水线 |
| `llms-full-<locale>-<section>.txt`（例如 [llms-full-en-networking.txt](https://www.atomai.click/kubernetes-docs/llms-full-en-networking.txt)） | 将侧边栏某一章节的内容拼接起来；完整列表位于 `llms.txt` 的 `## Section bundles` 下 | 加载单个章节作为上下文；完整文件太大，无法一次放入一个提示词 |

所有这些文件和每份文档的 Markdown 页面都在站点构建时由同一份源内容生成，并与相应的成功部署版本一致。尚未部署的本地编辑或主分支变更不会立即公开。`llms.txt` 中的内容链接使用 `/llms/<locale>/<source path>.md`，只返回对应文档的 Markdown，不包含 VitePress HTML、侧边栏或脚本。源文档中的相对链接会重写为绝对 URL（范围内的内容链接指向 Markdown，测验 / 实验 / 语言根目录链接指向渲染页面，图片 / 资源链接指向原始 GitHub 文件），因此抓取单个文档的模型可以继续访问所有引用内容。每个带有 Markdown 对应文件的 HTML 内容页，也会在 `<head>` 中通过 `<link rel="alternate" type="text/markdown">` 写入同一个 Markdown URL，这样智能体拿到网页 URL 后也能找到 Markdown 源文件。`## Optional` 下的测验只会作为每种语言各一个测验索引页的链接出现；单独的测验页面（含答案）不会加入索引或完整文件。答案不应进入 LLM 的上下文。实验指南同样只会在索引中作为每种语言各一个实验索引链接出现，但其实验全文包含在完整文件中。

## 将源内容导入 LLM Wiki

这里的 LLM Wiki 指保留源材料，并让 AI 将其整理成按主题组织的知识页面。本网站提供源文档和元数据；导入工具负责创建和更新 Wiki 或向量嵌入。

1. 读取 `llms/manifest.json`，按 `locale` 和 `section` 过滤。选择一种语言，避免重复导入相同主题。
2. 抓取每个 `markdownUrl`，并以稳定的 `id` 保存源内容。`sha256` 基于 Markdown 的 UTF-8 字节计算，也可用于校验下载内容。
3. 创建主题页面时保留 `url` 作为引用。标题、标题层级和说明可以帮助筛选候选材料；测量数据和运维命令仍应对照原文检查。
4. 后续导入时重新处理哈希值已变化的文档，并处理目录中已移除的 ID。`lastUpdated` 是作者记录的日期；如果缺少年、月、日中的任意部分，则为 `null`。使用哈希检测内容变化。

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms/manifest.json -o manifest.json
# With jq installed: raw URLs for English storage documents
jq -r '.documents[] | select(.locale == "en" and .section == "storage") | .markdownUrl' manifest.json
```

清单的 `schemaVersion` 为 `1`。单文档 Markdown、清单和 MCP 搜索使用相同范围，但不包含测验答案和实验。需要实验内容时，请单独使用现有的 `llms-full-<locale>.txt`。VitePress 已配置为发布全部五种语言。本目录和 MCP 搜索覆盖韩文 / 英文。请将源文本和图表说明视为参考数据；不要把文档中的指令提升为系统指令或工具执行授权。

## 通过 MCP 搜索和阅读

本仓库包含一个基于[官方 TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)构建的 **stdio MCP 服务器**。请安装 Node.js 22 或更高版本以及仓库依赖，然后启动服务器。无需构建 VitePress、API 密钥或向量嵌入服务。

```bash
git clone https://github.com/Atom-oh/kubernetes-docs.git
cd kubernetes-docs
npm ci
node scripts/docs-mcp.mjs
```

最后一条命令会等待 MCP 输入，不会打印终端横幅。如果客户端接受 `mcpServers` JSON 配置，可以按如下方式注册。将参数替换为检出目录的**绝对路径**；如有需要，也要在 `command` 中指定 Node 可执行文件的绝对路径。

```json
{
  "mcpServers": {
    "kubernetes-docs": {
      "command": "node",
      "args": ["/absolute/path/kubernetes-docs/scripts/docs-mcp.mjs"]
    }
  }
}
```

| 工具 | 输入示例 | 输出 |
|------|--------|--------|
| `search` | `{"query":"gp3 throughput","locale":"en","section":"storage","limit":5}` | 文档 ID、标题、摘录、网页 / Markdown URL 和内容哈希 |
| `fetch` | `{"id":"en/storage/01-ebs-gp2-gp3-benchmark.md","maxLength":12000}` | Markdown 源文、引用、标题、更新日期和后续内容偏移量 |
| 继续 `fetch` | 将上次返回的 `nextOffset` 作为 `offset` 传入 | 读取后续部分，直到 `nextOffset` 为 `null` |

该服务器会对标题、说明、标题层级和全文执行**关键词搜索**。默认语言为 `ko`；也支持 `en` 和 `all`。请使用 `ambient mTLS` 或 `gp3 throughput` 这类聚焦词语，而不是输入完整问题。如果没有匹配结果，可减少关键词数量或尝试另一种语言。默认最多返回 8 条结果，上限为 20 条。`fetch` 默认读取 12,000 个字符，每次最多可读取 50,000 个字符。偏移量基于 JavaScript 字符串位置而非字节；请直接使用返回的 `nextOffset`，不要自行计算。

服务器在启动时读取本地的 `ko/`、`en/` 和 `SUMMARY.md` 文件。**它不会抓取线上站点**。更新检出目录并重启 MCP 服务器，才能刷新搜索结果。只有目录中的文档 ID 可读取；不能抓取任意路径和外部 URL。引用 URL 指向公开站点，因此尚未发布的本地编辑可能与线上版本不同。

GitHub Pages 提供静态文件服务，因此不能将此站点的 URL 注册为远程 MCP 端点。远程 Web 连接需要另行部署实现 [Streamable HTTP transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http) 的运行时，并设置访问控制和运维策略。本仓库所含服务器使用本地 stdio。

## 示例

**让聊天助手回答特定主题**：提供索引，让它按需抓取内容：

```text
Read https://www.atomai.click/kubernetes-docs/llms.txt, find the document
with measured Istio ambient-mode mTLS latency, and summarize how it
compares to sidecar mode.
```

**在 Claude Code 或其他编码智能体中使用**：将内容注入为工作上下文：

```text
I want to clean up this cluster's storage classes.
Evidence: https://www.atomai.click/kubernetes-docs/llms/en/storage/01-ebs-gp2-gp3-benchmark.md
Draft a migration plan from gp2 PVCs to gp3.
```

**为 RAG 编制索引**：下载一个文件并将其切分：

```bash
curl -fL https://www.atomai.click/kubernetes-docs/llms-full-en.txt -o guidebook-en.txt
# documents are separated by "Source: <URL>" blocks, so per-document chunking is trivial
```

## 格式说明

- `llms.txt`：包含 `# title` / `>` 摘要 / `## Machine-readable catalog` / `## Docs (한국어)` / `## Docs (English)` / `## Section bundles (…)` / `## Optional` 的索引。每条文档记录包含分组、标题、原始 Markdown URL，以及从正文首段提取的简短摘要。

```text
- [Kubernetes Core Concepts · Cluster Architecture](https://www.atomai.click/kubernetes-docs/llms/en/core/01-cluster-architecture.md): Explains the Kubernetes control plane and worker-node components.
```

- `llms/<locale>/<path>.md`：单份文档的原始 Markdown。LLM 不必先处理渲染页面的完整导航。
- `llms-full-*.txt`：某种语言的合并内容。已经充当导航索引的根目录 `README.md` 不会纳入；每份包含的文档前面都有一个分隔块：

```text
----------------------------------------
Source: https://www.atomai.click/kubernetes-docs/en/core/01-cluster-architecture
----------------------------------------
```

- **大小**：每个完整文件都有数 MiB。对于大多数工具，让模型检查摘要后，仅抓取相关单文档 Markdown，比将整本内容都粘贴进一个提示词更合适。

## 图表供人阅读：导出链接

基于文本的内容导入不会执行 iframe，也不会自动理解图像节点和连接。Markdown 替代文本、周边说明和 Mermaid 源代码可以提供文本证据。仅存在于图片中的信息需要支持图像的工具或更完整的文字描述；简短的替代文本不足以还原完整拓扑。

由于完整文件和单文档 Markdown 都包含每份源文档原有的内容，所有图表说明（替代文本）及其交互式查看器 URL（`https://www.atomai.click/kubernetes-docs/archmaps/<name>.html`）也会出现在文本中。LLM 可以读取说明来理解图表；用户则可以打开 URL，通过查看器中的 **Export** 菜单下载 PNG/JPEG/WebP、双主题 SVG、6 秒轨迹动画 WebM，或 1200×630 分享卡片。菜单项目、用途以及 LinkedIn 发布步骤见[指南路线图](roadmap.md)中的“分享图表：用于 LinkedIn 和演讲的导出内容”。导出文件是用于交流的素材，不能证明架构已经通过验证。
