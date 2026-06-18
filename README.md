# image-ppt-workflow 🦞

AI PPT 生成技能——基于 grsai API（gpt-image-2-vip）直接生成整页幻灯片图片，合成 PPTX，自动写入中文演讲稿备注。**自带生图脚本，零外部依赖。**

## 快速开始

### 1. 获取 API Key

本技能通过 grsai 平台调用 gpt-image-2-vip / nano-banana-2 等模型生图。

1. 打开 https://grsai.ai/zh/dashboard/api-keys
2. 注册/登录账号
3. 在「API Keys」页面创建一个新的 API Key
4. 复制 Key 并设置到环境变量：

```bash
export GRSAI_API_KEY="***"
```

推荐写入 `~/.bashrc` 或 OpenClaw 的 `openclaw.json` 环境变量配置中。

### 2. 依赖

- `curl` — API 调用
- `jq` — JSON 解析
- `python3` + `python-pptx` + `Pillow` — PPTX 合成

### 3. 使用

```bash
# 初始化项目（默认创建到 ~/image-ppt-workflow-workspace/<日期>-<项目名>/）
SKILL_DIR="$HOME/.openclaw/skills/image-ppt-workflow"
"$SKILL_DIR"/scripts/setup-project.sh demo 10

# 进入项目目录；后续全部使用项目内相对路径
cd ~/image-ppt-workflow-workspace/$(date +%F)-demo

# 生图
"$SKILL_DIR"/scripts/generate.sh \
  --model gpt-image-2-vip \
  --prompt "A PPT slide in Chinese traditional style..." \
  --ratio 2048x1152 \
  --output slides/ \
  --output-file "01-slide-cover.png" \
  --manifest slides-manifest.json \
  --prompt-file prompts/01-slide-cover.md \
  --page 1 \
  --project "$(basename "$PWD")"

# 基于参考图编辑
IMG_B64=$(base64 -w0 original.png)
"$SKILL_DIR"/scripts/generate.sh \
  --model gpt-image-2-vip \
  --prompt "Edit this slide: ..." \
  --ratio 2048x1152 \
  --image "data:image/png;base64,$IMG_B64" \
  --output slides/ \
  --output-file "02-slide-toc.png" \
  --manifest slides-manifest.json \
  --prompt-file prompts/02-slide-toc.md \
  --page 2 \
  --project "$(basename "$PWD")"

# 合成 PPTX
python3 "$SKILL_DIR"/scripts/merge_to_pptx.py \
  --slides slides/ \
  --notes speaker-notes.md \
  --output demo主题汇报.pptx \
  --require-manifest slides-manifest.json
```

## 脚本说明

### 正式脚本

| 脚本 | 用途 |
|------|------|
| `scripts/setup-project.sh` | 初始化项目目录，默认创建到 `~/image-ppt-workflow-workspace/<日期>-<项目名>/` |
| `scripts/validate-prompts.py` | 校验每页 Prompt 是否符合模板、中文完整性、密度和版式规则 |
| `scripts/manifest.py` | 校验 `slides-manifest.json`，对齐 `slides/` 与 `prompts/` |
| `scripts/generate.sh` | 调用 grsai API 生图，支持参考图编辑，并自动登记 manifest |
| `scripts/merge_to_pptx.py` | 幻灯片图片 + 演讲备注 → PPTX，正式流程必须传 `--require-manifest` |
| `scripts/import-template-from-image.sh` | 从截图导入新模板的流程占位说明 |

### 图片导入新模板：差异门禁

`scripts/import-template-from-image.sh` 不是一键入库脚本，只是候选模板导入流程说明。依据参考图片生成新模板前，必须先校验它与当前 active 模板（`01 02 03 04 05 06 07 08 09 10 11 12 13`）是否存在明显、可迁移的风格差异。

如果只是配色、行业、主题、素材或单页构图变体，禁止新增一级模板，应归入最接近的现有模板 mode。只有通过差异校验、候选模板 markdown 全文审核、6 类样图（cover / toc / content / data / transition / closing）飞书审核，并获得用户明确确认后，才允许进入 live 模板库并更新 README。候选模板文件未审核通过前，不得写入 `templates/` live 目录。
模板 markdown 正文只允许正向描述本模板 DNA；“与现有模板的边界/不是某模板”等差异对比只放差异校验报告，不写入正式模板文件。


> 硬规则：不允许用 PIL / SVG / HTML / Canvas / matplotlib / PPT shapes / 截图渲染 / 文字叠加脚本来画图或补字。失败就改 prompt 重试，不能代码兜底。

## 工作流程

详见 [SKILL.md](./SKILL.md) 的 10 步工作流：

1. 输入资料 → 2. 内容分析 → 3. 方案确认 → 4. 生成大纲 → 5. 审核大纲
→ 6. 生成每页 Prompt → 7. 生图 → 8. 生成备注 → 9. 合成 PPTX → 10. 迭代

## 分辨率规范

PPT 幻灯片默认 **2K 16:9（2048×1152）**，通过 `--ratio 2048x1152` 指定。
支持 1K / 2K / 4K，根据 `--quality` 参数选择。

## 模板清单

内置 13 套 active 一级风格模板，覆盖主流汇报场景：

### 01 东方美学 · 纸感极简
文化/学术/品牌故事

![封面](templates/examples/01/cover.jpg)
![目录](templates/examples/01/toc.jpg)
![内容](templates/examples/01/content.jpg)
![数据](templates/examples/01/data.jpg)
![过渡](templates/examples/01/transition.jpg)
![结尾](templates/examples/01/closing.jpg)

