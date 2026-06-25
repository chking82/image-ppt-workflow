---
name: image-ppt-workflow
description: 制作 PPT / 幻灯片 / 汇报材料的默认工作流。基于 grsai API（gpt-image-2-vip）整页生成幻灯片图片并合成 PPTX，自动写入中文演讲稿备注，每页独立 prompt、独立生成、可单页迭代。触发场景：用户要做 PPT、幻灯片、汇报材料、演示文稿、路演/方案展示页。
triggers:
  - pattern: "PPT|ppt|幻灯片|汇报材料|演示文稿|演示文档|路演|做个?PPT|slides?"
    description: "PPT/幻灯片制作请求"
metadata:
  openclaw:
    primaryEnv: GRSAI_API_KEY
---
# image-ppt-workflow Skill

> 基于 grsai API（gpt-image-2-vip）生成整页幻灯片图片，合成 PPTX。
> 自动写入中文演讲稿备注。每页独立 prompt、独立生成、可单页迭代。

**核心流程**: `输入 → 分析 → 检索 → 确认 → 大纲 → Prompt → 生图 → 备注 → 合成PPTX → 迭代`

## 辅助脚本

| 脚本 | 功能 |
|------|------|
| `scripts/setup-project.sh <name> [模板编号]` | 初始化项目目录、加载模板 |
| `scripts/validate-prompts.py <项目目录>` | 校验每页 Prompt 是否符合模板规则 |
| `scripts/manifest.py check/reconcile/reconcile-prompts <manifest>` | 校验 slides manifest 完整性（防退化）|
| `scripts/generate.sh` | 单页生图（gpt-image-2-vip / nano-banana-2），自动登记 manifest |
| `scripts/merge_to_pptx.py` | 合并图片+备注为 PPTX，支持 `--require-manifest` 硬门禁 |

## 工作流

### 强制断点总则（默认必审）

以下断点默认必须获得关哥明确反馈，不能用“未回复/沉默/我觉得差不多”当作通过：
1. **方案确认**（Step 3）——风格、受众、页数、密度、叙事弧线确认后才能建大纲。
2. **大纲审核**（Step 5）——每页标题、结构、顺序确认后才能写 Prompt。
3. **Prompt 审核**（Step 6）——每页 Prompt 确认后才能生图。
4. **样稿审核**（Step 7b）——首批样稿确认后才能继续批量生成剩余页面。

**全量复审规则**：大纲或 Prompt 一旦修改，必须把修改后的完整版本重新发给关哥审核，不能只发修改点、diff、摘要或“改好了”。
- 大纲复审：发送完整 `outline.md` 的每页标题、结构、关键内容、视觉规格、版式建议。
- Prompt 复审：必须发送每个 Prompt 文件的完整正文内容；如页数过多，可分批发送，但每批必须包含对应 Prompt 文件的完整内容，不能只发文件清单、文件名、变更段落或摘要。
- 获得明确确认前，不得进入下一步。

除非关哥在当前任务里明确说“跳过某个审核/全程免审”，否则一律按必审执行。

### Step 1: 输入资料
将用户提供的内容保存为 `~/image-ppt-workflow-workspace/<项目>/source.md`。

**路径规范（硬规则）**：
- 项目目录默认放在 `~/image-ppt-workflow-workspace/<日期>-<项目名>/`，不要放到 skill 目录下。
- 项目内引用一律使用相对路径：`source.md`、`prompts/...`、`slides/...`、`slides-manifest.json`。
- 执行生图/合成命令时，先 `cd ~/image-ppt-workflow-workspace/<项目>/`，再传项目内相对路径。
- `slides-manifest.json` 里的 `prompt_file` 和 `generated_source` 必须是项目内相对路径，禁止写本机绝对路径（例如 `/absolute/path/...`）。

### Step 2: 内容分析
分析 source.md 写入 `analysis.md`（类型/受众/页数/风格/重点方向）。AI 自主推理，不需用户确认。

