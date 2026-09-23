# 整体阅读架构与双语工作流：开源产品拆解

检索日期：2026-09-23

## 用户问题

ResearchCopilot 已经拥有 PDF 阅读、目录、检索、问答、会话、阅读记录和论文卡片，但这些能力不能继续按“用户提出一个功能，就新增一套局部实现”的方式增长。产品需要一条稳定的论文阅读主线，以及能够被翻译、解释、提问、笔记和总结共同复用的核心数据结构。

本轮同时修正一个此前蓝图覆盖不足的问题：双语能力不能只是“划词翻译”按钮。界面语言、论文原文语言、AI 解释语言、翻译目标语言和术语一致性必须被明确区分，并贯穿阅读、证据、会话、笔记和导出。

## 参考项目与一手资料

### 1. Open Notebook

- 官方仓库与文档：<https://github.com/lfnovo/open-notebook>
- 用户指南：<https://github.com/lfnovo/open-notebook/blob/main/docs/3-USER-GUIDE/index.md>
- 内容处理设计：<https://github.com/lfnovo/open-notebook/blob/main/docs/7-DEVELOPMENT/content-processing.md>
- 许可证：MIT。

成熟做法：

- 用 Notebook、Source、Note、Chat、Transformation 等少量稳定资源承载不同功能，而不是让每个界面动作拥有独立的数据孤岛。
- Chat 与 Search/Ask 是不同任务，但共享来源选择、内容处理、引用和上下文控制。
- 用户能够决定模型可访问哪些来源以及使用全文还是摘要，隐私和费用边界可见。
- 官方开发文档把切分、Embedding 和上下文构建定义为跨来源、笔记和洞察共同使用的能力。

### 2. Zotero PDF Translate

- 官方仓库：<https://github.com/windingwind/zotero-pdf-translate>
- 官方说明：<https://github.com/windingwind/zotero-pdf-translate/blob/main/README.md>
- 许可证：AGPL-3.0。

成熟做法：

- 翻译动作直接依附于 PDF 选区、批注和笔记，不创建与阅读器脱节的独立翻译应用。
- 选区原文与译文可以一起进入批注或笔记，保留阅读来源。
- 显示语言、目标语言、自动/手动触发和翻译引擎是不同设置，不混为一个“中英文切换”。
- 单词查询与段落翻译是不同任务，避免用昂贵模型完成所有语言操作。

### 3. Zotero Context Translate

- 官方仓库：<https://github.com/maverickzyc/zotero-context-translate>
- 英文说明：<https://github.com/maverickzyc/zotero-context-translate/blob/main/README.en.md>
- 许可证：AGPL-3.0-or-later。

成熟做法：

- 选区翻译会恢复所在句子、段落及必要的相邻段落，而不是只发送失去上下文的字符串。
- 原文块使用稳定 ID；整篇翻译按照“解析、结构化、术语表、翻译、验证、渲染”流水线执行。
- 提供论文/资料库级术语表、翻译缓存、历史记录和可恢复任务。
- 全文输出支持原文、译文和双语视图，但仍把原始 PDF 作为可核验来源。
- 明确展示隐私差异：普通文本模式不上传 PDF；选择外部复杂解析时才可能上传 PDF。

### 4. PaperQA2

- 官方仓库：<https://github.com/mmrech/paper-qa2>
- 论文：<https://arxiv.org/abs/2409.13740>
- 许可证：Apache-2.0；本项目当前只借鉴公开流程思想，不复制其实现代码。

成熟做法：

- 将论文搜索、证据收集和回答生成拆为可组合阶段。
- 检索出的原文块先经过与问题相关的上下文化和重排序，再进入最终回答。
- 文档元数据、原文证据和回答引用一起流动，避免答案与论文来源脱节。
- 模型提供商和核心论文问答流程保持可替换关系。

### 5. Jadense in Zotero（补充观察）

- 官方仓库：<https://github.com/jadense-ai/jadense-in-zotero>
- 官方说明：<https://github.com/jadense-ai/jadense-in-zotero/blob/main/README.en.md>
- 许可证：Jadense Non-Commercial License 1.0，属于 source-available，而非可自由复用的标准开源许可证。

