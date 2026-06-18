#!/usr/bin/env bash
# import-template-from-image.sh — 从 PPT 模板截图生成“候选模板”的流程说明
#
# 重要：这不是一键导入 live 模板的脚本。依据图片生成新模板前，必须先校验
# 与现有 active 模板是否存在明显、可迁移、可复用的风格差异。
# 差异不足时禁止新增一级模板，只能归入现有模板 mode / 变体。
#
# 当前 active 模板：01 02 03 04 05 06 07 08 09 10 11 12 13
#
# 标准流程由 AI agent 执行：
# 1. 用户提供模板截图 / 参考图。
# 2. AI 使用 image 工具分析截图，抽取 candidate-style-dna.md：
#    - 使用场景
#    - 色彩系统（背景色、主色、辅助色、强调色、比例）
#    - 版式语法（留白、网格、分栏、标题区、页脚/页码）
#    - 图形语法（卡片、插画、照片、线框、箭头、泳道、图表、纹样等）
#    - 文字系统（标题气质、字号层级、正文密度、标注风格）
#    - 页面类型适配（cover/toc/content/data/transition/closing）
# 3. AI 读取 templates/TEMPLATE-DNA-INDEX.md，与 active 模板逐项比对：
#    - 使用场景
#    - 版式语法
#    - 图形语法
#    - 信息密度
#    - 页面类型扩展
#    - 视觉识别
# 4. 差异不足：拒绝导入，给出归并到现有模板 mode 的建议。
# 5. 差异明显：只允许创建 candidate 模板，不得直接写 live。
# 6. 将 candidate 模板 markdown 全文发给关哥审核；未审核通过，不得写入 templates/ live 目录。
#    candidate 模板正文只允许正向描述自身 DNA；差异/边界对比只放 difference-gate-report.md。
# 7. 模板文件审核通过后，candidate 才能生成 6 类样图：cover/toc/content/data/transition/closing。
# 8. 创建飞书样图审核文档，关哥明确确认后，才允许写入 templates/examples/<编号>/、正式模板文件并更新 README。

cat <<'EOF'
Template import workflow (candidate only):
1) analyze reference image -> candidate-style-dna.md
2) compare with active templates (01 02 03 04 05 06 07 08 09 10 11 12 13)
3) reject if no obvious reusable style difference
4) create candidate only if difference gate passes
5) send full candidate template markdown for review
6) only after template-file approval, generate 6 sample pages + Feishu review
7) after sample approval, promote to live template/examples and README
EOF
