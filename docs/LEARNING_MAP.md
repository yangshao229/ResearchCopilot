# ResearchCopilot 分阶段学习地图

这份文档只负责记录“每个阶段做了什么、涉及哪些文件、以后需要学习哪些知识”。项目开发期间以完成功能为主；项目形成完整可用版本后，再按照本文顺序从零讲解和练习。

记录规则：

- 每完成一个里程碑就追加一节，不依赖聊天记录记忆。
- 区分新增文件和重要修改文件，避免学习时找不到代码来源。
- 学习时先讲数据如何流动，再讲单个文件和代码细节。
- 不要求学习者在开发期间同步掌握下面所有内容。

## 阶段 0：可复现的 Python 工程基线

Git：`7bb88db chore : initialize Python project`

新增文件：

- `.gitignore`
- `.python-version`
- `PROJECT.md`
- `pyproject.toml`
- `uv.lock`
- `src/research_copilot/__init__.py`
- `tests/test_smoke.py`

以后学习：项目目录结构、Python 包、虚拟环境、uv、依赖锁定、pytest、Git 的工作区/暂存区/提交。

## 阶段 1：保留页码的 PDF 加载

Git：`70e7df1 feat: add page-aware PDF loading`

新增文件：

- `src/research_copilot/pdf_loader.py`
- `tests/test_pdf_loader.py`

重要修改：`pyproject.toml`、`uv.lock`

以后学习：`Path` 对象、函数、列表和字典、pypdf、逐页抽取、页码为什么必须在最早阶段保留、用临时 PDF 编写测试。

## 阶段 2：分页 JSON 与 PDF 导入流水线

Git：

- `aaee8b7 feat: add JSON storage for page data`
- `17950ee feat: add PDF-to-JSON import pipeline`

新增文件：

- `src/research_copilot/page_store.py`
- `src/research_copilot/pdf_importer.py`
- `tests/test_page_store.py`
- `tests/test_pdf_to_json.py`

重要修改：`page_store.py`、`test_page_store.py`

以后学习：JSON 序列化与反序列化、UTF-8、`with` 上下文管理器、读写模式、模块之间如何通过函数组合成数据流水线。

## 阶段 3：文本切分与关键词检索

Git：

- `e9dffee feat: add page-aware chunking and keyword retrieval`
- `3b2b9bf feat: connect stored papers to keyword search`

新增文件：

- `src/research_copilot/text_splitter.py`
- `src/research_copilot/keyword_retriever.py`
- `src/research_copilot/paper_search.py`
- `tests/test_text_splitter.py`
- `tests/test_keyword_retriever.py`
- `tests/test_paper_search.py`

以后学习：chunk、overlap、页码元数据、关键词计分、排序、为什么透明的检索基线是后续比较 Embedding 的参照物。

## 阶段 4：命令行工作流与论文卡片草稿

Git：`5cd2468 feat: add CLI and reviewable paper cards`

新增文件：

- `src/research_copilot/cli.py`
- `src/research_copilot/paper_card.py`
- `tests/test_cli.py`
- `tests/test_paper_card.py`

重要修改：`PROJECT.md`、`src/research_copilot/__init__.py`

以后学习：命令行参数、应用入口、Markdown 模板、生成内容与人工确认的边界、为什么默认拒绝覆盖已有笔记。

## 阶段 5：多语种 Embedding 与语义检索

Git：`900b1b4 feat: add multilingual semantic paper search`

新增文件：

- `src/research_copilot/semantic_retriever.py`
- `tests/test_semantic_retriever.py`
- `docs/OPEN_SOURCE_RESEARCH.md`

重要修改：`paper_search.py`、`cli.py`、`test_paper_search.py`、`pyproject.toml`、`uv.lock`、`PROJECT.md`

以后学习：Embedding、向量、余弦相似度、多语种 E5 的 query/passage 前缀、依赖注入、用假模型测试、语义相似不等于证据质量。

## 阶段 6：产品蓝图与阅读流程

Git：`0f83d40 docs: define paper reading product blueprint`

新增文件：

- `docs/PRODUCT_BLUEPRINT.md`

重要修改：`PROJECT.md`、`docs/OPEN_SOURCE_RESEARCH.md`

以后学习：从开源项目提取设计经验、确定产品边界、证据优先的论文阅读流程、本地与云端的隐私分工、如何把长期目标拆成里程碑。

## M1：本地 PDF 阅读工作台

Git：`798ad2f feat: add local PDF reading workspace`

新增文件：

- `README.md`
- `src/research_copilot/web_app.py`
- `tests/test_web_app.py`
- `web/index.html`
- `web/package.json`
- `web/package-lock.json`
- `web/tsconfig.json`
- `web/vite.config.ts`
- `web/src/main.tsx`
- `web/src/App.tsx`
- `web/src/api.ts`
- `web/src/styles.css`
- `web/src/vite-env.d.ts`

重要修改：`.gitignore`、`PROJECT.md`、`pyproject.toml`、`cli.py`、`uv.lock`

以后学习：前后端分工、HTTP API、FastAPI、React 组件与状态、TypeScript 类型、PDF.js、浏览器 localStorage、路径安全、前端构建。

## M2：问题到可检查的原文证据

Git：`4b19bb6 feat: connect paper reader to local evidence search`

新增文件：

- `src/research_copilot/paper_search_service.py`
- `web/src/components/AssistantPanel.tsx`
- `web/src/components/PdfReader.tsx`

重要修改：`web_app.py`、`test_web_app.py`、`App.tsx`、`api.ts`、`styles.css`、`README.md`、`PROJECT.md`

以后学习：服务层、请求/响应模型、输入验证、POST 与 JSON、懒加载本地模型、React 受控组件、组件间数据传递、PDF 文本选区、异步请求、错误状态、点击证据跳转页码。

阶段结论：关键词检索能稳定定位术语；语义检索能用中文查英文，但基础相似度排序可能把参考文献或泛化段落排在真正答案之前，因此后续需要混合检索、重排序和评测。

## M3：基于证据的 DeepSeek 引用回答

Git：`6c55279 feat: add grounded DeepSeek paper answers`

新增文件：

- `.env.example`
- `src/research_copilot/paper_answer_service.py`
- `tests/test_paper_answer_service.py`
- `docs/M3_EVALUATION.md`

重要修改：`pyproject.toml`、`uv.lock`、`cli.py`、`web_app.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`App.tsx`、`styles.css`、`README.md`、`PROJECT.md`

以后学习：RAG 的完整数据流、模型提供方抽象、环境变量与密钥管理、Responses API、JSON Schema 结构化输出、Pydantic 校验、服务器端引用白名单、失败关闭原则、前端异步状态、API 错误处理、点击引用跳页、真实问题评测、TLS 与网络客户端差异。

验证结果：29 个自动测试通过；5 个真实问题完成评测；网页真实回答与第 5 页引用跳转通过。当前语义排序仍会混入参考文献，下一阶段进入混合检索和重排序。

## M4：可解释的混合检索、重排序与评测

Git：`cf95671 feat: add explainable hybrid retrieval`

新增文件：

- `src/research_copilot/hybrid_retriever.py`
- `src/research_copilot/retrieval_evaluation.py`
- `src/research_copilot/retrieval_benchmark.py`
- `evaluation/retrieval_questions.json`
- `scripts/evaluate_retrieval.py`
- `tests/test_hybrid_retriever.py`
- `tests/test_retrieval_evaluation.py`
- `tests/test_retrieval_benchmark.py`
- `docs/M4_EVALUATION.md`

重要修改：`paper_search.py`、`paper_search_service.py`、`paper_answer_service.py`、`web_app.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`App.tsx`、`styles.css`、`README.md`、`PROJECT.md`

以后学习：候选召回、关键词与向量分数为什么不能直接相加、Reciprocal Rank Fusion、启发式重排序、参考文献降权、Recall@k、MRR、固定评测集、离线回归评测、如何在网页解释排序过程。

验证结果：固定 5 题的 Mean Recall@5 均为 `1.00`；混合检索 MRR 为 `1.00`，高于关键词和语义检索的 `0.90`。M3 中失败的并行问题已把正文第 2 页排到第一。

## M5：本地阅读记录与人工确认

Git：`ee33940 feat: persist reviewable reading records`

新增文件：

- `src/research_copilot/reading_history.py`
- `tests/test_reading_history.py`
- `docs/M5_VALIDATION.md`

重要修改：`paper_answer_service.py`、`web_app.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`App.tsx`、`styles.css`、`README.md`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`

以后学习：本地 JSON 持久化、原子文件替换、UUID、UTC 时间、FastAPI 的 GET/PATCH/下载接口、React 的副作用与列表状态、草稿和人工确认状态、Markdown front matter、为什么 AI 不能代替用户点击“已确认”。

验证结果：自动测试覆盖保存、重启后读取、更新、未确认拒绝导出和 Markdown 导出；真实 DeepSeek 回答保存为“待人工确认”，整页刷新后“记录 1”仍然存在。

## M6：成熟论文卡片与安全修订

新增文件：

- `src/research_copilot/paper_card_compiler.py`
- `tests/test_paper_card_compiler.py`
- `docs/M6_VALIDATION.md`

重要修改：`reading_history.py`、`web_app.py`、`test_reading_history.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`App.tsx`、`styles.css`、`README.md`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`

以后学习：确定性模板编译、Literal 类型、人工分类、Markdown 结构、来源追踪、统一差异、版本化文件、拒绝覆盖策略、浏览器 Blob 下载、为什么成熟笔记不能由模型自动确认。

验证结果：至少两条确认记录才能生成；卡片保留页码、摘录和记录 ID；已有正式文件时显示差异并导出带时间戳的新版本。真实页面显示分类器和总结入口，没有替用户确认现有草稿。

## M6.1：第一版阅读体验补全

新增文件：

- `Start ResearchCopilot.command`
- `docs/M6_1_VALIDATION.md`

重要修改：`cli.py`、`web_app.py`、`reading_history.py`、`test_web_app.py`、`test_reading_history.py`、`api.ts`、`App.tsx`、`PdfReader.tsx`、`AssistantPanel.tsx`、`styles.css`、`README.md`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`

以后学习：浏览器上传二进制文件、安全文件名、SHA-256 去重、原子写入、响应式三栏布局、`ResizeObserver`、连续 PDF 渲染、滚动位置与页码同步、文本选区定位、前后端双重业务校验、默认浏览器启动、macOS 双击脚本。

验证结果：网页可直接导入 PDF 并识别重复文件；连续阅读、适合宽度、分栏收起和窄屏布局可用；选区有四种快捷动作；只有填写个人理解并选择栏目后才能加入论文卡片；自动测试、前端构建和真实页面检查均通过。详细过程见 [M6.1 验收](M6_1_VALIDATION.md)。

## 后续阶段

每完成一个后续里程碑，继续在这里记录新增文件、重要修改、验证结果与以后需要讲解的知识点。

新增功能在进入实现前，还要在 `docs/research/` 保存对应的开源产品拆解报告，并在阶段记录中链接它。第一份报告是 [论文结构与问题路由拆解](research/2026-09-21-paper-structure-and-question-routing.md)。

## M6.2：论文结构导航与问题路由

新增文件：

- `src/research_copilot/paper_structure.py`
- `src/research_copilot/paper_question_router.py`
- `tests/test_paper_structure.py`
- `tests/test_paper_question_router.py`
- `docs/M6_2_VALIDATION.md`

重要修改：`web_app.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`PdfReader.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`

