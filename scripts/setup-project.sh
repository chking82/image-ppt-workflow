#!/usr/bin/env bash
# setup-project.sh — 初始化 PPT 项目工作区
# 用法: bash scripts/setup-project.sh <project-name> [template-number]

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_DIR="${IMAGE_PPT_WORKSPACE:-${HOME}/image-ppt-workflow-workspace}"
TODAY=$(date +%Y-%m-%d)

PROJECT_NAME="${1:?用法: bash scripts/setup-project.sh <project-name> [template-number]}"
TEMPLATE_NUM="${2:-}"

PROJECT_DIR="${WORKSPACE_DIR}/${TODAY}-${PROJECT_NAME}"

echo "📁 创建项目目录: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}"/{prompts,slides}

# 如果有 template 编号，加载对应模板
if [[ -n "$TEMPLATE_NUM" ]]; then
    TEMPLATE_PATTERN="${SKILL_DIR}/templates/$(printf '%02d' "$((10#$TEMPLATE_NUM))")-"*.md
    TEMPLATE_MATCHES=( $TEMPLATE_PATTERN )
    if [[ ${#TEMPLATE_MATCHES[@]} -gt 0 && -f "${TEMPLATE_MATCHES[0]}" ]]; then
        TEMPLATE_FILE="${TEMPLATE_MATCHES[0]}"
        cp "$TEMPLATE_FILE" "${PROJECT_DIR}/selected-template.md"
        echo "✅ 已加载模板: $(basename "$TEMPLATE_FILE")"
    else
        echo "❌ 模板不存在: $TEMPLATE_PATTERN"
        exit 1
    fi
fi

echo "✅ 工作区已就绪: ${PROJECT_DIR}"
echo "   下一步: 将源资料写入 ${PROJECT_DIR}/source.md"
