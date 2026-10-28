#!/usr/bin/env python3
"""登记/移除 CodeBuddy 的 SessionStart 引导注入 hook。

CodeBuddy 的技能 frontmatter 不支持 hooks，所以"每次会话开头强制注入"只能写进
settings.json。本工具只碰 `hooks.SessionStart` 里带本项目指纹的那一条，改前备份。

    python3 adapt/hook_register.py add    --script PATH [--settings PATH]
    python3 adapt/hook_register.py remove [--settings PATH]
    python3 adapt/hook_register.py status [--settings PATH]

退出码：add/remove 成功 0；status 已注册 0、未注册 1。
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

FINGERPRINT = "superpowers"  # 命令里出现这个就当成本项目注册的 hook


def default_settings() -> Path:
    return Path.home() / ".codebuddy" / "settings.json"


def load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path} 不是合法 JSON，不敢改：{e}")


def save(path: Path, cfg: dict) -> Path | None:
    backup = None
    if path.is_file():
        backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return backup


def session_start_entries(cfg: dict) -> list:
    return cfg.get("hooks", {}).get("SessionStart", [])


def is_ours(entry: dict) -> bool:
    return FINGERPRINT in json.dumps(entry, ensure_ascii=False)


def cmd_add(script: Path, settings: Path) -> int:
    if not script.is_file():
        raise SystemExit(f"hook 脚本不存在：{script}")
    cfg = load(settings)
    hooks = cfg.setdefault("hooks", {})
    entries = [e for e in hooks.get("SessionStart", []) if not is_ours(e)]
    entries.append({
        "hooks": [{
            "type": "command",
            "command": f'"{script}"',
            "timeout": 15,
        }]
    })
    hooks["SessionStart"] = entries
    backup = save(settings, cfg)
    print(f"已注册 SessionStart hook：{settings}")
    print(f"  命令：\"{script}\"")
    if backup:
        print(f"  原文件备份：{backup}")
    print("  生效时机：**新开会话**（当前会话不会重新注入）")
    return 0


def cmd_remove(settings: Path) -> int:
    cfg = load(settings)
    hooks = cfg.get("hooks", {})
    entries = hooks.get("SessionStart", [])
    kept = [e for e in entries if not is_ours(e)]
    if len(kept) == len(entries):
        print("没有找到本项目注册的 hook，未做改动")
        return 0
    if kept:
        hooks["SessionStart"] = kept
    else:
        hooks.pop("SessionStart", None)
    if not hooks:
        cfg.pop("hooks", None)
    backup = save(settings, cfg)
    print(f"已移除 SessionStart hook（删掉 {len(entries) - len(kept)} 条）")
    if backup:
        print(f"  原文件备份：{backup}")
    return 0


def cmd_status(settings: Path) -> int:
    cfg = load(settings)
    ours = [e for e in session_start_entries(cfg) if is_ours(e)]
    if not ours:
        print(f"未注册（{settings}）")
        return 1
    for e in ours:
        for h in e.get("hooks", []):
            print(f"已注册：{h.get('command')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["add", "remove", "status"])
    ap.add_argument("--script", help="hook 脚本绝对路径（add 必填）")
    ap.add_argument("--settings", help="settings.json 路径，默认 ~/.codebuddy/settings.json")
    args = ap.parse_args()

    settings = Path(args.settings).expanduser() if args.settings else default_settings()
    if args.action == "add":
        if not args.script:
            raise SystemExit("add 需要 --script")
        return cmd_add(Path(args.script).expanduser().resolve(), settings)
    if args.action == "remove":
        return cmd_remove(settings)
    return cmd_status(settings)


if __name__ == "__main__":
    raise SystemExit(main())