以后学习：PDF 书签树、递归遍历、Pydantic 结构模型、启发式规则与置信度、确定性问题路由、为什么全文统计不能依靠 Top-k RAG、React 异步加载、目录层级渲染、程序跳页与滚动事件竞争、真实页面验收为何能发现自动测试遗漏的问题。

验证结果：真实 `sample.pdf` 从自带书签读取 22 个标题；目录可点击跳页；结构问题本地回答且不调用 API；段落统计无法可靠完成时安全拒绝；后端 `55 passed`，前端构建通过。详细过程见 [M6.2 验收](M6_2_VALIDATION.md)。本阶段设计依据见 [论文结构与问题路由拆解](research/2026-09-21-paper-structure-and-question-routing.md)。

## M6.3：论文专属阅读路线与独立会话

新增文件：

- `src/research_copilot/conversation_sessions.py`
- `src/research_copilot/paper_reading_guide.py`
- `tests/test_conversation_sessions.py`
- `tests/test_paper_reading_guide.py`
- `docs/research/2026-09-22-paper-reading-guides-and-sessions.md`
- `docs/M6_3_VALIDATION.md`

重要修改：`reading_history.py`、`web_app.py`、`test_reading_history.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`styles.css`、`App.tsx`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`

以后学习：数据模型为什么需要稳定 ID、按论文分文件保存、原子写入、Pydantic 默认值如何兼容旧 JSON、前后端双重范围校验、React 多个异步请求如何独立失败、会话筛选与整篇论文汇总的区别、如何从目录角色生成可解释问题、为什么点击建议不能自动调用模型。

验证结果：`sample.pdf` 根据真实标题生成专属阅读问题；点击建议只填入问题；新建“方法精读”后记录为空，切回“默认阅读”恢复原有 4 条记录；跨论文会话 ID 被后端拒绝；刷新时的并发首次读取安全；完整测试 `66 passed`，前端构建和真实页面检查通过。详细过程见 [M6.3 验收](M6_3_VALIDATION.md)。本阶段设计依据见 [论文专属阅读路线与独立会话拆解](research/2026-09-22-paper-reading-guides-and-sessions.md)。

## 架构校准：统一阅读模型与双语基础层设计

新增文件：

- `docs/research/2026-09-23-coherent-reading-architecture-and-bilingual-workflow.md`

重要修改：`docs/PRODUCT_BLUEPRINT.md`、`docs/OPEN_SOURCE_RESEARCH_PROTOCOL.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`

以后学习：功能清单与领域模型的区别、如何从完整用户旅程设计模块边界、领域对象、统一阅读上下文、横切关注点、语言状态分层、原文锚点、翻译缓存、术语表、许可证约束，以及为什么翻译、解释和问答应复用同一条处理管线。

阶段结论：此前蓝图虽然列出了划词翻译和多语种检索，却没有把语言建模为贯穿导入、阅读、证据、问答、记录和导出的基础能力。本次将产品收敛为八类核心对象，并新增架构影响与兼容性检查门槛。下一步先在 M6.4 落地统一 `ReadingContext`，再在 M6.5 实现双语阅读基础层，而不是直接增加孤立的语言按钮。设计依据见 [整体阅读架构与双语工作流拆解](research/2026-09-23-coherent-reading-architecture-and-bilingual-workflow.md)。

## M6.4 前置：统一阅读架构基线

新增文件：

- `src/research_copilot/domain.py`
- `src/research_copilot/storage.py`
- `src/research_copilot/paper_library.py`
- `src/research_copilot/document_service.py`
- `src/research_copilot/reading_service.py`
- `tests/test_domain.py`
- `tests/test_document_service.py`
- `web/src/components/assistant/AssistantViews.tsx`
- `docs/M6_4_FOUNDATION_VALIDATION.md`

重要修改：`cli.py`、`conversation_sessions.py`、`page_store.py`、`paper_answer_service.py`、`paper_search_service.py`、`reading_history.py`、`web_app.py`、`test_reading_history.py`、`AssistantPanel.tsx`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`。

以后学习：领域模型与传输模型的区别、Pydantic 组合模型、服务编排、依赖倒置、兼容旧接口的渐进重构、缓存键与失效、可重入锁、并发写入、唯一临时文件与原子替换、React 容器组件与展示组件、为什么架构重整应先保持行为不变。

验证结果：既有功能未改变；统一上下文已经成为问答编排入口；同一论文结构只解析一次并在文件变化后失效；并发写入不会丢阅读记录；后端 `70 passed`，前端 TypeScript 与生产构建通过。下一小步是在这条统一管线上增加章节范围解析和限定检索，而不是创建另一套检索流程。详细结果见 [M6.4 架构基线验收](M6_4_FOUNDATION_VALIDATION.md)。

## M6.4：章节感知检索

设计依据：[章节感知检索开源产品拆解](research/2026-09-25-section-aware-retrieval.md)。

新增文件：

- `src/research_copilot/section_scope.py`
- `tests/test_section_scope.py`

重要修改：`domain.py`、`paper_search.py`、`paper_search_service.py`、`paper_answer_service.py`、`reading_service.py`、`reading_history.py`、`web_app.py`、`test_paper_search.py`、`api.ts`、`AssistantPanel.tsx`、`AssistantViews.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`。

以后学习：如何从自然语言识别章节意图、文档层级树、同级标题定义章节边界、页码过滤为何比从 Top-k 结果猜章节可靠、模糊匹配的回退策略、HTTP 响应头如何保持旧 JSON 接口兼容、检索范围怎样保存到阅读记录。

实现结果：自动章节识别优先用 PDF 书签或保守推断的标题；章节内容限定到起始页和下一同级/上级标题之前；没有结果时提示用户改用全文；用户可选全文。使用 Attention Is All You Need、LoRA 与无书签的 BERT 真实 PDF 验收了书签解析、标题推断、章节页码过滤和全文回退。Embedding 离线评测因环境无法访问 Hugging Face 而未重跑。详细结果见 [M6.4 章节检索验收](M6_4_VALIDATION.md)。

## M6.5.1：论文级语言偏好与回答语言

设计依据：[双语阅读基础层开源产品拆解](research/2026-09-25-bilingual-reading-foundation.md)。

新增文件：

- `src/research_copilot/language_preferences.py`
- `tests/test_language_preferences.py`
- `docs/research/2026-09-25-bilingual-reading-foundation.md`
- `docs/M6_5_1_VALIDATION.md`

重要修改：`domain.py`、`paper_answer_service.py`、`reading_history.py`、`reading_service.py`、`web_app.py`、`test_paper_answer_service.py`、`test_reading_history.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`。

以后学习：`Literal` 类型与请求边界校验、Pydantic 默认工厂、按论文 ID 隔离的配置 JSON、FastAPI GET/PUT、语言策略如何进入模型提示词、一次请求的配置快照为何随记录保存、旧 JSON 数据迁移兼容、为什么证据仍保持原文。

验证结果：`80 passed`；论文语言偏好隔离、API 输入校验、回答生成传参、阅读历史快照和旧 JSON 兼容通过；前端 TypeScript 检查与生产构建通过。未调用真实 DeepSeek。此步只建立语言偏好与输出策略，还没有完整英文 UI、自动原文语言检测、段落级翻译上下文、术语表、翻译缓存或整篇双语视图。详细结果见 [M6.5.1 验收](M6_5_1_VALIDATION.md)。

## M6.5.2：选区上下文翻译

设计依据：[选区上下文翻译开源产品拆解](research/2026-09-25-selection-context-translation.md)。

新增文件：

- `src/research_copilot/selection_context.py`
- `tests/test_selection_context.py`
- `docs/research/2026-09-25-selection-context-translation.md`
- `docs/M6_5_2_VALIDATION.md`

重要修改：`domain.py`、`paper_answer_service.py`、`paper_search_service.py`、`reading_history.py`、`reading_service.py`、`web_app.py`、`test_paper_answer_service.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`。

以后学习：空白归一化与偏移映射、PDF 文本层为何不等于段落结构、上下文窗口与长度限制、前端本地预览和显式外部调用的隐私边界、直接证据与 RAG 检索证据的区别、`ReadingContext` 的 task/anchor 如何流经 API/服务/模型/历史记录、Pydantic 对旧 JSON 的兼容默认值。

验证结果：完整测试 `88 passed`；前端 TypeScript 与生产构建通过；`sample.pdf` 第 2 页本地恢复出选区上下文。不调用真实 DeepSeek/Hugging Face。详细结果见 [M6.5.2 验收](M6_5_2_VALIDATION.md)。

## M6.5.3：选区翻译缓存与显式重译

设计依据：[选区翻译复用开源产品拆解](research/2026-09-26-selection-translation-cache.md)。

新增文件：

- `docs/research/2026-09-26-selection-translation-cache.md`
- `docs/M6_5_3_VALIDATION.md`

重要修改：`domain.py`、`reading_history.py`、`reading_service.py`、`web_app.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`、`LEARNING_MAP.md`。

以后学习：缓存键是什么、为什么论文/会话/原文页码/上下文/语言/模型必须共同决定复用、旧记录的兼容默认值、提示版本怎样使缓存失效、为什么失败结果不可缓存、服务端与前端如何表达“未调用 API”、为什么强制重译只影响本次请求。

验证结果：完整测试 `88 passed`；前端 TypeScript 与生产构建通过；真实 `sample.pdf` 第 2 页上下文定位通过。未调用真实 DeepSeek，详细结果见 [M6.5.3 验收](M6_5_3_VALIDATION.md)。

## M6.5.4：论文级人工术语表

设计依据：[术语表开源产品拆解](research/2026-09-26-paper-glossary.md)。

新增文件：

- `docs/research/2026-09-26-paper-glossary.md`
- `docs/M6_5_4_VALIDATION.md`
- `src/research_copilot/paper_glossary.py`
- `tests/test_paper_glossary.py`
- `web/src/components/GlossaryManager.tsx`

重要修改：`domain.py`、`selection_context.py`、`reading_history.py`、`reading_service.py`、`paper_answer_service.py`、`web_app.py`、`test_paper_answer_service.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`App.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`、`LEARNING_MAP.md`。

以后学习：领域模型与独立 JSON 存储、输入校验、英文词边界与术语匹配排序、只发送命中项的隐私边界、翻译提示中“用户译名偏好”和“论文证据”的区别、术语快照哈希与缓存失效、前后端状态同步、如何用假模型验证请求而不花 API 费用。

验证结果：完整测试 `94 passed`；前端 TypeScript 与生产构建通过；真实 `sample.pdf` 第 2 页术语匹配与页面展开检查通过。未调用真实 DeepSeek，详细结果见 [M6.5.4 验收](M6_5_4_VALIDATION.md)。

## M6.5.5：原文语言的本地判断与人工覆写

设计依据：[原文与界面语言开源产品拆解](research/2026-09-27-source-and-interface-language.md)。

新增文件：

- `docs/research/2026-09-27-source-and-interface-language.md`
- `docs/M6_5_5_VALIDATION.md`
- `src/research_copilot/source_language.py`
- `tests/test_source_language.py`

重要修改：`domain.py`、`paper_library.py`、`reading_service.py`、`test_language_preferences.py`、`test_web_app.py`、`api.ts`、`AssistantPanel.tsx`、`styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`、`LEARNING_MAP.md`。

以后学习：原文/界面/回答/翻译目标四种语言为何分开、PDF 可抽取文本与扫描件、启发式判断和 `unknown`/`mixed`、用户覆写与旧 JSON 兼容、为何展示属性不应进入译文缓存键、怎样保持论文与会话作用域清楚。

验证结果：完整测试 `97 passed`；前端 TypeScript 与生产构建通过；真实 `sample.pdf` 检测为英文，页面显示和独立设置检查通过。未调用真实 DeepSeek；详细结果见 [M6.5.5 验收](M6_5_5_VALIDATION.md)。

