# ResearchCopilot × Obsidian：长期知识库蓝图

状态：设计已定，用户的独立 Vault 已在 Obsidian 中打开并与 ResearchCopilot 本机连接；M8.V2a/V2b 已实现单条人工确认笔记与论文索引卡的预览和首次安全保存，M8.V3 已实现 Obsidian 外部编辑后的只读回读。针对“已连接但 Vault 为空”，M8.V4a 按[来源目录拆解](research/2026-10-09-obsidian-paper-catalog.md)增加可预览的 PDF 来源目录与 Bases 视图，不把来源条目冒充已确认研究笔记。网页内更新、自动合并和跨设备同步尚未实现。依据：[开源产品拆解](research/2026-10-04-obsidian-knowledge-vault.md)、[M8.V2b 验收](M8_V2B_VALIDATION.md)与[M8.V3 验收](M8_V3_VALIDATION.md)。

## 一句话定位

ResearchCopilot 是读论文与核对证据的工作台；Obsidian Vault 是**人工确认后的研究知识**的长期、可编辑、可迁移存储。这里的“数据库”是文件式知识库：Markdown 是记录，少量 YAML 属性是可筛选字段，Obsidian Bases 是视图，不把 Obsidian 当关系数据库服务器。未安装 Obsidian 时仍可直接编辑 Markdown，论文阅读功能不受影响。

这遵循 [Karpathy 的持久 wiki 构想](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)中“资料与逐渐积累的知识分层”的思想，但改变其写入权限：ResearchCopilot 的 AI 只能建议，用户决定哪些结论进入正式库。

## 权威边界

| 内容 | 权威位置 | Vault 是否保存 | 原因 |
| --- | --- | --- | --- |
| 论文原始 PDF | 设备上的原始 PDF，以 SHA-256 辨认版本 | 默认不复制；只存来源和指纹 | PDF 是证据，不是可编辑笔记；避免大文件同步与重复副本。 |
| 已确认论文卡、个人理解、重要问答、开放问题 | 用户选定 Vault 中的 Markdown | 是 | 这是要跨时间和设备积累的知识。 |
| 论文元数据、阅读状态、标签 | Vault 论文笔记的 YAML 属性 | 是 | 供 Obsidian Bases 与 ResearchCopilot 使用同一份字段。 |
| AI 草稿、未审定译文/回答、完整会话 | 应用本地运行数据 | 默认否 | 避免把模型输出误认为人的确认知识；可日后显式归档。 |
| PDF 抽取文本、Embedding、检索索引、模型缓存、阅读页码 UI 状态 | 应用本地可重建数据 | 否 | 与知识内容不同，不应占据可移植 Vault。 |
| 密钥与设备绝对路径 | 各设备本地配置 | 绝不 | 隐私与跨平台。 |

同一种**已确认笔记**只能有一个权威副本：Vault 文件。旧 `artifacts/` 卡片/导出可作迁移来源或快照，不作为同时可写的第二份正式笔记。若 Vault 暂时不可用，应用保留阅读能力，但不假称正式入库成功。

## 核心身份与引用约定

1. 新增不可变的 `paper_uid`（导入时生成一次），不从文件名、路径、DOI 或模型推断生成。现有路径哈希 `paper_id` 保留为迁移别名，旧阅读记录需有安全映射，不能破坏历史数据。
2. `pdf_sha256` 指向实际字节版本。相同论文的新 PDF 版本可以沿用 `paper_uid`，但引用必须显示其产生时的 PDF 指纹；指纹不符时要求重新核对页码。
3. 每条正式阅读笔记有独立 `record_uid`；从单篇笔记升级为跨论文主题笔记仍可追溯原记录。
4. 引用记录 `paper_uid`、`pdf_sha256`、**从 1 开始的 PDF 文件页序号**、原文短引和可选块/坐标锚点。印刷页码仅作为额外展示，不替代 PDF 页序号。
5. DOI、arXiv ID、标题、作者是可编辑书目信息与去重线索，不是唯一键；同名文件或无 DOI 不影响身份。