### Step 2b: 深度信息检索（⛔ 用户只给主题时必填）
用户只给主题没给资料时，必须先 web_search + tavily_extract 检索事实，基于实际资料出提纲。有完整资料时可跳过。

### Step 3: 方案确认（⛔ 阻塞）
向用户展示 8 项方案，等待确认：
1. **风格模板** — 列出 13 个 active 一级模板（见附录），不可省略
2. **风格微调** — 品牌色/元素偏好
3. **受众** — 高管/客户/专家/内部/公众
4. **页数** — 建议 X 页
5. **密度模式** — 文档模式（默认，250-350字/页）vs 演讲模式（80-150字/页）
6. **叙事弧线** — beat 序列（setup→tension→resolution→proof→action）
7. **大纲审核** — 默认必审，必须等关哥确认
8. **Prompt 审核** — 默认必审，必须等关哥确认

用户明确确认后才进入下一步。方向不对，后面越精美越浪费。

### Step 3b: 加载模板
运行 `scripts/setup-project.sh <项目名> <模板编号>`，将选中模板保存为 `selected-template.md`。

默认会创建到：
```bash
~/image-ppt-workflow-workspace/<日期>-<项目名>/
```

如需临时改工作区，可用：
```bash
IMAGE_PPT_WORKSPACE=/your/workspace "$SKILL_DIR"/scripts/setup-project.sh <项目名> <模板编号>
```

### Step 4: 生成大纲（⛔ 强制结构规则）
输出 `outline.md`，必须遵循：
```
封面页 → 目录页 → [过渡页 → 内容页×N] ×M章节 → 结尾页
```
- 多章节（>1章）时必须有过渡页
- 每页包含：类型、Beat、叙事目标、关键内容、视觉规格、版式建议
- 同时输出 `narrative-arc.md`（beat 序列 + 信心拐点 + 呼吸页）

### Step 4b: 内容厚度检查（⛔ 质量门禁，2026-06-13 引入）

**借鉴自 GordenSun/GordenSuperPPTSkills §0**："排版太简单几乎都是因为内容太薄"。

每页内容页的最低量化标准：

| 项 | 最低要求 |
|---|---|
| 导语 | 1 句（含 2-3 个高亮关键词）|
| 模块数 | ≥ 3 个并列模块（每模块 标题 + 2-3 要点 + 1 特大号指标）|
| 信息点数 | ≥ 15 个文字信息点（推荐 20+）|
| 底部横幅 | 1 条通栏总结（推荐）|

**内容薄时的处理**：
- 先做厚结构化拆解（把"上市"拆成 时间/募资额/意义/估值）
- 不可编造数据
- 不可仅靠放大字号填白

**自动校验**（`validate-prompts.py` 已加密度检查，详见附录四）：
- 信息点数 < 15 → 警告
- < 10 → 报错

### Step 5: 审核大纲（⛔ 阻塞，默认必审）
展示完整大纲让用户确认，必须包含每页标题、结构、关键内容、视觉规格、版式建议。可删页、调顺序、补商业闭环、调 beat 分配。
如根据反馈修改了大纲，必须重新发送修改后的完整大纲复审，不能只发修改点。
必须获得关哥明确反馈后才进入 Step 6；未回复不算通过。

### Step 6: 生成 Prompt（⛔ 核心步骤）
**AI 基于模板规则+大纲内容手写每页 Prompt**，写入 `prompts/XX-slide-xxx.md`。

> ⚠️ Prompt 生成不能依赖脚本，必须 AI 手写以确保质量。脚本 `validate-prompts.py` 仅用于事后校验。

