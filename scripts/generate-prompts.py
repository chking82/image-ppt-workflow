#!/usr/bin/env python3
"""generate-prompts.py — 基于模板+大纲生成每页 Prompt
用法: python3 scripts/generate-prompts.py <project-dir>
  读取: <project-dir>/selected-template.md + <project-dir>/outline.md
  输出: <project-dir>/prompts/NN-slide-xxx.md
"""

import re
import os
import sys
import json

def parse_template(template_path):
    """解析模板，提取色彩系统、版式结构、文字系统、质感规则、页面类型模板"""
    with open(template_path) as f:
        content = f.read()
    
    info = {
        'raw': content,
        'colors': {},
        'layouts': [],
        'text_rules': [],
        'texture_rules': [],
        'page_templates': {},
        'checklist': [],
    }
    
    # 提取色彩系统表格
    color_section = re.search(r'## 色彩系统\n(.*?)\n##', content, re.DOTALL)
    if color_section:
        for row in re.findall(r'\|\s*\*\*(.+?)\*\*\s*\|\s*(\d+%)\s*\|\s*(.+?)\s*\|', color_section.group(1)):
            info['colors'][row[0]] = {'ratio': row[1], 'desc': row[2]}
    
    # 提取版式结构
    layout_section = re.search(r'## 版式结构\n(.*?)\n##', content, re.DOTALL)
    if layout_section:
        info['layouts'] = re.findall(r'-\s*\*\*(.+?)\*\*[：:]\s*(.+)', layout_section.group(1))
        info['layout_subsections'] = re.findall(r'### (.+?)\n(.*?)(?=###|\n##)', layout_section.group(1), re.DOTALL)
    
    # 提取文字系统
    text_section = re.search(r'## 文字系统\n(.*?)\n##', content, re.DOTALL)
    if text_section:
        info['text_rules'] = re.findall(r'-\s*\*\*(.+?)\*\*[：:]\s*(.+)', text_section.group(1))
    
    # 提取质感与材质
    texture_section = re.search(r'## 质感与材质\n(.*?)\n##', content, re.DOTALL)
    if texture_section:
        info['texture_rules'] = re.findall(r'-\s*(?:\*\*(.+?)\*\*[：:]?\s*)?(.+)', texture_section.group(1))
    
    # 提取页面类型模板
    page_section = re.search(r'## 页面类型模板\n(.*?)\n##', content, re.DOTALL)
    if page_section:
        for page_type in re.finditer(r'### (.+?)\n(.*?)(?=###|$)', page_section.group(1), re.DOTALL):
            type_name = page_type.group(1).strip()
            rules = [l.strip('- ') for l in page_type.group(2).strip().split('\n') if l.strip().startswith('-')]
            info['page_templates'][type_name] = rules
    
    # 提取检查清单
    checklist_section = re.search(r'## (?:质量检查|情感过滤)清单\n(.*?)\n##', content, re.DOTALL)
    if checklist_section:
        info['checklist'] = re.findall(r'-\s*\[\s*\]\s*(.+)', checklist_section.group(1))
    
    return info


def parse_outline(outline_path):
    """解析 outline.md，提取每页信息"""
    with open(outline_path) as f:
        content = f.read()
    
    slides = []
    for block in re.split(r'\n(?=## Slide \d+)', content):
        block = block.strip()
        if not block.startswith('## Slide'):
            continue
        
        slide = {
            'number': None,
            'title': '',
            'type': '',
            'beat': '',
            'content': [],
            'visual': {},
            'layout_suggestion': '',
        }
        
        # 提取页码和标题
        title_match = re.match(r'## Slide (\d+) - (.+)', block.split('\n')[0])
        if title_match:
            slide['number'] = int(title_match.group(1))
            slide['title'] = title_match.group(2).strip()
        
        # 提取类型
        type_match = re.search(r'\*\*类型\*\*[：:]\s*(.+)', block)
        if type_match:
            slide['type'] = type_match.group(1).strip()
        
        # 提取 beat
        beat_match = re.search(r'\*\*Beat\*\*[：:]\s*(.+)', block)
        if beat_match:
            slide['beat'] = beat_match.group(1).strip()
        
        # 提取关键内容
        content_match = re.search(r'\*\*关键内容\*\*[：:]\n(.*?)(?=\n\s*- \*\*|\Z)', block, re.DOTALL)
        if content_match:
            slide['content'] = [l.strip('- ') for l in content_match.group(1).strip().split('\n') if l.strip()]
        
        # 提取视觉规格
        visual_match = re.search(r'\*\*视觉规格\*\*[：:]\n(.*?)(?=\n\s*- \*\*|\Z)', block, re.DOTALL)
        if visual_match:
            slide['visual']['raw'] = visual_match.group(1).strip()
        
        # 提取版式建议
        layout_match = re.search(r'\*\*版式建议\*\*[：:]\s*(.+)', block)
        if layout_match:
            slide['layout_suggestion'] = layout_match.group(1).strip()
        
        slides.append(slide)
    
    return slides


