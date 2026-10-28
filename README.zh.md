# Superpowers for CodeBuddy

把 [obra/superpowers](https://github.com/obra/superpowers)（**v7.0.1**，MIT）适配到 CodeBuddy 的技能包：15 个技能，装上就能用。

> 技能内容来自上游，本项目只做适配层。上游里程碑、方法论、设计理念请回上游看；这里只负责"在 CodeBuddy 上跑得通、跑得对"。

## 为什么会有这个

上游支持 Claude Code、Codex、Cursor、Gemini CLI 等 15 个 harness，**没有 CodeBuddy**。直接拷 `skills/` 过去会坏在三处：

1. 技能名靠目录名，全球唯一 → 不加前缀会和别人的技能撞名
2. 正文里 49 处 `superpowers:foo` 命名空间 → CodeBuddy 没有命名空间，`use_skill` 直接找不到
3. 脚本里硬编码兄弟目录 `../../subagent-driven-development/scripts` → 改名后 `cd` 到不存在的路径，计划执行直接失效

这些都在生成器里逐条处理，并且有回归测试盯着。

## 和插件市场里那个 superpowers 的关系

| | 插件市场 `superpowers` | 本项目 |
|---|---|---|
| 对应上游版本 | 4.0.3 | **7.0.1** |
| 形态 | 插件（含命令、hook、lib） | 技能包（纯技能） |
| 技能名 | 无前缀 `brainstorming` | `superpowers-brainstorming` |
| 更新方式 | 随市场 | 生成器跟随上游 tag，CI 每周探测 |

**两者会同时生效**（技能名不同，都会被触发）。如果你已经装了插件市场那个，建议先禁用它再装本项目，否则两套流程会打架。

## 安装

```bash
git clone https://github.com/rohoqin/superpowers-codebuddy.git
cd superpowers-codebuddy
./install.sh
```

装到 `~/.codebuddy/skills/`。想装到当前项目：`./install.sh --project`。

### 关于引导注入（可选）

Claude Code 上，上游靠 `SessionStart` hook 在每次会话开头把 `using-superpowers` 全文塞进上下文，技能因此"强制生效"。

CodeBuddy 的**技能 frontmatter 不支持 hooks**（只认 name/description/allowed-tools/model），所以这件事只能写进 `settings.json`：

```bash
./install.sh --with-hook
```

它会备份你的 `settings.json`，然后只追加一条 `hooks.SessionStart`，命令指向本项目的 `hooks/session-start`。
不加 `--with-hook` 也能用——技能靠 `description` 自动触发，只是少了"每次开头强制前置"的强度。

## 自检

```bash
python3 adapt/verify.py        # 16 项，必须全绿
```

再开个新会话，问它「你现在有 superpowers 吗」——它能说出并调用 `superpowers-*` 技能就对了。
验证注入是否生效：让它复述看到的 superpowers 规则，能复述 `EXTREMELY_IMPORTANT` 那段即为注入成功。

## 卸载

```bash
./install.sh --uninstall              # 只删本工具清单里记录的技能目录
./install.sh --uninstall              # 同时会自动移除自己注册的 hook
```

不会碰别人装的技能。删之前会按清单核对，清单不在就拒绝执行。

## 包含哪些技能

`brainstorming`、`diagnosing-superpowers`、`dispatching-parallel-agents`、`executing-plans`、
`finishing-a-development-branch`、`receiving-code-review`、`requesting-code-review`、
`subagent-driven-development`、`systematic-debugging`、`test-driven-development`、
`using-git-worktrees`、`using-superpowers`、`verification-before-completion`、
`writing-plans`、`writing-skills`

## 已知限制

- **没有可写代码的子 Agent。** CodeBuddy 的 `task` 只暴露只读的 `code-explorer`，所以 `subagent-driven-development` 的"逐任务派发"在 CodeBuddy 上改用 `executing-plans` 内联执行。适配文档里写清了。
- **可视化伴侣**需要常驻进程，CodeBuddy 的 `execute_command` 没有 `run_in_background`，改用 `nohup ... &`。
- **不默认改你的全局配置。** 只有显式 `--with-hook` 才会写 `settings.json`，且改前备份。

## 维护

```bash
python3 adapt/generate.py                  # 按 adapt/upstream.json 锁定的 tag 重新生成
python3 adapt/generate.py --ref v7.0.2     # 试新版本
```

上游增删技能时生成器会**直接失败**并列出差异，不会默默生成一个错位的包。核对后同步更新 `adapt/upstream.json` 再跑。

## 授权

本项目（适配层）MIT。技能内容版权归 [Jesse Vincent / Prime Radiant](https://github.com/obra/superpowers) 所有，同为 MIT，详见 [NOTICE](NOTICE)。