只观察产品流程，不复制代码：

- 将选区翻译、整篇翻译、论文问答、来源关联批注和图表解释放在同一个阅读工作台中。
- 语言偏好按论文保存；整篇译文能定位回原始段落。
- 本地 OCR 是按需能力，不让复杂解析阻塞普通问答与选区翻译。

## 各项目共同揭示的成熟流程

这些项目的实现方式不同，但可以归纳为同一条阅读链：

```text
论文/来源
  ↓
可定位的内容单元（页、章节、段落、选区）
  ↓
用户任务（查词、翻译、解释、提问、总结）
  ↓
明确的上下文范围与原文证据
  ↓
模型或确定性工具处理
  ↓
带来源的结果
  ↓
用户确认后进入笔记/卡片
```

因此，翻译不是一条孤立管线；它只是“对当前阅读上下文执行的一种任务”。问答、公式解释和图表解释也应复用同一个上下文与证据契约。

## 对 ResearchCopilot 的整体取舍

### 直接采用

1. 用少量稳定领域对象承载所有功能：Paper、SourceDocument、DocumentBlock、ReadingSession、ReadingContext、EvidenceSet、ReadingRecord、KnowledgeArtifact。
2. 所有 AI 动作共享 `ReadingContext`：当前论文、会话、页码/章节/选区、任务类型、检索范围和语言策略。
3. 所有输出共享来源规则：原文不被译文覆盖；译文和解释必须能回到原文页码，后续升级为页面区域。
4. 将界面语言、回答语言、翻译目标语言和原文语言拆开建模。
5. 保存每篇论文的语言偏好和术语表；跨论文可以复用用户术语表，但不能混淆来源。
6. 普通选区翻译只发送选区及有限上下文；整篇翻译属于独立、可暂停、可恢复、明确提示费用与隐私的后台任务。
7. 解析、检索、生成、保存分别通过稳定接口组合，模型和解析器可以替换。

### 按本项目调整

1. ResearchCopilot 的中心仍是原始 PDF，不把双语 HTML 或 AI 摘要变成默认第一视图。
2. 第一版双语能力先完成“选区/段落中英对照、术语一致、证据回跳”；整篇双语重排放到复杂解析稳定之后。
3. 继续使用本地多语种 Embedding：中文问题可以直接检索英文原文，不需要先翻译整篇论文。
4. DeepSeek 只接收当前任务需要的原文上下文；发送范围在调用前可见。
5. 语言设置按层级合并：系统默认 → 论文偏好 → 当前任务临时覆盖，不创建多套互相冲突的开关。

### 明确拒绝

1. 不把“中英文切换”实现成一个含义不清的总开关。
2. 不生成第二份脱离 PDF 页码和原文锚点的译文副本。
3. 不默认上传整篇 PDF 给模型。
4. 不让翻译结果直接成为已确认笔记。
5. 不为翻译、解释、公式和问答分别创建互不兼容的会话与历史格式。
6. 不复制 AGPL 或非商业许可证项目的代码；本轮只借鉴公开的产品与架构思想。

## 统一核心模型

```text
Paper
 ├─ SourceDocument
 │   └─ DocumentBlock[] ── 原文、页码、章节、坐标、语言
 ├─ ReadingSession[]
 │   └─ ReadingContext ─── 当前锚点、任务、范围、语言策略
 │       └─ EvidenceSet ── 原始证据，不被翻译覆盖
 ├─ ReadingRecord[] ────── 翻译/解释/回答 + 来源 + 用户确认状态
 └─ KnowledgeArtifact[] ── 经确认的论文卡片、章节笔记、术语卡
```

`task_type` 决定处理方式，但不改变记录格式：

- `lookup`：术语查询，可优先使用本地词典。
- `translate`：选区和有限上下文翻译。
- `explain`：段落或概念解释。
- `formula`：公式拆解。
- `question`：当前论文 RAG 问答。
- `structure`：目录、页数等确定性回答。
- `summarize`：只汇总用户明确选择的范围或已确认记录。