## M6.5.6：完整中英文界面切换

设计依据：[界面语言开源产品拆解](research/2026-09-28-interface-language.md)。

新增文件：

- `docs/research/2026-09-28-interface-language.md`
- `docs/M6_5_6_VALIDATION.md`
- `web/src/i18n.ts`、`web/src/i18n-context.tsx`、`web/src/ui-status.ts`
- `web/src/locales/zh-CN.json`、`web/src/locales/en.json`
- `tests/test_frontend_i18n.py`

重要修改：`src/research_copilot/paper_reading_guide.py`（阅读建议增加结构化章节名）、`web/src/api.ts`、`web/src/main.tsx`、`web/src/App.tsx`、`web/src/components/PdfReader.tsx`、`AssistantPanel.tsx`、`GlossaryManager.tsx`、`assistant/AssistantViews.tsx`、`web/src/styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`、`LEARNING_MAP.md`。

以后学习：UI 语言与原文/回答/翻译目标为何独立，React Context 与 `localStorage`，消息键及占位符，后端中文状态和用户内容的边界，为什么在英文界面保留 PDF 原文和历史会话名，目录一致性测试与实际浏览器验收。

验证结果：完整测试 `100 passed`，TypeScript 和生产构建通过；真实页面中英切换、刷新保留、目录/提问区及原文不变检查通过。未调用真实 DeepSeek；详细结果见 [M6.5.6 验收](M6_5_6_VALIDATION.md)。

## M6.6：按需翻译当前 PDF 页

设计依据：[当前页论文翻译开源产品拆解](research/2026-09-28-page-translation.md)。

新增文件：

- `docs/research/2026-09-28-page-translation.md`
- `docs/M6_6_VALIDATION.md`
- `src/research_copilot/page_translation.py`
- `tests/test_page_translation.py`
- `web/src/components/PageTranslationPanel.tsx`

重要修改：`src/research_copilot/web_app.py`、`tests/test_frontend_i18n.py`、`web/src/api.ts`、`web/src/App.tsx`、`web/src/components/AssistantPanel.tsx`、`web/src/locales/en.json`、`web/src/locales/zh-CN.json`、`web/src/styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`、`LEARNING_MAP.md`。

以后学习：PDF 文本层与扫描件、页码锚点、按需 API 调用和费用边界、服务端缓存键与失效、术语表命中、原文与译文并排、为什么未经布局解析不能宣称逐段精确对齐，以及 DeepSeek 适配器和假模型测试。

验证结果：完整测试 `104 passed`、前端构建通过；真实 `sample.pdf` 页面中英文都出现“翻译当前页”，页码跟随 PDF 翻页。未调用真实 DeepSeek；详见 [M6.6 验收](M6_6_VALIDATION.md)。

## M6.6.1：逐页译文中的公式保护

设计依据：[公式保护开源产品拆解](research/2026-09-28-formula-safe-page-translation.md)。

新增文件：

- `docs/research/2026-09-28-formula-safe-page-translation.md`
- `docs/M6_6_1_VALIDATION.md`
- `src/research_copilot/formula_protection.py`
- `web/src/components/FormulaClip.tsx`

重要修改：`src/research_copilot/page_translation.py`、`tests/test_page_translation.py`、`web/src/api.ts`、`web/src/components/PageTranslationPanel.tsx`、`web/src/locales/zh-CN.json`、`web/src/locales/en.json`、`web/src/styles.css`、`PROJECT.md`。

以后学习：PDF 可见字形与文本层为何不同、公式占位符与失败关闭、PDF 坐标与浏览器裁图、缓存版本、为何“看原图”比猜测 LaTeX 安全、独立公式与行内公式的边界。

验证结果：完整测试 `108 passed`、前端构建通过；真实 `sample.pdf` 第 5 页的 3 处独立公式得到原图区域，数学特殊符号保留原字符。未调用真实 DeepSeek；详见 [M6.6.1 验收](M6_6_1_VALIDATION.md)。

## M7.1：逐页 PDF 解析质量关卡

设计依据：[逐页解析质量开源产品拆解](research/2026-09-29-page-extraction-quality.md)。

新增文件：

- `docs/research/2026-09-29-page-extraction-quality.md`
- `docs/M7_1_VALIDATION.md`
- `src/research_copilot/page_quality.py`
- `tests/test_page_quality.py`

重要修改：`src/research_copilot/page_translation.py`、`src/research_copilot/web_app.py`、`web/src/api.ts`、`web/src/components/PageTranslationPanel.tsx`、`web/src/locales/zh-CN.json`、`web/src/locales/en.json`、`web/src/styles.css`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`。

以后学习：PDF 文本层质量与版面顺序为何是不同问题、保守阈值与失败关闭、只读检测 API、前端异步加载和阻断模型调用、零新依赖阶段如何为下一步版面块解析建立基线。

验证结果：完整测试 `110 passed`、前端构建通过；真实 `sample.pdf` 第 5 页识别为需要复核数学内容，未调用真实 DeepSeek。见 [M7.1 验收](M7_1_VALIDATION.md)。

## M7.2：当前页原文区域与 PDF 坐标

设计依据：[原文区域定位开源产品拆解](research/2026-09-29-page-source-anchors.md)。

新增文件：

- `docs/research/2026-09-29-page-source-anchors.md`
- `docs/M7_2_VALIDATION.md`
- `src/research_copilot/page_layout.py`
- `tests/test_page_layout.py`

重要修改：`pyproject.toml`、`uv.lock`、`src/research_copilot/web_app.py`、`web/src/api.ts`、`web/src/App.tsx`、`web/src/components/PdfReader.tsx`、`web/src/components/AssistantPanel.tsx`、`web/src/components/PageTranslationPanel.tsx`、两份界面语言消息表、`web/src/styles.css`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`、`docs/LEARNING_MAP.md`。

以后学习：PDF 坐标和浏览器缩放、高亮覆盖层、按论文和页码隔离状态、pdfplumber 的词位置与阅读顺序并非一回事、Pydantic 输出模型、只读 API、空页和旋转页的显式降级、双栏与数学上下标为何不能用简单的 y 排序解决。

验证结果：完整测试 `113 passed`，前端 TypeScript 与生产构建通过；真实 `sample.pdf` 第 5 页返回 22 个区域，点击 `3.2.3` 标题后可在原 PDF 上看到对应高亮。没有调用 DeepSeek；仍未实现逐块译文对齐。见 [M7.2 验收](M7_2_VALIDATION.md)。

## M7.3：复杂版面风险与固定样本评测

设计依据：[阅读顺序与复杂版面风险开源产品拆解](research/2026-09-29-layout-risk-evaluation.md)。

新增文件：

- `docs/research/2026-09-29-layout-risk-evaluation.md`
- `docs/M7_3_VALIDATION.md`

重要修改：`src/research_copilot/page_layout.py`、`tests/test_page_layout.py`、`web/src/api.ts`、`web/src/components/PageTranslationPanel.tsx`、两份界面语言消息表、`web/src/styles.css`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`、`docs/LEARNING_MAP.md`。

以后学习：为何 PDF 坐标不等于阅读顺序、候选风险与准确识别的区别、双栏的纵向重叠信号、无竖线表格的横线信号、细小字形与上下标、测试中的假 PDF 和真实论文人工真值、为什么“无风险”不能推论为“可以自动对齐”。

验证结果：完整测试 `114 passed`、前端构建通过；真实 `sample.pdf` 第 5 页提示数学碎片，第 6 页提示表格横线与数学碎片。未调用 DeepSeek；没有改变现有译文。见 [M7.3 验收](M7_3_VALIDATION.md)。

## M7.3 后续修复：逐页翻译输出被推理 token 耗尽

重要修改：`src/research_copilot/page_translation.py`、`tests/test_page_translation.py`、`PROJECT.md`、`docs/LEARNING_MAP.md`；无新增代码文件，也未改变 PDF、译文缓存格式或前端交互。

故障根因：真实第 7 页的 DeepSeek Responses API 返回 HTTP 200，但 `status=incomplete`、`reason=max_output_tokens`，8,000 个输出 token 全用于推理，`output_text` 为空。修复后逐页翻译显式设置 `reasoning.effort=none`，并在响应截断或为空时给出明确错误，不将失败结果写入缓存。依据：[DeepSeek Responses API 文档](https://api-docs.deepseek.com/api/create-response/)。

以后学习：HTTP 成功与模型生成成功为何不同、推理 token 与可见输出共享预算、接口状态和 JSON Schema 双层校验、用真实 API 诊断但不输出密钥或正文、为什么单元测试通过还需端到端验证。

验证结果：完整测试 `115 passed`、前端构建通过；真实 `sample.pdf` 第 7 页修复前 `incomplete`、可见输出 0 字；修复后 `completed`、推理 token 0、返回约 1,300 字译文。阅读器中实际显示中文译文和两个独立公式原图，刷新后直接从本地缓存读取。行内公式与表格仍未可靠还原。

## M7.4a：跨 PDF 抽取行的展示公式保护

设计依据：[跨文本行公式保护开源产品拆解](research/2026-09-30-display-math-continuation.md)。

新增文件：`docs/research/2026-09-30-display-math-continuation.md`、`docs/M7_4A_VALIDATION.md`。

重要修改：`src/research_copilot/formula_protection.py`、`src/research_copilot/page_translation.py`、`tests/test_page_translation.py`、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。

以后学习：PDF 视觉行与文本层换行为何不一致、访客回调中的文字坐标、保守几何匹配、原图保护与模型翻译的边界、失败时不生成假公式、译文缓存版本和真实 API 端到端验证。

验证结果：完整测试 `117 passed`、前端构建通过；真实第 7 页重新翻译后没有学习率公式的尾部文字碎片，仍显示本地原图。M7.4 整体未完成，恢复工作见 [M7.4a 暂停点与验收](M7_4A_VALIDATION.md)。

## M7.4b：有横线表格的原图保护

设计依据：[表格页安全翻译开源产品拆解](research/2026-09-30-ruled-table-translation.md)。

新增文件：`docs/research/2026-09-30-ruled-table-translation.md`、`docs/M7_4B_VALIDATION.md`、`src/research_copilot/table_protection.py`、`web/src/components/OriginalPdfClip.tsx`。

重要修改：`src/research_copilot/page_translation.py`、`tests/test_page_translation.py`、`web/src/api.ts`、`web/src/components/PageTranslationPanel.tsx`、两份界面语言消息表、`web/src/styles.css`、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。原 `web/src/components/FormulaClip.tsx` 改由通用原图组件替代。

以后学习：PDF 视觉表格与线性文字层的差别、保守几何检测、表题与单元格边界、拒绝不唯一匹配、占位符失败关闭、复用同一 PDF 裁图组件、窄栏横向查看、为何没有行列评测时不应伪造表格译文。

验证结果：完整测试 `121 passed`、前端构建通过；真实 `sample.pdf` 第 6 页只把表格单元文字替换为本地原图，表题及后续正文译为中文，刷新后读取缓存。实测调用 DeepSeek 一次；表内单元格仍未翻译。见 [M7.4b 验收](M7_4B_VALIDATION.md)。

## M7.4c：双栏页抽取顺序关卡

设计依据：[双栏页阅读顺序开源产品拆解](research/2026-09-30-column-reading-order.md)。

新增文件：`docs/research/2026-09-30-column-reading-order.md`、`docs/M7_4C_VALIDATION.md`、`src/research_copilot/column_order.py`、`tests/test_column_order.py`。

重要修改：`src/research_copilot/page_quality.py`、`src/research_copilot/page_translation.py`、`src/research_copilot/page_layout.py`、`web/src/api.ts`、两份界面语言消息表、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。

以后学习：PDF 绘制顺序与人类阅读顺序、文字片段坐标、双栏候选的保守判断、通栏表格/说明的误报、为何多次回跳可以阻断但“没有回跳”不能证明正确、前后端双重门槛、窄中缝的原文锚点分割、旧缓存安全读取和跨论文隔离。

验证结果：完整测试 `127 passed`、前端构建通过；真实 BERT 第 2、6 页目视核对，16 页本地扫描无误阻断；项目 `sample.pdf` 15 页未误判为双栏。合成错序页在服务端和 HTTP API 均被拒绝，模型调用 0 次。见 [M7.4c 验收](M7_4C_VALIDATION.md)。

## M7.4c 后维护：代码一致性与去重

新增文件：无。重要修改：`web/src/api.ts`、`src/research_copilot/page_translation.py`、`docs/LEARNING_MAP.md`。

审查范围：网页入口、助手面板、前端 API、后端路由、逐页翻译与检索服务。发现最明确的重复是前端二十余个接口调用各自处理 HTTP 错误和 JSON；现收敛为私有的 `requestResponse`、`requestJson` 与 `jsonOptions`，保留各接口的 URL、请求体和失败回退文案，并统一优先显示服务端错误详情。双栏质量报告的两条重复构造路径也合并。没有改变 API、缓存键、论文资料或用户数据。

保留的边界：后端路由长，但拆为更多文件不能自动减少逻辑；公式与表格保护分别处理不同几何对象，不因名字相似而强行合并；旧命令行论文卡片和新网页卡片仍服务不同入口。PDF 多次解析和大前端组件是后续**有性能数据或交互测试时**再拆的候选，不在这次无基线的整理中冒险重写。

以后学习：前端请求封装、HTTP 错误与 JSON 数据的区别、保持外部契约不变的重构、为什么“文件少”不等于“架构简单”、如何用构建与端到端检查保护重构。

## M7.4d：唯一可定位的行内数学参数原图保护

设计依据：[行内数学参数开源产品拆解](research/2026-10-02-inline-math-preservation.md)。

新增文件：`docs/research/2026-10-02-inline-math-preservation.md`、`docs/M7_4D_VALIDATION.md`、`tests/test_inline_formula.py`。

重要修改：`src/research_copilot/formula_protection.py`、`src/research_copilot/page_quality.py`、`src/research_copilot/page_translation.py`、`web/src/api.ts`、`web/src/components/OriginalPdfClip.tsx`、`web/src/components/PageTranslationPanel.tsx`、`web/src/styles.css`、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。

以后学习：PDF 文字层为何丢失上/下标、正则只用于候选而非数学重建、`pdfplumber` 字符坐标、视觉行与唯一匹配、原文小裁片、模型占位符校验、Pydantic 可选字段兼容性、前端行内画布与块级原图、缓存版本失效、真实模型与假模型验收的差别。

验证结果：初次完整测试 `131 passed`、前端构建通过；真实 `sample.pdf` 第 7 页找到三处唯一行内参数，假模型服务流程收到五个公式占位符。之后只调用一次 DeepSeek 完成真实译文，网页确认三处行内原图、两处独立公式及缓存读取；见 [M7.4d 验收](M7_4D_VALIDATION.md)。

## M7.4e：行内数学真值与误报评测

设计依据：[行内数学保护真值与误报评测拆解](research/2026-10-03-inline-math-evaluation.md)。

新增文件：`docs/research/2026-10-03-inline-math-evaluation.md`、`docs/evaluations/m7_4e_inline_math_truth.json`、`tests/test_inline_formula_evaluation.py`、`docs/M7_4E_VALIDATION.md`。

重要修改：`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。生产公式识别、API、缓存和前端未改变。