#### 铁律（写完后运行 `validate-prompts.py` 逐项检查）
1. **中文文字必须完整写入 prompt** — 标题、正文、标注、引语一个都不能少，原样写入英文 prompt
2. **可见文字中文优先（硬门禁，2026-06-16）** — prompt 的设计指令可以英文写，但凡是会出现在画面上的文字（Title/Subtitle/label/caption/footer/kicker/masthead/axis/legend/row/column/annotation 等字段里的引号内容）默认必须中文；英文只允许极少数必要缩写白名单（AI/API/GPU/KPI/ROI/Q1 等），且必须有中文语境。`CONTENTS / ISSUE / Thanks / Executive insight / ROADMAP / ABSTRACT / SECTION / VOL` 等一律改中文。
3. **标题必须是判断句** — 不是名词短语（见附录二）
4. **内部语言净化** — setup/tension/beat 等术语不能出现在客户可见文案（见附录二）
5. **色彩必须来自模板** — 不能凭空发明颜色
6. **避免内部术语** — prompt 中不出现 setup/tension/beat 等编排术语


#### 模板身份与去重规则（2026-06-18）

写 Prompt 前先查 `templates/TEMPLATE-DNA-INDEX.md`，确认选择的是当前 13 个 active 模板之一。

- 后续新增模板必须有独立使用场景、独立版式语法、独立图形语法、独立页面结构；如果只是配色/行业/内容变体，必须归入已有模板 mode。
- 模板不是越多越好。边界说不清的相近模板应合并，而不是靠一堆“差异边界”硬撑。
- 模板文件只做正向 DNA 描述；与现有模板的差异对比只放导入时的差异校验报告。

#### 图片导入新模板差异门禁（硬规则，2026-06-18）

用户提供参考图片，希望据此导入/生成新模板时，必须先执行“现有模板差异校验”。没有明显风格差异时，不允许新增 active 一级模板，只能归入最接近的现有模板 mode / 变体。

**当前 active 模板清单**：`01 02 03 04 05 06 07 08 09 10 11 12 13`

##### A. 先抽取参考图风格 DNA

使用 `image` 工具或人工视觉分析，形成 `candidate-style-dna.md`，至少记录：

1. **使用场景**：汇报/教学/学术/架构/项目/数据报告/生活方式等。
2. **色彩系统**：背景、主色、辅助色、强调色、色彩比例。
3. **版式语法**：留白比例、网格结构、分栏方式、标题区、页脚/页码习惯。
4. **图形语法**：卡片、插画、照片、线框、箭头、泳道、图表、纹样、手绘、地图、器物等。
5. **文字系统**：标题气质、字号层级、正文密度、标注风格、中文/英文呈现方式。
6. **页面类型适配**：能否稳定扩展为 cover / toc / content / data / transition / closing 六类页面。

禁止只写“高级”“科技感”“商务风”这类泛词。

##### B. 与 active 模板逐项比对

必须读取 `templates/TEMPLATE-DNA-INDEX.md`，并与所有 active 模板比较：

| 维度 | 判断问题 |
|---|---|
| 使用场景 | 是否服务一个现有模板无法稳定覆盖的场景？ |
| 版式语法 | 是否有不同于现有模板的布局结构，而不只是换配色？ |
| 图形语法 | 是否有独立图形语言，而不只是换图标/换行业素材？ |
| 信息密度 | 是否有独立的内容承载方式？ |
| 页面类型扩展 | 是否能自然扩展为 6 类页面，而不是只有一张图好看？ |
| 视觉识别 | 拿掉主题文字后，是否仍能一眼区分于现有模板？ |

##### C. 差异通过标准

只有同时满足以下条件，才允许进入候选模板流程：

- 至少 **3 个维度** 与最相近 active 模板存在明确差异；
- 差异是可迁移的视觉语法，不是单次项目内容；
- 能明确写出“为什么不能归入现有模板 mode”；
- 能设计出 6 类页面样图 prompt。

##### D. 差异不足时的处理

差异不足时必须拒绝新增一级模板，并给出归并建议，例如：

- 归入 09 的红蓝诊断 / 咨询数据报告 mode；
- 归入 05 的生活洞察报告 mode；
- 归入 10 的现代企业数据驱动 mode；
- 归入 13 的架构蓝图 mode；
- 或归入其他最接近 active 模板。

