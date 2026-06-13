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
    from frame_kinds import get_frame_ids, find_frame_by_id
except ImportError:
    get_frame_ids = lambda: []
    find_frame_by_id = lambda x: None


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


def _extract_frame_kind(content: str) -> str:
    """从 prompt 中提取 frame_kind 标注"""
    pats = [
        r'frame[_\s]kind[:\s]*[`"\']?([a-z_\-]+)[`"\']?',
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
        if slide_num in [1, 2, 3, 6, 11, 17, 19]:
            warnings.append("\u26a0\ufe0f  \u5c01\u9762/\u76ee\u5f55/\u8fc7\u6e21\u9875/\u7ed3\u5c3e\u9875\u53ef\u80fd\u4e0d\u9700\u8981\u6b63\u6587")
        else:
            issues.append("\u274c \u7f3a\u5c11\u6b63\u6587\u6587\u5b57")

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

    # 10. P2\u2502frame_kind \u5fc5\u586b
    frame_kind = _extract_frame_kind(content)
    valid_ids = get_frame_ids()
    if frame_kind:
        if valid_ids and frame_kind in valid_ids:
            info = find_frame_by_id(frame_kind)
            name = info['name'] if info else frame_kind
            passed.append(f"\u2705 frame_kind: {frame_kind}\uff08{name}\uff09")
        elif valid_ids:
            sample = ', '.join(valid_ids[:6])
            issues.append(f"\u274c frame_kind '{frame_kind}' \u4e0d\u5728\u76ee\u5f55\u91cc\uff08\u6709\u6548: {sample}...\uff09")
    else:
        if not is_low_density:
            issues.append("\u274c \u7f3a frame_kind \u6807\u6ce8\uff08\u5fc5\u987b\u4ece frame_kinds.py 14 \u79cd\u6846\u67b6\u91cc\u9009\u4e00\u79cd\uff09")

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