## 建议的最小 Vault 结构

用户显式选择一个已有 Vault 或新建一个 Vault；不把它偷偷放在项目的 `artifacts/` 下，也不嵌入另一个已有 Vault。正式知识仍在 `Papers/` 与 `Notes/`；M8.V4a 的 `Sources/` 仅存已导入 PDF 的可核对来源元数据，`.base` 只是过滤视图。

```text
ResearchCopilot-Vault/
  Sources/                # 已导入 PDF 的来源目录；不代表人工确认
    <paper_uid>.md
  Papers/                 # 一篇论文一份正式卡片
    <paper_uid>.md
  Notes/                  # 用户确认的心得、重要问答、待解问题
    <record_uid>.md
  ResearchCopilot 论文库.base  # Obsidian Bases 的来源目录表格
  Views/                  # 后续可选：Obsidian Bases 的 .base 视图
  index.md                # 后续可选：人工可读的知识入口
  log.md                  # 后续可选：写入与修订时间线
```

`Concepts/` 和 `Topics/` 只有在至少两篇论文已有可核查的确认记录、并且跨论文证据门槛通过后才启用；不能因为模型能生成综述就提前扩张目录。Obsidian 的 [Properties](https://obsidian.md/help/properties) 适合短字段；长解释、公式和引文保留在正文。

论文笔记最小示例（字段名称在实现前由测试固定）：

```markdown
---
schema_version: 1
kind: paper
uid: paper-7e2c
title: Attention Is All You Need
reading_status: reading
tags:
  - transformer
pdf_sha256: "<64 位 SHA-256>"
source_url: "https://arxiv.org/abs/1706.03762"
---

# Attention Is All You Need

## 我确认的核心理解

（由我审核后填写；AI 草稿不会自动出现在这里。）

## 关键证据与笔记

- [[Notes/record-9a4d|自注意力为何替代循环层]]
```

笔记正文保存人的理解与原文依据，例如：`PDF 第 3 页 · paper_uid · pdf_sha256 · 原文短引`。模型的推断、论文明确陈述、用户自己的判断须分开标记。机器字段只提供可查找身份，不把整段自然语言硬塞入 YAML。示例 UID 是格式说明，不是对现有论文的实际赋值。

一条正式阅读笔记的最小字段为 `schema_version`、`kind: reading_note`、`uid`、`paper_uid`、`review_status: confirmed`、`created_at`；正文分为“我的理解”“原文依据（含 PDF 页序号、PDF 指纹、短引）”“仍待核对”。如笔记来自某次提问，还保留来源 `reading_record_uid` 和 `reading_session_uid`，但不把整段聊天记录复制进 Vault。`pdf_sha256` 与页序号属于每条引用，而不只属于论文卡片：同一论文更新 PDF 时，旧引用不会悄悄指向新版本的同一页。

## 使用流程与界面分工

```text
导入 PDF / 认领论文身份
  → 预览并确认来源目录入库；在 Obsidian Bases 中查看待读论文
  → 在 ResearchCopilot 阅读、翻译、提问和查看原文页证据
  → AI 给出候选；用户编辑、确认具体记录
  → 预览即将写入或修改的 Vault 文件差异
  → 安全保存到 Vault，并在阅读器显示“已入库”及打开笔记入口
  → 在 Obsidian 中浏览 Bases、补写观点、建立笔记链接
  → 阅读器重新读取 Vault 修改；证据引用仍可回到 PDF
```

- ResearchCopilot 负责实时阅读和原文核验；不复制一套完整 Obsidian 编辑器。
- Obsidian 负责长期组织：按阅读状态、标签、主题、开放问题筛选；一个论文可出现在多个主题里，不复制卡片。
- 原文与已确认知识是两条检索通道。问“论文写了什么”优先读 PDF；问“我以前怎么看这个问题”可查 Vault，但回答要标明“我的笔记”而非论文原文。
- 若外部笔记链接使用 Obsidian 专有形式，也保留普通 Markdown 可读文字与稳定 UID；应用内部跳转不得仅依赖 Obsidian URI。

## 双向读写、安全与同步

首版写入采用白名单目录与字段校验、写前文件哈希比较、差异预览、临时文件原子替换；若 Obsidian/同步工具在用户确认后又修改文件，则停止写入并显示冲突，不静默覆盖或生成重名副本。应用读取外部修改时不自动把 `status`、引用和新字段当作可信：schema 校验失败要标记为需修复，不删除原文件。笔记删除与合并都要单独确认。

源码继续用现有 Git 仓库同步；Vault 可由用户选择**单独的私有 Git 仓库**或其他适合 Markdown 的同步/备份方式，两者不能无意混入源码仓库。同步方式需单一、可恢复，并在双设备并发编辑时检测冲突。PDF 是否同步由用户另定；模型、密钥、索引和 `.venv` 不跨设备同步。Vault 中不写 `/Users/...` 或 `C:\\...`；每台电脑通过 `paper_uid + pdf_sha256` 关联本地 PDF。没有匹配 PDF 时仍能看笔记，但回原文显示“此设备缺少对应原文”。

## 与当前代码的接缝

- `paper_library.py`：目前 `paper_id` 是相对路径 SHA-256 的前 16 位，不能直接当跨设备知识身份；先建立 `paper_uid` 与旧 ID 对照、迁移预览，再切换引用。
- `reading_history.py`：确认状态与引用可复用；当前 JSON/导出保持兼容，入库前核对对应论文 UID 与 PDF 指纹。
- `paper_card_compiler.py`：重用“只用已确认记录生成卡片”和拒绝覆盖思路；将单向 `artifacts/` 导出改为面向 Vault 的候选差异，不自动覆盖 Obsidian 编辑。
- `KnowledgeArtifact` 继续表示最终知识产物；Vault 只是它的存储适配器。不要再造一套“Obsidian 专用问答/论文/引用”业务模型。

## 阶段划分与完成门槛

| 阶段 | 范围 | 退出条件 |
| --- | --- | --- |
| M8.V0 蓝图 | 权威边界、schema、稳定身份、迁移/冲突计划 | 本文与开源拆解完成；不碰用户 Vault。 |
| M8.V1 只读 | 用户选 Vault；校验笔记；展示旧导出迁移预览 | 不写 Vault；坏 YAML、重复 UID、缺 PDF 有清楚提示。 |
| M8.V2 确认写入 | V2a/V2b 已完成：一条笔记与论文索引卡的预览、首次安全创建 | 预览内容、原子创建、已有文件拒绝覆盖；不调用模型，不复制第二份知识正文。 |
| M8.V3 回读 | 已完成只读回读：Obsidian 中改动后重新读取即可见 | 当前字节与 SHA-256、无旧缓存误覆盖、跨论文与无效文件拒绝；网页写回另立版本冲突里程碑。 |
| M8.V4a 来源目录 | 已完成：预览后创建 `Sources/` 元数据与 Bases 视图 | 可在 Obsidian 中查看已导入的待读论文；无 AI 结论、无 PDF 复制、无自动覆盖。 |
| M8.V4 后续组织 | 索引/lint、主题关系 | 待真实确认笔记积累后再做；主题结论仍须逐条原文证据。 |
| M8.V5 双设备 | 私有同步演练与恢复 | 同一 UID、不暴露密钥、缺 PDF 安全降级、冲突可恢复。 |

M8.4d 的跨论文**答案生成**是独立证据门槛；Vault 基础设施可先设计和只读接入，但不因此放开比较答案、自动主题综述或“AI 已确认”状态。

## 后续仍待决定

1. 已选择独立的 `ResearchCopilot-Vault`；后续若更换 Vault，需显式重新连接，不自动迁移旧文件。
2. Vault 的跨设备同步方式及是否同步 PDF；默认只建议先做本机备份，完成单机回读后再验证跨设备。
3. 旧 `artifacts/` 中哪些卡片确实已由本人确认，才能迁入正式知识库；没有明确确认的一律保留为候选。
