#!/usr/bin/env python3
"""仓库级回归测试。CI 与本地都跑这个，退出码 0 才算通过。

    python3 adapt/verify.py

覆盖：生成物与上游清单一致、frontmatter、相对引用、命名空间残留、
平台文档登记、hook 契约与失败模式、install.sh 安装/卸载/冲突拦截、
计划执行脚本真实链路、法务声明。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
HOOK = ROOT / "hooks" / "session-start"
INSTALL = ROOT / "install.sh"
HOOK_REG = ROOT / "adapt" / "hook_register.py"
PIN = json.loads((ROOT / "adapt" / "upstream.json").read_text(encoding="utf-8"))
PREFIX = "superpowers-"

results: list[tuple[bool, str, str]] = []


def check(name, fn):
    try:
        detail = fn()
        results.append((True, name, detail or ""))
    except AssertionError as e:
        results.append((False, name, str(e)))
    except Exception as e:  # noqa: BLE001
        results.append((False, name, f"{type(e).__name__}: {e}"))


def dirs() -> list[Path]:
    return sorted(p for p in SKILLS.glob(PREFIX + "*") if p.is_dir())


def t_skill_set():
    got = sorted(p.name[len(PREFIX):] for p in dirs())
    want = sorted(PIN["skills"])
    assert got == want, f"与 adapt/upstream.json 不一致\n  多: {set(got) - set(want)}\n  少: {set(want) - set(got)}"
    return f"{len(got)} 个技能，与 upstream.json 一致"


def t_frontmatter():
    for d in dirs():
        md = d / "SKILL.md"
        assert md.is_file(), f"{d.name} 缺 SKILL.md"
        text = md.read_text(encoding="utf-8")
        assert text.startswith("---"), f"{d.name} 缺 frontmatter"
        fm = text.split("---", 2)[1]
        m = re.search(r"^name:\s*(.+)$", fm, re.M)
        assert m, f"{d.name} 缺 name"
        assert m.group(1).strip().strip('"') == d.name, f"{d.name} 的 name 与目录不一致"
        m = re.search(r"^description:\s*(.+)$", fm, re.M)
        assert m and len(m.group(1).strip()) > 20, f"{d.name} description 过短"
    return "15/15 目录名与 name 一致"


def t_links():
    skip = {"anthropic-best-practices.md"}  # 上游教学材料里的示例链接，非真实引用
    bad = []
    for d in dirs():
        for f in d.rglob("*.md"):
            if f.name in skip:
                continue
            text = re.sub(r"```.*?```", "", f.read_text(encoding="utf-8"), flags=re.S)
            for m in re.finditer(r"\]\(([^)#]+)(?:#[^)]*)?\)", text):
                tgt = m.group(1).strip()
                if tgt.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (f.parent / tgt).exists():
                    bad.append(f"{f.relative_to(SKILLS)} -> {tgt}")
    assert not bad, "断链:\n  " + "\n  ".join(bad[:10])
    return "全部相对引用可达"


def t_namespace():
    bad = []
    for d in dirs():
        for f in d.rglob("*.md"):
            if f.name == "codebuddy-tools.md":
                continue
            for line in f.read_text(encoding="utf-8").splitlines():
                if re.search(r"superpowers:[a-z]", line):
                    bad.append(f"{f.relative_to(SKILLS)}: {line[:70]}")
    assert not bad, "仍残留冒号命名空间（会导致 use_skill 找不到技能）:\n  " + "\n  ".join(bad[:5])
    us = SKILLS / (PREFIX + "using-superpowers")
    assert "references/codebuddy-tools.md" in (us / "SKILL.md").read_text(encoding="utf-8"), \
        "using-superpowers 未登记 CodeBuddy 平台文档"
    assert (us / "references" / "codebuddy-tools.md").is_file(), "codebuddy-tools.md 未安装"
    return "无命名空间残留，平台文档已登记"


def run_hook(env=None, stdin=b'{"hook_event_name":"SessionStart","source":"startup"}'):
    e = dict(os.environ)
    if env:
        e.update(env)
    t0 = time.time()
    p = subprocess.run([str(HOOK)], input=stdin, capture_output=True, env=e, timeout=30)
    return p, time.time() - t0


def t_hook_contract():
    p, _ = run_hook()
    assert p.returncode == 0, f"hook 退出码 {p.returncode}: {p.stderr[:200]!r}"
    payload = json.loads(p.stdout.decode())
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart", "hookEventName 不对"
    ctx = hso["additionalContext"]
    assert len(ctx) > 1500, f"additionalContext 过短（{len(ctx)} 字符）"
    for needle in ("EXTREMELY_IMPORTANT", "use_skill", "todo_write", PREFIX + "using-superpowers"):
        assert needle in ctx, f"注入内容缺少 {needle}"
    assert "name: superpowers-using-superpowers" not in ctx, "frontmatter 没剥离干净"
    return f"合法 JSON，注入 {len(ctx)} 字符"


def t_hook_failopen():
    p, _ = run_hook(env={"SUPERPOWERS_SKILL_DIR": "/nonexistent"})
    assert p.returncode == 0 and p.stdout.strip() == b"", "技能缺失时应静默放行"
    p2, _ = run_hook(stdin=b"")
    assert p2.returncode == 0, "空 stdin 时不应报错"
    return "缺技能/空输入均静默放行"


def t_hook_speed():
    _, dt = run_hook()
    assert dt < 2.0, f"{dt:.2f}s 超过 2s 预算"
    return f"{dt * 1000:.0f}ms"


def sandbox() -> tuple[tempfile.TemporaryDirectory, Path, dict]:
    tmp = tempfile.TemporaryDirectory(prefix="spcb-")
    base = Path(tmp.name) / ".codebuddy"
    env = {**os.environ, "CODEBUDDY_DIR": str(base)}
    return tmp, base, env


def t_install():
    tmp, base, env = sandbox()
    try:
        r = subprocess.run(["bash", str(INSTALL)], capture_output=True, text=True, env=env)
        assert r.returncode == 0, f"安装失败: {r.stderr[-400:]}"
        installed = sorted(p.name for p in (base / "skills").glob(PREFIX + "*"))
        assert len(installed) == len(PIN["skills"]), f"装了 {len(installed)} 个"
        manifest = base / "superpowers" / "installed.txt"
        assert manifest.is_file() and len(manifest.read_text().split()) == len(PIN["skills"]), "清单不对"
        assert not (base / "settings.json").exists(), "未加 --with-hook 却动了 settings.json"
        return f"沙箱安装 {len(installed)} 个技能，未触碰 settings.json"
    finally:
        tmp.cleanup()


def t_install_conflict():
    tmp, base, env = sandbox()
    try:
        (base / "skills" / "brainstorming").mkdir(parents=True)
        r = subprocess.run(["bash", str(INSTALL)], capture_output=True, env=env)
        err = r.stderr.decode("utf-8", "replace")
        assert r.returncode == 4, f"应被拦下（退出码 4），实际 {r.returncode}"
        assert "4.0.3" in err or "无前缀" in err, f"没给出可理解的冲突原因: {err[:200]}"
        r2 = subprocess.run(["bash", str(INSTALL), "--force"], capture_output=True, text=True, env=env)
        assert r2.returncode == 0, f"--force 后应能继续: {str(r2.stderr)[:200]}"
        assert (base / "skills" / "brainstorming").is_dir(), "不该删掉别人的目录"
        return "无前缀冲突被拦截，--force 可继续且不动他人目录"
    finally:
        tmp.cleanup()


def t_install_hook_and_uninstall():
    tmp, base, env = sandbox()
    try:
        base.mkdir(parents=True, exist_ok=True)
        settings = base / "settings.json"
        # 预先放一份"用户已有配置"，验证不会被搞丢、且改前有备份
        settings.write_text('{\n  "enabledPlugins": {"pptx@x": true}\n}\n', encoding="utf-8")

        r = subprocess.run(["bash", str(INSTALL), "--with-hook"], capture_output=True, text=True, env=env)
        assert r.returncode == 0, f"--with-hook 失败: {r.stderr[-300:]}"
        cfg = json.loads(settings.read_text(encoding="utf-8"))
        assert cfg.get("enabledPlugins") == {"pptx@x": True}, "原有配置被覆盖了"
        entries = cfg["hooks"]["SessionStart"]
        cmds = [h["command"] for e in entries for h in e["hooks"]]
        assert any("session-start" in c for c in cmds), f"没注册上: {cmds}"
        for e in entries:
            assert isinstance(e.get("hooks"), list)
            for h in e["hooks"]:
                assert h.get("type") == "command" and isinstance(h.get("command"), str)
        assert list(settings.parent.glob("settings.json.bak-*")), "改配置前没备份"

        st = subprocess.run([sys.executable, str(HOOK_REG), "status", "--settings", str(settings)],
                            capture_output=True, text=True)
        assert st.returncode == 0, "status 应报已注册"

        u = subprocess.run(["bash", str(INSTALL), "--uninstall"], capture_output=True, text=True, env=env)
        assert u.returncode == 0, f"卸载失败: {u.stderr[-300:]}"
        assert not (base / "skills" / (PREFIX + "brainstorming")).exists(), "技能目录没删干净"
        assert not (base / "superpowers" / "installed.txt").exists(), "清单没删"
        st2 = subprocess.run([sys.executable, str(HOOK_REG), "status", "--settings", str(settings)],
                             capture_output=True, text=True)
        assert st2.returncode == 1, "卸载后 hook 仍处于注册状态"
        return "装/注册/卸载全链路通过，hook 注册可完全移除"
    finally:
        tmp.cleanup()


def t_plan_scripts():
    sdd = SKILLS / (PREFIX + "executing-plans") / "scripts"
    if not shutil.which("git"):
        return "未安装 git，跳过"
    tmp = Path(tempfile.mkdtemp(prefix="spcb-plan-"))
    try:
        run = lambda *a: subprocess.run(a, cwd=tmp, capture_output=True, text=True)
        run("git", "init", "-q")
        run("git", "config", "user.email", "v@v.v")
        run("git", "config", "user.name", "v")
        (tmp / "plan.md").write_text("# Plan\n\n## Task 1: a\n\n- [ ] x\n\n## Task 2: b\n\n- [ ] y\n",
                                     encoding="utf-8")
        run("git", "add", "-A")
        run("git", "commit", "-qm", "init")

        started = run("bash", str(sdd / "task-start"), "plan.md", "1")
        assert started.returncode == 0, f"task-start 失败: {started.stderr.strip()[:200]}"
        base = re.search(r"^base:\s*(\S+)", started.stdout, re.M)
        assert base and "brief:" in started.stdout, "task-start 输出缺 brief/base"

        ok = run("bash", str(sdd / "task-done"), "plan.md", "1", base.group(1), "--", "true")
        assert ok.returncode == 0, f"task-done 失败: {ok.stderr.strip()[:200]}"
        ledger = next(tmp.glob(".superpowers/sdd/*/progress.md"), None)
        assert ledger and "Task 1: complete" in ledger.read_text(encoding="utf-8"), "账本没记账"

        bad = run("bash", str(sdd / "task-done"), "plan.md", "2", base.group(1), "--", "false")
        assert bad.returncode != 0 and "Task 2" not in ledger.read_text(encoding="utf-8"), \
            "失败用例被错误记账"
        return "跨技能脚本链路正常（兄弟目录路径改写有效）"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def t_scripts_syntax():
    checked = 0
    targets = [p for p in ROOT.rglob("*") if p.is_file()
               and ".cache" not in p.parts and ".git" not in p.parts and "skills" not in p.parts]
    targets += [p for p in SKILLS.rglob("*") if p.is_file() and p.suffix in ("", ".sh")]
    for p in targets:
        if p.suffix not in ("", ".sh") or p.name in ("SKILL.md",):
            continue
        try:
            head = p.read_text(encoding="utf-8", errors="ignore")[:2]
        except OSError:
            continue
        if p.suffix != ".sh" and head != "#!":
            continue
        r = subprocess.run(["bash", "-n", str(p)], capture_output=True)
        assert r.returncode == 0, f"{p.name} 语法错误: {r.stderr.decode()[:120]}"
        checked += 1
    return f"bash -n 通过 {checked} 个脚本"


def t_python_syntax():
    files = [p for p in ROOT.rglob("*.py") if ".cache" not in p.parts and ".git" not in p.parts]
    for p in files:
        r = subprocess.run([sys.executable, "-m", "py_compile", str(p)], capture_output=True)
        assert r.returncode == 0, f"{p.name} 编译失败: {r.stderr.decode()[:200]}"
    for p in ROOT.rglob("__pycache__"):
        shutil.rmtree(p, ignore_errors=True)
    return f"{len(files)} 个 Python 文件编译通过"


def t_reproducible():
    cache = ROOT / ".cache" / "upstream"
    if not cache.exists():
        return "无上游缓存，跳过（CI 里由 sync workflow 覆盖）"
    before = hashlib.sha256()
    for f in sorted(SKILLS.rglob("*")):
        if f.is_file():
            before.update(f.read_bytes())
    r = subprocess.run([sys.executable, str(ROOT / "adapt" / "generate.py"),
                        "--upstream", str(cache)], capture_output=True, text=True)
    assert r.returncode == 0, f"重新生成失败: {r.stderr[-300:]}"
    after = hashlib.sha256()
    for f in sorted(SKILLS.rglob("*")):
        if f.is_file():
            after.update(f.read_bytes())
    assert before.hexdigest() == after.hexdigest(), "重跑生成器后内容变化，说明生成不可复现或有人手改了产物"
    return "重跑生成器后 products 完全一致"


def t_package_version():
    ver = f"{PIN['ref'].lstrip('v')}-cb.{PIN['adaptation']}"
    r = subprocess.run([sys.executable, str(ROOT / "adapt" / "package.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"打包产物缺失或与版本不一致: {r.stderr.strip()[:200]}"
    zips = list((ROOT / "dist").glob("*.zip"))
    assert [z.name for z in zips] == [f"superpowers-skill-{ver}.zip"], \
        f"dist 里的产物名与版本 {ver} 不一致: {[z.name for z in zips]}"
    return f"dist 产物与版本 {ver} 一致"


def t_legal():
    lic = ROOT / "LICENSE"
    notice = ROOT / "NOTICE"
    assert lic.is_file() and "MIT" in lic.read_text(encoding="utf-8"), "缺 MIT LICENSE"
    assert notice.is_file(), "缺 NOTICE"
    text = notice.read_text(encoding="utf-8")
    for needle in ("superpowers", "Jesse Vincent", "MIT"):
        assert needle in text, f"NOTICE 缺少 {needle}"
    return "LICENSE / NOTICE 归属声明齐全"


def t_readme_version():
    readme = ROOT / "README.zh.md"
    assert readme.is_file(), "缺 README.zh.md"
    text = readme.read_text(encoding="utf-8")
    assert PIN["ref"] in text, f"README 未标注上游版本 {PIN['ref']}"
    return f"README 标注上游 {PIN['ref']}"


for name, fn in [
    ("技能清单与 upstream.json 一致", t_skill_set),
    ("frontmatter 与目录名", t_frontmatter),
    ("相对引用可达", t_links),
    ("命名空间与平台文档", t_namespace),
    ("hook 注入契约", t_hook_contract),
    ("hook 失败放行", t_hook_failopen),
    ("hook 耗时", t_hook_speed),
    ("install.sh 沙箱安装", t_install),
    ("与旧版冲突拦截", t_install_conflict),
    ("hook 注册与卸载", t_install_hook_and_uninstall),
    ("跨技能脚本链路", t_plan_scripts),
    ("shell 语法", t_scripts_syntax),
    ("python 语法", t_python_syntax),
    ("生成可复现", t_reproducible),
    ("打包产物版本", t_package_version),
    ("法务声明", t_legal),
    ("README 版本标注", t_readme_version),
]:
    check(name, fn)

print("\n=== superpowers-codebuddy 回归测试 ===")
w = max(len(n) for _, n, _ in results)
ok = sum(1 for good, _, _ in results if good)
for good, name, detail in results:
    print(f"[{'PASS' if good else 'FAIL'}] {name.ljust(w)}  {detail}")
print(f"\n{ok}/{len(results)} 通过")
sys.exit(0 if ok == len(results) else 1)
