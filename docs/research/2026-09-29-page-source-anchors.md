# M7.2 原文区域定位：开源论文产品拆解

检索日期：2026-09-29。

## 用户问题

逐页译文和问答虽保留 PDF 页码，但读者仍须自己在整页中找对应原文。PDF 文本层的行顺序、数学上下标和视觉布局又可能不同；在没有可验证的页面坐标前，直接声称逐段双语对齐会制造错误信心。本阶段建立可点击的原文区域锚点，让读者能回到可见 PDF 核对。

## 参考项目与一手资料

| 项目 | 官方来源 | 数据与交互做法 | 许可/成本 |
| --- | --- | --- | --- |
| [Docling](https://github.com/docling-project/docling) | [DoclingDocument](https://github.com/docling-project/docling/blob/main/docs/concepts/docling_document.md)、[阅读顺序实现](https://github.com/docling-project/docling/blob/main/docling/models/stages/reading_order/readingorder_model.py) | 文本、图片、表格分对象；项目结构保存阅读顺序，每项可携带 provenance 与 bbox。坐标和结构分开，不能把一个按 y 排序的列表当成准确阅读顺序。 | MIT；整套模型流水线对 Mac/Windows 均有额外运行成本。 |
| [Marker](https://github.com/datalab-to/marker) | [JSON/调试输出](https://github.com/datalab-to/marker/blob/master/README.md) | JSON 输出布局块与页内 bbox，调试图叠加检测区；处理阅读顺序、公式和表格是不同阶段。 | 代码 Apache-2.0，模型权重另有条款，当前不引入。 |
| [MinerU](https://github.com/opendatalab/MinerU) | [输出文件结构](https://github.com/opendatalab/MinerU/blob/master/docs/en/reference/output_files.md)、[许可](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md) | 内容列表可按阅读顺序输出，原布局另存页面框；段落/公式/表格须保留类型，不应混成无坐标字符串。 | 带附加条款且模型/依赖较重；借鉴结构，不复制代码。 |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | [README](https://github.com/jsvine/pdfplumber/blob/stable/README.md)、[MIT 许可](https://github.com/jsvine/pdfplumber/blob/stable/LICENSE.txt) | 提供本地可抽取字/词及其 `(x0, top, x1, bottom)` 坐标，还支持裁剪区域。其 `use_text_flow` 文档明确不保证逻辑阅读顺序。 | MIT，依赖 pdfminer.six；跨平台 Python 包，无云端服务。 |

## 各项目的成熟做法

- **交互**：可从派生文本跳回原文位置；读者仍能看完整 PDF，而非只看 Markdown 重排。
- **数据**：每个对象带页码、文字、bbox、类型与可追溯来源；顺序与坐标是不同事实。
- **检索/模型**：解析在本机进行；这一步不把位置卡片发送给 DeepSeek，也不替换现有检索证据和译文。
- **引用**：原文 PDF 是权威来源。定位框是阅读辅助，不等于人工确认引用或公式解析。
- **失败**：没有文本层、旋转页或复杂双栏时，应显示未支持/需复核，不能伪造 bbox 或次序。

## 对 ResearchCopilot 的取舍

| 决定 | 采用方式 | 理由 |
| --- | --- | --- |
| 借鉴 bbox + 页码出处 | 定义 `PageSourceRegion`，当前页只读生成；坐标统一为 PDF 页面左上角的 point。 | 与已有 PDF.js 视图、公式裁剪坐标一致。 |
| 借鉴可视化验证 | 在译文页签列出少量当前页原文区域，点击可在中间 PDF 高亮并滚动定位。 | 读者能直接核对，不需要信任抽出的行文本。 |
| 调整内容粒度 | 先输出可定位的行/区域，不自动合并成“段落”，也不提供伪精确的行对行翻译。 | pdfplumber 本身不保证复杂阅读顺序；避免误导。 |
| 暂拒完整解析套件 | 暂不装 Docling/Marker/MinerU 模型。 | 当前问题只需位置验证，模型下载及授权成本尚无必要。 |

## 架构影响与兼容性

新增一个局部的 `PageSourceRegion` 数据结构，原因是现有 `ReadingAnchor` 只有页码/选中文字，不能表达 PDF 区域。它是原文锚点的细化，不建立新论文、会话或笔记存储。新的只读 API 从现有资料库路径取当前页 PDF；前端只在“译文”页签请求，点击卡片通过既有页码状态定位并高亮。原文和译文仍以 PDF/页码为单一权威；不会更改译文缓存或发送原文。当前论文/跨论文严格按 `paper_id`，切换时清掉旧高亮；不同会话共享同一 PDF 原文位置；本地位置检查不触云端；Python 依赖需在 macOS/Windows 都可安装。旋转页及无法给出可信框的内容不显示伪锚点。

## 数据与隐私边界

只读本机 PDF，可在内存中按页生成区域；不写索引、不调用 DeepSeek，不向浏览器以外的目的地发送数据。PDF 仍只由原有本地 `/file` 路由提供。

## 实现顺序与验收标准

1. 增加 pdfplumber 作为可复现依赖，以页码、宽高、文本和有效 bbox 返回当前页最多适量的可见文字区域。每个区域有稳定 ID；文本过短/框越界不展示。
2. 对空页返回空列表；无效页码/论文报错；旋转页与其他无法定位的版式以显式状态降级。
3. 浏览器“译文”页签点击某区域后，中间 PDF 滚动并显示对应框；切页/换论文后清除旧框。不会触发 DeepSeek。
4. 用真实 `sample.pdf` 第 5 页核对区域边界和高亮；自动测试覆盖正常与失败路径，前端构建通过。

## 暂不实现

本阶段不承诺段落/双栏阅读顺序、精确的译文分块、公式或表格 OCR。下个阶段须评测布局顺序与合并规则，合格后才把块与译文配对。
