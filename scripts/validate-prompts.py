#!/usr/bin/env python3
"""validate-prompts.py — 校验每页 Prompt 是否符合模板规则
用法: python3 scripts/validate-prompts.py <项目目录>
  读取: <项目目录>/selected-template.md + <项目目录>/prompts/*.md
  输出: 校验报告，逐项列出通过/失败
"""

import re
import os
import sys
import glob
from pathlib import Path as _VPath

sys.path.insert(0, str(_VPath(__file__).resolve().parent))
try:
    from frame_kinds import (
        get_frame_ids, find_frame_by_id, normalize_frame_id, frame_supports_page_type,
        is_frame_allowed_for_page_type, get_content_frame_kinds, get_page_type_whitelist,
    )
except ImportError:
    get_frame_ids = lambda: []
    find_frame_by_id = lambda x: None
    normalize_frame_id = lambda x: x
    frame_supports_page_type = lambda frame_id, page_type: True
    is_frame_allowed_for_page_type = lambda frame_id, page_type: True
    get_content_frame_kinds = lambda: set()
    get_page_type_whitelist = lambda: {}


# === 哪些页型对密度要求低（不强制 15+ 信息点） ===
LOW_DENSITY_TYPES = {
    "封面", "cover", "目录", "toc", "过渡", "transition",
    "结尾", "ending", "谢谢", "thank",
}


def parse_template(template_path):
    """解析模板，提取色彩系统中的色值"""
    with open(template_path) as f:
        content = f.read()
    colors = set(re.findall(r"`(#\w{6})`", content))
    return colors


def _count_info_points(content: str) -> int:
    """统计 prompt 中包含的'信息点'数（启发式）"""
    n = 0
    n += len(re.findall(r'["\u201c][^"\u201d]{2,60}[\u4e00-\u9fff][^"\u201d]*["\u201d]', content))
    n += len(re.findall(r'\([^()]{3,80}\)', content))
    n += len(re.findall(r'\d+\.?\d*[%\u2030\u4eba\u4e07]', content))
    bullets = re.findall(r'(?:^|\n)\s*[-*\u2022]\s+\S+', content)
    n += len(bullets)
    n += len(re.findall(r'\u300c[^\u300d]{2,40}\u300d', content))
    return n


def _count_modules(content: str) -> int:
    """统计并列模块数"""
    pat = r'(?:Module|Card|Section|Column|Panel|\u6a21\u5757|\u5361\u7247|\u5217|\u9762\u677f)[\s\S]{0,150}?'
    matches = re.findall(pat + r'(?:title|heading|["\u201c][^"\u201d]{2,30})', content, re.IGNORECASE)
    return len(matches)


def _is_low_density_page(content: str) -> bool:
    """判断是否低密度页（封面/目录/过渡/结尾）"""
    cl = content.lower()
    for kw in LOW_DENSITY_TYPES:
        if kw.lower() in cl:
            return True
    return False



SPECIAL_PAGE_TYPES = {"cover", "toc", "transition", "closing"}


def _extract_page_type(content: str) -> str:
    """从 prompt 中识别页面类型，归一化为 cover/toc/transition/closing/content。"""
    m = re.search(r'(?:Page\s*type|页面类型)\s*[:：]\s*([^\n。\.]+)', content, re.IGNORECASE)
    raw = m.group(1).strip().lower() if m else content.lower()
    if any(k in raw for k in ['封面', 'cover']):
        return 'cover'
    if any(k in raw for k in ['目录', 'toc', 'table of contents']):
        return 'toc'
    if any(k in raw for k in ['过渡', '章节', 'transition', 'chapter divider']):
        return 'transition'
    if any(k in raw for k in ['结尾', '结束', '谢谢', 'closing', 'ending', 'thank']):
        return 'closing'
    return 'content'


SPECIAL_PAGE_FRAME_RULES = {
    'cover': {
        'name': '封面页',
        'allowed_frames': {'hero_poster'},
        'must_groups': [
            ('主视觉海报', ['hero', 'poster', '主视觉', '海报', 'large illustration', '主题插画']),
            ('大标题', ['large title', 'calligraphic title', '大标题', '书法感标题', 'title on the right', '标题用书法']),
            ('副标题/题跋/竖排', ['subtitle', 'vertical subtitle', '题跋', '竖排', '副标题']),
            ('印章标记', ['seal', '印章', 'stamp']),
            ('留白', ['whitespace', '留白', 'generous empty space', 'large blank']),
        ],
        'forbid': ['bento grid', 'bento_grid', 'cards', 'card grid', 'modules', 'dashboard', 'kpi rail', 'funnel', 'fishbone', 'map locator'],
    },
    'toc': {
        'name': '目录页',
        'allowed_frames': {'toc_list_illustration'},
        'must_groups': [
            ('章节列表', ['chapter list', '章节列表', '目录列表', 'table of contents']),
            ('左右结构', ['left side', 'right side', '左侧', '右侧']),
            ('插画/纹样/宣纸留白', ['illustration', '纹样', 'rice-paper', '宣纸', '淡纹样', '大面积']),
        ],
        'forbid': ['dashboard', 'kpi rail', 'fishbone', 'funnel', 'dense cards', '多模块卡片', 'bento dashboard'],
    },
    'transition': {
        'name': '过渡页',
        'allowed_frames': {'chapter_divider'},
        'must_groups': [
            ('居中结构', ['centered', '居中', 'center aligned']),
            ('超大章节编号', ['large chapter number', 'oversized chapter number', '超大章节编号', '巨大章节编号', 'large chapter mark', 'monumental oversized chinese character']),
            ('标题在编号下方', ['title below', 'below the number', '章节标题在编号下方', 'title under']),
            ('低透明背景', ['15% transparent', '15% opacity', '10-18% opacity', 'transparent background', '低透明', '淡背景']),
            ('极简/留白', ['minimal text', 'whitespace', '留白', 'breathing page', '呼吸页']),
        ],
        'forbid': ['bento grid', 'bento_grid', 'cards', 'modules', 'dashboard', 'three columns', '3 columns', 'map locator', 'left/right', 'left side', 'right side', 'on the left', 'on the right'],
    },
    'closing': {
        'name': '结尾页',
        'allowed_frames': {'closing_poster'},
        'must_groups': [
            ('居中结束语', ['centered', '居中', 'slogan', '感谢语', '结束语']),
            ('印章/Logo', ['seal', '印章', 'logo']),
            ('底部淡纹样', ['bottom pattern', '底部', '淡纹样', 'subtle pattern']),
        ],
        'forbid': ['dashboard', 'kpi rail', 'funnel', 'timeline', 'data chart', 'cards', 'modules'],
    },
}


