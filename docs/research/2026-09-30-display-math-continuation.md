# M7.4a 跨文本行公式保护：开源论文阅读产品拆解

检索日期：2026-09-30。本记录先于实现完成。

## 用户问题

真实 `sample.pdf` 第 7 页的学习率公式在原图上占一个视觉行，但 PDF 文字层把上标、下标拆成两条文字行。现有翻译流程只把第一条替换为原图占位符，第二条残留在中文译文中，读者会看到不完整的公式碎片。目标是让明确可定位的整条展示公式以原 PDF 图像出现，而不声称恢复了它的 LaTeX 或数学语义。

## 参考项目与一手资料

| 项目 | 一手资料与做法 | 许可和成本 |
| --- | --- | --- |
| [Docling](https://github.com/docling-project/docling) | [DoclingDocument](https://docling-project.github.io/docling/concepts/docling_document/) 区分内容对象、来源坐标和正文阅读顺序；公式是独立内容项，不应从页级字符串推断视觉顺序。 | [MIT 代码](https://github.com/docling-project/docling/blob/main/LICENSE)，模型另查许可；本阶段不下载模型。 |
| [Marker](https://github.com/datalab-to/marker) | [官方 README](https://github.com/datalab-to/marker/blob/master/README.md) 将 Equation、TextInlineMath、Table 分成不同块，复杂块可用局部修复而不是整页强行线性化。 | Apache-2.0 代码、模型权重另有条款和资源需求；不复制代码。 |
| [PDFMathTranslate](https://github.com/PDFMathTranslate/PDFMathTranslate-next) | [官方进阶文档](https://github.com/PDFMathTranslate/PDFMathTranslate-next/blob/main/docs/en/advanced/advanced.md) 允许按公式字体和字符保留不可翻译对象，并提供局部页翻译。 | [AGPL-3.0](https://github.com/PDFMathTranslate/PDFMathTranslate-next/blob/main/README.md)，不引入其实现。 |
| [MinerU](https://github.com/opendatalab/MinerU) | [官方仓库](https://github.com/opendatalab/MinerU) 把公式、表格、阅读顺序做成独立解析能力，复杂页可回到可视化结果核对。 | 自定义 MinerU Open Source License，带附加条款；模型与运行成本较高，本阶段不依赖。 |

## 各项目的成熟做法

- **交互**：读者持续看到 PDF 原图；结构化译文只是辅助，不应把不完整公式伪装成可靠数学表达。
- **数据**：公式块是视觉对象，原文坐标和阅读顺序分开；不能只依据 `splitlines()` 来判定一条公式在哪里结束。
- **模型与检索**：对确定的展示公式先保护，再翻译附近文字；未知的行内数学仍保留在原 PDF，不让模型猜 LaTeX。
- **引用**：译文仍绑定原 PDF 页，公式图像从本地同一页裁取；不改变问答引用或检索证据。
- **隐私和失败**：原图留本机，不把公式图像发给 DeepSeek。找不到唯一原文位置时不新增占位符；模型漏掉占位符则拒绝保存。

## 对 ResearchCopilot 的取舍

| 方案 | 决定 | 原因 |
| --- | --- | --- |
| 扩展现有展示公式保护，在视觉上同一行的文字层续行一起替换 | 本阶段采用 | 真实第 7 页错误有明确原图和文字层证据；复用现有 `FormulaRegion`、页级译文和 PDF 局部图像。 |
| 只用 `splitlines()` 第一行替换 | 拒绝 | 下标等可能被抽成下一行，留下假公式。 |
| 让 LLM 根据碎片重新写 LaTeX | 拒绝 | 可能出现看似合理但与论文原图不一致的公式。 |
| 立即安装 Docling、Marker 或 MinerU 全套模型 | 暂缓 | 先用固定样本量化局部问题；不增加 Mac/Windows 环境负担和许可证风险。 |

## 架构影响与兼容性

只修改现有 `protect_display_formulas` 的候选范围；继续使用 `PageTranslationService`、`FormulaRegion`、原 PDF 裁图和占位符校验。算法改变后更新译文缓存版本，避免读者继续看到旧的残缺公式译文；旧缓存文件不删除。无需新核心对象、API、数据库或前端页面。

| 场景 | 要求 |
| --- | --- |
| 当前论文 / 换论文 | 只对当前 PDF 页解析；论文 ID 和页码仍决定缓存归属。 |
| 原文 / 译文 | 原 PDF 原样保留；译文用同页公式裁图代替可确认的展示公式碎片。 |
| 不同会话 | 页级译文缓存不随会话复制；问答记录仍按会话隔离。 |
| 本地 / 云端 | 检测和裁图本地完成；发送给 DeepSeek 的文字不包含已保护公式原文。 |
| macOS / Windows | 仅复用 pypdf 和现有 Python 3.12 逻辑，不引入系统命令或模型下载。 |

## 实现顺序与验收标准

1. 用原图和 PDF 文字层记录真实第 7 页的视觉公式与两条抽取行；普通单行公式是对照样本。
2. 只在可定位且明显属于同一视觉公式的续行上扩大替换范围；不能吞掉后面的解释段落。
3. 合成测试覆盖拆成两行、普通单行、无唯一坐标和漏占位符的失败场景；缓存版本更新。
4. 自动测试及前端构建通过；真实第 7 页的待翻译文本不再含第二条公式碎片，译文展示一张完整的同页原图。

## 暂不实现

不把所有行内公式转为 LaTeX，不重建表格单元，不宣布双栏阅读顺序已验证。M7.4 后续仍需固定样本评测这些场景，再决定是否引入布局模型或专门的 OCR/数学解析器。
