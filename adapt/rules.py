"""上游 superpowers 正文 → CodeBuddy 技能 的变换规则。

每条规则对应设计文档 §8 的一行（R1–R7）。规则是纯函数：拿文件路径/文本，
返回"要不要改、改成什么"，不自己读环境。generate.py 负责 I/O 与顺序。
"""
from __future__ import annotations

import pathlib
import re

PREFIX = "superpowers-"

TEXT_SUFFIXES = {".md", ".js", ".cjs", ".mjs", ".ts", ".sh", ".json", ".dot", ".html", ".yaml", ".yml"}


def skill_dirname(upstream_name: str) -> str:
    """R1 目录名加前缀，保证技能名在 CodeBuddy 里全局唯一。"""
    return PREFIX + upstream_name


def frontmatter_name(upstream_name: str) -> str:
    """R1 frontmatter 的 name 必须与目录名一致，否则运行时按名加载会失败。"""
    return PREFIX + upstream_name


def rewrite_template_name(text: str, upstream_name: str) -> str:
    """把 frontmatter 里的 `name: <upstream>` 改成带前缀的形式（只动前 20 行）。"""
    return re.sub(
        rf"^name:\s*{re.escape(upstream_name)}\s*$",
        f"name: {frontmatter_name(upstream_name)}",
        text,
        count=1,
        flags=re.M,
    )


def rewrite_references(text: str, all_names: list[str]) -> str:
    """R2 + R3：命名空间与跨技能相对路径。

    上游正文用 `superpowers:foo` 指代兄弟技能，脚本里还有
    `$(dirname "$0")/../../foo/scripts` 这种硬编码兄弟目录路径。
    加前缀后两者都必须改写，否则 `use_skill` 找不到技能、
    task-start/task-done 会 cd 到不存在的目录。
    """
    for name in all_names:
        text = text.replace(f"superpowers:{name}", PREFIX + name)
        text = re.sub(
            r"((?:\.\./)+)" + re.escape(name) + r"/",
            r"\1" + PREFIX + name + "/",
            text,
        )
    return text


def is_text_file(path: pathlib.Path) -> bool:
    if path.suffix in TEXT_SUFFIXES:
        return True
    # 无扩展名但带 shebang 的脚本
    try:
        return path.read_text(encoding="utf-8").startswith("#!")
    except (UnicodeDecodeError, OSError):
        return False


def apply_platform_doc(skill_dir: pathlib.Path, doc: pathlib.Path) -> None:
    """R4：装运行时对照文档，并登记进 using-superpowers 的平台表格。

    不登记的话，CodeBuddy 专用说明永远不会被读到。
    """
    if skill_dir.name != skill_dirname("using-superpowers"):
        return
    refs = skill_dir / "references"
    refs.mkdir(exist_ok=True)
    target = refs / "codebuddy-tools.md"
    target.write_text(doc.read_text(encoding="utf-8"), encoding="utf-8")

    skill_md = skill_dir / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    if "references/codebuddy-tools.md" in text:
        return
    line = "- CodeBuddy: `references/codebuddy-tools.md`"
    # 插在平台列表末尾（Muse 之后），保持上游原有顺序
    if "- Muse: `references/muse-tools.md`" in text:
        text = text.replace(
            "- Muse: `references/muse-tools.md`",
            "- Muse: `references/muse-tools.md`\n" + line,
            1,
        )
    elif "## Platform Adaptation" in text:
        text = text.replace("## Platform Adaptation", "## Platform Adaptation\n\n" + line, 1)
    else:
        raise SystemExit("using-superpowers/SKILL.md 里找不到 Platform Adaptation 段，上游结构变了")
    skill_md.write_text(text, encoding="utf-8")


def apply_skills_path(skill_dir: pathlib.Path) -> None:
    """R5：writing-skills 会告诉用户技能放哪；不补 CodeBuddy 路径就会写去 Claude 目录。"""
    if skill_dir.name != skill_dirname("writing-skills"):
        return
    path = skill_dir / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    if "codebuddy/skills" in text:
        return
    if "(`~/.claude/skills/` on Claude Code)" not in text:
        raise SystemExit("writing-skills/SKILL.md 里找不到技能路径说明，上游结构变了")
    text = text.replace(
        "(`~/.claude/skills/` on Claude Code)",
        "(`~/.codebuddy/skills/` on CodeBuddy, `~/.claude/skills/` on Claude Code)",
        1,
    )
    path.write_text(text, encoding="utf-8")


def apply_visual_companion(skill_dir: pathlib.Path) -> None:
    """R6：CodeBuddy 的 execute_command 没有 run_in_background 参数。"""
    if skill_dir.name != skill_dirname("brainstorming"):
        return
    path = skill_dir / "visual-companion.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if "CODEBUDDY-BG" in text:
        return
    old = (
        "Use `run_in_background: true` on the Bash tool call so the server "
        "survives across conversation turns"
    )
    if old not in text:
        # 上游改写了这句话：不静默跳过，让人看见
        print("  ! visual-companion.md 里没有预期的 run_in_background 说明，跳过 R6（需人工核对）")
        return
    new = (
        "On CodeBuddy there is no `run_in_background` option: launch it detached "
        "(`nohup <cmd> >/tmp/sp-visual.log 2>&1 &`) so the server survives across "
        "conversation turns <!-- CODEBUDDY-BG -->"
    )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
