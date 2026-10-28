# CodeBuddy Tool Notes

CodeBuddy (腾讯云代码助手) 不是 Claude Code，但它复用同一套 hook 协议与工具词汇。
这些技能原文用 Claude 词汇书写（`Skill`、`TodoWrite`、`Bash`…），下表是等价的
CodeBuddy 工具。**能用 CodeBuddy 工具就用 CodeBuddy 工具**，不要臆造工具名。

## 工具对照

| 技能原文里的说法 | CodeBuddy 工具 | 说明 |
|---|---|---|
| `Skill` 工具 / `superpowers:foo` | `use_skill` + `superpowers-foo` | 技能名带 `superpowers-` 前缀，没有 `:` 命名空间 |
| `TodoWrite` | `todo_write` | 清单式任务跟踪；技能的每个 checklist 项建一个 todo |
| `Task` / `Agent`（派发子 Agent） | `task` | `subagent_name` 见下方限制 |
| `Read` | `read_file` | |
| `Write` | `write_to_file` | |
| `Edit` | `replace_in_file` | |
| `Bash` | `execute_command` | `requires_approval:false` 用于安全只读命令 |
| `Glob` | `list_dir` / `search_file` | |
| `Grep` | `search_content` | |
| `WebFetch` / `WebSearch` | `web_fetch` / `web_search` | 需要时先 `ToolSearch` 取 schema |

## 技能位置

- 用户级：`~/.codebuddy/skills/<name>/SKILL.md`
- 项目级：`<repo>/.codebuddy/skills/<name>/SKILL.md`（同名覆盖用户级）
- 附带文件放同目录：`references/`、`scripts/`、`assets/`

## 子 Agent 限制（影响 subagent-driven-development）

CodeBuddy 的 `task` 工具只暴露受限的专用 subagent（当前为 `code-explorer`，
只读检索用），**没有可写代码的通用 implementer subagent**。因此：

- 需要只读探查 / 并行搜代码 → `task` + `code-explorer`，这是 `dispatching-parallel-agents` 的落地方式。
- 需要真正写代码的逐任务派发 → CodeBuddy 上**改用 `superpowers-executing-plans`**（当前会话内联执行 + 收尾一次整体评审）。
- 不要伪造派发，也不要把 `code-explorer` 当成能跑测试的 implementer。

## 执行环境

- 命令通过 shell 执行，`execute_command` 无 `run_in_background` 参数。
  需要常驻进程（如 brainstorming 的可视化伴侣服务）时，用
  `nohup ... > /tmp/x.log 2>&1 &` 自行转入后台，再用 `$STATE_DIR/server-info` 读端口。
- macOS / zsh：`grep --include='*.md'` 的 glob 要加引号，否则 zsh 会当成自身 glob 报 `no matches found`。

## 引导（bootstrap）机制

Claude Code 靠 `SessionStart` hook 把 `using-superpowers` 全文注入会话。
CodeBuddy IDE 支持同名 hook（`settings.json` 的 `hooks.SessionStart`，
输出 `hookSpecificOutput.additionalContext`），本技能包已注册该 hook；
即使 hook 未生效，CodeBuddy 也会把每个技能的 `description` 注入系统提示，
所以技能仍能被自动触发。

## 规则文件

CodeBuddy 的用户/项目约定文件是 `CODEBUDDY.md` 与 `.codebuddy/rules/*.md`
（等价于原文提到的 `CLAUDE.md` / `AGENTS.md`）。用户指令优先级高于技能。
