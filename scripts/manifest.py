#!/usr/bin/env python3
"""manifest.py — 校验 image-ppt-workflow 的 slides manifest 完整性

用法:
  # 1) 校验某个 manifest 文件
  python3 scripts/manifest.py check <项目>/slides-manifest.json

  # 2) 对比 manifest 与 slides/ 目录（找出缺图/孤儿）
  python3 scripts/manifest.py reconcile <项目>/slides-manifest.json <项目>/slides/

  # 3) 对比 manifest 与 prompts/ 目录（找出 prompt 缺 manifest 记录）
  python3 scripts/manifest.py reconcile-prompts <项目>/slides-manifest.json <项目>/prompts/

退出码:
  0 全部 OK
  1 校验失败
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def _die(msg: str, code: int = 1) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    raise SystemExit(code)


def _ok(msg: str) -> None:
    print(f"✅ {msg}")


def load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        _die(f"manifest 不存在: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _die(f"manifest JSON 解析失败: {e}")
    if "version" not in data:
        _die("manifest 缺 version 字段")
    if "slides" not in data or not isinstance(data["slides"], list):
        _die("manifest 缺 slides 数组")
    return data


def cmd_check(manifest: Path) -> int:
    data = load_manifest(manifest)
    slides = data["slides"]
    print(f"📋 {manifest.name}: {len(slides)} 张图")
    issues: List[str] = []
    seen_sources: set = set()
    for idx, slide in enumerate(slides, start=1):
        for required in ("generated_source", "model", "generated_at"):
            if not slide.get(required):
                issues.append(f"slide #{idx}: 缺 {required}")
        src = slide.get("generated_source")
        if src in seen_sources:
            issues.append(f"slide #{idx}: 重复 generated_source '{src}'")
        if src:
            seen_sources.add(src)
    if issues:
        print("\n".join(f"  - {x}" for x in issues))
        return _die(f"manifest 不通过校验 ({len(issues)} 个问题)")
    _ok("manifest 校验通过")
    return 0


def cmd_reconcile(manifest: Path, slides_dir: Path) -> int:
    data = load_manifest(manifest)
    recorded = {s["generated_source"] for s in data["slides"]}
    if not slides_dir.exists():
        _die(f"slides 目录不存在: {slides_dir}")
    on_disk = {p.name for p in slides_dir.glob("*.png")}
    missing_in_manifest = on_disk - {Path(s).name for s in recorded}
    missing_on_disk = {Path(s).name for s in recorded} - on_disk
    if missing_in_manifest:
        print("⚠️  slides/ 下有但 manifest 没记录:")
        for n in sorted(missing_in_manifest):
            print(f"  - {n}")
    if missing_on_disk:
        print("⚠️  manifest 记录了但 slides/ 下找不到:")
        for n in sorted(missing_on_disk):
            print(f"  - {n}")
    if not missing_in_manifest and not missing_on_disk:
        _ok("manifest ↔ slides 目录一致")
        return 0
    return 1


def cmd_reconcile_prompts(manifest: Path, prompts_dir: Path) -> int:
    data = load_manifest(manifest)
    recorded = {Path(s.get("prompt_file", "")).name for s in data["slides"] if s.get("prompt_file")}
    if not prompts_dir.exists():
        _die(f"prompts 目录不存在: {prompts_dir}")
    on_disk = {p.name for p in prompts_dir.glob("*.md")}
    missing_in_manifest = on_disk - recorded
    missing_on_disk = recorded - on_disk
    if missing_in_manifest:
        print("⚠️  prompts/ 下有但 manifest 没记录:")
        for n in sorted(missing_in_manifest):
            print(f"  - {n}")
    if missing_on_disk:
        print("⚠️  manifest 记录了但 prompts/ 下找不到:")
        for n in sorted(missing_on_disk):
            print(f"  - {n}")
    if not missing_in_manifest and not missing_on_disk:
        _ok("manifest ↔ prompts 目录一致")
        return 0
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "manifest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="校验 manifest 完整性").add_argument("manifest", type=Path)
    r1 = sub.add_parser("reconcile", help="对比 manifest 与 slides/ 目录")
    r1.add_argument("manifest", type=Path)
    r1.add_argument("slides_dir", type=Path)
    r2 = sub.add_parser("reconcile-prompts", help="对比 manifest 与 prompts/ 目录")
    r2.add_argument("manifest", type=Path)
    r2.add_argument("prompts_dir", type=Path)
    args = ap.parse_args()
    if args.cmd == "check":
        return cmd_check(args.manifest)
    if args.cmd == "reconcile":
        return cmd_reconcile(args.manifest, args.slides_dir)
    if args.cmd == "reconcile-prompts":
        return cmd_reconcile_prompts(args.manifest, args.prompts_dir)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
