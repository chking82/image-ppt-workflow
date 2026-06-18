#!/usr/bin/env python3
"""Generate all 9 template example images via grsai API."""
import requests, json, os, time, sys

API_KEY = os.environ.get("GRSAI_API_KEY", "")
if not API_KEY:
    print("Error: GRSAI_API_KEY not set. export GRSAI_API_KEY=xxx")
    sys.exit(1)

API_URL = "https://api.grsai.com/v1/images/generations"

OUTPUT_DIRS = {
    "02": "templates/examples/02",
    "03": "templates/examples/03",
    "04": "templates/examples/04",
}

prompts = [
    # Template 02 - Hand-drawn comic
    {
        "dir": "02", "name": "cover.png",
        "prompt": """Presentation slide cover page in a hand-drawn comic illustration style. The background is warm white (#FFFDF5) with light blue (#F0F7FF) and light pink (#FFF5F5) panels. A large hand-lettered title "手绘漫画模板" in black (#2D2D2D) sketchy hand-drawn font at center. Around it: playful cartoon characters with big eyes, speech bubbles/dialogue boxes with doodle-style borders, comic panel grid lines, marker-style color fills in red (#FF6B6B), green (#4ECDC4), yellow (#FFD93D), and purple (#6C5CE7). Speed lines, explosion stars, crayon texture, uneven hand-drawn borders. The entire slide looks like a hand-sketched comic book page made with markers and pens. Professional presentation quality, 16:9."""
    },
    {
        "dir": "02", "name": "toc.png",
        "prompt": """Presentation table of contents page in hand-drawn comic style. Background warm white (#FFFDF5) with comic panel grid layout dividing the page into 6 rectangle panels. Top banner with hand-lettered title "目录" in black (#2D2D2D). Each of 6 panels contains one chapter number and title in sketchy hand-drawn font: 1-背景分析、2-核心策略、3-实施方案、4-数据支撑、5-案例展示、6-总结展望. Small cartoon characters and doodles next to each panel. Speech bubbles, marker color accents in red (#FF6B6B), green (#4ECDC4), yellow (#FFD93D), purple (#6C5CE7). Comic-style speed lines, explosion stars, crayon texture borders. Professional 16:9 presentation slide."""
    },
    {
        "dir": "02", "name": "content.png",
        "prompt": """Presentation content page in hand-drawn comic style. Comic panel strip layout with 3 horizontal panels. Background warm white (#FFFDF5). Each panel contains one numbered point (#1 #2 #3) in hand-drawn circular badges with sketchy black (#2D2D2D) ink. A cartoon character in a speech bubble explaining each point. Hand-drawn content text "手绘编号要点一" "手绘编号要点二" "手绘编号要点三". Marker color accents in red (#FF6B6B), green (#4ECDC4), yellow (#FFD93D). Crayon texture, speed lines, comic panel borders. Professional 16:9 presentation quality."""
    },

    # Template 03 - Accenture minimalist
    {
        "dir": "03", "name": "cover.png",
        "prompt": """Presentation cover slide in Accenture-style minimalist corporate design. Pure white (#FFFFFF) background with generous negative space. Large bold title "商务极简方案" in deep charcoal (#333333) sans-serif font at center. A thin accent line in consulting blue (#0066CC) beneath the title. Small minimalist subtitle in gray. Clean grid alignment, no textures or gradients. Small consulting blue logo placeholder at bottom-right. Extreme simplicity, no decorative elements. Professional 16:9 presentation quality."""
    },
    {
        "dir": "03", "name": "toc.png",
        "prompt": """Presentation table of contents slide in Accenture-style minimalist design. Pure white (#FFFFFF) background. Clean grid layout with 6 chapter items arranged in two rows of three. Each item has a small number in consulting blue (#0066CC) followed by black (#333333) chapter title: 1-背景分析、2-核心策略、3-实施方案、4-数据支撑、5-案例展示、6-总结展望. Thin horizontal dividers between rows. Perfect grid alignment, generous spacing. Top left has small "目录" label in consulting blue. No textures or decoration. Professional 16:9 presentation quality."""
    },
    {
        "dir": "03", "name": "content.png",
        "prompt": """Presentation content slide in Accenture-style minimalist design. Two-column layout on pure white (#FFFFFF) background. Left column: chapter number "03" in large consulting blue (#0066CC) font, chapter title "实施方案" in black (#333333). Right column: an insight box with thin consulting blue border containing a key insight quote. Below: a bullet point list of 3 key action items in clean sans-serif text. No textures, no decorative elements. Perfect grid alignment. Professional 16:9 presentation quality."""
    },

    # Template 04 - Tech data viz
    {
        "dir": "04", "name": "cover.png",
        "prompt": """Presentation cover slide in futuristic tech data-visualization style. Dark background (#0D1117 deep space gray) with subtle grid texture. Large title "科技数据方案" in glowing neon blue (#58A6FF) with light emission effect. Floating data card elements around the title: small transparent glass-panel cards with neon border highlights showing data metrics. Neon pink (#FF6B9D) and neon green (#3FB950) accent glows. Amber yellow (#D29922) sparkle dots. Grid matrix pattern on the dark background. High-tech cyberpunk dashboard aesthetic. Professional 16:9 presentation quality."""
    },
    {
        "dir": "04", "name": "toc.png",
        "prompt": """Presentation table of contents slide in futuristic tech data-visualization style. Dark background (#0D1117 deep space gray) with subtle grid texture. 6 transparent glass-panel data cards arranged in 2 rows of 3, each with neon border glow in blue (#58A6FF). Each card contains a small colored icon and chapter title: 1-背景分析、2-核心策略、3-实施方案、4-数据支撑、5-案例展示、6-总结展望. Neon pink (#FF6B9D) accent on cards 1 and 4, neon green (#3FB950) on card 5. Amber yellow (#D29922) data sparkle dots. Heading "目录" in glowing neon blue at top. Professional 16:9 presentation quality."""
    },
    {
        "dir": "04", "name": "content.png",
        "prompt": """Presentation content slide in futuristic tech data-dashboard style. Dark background (#0D1117) with grid texture. Dashboard card grid layout: top row has 3 small data metric cards with glowing neon values in blue (#58A6FF), pink (#FF6B9D), green (#3FB950) on semi-transparent dark glass panels with neon border (#161B22). Center: a larger data chart visualization card with line graph in neon green and amber yellow (#D29922) on dark background. Right side: 3 key bullet points in white text. Everything has subtle glow effects. Professional 16:9 presentation quality."""
    },
]