以后学习：如何把受支持召回、普通文本误报和歧义数学安全回退分开计分，人工真值与合成排版轮廓的边界，为什么坐标唯一只证明原页位置、不证明数学语义，以及规则没有足够真实样本时为何“不扩大”也是可验证的工程结果。

验证结果：14 个账本案例中受支持召回率 `1.00`（4/4）、明确负样本误报率 `0.00`（0/2）、安全回退率 `1.00`（8/8）；本机真实 `sample.pdf` 第 7 页三处行内区域稳定且 PDF SHA-256 未变化。该原始 PDF 不随 Git 同步，其他设备缺失时只跳过真实样本核对。完整测试与前端构建通过；本阶段没有调用 DeepSeek，也没有把合成结果表述为跨论文真实准确率。见 [M7.4e 验收](M7_4E_VALIDATION.md)。

## M8.1：本地论文集合与标签

设计依据：[本地论文集合与标签开源产品拆解](research/2026-10-03-library-collections-tags.md)。

新增文件：`docs/research/2026-10-03-library-collections-tags.md`、`docs/M8_1_VALIDATION.md`、`src/research_copilot/library_organization.py`、`tests/test_library_organization.py`。

重要修改：`src/research_copilot/paper_library.py`、`src/research_copilot/web_app.py`、`web/src/api.ts`、`web/src/App.tsx`、两份界面语言消息表、`web/src/styles.css`、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。

以后学习：资源库组织元数据与文件路径的分离、多对多引用、稳定 ID、大小写不敏感规范化、原子 JSON 写入、依赖注入测试、集合删除的安全语义、前端派生筛选状态、为什么集合筛选不能静默扩大问答范围，以及何时应从 JSON 迁移到可查询存储。

验证结果：完整测试 `137 passed`、前端 TypeScript 与生产构建通过；使用两篇临时 PDF 验证集合、标签、筛选所需 API 和删除语义，没有修改真实论文、阅读记录或翻译缓存，也没有调用 DeepSeek。受限环境不允许监听空闲临时端口，因此本轮以生产构建和 FastAPI 端到端测试完成自动验收。见 [M8.1 验收](M8_1_VALIDATION.md)。

## M8.2：本地资料库全文搜索

设计依据：[本地资料库全文搜索开源产品拆解](research/2026-10-03-library-full-text-search.md)。

新增文件：`docs/research/2026-10-03-library-full-text-search.md`、`docs/M8_2_VALIDATION.md`、`tests/test_library_search.py`。

重要修改：`src/research_copilot/domain.py`、`src/research_copilot/paper_search_service.py`、`src/research_copilot/web_app.py`、`web/src/api.ts`、`web/src/App.tsx`、两份界面语言消息表、`web/src/styles.css`、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。

以后学习：资料库查找与跨论文生成的边界、显式范围 ID、分页抽取缓存复用、多词同现语义、纯文本片段与 HTML 高亮的安全差别、稳定排序、单文档失败隔离、扫描件与零命中的区别、为何点击定位不能自动扩大当前问答上下文，以及何时需要真正的全文索引。

验证结果：完整测试 `140 passed`、前端 TypeScript 与生产构建通过；临时三论文场景覆盖两篇可搜索和一篇损坏 PDF。真实 `sample.pdf` 在临时缓存目录搜索 `attention`，前五个位置为第 4、5、2、6、1 页，源文件哈希保持不变。没有读取密钥、加载 embedding、调用 DeepSeek 或修改阅读记录与翻译缓存。见 [M8.2 验收](M8_2_VALIDATION.md)。

## M8.3：显式多论文研究集合与证据聚合评测

设计依据：[显式多论文研究集合与证据聚合评测拆解](research/2026-10-03-explicit-multi-paper-evidence.md)。

新增文件：`docs/research/2026-10-03-explicit-multi-paper-evidence.md`、`docs/evaluations/m8_3_multi_paper_evidence_truth.json`、`docs/M8_3_VALIDATION.md`、`tests/test_multi_paper_evidence_evaluation.py`。

重要修改：`src/research_copilot/domain.py`、`src/research_copilot/web_app.py`、`web/src/api.ts`、`web/src/App.tsx`、两份界面语言消息表、`web/src/styles.css`、`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。

以后学习：任务范围与长期集合的区别、请求携带完整论文 ID 范围、逐来源公平上限、分组证据与全局 Top-K 的差别、三态失败语义、浏览器 localStorage、范围变化使旧结果失效、来源覆盖/页码召回/范围泄漏指标，以及为什么合成聚合逻辑通过仍不能证明真实跨论文回答可靠。

验证结果：固定合成账本的预期来源覆盖率 `1.00`（3/3）、页码召回率 `1.00`（3/3）、状态准确率 `1.00`（7/7）、范围泄漏率 `0.00`；完整测试 `143 passed`，前端生产构建通过。当前只有一篇真实本地论文，因此没有进行或声称真实跨论文准确率，也没有调用 DeepSeek、修改论文、阅读记录或翻译缓存。见 [M8.3 验收](M8_3_VALIDATION.md)。

## M8.4a：真实双论文证据基线

设计依据：[真实多论文证据评测拆解](research/2026-10-04-real-multi-paper-evaluation.md)。

新增文件：`docs/research/2026-10-04-real-multi-paper-evaluation.md`、`docs/evaluations/m8_4a_real_two_paper_truth.json`、`src/research_copilot/real_multi_paper_evaluation.py`、`scripts/evaluate_real_multi_paper.py`、`tests/test_real_multi_paper_evaluation.py`、`docs/M8_4A_VALIDATION.md`。

重要修改：`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。产品 API、前端、问答生成、用户数据和翻译缓存未改变。

以后学习：真实 PDF 版本哈希、固定问题与人工页锚点、来源覆盖和页锚点覆盖的区别、已知无关证据下界、证据不足负例、范围泄漏、自然问题与逐词匹配的鸿沟、中英文跨语言检索边界、可复现失败基线，以及为什么评测暴露失败也可以完成一个里程碑。

验证结果：两篇真实论文 6 个问题上，来源覆盖与人工页锚点覆盖均为 `0.556`（5/9），明确无证据准确率 `1.00`（3/3），已知无关证据率 `0.20`（3/15），范围泄漏 0；完整测试 `146 passed`，前端生产构建通过。评测只使用临时缓存，没有读取密钥、调用 DeepSeek 或修改论文和用户数据。结果明确阻止比较答案上线，下一步在同一账本上评测最小检索改进。见 [M8.4a 验收](M8_4A_VALIDATION.md)。

## M8.4b：真实双论文检索策略对照

设计依据：[多论文检索策略对照拆解](research/2026-10-04-multi-paper-retrieval-strategy.md)。

新增文件：`docs/research/2026-10-04-multi-paper-retrieval-strategy.md`、`scripts/compare_real_multi_paper_retrieval.py`、`docs/M8_4B_VALIDATION.md`。

重要修改：`src/research_copilot/real_multi_paper_evaluation.py`、`src/research_copilot/semantic_retriever.py`、`tests/test_real_multi_paper_evaluation.py`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`、`docs/LEARNING_MAP.md`。网页 API、前端、用户阅读数据和翻译缓存未改变。

以后学习：关键词检索与 Embedding 检索的不同失败模式、E5 的查询/段落前缀、RRF 混合排序、切块结果按 PDF 页去重、固定模型修订与离线复现、来源召回不等于页码证据可信、已知无关页只是误报下界、为什么向量检索会在无答案时也给出最近的内容，以及拒答门槛为何必须单独评测。

验证结果：同一双论文真值上，混合检索人工页锚点为 `8/9`，高于逐页关键词的 `5/9`；但三个预期无证据组合均返回了页，不能直接上线跨论文生成。完整测试 `148 passed`，前端生产构建通过。详见 [M8.4b 验收](M8_4B_VALIDATION.md)。

## M8.4c：证据门槛与页级融合

设计依据：[多论文证据门槛与页级融合拆解](research/2026-10-04-multi-paper-evidence-gate.md)。

新增文件：`docs/research/2026-10-04-multi-paper-evidence-gate.md`、`docs/evaluations/m8_4c_evidence_gate_truth.json`、`scripts/evaluate_real_evidence_gate.py`、`docs/M8_4C_VALIDATION.md`。

重要修改：`src/research_copilot/real_multi_paper_evaluation.py`、`tests/test_real_multi_paper_evaluation.py`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`、`docs/LEARNING_MAP.md`。生产 API、前端、用户数据与生成链未改变。

