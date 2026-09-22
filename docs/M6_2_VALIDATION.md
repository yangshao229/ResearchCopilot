# M6.2 论文结构导航与问题路由验收

验收日期：2026-09-22

对应开源产品拆解：[论文结构与问题路由](research/2026-09-21-paper-structure-and-question-routing.md)

## 本阶段解决的问题

过去，页数、章节、标题和段落总数等问题都会进入普通 Top-k RAG。局部检索片段不能代表整篇论文，因此系统可能找到无关证据后拒答，也可能诱导模型猜测全文结构。

本阶段先将论文结构变成独立数据，并把结构问题与内容问题分流：

- 优先读取 PDF 自带书签，保留标题层级与真实 PDF 页码。
- 没有书签时，才使用保守的编号标题和常见章节名规则推断，并显示人工核对警告。
- 无法可靠识别时返回明确失败状态，不伪造目录。
- 页数、章节、标题问题在本地回答，不调用 DeepSeek。
- 段落总数问题明确解释 PDF 缺少可靠段落结构，不再用局部证据猜测。
- 内容问题继续进入原来的混合检索与带引用回答流程。

## 新增文件

- `src/research_copilot/paper_structure.py`
- `src/research_copilot/paper_question_router.py`
- `tests/test_paper_structure.py`
- `tests/test_paper_question_router.py`
- `docs/M6_2_VALIDATION.md`

## 重要修改

- `src/research_copilot/web_app.py`
- `tests/test_web_app.py`
- `web/src/api.ts`
- `web/src/components/AssistantPanel.tsx`
- `web/src/components/PdfReader.tsx`
- `web/src/styles.css`
- `PROJECT.md`
- `docs/PRODUCT_BLUEPRINT.md`
- `docs/LEARNING_MAP.md`

## 自动验证

- 后端完整测试：`55 passed`。
- 前端 TypeScript 检查和生产构建通过。
- 测试覆盖 PDF 书签层级、书签页码、保守标题推断、无法识别时的失败状态、本地页数回答、目录回答、段落统计拒绝和普通内容问题回退到 RAG。

## 真实论文验收

使用项目中的 `sample.pdf`（Attention Is All You Need）验收：

- 读取到 15 个 PDF 页面。
- 从 PDF 自带书签读取到 22 个各级标题。
- 正确保留 `Model Architecture → Attention → Multi-Head Attention` 的层级。
- `Multi-Head Attention` 对应 PDF 第 4 页，`Conclusion` 对应 PDF 第 10 页。
- 点击目录中的 `Conclusion` 后，阅读器页码稳定跳到第 10 页。
- 提问“这篇论文有哪些大标题和小标题？”后显示“本地结构分析 / 未调用 API”，列出 22 个标题与页码。
- 结构回答被保存到当前论文自己的阅读记录中，没有混入其他论文。

## 发现并修复的真实页面问题

第一次页面验收时，目录跳页会被连续阅读的滚动监听覆盖，目标页码短暂改变后又回到其他页面。修复后，程序跳页期间会忽略中途经过页面的滚动事件，并在目标页面完成定位后恢复正常滚动追踪。

## 当前边界

- 本阶段只处理 PDF 书签与纯文本标题规则，还没有字体大小、页面坐标和版面模型。
- “解释 3.2.1 节”仍会进入普通内容检索，尚未把章节范围传给检索器。
- 阅读记录已按论文隔离，但同一论文内还没有多个可命名会话。
- 推荐问题还没有根据论文结构动态生成。