def match_page_template(slide_type, template_info):
    """匹配模板中的页面类型模板"""
    page_templates = template_info['page_templates']
    
    # 直接匹配
    for pt_name in page_templates:
        if any(kw in slide_type for kw in [pt_name[:4], pt_name.split('页')[0]]):
            return pt_name, page_templates[pt_name]
    
    # 模糊匹配
    type_keywords = {
        '封面': ['封面', 'cover'],
        '目录': ['目录', 'toc'],
        '过渡': ['过渡', 'transition', '章节'],
        '结尾': ['结尾', 'ending', '总结', '谢谢'],
        '数据指标': ['数据指标', 'KPI', '指标'],
        '对比分析': ['对比', 'comparison', 'Before', 'After'],
        '趋势分析': ['趋势', 'trend', '折线'],
        '架构': ['架构', '技术栈', 'architecture'],
        '内容': ['内容', '图文', 'content'],
        '中心辐射': ['中心辐射', '中心', '辐射'],
    }
    
    for slide_kw, pt_keywords in type_keywords.items():
        for kw in pt_keywords:
            if kw.lower() in slide_type.lower():
                for pt_name in page_templates:
                    if slide_kw in pt_name:
                        return pt_name, page_templates[pt_name]
    
    return None, []


def generate_prompt(slide, template_info, slide_idx):
    """为单个 slide 生成完整 prompt"""
    pt_name, pt_rules = match_page_template(slide['type'], template_info)
    
    # 构建 prompt
    prompt_parts = []
    
    # 背景
    bg_color = template_info['colors'].get('底色', {}).get('desc', 'dark blue-black gradient')
    color_codes = re.findall(r'`(#\w+)`', bg_color)
    if not color_codes:
        color_codes = ['#0D1117']
    prompt_parts.append(f"A presentation slide with {color_codes[0]} gradient background, subtle grid lines")
    
    # 标题（始终包含）
    if slide['title']:
        prompt_parts.append(f'Title at top: "{slide["title"]}" in bold white (44pt) with neon glow')
    
    # 页面类型特定规则
    if pt_rules:
        for rule in pt_rules:
            # 跳过纯装饰性规则，只保留布局相关的
            if any(kw in rule for kw in ['标题', '副标题', '背景', '底部', '居中', '左侧', '右侧', '布局', '排列', '列表', '卡片']):
                prompt_parts.append(rule)
    
    # 关键内容作为正文
    if slide['content']:
        content_text = '", "'.join(slide['content'][:4])  # 最多4条
        prompt_parts.append(f'Body text in light grey: "{content_text}"')
    
    # 版式建议
    if slide['layout_suggestion']:
        prompt_parts.append(f'Layout: {slide["layout_suggestion"]}')
    
    # 通用结尾
    prompt_parts.append("All neon glows are restrained (1-3px blur, 40% opacity). 2K resolution, 16:9 aspect ratio.")
    
    return ". ".join(prompt_parts)


def main():
    if len(sys.argv) < 2:
        print("用法: python3 generate-prompts.py <project-dir>")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    template_path = os.path.join(project_dir, 'selected-template.md')
    outline_path = os.path.join(project_dir, 'outline.md')
    prompts_dir = os.path.join(project_dir, 'prompts')
    
    if not os.path.exists(template_path):
        print("❌ 未找到 selected-template.md")
        sys.exit(1)
    if not os.path.exists(outline_path):
        print("❌ 未找到 outline.md")
        sys.exit(1)
    
    os.makedirs(prompts_dir, exist_ok=True)
    
    template_info = parse_template(template_path)
    slides = parse_outline(outline_path)
    
    print(f"📋 模板: {os.path.basename(template_path)}")
    print(f"   色彩: {len(template_info['colors'])} 个层级")
    print(f"   页面类型模板: {len(template_info['page_templates'])} 种")
    print(f"📋 大纲: {len(slides)} 页")
    print()
    
    for slide in slides:
        prompt = generate_prompt(slide, template_info, slide['number'])
        
        # 写 prompt 文件
        num_str = f"{slide['number']:02d}"
        filename = f"{num_str}-slide-{slide['title'][:10]}.md"
        filepath = os.path.join(prompts_dir, filename)
        
        content = f"""## Slide {slide['number']} - {slide['title']}

**页面类型**: {slide['type']}

**提示词**:
{prompt}
"""
        with open(filepath, 'w') as f:
            f.write(content)
        
        matched, _ = match_page_template(slide['type'], template_info)
        match_info = f" → 匹配模板「{matched}」" if matched else ""
        print(f"  ✅ Slide {slide['number']:2d}: {slide['title'][:30]}{match_info}")
        print(f"     → {filepath}")
    
    print(f"\n✅ 已生成 {len(slides)} 个 prompt 文件到 {prompts_dir}/")


if __name__ == '__main__':
    main()