##### E0. 模板文件只做正向 DNA 描述（硬规则，2026-06-18）

图片导入生成的模板 markdown 不得包含独立的“与现有模板的边界”章节，也不得把“不是 01 / 不是 08 / 不是 09”作为模板正文结构。

差异比对、相似模板、为什么不能合并，只能放在 `difference-gate-report.md` 或飞书审核文档的差异校验部分。正式模板文件内部必须像 01 模板一样正向描述自身 DNA：一句话定位、必须出现的视觉锚点、风格强化描述、页面级锚点、页面类型模板和过滤清单。

如确需防混淆，只能改写成正向约束，合并进“必须出现的视觉锚点”“风格强化描述”“风格纯度要求”或“强制禁止”。

##### E. 候选模板不得直接入 live

通过差异校验后，也只能创建 candidate，不得直接写入 live 模板库。必须继续完成：

1. 写 `candidate-style-dna.md`；
2. 写候选模板 markdown；
3. **模板文件审核（硬门禁）**：将候选模板 markdown 全文发送给关哥审核，必须获得明确确认；未确认前不得写入 `templates/` live 目录，也不得宣称模板已落地；
4. 模板文件审核通过后，才能基于该 candidate 生成 6 类样图：cover / toc / content / data / transition / closing；
5. 创建飞书样图审核文档；
6. 关哥明确确认样图；
7. 才能覆盖到 `templates/examples/<编号>/`、写入/更新正式模板文件，并更新 README。

未通过差异校验、未通过模板文件审核或未通过 6 页样图审核，一律不得新增 active 一级模板。


#### 特殊页模板契约（硬门禁，2026-06-15）

写封面/目录/过渡/结尾页 Prompt 时，必须先读取 `selected-template.md` 中对应页面类型规范和「特殊页硬规则」。特殊页不允许套用内容页 frame_kind。

| 页面类型 | 推荐 frame_kind | 硬要求 |
|---|---|---|
| 封面页 | `hero_poster` | 主视觉 + 大标题 + 副标题/题跋 + 印章 + 大留白；禁止 bento/grid/cards/dashboard |
| 目录页 | `toc_list_illustration` | 左侧章节列表 + 右侧大面积插画/纹样/留白；禁止复杂 dashboard/数据页化 |
| 过渡页 | `chapter_divider` | 居中超大章节编号 + 标题在编号下方 + 10-18% 低透明背景 + 极简留白；禁止左右分栏/卡片/流程图/地图/内容堆叠 |
| 结尾页 | `closing_poster` | 居中结束语或 slogan + 印章/Logo + 底部淡纹样；禁止新增章节/复杂图表/信息卡片 |

`validate-prompts.py` 对特殊页实行硬校验；失败不得生图。若模板 examples 有 `transition.png` / `closing.png`，写 Prompt 前必须参考；若 examples 缺失，则严格执行上述契约，不得自创内容页式布局。

#### 契约 vs 模板：谁管什么（2026-06-15 引入）

> 上面的「特殊页硬规则」与模板里的「页面类型模板」名字像、容易被混，但**是两套东西、读两份、作用在不同对象**。

| 维度 | 特殊页硬规则 · 封面页契约 | 页面类型模板 · 封面页 |
|---|---|---|
| 性质 | 硬门禁（不满足 fail） | 美学指导（不满足不 fail，但画风走偏） |
| 数量 | 12 个 active 模板**全通用**一套 | 12 个 active 模板**各自一套** |
| 定的是什么 | 底线（必须含什么、不能含什么） | 风格倾向（在这个模板里长啥样） |
| 谁读 | `validate-prompts.py` 读 → P10/P13 校验 | 生图模型读 → 拿去画图 |
| 作用对象 | 决定**让不让画** | 决定**画成什么样** |

