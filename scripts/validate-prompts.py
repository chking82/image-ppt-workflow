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

def parse_template(template_path):
    """解析模板，提取色彩系统中的色值"""
    with open(template_path) as f:
        content = f.read()
    colors = set(re.findall(r'`(#\w{6})`', content))
    return colors


def validate_prompt(prompt_path, template_colors, slide_num, total_slides):
    """校验单个 prompt 文件"""
    with open(prompt_path) as f:
        content = f.read()
    
    issues = []
    warnings = []
    passed = []
    
    # 1. 检查是否包含中文标题文字 — 放宽匹配
    # 匹配 "Title at top: \"中文标题\" in bold" 或 "title \"中文\"" 等
    title_matches = re.findall(r'(?:[Tt]itle|heading|chapter number|number|label)[^"\n]{0,60}["\']([^"\']{3,50}[\u4e00-\u9fff][^"\']*)["\']', content)
    if not title_matches:
        # 兜底：匹配任何引号内的较长中文短语
        title_matches = re.findall(r'["\']([\u4e00-\u9fff][^"\']{3,50})["\']', content)
    # 过滤掉明显不是标题的短文本
    title_matches = [t for t in title_matches if len(t) > 5]
    if title_matches:
        passed.append(f"✅ 包含标题文字: {title_matches[0][:30]}...")
    else:
        issues.append(f"❌ 缺少标题文字（原样中文）")
    
    # 2. 检查是否包含正文/标注文字 — 放宽匹配
    # 匹配 body text, annotation, metric, labeled 等后面的中文
    body_matches = []
    body_patterns = [
        r'(?:[Bb]ody text|annotation|metric|labeled|subtitle|arrow)[^"\n]{0,80}["\']([^"\']{3,60}[\u4e00-\u9fff][^"\']*)["\']',
        r'["\']([\u4e00-\u9fff][^"\']{4,60})["\']',
    ]
    for pat in body_patterns:
        body_matches.extend(re.findall(pat, content))
    # 去重，排除标题
    body_matches = list(set([t.strip() for t in body_matches if len(t) > 4]))
    body_matches = [t for t in body_matches if t not in title_matches]
    # 排除内部术语
    exclude_terms = ['setup', 'tension', 'resolution', 'proof', 'action', 'beat', 'Compute-Bound', 'Memory-Bound']
    body_matches = [t for t in body_matches if not any(ex in t for ex in exclude_terms)]
    
    if body_matches:
        passed.append(f"✅ 包含正文/标注文字 ({min(len(body_matches), 6)} 条)")
    else:
        if slide_num in [1, 2, 3, 6, 11, 17, 19]:
            warnings.append("⚠️  封面/目录/过渡页/结尾页可能不需要正文")
        else:
            issues.append("❌ 缺少正文文字")
    
    # 3. 检查色彩是否来自模板
    template_color_set = template_colors | {
        '#0D1117', '#161B22', '#1C2333', '#58A6FF', '#00D4FF', '#39D353',
        '#F5A623', '#FF7B72', '#F0883E', '#79C0FF', '#BC8CFF',
        '#8B949E', '#E6EDF3', '#FFFFFF', '#E0E0E0', '#D0D0D0',
        '#C0C0C0', '#B0B0B0', '#A0A0A0', '#909090',
    }
    prompt_colors = set(re.findall(r'#\w{6}', content))
    non_template_colors = prompt_colors - template_color_set
    if non_template_colors:
        warnings.append(f"⚠️  使用了模板外的色值: {non_template_colors}")
    else:
        passed.append("✅ 色彩来自模板色彩系统")
    
    # 4. 检查分辨率和比例
    if any(kw in content.lower() for kw in ['2k', '2048x1152', '16:9', '16：9']):
        passed.append("✅ 指定了分辨率和比例")
    else:
        issues.append("❌ 未指定分辨率和比例（2K, 16:9）")
    
    # 5. 检查是否有明确的画面布局描述
    layout_kw = ['left', 'right', 'center', 'top', 'bottom', 'side', 'arranged', 'column', 'above', 'below']
    has_layout = any(kw in content.lower() for kw in layout_kw)
    if has_layout:
        passed.append("✅ 有明确的画面布局描述")
    else:
        issues.append("❌ 缺少画面布局描述（左右/上下/中心等）")
    
    # 6. 检查内部语言净化（使用单词边界，避免误匹配 resolution 等单词片段）
    internal_terms = [r'\bsetup\b', r'\btension\b', r'\bproof\b', r'\baction\b', r'\bbeat\b']
    found_terms = []
    for term_pattern in internal_terms:
        if re.search(term_pattern, content, re.IGNORECASE):
            found_terms.append(re.sub(r'\\b', '', term_pattern))
    if found_terms:
        issues.append(f"❌ 包含内部术语: {found_terms}")
    else:
        passed.append("✅ 无内部语言泄露")
    
    # 7. 检查发光效果参数
    if 'glow' in content.lower() and any(kw in content.lower() for kw in ['blur', 'opacity', 'restrained', 'subtle', '1-3px', 'soft']):
        passed.append("✅ 发光效果有参数限制")
    else:
        warnings.append("⚠️  发光效果缺少具体参数（blur/opacity）")
    
    # 8. 检查是否避免了 "NO text" 等矛盾指令
    if 'no text' in content.lower() or 'without text' in content.lower():
        issues.append("❌ 包含 'no text' 指令，与中文文字需求矛盾")
    else:
        passed.append("✅ 无矛盾指令")
    
    return passed, warnings, issues


def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate-prompts.py <项目目录>")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    template_path = os.path.join(project_dir, 'selected-template.md')
    prompts_dir = os.path.join(project_dir, 'prompts')
    
    if not os.path.exists(template_path):
        print("❌ 未找到 selected-template.md")
        sys.exit(1)
    if not os.path.exists(prompts_dir):
        print("❌ 未找到 prompts/ 目录")
        sys.exit(1)
    
    template_colors = parse_template(template_path)
    prompt_files = sorted(glob.glob(os.path.join(prompts_dir, '*.md')))
    total_slides = len(prompt_files)
    
    if not prompt_files:
        print("❌ prompts/ 目录中没有 prompt 文件")
        sys.exit(1)
    
    print(f"📋 模板色值: {len(template_colors)} 个")
    print(f"📋 待校验 prompt: {total_slides} 个")
    print()
    
    total_passed = 0
    total_warnings = 0
    total_issues = 0
    
    for pf in prompt_files:
        basename = os.path.basename(pf)
        match = re.match(r'(\d+)', basename)
        slide_num = int(match.group(1)) if match else 0
        
        passed, warnings, issues = validate_prompt(pf, template_colors, slide_num, total_slides)
        
        status = "✅ 通过" if not issues else "❌ 失败"
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
    print(f"📊 校验结果:")
    print(f"   ✅ 通过项: {total_passed}")
    print(f"   ⚠️  警告项: {total_warnings}")
    print(f"   ❌ 失败项: {total_issues}")
    print()
    
    if total_issues > 0:
        print("❌ 有失败项，请先修复再生图。")
        sys.exit(1)
    else:
        print("✅ 所有 prompt 通过校验，可以生图。")


if __name__ == '__main__':
    main()
