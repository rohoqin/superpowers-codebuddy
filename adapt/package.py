#!/usr/bin/env python3
"""打包 SkillHub 提交用的 zip。

    python3 adapt/package.py            # 产出 dist/superpowers-skill-<ver>.zip
    python3 adapt/package.py --check    # 只校验已有产物

zip 布局（提交前请按官方 SkillHub 指引再核一遍，见设计文档 §12）：

    skills/superpowers-*/...            15 个技能（与仓库内一致）
    .codebuddy-skill/marketplace.json   市场清单（条目 = 一个技能）
    README.md

版本号 = <上游版本>-cb.<适配版本>，来自 adapt/upstream.json。
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIN = json.loads((ROOT / "adapt" / "upstream.json").read_text(encoding="utf-8"))
DIST = ROOT / "dist"


def version() -> str:
    return f"{PIN['ref'].lstrip('v')}-cb.{PIN['adaptation']}"


def entry(name: str) -> dict:
    md = ROOT / "skills" / name / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    fm = text.split("---", 2)[1]
    desc = next(l.split(":", 1)[1].strip().strip('"') for l in fm.splitlines() if l.startswith("description:"))
    return {
        "name": name,
        "version": version(),
        "description": desc[:400],
        "source": f"skills/{name}",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只检查已有产物是否与版本一致")
    args = ap.parse_args()

    ver = version()
    target = DIST / f"superpowers-skill-{ver}.zip"

    if args.check:
        if not target.is_file():
            print(f"缺少产物：{target.relative_to(ROOT)}", file=sys.stderr)
            return 1
        print(f"产物存在：{target.relative_to(ROOT)}")
        return 0

    names = sorted(p.name for p in (ROOT / "skills").glob("superpowers-*") if p.is_dir())
    if not names:
        print("skills/ 为空，先跑 adapt/generate.py", file=sys.stderr)
        return 1

    manifest = {
        "name": "superpowers-codebuddy",
        "description": "Superpowers（obra/superpowers）的 CodeBuddy 适配技能包",
        "owner": {"name": "Roho Qin"},
        "tags_zh": ["开发工具", "效率工具"],
        "tags_en": ["Development Tools", "Productivity Tools"],
        "skills": [entry(n) for n in names],
    }

    DIST.mkdir(exist_ok=True)
    for old in DIST.glob("*.zip"):
        old.unlink()

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            for f in sorted((ROOT / "skills" / n).rglob("*")):
                if f.is_file():
                    z.write(f, f"skills/{n}/{f.relative_to(ROOT / 'skills' / n)}")
        z.writestr(".codebuddy-skill/marketplace.json",
                   json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        readme = ROOT / "README.zh.md"
        if readme.is_file():
            z.write(readme, "README.md")

    print(f"已产出 {target.relative_to(ROOT)}（{len(names)} 个技能，版本 {ver}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