def _validate_special_page_contract(content: str, page_type: str, frame_kind: str):
    """特殊页页面契约硬校验：防止封面/目录/过渡/结尾被写成内容页。"""
    issues, warnings, passed = [], [], []
    if page_type not in SPECIAL_PAGE_TYPES:
        return passed, warnings, issues

    rule = SPECIAL_PAGE_FRAME_RULES[page_type]
    canonical = normalize_frame_id(frame_kind) if frame_kind else ''
    cl = content.lower()

    if not canonical:
        issues.append(f"❌ 特殊页版式不合格：{rule['name']} 必须声明专用 frame_kind（建议: {', '.join(sorted(rule['allowed_frames']))}）")
    elif canonical not in rule['allowed_frames']:
        issues.append(f"❌ 特殊页 frame_kind 不匹配：{rule['name']} 不能使用 '{frame_kind}'（归一化: '{canonical}'），建议: {', '.join(sorted(rule['allowed_frames']))}")
    elif not frame_supports_page_type(canonical, page_type):
        issues.append(f"❌ frame_kind '{canonical}' 未声明支持 {rule['name']}")
    else:
        passed.append(f"✅ 特殊页 frame_kind 匹配：{rule['name']} → {canonical}")

    forbidden_hit = [kw for kw in rule['forbid'] if kw.lower() in cl]
    if forbidden_hit:
        issues.append(f"❌ {rule['name']} 含内容页/错误布局关键词: {forbidden_hit}")
    else:
        passed.append(f"✅ {rule['name']} 未出现内容页式禁用布局词")

    missing = []
    for label, kws in rule['must_groups']:
        if not any(kw.lower() in cl for kw in kws):
            missing.append(label)
    if missing:
        issues.append(f"❌ {rule['name']} 缺少模板必须结构: {missing}")
    else:
        passed.append(f"✅ {rule['name']} 包含模板必须结构")

    return passed, warnings, issues

