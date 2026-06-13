"""frame_kinds.py — 高阶版式框架目录（P2 引入，2026-06-13）

借鉴 GordenSun/GordenSuperPPTSkills image-prompt-guide §1.7：
每页一个「复杂视觉框架」，全篇不重复。从本目录里为每页选一个不同的结构。
"""

# 高阶框架目录（12 种）
# 每个框架有：name（中文）、name_en（英文）、shape（几何形态）、use_when（适用场景）
FRAME_KINDS = [
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


def get_frame_kinds() -> list[dict]:
    """返回所有高阶框架的列表。"""
    return FRAME_KINDS


def get_frame_ids() -> list[str]:
    """返回所有高阶框架的 id 列表（用于校验）。"""
    return [f["id"] for f in FRAME_KINDS]


def find_frame_by_id(frame_id: str) -> dict | None:
    """根据 id 查找框架。"""
    for f in FRAME_KINDS:
        if f["id"] == frame_id:
            return f
    return None


def describe_frame_kinds() -> str:
    """生成可读的高阶框架目录（用于 prompt 模板和 SKILL.md 文档）。"""
    lines = ["| id | 名称 | 形态 | 适用场景 |", "|---|---|---|---|"]
    for f in FRAME_KINDS:
        lines.append(f"| `{f['id']}` | {f['name']} | {f['shape']} | {f['use_when']} |")
    return "\n".join(lines)
