# 开源自测版：在自己的电脑上运行

这是单人本地自测版，不是可直接放到公网让多人登录的网站。服务默认只监听 `127.0.0.1`，没有账号认证。请不要设置 `--host 0.0.0.0`、开放路由器端口，或用公网反向代理发布这个实例。

## 你需要准备什么

- macOS 或 Windows 电脑；Python 3.12 由 [uv](https://docs.astral.sh/uv/getting-started/installation/) 管理。
- [Node.js](https://nodejs.org/) 20.19+ 或 22.12+，以及随之安装的 npm（前端使用 Vite 8）。
- 本仓库源码，包含 `uv.lock` 和 `web/package-lock.json`。可在仓库发布后使用 GitHub 的 **Code → Download ZIP**，解压到自己的文件夹；也可用 Git 克隆。不要把两台电脑的 `.venv`、`web/node_modules` 或模型缓存相互复制。
- 需要 AI 问答／翻译时，再准备自己的 DeepSeek API Key；只阅读 PDF 和用本地关键词检索不需要 Key。Obsidian 也是可选的。

在终端进入**解压后的项目根目录**（能看见 `pyproject.toml` 和 `web/` 的地方）。Windows 可在该文件夹地址栏输入 `powershell` 后回车；macOS 可用终端的 `cd` 命令进入该目录。

## 第一次安装（macOS / Windows PowerShell 通用）

```text
uv sync --locked
npm --prefix web ci
npm --prefix web run build
```

`uv sync --locked` 按项目锁文件建立独立 `.venv`；`npm ci` 按前端锁文件全新安装依赖；`build` 生成本机使用的网页文件。首次安装需要联网且可能较慢，尤其是 Python 的模型运行依赖。若 `--locked` 报错，请反馈，不要自行删除锁文件来掩盖不一致。

随后从项目根目录启动：

```text
uv run --no-sync research-copilot serve
```

终端会打印实际本机地址并尝试打开默认浏览器，通常是 `http://127.0.0.1:8000/`；若端口被占用，会改用 8001–8019。**请以本次终端打印的地址为准**。保持终端窗口运行；按 `Ctrl+C` 停止。macOS 首次安装后也可以双击项目中的 `Start ResearchCopilot.command`。

Windows 上如 PowerShell 提示找不到 `uv` 或 `npm`，请先按各自官方安装说明安装并重新打开 PowerShell；不需要改系统的脚本执行策略。Windows 上不要双击 macOS 的 `.command` 文件。此流程已写成跨平台命令，但正式发布前仍需在一台实际 Windows 电脑验证，发现差异请提交反馈。

## 可选：DeepSeek 与 Obsidian

只在本机把 `.env.example` 复制成 `.env`，并用文本编辑器把其中的占位 Key 改为你自己的 Key：

```text
DEEPSEEK_API_KEY=你的实际Key
```

macOS 终端可运行 `cp .env.example .env`；Windows PowerShell 可运行 `Copy-Item .env.example .env`。不要把 `.env` 发给维护者、放进 Issue、录屏或提交到 Git。DeepSeek API 会在你主动点击问答/翻译时收到问题与选定的证据或页面文字，可能产生费用；本地 PDF 原文件不会因普通阅读自动上传。

Obsidian 不影响基本阅读。若要建立个人知识库，请在 Obsidian 中另建 Vault（不要放进本项目目录），再按[使用说明书](USER_GUIDE.md)的“连接 Obsidian”步骤，在网页中填写**自己的** Vault 绝对路径；不要使用维护者电脑的路径。PDF、Vault、索引、模型、阅读记录都不随 Git 同步。备份前先读[数据备份说明](VAULT_BACKUP_RECOVERY.md)。

## 建议自测的完整路径

1. 不配置 Key 启动，确认能打开页面，并导入你有权使用的一份 PDF。检查页数、翻页、目录和本地关键词证据。
2. 有 Key 时，再试一页翻译和一个具体问题；逐一点击引用，确认确实回到 PDF 原文页。复杂公式、双栏、扫描件仍须人工核对。
3. 若使用 Obsidian，先在自己的 Vault 预览并确认“论文目录入库”；知识笔记只有你核对并再次确认后才会保存。
4. 关闭终端，确认网页不再可用；重新启动后，检查本地论文与阅读记录仍在。

## 出问题时

- 页面显示“无法连接”：确认启动终端还在运行，打开它打印的完整地址；代理/VPN 需要绕过 `127.0.0.1`。
- `uv sync` 或 `npm ci` 失败：附上操作系统、Python/uv/Node/npm 版本和**脱敏后的**报错，不要上传 `.env` 或私人 PDF。
- 无 Key 时云端问答/翻译不可用是预期行为；语义检索还需要本机另行准备 Embedding 模型，见[使用说明书](USER_GUIDE.md)。关键词检索可作为不下载模型的起点。
- Safari 页面短暂出现又消失：请记录浏览器版本、复现步骤及脱敏后的错误信息；不要只报“白屏”。

请通过 GitHub 的 Bug 或体验反馈模板提交问题。截图前遮住论文正文、PDF 文件名、Vault 路径、API Key 和个人信息；若问题只有私人论文能复现，先尝试用公开论文或不含原文的最小步骤重现。

## 发布者检查清单

仓库所有者正式公开前，应在**准备公开的提交状态和全部 Git 历史**检查密钥、私人 PDF、Vault、模型与生成数据；检查依赖与静态资源许可；从干净目录按本指南安装并测试；确认不会误把本机 `.env` 或 Vault 复制进发布包。公开后，每次推送前仍应重复检查新改动；本指南本身不会上传本机数据。
