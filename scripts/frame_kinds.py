"""frame_kinds.py — 高阶版式框架目录（P2 引入，2026-06-13）

借鉴 GordenSun/GordenSuperPPTSkills image-prompt-guide §1.7：
每页一个「复杂视觉框架」，全篇不重复。从本目录里为每页选一个不同的结构。
"""

# 高阶框架目录（12 种）
# 每个框架有：name（中文）、name_en（英文）、shape（几何形态）、use_when（适用场景）
FRAME_KINDS = [
    # === 特殊页专用框架（2026-06-15 引入）===
    # 封面/目录/过渡/结尾不要混用内容页框架；特殊页先看 page_type，再选 frame_kind。
    {
        "id": "hero_poster",
        "name": "封面主视觉海报",
        "name_en": "Hero Poster Cover",
        "shape": "大面积主视觉 + 大标题 + 副标题/印章",
        "use_when": "封面页、主题开场、品牌主视觉",
        "page_types": ["封面", "cover"],
    },
    {
        "id": "toc_list_illustration",
        "name": "目录列表配插画",
        "name_en": "TOC List + Illustration",
        "shape": "左侧章节列表 + 右侧大面积插画/纹样",
        "use_when": "目录页、章节导航页",
        "page_types": ["目录", "toc"],
    },
    {
        "id": "chapter_divider",
        "name": "章节过渡页",
        "name_en": "Chapter Divider",
        "shape": "大面积低透明背景 + 居中超大章节编号 + 下方章节标题",
        "use_when": "章节过渡页、呼吸页",
        "page_types": ["过渡", "transition", "chapter"],
    },
    {
        "id": "closing_poster",
        "name": "结尾余韵海报",
        "name_en": "Closing Poster",
        "shape": "居中结束语 + 印章/Logo + 底部淡纹样",
        "use_when": "结尾页、感谢页、收束页",
        "page_types": ["结尾", "closing", "ending", "thanks", "thank"],
    },

    # === 内容页框架 ===
    {
        "id": "mobius_ring",
        "name": "莫比乌斯环",
        "name_en": "Mobius Ring",
        "shape": "8 字形闭环",
        "use_when": "流程往复、循环迭代、双向关系",
    },
    {
        "id": "bento_grid",
        "name": "Bento 便当盒",
        "name_en": "Bento Grid",
        "shape": "多尺寸卡片网格",
        "use_when": "多模块并列、参数总览、特性集合",
    },
    {
        "id": "concentric_radar",
        "name": "同心圆雷达",
        "name_en": "Concentric Radar",
        "shape": "多层同心圆",
        "use_when": "能力评估、维度评分、层级结构",
    },
    {
        "id": "fishbone",
        "name": "鱼骨图",
        "name_en": "Fishbone",
        "shape": "因果分支",
        "use_when": "根因分析、问题拆解、归因",
    },
    {
        "id": "funnel",
        "name": "漏斗",
        "name_en": "Funnel",
        "shape": "上宽下窄",
        "use_when": "转化路径、用户旅程、漏斗指标",
    },
    {
        "id": "hub_spoke",
        "name": "中心辐射",
        "name_en": "Hub-Spoke",
        "shape": "中心 + 周边",
        "use_when": "平台架构、生态系统、辐射式关系",
    },
    {
        "id": "pyramid",
        "name": "金字塔",
        "name_en": "Pyramid",
        "shape": "下宽上窄",
        "use_when": "层级关系、优先级、堆叠架构",
    },
    {
        "id": "timeline_milestone",
        "name": "里程碑缎带",
        "name_en": "Timeline Milestone",
        "shape": "横向时间轴 + 节点",
        "use_when": "发展历程、项目时间线、版本演进",
    },
    {
        "id": "layered_architecture",
        "name": "分层架构带",
        "name_en": "Layered Architecture",
        "shape": "水平多层堆叠",
        "use_when": "技术架构、组织层级、流程分层",
    },
    {
        "id": "kpi_rail",
        "name": "侧栏 KPI rail",
        "name_en": "Side KPI Rail",
        "shape": "窄竖条 + 多指标",
        "use_when": "数据看板、关键指标、对比",
    },
    {
        "id": "map_locator",
        "name": "地图定位连线",
        "name_en": "Map + Locator",
        "shape": "地图 + 定位点",
        "use_when": "布局、出海、网络、地理分布",
    },
    {
        "id": "house_architecture",
        "name": "房子型架构",
        "name_en": "House Architecture",
        "shape": "屋顶 + 主体 + 地基",
        "use_when": "系统组成、技术体系、组成要素",
    },
    {
        "id": "dna_helix",
        "name": "DNA 双螺旋",
        "name_en": "DNA Helix",
        "shape": "双链交叉",
        "use_when": "双要素耦合、价值链、关联结构",
    },
    {
        "id": "step_cards",
        "name": "阶段大卡时间轴",
        "name_en": "Step Cards Timeline",
        "shape": "横向节点 + 大卡",
        "use_when": "路线图、阶段规划、里程碑",
    },
]


