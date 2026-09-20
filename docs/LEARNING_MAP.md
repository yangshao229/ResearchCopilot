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

## 后续阶段

每完成一个里程碑，继续在这里记录新增文件、重要修改、验证结果与以后需要讲解的知识点。
