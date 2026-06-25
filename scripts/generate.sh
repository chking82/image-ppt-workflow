#!/usr/bin/env bash
# ============================================================
# generate.sh — 基于 grsai API 的 PPT 生图脚本
# 集成自 grsai-image 技能，使 image-ppt-workflow 自包含
# 依赖: curl, jq
# 环境变量: GRSAI_API_KEY (必填)
# API: https://grsai.dakka.com.cn/v1/api/generate
# ============================================================
set -euo pipefail

# --- 自动加载 workspace/.env（环境变量已存在则不覆盖）---
# 注意: 临时关闭 errexit，避免 .env 中命令替换行(如 printenv 空值)在 set -e 下中断加载
if [[ -z "${GRSAI_API_KEY:-}" ]]; then
  for envf in "$HOME/.openclaw/workspace/.env" "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." 2>/dev/null && pwd)/.env"; do
    if [[ -f "$envf" ]]; then
      set +e; set -a; . "$envf" 2>/dev/null; set +a; set -e
    fi
  done
fi

BASE_URL="${GRSAI_BASE_URL:-https://grsai.dakka.com.cn}"
API_KEY="${GRSAI_API_KEY:?请设置 GRSAI_API_KEY}"

MODEL="gpt-image-2-vip"
PROMPT=""
ASPECT_RATIO="2048x1152"
IMAGE_SIZE="2K"
REPLY_TYPE="json"
REFERENCE_IMAGES=()
OUTPUT_DIR="./generated"
TIMEOUT=300
MANIFEST_PATH=""
PROMPT_FILE=""
PAGE_NUM=""
PROJECT_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model|-m)       MODEL="$2"; shift 2 ;;
    --prompt|-p)      PROMPT="$2"; shift 2 ;;
    --ratio|-r)       ASPECT_RATIO="$2"; shift 2 ;;
    --quality|-q)     IMAGE_SIZE="$2"; shift 2 ;;
    --reply-type)     REPLY_TYPE="$2"; shift 2 ;;
    --image|-i)       REFERENCE_IMAGES+=("$2"); shift 2 ;;
    --output|-o)      OUTPUT_DIR="$2"; shift 2 ;;
    --output-file)    OUTPUT_FILE="$2"; shift 2 ;;
    --timeout|-t)     TIMEOUT="$2"; shift 2 ;;
    --base-url)       BASE_URL="$2"; shift 2 ;;
    --manifest)       MANIFEST_PATH="$2"; shift 2 ;;
    --prompt-file)    PROMPT_FILE="$2"; shift 2 ;;
    --page)           PAGE_NUM="$2"; shift 2 ;;
    --project)        PROJECT_NAME="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 --model MODEL --prompt PROMPT [OPTIONS]"
      echo "  --model, -m       模型名称 (默认: gpt-image-2-vip)"
      echo "  --prompt, -p      提示词 (必填)"
      echo "  --ratio, -r       比例/尺寸 (默认: 2048x1152)"
      echo "  --quality, -q     分辨率: 1K/2K/4K (默认: 2K)"
      echo "  --reply-type      json/stream/async (默认: json)"
      echo "  --image, -i       参考图 URL 或 base64 (可多次传)"
      echo "  --output, -o      输出目录 (默认: ./generated)"
      echo "  --output-file     直接指定输出文件名 (覆盖 OUTPUT_DIR)"
      echo "  --timeout, -t     超时秒数 (默认: 300)"
      echo "  --base-url        API 基础地址 (默认: 国内节点)"
      echo "  --manifest        manifest.json 路径 (正式流程必填，项目内相对路径)"
      echo "  --prompt-file     对应 prompt 文件路径 (正式流程必填，项目内相对路径)"
      echo "  --page            页码 (正式流程必填)"
      echo "  --project         项目名 (正式流程必填)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo "❌ --prompt 是必填参数" >&2
  exit 1
fi