举例秦始皇 08 国潮封面：
- **契约**说：必须有主视觉+大标题+印章，不能有 3+ 卡片，frame_kind 必须 `hero_poster`
- **08 国潮模板**说：插画占 40-60%，故宫红印章在底部，书法感标题，左侧竖排副标题

两者都满足才是合格的「08 国潮风格封面页」。

视觉上可以这样叠：

```
                    [16:9 2K 通用规格]
                            ↓
   ┌────────────────────────┴────────────────────────┐
   ↓                                                  ↓
[页面类型模板·封面页]            [特殊页硬规则·封面页契约]
   风格指导（每模板不同）         硬门禁（12 个 active 模板通用）
   写给 nano-banana 看           写给 validate-prompts 校验
            ↓                                  ↓
       画成什么样                       让不让画
```

> **来源**：2026-06-15 秦始皇复盘。复盘前模板里只有美学指导、没契约，封面被画成 3 卡片堆叠、校验脚本全部放行。补契约为「底裤」 — 不管选哪个模板，封面都不能烂成 3 卡片。

逐页检查清单（2026-06-15 修订：查"对"不查"有"，对应秦始皇复盘卡 #5 #6 #7）：
- [ ] 标题是判断/陈述句，不是名词短语（封面/过渡/结尾必须含判断词：是/让/把/在/的/与/用）？
- [ ] 卡片/模块堆叠数受限？ 封面 ≤2 / 目录 ≤4 / 过渡 ≤1 / 结尾 ≤2（卡片/模块/card/module/box/grid/panel/tile/卡片/模块/面板 关键词计数）
- [ ] page_type × frame_kind 是否在白名单？  cover→hero_poster / toc→toc_list_illustration / transition→chapter_divider / closing→closing_poster / content→任选 14 个内容框架
- [ ] prompt 包含该页标题文字（原样中文）？
- [ ] prompt 包含该页正文/要点文字（原样中文）？
- [ ] prompt 包含该页数据/标注文字（原样中文）？
- [ ] 画面可见文字是否中文优先？禁止 `CONTENTS`、`ISSUE`、`SECTION`、`Thanks`、`Executive insight`、`Roadmap`、`Abstract` 等英文作为可见文案；必要缩写需在中文语境内使用。
- [ ] prompt 有明确的画面布局描述（左右/上下/中心）？
- [ ] prompt 色彩来自模板色彩系统，不出现 hex 码字面量？
- [ ] prompt 指定了分辨率和比例（2K, 16:9）？
- [ ] prompt body 无 `palette:` / `#XXXXXX` / `under XX%` 等会被 nano-banana 当文字渲染的元数据？
- [ ] 模板身份是否清楚？先查 `templates/TEMPLATE-DNA-INDEX.md`，确认选择的是当前 13 个 active 模板之一。
- [ ] 新模板/新风格是否只是已有模板的配色、行业主题或内容模式变化？如果是，归入现有模板 mode，不新增一级模板。
- [ ] 封面/过渡页包含章节编号？

### 模板负向约束（强制禁止，2026-06-15 引入）

每个模板在正向规范之外还包含「❌ 强制禁止」段落，生成 prompt 时必须遵守并复述进 prompt body：

- ❌ 禁止在画面上出现色值标注、`palette: #XXXXXX`、`under X%` 等设计稿元数据样式
- ❌ 禁止把 prompt 里的结构指令（如"小标题""正文""卡片"）当作画面元素渲染成色块/文字
- ❌ 禁止堆叠超过特殊页上限的卡片/模块数量（封面 ≤2 / 目录 ≤4 / 过渡 ≤1 / 结尾 ≤2）
- ❌ 禁止出现水印、二维码、Logo 文本（除非模板明确允许）
- ❌ 禁止在内容页出现"调色板/色卡/品牌指南"等设计元数据样式
- ❌ 禁止特殊页混用内容页 frame_kind（cover 用了 bento_grid = 直接 fail P13）