以后学习：Top-K 与相关性的差别、为什么向量空间永远存在最近邻、余弦分数与 RRF 分数的尺度边界、页级去重后再融合、短术语连续短语门槛、自然问题负例、正负分数区间重叠、门槛选择数据与独立验收数据的隔离，以及“排序更好”为什么不等于“可以安全回答”。

验证结果：页级融合把人工页锚点覆盖从 `8/9` 提高到 `9/9`；扩展账本共 7 个负组合。保住全部自然正例的余弦门槛只能正确拒答 `6/7`，拒答 `7/7` 则页锚点降至 `8/9`，因为自然正例最低分 `0.8169864591` 与自然负例最高分 `0.8172089757` 重叠。完整测试 `151 passed`、前端生产构建通过；未调用 DeepSeek、未修改论文或用户数据。见 [M8.4c 验收](M8_4C_VALIDATION.md)。

## M8.4d：细粒度证据充分性与独立留出集

设计依据：[细粒度证据充分性拆解](research/2026-10-04-fine-grained-evidence-sufficiency.md)。

新增文件：`docs/research/2026-10-04-fine-grained-evidence-sufficiency.md`、`docs/evaluations/m8_4d_fine_grained_evidence_truth.json`、`scripts/evaluate_fine_grained_evidence.py`、`docs/M8_4D_VALIDATION.md`。

重要修改：`src/research_copilot/semantic_retriever.py`、`src/research_copilot/real_multi_paper_evaluation.py`、`tests/test_real_multi_paper_evaluation.py`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`、`docs/LEARNING_MAP.md`。生产 API、前端、用户数据、问答与生成链未改变。

以后学习：Retrieve-and-rerank 的两阶段边界；pooled sentence cosine 与词元 late interaction 的区别；为什么未经该目标训练的 E5 隐藏状态不能冒充 Cross Encoder；calibration/held-out 隔离；参考文献字面命中为何不是答案证据；证据关卡无法补救候选召回漏页；失败的离线实验为什么也应固定账本而不是删除难例。

验证结果：校准集正例最低分 `0.7371592522` 低于负例最高分 `0.7945405841`；保住 `9/9` 锚点时只拒答 `2/7`。冻结门槛后 held-out 锚点 `3/4`、拒答 `0/4`，且 BERT 参考文献 ImageNet 页产生 `2` 个已知无关命中。完整测试 `159 passed`，前端生产构建通过，PDF 哈希未变；未联网下载模型或调用 DeepSeek。见 [M8.4d 验收](M8_4D_VALIDATION.md)。

该阶段当时要求 M8.4e 必须先取得用户许可，才能固定有明确许可证与修订的多语 Cross Encoder/reranker；后续已按此边界完成离线影子评测，结果见下方 M8.4e。calibration/held-out 隔离继续保留，比较答案和主题笔记仍关闭。

## M8.V0：Obsidian 长期知识库设计（仅蓝图）

设计依据：[Obsidian 知识库开源产品拆解](research/2026-10-04-obsidian-knowledge-vault.md)与[详细蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)。

新增文件：`docs/research/2026-10-04-obsidian-knowledge-vault.md`、`docs/OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md`。

重要修改：`docs/PRODUCT_BLUEPRINT.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。本轮只设计，不安装 Obsidian、不连接或修改用户 Vault，不迁移旧笔记，也不改变生产 API 与测试基线。

以后学习：普通 Markdown/YAML 如何承担文件式知识库；原文证据与个人理解为何要分权威；稳定 UID 与 PDF 内容指纹各解决什么问题；AI 草稿和人工确认的写入门槛；双向读写的版本冲突；Obsidian Bases 视图与存储的区别；Mac/Windows 同步时为什么不应保存绝对路径和重建缓存。

下一实施步：先迁移并固定论文身份，再做只读 Vault 校验与旧导出预览。跨论文生成继续受 M8.4d 证据门槛约束。

## M8.V1a：稳定论文身份与 PDF 版本关卡

设计依据：[Obsidian 知识库开源产品拆解](research/2026-10-04-obsidian-knowledge-vault.md)与[详细蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)。

新增文件：`src/research_copilot/paper_identity.py`、`tests/test_paper_identity.py`、`docs/M8_V1A_VALIDATION.md`。

重要修改：`src/research_copilot/paper_library.py`、`src/research_copilot/web_app.py`、`tests/test_web_app.py`、`web/src/api.ts`、`PROJECT.md`、`docs/PRODUCT_BLUEPRINT.md`、`docs/LEARNING_MAP.md`。没有迁移旧阅读记录、连接或写入用户 Vault，也没有修改论文、译文缓存或正式笔记。

以后学习：业务身份与内容指纹为何必须分离；改名/移动怎样靠指纹认回同一论文；同一路径内容变化为什么应保留 UID 但阻止旧页码自动延续；旧路径哈希 ID 如何在迁移期继续服务 API；重复 UID/别名为什么必须失败关闭；跨设备映射为什么不能保存绝对路径。

验证结果：改名/移动复用 UID、版本变化提示和重复别名拒绝均有回归测试；完整测试 `157 passed`，前端生产构建通过。两篇真实 PDF 在临时身份目录中重复扫描 UID 稳定，扫描前后源文件哈希未变。详见 [M8.V1a 验收](M8_V1A_VALIDATION.md)。

下一实施步：用户明确 Vault 路径后做 M8.V1 只读校验和旧导出迁移预览；在此之前不猜测路径、不写 Vault。跨论文生成继续受 M8.4d 证据门槛约束。

## U1：日常启动与资料库兼容性修复

修改文件：`src/research_copilot/cli.py`、`tests/test_cli.py`、`web/src/api.ts`、`web/src/App.tsx`、`web/src/locales/zh-CN.json`、`web/src/locales/en.json`、`README.md`、`PROJECT.md`、`docs/LEARNING_MAP.md`。没有新增业务模型、改动论文、阅读记录或正式笔记。

以后学习：端口占用为何会让新版网页连到旧版 API；服务真正就绪后才打开浏览器；`Promise.all` 一个请求失败导致整体初始化失败与 `Promise.allSettled` 的区别；旧接口字段缺失时的安全默认值；从单元测试延伸到浏览器真实操作与小额模型调用的分层验收。

验证结果：完整测试 `154 passed`，前端生产构建通过。旧进程继续占用 8000 时，新版在 8001 启动且返回两篇论文，浏览器显示两篇论文；旧进程对应页面不再将两篇误显示成 0 篇，并提示版本不匹配。本地搜索 `self-attention` 找到 10 处原文，点击后跳至 PDF 第 6 页。用公开短句分别完成一次 DeepSeek 结构化问答与翻译调用；再从网页翻译公开论文 PDF 第 2 页，译文显示成功，产生可重建的本地页译文缓存。未上传整篇论文、未写入正式笔记；公式、双栏和表格仍需人工对照原 PDF。

## M8.V1b：Obsidian 只读连接与双击启动

设计依据：[Obsidian 知识库开源产品拆解](research/2026-10-04-obsidian-knowledge-vault.md)与[详细蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)。

新增文件：`src/research_copilot/obsidian_vault.py`、`tests/test_obsidian_vault.py`、`web/src/components/VaultPanel.tsx`、`docs/M8_V1B_VALIDATION.md`。修改文件：`Start ResearchCopilot.command`、`src/research_copilot/web_app.py`、`src/research_copilot/cli.py`、`web/src/api.ts`、`web/src/App.tsx`、`web/src/styles.css`、两份界面语言文件、`pyproject.toml`、`uv.lock`、`README.md`、`PROJECT.md`、本学习地图和产品蓝图。没有创建用户 Vault 或写入其笔记。

以后学习：访达双击脚本与终端 PATH 的区别；`.venv` 与 `uv` 分工；本地端口是什么；Vault 为什么是普通 Markdown 文件夹；YAML frontmatter 与 schema 校验；为什么只读接入先于正式写入；重复 UID、符号链接和旧导出为何不能静默接受；本机配置与跨设备知识内容的边界。

验证结果：完整后端测试 `165 passed`，前端生产构建通过；严格拒绝把 YAML 布尔值冒充 schema 版本，连接配置原子保存且扫描顺序确定。临时新服务在 8002 打开并显示两篇论文与 Obsidian 入口，测试服务已关闭。只在临时测试 Vault 验证读写边界；用户尚无真实 Vault，故未完成真实个人资料库验收。详见[M8.V1b 验收](M8_V1B_VALIDATION.md)。

## M8.V2a：人工确认阅读记录的首次安全入库

设计依据：[本轮开源产品拆解](research/2026-10-05-reviewed-note-to-vault.md)、[Obsidian 长期知识库蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)与[验收](M8_V2A_VALIDATION.md)。用户已在 Obsidian 打开独立 Vault，ResearchCopilot 本机连接成功；真实 Vault 目前为空，本轮未自动写入。

新增文件：`docs/research/2026-10-05-reviewed-note-to-vault.md`、`docs/M8_V2A_VALIDATION.md`。

重要修改：`src/research_copilot/obsidian_vault.py`、`src/research_copilot/web_app.py`、`tests/test_obsidian_vault.py`、`web/src/api.ts`、`web/src/components/assistant/AssistantViews.tsx`、`web/src/components/VaultPanel.tsx`、`web/src/styles.css`、两份界面语言文件、`README.md`、`PROJECT.md` 与产品蓝图。

以后学习：API 为什么只能接收预览摘要而不接收任意 Markdown；服务器如何从已确认记录重新生成文件；`paper_uid`、PDF SHA-256 与原始页码如何共同保护引用；为什么摘要还必须绑定目标 Vault、预览之后要再次验证整个 Vault；排他创建如何阻止覆盖 Obsidian 外部编辑；测试中如何证明“预览不写入”和“失败保留原文件”。

验证结果：完整后端测试 `170 passed`、前端 TypeScript 与生产构建通过；切换目标 Vault、无效既有笔记和空来源问题均会失败关闭。只在临时测试 Vault 写入，未调用模型，也未向真实 Vault 自动保存笔记。下一步 M8.V2b 实现正式论文卡预览与首次保存，M8.V3 才处理已有笔记的外部编辑回读。

## M8.V2b：正式论文卡作为已入库笔记的索引

设计依据：[开源产品拆解](research/2026-10-05-vault-paper-index.md)、[成品化路线](PRODUCT_COMPLETION_PLAN.md)与[本阶段验收](M8_V2B_VALIDATION.md)。

新增文件：`docs/research/2026-10-05-vault-paper-index.md`、`docs/PRODUCT_COMPLETION_PLAN.md`、`docs/M8_V2B_VALIDATION.md`。

重要修改：`src/research_copilot/obsidian_vault.py`、`src/research_copilot/web_app.py`、`tests/test_obsidian_vault.py`、`web/src/api.ts`、`web/src/components/AssistantPanel.tsx`、`web/src/components/assistant/AssistantViews.tsx`、两份语言文件、`README.md`、`PROJECT.md` 和知识库蓝图。旧论文卡导出 API 留作兼容，但主要界面不再把候选文件与 Vault 正式卡混用。