## 双语能力的数据与交互契约

语言状态必须明确区分：

| 字段 | 含义 | 作用范围 |
| --- | --- | --- |
| `ui_locale` | 页面按钮和提示使用的语言 | 整个应用 |
| `source_language` | 原文块检测到的语言 | 每个内容块 |
| `explanation_language` | AI 解释与普通回答的语言 | 用户默认，可按论文覆盖 |
| `translation_target` | 翻译任务的目标语言 | 当前论文或当前任务 |
| `terminology_policy` | 专业术语如何保留双语与缩写 | 用户/资料库 + 论文覆盖 |

界面只暴露用户真正需要的三个入口：

1. 设置中的“界面语言”。
2. 论文工具栏中的“阅读显示：原文 / 中英对照 / 译文”（整篇模式后置实现）。
3. 助手中的“回答语言：跟随提问 / 中文 / English”。

选区菜单继续使用任务动作：查词、翻译、解释、公式，而不是让用户先理解复杂语言设置。

## 数据与隐私边界

- PDF、解析文本、Embedding、缓存、会话和术语表默认保存在本机。
- 原文证据必须保留，不得只保存译文。
- 选区翻译只发送选区和为消歧所需的有限相邻内容。
- 全文翻译若未来启用，必须在开始前展示预计范围、服务商、可能费用以及 PDF/文本是否会上传。
- API 密钥不进入翻译历史、日志、Git 或导出文件。

## 对当前代码的映射

本轮不推倒重写，现有模块可以归入统一架构：

| 现有模块 | 统一职责 |
| --- | --- |
| `pdf_loader.py`、`paper_structure.py`、`text_splitter.py` | SourceDocument / DocumentBlock |
| `conversation_sessions.py`、阅读位置 | ReadingSession / ReadingContext |
| `paper_question_router.py` | task type 与范围路由 |
| `paper_search_service.py`、各 retriever | EvidenceSet 构建 |
| `paper_answer_service.py` | AssistanceRequest 执行与回答验证 |
| `reading_history.py` | 统一 ReadingRecord |
| `paper_card_compiler.py` | KnowledgeArtifact 编译 |

后续重构重点是补齐共享契约，不再为每个按钮增加独立业务链。

## 实现顺序

1. 先把统一阅读上下文与请求契约写入蓝图，并用测试锁定现有行为。
2. M6.4 在该契约上完成章节感知范围，验证“任务 + 范围 + 证据”能够组合。
3. M6.5 完成双语阅读基础层：语言偏好、选区上下文翻译、双语记录和术语一致性。
4. M7 完成布局块和坐标后，再评估整篇双语重排、公式、图表和 OCR。
5. M8 复用同一核心对象扩展到多论文集合，不再另造一套问答记录。

## 验收标准

### 架构验收

- 每个现有与计划功能都能映射到上述核心对象和统一流程。
- 新功能提案必须说明复用哪些对象、增加哪些字段以及对其他流程的影响。
- 翻译、解释和问答保存为同一种 ReadingRecord，且都能定位回原文。
- 论文切换后，会话、语言偏好、术语覆盖和记录严格隔离。

### 双语最小版本验收

- 中文界面与回答语言互不绑定；英文界面仍可要求中文解释。
- 中文问题可以检索英文原文，证据面板始终显示未经替换的英文证据。
- 选择英文段落后，翻译结果包含原文、译文、PDF 页码和所用上下文范围。
- 相同论文、页码、选区、目标语言和术语版本可命中缓存。
- 翻译失败不会污染原文、笔记或已有缓存。
- 切换论文不会显示另一篇论文的翻译历史或论文级术语偏好。

## 暂不实现的内容

- 自动翻译所有新导入论文。
- 用译文替换 PDF 文本层。
- 为所有语言对宣称同等翻译质量。
- 在 M7 布局解析与坐标定位完成前实现复杂整篇双语排版。
- 让 AI 自动确认译文、回答或论文卡片。
