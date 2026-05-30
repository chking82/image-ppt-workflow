#!/usr/bin/env bash
# ============================================================
# generate.sh — 基于 grsai API 的 PPT 生图脚本
# 集成自 grsai-image 技能，使 image-ppt-workflow 自包含
# 依赖: curl, jq
# 环境变量: GRSAI_API_KEY (必填)
# API: https://grsai.dakka.com.cn/v1/api/generate
# ============================================================
set -euo pipefail

BASE_URL="${GRSAI_BASE_URL:-https://grsai.dakka.com.cn}"
API_KEY="${GRSAI_API_KEY:?请设置 GRSAI_API_KEY}"

MODEL="gpt-image-2-vip"
PROMPT=""
ASPECT_RATIO="3840x2160"
IMAGE_SIZE="4K"
REPLY_TYPE="json"
REFERENCE_IMAGES=()
OUTPUT_DIR="./generated"
TIMEOUT=300

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
    --help|-h)
      echo "Usage: $0 --model MODEL --prompt PROMPT [OPTIONS]"
      echo "  --model, -m       模型名称 (默认: gpt-image-2-vip)"
      echo "  --prompt, -p      提示词 (必填)"
      echo "  --ratio, -r       比例/尺寸 (默认: 3840x2160)"
      echo "  --quality, -q     分辨率: 1K/2K/4K (默认: 4K)"
      echo "  --reply-type      json/stream/async (默认: json)"
      echo "  --image, -i       参考图 URL 或 base64 (可多次传)"
      echo "  --output, -o      输出目录 (默认: ./generated)"
      echo "  --output-file     直接指定输出文件名 (覆盖 OUTPUT_DIR)"
      echo "  --timeout, -t     超时秒数 (默认: 300)"
      echo "  --base-url        API 基础地址 (默认: 国内节点)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$PROMPT" ]]; then
  echo "❌ --prompt 是必填参数" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

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