is_bad_rel_path() {
  local p="$1"
  [[ "$p" == /* || "$p" == *".."* ]]
}

# 正式工作流要求 manifest 硬门禁；如需一次性调试，显式设置 IMAGE_PPT_ALLOW_NO_MANIFEST=1。
if [[ -z "$MANIFEST_PATH" && "${IMAGE_PPT_ALLOW_NO_MANIFEST:-}" != "1" ]]; then
  echo "❌ --manifest 是正式流程必填参数；如需临时调试，设置 IMAGE_PPT_ALLOW_NO_MANIFEST=1" >&2
  exit 1
fi

if [[ -n "$MANIFEST_PATH" ]]; then
  for required_name in MANIFEST_PATH PROMPT_FILE PAGE_NUM PROJECT_NAME; do
    if [[ -z "${!required_name:-}" ]]; then
      echo "❌ manifest 模式下缺少必填参数: $required_name" >&2
      echo "   需要同时传 --manifest --prompt-file --page --project" >&2
      exit 1
    fi
  done
  for path_value in "$MANIFEST_PATH" "$PROMPT_FILE" "$OUTPUT_DIR" "${OUTPUT_FILE:-}"; do
    if [[ -n "$path_value" ]] && is_bad_rel_path "$path_value"; then
      echo "❌ manifest 模式下路径必须是项目内相对路径，禁止绝对路径或 '..': $path_value" >&2
      exit 1
    fi
  done
fi

mkdir -p "$OUTPUT_DIR"


# ─── 写入 manifest ───
write_manifest() {
  local file_path="$1"
  local task_id_val="${2:-}"
  local status_val="${3:-succeeded}"
  if [[ -z "$MANIFEST_PATH" ]]; then return 0; fi
  mkdir -p "$(dirname "$MANIFEST_PATH")"
  local generated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local file_size="$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null || echo 0)"
  local rel_path="${file_path#./}"
  local new_entry
  new_entry=$(jq -n     --arg page "${PAGE_NUM:-}"     --arg prompt_file "${PROMPT_FILE:-}"     --arg generated_source "$rel_path"     --arg model "$MODEL"     --arg aspect_ratio "$ASPECT_RATIO"     --arg generated_at "$generated_at"     --arg task_id "$task_id_val"     --arg status "$status_val"     --argjson file_size "$file_size"     '{page:($page|select(. != "")|tonumber // null), prompt_file:$prompt_file, generated_source:$generated_source, model:$model, aspect_ratio:$aspect_ratio, generated_at:$generated_at, task_id:$task_id, status:$status, file_size:$file_size}')
  if [[ -f "$MANIFEST_PATH" ]]; then
    local existing="$(jq -c --arg path "$rel_path" '.slides |= map(select(.generated_source != $path))' "$MANIFEST_PATH" 2>/dev/null || cat "$MANIFEST_PATH")"
    echo "$existing" | jq --argjson entry "$new_entry" --arg project "${PROJECT_NAME:-}" --arg created_at "$generated_at" --arg version "1.0" '. + {version:$version, project:$project, created_at:(.created_at // $created_at), slides:((.slides // []) + [$entry])}' > "${MANIFEST_PATH}.tmp" && mv "${MANIFEST_PATH}.tmp" "$MANIFEST_PATH"
  else
    jq -n --argjson entry "$new_entry" --arg project "${PROJECT_NAME:-}" --arg created_at "$generated_at" --arg version "1.0" '{version:$version, project:$project, created_at:$created_at, slides:[$entry]}' > "$MANIFEST_PATH"
  fi
  echo "📋 manifest: $MANIFEST_PATH (+$rel_path)"
}


# 构建请求 JSON
IMAGES_JSON="[]"
if [[ ${#REFERENCE_IMAGES[@]} -gt 0 ]]; then
  IMAGES_JSON=$(printf '%s\n' "${REFERENCE_IMAGES[@]}" | jq -R . | jq -s .)
fi

PAYLOAD=$(jq -n \
  --arg model "$MODEL" \
  --arg prompt "$PROMPT" \
  --arg aspectRatio "$ASPECT_RATIO" \
  --arg replyType "$REPLY_TYPE" \
  --argjson images "$IMAGES_JSON" \
  '{model:$model, prompt:$prompt, aspectRatio:$aspectRatio, replyType:$replyType, images:$images}')

if [[ -n "$IMAGE_SIZE" ]]; then
  PAYLOAD=$(echo "$PAYLOAD" | jq --arg imageSize "$IMAGE_SIZE" '. + {imageSize:$imageSize}')
fi

echo "🎨 grsai 生图"
echo "   模型: $MODEL"
echo "   提示词: $PROMPT"
echo "   比例/尺寸: $ASPECT_RATIO"
[[ -n "$IMAGE_SIZE" ]] && echo "   分辨率: $IMAGE_SIZE"
echo "   模式: $REPLY_TYPE"
echo ""

# 提交请求
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/api/generate" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --max-time "$TIMEOUT")

STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')

if [[ "$STATUS" == "succeeded" ]]; then
  IMG_URL=$(echo "$RESPONSE" | jq -r '.results[0].url')
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  if [[ -n "${OUTPUT_FILE:-}" ]]; then
    FILENAME="${OUTPUT_DIR}/${OUTPUT_FILE}"
  else
    FILENAME="${OUTPUT_DIR}/grsai_${MODEL//[^a-zA-Z0-9]/_}_${TIMESTAMP}.png"
  fi
  curl -sL "$IMG_URL" -o "$FILENAME"
  echo "✅ 已保存: $FILENAME"
  echo "📎 URL: $IMG_URL"
  write_manifest "$FILENAME" ""
elif [[ "$STATUS" == "running" ]]; then
  TASK_ID=$(echo "$RESPONSE" | jq -r '.id')
  echo "⏳ 任务进行中 (ID: $TASK_ID)"
  echo "   进度: $(echo "$RESPONSE" | jq -r '.progress // "?"')%"
  # 轮询直到完成
  for i in $(seq 1 30); do
    sleep 10
    RESULT=$(curl -s "$BASE_URL/v1/api/result?id=$TASK_ID" \
      -H "Authorization: Bearer $API_KEY")
    NEW_STATUS=$(echo "$RESULT" | jq -r '.status')
    NEW_PROGRESS=$(echo "$RESULT" | jq -r '.progress // "?"')
    echo "   [$i] 状态: $NEW_STATUS, 进度: ${NEW_PROGRESS}%"
    if [[ "$NEW_STATUS" == "succeeded" ]]; then
      IMG_URL=$(echo "$RESULT" | jq -r '.results[0].url')
      TIMESTAMP=$(date +%Y%m%d_%H%M%S)
      if [[ -n "${OUTPUT_FILE:-}" ]]; then
        FILENAME="${OUTPUT_DIR}/${OUTPUT_FILE}"
      else
        FILENAME="${OUTPUT_DIR}/grsai_${MODEL//[^a-zA-Z0-9]/_}_${TIMESTAMP}.png"
      fi
      curl -sL "$IMG_URL" -o "$FILENAME"
      echo "✅ 已保存: $FILENAME"
      echo "📎 URL: $IMG_URL"
      write_manifest "$FILENAME" "$TASK_ID"
      exit 0
    elif [[ "$NEW_STATUS" == "failed" || "$NEW_STATUS" == "violation" ]]; then
      echo "❌ 生成失败: $NEW_STATUS"
      echo "$RESULT" | jq '.'
      exit 1
    fi
  done
  echo "⏰ 轮询超时，任务 ID: $TASK_ID"
  echo "   手动查询: curl -s '$BASE_URL/v1/api/result?id=$TASK_ID' -H 'Authorization: Bearer \$GRSAI_API_KEY'"
  exit 1
else
  echo "❌ 生成失败: $STATUS"
  echo "$RESPONSE" | jq '.'
  exit 1
fi
