# M6.5.1 论文级语言偏好与回答语言验收

日期：2026-09-25

## 设计依据

编码前完成 [双语阅读基础层开源产品拆解](research/2026-09-25-bilingual-reading-foundation.md)，对照 Zotero Context Translate、Zotero PDF Translate 和 Open Notebook 的官方仓库、README/API 与工作流文档。本轮只借鉴公开交互/架构思想，没有复制代码或引入依赖。

## 完成内容

- 将回答语言、翻译目标、术语策略建模为严格校验的 `LanguagePolicy`，作为现有 `ReadingContext` 的组成部分。
- 新增按论文 ID 隔离的本地 JSON 语言偏好存储和 GET/PUT API。
- 提问面板提供回答语言、翻译目标和术语策略三个独立选项；切换论文时重新加载该论文偏好。
- 语言策略进入模型提示词，证据仍取自未翻译的论文原文。
- `PaperAnswer`、`ReadingRecord` 与 Markdown 导出保存请求使用的语言策略。
- 旧阅读记录缺少语言字段时按默认策略加载；旧请求不传语言字段仍可用。
- 选区“翻译”动作会根据当前论文的翻译目标生成明确指令，但本步尚未实现段落上下文恢复/独立翻译任务；相关后续边界见开源拆解报告。

## 自动验收

- Python：`80 passed`；包含论文间设置隔离、API 参数校验、回答语言传递、历史快照和旧 JSON 兼容测试。
- Web：`npm run build` 成功（TypeScript 检查与 Vite 构建通过）。仍有既存的大型 PDF.js bundle 提示。
- `git diff --check` 通过。
- 不调用真实 DeepSeek；通过测试模型验证输出语言指令与记录字段，避免消耗 API 额度。

## 范围与待办

本小步没有将 UI 全量英文化，也没有新增自动原文语言检测、论文术语表、翻译缓存、选区相邻段落解析或双语 PDF 排版。下一小步应让翻译作为明确任务复用同一阅读记录，并显示实际发送的选区/有限上下文及 PDF 页码，而不是把整篇或无关检索片段送给模型。

## 文件地图

- 新增：`src/research_copilot/language_preferences.py`、`tests/test_language_preferences.py`、`docs/research/2026-09-25-bilingual-reading-foundation.md`、本验收文档。
- 修改：`domain.py`、`paper_answer_service.py`、`reading_history.py`、`reading_service.py`、`web_app.py`、对应测试、`web/src/api.ts`、`web/src/components/AssistantPanel.tsx`、`web/src/styles.css`、`PROJECT.md`、`PRODUCT_BLUEPRINT.md`、`LEARNING_MAP.md`。
- 用户已有修改：`src/research_copilot/paper_card.py` 仅有格式折叠变化，未纳入本阶段功能。