每张 prompt 文件结尾推荐加一段：
```
- Forbidden:
  - no palette swatches
  - no hex color labels (#XXXXXX)  
  - no "under X%" usage notes
  - no design-metadata watermarks
```

`validate-prompts.py` 升级点（2026-06-15）：
- **P5 增强**：特殊页（封面/目录/过渡/结尾）额外检查「标题是判断句」+「卡片数 ≤ 上限」
- **P13 新增**：page_type × frame_kind 硬白名单，不在表里直接 fail
- **P12 保留**：模板元数据泄漏（palette/hex/under % 字面量）

必须把每页 Prompt 文件的完整正文内容发给关哥审核，并获得明确反馈后才生图；未回复不算通过。
Prompt 审核时不能只发 `prompts/` 文件清单、文件名列表或摘要，必须发可直接审阅的完整 Prompt 文本。
如根据反馈修改了 Prompt，必须重新发送修改后的完整 Prompt 文件内容复审；不能只发修改点、diff 或摘要。

### Step 7: 生成图片
使用 `scripts/generate.sh` 逐页生图：
```bash
cd ~/image-ppt-workflow-workspace/<项目>/
"$SKILL_DIR"/scripts/generate.sh --model gpt-image-2-vip --prompt "..." --ratio 2048x1152 \
  --output slides/ --output-file "01-slide-cover.png" \
  --manifest slides-manifest.json \
  --prompt-file prompts/01-slide-cover.md \
  --page 1 --project <项目名>
```

**模型选择**：首选 `gpt-image-2-vip`（中文渲染最好），连续失败 3 次后降级 `nano-banana-2`。❌ 禁止用 `gpt-image-2`（非 vip）。

**并发**：10 页以上必须并发生图，每批 4-7 个并发调用。

### Step 7b: 样稿确认（⛔ 阻塞，默认必审）
默认必须先生成样稿并发送给关哥确认风格/文字可读性/视觉层级。确认通过后才生成剩余页面。
- 10 页以上：先生成前 6 页合成样稿。
- 10 页以下：先生成前 2-3 页或关键页样稿；若页数很少，也至少先发首张样稿确认风格。
- 未获得明确反馈，不得继续批量生图。

```bash
# 用 manifest 校验 + 合成
cd ~/image-ppt-workflow-workspace/<项目>/
python3 "$SKILL_DIR"/scripts/manifest.py check slides-manifest.json
python3 "$SKILL_DIR"/scripts/manifest.py reconcile slides-manifest.json slides/
python3 "$SKILL_DIR"/scripts/merge_to_pptx.py \
  --slides slides/ \
  --notes speaker-notes.md \
  --output 样稿.pptx \
  --require-manifest slides-manifest.json
```

### Step 8: 生成演讲备注
**AI 基于大纲手写口述稿**，写入 `speaker-notes.md`。要求：自然、口语化、有衔接。文档模式 30-60 秒/页，演讲模式 60-90 秒/页。

> ⚠️ 备注不能依赖脚本生成，必须 AI 手写以确保质量。

### Step 9: 合成 PPTX（⛔ manifest 硬门禁）
```bash
cd ~/image-ppt-workflow-workspace/<项目>/
python3 "$SKILL_DIR"/scripts/merge_to_pptx.py \
  --slides slides/ \
  --notes speaker-notes.md \
  --output <主题名称>.pptx \
  --require-manifest slides-manifest.json
```

**没有 manifest → 拒绝合成**（2026-06-13 起的硬门禁）。这是防退化机制：保证每张图都有真实生成证据（model/generated_at/task_id 等），不靠代码画图或裁原图局部凑数。

输出文件名基于主题命名，不能统一用 output.pptx。