以后学习：索引卡和知识正文为何分开；为什么只链接已写入 Vault 的笔记；相对 Markdown 链接与跨平台路径；预览摘要为什么还要包含被链接笔记的内容指纹；排他创建与外部编辑保护；如何在不新增业务模型的前提下复用已有存储服务。

验证结果：完整测试 `174 passed`，前端生产构建通过；真实 Vault 未被自动写入。下一阶段是 M8.V3 的外部编辑回读和冲突处理。

## M8.V3：Obsidian 外部编辑只读回读

设计依据：[外部编辑回读拆解](research/2026-10-05-vault-external-readback.md)、[成品化路线](PRODUCT_COMPLETION_PLAN.md)与[本阶段验收](M8_V3_VALIDATION.md)。

新增文件：`docs/research/2026-10-05-vault-external-readback.md`、`docs/M8_V3_VALIDATION.md`。

重要修改：`src/research_copilot/obsidian_vault.py`、`src/research_copilot/web_app.py`、`tests/test_obsidian_vault.py`、`web/src/api.ts`、`web/src/components/assistant/AssistantViews.tsx`、两份语言文件、`README.md`、`PROJECT.md`、产品蓝图与知识库蓝图。没有增加网页写回、自动合并或第二份知识正文。

以后学习：文件内容哈希与业务 UID 的不同职责；服务端按 UID 定位为何比接受绝对路径安全；完整 Vault 校验、符号链接边界与读取期间竞争；React 纯文本渲染与迟到请求的版本隔离；用户知识和论文原文的权威分离；未来更新为什么必须携带读取版本并先显示差异。

验证结果：当前完整测试 `177 passed`、前端 TypeScript 与生产构建通过；临时 Vault 中的外部修改会在下一次读取时返回新字节和新 SHA-256，跨论文、删除、无效 YAML 与符号链接均失败关闭。连续刷新或切换论文也不会让较早的请求覆盖当前结果。未写用户真实 Vault，未调用模型。真实 Vault 仍为空；下一步优先做完整阅读闭环的本机人工验收，M8.V4 等实际笔记数量足以验证组织需求后再启动。

## M8.U1：Vault 备份与恢复指引

设计依据：[备份与恢复开源产品拆解](research/2026-10-05-vault-backup-recovery-guidance.md)、[操作说明](VAULT_BACKUP_RECOVERY.md)与[本阶段验收](M8_U1_VALIDATION.md)。

新增文件：`docs/research/2026-10-05-vault-backup-recovery-guidance.md`、`docs/VAULT_BACKUP_RECOVERY.md`、`docs/M8_U1_VALIDATION.md`。

重要修改：`web/src/components/VaultPanel.tsx`、两份界面语言文件、`web/src/styles.css`、`README.md`、`PROJECT.md`、产品蓝图与成品化路线。不新增后端 API、依赖、备份任务或文件权限。

以后学习：同步与备份的不同故障模型；知识权威、未入库草稿、身份映射和可重建缓存的分层；操作系统版本备份；为什么恢复到新位置比直接覆盖安全；为什么应用不应在不知道保留策略时自动压缩或上传私密知识。

验证结果：完整测试 `176 passed`、前端 TypeScript 与生产构建通过。受限环境无法监听 8010、8011，故未停止任何已有进程，也未做浏览器误报验收；本轮只有静态说明与链接，没有读取备份状态、改写用户数据或调用模型。下一步检查首次启动、空论文库和后端版本不匹配的页面引导。

## M8.U2：首次使用与本地服务恢复

设计依据：[首次使用与本地服务恢复拆解](research/2026-10-05-first-run-and-service-recovery.md)与[本阶段验收](M8_U2_VALIDATION.md)。

新增文件：`docs/research/2026-10-05-first-run-and-service-recovery.md`、`docs/M8_U2_VALIDATION.md`。

重要修改：`src/research_copilot/web_app.py`、`tests/test_web_app.py`、`web/src/api.ts`、`web/src/App.tsx`、两份界面语言文件、`web/src/styles.css`、`README.md`、`PROJECT.md`、产品蓝图与成品化路线。

以后学习：空状态与错误状态为什么必须分开；前后端 API schema 握手；兼容降级与硬阻断的取舍；重试为何不应偷偷重启进程；窄屏收起侧栏时主任务入口仍须可见；React 异步请求的独立失败与状态保持。

验证结果：健康端点固定返回版本与 `api_schema=2`；完整测试 `177 passed`、前端 TypeScript 与生产构建通过。没有修改用户数据或调用模型。下一步检查窄屏与 Safari/WebKit 基础兼容。

2026-10-07 续验：`src/research_copilot/cli.py` 与 `tests/test_cli.py` 补全本地端口权限错误的区分；用临时服务在内置浏览器确认首页、PDF、目录和只读证据检索能实际工作，随后停止服务。以后学习：监听端口失败可能是“被占用”也可能是“没有权限”，错误提示不能把两者混为一谈。详见 [M8.U2 补充](M8_U2_VALIDATION.md)。这不代替真实 Safari／Vault 人工验收。

## M8.U3：窄屏与 Safari/WebKit 基础兼容

设计依据：[窄屏与 Safari/WebKit 开源产品拆解](research/2026-10-05-narrow-screen-safari-compatibility.md)与[本阶段验收](M8_U3_VALIDATION.md)。

新增文件：`docs/research/2026-10-05-narrow-screen-safari-compatibility.md`、`docs/M8_U3_VALIDATION.md`。

重要修改：`web/src/components/PdfReader.tsx`、`web/src/styles.css`、`README.md`、`PROJECT.md`、产品蓝图与成品化路线。没有新增依赖、API、领域对象或存储。

以后学习：WCAG 320 CSS 像素回流边界；PDF 这类二维内容为何应局部滚动而非强制文本重排；Safari 动态工具栏与 `dvh`/`vh` 渐进增强；flex 子项的 `min-height: 0`；浏览器能力检测与 `ResizeObserver` 安全降级；静态构建不能替代真实浏览器验收。

验证结果：完整测试 `177 passed`、前端 TypeScript 与生产构建通过。受限环境无法安全启动 8010–8099 的临时服务，故只完成静态与生产构建验收，没有把结果冒充真实 Safari 人工验收，也没有触碰已有进程、用户数据或模型。下一步需要用户在本机 Safari 中用一篇真实论文完成完整阅读与首次 Vault 入库闭环。

## 日常阅读失败关闭回归修复

验收依据：[日常阅读失败关闭回归验收](DAILY_READING_REGRESSION_VALIDATION.md)。这是对 M2/M3/M6.3 已定义行为的缺陷修复，不新增产品能力，因此复用原功能拆解，不另立新功能研究报告。

重要修改：`src/research_copilot/paper_search_service.py`、`src/research_copilot/paper_answer_service.py`、`src/research_copilot/page_translation.py`、`src/research_copilot/paper_reading_guide.py`、`src/research_copilot/web_app.py`及对应测试、`README.md`、`PROJECT.md`和产品蓝图。

以后学习：可选本地模型为何要显式离线加载；普通阅读请求不能暗中触发网络重试；以完整文本元组作为缓存键如何让论文内容变化自动失效；有界 LRU 与线程锁；HTTP 200 不等于模型输出完整或符合目标语言；结构化回答与隐藏推理竞争输出预算；附录标题为何不能自动成为第二条主阅读路线；失败关闭必须覆盖搜索、回答和翻译入口。

验证结果：完整测试 `181 passed`、前端 TypeScript 与生产构建通过；新增中文目标的长英文原样返回拒绝测试，以及不变论文块复用、正文变化自动重算和有界淘汰测试。当前回归未联网下载模型、调用 DeepSeek 或修改用户数据。真实 Vault 仍为 0 条笔记与 0 张论文卡，下一步继续等待本机全闭环人工验收。

## 真实论文 LoRA 阅读流程与使用说明

验收依据：[真实论文流程验收](REAL_PAPER_ACCEPTANCE_2026-10-06.md)。本轮是既有功能的真实样本复测和缺陷修复，不增加新的产品入口；新功能开源拆解协议不适用于这次修 bug。

新增文件：`docs/USER_GUIDE.md`、`docs/REAL_PAPER_ACCEPTANCE_2026-10-06.md`。本机新增但 Git 忽略的练习资料：`data/raw/lora-hu-2021-v2.pdf`，以及第 2 页翻译缓存。

重要修改：`.gitignore`、`src/research_copilot/paper_search_service.py`、`src/research_copilot/paper_answer_service.py`、`src/research_copilot/paper_reading_guide.py`、`src/research_copilot/web_app.py`及对应三份测试；`README.md` 与成品化路线增加使用和验收入口。其他已存在的 M8 修改仍按其各自阶段记录，不归入本轮新功能。

以后学习：真实 PDF 样本怎样暴露测试夹具看不到的问题；下载／导入文件与 Git 可复现源码的边界；为什么检索命中页不等于证据充分；DeepSeek 的 incomplete 状态与结构化输出预算；API 假模型测试与真实模型验收各自能证明什么；纸面自动化成功为何不能代替你在真实 Vault 中确认个人理解。

验证结果：LoRA 26 页 PDF、目录、方法页检索、真实 DeepSeek 中文回答与第 2 页翻译均经过实际服务检查；隔离临时 Vault 走通笔记／卡片防覆盖闭环，未写用户真实 Vault。后续体验修复的完整测试 `182 passed`，前端生产构建通过；用户 Safari 中的真实人工确认仍待完成。

## 本地 Embedding 管理与重排序候选

依据：[真实论文验收补充](REAL_PAPER_ACCEPTANCE_2026-10-06.md)和[多语重排序开源拆解](research/2026-10-06-retrieval-reranker-candidate.md)。新增文件：`docs/research/2026-10-06-retrieval-reranker-candidate.md`。重要修改：`semantic_retriever.py`、`paper_search_service.py`、`paper_search.py`、`page_translation.py`、`real_multi_paper_evaluation.py`、`scripts/evaluate_retrieval.py`、对应测试与使用说明。

以后学习：双塔 Embedding 与 Cross Encoder 的不同职责；模型固定修订、显式下载和跨设备不进 Git；有界内存向量缓存与内容变化自动失效；长篇英文原样返回不能算中文译文；一次 BM25 试验未通过真实样本就撤回，为什么比“指标好看”更重要。

验证结果：固定 E5 修订已在这台 Mac 离线加载；LoRA 连续两次查询实测约 5.48 秒和 0.01 秒，只有一组论文片段向量进入缓存（单次测量）。当时全套测试 `182 passed`、前端构建通过。该阶段结束时宽泛问句排序尚未达到验收门槛；候选重排序器尚未下载或接入，后续进展见下节。

## M8.4e：多语重排序器离线影子评测

设计依据：[多语重排序开源拆解](research/2026-10-06-retrieval-reranker-candidate.md)与[多论文验收](M8_4E_RERANKER_VALIDATION.md)。

新增文件：`docs/evaluations/m8_4e_reranker_truth.json`、`scripts/evaluate_reranker.py`、`src/research_copilot/reranker_evaluation.py`、`tests/test_evaluate_reranker.py`、`docs/M8_4E_RERANKER_VALIDATION.md`。本机模型缓存 `data/model_cache/` 被 Git 忽略，不跨设备同步。

以后学习：双塔模型先从全部片段中召回，Cross Encoder 只精排有限候选；为什么要在模型评测前固定 PDF 哈希、页码真值和无答案题；正例 Top-5 命中率与拒答能力为什么是不同指标；中文查询为何需要独立验收；离线模型修订和 `safetensors` 对可复现性与安全性的作用。