### 02 手绘漫画 · 趣味叙事
产品教学/用户指南/科普

![封面](templates/examples/02/cover.jpg)
![目录](templates/examples/02/toc.jpg)
![内容](templates/examples/02/content.jpg)
![数据](templates/examples/02/data.jpg)
![过渡](templates/examples/02/transition.jpg)
![结尾](templates/examples/02/closing.jpg)

### 03 糖果色职场述职 · 几何轻汇报
个人述职/岗位汇报/阶段总结/轻量团队复盘

![封面](templates/examples/03/cover.jpg)
![目录](templates/examples/03/toc.jpg)
![内容](templates/examples/03/content.jpg)
![数据](templates/examples/03/data.jpg)
![过渡](templates/examples/03/transition.jpg)
![结尾](templates/examples/03/closing.jpg)

### 04 科技数据 · 未来感
AI/算力/平台发布/数据驱动

![封面](templates/examples/04/cover.jpg)
![目录](templates/examples/04/toc.jpg)
![内容](templates/examples/04/content.jpg)
![数据](templates/examples/04/data.jpg)
![过渡](templates/examples/04/transition.jpg)
![结尾](templates/examples/04/closing.jpg)

### 05 生活方式 · 温暖治愈
消费品/美妆护肤/生活方式/食品/生活服务/母婴

![封面](templates/examples/05/cover.jpg)
![目录](templates/examples/05/toc.jpg)
![内容](templates/examples/05/content.jpg)
![数据](templates/examples/05/data.jpg)
![过渡](templates/examples/05/transition.jpg)
![结尾](templates/examples/05/closing.jpg)

### 06 杂志排版 · 编辑设计
时尚品牌/设计作品集/年度品牌报告/发布会 Keynote/高端产品发布

![封面](templates/examples/06/cover.jpg)
![目录](templates/examples/06/toc.jpg)
![内容](templates/examples/06/content.jpg)
![数据](templates/examples/06/data.jpg)
![过渡](templates/examples/06/transition.jpg)
![结尾](templates/examples/06/closing.jpg)

### 07 学术答辩 · 规范严谨
毕业论文答辩/学术汇报/科研基金申请（机构主色槽位：默认学术深蓝 #003F5C，可换清华紫 #660874 / 复旦蓝 #003D82 / 武大红 #9D2727）

![封面](templates/examples/07/cover.jpg)
![目录](templates/examples/07/toc.jpg)
![内容](templates/examples/07/content.jpg)
![数据](templates/examples/07/data.jpg)
![过渡](templates/examples/07/transition.jpg)
![结尾](templates/examples/07/closing.jpg)

### 08 国潮插画 · 新中式
文旅推广/非遗品牌/节日营销/国潮产品发布/文化 IP

![封面](templates/examples/08/cover.jpg)
![目录](templates/examples/08/toc.jpg)
![内容](templates/examples/08/content.jpg)
![数据](templates/examples/08/data.jpg)
![过渡](templates/examples/08/transition.jpg)
![结尾](templates/examples/08/closing.jpg)

### 09 数据报告 · 麦肯锡风
战略咨询/行业研究/尽调报告/董事会汇报

![封面](templates/examples/09/cover.jpg)
![目录](templates/examples/09/toc.jpg)
![内容](templates/examples/09/content.jpg)
![数据](templates/examples/09/data.jpg)
![过渡](templates/examples/09/transition.jpg)
![结尾](templates/examples/09/closing.jpg)

### 10 现代企业 · 数据驱动
商业汇报/战略规划/数据分析/高管汇报

![封面](templates/examples/10/cover.jpg)
![目录](templates/examples/10/toc.jpg)
![内容](templates/examples/10/content.jpg)
![数据](templates/examples/10/data.jpg)
![过渡](templates/examples/10/transition.jpg)
![结尾](templates/examples/10/closing.jpg)

### 11 党政党建 · 红色主旋律

![封面](templates/examples/11/cover.jpg)
![目录](templates/examples/11/toc.jpg)
![内容](templates/examples/11/content.jpg)
![数据](templates/examples/11/data.jpg)
![过渡](templates/examples/11/transition.jpg)
![结尾](templates/examples/11/closing.jpg)

### 12 企业项目管理 · 红蓝专业
项目汇报/进度跟踪/季度总结/PMO战情室

![封面](templates/examples/12/cover.jpg)
![目录](templates/examples/12/toc.jpg)
![内容](templates/examples/12/content.jpg)
![数据](templates/examples/12/data.jpg)
![过渡](templates/examples/12/transition.jpg)
![结尾](templates/examples/12/closing.jpg)

### 13 企业架构 · 深蓝专业
架构汇报/组织管理/战略规划/数据中台蓝图

![封面](templates/examples/13/cover.jpg)
![目录](templates/examples/13/toc.jpg)
![内容](templates/examples/13/content.jpg)
![数据](templates/examples/13/data.jpg)
![过渡](templates/examples/13/transition.jpg)
![结尾](templates/examples/13/closing.jpg)

## 模型选择

| 优先级 | 模型 | 中文渲染 |
|--------|------|---------|
| 首选 | `gpt-image-2-vip` | ✅ 最佳 |
| 备选 | `nano-banana-2` | ✅ 良好 |
| ❌ 避免 | `gpt-image-2`（非 vip） | 中文易乱码 |
