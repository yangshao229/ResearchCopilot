#!/bin/zsh

set -e

cd "${0:A:h}"
uv run research-copilot serve