验证结果：三篇真实论文的 8 道有答案题，正确 PDF 页进入前五从 `2/8` 升到 `5/8`；中文仅 `0/3 → 1/3`，无答案题仍返回片段，因此不接入默认问答。完整 Python 测试 `186 passed`、前端 TypeScript 与生产构建通过；没有调用 DeepSeek 或写用户真实 Vault。

## 证据来源版本锚点回归修复

设计依据：[Obsidian 知识库拆解](research/2026-10-04-obsidian-knowledge-vault.md)、[已确认笔记拆解](research/2026-10-05-reviewed-note-to-vault.md)与 [M8.V2a 验收补充](M8_V2A_VALIDATION.md)。这是既有来源协议的安全补全，不新增产品入口。

重要修改：`domain.py` 增加可选的来源文档／页锚点；PDF 抽取缓存写入 SHA-256，检索只为指纹已验证的文本附加当前论文来源；回答、阅读历史和 Vault 预览沿用同一锚点。旧 JSON 仍可读取，但缺少指纹的旧抽取缓存会先重建，显式跨版本引用拒绝入库。

以后学习：稳定论文身份与具体 PDF 版本为何要分开；页码只有绑定 PDF 指纹才可跨设备复核；兼容旧记录不等于为旧记录伪造来源；可重建缓存的 schema 升级为何应失败关闭而不是沿用不确定文本。

验证结果：完整测试 `187 passed`、前端 TypeScript 与生产构建通过；覆盖当前来源锚点、旧缓存重建、跨版本引用拒绝与旧记录兼容。没有写用户真实 Vault、修改论文或调用 DeepSeek。

## M8：来源契约、统一证据包与已查看证据快照

设计依据：[来源契约验收](M8_SOURCE_CONTRACT_VALIDATION.md)、[证据包拆解](research/2026-10-06-evidence-set-consolidation.md)、[证据包验收](M8_EVIDENCE_SET_VALIDATION.md)、[快照拆解](research/2026-10-06-evidence-snapshot.md)与[快照验收](M8_EVIDENCE_SNAPSHOT_VALIDATION.md)。

新增文件：`src/research_copilot/evidence_snapshot.py`、`tests/test_evidence_set.py`、`tests/test_evidence_snapshot.py`、`tests/test_source_provenance.py` 和三份阶段验收文档。

重要修改：领域层以 `EvidenceSet` 统一检索候选、模型上下文和引文编号；搜索响应为当前 PDF 证据签发短期内存令牌，回答只在论文版本、问题、模式、条数与范围完全一致时复用该证据包。前端保存当前结果的令牌，并随同一问题提交；旧客户端不传令牌时仍兼容直接问答。

以后学习：来源身份、证据集合和证据充分性是三个不同问题；为什么用户刚看过的结果需要请求间快照；令牌为什么不能代替 PDF 哈希；进程内 TTL 与有界淘汰的安全取舍；为什么任何参数变化都应失败关闭而不是静默重新检索；为什么“回答用了同一证据”仍不能证明该证据足以回答。

验证结果：阶段测试依次为 `190 passed`、`194 passed`，快照首次全量 `197 passed`；补充服务重启与生成途中 PDF 变化回归后，最新全量 `200 passed`。前端 TypeScript 与生产构建通过。API 回归证明底层抽取缓存变化后，持令牌回答仍使用用户刚查看的原片段；问题、模式、条数、范围、PDF 版本、有效期或容量变化均在模型调用与历史写入前拒绝。没有调用 DeepSeek、修改论文／翻译缓存／用户阅读数据或写用户真实 Vault。

## M8.4f：页级多样性影子诊断

设计依据：[三项目／论文拆解](research/2026-10-06-page-diversity-shadow.md)与[离线验收](M8_4F_PAGE_DIVERSITY_VALIDATION.md)。新增文件：两份阶段文档。重要修改：`scripts/evaluate_reranker.py`、`tests/test_evaluate_reranker.py`；不修改生产检索或网页入口。

以后学习：Top-5 片段与 Top-5 不同 PDF 页为何不是同一个指标；同页重复占位如何损失页覆盖；“页码命中”与“某个片段真的足以回答”的差别；为什么一题改善、中文和无答案不改善时要保留影子状态。

验证结果：三篇真实论文的固定 11 题中，页级去重仅使有答案正确页覆盖从 `5/8` 到 `6/8`，中文仍 `1/3`；无答案能力没有改善。评测核心从 CLI 脚本收敛到可安装的项目模块，避免全量测试依赖工作目录；真实论文离线结果已复跑，最新 Python 全量 `201 passed`、前端构建通过。下一步分别诊断跨语排序与无答案证据充分性，不在这批题上硬调参数。

## M8.4g：中英文同义问题诊断

依据：[Cross Encoder 官方模型卡、mMARCO 原始论文与数据集卡、Sentence Transformers 官方 Retrieve & Re-rank 文档，以及离线结果](M8_4G_CROSS_LANGUAGE_DIAGNOSTIC.md)。新增文件：`docs/evaluations/m8_4g_matched_language_truth.json`、`docs/M8_4G_CROSS_LANGUAGE_DIAGNOSTIC.md`。不修改产品代码、模型依赖或生产排序。

以后学习：中英两组问句要先保证语义相同才能比较；候选召回与重排序是不同阶段；一个“多语模型”能处理中文，并不等于它在中文问题对英文科研文本上经过本项目验证；小样本诊断和产品上线门槛不同。

验证结果：3 组配对问题、6 条正例查询的正确页均进入前 30 个候选，影子重排前 5 命中为英文 `3/3`、中文 `1/3`；页级去重未增加命中。另有 3 条中文无答案查询的最高分与正例重叠，不能用分数阈值充当可靠拒答。不调用 DeepSeek、不写用户 Vault，保留影子状态。

## M8.4h：候选重排器的中英对照

依据：[BAAI 与 Sentence Transformers 官方方案、冻结问题账本和真实离线结果](M8_4H_MODEL_COMPARISON.md)。新增文件：`docs/evaluations/m8_4h_model_comparison_truth.json`、`docs/M8_4H_MODEL_COMPARISON.md`；本机新增 Git 忽略的 BGE 模型缓存。没有新增产品入口或生产依赖。

以后学习：为什么必须在试模型前锁定问题；问题级留出与论文级独立测试的差别；同一模型在两组题上出现反向结果时为何不能挑好看的指标上线；页码 Top-5、回答正确性与拒答能力的区别；本机延迟、模型体积和阅读体验的权衡。

验证结果：12 条新问题里，混合检索、原重排器、BGE 的正确页前五分别为 `8/12`、`11/12`、`12/12`；但旧困难集原模型 `4/6`，BGE 降至 `2/6`，且 BGE CPU 中位重排耗时约 `4.93s`，原模型约 `0.63s`。两者均继续保持影子状态，不调用 DeepSeek、不写真实 Vault。

## M8.4i：独立 RAG 论文验证

依据：[RAG 原始论文、Hugging Face 官方 RAG 文档、Sentence Transformers 官方两阶段检索说明、两种重排器官方模型卡与离线结果](M8_4I_INDEPENDENT_PAPER_VALIDATION.md)。新增文件：`docs/evaluations/m8_4i_independent_rag_truth.json`、`docs/M8_4I_INDEPENDENT_PAPER_VALIDATION.md`；RAG PDF 仅为 Git 忽略的本机评测输入。不修改产品代码或生产排序。

以后学习：问题级留出与论文级留出的区别；为什么一篇独立论文只能增加迁移证据、不能证明产品就绪；正确页进入 Top-5、片段足以回答与最终拒答为何必须分开；负例分数与正例重叠时为什么不能靠单一阈值；模型体积、片段长度与 CPU 延迟如何共同影响本地阅读体验。

验证结果：RAG 论文 4 组中英文正例中，混合检索、mMARCO、BGE 的正确页前五分别为 `7/8`、`8/8`、`8/8`；两条无答案题仍获得分数且与正例区间重叠。BGE 在本轮长片段上的 CPU 中位重排耗时约 `8.96s/题`，mMARCO 约 `0.62s/题`。完整测试 `201 passed`、前端构建通过；不调用 DeepSeek、不写真实 Vault，继续保持影子状态。

## M8.4j：答案承载证据覆盖

设计依据：[FEVER、HotpotQA、SQuAD 2.0、KILT 与 RAG 原论文拆解](research/2026-10-08-answer-bearing-evidence-shadow.md)和[影子验收](M8_4J_ANSWER_BEARING_EVIDENCE_VALIDATION.md)。重要修改：`docs/evaluations/m8_4i_independent_rag_truth.json`、`src/research_copilot/reranker_evaluation.py`、`tests/test_evaluate_reranker.py`；不修改产品检索、API 或网页。

以后学习：provenance 页码、支持事实和答案正确性的边界；为什么同页多个片段可能共同构成完整证据；字符串覆盖只能作为窄诊断，不能代替语义充分性；候选生成漏掉关键片段时重排器为什么无能为力；无答案仍需要独立拒答门槛。

验证结果：8 条 RAG 正例的正确页 Top-5 在混合检索、mMARCO、BGE 中为 `7/8`、`8/8`、`8/8`，答案承载短语完整则为 `5/8`、`7/8`、`7/8`。中文快速解码题的正确页虽已进入候选，但关键片段未进入前 30；页去重影子还把 mMARCO/BGE 覆盖降到 `5/8`、`6/8`。完整测试 `203 passed`、前端构建通过；不调用 DeepSeek、不修改用户论文、阅读记录、翻译缓存或真实 Vault。

## M8.4k：同页相邻片段影子诊断

依据：[LlamaIndex 的小到大检索思路拆解](research/2026-10-08-local-context-window-shadow.md)与[固定 RAG 论文离线验收](M8_4K_CONTEXT_WINDOW_VALIDATION.md)。新增文件：`src/research_copilot/context_window_evaluation.py`、`scripts/evaluate_context_window.py`、`tests/test_context_window_evaluation.py`、`docs/evaluations/m8_4j_support_spans.json` 和两份阶段文档。没有修改生产问答或网页。

以后学习：切分成小片段有利于定位，但片段边界可能截断答案；“正确页命中”和“真正包含答案”是两个指标；为什么同页邻居窗口必须校验 PDF 版本与文本；去重时为什么只能删除经验证的重叠；为什么补齐证据不能自动解决无答案拒答；为什么上下文更多也意味着 token、延迟和误导成本。

验证结果：原始混合检索 Top-5 的必要短语覆盖 `7/8`，向后补一个同页片段为 `8/8`；平均文本量由 `4,870` 增至 `8,520` 字符。双向邻居也为 `8/8`，但增至 `11,130` 字符。只有一道中文快速解码题获益，负例拒答未测，因此保持影子状态。Python 全量 `206 passed`、前端生产构建通过；不调用 DeepSeek、不写真实 Vault。

## M8.4l：三篇既有论文的同页窗口稳健性检查

沿用[同页上下文开源方案拆解](research/2026-10-08-local-context-window-shadow.md)，结果见[三论文离线验收](M8_4L_THREE_PAPER_CONTEXT_VALIDATION.md)。新增文件：`docs/evaluations/m8_4l_existing_papers_support_spans.json` 和本验收记录；将原有评测脚本泛化为多论文，并增加同页证据一致性回归。生产代码与用户界面不变。

