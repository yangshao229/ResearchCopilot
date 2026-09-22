# M6.3 论文专属阅读路线与独立会话验收

验收日期：2026-09-22

对应开源产品拆解：[论文专属阅读路线与独立会话](research/2026-09-22-paper-reading-guides-and-sessions.md)

## 本阶段解决的问题

过去所有问题都进入同一篇论文的同一个历史列表，页面也没有根据论文内容提供阅读顺序。这样既难以区分“理解方法”“检查实验”等不同任务，也容易让用户误以为固定提问适合所有论文。

本阶段增加了两个本地能力：

- 根据当前 PDF 的真实目录识别概览、方法、实验和批判阅读入口，只为实际存在的章节生成问题。
- 为每篇论文建立独立会话列表，每条回答显式保存所属会话；切换会话只显示该会话的记录。

点击推荐问题只会把问题填入输入框，仍由用户决定是否检索或调用 DeepSeek。会话和阅读路线都在本地创建，不调用模型 API。

## 新增文件

- `src/research_copilot/conversation_sessions.py`
- `src/research_copilot/paper_reading_guide.py`
- `tests/test_conversation_sessions.py`
- `tests/test_paper_reading_guide.py`
- `docs/research/2026-09-22-paper-reading-guides-and-sessions.md`
- `docs/M6_3_VALIDATION.md`

## 重要修改

- `src/research_copilot/reading_history.py`
- `src/research_copilot/web_app.py`
- `tests/test_reading_history.py`
- `tests/test_web_app.py`
- `web/src/api.ts`
- `web/src/components/AssistantPanel.tsx`
- `web/src/styles.css`
- `web/src/App.tsx`
- `PROJECT.md`
- `docs/PRODUCT_BLUEPRINT.md`
- `docs/LEARNING_MAP.md`

## 数据边界

- 会话包含稳定 ID、论文 ID、名称和创建时间，按论文分别保存。
- 旧问答 JSON 即使没有 `session_id`，读取时也会自动归入“默认阅读”。
- 后端同时检查 `paper_id` 与 `session_id`；其他论文的会话编号不能用于当前论文。
- 会话目前只组织记录，不会把过去全部问答隐式发送给 DeepSeek。
- 论文卡片继续汇总当前论文全部会话中已人工确认的记录，不因会话筛选漏掉正式笔记。

## 自动验证

- 后端完整测试：`66 passed`。
- 前端 TypeScript 检查和生产构建通过。
- 测试覆盖默认会话、命名会话、同名拒绝、跨论文隔离、旧记录兼容、按会话筛选、并发首次读取、推荐问题绑定真实章节、无实验章节时不伪造实验问题，以及伪造其他论文会话 ID 时拒绝回答。

## 真实论文验收

使用 `sample.pdf`（Attention Is All You Need）验收：

- 根据 PDF 书签生成了 Introduction、Background、Model Architecture、Results、Conclusion 等阅读问题。
- 点击“拆解方法 · Model Architecture”后，只把带第 2 页信息的问题填入输入框，没有自动生成回答或新增历史。
- 在网页中新建“方法精读”会话后，当前会话立即切换，笔记页显示 0 条问答记录。
- 切回“默认阅读”后，原有 4 条记录重新出现；两组记录没有混合。
- 页面明确显示当前范围固定为 `sample.pdf`，不会暗中扩大到其他论文。

真实页面首次刷新时还发现两个并发请求可能同时创建默认会话文件。会话存储现已使用进程内可重入锁，并为每次原子写入使用独立临时文件；新增并发回归测试防止同类问题再次出现。

## 当前边界

- 还没有会话重命名、归档和删除。
- 会话不是模型的多轮上下文；每次回答仍以当前问题和本次检索证据为准。
- “解释 3.2.1 节”等问题还没有自动限制到目标章节范围，这将作为 M6.4 单独研究和实现。
- 推荐问题基于可解释的英文标题关键词；非标准论文类型以后需要更成熟的论文类型判断。
