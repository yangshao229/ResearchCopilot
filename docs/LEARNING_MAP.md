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