以后学习：为什么答题所需信息可能位于已命中页的非相邻片段；为什么“前 30 里有答案”和“前 5 里有答案”对应不同修复；为什么必须限制证据来自同一 PDF 页；为什么成对中英文题不能当作 12 个独立知识点；为什么不能用上下文膨胀掩盖检索排序缺陷。

验证结果：LoRA、Transformer、BERT 的 6 组中英问法共 12 条，原片段短语覆盖 `5/12`，向后一个同页邻居 `7/12`，双向仍 `7/12`；平均字符数 `4,772 → 8,269 → 10,969`。BERT 仅 `1/4`，说明仅靠窗口无法修复答案页未进入 Top-5。RAG 原账本同页收紧后结果不变。Python 全量 `207 passed`，前端构建通过；未调用 DeepSeek、未写真实 Vault。

## M8.4m：答案承载重排与拒答分离

依据：[mMARCO、BGE、BEIR 与 SQuAD 2.0 拆解](research/2026-10-08-answer-bearing-rerank-abstention.md)和[离线验收](M8_4M_ANSWER_BEARING_RERANK_VALIDATION.md)。新增冻结账本 `docs/evaluations/m8_4m_answer_bearing_rerank_truth.json`；评测汇总增加正例最低分、负例最高分和单阈值可分性，答案覆盖可要求全部事实来自同一 PDF 页。生产代码、API 和网页不变。

以后学习：页码相关与答案承载片段的区别；为什么重排只对候选池内的片段有效；为什么 Cross Encoder 分数适合单问题内排序却不能自动作为跨问题拒答概率；为何必须同时报告中英、逐论文、延迟和旧困难集；同页多个互补片段为什么不能被页级去重；旧论文上的满分为何仍需新论文复核。

验证结果：12 条正例的混合检索、mMARCO、BGE 同页答案短语 Top-5 为 `5/12`、`11/12`、`12/12`；两种重排器的 6 条负例最高分均与正例区间重叠，统一拒答阈值失败。BGE CPU 中位约 `4.94s/题`，mMARCO 约 `1.01s/题`。完整测试 `210 passed`、前端构建通过；不调用 DeepSeek、不修改用户数据或真实 Vault。

## M8.4n：独立论文答案承载重排迁移

沿用[答案承载重排与拒答分离拆解](research/2026-10-08-answer-bearing-rerank-abstention.md)，结果见[独立 RAG 论文验收](M8_4N_INDEPENDENT_ANSWER_BEARING_RERANK_VALIDATION.md)。新增冻结账本 `docs/evaluations/m8_4n_independent_answer_bearing_rerank_truth.json`，复用既有评测模块、两个固定模型修订和 M8.4i/M8.4j 已在模型选择前冻结的论文与问题；生产代码、API 和网页不变。

以后学习：论文级独立测试为什么比旧题继续加分更可信；正确页进入候选与完整答案片段进入候选为何仍是两道门槛；重排器为何不能修复候选生成缺失；同页多个片段为何不能简单去重；为什么 BGE 的 Top-1 改善不能抵消相同 Top-5 上限与更高延迟；困难负例分数重叠为何仍要求独立的生成拒答验收。

验证结果：8 条正例的混合检索、mMARCO、BGE 同页答案事实 Top-5 为 `5/8`、`7/8`、`7/8`；唯一共同失败是前 30 候选缺少完整答案事实的中文快速解码题。mMARCO 正例最低分 `-0.4996`、负例最高分 `1.0356`，BGE 分别为 `0.6373` 与 `0.7807`，均无法用单阈值拒答。BGE CPU 中位约 `4.96s/题`，mMARCO 约 `0.60s/题`。完整测试 `210 passed`、前端构建通过；不调用 DeepSeek、不修改用户数据或真实 Vault。

## M8.4o：旧困难题证据标注与同页窗口复核

沿用[候选重排与拒答分离拆解](research/2026-10-08-reranked-support-and-abstention-shadow.md)，结果见[困难题验收](M8_4O_HARD_QUESTION_CONTEXT_AUDIT.md)。新增账本 `docs/evaluations/m8_4m_hard_set_support_spans.json` 和本验收文档；离线评测脚本增加可选两片段同页窗口、候选正确页与片段序号诊断，默认旧视图不变。生产检索、回答、API 和网页不变。

以后学习：人工真值为什么必须对齐问题语义；“命中正确页”和“命中足以回答的片段”如何分开计数；英文、中文同义问题为什么还要分别验收；为什么扩大上下文会增加 token 与噪声；为什么相关分数不等于可回答概率。

验证结果：旧困难题 6 条中英问法的正确页前 30 覆盖 `6/6`，必要短语原片段前 30 覆盖 `3/6`；mMARCO 原片段、后一片段、后两片段的 Top-5 短语完整分别为 `0/6`、`1/6`、`3/6`，后两片段的平均前五字符约为原来的 2.17 倍。另两组已固定题目没有从第二个邻居获得新增覆盖。Python 全量 `211 passed`、前端构建通过；未调用 DeepSeek、未修改真实 Vault。

## M8.4p：同页邻居候选扩展失败性实验

设计依据：[LlamaIndex、LangChain、Haystack 与 Sentence Transformers 的候选／上下文分离拆解](research/2026-10-08-neighbour-candidate-expansion-shadow.md)，结果见[离线验收](M8_4P_NEIGHBOUR_CANDIDATE_EXPANSION_VALIDATION.md)。新增独立 RAG 同页事实账本；评测模块增加稳定、同页、可核对的邻居候选扩展纯函数，离线脚本比较四种候选方向。生产切分、检索、`EvidenceSet`、API 和网页不变。

以后学习：为什么内部候选覆盖与最终 Top-5 覆盖是两个独立门槛；怎样在不扩大用户可见证据预算时比较召回修复；为什么邻居进入候选后仍可能被重排器压到 Top-5 之外；候选数量、Cross Encoder 延迟和答案覆盖如何一起决策；为什么一个失败题不能成为上线策略的唯一依据。

验证结果：独立 RAG 论文的候选事实覆盖由 `7/8` 增至 `8/8`，但 mMARCO Top-5 始终 `7/8`；平均候选数由 30 增至 41–49，中位重排耗时由约 `0.60s` 增至 `0.79–0.99s`。旧三论文困难集候选事实最多由 `3/6` 增至 `5/6`，Top-5 始终 `0/6`。完整测试 `213 passed`、前端构建通过；未调用 DeepSeek、未修改用户数据或真实 Vault，不接入生产。

## M8.4q：生成阶段的证据不足拒答契约

依据：[开源问答产品拆解](research/2026-10-08-generation-abstention-contract.md)与[本轮验收](M8_4Q_GENERATION_ABSTENTION_CONTRACT_VALIDATION.md)。修改文件：`src/research_copilot/paper_answer_service.py`、`tests/test_paper_answer_service.py`、`tests/test_web_app.py`；新增上述两份阶段文档，并同步更新项目蓝图。没有新增依赖或付费调用。

以后学习：检索分数、引用 ID 和证据充分性为何不是同一个概念；为什么提示词只能引导模型，服务端还需要确定性约束；拒答时为何不能把模型草稿中的肯定结论写入界面或阅读记录；中英文拒答与用户问题语言的关系；假引用、语义不符引用与人工真值验证分别需要什么检查。

验证结果：模拟模型同时宣称“证据不足”却输出肯定结论和有效引用 ID，服务端现强制改为安全拒答，清空引用，不泄露草稿正文；所选原文翻译失败路径亦如此。真实与伪造引用混用也会整体拒答，不再部分通过。完整 Python 测试 `218 passed`、前端构建通过，本地健康检查通过。尚不能证明模型在误判“证据充足”时的语义真实性；没有调用真实 DeepSeek，也没有写用户 Vault。

## M8.4r：真实回答人工复核

依据：[Haystack、LlamaIndex、Ragas 与 SQuAD 2.0 的评测流程拆解](research/2026-10-09-human-answer-audit.md)。新增[固定 8 题与人工裁决规则](M8_4R_HUMAN_ANSWER_AUDIT_PLAN.md)、机器可读[题目选择](evaluations/m8_4r_answer_audit_selection.json)和可恢复的本地采样脚本 `scripts/audit_generated_answers.py`；复用已有问题账本及四篇 PDF 的 SHA-256，不新增依赖或生产入口。

以后学习：为什么有答案与无答案必须分开计分；引用编号有效、引用语义忠实和答案事实正确分别是什么；为什么 API 失败不是正确拒答；怎样先固定问题再调模型；小样本评测为何不能冒充普遍准确率。

当前结果：四篇 PDF 的本机 SHA-256 与既有真值账本一致；用户明确授权内容传输后完成 8 次真实 DeepSeek 调用，[人工逐题复核](M8_4R_HUMAN_ANSWER_AUDIT_VALIDATION.md)发现有答案题核心正确 4/4、无答案题正确拒答 4/4，RAG 有一条非必要附录引用。题目非盲测，不能当通用准确率。额外的一次 BERT 英文题重测使总调用达到 9 次，超过原定 8 次上限，已记录且不再调用；用户不要求英文题强制英文回答，临时语言改动已撤回。脚本不会由单元测试调用 API，真实 Vault 不参与。

## M8.V4a：Obsidian 已导入论文目录

依据：[Open Notebook、Zotero、PaperQA2 与 Obsidian Bases 拆解](research/2026-10-09-obsidian-paper-catalog.md)，验收见[来源目录报告](M8_V4A_OBSIDIAN_PAPER_CATALOG_VALIDATION.md)。复用已有 `ObsidianVaultStore`、`PaperLibrary` 和稳定 `paper_uid`，不增加数据库或第二套论文身份系统。主要修改 `src/research_copilot/obsidian_vault.py`、`src/research_copilot/web_app.py`、`web/src/api.ts`、`web/src/components/VaultPanel.tsx`、两份前端语言文件及 `tests/test_obsidian_vault.py`；另新增本阶段调研和验收文档。

以后学习：来源目录和正式论文卡为什么要分开；YAML 属性如何被 Obsidian Bases 变成可筛选表格；预览摘要、首次独占创建与“不覆盖”的关系；稳定 UID 与 PDF 指纹如何防止重名或版本错配；为什么默认启动路径和命令行路径必须共享身份索引；Vault 是文件式知识库而不是 PDF 备份。

结果：真实 Vault 的 4 篇已导入论文现有来源条目和 Bases 表格；正式知识仍为 0 条，须用户逐条核对后保存。纠正一次身份目录不一致造成的旧记录，旧字节留在可恢复文件夹。完整测试 `225 passed`、前端构建通过，无 DeepSeek 调用、无 PDF 复制。

## 开源自测版：让别人安全地在本机复现

依据：[三款开源产品的部署与安全拆解](research/2026-10-12-self-hosted-beta.md)。新增文件：`LICENSE`、`CONTRIBUTING.md`、`SECURITY.md`、`docs/SELF_HOSTED_BETA.md`、`.github/ISSUE_TEMPLATE/bug_report.yml`、`.github/ISSUE_TEMPLATE/usability_feedback.yml`、本阶段拆解与[验收记录](SELF_HOSTED_BETA_VALIDATION.md)。重要修改：`README.md`、`docs/USER_GUIDE.md`、`docs/PRODUCT_COMPLETION_PLAN.md`、`pyproject.toml`、`src/research_copilot/cli.py`、`src/research_copilot/web_app.py`、`tests/test_cli.py`。

以后学习：开源许可与第三方依赖许可的区别；锁文件和干净安装；`127.0.0.1` 与公网监听的区别；为什么无认证服务必须拒绝开放监听；Git 忽略与 Git 历史泄露的区别；安全反馈如何脱敏；为什么 macOS 通过测试不能代替 Windows 验收。