# 历史项目/模板里常见的自造 frame_kind 别名。
# 归一化后参与特殊页硬校验，避免旧项目全部被“未知框架”误杀。
FRAME_ALIASES = {
    "chapter_gate": "chapter_divider",
    "symbolic_gate": "chapter_divider",
    "mystery_gate": "chapter_divider",
    "transition_gate": "chapter_divider",
    "section_divider": "chapter_divider",
    "cover_poster": "hero_poster",
    "title_poster": "hero_poster",
    "toc_list": "toc_list_illustration",
    "toc_illustration": "toc_list_illustration",
    "closing_poster_centered": "closing_poster",
    "thank_you_poster": "closing_poster",
}


def normalize_frame_id(frame_id: str) -> str:
    """把历史/模板自造 frame_kind 归一化到目录 id。"""
    if not frame_id:
        return ""
    key = frame_id.strip().lower().replace(" ", "_").replace("-", "_")
    return FRAME_ALIASES.get(key, key)


def get_frame_kinds() -> list[dict]:
    """返回所有高阶框架的列表。"""
    return FRAME_KINDS


def get_frame_ids() -> list[str]:
    """返回所有高阶框架的 id 列表（用于校验）。"""
    return [f["id"] for f in FRAME_KINDS]


def find_frame_by_id(frame_id: str) -> dict | None:
    """根据 id 查找框架。"""
    frame_id = normalize_frame_id(frame_id)
    for f in FRAME_KINDS:
        if f["id"] == frame_id:
            return f
    return None



# === 2026-06-15: 内容页框架全集（白名单用） ===
# 内容页（page_type=content）允许使用以下所有框架。
# 这是显式导出的常量，validate-prompts.py P13 互校验直接消费。
CONTENT_FRAME_KINDS: set[str] = {
    f["id"] for f in FRAME_KINDS if not f.get("page_types")
}

# === 2026-06-15: page_type × frame_kind 硬白名单（P13 互校验） ===
# 规则来源：秦始皇复盘卡 #6 — page_type 和 frame_kind 是两套独立维度，
# 之前只是软提示（frame_supports_page_type），现在升级为硬门禁。
# 关键约束：封面只能 hero_poster；结尾只能 closing_poster；
# 目录只能 toc_list_illustration；过渡只能 chapter_divider 及其 alias。
PAGE_TYPE_FRAME_WHITELIST: dict[str, set[str]] = {
    "cover":      {"hero_poster", "title_poster", "cover_poster"},
    "toc":        {"toc_list_illustration", "toc_list", "toc_illustration"},
    "transition": {
        "chapter_divider",
        # 以下 5 个是历史 alias，归一化后等价 chapter_divider
        "chapter_gate", "symbolic_gate", "mystery_gate",
        "transition_gate", "section_divider",
    },
    "closing":    {"closing_poster", "closing_poster_centered", "thank_you_poster"},
    # "content" 不在白名单表里 —— 走 CONTENT_FRAME_KINDS 全集
}


def get_content_frame_kinds() -> set[str]:
    """返回所有允许在内容页使用的 frame_kind 集合。"""
    return CONTENT_FRAME_KINDS.copy()


def get_page_type_whitelist() -> dict[str, set[str]]:
    """返回 page_type → 允许的 frame_kind 集合的映射（深拷贝）。"""
    return {k: v.copy() for k, v in PAGE_TYPE_FRAME_WHITELIST.items()}


def is_frame_allowed_for_page_type(frame_id: str, page_type: str) -> bool:
    """P13 硬校验：检查 frame_id 是否允许出现在 page_type 上。

    - page_type=content：frame_id 必须在 CONTENT_FRAME_KINDS
    - page_type in {cover,toc,transition,closing}：frame_id（归一化后）必须在白名单
    - frame_id 未声明（空）：返回 False（让校验脚本报"未声明 frame_kind"）
    """
    if not frame_id or not page_type:
        return False
    canonical = normalize_frame_id(frame_id)
    pt = page_type.strip().lower()
    if pt == "content":
        return canonical in CONTENT_FRAME_KINDS
    if pt in PAGE_TYPE_FRAME_WHITELIST:
        return canonical in PAGE_TYPE_FRAME_WHITELIST[pt]
    # 未知 page_type 走软逻辑
    return frame_supports_page_type(canonical, pt)


def frame_supports_page_type(frame_id: str, page_type: str) -> bool:
    """检查 frame_kind 是否声明支持某类页面。

    没有 page_types 的内容框架只适合内容页；封面/目录/过渡/结尾必须用特殊页框架。
    """
    canonical = normalize_frame_id(frame_id)
    info = find_frame_by_id(canonical)
    if not info:
        return False
    pt = (page_type or "").strip().lower()
    special = {"cover", "toc", "transition", "closing"}
    allowed = info.get("page_types")
    if not allowed:
        return pt not in special
    allowed_norm = {str(x).strip().lower() for x in allowed}
    return pt in allowed_norm or any(x and x in pt for x in allowed_norm)


def describe_frame_kinds() -> str:
    """生成可读的高阶框架目录（用于 prompt 模板和 SKILL.md 文档）。"""
    lines = ["| id | 名称 | 形态 | 适用场景 |", "|---|---|---|---|"]
    for f in FRAME_KINDS:
        lines.append(f"| `{f['id']}` | {f['name']} | {f['shape']} | {f['use_when']} |")
    return "\n".join(lines)
