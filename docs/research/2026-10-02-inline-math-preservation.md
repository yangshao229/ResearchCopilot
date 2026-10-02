# M7.4d 行内数学参数保护：开源论文阅读产品拆解

检索日期：2026-10-02。此记录先于功能代码完成。

## 用户问题

论文 `sample.pdf` 第 7 页原图写有带上、下标的优化器参数（`β₁`、`β₂`、`ϵ = 10⁻⁹`），但可抽取文字变成 `β1 = 0.9,β2 = 0.98 andϵ = 10−9`。普通字符串既不能表达上下标，也会粘连邻近英文。逐页翻译若把它当普通散文交给模型，读者容易误认模型重写的公式就是论文原文。

## 参考项目与一手资料

| 项目 | 成熟做法 | 许可与成本 |
| --- | --- | --- |
| [Marker 官方 README](https://github.com/datalab-to/marker/blob/master/README.md) | 区分 `Equation` 与 `TextInlineMath`；结构化结果仍保留页与块，数学重建依赖 OCR/VLM 路径，并明确纯文字层模式对数学不可靠。 | [Apache-2.0 代码](https://github.com/datalab-to/marker/blob/master/LICENSE)，模型权重另查；不复制实现或下载模型。 |
| [PDFMathTranslate 进阶文档](https://github.com/PDFMathTranslate/PDFMathTranslate-next/blob/main/docs/en/advanced/advanced.md) | 允许用公式字体、字符规则把不可翻译内容排除，同时提供只翻译部分页的工作流。 | [AGPL-3.0 仓库](https://github.com/PDFMathTranslate/PDFMathTranslate-next/blob/main/LICENSE)；只借鉴分离翻译/原版式的思想，不引入代码。 |
| [DoclingDocument 文档](https://docling-project.github.io/docling/concepts/docling_document/) 与 [API](https://docling-project.github.io/docling/reference/docling_document/) | 文档项可携带来源位置；公式与正文不是同一个无结构字符串，行内分组也可以明确表达。 | [MIT 代码](https://github.com/docling-project/docling/blob/main/LICENSE)；完整解析流水线成本高，本阶段不安装。 |

## 各项目的成熟做法与取舍

- **交互**：原 PDF 始终是事实来源；译文中能可靠定位的行内数学片段用同页原图小裁片显示，旁边散文正常翻译。无法定位时明确提醒对照原 PDF，而不伪造 LaTeX。
- **数据**：沿用现有 `FormulaRegion`、原文页码、页级译文和 PDF 裁图组件，增加“行内”显示属性；不新建公式数据库或会话体系。
- **模型**：只把唯一匹配的片段换成占位符，再翻译其余正文；回包必须原样包含每个占位符一次，否则不保存。坐标只用于定位，不用于猜测数学语义。
- **引用**：仍按原论文和原 PDF 页码定位；行内裁片仅为原文展示，不成为新的问答证据。
- **隐私与失败**：PDF 裁图留本机，不发送图像给 DeepSeek；不确定的数学位置不做替换，亦不声称整页行内公式已验证。

| 方案 | 取舍 | 原因 |
| --- | --- | --- |
| 唯一可定位的希腊字母赋值片段保留同页原图 | 本阶段采用 | 第 7 页有明确人工真值，可以验证原文片段、坐标与译文占位符。 |
| 以字符串正则重写上下标或让模型生成 LaTeX | 拒绝 | 抽取文本已经失真，无法证明重建结果正确。 |
| 对所有行内表达式或整页强制 OCR/VLM | 暂缓 | 需要更大人工真值集、模型许可证与 Mac/Windows 成本评估。 |

## 架构影响与兼容性

复用 `PageTranslationService → FormulaRegion → OriginalPdfClip`，不改检索、问答或卡片。增加行内识别函数；缓存提示版本升级，旧译文不删除但不复用。`FormulaRegion.inline` 默认为 `false`，旧结构可读。

| 组合 | 约束 |
| --- | --- |
| 当前论文 / 跨论文 | 每次只检查当前 PDF 当前页；缓存仍按论文 ID、页码、原文和术语版本隔离。 |
| 原文 / 译文 | 原 PDF 不变；只有通过唯一几何匹配的行内片段显示原图。 |
| 不同会话 | 页级译文仍共享，同一论文的问答记录继续按会话隔离。 |
| 本地 / 云端 | 定位与裁图本地完成；DeepSeek 仅收到占位符和其余文本。 |
| macOS / Windows | 复用现有 Python 3.12、pdfplumber、pypdf 和浏览器 PDF.js；不增加系统依赖或跨设备缓存。 |

## 实现顺序与验收标准

1. 核对真实第 7 页原图、`pypdf` 文字与 `pdfplumber` 字符坐标，固定可保护的狭窄赋值模式。
2. 只有源片段和视觉字符序列均唯一、同一行且坐标有效时才生成行内裁片；多个或零个候选均放弃保护。
3. 测试保留周围散文、多个参数、重复/歧义位置、漏占位符及旧缓存失效；真实页应能生成三处精确原图位置，不吞掉“Adam optimizer”和后续句子。
4. 完整测试、前端构建和浏览器检查通过；不调用真实 DeepSeek，除非用户另行要求实际翻译验收。

## 暂不实现

不自动恢复数学语义、所有行内公式、表格单元、OCR 或逐块双语对齐。即使本阶段通过，其他数学表达仍须以原 PDF 为准。
