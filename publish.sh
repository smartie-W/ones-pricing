#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ $# -eq 0 ]]; then
  echo "用法: ./publish.sh \"提交说明\""
  exit 1
fi

COMMIT_MESSAGE="$*"

echo "1/3 运行价格校验..."
python3 validate_pricing.py

if [[ -z "$(git status --porcelain)" ]]; then
  echo "没有检测到代码变更，无需发布。"
  exit 0
fi

echo "2/3 提交代码..."
git add .
git commit -m "$COMMIT_MESSAGE"

echo "3/3 推送到远端..."
git push

echo "发布完成。"
