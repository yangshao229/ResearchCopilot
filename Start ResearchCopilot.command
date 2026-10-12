#!/bin/zsh

cd "${0:A:h}" || exit 1
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

if [[ ! -f web/dist/index.html ]]; then
  echo "ResearchCopilot 页面尚未准备好。请按 README.md 的首次安装步骤构建网页。"
  read "?按回车键关闭窗口…"
  exit 1
fi

if [[ -x .venv/bin/research-copilot ]]; then
  .venv/bin/research-copilot serve
elif command -v uv >/dev/null 2>&1; then
  uv run --offline research-copilot serve
else
  echo "没有找到项目 Python 环境。请按 README.md 的首次安装步骤运行 uv sync。"
  read "?按回车键关闭窗口…"
  exit 1
fi

status=$?
if [[ $status -ne 0 ]]; then
  echo "ResearchCopilot 启动失败（退出码 $status）。请把本窗口的错误信息发给我。"
  read "?按回车键关闭窗口…"
fi
exit $status
