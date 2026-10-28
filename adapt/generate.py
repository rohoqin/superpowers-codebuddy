#!/usr/bin/env python3
"""把上游 obra/superpowers 的技能目录生成为 CodeBuddy 可用的 skills/。

    python3 adapt/generate.py                 # 用 adapt/upstream.json 里锁定的 ref
    python3 adapt/generate.py --ref v7.0.2    # 临时试另一个 tag
    python3 adapt/generate.py --upstream DIR  # 用本地已有克隆，不联网

设计约束（见 docs/superpowers/specs/...-design.md §8）：
- 上游增删技能属于需要人决策的变更，这里**直接失败**并打印差异（R8）。
- 生成结果必须可复现：同样的 ref 跑两遍，`git diff` 为空。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_JSON = REPO_ROOT / "adapt" / "upstream.json"
ASSETS = REPO_ROOT / "adapt" / "assets"
OUT_DIR = REPO_ROOT / "skills"
CACHE_DIR = REPO_ROOT / ".cache" / "upstream"


def load_pin() -> dict:
    return json.loads(UPSTREAM_JSON.read_text(encoding="utf-8"))


def fetch_upstream(pin: dict, ref: str) -> Path:
    """浅克隆/更新上游缓存，返回含 skills/ 的目录。"""
    url = pin["repo"]
    if not CACHE_DIR.exists():
        CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, url, str(CACHE_DIR)],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(["git", "-C", str(CACHE_DIR), "fetch", "--depth", "1", "--force", "origin", ref],
                       check=True, capture_output=True)
        subprocess.run(["git", "-C", str(CACHE_DIR), "checkout", "-q", "FETCH_HEAD"],
                       check=True, capture_output=True)
    return CACHE_DIR


def check_skill_set(src: Path, pin: dict, ref: str) -> list[str]:
    """R8：上游技能清单必须与 upstream.json 完全一致，否则失败退出。"""
    found = sorted(p.name for p in (src / "skills").iterdir() if p.is_dir())
    expected = sorted(pin["skills"])
    if found == expected:
        return found

    added = [n for n in found if n not in expected]
    removed = [n for n in expected if n not in found]
    print(f"上游 {ref} 的技能清单与 adapt/upstream.json 不一致：", file=sys.stderr)
    if added:
        print(f"  新增（需确认是否需要适配）: {', '.join(added)}", file=sys.stderr)
    if removed:
        print(f"  消失（需确认是否上游已删除）: {', '.join(removed)}", file=sys.stderr)
    print("核对后同步更新 adapt/upstream.json 的 skills 与 ref，再重跑。", file=sys.stderr)
    raise SystemExit(3)


def generate(src: Path, names: list[str]) -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for old in OUT_DIR.glob(rules.PREFIX + "*"):
        shutil.rmtree(old)

    count = 0
    for name in names:
        target = OUT_DIR / rules.skill_dirname(name)
        shutil.copytree(src / "skills" / name, target)

        # R1：frontmatter name 与目录一致
        skill_md = target / "SKILL.md"
        skill_md.write_text(
            rules.rewrite_template_name(skill_md.read_text(encoding="utf-8"), name),
            encoding="utf-8",
        )

        # R2 + R3：命名空间与兄弟目录路径（md 与脚本都要改）
        for f in target.rglob("*"):
            if f.is_file() and rules.is_text_file(f):
                text = f.read_text(encoding="utf-8")
                new = rules.rewrite_references(text, names)
                if new != text:
                    f.write_text(new, encoding="utf-8")

        # R4 / R5 / R6
        rules.apply_platform_doc(target, ASSETS / "codebuddy-tools.md")
        rules.apply_skills_path(target)
        rules.apply_visual_companion(target)
        count += 1
    return count


def main() -> int:
    pin = load_pin()
    ap = argparse.ArgumentParser(description="生成 CodeBuddy 技能包")
    ap.add_argument("--ref", default=pin["ref"], help=f"上游 tag/分支（默认 {pin['ref']}）")
    ap.add_argument("--upstream", help="已有上游克隆路径（不联网）")
    args = ap.parse_args()

    if args.upstream:
        src = Path(args.upstream).expanduser().resolve()
        if not (src / "skills").is_dir():
            print(f"{src} 下没有 skills/，不是有效的上游克隆", file=sys.stderr)
            return 1
    else:
        src = fetch_upstream(pin, args.ref)

    names = check_skill_set(src, pin, args.ref)
    count = generate(src, names)

    commit = subprocess.run(["git", "-C", str(src), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    print(f"已生成 {count} 个技能 -> {OUT_DIR.relative_to(REPO_ROOT)}")
    print(f"上游 {args.ref} @ {commit or pin['commit']}")
    if args.ref != pin["ref"]:
        print(f"注意：本次 ref 与 adapt/upstream.json 的 {pin['ref']} 不同，提交前请同步更新", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