**🔒 输出落点硬规则（2026-06-23 起）**：
- `--output` 必须落在**项目目录内**（即 `~/image-ppt-workflow-workspace/<项目>/` 下），不能落到 workspace 根目录或其他位置。
- 强烈建议传**绝对路径**：`--output ~/image-ppt-workflow-workspace/<项目>/<主题名>.pptx`，避免 cwd 漂移导致文件乱跑。
- 合成前务必先 `cd ~/image-ppt-workflow-workspace/<项目>/`。
- 脚本已加门禁：`--output` 目录不在 `--slides` 父目录（=项目根）内 → **直接拒绝合成（exit 1）**。
- 旧项目/特殊情况需越界，才显式设置 `IMAGE_PPT_ALLOW_OUTSIDE_PROJECT=1`。

### Step 10: 单页迭代
用户要求修改某一页时：修改 prompt → `generate.sh --image` 基于原图编辑再生 → 重新走 manifest 登记（自动去重）。

### 交付前确认
- PPTX 文件大小是否 ≤ 20MB？超出则按章节拆分为多个 Part
- 每个 Part 保持内容完整性（章节不被切断）
- 每个 Part 配有对应演讲备注
- 成果直接发飞书，图片用 message+media，文件上传云空间发链接

---

## ❌ 硬门禁：画图必须通过提示词生成（2026-06-13 关哥拍板）

**任何图都必须通过提示词让图像生成模型生成，不允许用代码画图**：

- ❌ Python/PIL（Pillow、ImageDraw、ImageFont）
- ❌ SVG、HTML、Canvas、matplotlib、PowerPoint shapes
- ❌ 截图渲染
- ❌ "AI 底图 + PIL 画字"路线（任何变体）

**失败处理**：图像生成失败 → 改 prompt 重试 → 再次失败 → 上报用户，**不允许**用 PIL/SVG 等代码画图兜底。

**适用范围**：本技能 (`image-ppt-workflow`) 及所有配套工作流（`gpt-image-ppt-workspace/`、`image-ppt-workflow-workspace/`、项目级脚本）。

---

## 📋 Slides Manifest（防退化机制，2026-06-13 引入）

每张生图必须登记到 `slides-manifest.json`，**没有 manifest 不能合成 PPTX**。

### generate.sh 新参数

| 参数 | 作用 | 示例 |
|---|---|---|
| `--manifest <path>` | manifest.json 路径（必传）| `--manifest ${PROJ}/slides-manifest.json` |
| `--prompt-file <path>` | 对应 prompt 文件路径，写到 manifest | `--prompt-file prompts/01-slide-cover.md` |
| `--page <n>` | 页码，写到 manifest | `--page 1` |
| `--project <name>` | 项目名，写到 manifest | `--project 2026-q3-strategy` |

### manifest.json schema

```json
{
  "version": "1.0",
  "project": "<项目名>",
  "created_at": "2026-06-13T18:55:00Z",
  "slides": [
    {
      "page": 1,
      "prompt_file": "prompts/01-slide-cover.md",
      "generated_source": "slides/01-slide-cover.png",
      "model": "gpt-image-2-vip",
      "aspect_ratio": "2048x1152",
      "generated_at": "2026-06-13T18:55:30Z",
      "task_id": "grsai_xxx",
      "status": "succeeded",
      "file_size": 1234567
    }
  ]
}
```

### manifest.py 校验脚本

| 子命令 | 作用 |
|---|---|
| `manifest.py check <manifest.json>` | 校验字段完整性（缺 model/generated_at 等即报错）|
| `manifest.py reconcile <manifest.json> <slides_dir>` | 对比 manifest 与 slides/ 目录（找孤儿/缺图）|
| `manifest.py reconcile-prompts <manifest.json> <prompts_dir>` | 对比 manifest 与 prompts/ 目录（找孤儿 prompt）|

### merge_to_pptx.py 硬门禁

合成 PPTX 必须传 `--require-manifest <manifest.json>`：
- manifest 不存在 → 拒绝合成（exit 1）
- manifest 校验失败 → 拒绝合成（exit 1）
- manifest 与 `slides/` 或 `prompts/` 不一致 → 拒绝合成（exit 1）
- 不传 `--require-manifest` → 正式流程拒绝合成