def generate_image(prompt_data, attempt=1):
    dir_key = prompt_data["dir"]
    filename = prompt_data["name"]
    prompt_text = prompt_data["prompt"]
    out_dir = OUTPUT_DIRS[dir_key]
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    print(f"[{attempt}] Generating {dir_key}/{filename}...")
    
    # Use gpt-image-2-vip first; fallback to nano-banana-2
    model = "gpt-image-2-vip"
    if attempt >= 4:
        model = "nano-banana-2"
        print(f"Fallback to {model}")
    
    payload = {
        "model": model,
        "prompt": prompt_text,
        "n": 1,
        "size": "2048x1152",
        "response_format": "url"
    }

    try:
        r = requests.post(API_URL, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        img_url = data["data"][0]["url"]
        
        # Download the image
        img_r = requests.get(img_url, timeout=60)
        img_r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(img_r.content)
        
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  ✓ Saved {out_path} ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        if attempt < 4:
            print(f"  Retrying ({attempt+1}/4)...")
            time.sleep(3)
            return generate_image(prompt_data, attempt + 1)
        else:
            print(f"  ✗ Failed after 4 attempts")
            return False

success = 0
fail = 0
for p in prompts:
    if generate_image(p):
        success += 1
    else:
        fail += 1
    time.sleep(2)  # Rate limit between requests

print(f"\n=== Done: {success} success, {fail} failed ===")
if fail > 0:
    sys.exit(1)