def _extract_frame_kind(content: str) -> str:
    """从 prompt 中提取 frame_kind 标注。

    2026-06-15 修复：原正则在 “**Frame kind:** `bento_grid`” 这种
    粗体跨过关键词与冒号时 误判。现重写：宽松匹配 “frame kind” 周围可能
    的 0-2 个 ***，后跟任意空白/中文冒号，再跳过一个可选手动引号，取标识符。
    """
    pats = [
        # 1) Frame kind: <id>  或  **Frame kind:** `<id>`  (任意 ** 位置)
        r'frame[\s_]kind[^a-z0-9]{0,8}[`"\']?([a-z_][a-z0-9_\-]{1,30})[`"\']?',
        # 2) frame_kind 字段名: <id>
        r'frame_kind\s*[:=][`"\']?([a-z_][a-z0-9_\-]{1,30})[`"\']?',
        # 3) 中文“框架：xxx”
        r'\u6846\u67b6[:\uff1a]\s*[`"\']?([^\s`"\'\n]{2,20})[`"\']?',
    ]
    for pat in pats:
        m = re.search(pat, content, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _extract_palette(content: str) -> set:
    """从 prompt 中提取 palette 标注"""
    pats = [
        r'palette[:\s]+([#\w, ]+)',
        r'\u914d\u8272[:\uff1a]\s*([#\w, ]+)',
    ]
    colors: set = set()
    for pat in pats:
        for m in re.finditer(pat, content, re.IGNORECASE):
            chunk = m.group(1)
            for c in re.findall(r'#\w{6}', chunk):
                colors.add(c.upper())
    return colors


def _project_palette(project_dir: str) -> set:
    """从项目目录的 outline.md 提取全篇统一 palette"""
    outline = _VPath(project_dir) / "outline.md"
    if not outline.exists():
        return set()
    text = outline.read_text(encoding="utf-8")
    m = re.search(
        r'(?:palette|\u5168\u7bc7\u914d\u8272|unified[\s_]palette)[:\uff1a]\s*([#\w, ]+)',
        text, re.IGNORECASE,
    )
    if not m:
        return set()
    return {c.upper() for c in re.findall(r'#\w{6}', m.group(1))}


def _project_frame_kinds(project_dir: str) -> list:
    """从项目目录的 outline.md 提取每页 frame_kind 列表"""
    outline = _VPath(project_dir) / "outline.md"
    if not outline.exists():
        return []
    text = outline.read_text(encoding="utf-8")
    kinds = []
    for m in re.finditer(
        r'(?:\*\*)?frame[_\s]kind(?:\*\*)?\s*[:\uff1a:]\s*[`"\']?([a-z_\-]+)[`"\']?',
        text, re.IGNORECASE,
    ):
        kinds.append(m.group(1).strip())
    return kinds



# === 2026-06-16: 可见文字中文优先硬门禁 ===
# 目标：prompt 本身可以用英文写设计指令，但所有“将被画到画面上的文字”默认必须中文。
# 现有校验只检查“有中文”，不能防止 CONTENTS / ISSUE / Thanks / Executive insight 等英文被渲染。
VISIBLE_TEXT_LABEL_PATTERNS = [
    r'title', r'subtitle', r'heading', r'label', r'caption', r'footer', r'header',
    r'badge', r'chip', r'kicker', r'masthead', r'folio', r'byline', r'callout',
    r'quote', r'annotation', r'legend', r'axis', r'row', r'column', r'bullet',
    r'section label', r'issue number', r'cover line', r'chapter', r'number',
    r'正文', r'标题', r'副标题', r'标注', r'标签', r'页脚', r'页眉', r'题跋',
    r'目录', r'章节', r'行', r'列', r'引语', r'注释', r'图例', r'坐标轴',
]

# 允许极少数真正必要的缩写。原则：能中文化就中文化；缩写必须短且常见。
ALLOWED_VISIBLE_ENGLISH_TOKENS = {
    'AI', 'API', 'CPU', 'GPU', 'NPU', 'SaaS', 'PaaS', 'IaaS',
    'KPI', 'ROI', 'ROE', 'OKR', 'CRM', 'ERP', 'BI', 'B端', 'C端',
    'Q1', 'Q2', 'Q3', 'Q4', 'A', 'B', 'C', 'D',
}

# 这些英文词一旦出现在“可见文字候选”里，基本就是画面英文泄漏。
FORBIDDEN_VISIBLE_ENGLISH_WORDS = {
    'CONTENTS', 'CONTENT', 'THANK', 'THANKS', 'SECTION', 'ISSUE', 'VOL', 'VOLUME',
    'ANNUAL', 'REPORT', 'EXECUTIVE', 'INSIGHT', 'INSIGHTS', 'STRATEGY', 'STRATEGIC',
    'OPTIONS', 'OPTION', 'ROADMAP', 'MILESTONE', 'ABSTRACT', 'REFERENCE', 'REFERENCES',
    'CONCLUSION', 'SUMMARY', 'FINDINGS', 'FINDING', 'GROWTH', 'TARGET', 'PATH', 'PATHS',
    'NARRATIVE', 'STYLE', 'BRAND', 'GLOBAL', 'MARKET', 'OPPORTUNITY', 'RISK',
    'MCKINSEY', 'ACCENTURE', 'KINFOLK', 'MONOCLE', 'VOGUE', 'JUNE', 'JAN', 'FEB',
    'MAR', 'APR', 'MAY', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
}

NEGATIVE_OR_META_LINE_RE = re.compile(
    r'(Forbidden|Rendering constraints|avoid|do not|no\s+|not\s+|must feel|Composition|Layout|Global visual style|visual style)',
    re.IGNORECASE,
)


def _latin_tokens(text: str) -> list:
    """提取英文/拉丁 token，保留 Q1 这类季度写法。"""
    return re.findall(r'[A-Za-z]+\d*|[A-Za-z]\d+', text)


def _line_looks_like_visible_text(line: str) -> bool:
    """判断一行是否在描述画面上的可见文字，而不是普通设计指令。"""
    if NEGATIVE_OR_META_LINE_RE.search(line):
        return False
    head = line.split(':', 1)[0]
    if any(re.search(pat, head, re.IGNORECASE) for pat in VISIBLE_TEXT_LABEL_PATTERNS):
        return True
    return False


def _extract_quoted_texts(line: str) -> list:
    """提取一行中可能要渲染到画面的引号文本。"""
    vals = []
    vals.extend(re.findall(r'["\u201c]([^"\u201d]{1,120})["\u201d]', line))
    vals.extend(re.findall(r"'([^']{1,120})'", line))
    return [v.strip() for v in vals if v.strip()]


def _english_violation_for_visible_text(text: str):
    """返回 None 表示通过；否则返回违规原因。"""
    tokens = _latin_tokens(text)
    if not tokens:
        return None

    # 单个必要缩写/字母允许，例如 “GPU 算力”“A 路径”。
    bad_tokens = []
    forbidden_hits = []
    for tok in tokens:
        norm = tok if any(c.islower() for c in tok) else tok.upper()
        if tok.upper() in FORBIDDEN_VISIBLE_ENGLISH_WORDS:
            forbidden_hits.append(tok)
        if tok not in ALLOWED_VISIBLE_ENGLISH_TOKENS and tok.upper() not in ALLOWED_VISIBLE_ENGLISH_TOKENS:
            bad_tokens.append(tok)

    if forbidden_hits:
        return f"包含禁止画面英文词 {forbidden_hits}"
    if bad_tokens:
        return f"包含非白名单英文词 {bad_tokens}"

    # 如果整段完全没有中文，只靠缩写/字母，也不合格（如 “KPI / ROI” 应写中文说明）。
    if not re.search(r'[\u4e00-\u9fff]', text):
        return "可见文字没有中文解释"
    return None


def _validate_visible_text_chinese(content: str):
    """P14：可见文字中文优先。Prompt 可英文写指令，但画面文字默认中文。"""
    passed, warnings, issues = [], [], []
    candidates = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if not _line_looks_like_visible_text(line):
            continue
        for q in _extract_quoted_texts(line):
            # 过短符号/纯数字跳过
            if len(q) <= 1 or re.fullmatch(r'[\d\s·/\-.%]+', q):
                continue
            candidates.append((lineno, q))

    if not candidates:
        warnings.append("⚠️  P14 未识别到可见文字候选，无法检查英文泄漏；请用引号明确所有画面文字")
        return passed, warnings, issues

    checked = 0
    for lineno, text in candidates:
        checked += 1
        reason = _english_violation_for_visible_text(text)
        if reason:
            issues.append(
                f"❌ P14 可见文字必须中文优先：第 {lineno} 行候选文案 '{text}' {reason}。"
                f"除非必要缩写，否则请改成中文（例如 CONTENTS→本节目录，ISSUE→期号，Thanks→感谢聆听）。"
            )

    if not any(i.startswith('❌ P14') for i in issues):
        passed.append(f"✅ P14 可见文字中文优先检查通过：{checked} 条候选文案")
    return passed, warnings, issues


# === 2026-06-18: 模板 DNA 身份硬门禁 ===
# 目标：防止相近模板退化成同一张脸；当前模板库只维护 13 个 active 一级模板。
TEMPLATE_DNA_RULES = {
    '生活方式 · 温暖治愈风': {
        'must_any_groups': [
            ('生活方式/温暖场景', ['生活场景', '自然光', '静物', '人物', '产品融入', '温暖', '燕麦白', '暖棕']),
            ('柔和材质/手写点缀', ['纸感', '亚麻', '木质', '圆角', '手写', '便签', '胶带', '水彩']),
        ],
        'forbid': ['深空黑', 'UML', '甘特', '红蓝冲突', '纯咨询白底', '冷冰冰仪表盘'],
    },
    '数据报告 · 麦肯锡风': {
        'must_any_groups': [
            ('咨询报告信息纪律', ['咨询报告', '结论标题', '董事会', '尽调', '行业研究', '数据来源', '脚注', '来源注释']),
            ('结构化数据分析图形', ['矩阵', '四象限', 'MECE', '瀑布图', '桥图', '条形图', '柱状图', '折线图', '漏斗', '金字塔']),
            ('白底深蓝克制', ['纯白', '白底', '深蓝', '企业蓝', '细分隔线', '留白']),
        ],
        'forbid': ['甘特', '看板列', 'UML', '分层架构', '人物插画', '生活场景', '3D 数据方块', '立方体堆叠'],
    },
    '现代企业 · 数据驱动风': {
        'must_any_groups': [
            ('企业数据看板/卡片系统', ['数据看板', '指标卡', 'KPI', '关键指标', '卡片式', '圆角卡片', '仪表盘']),
            ('蓝橙商业科技感', ['深蓝', '中蓝', '活力橙', '蓝橙', '浅灰蓝']),
            ('几何/3D 数据视觉', ['等距', 'isometric', '3D', '立方体', '数据方块', '几何图形', '环形图']),
        ],
        'forbid': ['甘特', '看板列', 'UML', '工笔', '生活场景', '论文', '红蓝冲突碎片'],
    },
    '党政党建 · 红色主旋律风': {
        'must_any_groups': [
            ('党政党建语义', ['党政', '党建', '党课', '主题教育', '政策学习', '会议精神', '机关党委']),
            ('红金主旋律视觉', ['中国红', '党政红', '金色', '红旗', '飘带', '五星', '长城', '山河']),
            ('正式中文标题体系', ['宋体', '小标宋', '庄重', '正式', '红金', '米白']),
        ],
        'forbid': ['糖果色', '霓虹', '科技界面', '生活场景', '商业驾驶舱', '潮玩', '英文装饰'],
    },
    '企业项目管理 · 红蓝专业风': {
        'must_any_groups': [
            ('PMO/项目管理语义', ['PMO', '项目管理', '进度', '交付', '风险', '资源', '负责人']),
            ('进度可视化', ['甘特', '时间线', '里程碑', '看板', '状态灯', '完成率', '进度条']),
            ('红蓝状态编码', ['珊瑚红', '海军蓝', '风险标记', '当前阶段', '正常状态', '延期']),
        ],
        'forbid': ['四象限市场矩阵', 'UML', '分层架构', '生活场景', '温暖插画', '3D 立方体堆叠'],
    },
    '企业架构 · 深蓝专业风': {
        'must_any_groups': [
            ('架构/系统语义', ['企业架构', '系统架构', '模块', '服务层', '数据层', '应用层', '接口', '治理']),
            ('严谨关系图', ['分层架构', '层级', 'UML', '连接线', '箭头', '数据流', '流程框图', '节点']),
            ('深蓝专业风格', ['深蓝', '浅蓝', '蓝色矩形', '白底', '标准化', '严谨']),
        ],
        'forbid': ['甘特', '看板列', '人物插画', '生活场景', '红蓝冲突', '杂志', '暖米色'],
    },
}

def _detect_template_name(project_dir: str) -> str:
    tpl = _VPath(project_dir) / 'selected-template.md'
    if not tpl.exists():
        return ''
    text = tpl.read_text(encoding='utf-8')
    m = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    return m.group(1).strip() if m else ''


def _validate_template_dna(content: str, project_dir: str):
    """P15：模板 DNA 差异化。先用关键词硬卡 09-14 的专属结构锚点。"""
    passed, warnings, issues = [], [], []
    name = _detect_template_name(project_dir)
    rule = TEMPLATE_DNA_RULES.get(name)
    if not rule:
        return passed, warnings, issues

    missing = []
    for label, kws in rule['must_any_groups']:
        if not any(kw.lower() in content.lower() for kw in kws):
            missing.append(label)
    if missing:
        issues.append(
            f"❌ P15 模板 DNA 不足：{name} 缺少专属锚点 {missing}。"
            f"不要退化成通用咨询二栏页；请把该模板自己的结构/配色/图形语言写进 prompt。"
        )
    else:
        passed.append(f"✅ P15 模板 DNA 锚点完整：{name}")

    hits = [kw for kw in rule['forbid'] if kw.lower() in content.lower()]
    if hits:
        issues.append(
            f"❌ P15 模板 DNA 串味：{name} 出现其他模板特征 {hits}。"
            f"请删除串味元素，强化本模板专属视觉语言。"
        )
    else:
        passed.append(f"✅ P15 未发现明显模板串味：{name}")
    return passed, warnings, issues

def validate_prompt(prompt_path, template_colors, slide_num, total_slides, project_dir="."):
    """校验单个 prompt 文件"""
    with open(prompt_path) as f:
        content = f.read()

    issues = []
    warnings = []
    passed = []

    # 1. 标题文字
    title_matches = re.findall(
        r'(?:[Tt]itle|heading|chapter number|number|label)[^"\n]{0,60}["\']([^"\']{3,50}[\u4e00-\u9fff][^"\']*)["\']',
        content,
    )
    if not title_matches:
        title_matches = re.findall(r'["\']([\u4e00-\u9fff][^"\']{3,50})["\']', content)
    title_matches = [t for t in title_matches if len(t) > 5]
    if title_matches:
        passed.append(f"\u2705 \u5305\u542b\u6807\u9898\u6587\u5b57: {title_matches[0][:30]}...")
    else:
        issues.append("\u274c \u7f3a\u5c11\u6807\u9898\u6587\u5b57\uff08\u539f\u6837\u4e2d\u6587\uff09")

    # 2. 正文/标注文字
    body_matches = []
    body_patterns = [
        r'(?:[Bb]ody text|annotation|metric|labeled|subtitle|arrow)[^"\n]{0,80}["\']([^"\']{3,60}[\u4e00-\u9fff][^"\']*)["\']',
        r'["\']([\u4e00-\u9fff][^"\']{4,60})["\']',
    ]
    for pat in body_patterns:
        body_matches.extend(re.findall(pat, content))
    body_matches = list(set([t.strip() for t in body_matches if len(t) > 4]))
    body_matches = [t for t in body_matches if t not in title_matches]
    exclude_terms = ['setup', 'tension', 'resolution', 'proof', 'action', 'beat', 'Compute-Bound', 'Memory-Bound']
    body_matches = [t for t in body_matches if not any(ex in t for ex in exclude_terms)]
    if body_matches:
        passed.append(f"\u2705 \u5305\u542b\u6b63\u6587/\u6807\u6ce8\u6587\u5b57 ({min(len(body_matches), 6)} \u6761)")
    else:
        if _is_low_density_page(content) or slide_num in [1, 2, 3, 6, 11, 17, 19]:
            warnings.append("\u26a0\ufe0f  \u5c01\u9762/\u76ee\u5f55/\u8fc7\u6e21\u9875/\u7ed3\u5c3e\u9875\u53ef\u80fd\u4e0d\u9700\u8981\u6b63\u6587")
        else:
            issues.append("\u274c \u7f3a\u5c11\u6b63\u6587\u6587\u5b57")


    # 2b. P14 可见文字中文优先（prompt 可英文写指令，但画面文字默认中文）
    cn_passed, cn_warnings, cn_issues = _validate_visible_text_chinese(content)
    passed.extend(cn_passed)
    warnings.extend(cn_warnings)
    issues.extend(cn_issues)


    # 2c. P15 模板 DNA 差异化（防 09-14 通用咨询化）
    dna_passed, dna_warnings, dna_issues = _validate_template_dna(content, project_dir)
    passed.extend(dna_passed)
    warnings.extend(dna_warnings)
    issues.extend(dna_issues)

    # 3. 色彩
    template_color_set = template_colors | {
        '#0D1117', '#161B22', '#1C2333', '#58A6FF', '#00D4FF', '#39D353',
        '#F5A623', '#FF7B72', '#F0883E', '#79C0FF', '#BC8CFF',
        '#8B949E', '#E6EDF3', '#FFFFFF', '#E0E0E0', '#D0D0D0',
        '#C0C0C0', '#B0B0B0', '#A0A0A0', '#909090',
    }
    prompt_colors = set(re.findall(r'#\w{6}', content))
    non_template_colors = prompt_colors - template_color_set
    if non_template_colors:
        warnings.append(f"\u26a0\ufe0f  \u4f7f\u7528\u4e86\u6a21\u677f\u5916\u7684\u8272\u503c: {non_template_colors}")
    else:
        passed.append("\u2705 \u8272\u5f69\u6765\u81ea\u6a21\u677f\u8272\u5f69\u7cfb\u7edf")

    # 4. 分辨率
    if any(kw in content.lower() for kw in ['2k', '2048x1152', '16:9', '16\uff1a9']):
        passed.append("\u2705 \u6307\u5b9a\u4e86\u5206\u8fa8\u7387\u548c\u6bd4\u4f8b")
    else:
        issues.append("\u274c \u672a\u6307\u5b9a\u5206\u8fa8\u7387\u548c\u6bd4\u4f8b\uff082K, 16:9\uff09")

    # 5. 布局
    layout_kw = ['left', 'right', 'center', 'top', 'bottom', 'side', 'arranged', 'column', 'above', 'below']
    if any(kw in content.lower() for kw in layout_kw):
        passed.append("\u2705 \u6709\u660e\u786e\u7684\u753b\u9762\u5e03\u5c40\u63cf\u8ff0")
    else:
        issues.append("\u274c \u7f3a\u5c11\u753b\u9762\u5e03\u5c40\u63cf\u8ff0\uff08\u5de6\u53f3/\u4e0a\u4e0b/\u4e2d\u5fc3\u7b49\uff09")

    # === 2026-06-15: 特殊页加强（秦始皇复盘卡 #5 修订）===
    # 把"查有"换成"查对"：特殊页标题必须是判断句；卡片/模块堆叠数受限。
    pt_for_p5 = _extract_page_type(content)
    if pt_for_p5 in SPECIAL_PAGE_TYPES:
        sp_name = SPECIAL_PAGE_FRAME_RULES[pt_for_p5]['name']
        # P5a: 标题判断句检查
        title_text = ''
        m_title = re.search(
            r'(?:\*\*[Tt]itle\*\*|[Tt]itle[:\uff1a][^\n]*?)["\'\u201c\u201d]([^\n"\u201c\u201d]{3,40}[\u4e00-\u9fff][^\n"\u201c\u201d]*)["\'\u201c\u201d]',
            content,
        )
        if m_title:
            title_text = m_title.group(1).strip()
        else:
            m_alt = re.search(r'["\u201c]([\u4e00-\u9fff][^"\u201c\u201d]{3,40})["\u201d]', content)
            if m_alt:
                title_text = m_alt.group(1).strip()

        if title_text:
            judgment_markers = ['是', '让', '把', '在', '的', '从', '与', '和', '比', '用', '靠', '走']
            noun_only_patterns = [
                r'^[A-Za-z0-9·•\s\-\.]+$',
                r'^[\u4e00-\u9fff]{2,8}$',
            ]
            is_judgment = any(m in title_text for m in judgment_markers)
            is_pure_noun = any(re.match(p, title_text) for p in noun_only_patterns)
            if pt_for_p5 in ('cover', 'transition', 'closing') and is_pure_noun:
                issues.append(
                    f"\u274c {sp_name} \u6807\u9898\u8fc7\u4e8e\u540d\u8bcd\u5316: '{title_text}' \u2014 "
                    f"\u5efa\u8bae\u6539\u6210\u5224\u65ad/\u9648\u8ff0\u53e5\uff08\u5982\u201cXXX \u662f YYY\u201d\u3001\u201cXXX \u8ba9 YYY\u201d\uff09"
                )
            elif pt_for_p5 in ('cover', 'transition', 'closing') and not is_judgment and not is_pure_noun:
                warnings.append(
                    f"\u26a0\ufe0f  {sp_name} \u6807\u9898 '{title_text}' \u53ef\u80fd\u4e0d\u662f\u5224\u65ad\u53e5\uff0c"
                    f"\u5efa\u8bae\u5305\u542b\u5224\u65ad\u8bcd\uff08\u662f/\u8ba9/\u628a/\u5728/\u7684/\u4e0e/\u7528\uff09"
                )
            else:
                passed.append(f"\u2705 {sp_name} \u6807\u9898\u4e3a\u5224\u65ad/\u9648\u8ff0\u53e5: '{title_text[:25]}...'")

        # P5b: 卡片/模块堆叠数限制
        card_patterns = re.findall(
            r'(?:card|module|box|grid|panel|tile|\u5361\u7247|\u6a21\u5757|\u9762\u677f|\u5217\u8868)',
            content.lower(),
        )
        card_count = len(card_patterns)
        limits = {'cover': 2, 'toc': 4, 'transition': 1, 'closing': 2}
        limit = limits.get(pt_for_p5, 999)
        if card_count > limit:
            issues.append(
                f"\u274c {sp_name} \u5361\u7247/\u6a21\u5757\u5173\u952e\u8bcd\u51fa\u73b0 {card_count} \u6b21\uff08\u4e0a\u9650 {limit}\uff09\u2014 "
                f"\u7279\u6b8a\u9875\u5e94\u5927\u5f00\u5927\u5408\uff0c\u5c11\u5806\u780c"
            )
        else:
            passed.append(
                f"\u2705 {sp_name} \u5361\u7247/\u6a21\u5757\u6570 {card_count} \u2264 {limit}"
            )

    # 6. 内部术语
    internal_terms = [r'\bsetup\b', r'\btension\b', r'\bproof\b', r'\baction\b', r'\bbeat\b']
    found_terms = []
    for term_pattern in internal_terms:
        if re.search(term_pattern, content, re.IGNORECASE):
            found_terms.append(re.sub(r'\\b', '', term_pattern))
    if found_terms:
        issues.append(f"\u274c \u5305\u542b\u5185\u90e8\u672f\u8bed: {found_terms}")
    else:
        passed.append("\u2705 \u65e0\u5185\u90e8\u8bed\u8a00\u6cc4\u9732")

    # 7. 发光参数
    if 'glow' in content.lower() and any(kw in content.lower() for kw in ['blur', 'opacity', 'restrained', 'subtle', '1-3px', 'soft']):
        passed.append("\u2705 \u53d1\u5149\u6548\u679c\u6709\u53c2\u6570\u9650\u5236")
    else:
        warnings.append("\u26a0\ufe0f  \u53d1\u5149\u6548\u679c\u7f3a\u5c11\u5177\u4f53\u53c2\u6570\uff08blur/opacity\uff09")

    # 8. 矛盾指令
    if 'no text' in content.lower() or 'without text' in content.lower():
        issues.append("\u274c \u5305\u542b 'no text' \u6307\u4ee4\uff0c\u4e0e\u4e2d\u6587\u6587\u5b57\u9700\u6c42\u77db\u76fe")
    else:
        passed.append("\u2705 \u65e0\u77db\u76fe\u6307\u4ee4")

    # 9. P1\u2502\u4fe1\u606f\u70b9\u5bc6\u5ea6\u68c0\u67e5
    info_points = _count_info_points(content)
    modules = _count_modules(content)
    is_low_density = _is_low_density_page(content)
    if is_low_density:
        passed.append("\u2139\ufe0f  \u4f4e\u5bc6\u5ea6\u9875\uff08\u5c01\u9762/\u76ee\u5f55/\u8fc7\u6e21/\u7ed3\u5c3e\uff09\uff0c\u8df3\u8fc7\u5bc6\u5ea6\u68c0\u67e5")
    else:
        if info_points >= 15:
            passed.append(f"\u2705 \u4fe1\u606f\u70b9\u5bc6\u5ea6: {info_points}\uff08\u2265 15 \u5408\u683c\uff09")
        elif info_points >= 10:
            warnings.append(f"\u26a0\ufe0f  \u4fe1\u606f\u70b9\u5bc6\u5ea6: {info_points}\uff0810-14 \u504f\u8584\uff0c\u5efa\u8bae\u52a0\u5185\u5bb9\uff09")
        else:
            issues.append(f"\u274c \u4fe1\u606f\u70b9\u5bc6\u5ea6: {info_points}\uff08< 10 \u592a\u8584\uff0c\u5fc5\u987b\u52a0\u5185\u5bb9\uff09")
        if modules >= 3:
            passed.append(f"\u2705 \u5e76\u5217\u6a21\u5757\u6570: {modules}\uff08\u2265 3 \u5408\u683c\uff09")
        elif modules >= 2:
            warnings.append(f"\u26a0\ufe0f  \u5e76\u5217\u6a21\u5757\u6570: {modules}\uff08\u504f\u5c11\uff0c\u5efa\u8bae \u2265 3\uff09")
        else:
            warnings.append(f"\u26a0\ufe0f  \u5e76\u5217\u6a21\u5757\u6570: {modules}\uff08\u5efa\u8bae\u8865\u5145\u6a21\u5757\u5316\u7ed3\u6784\uff09")

    # 10. P2\u2502frame_kind 必填 + 特殊页 page_type 契约
    page_type = _extract_page_type(content)
    frame_kind = _extract_frame_kind(content)
    canonical_frame_kind = normalize_frame_id(frame_kind) if frame_kind else ''
    valid_ids = get_frame_ids()
    if frame_kind:
        if valid_ids and canonical_frame_kind in valid_ids:
            info = find_frame_by_id(canonical_frame_kind)
            name = info['name'] if info else canonical_frame_kind
            suffix = f" → {canonical_frame_kind}" if canonical_frame_kind != frame_kind else ""
            passed.append(f"✅ frame_kind: {frame_kind}{suffix}（{name}）")
        elif valid_ids:
            sample = ', '.join(valid_ids[:8])
            issues.append(f"❌ frame_kind '{frame_kind}' 不在目录里（有效: {sample}...）")
    else:
        if not is_low_density or page_type in SPECIAL_PAGE_TYPES:
            issues.append("❌ 缺 frame_kind 标注（特殊页必须使用专用 frame_kind；内容页必须从 frame_kinds.py 目录里选一种）")

    sp_passed, sp_warnings, sp_issues = _validate_special_page_contract(content, page_type, frame_kind)
    passed.extend(sp_passed)
    warnings.extend(sp_warnings)
    issues.extend(sp_issues)

    # 13. P2\u2502page_type \u00d7 frame_kind \u4e92\u6821\u9a8c\u786c\u95e8\u7981\uff082026-06-15 \u79cd\u59cb\u7687\u590d\u76d8\u5361 #6\uff09
    # \u539f\u59cb\u95ee\u9898\uff1apage_type \u548c frame_kind \u662f\u4e24\u5957\u72ec\u7acb\u7ef4\u5ea6\uff0c\u539f\u811a\u672c\u53ea\u505a\u8f6f\u63d0\u793a\u3002
    # \u73b0\u5728\u5347\u7ea7\u4e3a\u786c\u95e8\u7981\uff1apage_type\u4e3a\u7279\u6b8a\u9875\u65f6 frame_kind \u5fc5\u987b\u5728\u767d\u540d\u5355\u91cc\uff1b
    # page_type \u4e3a\u5185\u5bb9\u9875\u65f6 frame_kind \u5fc5\u987b\u5728 CONTENT_FRAME_KINDS \u91cc\u3002
    if canonical_frame_kind:
        whitelist = get_page_type_whitelist()
        if page_type in whitelist:
            if canonical_frame_kind not in whitelist[page_type]:
                issues.append(
                    f"\u274c P13 page_type\u00d7frame_kind \u4e0d\u5339\u914d\uff1a"
                    f"page_type={page_type} \u4e0d\u5141\u8bb8\u4f7f\u7528 frame_kind='{frame_kind}'\uff08\u5f52\u4e00\u5316: '{canonical_frame_kind}'\uff09\uff0c"
                    f"\u5141\u8bb8\u7684\u6709\uff1a{sorted(whitelist[page_type])}\u3002"
                    f"\u662f\u5426\u628a page_type \u6807\u9519\u4e86\uff1f"
                )
            else:
                passed.append(
                    f"\u2705 P13 page_type\u00d7frame_kind \u4e92\u6821\u9a8c\u901a\u8fc7\uff1a{page_type} \u2192 {canonical_frame_kind}"
                )
        elif page_type == "content":
            content_kinds = get_content_frame_kinds()
            if canonical_frame_kind not in content_kinds:
                issues.append(
                    f"\u274c P13 \u5185\u5bb9\u9875 frame_kind \u4e0d\u5728\u76ee\u5f55\uff1a'{frame_kind}'\uff08\u5f52\u4e00\u5316: '{canonical_frame_kind}'\uff09\u3002"
                    f"\u5185\u5bb9\u9875\u53ea\u80fd\u7528\u8fd9\u4e9b frame_kind\uff1a{sorted(content_kinds)}\u3002"
                )
            else:
                passed.append(
                    f"\u2705 P13 \u5185\u5bb9\u9875 frame_kind \u5728\u76ee\u5f55\u91cc\uff1a{canonical_frame_kind}"
                )

    # 11. P2\u2502palette \u5fc5\u586b\u4e14\u5305\u542b\u5168\u7bc7\u4e3b\u8272
    palette = _extract_palette(content)
    project_palette = _project_palette(project_dir)
    if palette:
        passed.append(f"\u2705 \u914d\u8272\u6807\u6ce8: {len(palette)} \u4e2a\u8272\u503c")
        if project_palette:
            missing = project_palette - palette
            if missing:
                warnings.append(f"\u26a0\ufe0f  \u7f3a\u5168\u7bc7\u7edf\u4e00\u4e3b\u8272: {missing}\uff08\u5e94\u5728 prompt \u91cc\u51fa\u73b0\uff09")
    else:
        if not is_low_density:
            warnings.append("\u26a0\ufe0f  \u7f3a palette \u6807\u6ce8\uff08\u5efa\u8bae: palette: #0D1117,#58A6FF,...\uff09")

    # 12. P2\u2502\u6a21\u677f\u5143\u6570\u636e\u6cc4\u6f0f\u95e8\u7981\uff08\u4e0a\u4e00\u8f6e\u88ab\u4e0a\u4e0a\u4e86\uff09
    #    nano-banana \u4f1a\u628a prompt \u91cc\u7684\u7ed3\u6784\u5316\u914d\u8272\u58f0\u660e\uff08palette: #... / under 5%\uff09\u5f53\u6587\u5b57\u6e32\u67d3\u3002
    #    \u89c4\u5219\uff1aprompt body \u91cc\u4e0d\u5141\u8bb8\u51fa\u73b0\u8fd9\u4e9b\u201c\u5e94\u8be5\u53ea\u5728 template \u91cc\u201d\u7684\u5b57\u9762\u91cf\u3002
    metadata_leak_patterns = [
        (r'palette\s*[:\uff1a]\s*#', '\u4e0d\u8981\u5728 prompt \u91cc\u5199\u7ed3\u6784\u5316 palette \u5b57\u9762\u91cf\u3002\u914d\u8272\u53ea\u80fd\u5199\u6210\u81ea\u7136\u8bed\u8a00\uff08\u5982\u201c\u4e3b\u8272 = \u6731\u7ea2 + \u7384\u9ed1 + \u9752\u94dc\u201d\uff09\uff0c\u4e0d\u80fd\u5199\u201cpalette: #C23B22, #1B2A4A\u201d\u3002\u5426\u5219 nano-banana \u4f1a\u628a\u914d\u8272\u4ee3\u7801\u539f\u6837\u753b\u5230\u753b\u9762\u4e0a\u3002'),
        (r'#[0-9A-Fa-f]{6}', '\u4e0d\u8981\u5728 prompt body \u91cc\u5199 hex \u8272\u503c\uff08\u5982 #C23B22\uff09\u3002\u8fd9\u4f1a\u88ab nano-banana \u5f53\u6587\u5b57\u6e32\u67d3\u3002\u4ec5\u5728 template/selected-template.md \u4e2d\u4f5c\u4e3a\u5185\u90e8\u914d\u8272\u4f9d\u636e\u4f7f\u7528\u3002'),
        (r'under\s*\d+\s*%', '\u4e0d\u8981\u5199\u201cunder 5%\u201d\u8fd9\u79cd\u4f7f\u7528\u6bd4\u4f8b\u6ce8\u91ca\uff0c\u5b83\u4f1a\u88ab nano-banana \u539f\u6837\u6e32\u67d3\u5230\u753b\u9762\u4e0a\u3002\u6539\u5199\u6210\u201c\u91d1\u8272\u4ec5\u4f5c\u6781\u5c11\u70b9\u7eb7\u201d\u8fd9\u79cd\u81ea\u7136\u8bed\u8a00\u3002'),
        (r'#FDF6EC.*#F5E6D3', '\u4e0d\u8981\u5728 prompt \u91cc\u8fde\u7eed\u5217\u51fa\u591a\u4e2a\u7c97\u4f53\u8272\u503c\u3002\u4e0a\u4e00\u8f6e\u88ab\u4e0a\u4e0a\u4e86\uff0c18 \u9875\u5e95\u90e8\u51fa\u73b0\u4e86\u5b8c\u6574\u8272\u5361\u3002'),
    ]
    leak_hits = []
    for pat, msg in metadata_leak_patterns:
        if re.search(pat, content, re.IGNORECASE):
            leak_hits.append(msg)
    if leak_hits:
        issues.append(f"\u274c \u6a21\u677f\u5143\u6570\u636e\u6cc4\u6f0f\uff08nano-banana \u4f1a\u5c06\u8fd9\u4e9b\u5185\u5bb9\u539f\u6837\u6e32\u67d3\u4e3a\u6587\u5b57/\u8272\u5757\uff09\uff1a" + '; '.join(leak_hits))
    else:
        passed.append("\u2705 \u65e0\u6a21\u677f\u5143\u6570\u636e\u6cc4\u6f0f\uff08\u65e0 palette/hex/under XX% \u5b57\u9762\u91cf\uff09")

    return passed, warnings, issues


def main():
    if len(sys.argv) < 2:
        print("\u7528\u6cd5: python3 validate-prompts.py <\u9879\u76ee\u76ee\u5f55>")
        sys.exit(1)

    project_dir = sys.argv[1]
    template_path = os.path.join(project_dir, 'selected-template.md')
    prompts_dir = os.path.join(project_dir, 'prompts')

    if not os.path.exists(template_path):
        print("\u274c \u672a\u627e\u5230 selected-template.md")
        sys.exit(1)
    if not os.path.exists(prompts_dir):
        print("\u274c \u672a\u627e\u5230 prompts/ \u76ee\u5f55")
        sys.exit(1)

    template_colors = parse_template(template_path)
    prompt_files = sorted(glob.glob(os.path.join(prompts_dir, '*.md')))
    total_slides = len(prompt_files)

    if not prompt_files:
        print("\u274c prompts/ \u76ee\u5f55\u4e2d\u6ca1\u6709 prompt \u6587\u4ef6")
        sys.exit(1)

    # P2\u2502\u5168\u7bc7 frame_kind \u4e0d\u91cd\u590d\u68c0\u67e5\uff08\u6c47\u603b\u7ea7\uff09
    project_frame_kinds = _project_frame_kinds(project_dir)
    if project_frame_kinds:
        from collections import Counter
        dup = [k for k, c in Counter(project_frame_kinds).items() if c > 1]
        if dup:
            print(f"\u274c outline.md \u4e2d frame_kind \u91cd\u590d: {dup}\uff08\u6bcf\u9875\u5e94\u4e0d\u540c\uff09")
            sys.exit(1)
        else:
            print(f"\u2705 outline.md frame_kind \u5168\u7bc7\u4e0d\u91cd\u590d: {len(project_frame_kinds)} \u9875 / {len(set(project_frame_kinds))} \u79cd")

    print(f"📋 \u6a21\u677f\u8272\u503c: {len(template_colors)} \u4e2a")
    print(f"📋 \u5f85\u6821\u9a8c prompt: {total_slides} \u4e2a")
    print()

    total_passed = 0
    total_warnings = 0
    total_issues = 0

    for pf in prompt_files:
        basename = os.path.basename(pf)
        match = re.match(r'(\d+)', basename)
        slide_num = int(match.group(1)) if match else 0

        passed, warnings, issues = validate_prompt(
            pf, template_colors, slide_num, total_slides, project_dir,
        )

        status = "\u2705 \u901a\u8fc7" if not issues else "\u274c \u5931\u8d25"
        print(f"  {status} {basename}")

        for p in passed:
            print(f"    {p}")
            total_passed += 1
        for w in warnings:
            print(f"    {w}")
            total_warnings += 1
        for i in issues:
            print(f"    {i}")
            total_issues += 1
        print()

    print("=" * 50)
    print(f"📊 \u6821\u9a8c\u7ed3\u679c:")
    print(f"   \u2705 \u901a\u8fc7\u9879: {total_passed}")
    print(f"   \u26a0\ufe0f  \u8b66\u544a\u9879: {total_warnings}")
    print(f"   \u274c \u5931\u8d25\u9879: {total_issues}")
    print()

    if total_issues > 0:
        print("\u274c \u6709\u5931\u8d25\u9879\uff0c\u8bf7\u5148\u4fee\u590d\u518d\u751f\u56fe\u3002")
        sys.exit(1)
    else:
        print("\u2705 \u6240\u6709 prompt \u901a\u8fc7\u6821\u9a8c\uff0c\u53ef\u4ee5\u751f\u56fe\u3002")


if __name__ == '__main__':
    main()