### 幂等性

同一页（同一 `generated_source`）二次生成 → manifest 自动去重旧记录、写入新记录（更新 `generated_at`），不会重复登记。

---

## 附录一：叙事弧线设计

每页分配 beat 类型：
- **setup**（铺垫）→ **tension**（张力/痛点）→ **resolution**（解决）→ **proof**（证明）→ **action**（CTA）
- 必须有至少一个**信心拐点**（tension→resolution）和至少一个**呼吸页**（低密度过渡页）

## 附录二：标题写作规范 + 内部语言净化

### 标题必须是判断句
| ❌ 错误（名词短语） | ✅ 正确（判断句） |
|---|---|
| "行业现状分析" | "行业增速从 30% 掉到 8%" |
| "产品核心优势" | "竞品做不到实时策略调整" |
| "用户痛点" | "80% 的用户在第一步就流失" |

**3 秒测试**：扫一眼标题能说出这页在主张什么，就是合格的。

### 内部语言净化
| ❌ 泄露（内部语言） | ✅ 净化（客户视角） |
|---|---|
| "这一页负责建立系统闭环" | "CDP 和 MA 被重写后，营销形成真正闭环" |
| "proof 页：展示真实样例" | "云南白药：一次完整的运营闭环" |
| "信心拐点" | 直接删除 |

## 附录三：可用风格模板

| # | 模板 | 风格关键词 | 适用场景 |
|---|------|-----------|----------|
| 01 | 东方美学 · 纸感极简 | 克制、留白、纸面触感 | 文化/学术/品牌故事 |
| 02 | 手绘漫画 · 趣味叙事 | 分镜、对话框、手绘感 | 产品教学/科普 |
| 03 | 糖果色职场述职 · 几何轻汇报 | 灰蓝/鹅黄/粉橘、波浪底座、圆角卡片 | 个人述职/岗位汇报/阶段总结 |
| 04 | 科技数据 · 未来感 | 深色背景、发光效果、Dashboard | 技术发布/AI主题 |
| 05 | 生活方式 · 温暖治愈 | 摄影主角、大地色 | 消费品/生活方式 |
| 06 | 杂志排版 · 编辑设计 | 跨页大图、出血布局 | 时尚品牌/发布会 |
| 07 | 学术答辩 · 规范严谨 | 三线表、APA引用 | 毕业论文/科研基金 |
| 08 | 国潮插画 · 新中式 | 工笔插画、祥云纹样 | 文旅推广/非遗品牌 |
| 09 | 数据报告 · 麦肯锡风 | 行动标题、MECE矩阵 | 战略咨询/行业研究 |
| 10 | 现代企业 · 数据驱动 | 卡片网格、深蓝主色 | 商业汇报/数据分析 |
| 11 | 党政党建 · 红色主旋律 | 红金米白、红旗飘带、长城山河 | 党政机关汇报/党建党课/主题教育 |
| 12 | 企业项目管理 · 红蓝专业 | 珊瑚红+海军蓝、甘特图 | 项目汇报/进度跟踪 |
| 13 | 企业架构 · 深蓝专业 | 深蓝主色、流程图 | 系统架构/组织管理 |

## 附录四：validate-prompts.py 校验项（2026-06-13 扩展）

新增**信息点密度检查**（借鉴 GordenSun §0）：

| 检查项 | 通过条件 | 失败动作 |
|---|---|---|
| 信息点数 | ≥ 15 | 警告；< 10 报错 |
| 模块数 | ≥ 3 | 警告；< 2 报错 |
| 中文文字完整 | prompt 包含全部页面文字 verbatim | 报错 |
| 色彩来源 | 颜色 hex 必须在模板色彩系统里 | 警告 |
| 内部术语 | 不出现 setup/tension/beat 等 | 警告 |
