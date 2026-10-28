# superpowers-codebuddy 设计文档

日期：2026-10-28
状态：待批准
方案：C 双产物（自用适配层 + 面向市场的自包含包）

## 1. 意图与缘由

`obra/superpowers` 是一套给编码 Agent 用的开发方法论技能库（MIT，v7.0.1），上游支持 Claude Code、Codex、Cursor、Gemini CLI 等 15 个 harness，**不支持 CodeBuddy**。

本地已经做过一次可用适配（15 个技能、引导注入 hook、10 项回归测试全绿），现在要把它变成可公开分发的开源项目，同时进入 CodeBuddy 插件市场与 SkillHub。

用户的原话是"就做一个 CodeBuddy 适配版，做成技能发到 GitHub 和 SkillHub"。目标不是重新发明方法论，而是让 CodeBuddy 用户装上之后，行为和 Claude Code 用户一致，并且在上游迭代时不会静默腐烂。

## 2. 目标

- G1 装上即用：一条命令（或一次市场点击）装完，不需要用户手改配置。
- G2 跟上上游：上游发新版后，本仓库的产物能被自动重新生成并提交 PR，而不是人工 rebase。
- G3 可验证：仓库自带回归测试，上游结构变化时**显式失败**，不静默降级。
- G4 双出口：同一份内容可发布为 ① CodeBuddy 插件（`.codebuddy-plugin`）② SkillHub 技能包（`.codebuddy-skill`）。
- G5 诚实归属：技能内容署名 obra/superpowers，本项目只声明适配层贡献。

## 3. 非目标

- N1 不修改技能的方法论语义，不改写正文表达，不做"我们的增强版流程"。
- N2 阶段一不做完整中文化（仅 README、适配文档、注入引导用中文）。
- N3 不做 GUI / 浏览器演示站。
- N4 不代替上游处理 issue；用户遇到技能行为问题应回到上游。
- N5 不追求覆盖 Claude Code 特有的 hooks/agents 能力，缺失部分显式降级。

## 4. 反目标（做到即失败）

- A1 用户装个"技能"结果被改写了全局 `~/.codebuddy/settings.json` 且无提示。
- A2 半年后 `dist/` 停在某个旧版本，用户以为在用最新 superpowers。
- A3 上游改了目录结构，产物生成"成功"但内容已经错位（静默腐烂）。
- A4 与上游行为不一致却未在任何地方声明，导致用户拿本项目的表现去向上游报 bug。

## 5. 约束（已实测确认）

上游与运行时的既有事实，不是猜测：

| # | 事实 | 来源 |
|---|---|---|
| C1 | CodeBuddy 的工具词汇与 Claude 不同：`Skill`→`use_skill`、`TodoWrite`→`todo_write`、`Bash`→`execute_command`、`Edit`→`replace_in_file`、`Grep`→`search_content` | genie 扩展 `TOOL_NAME_CRAFT_TO_CLI` |
| C2 | CodeBuddy **支持** Claude 式 hooks：`settings.json` 的 `hooks.SessionStart`，认 `hookSpecificOutput.additionalContext`，也认插件自带 `hooks/hooks.json`（`${CODEBUDDY_PLUGIN_ROOT}`） | genie `SessionHookManager` / `HookManager` |
| C3 | hook 通过 `shell:true` 执行、stdin 传事件 JSON、默认超时 60s；实测注册后可被动态加载并触发 | 探针实验 |
| C4 | 插件可包含 `skills/`、`commands/`、`agents/`、`hooks/`、`rules/`、`mcpServers/` | 插件加载器 `resolveFeaturePaths` |
| C5 | 市场支持 GitHub 仓库作为市场源（`GithubMarketplace`），根目录放 `.codebuddy-plugin/marketplace.json` 或 `.codebuddy-skill/marketplace.json` | 市场加载器 |
| C6 | 技能市场条目允许"一个条目含多个嵌套子技能"（现有 `cloudbase` 23 个、`marketing-skills` 24 个） | 本地市场缓存 |
| C7 | `task` 工具只暴露只读的 `code-explorer`，没有可写代码的通用 implementer subagent | 当前运行时 |
| C8 | 已有两个同类移植仓库：`karberlee/superpowers-for-workbuddy`、`wyb10a10/superpowers-codebuddy` | 检索 |
| C9 | **CodeBuddy 官方插件市场已收录 `superpowers` v4.0.3**：作者 Jesse Vincent，14 个无前缀技能，自带 `hooks/`、`commands/`、`lib/skills-core.js` | `codebuddy-plugins-official/.codebuddy-plugin/marketplace.json` + `external_plugins/superpowers/` |
| C10 | GitHub 账号 `rohoqin`（Roho Qin），token 具备 `repo` + `workflow` scope | `gh auth status` |

## 6. 方案选择

| 方案 | 内容 | 取舍 |
|---|---|---|
| A 薄适配层 | 仓库只含 `sync.sh`/hook/`verify.py`，安装时 clone 上游再跑脚本 | 永不腐烂；但需联网跑脚本，市场与 SkillHub 通常要自包含包，审核会卡 |
| B 自包含包 | 技能正文全部 vendor 进仓库，`curl \| bash` 一键装 | 零门槛；但半年后停在旧版，差分扩大 |
| **C 双产物（选定）** | 根目录留适配层与生成器，`dist/` 由生成器产出自包含包，CI 每周检查上游并自动 PR | 两边都要维护一点结构；换来"开箱即用 + 不腐烂" |

选 C 的理由：进入市场必须交"别人能下载的包"（B 的形态），长期不坏必须有"跟随上游的机制"（A 的形态）。把 B 变成 A 的**产物**而不是 A 的**替代**，两者就不冲突。

## 7. 目录结构

```
superpowers-codebuddy/
├── .codebuddy-plugin/
│   └── marketplace.json            # 自托管市场清单：/plugin marketplace add <repo>
├── plugins/
│   └── superpowers/
│       ├── .codebuddy-plugin/
│       │   └── plugin.json         # 插件清单（name/version/description）
│       ├── hooks/
│       │   ├── hooks.json          # SessionStart 声明
│       │   └── session-start       # 引导注入脚本（fail-open）
│       ├── skills/                 # 【生成物】15 个 superpowers-* 技能
│       └── README.md
├── adapt/                          # 适配层源码（人工维护，只在改规则时动）
│   ├── generate.py                 # 上游 → plugins/superpowers/skills 的生成器
│   ├── rules/                      # 变换规则（见 §8）
│   ├── assets/codebuddy-tools.md   # 运行时对照文档
│   └── verify.py                   # 回归测试（10 项）
├── dist/                           # 【生成物】发布用压缩包，CI 产出
├── .github/workflows/
│   ├── verify.yml                  # PR/push：跑 verify.py 静态与契约测试
│   ├── sync-upstream.yml           # 每周一 03:00 UTC + 手动：探测上游新 tag，重新生成，开 PR
│   └── release.yml                 # 打 tag：生成 dist/ zip 并挂到 Release
├── docs/superpowers/specs/         # 设计文档
├── README.md / README.zh.md
├── LICENSE                         # MIT（本项目）
└── NOTICE                          # 上游归属与 MIT 声明
```

`plugins/superpowers/skills/` 与 `dist/` 是生成物：**接受它们进版本库**（市场与 GitHub 用户要能直接看、直接下），但由 CI 校验"生成物 == 生成器输出"，避免手改漂移。

## 8. 生成规则（核心，来自实测）

生成器输入：上游 tag 的 `skills/` 目录。输出：`plugins/superpowers/skills/superpowers-*/`。规则按顺序应用：

| R# | 规则 | 为什么必须有 |
|---|---|---|
| R1 | 目录名与 frontmatter `name` 都加 `superpowers-` 前缀 | CodeBuddy 无插件命名空间，技能按目录名全局唯一；加前缀避免与用户已有技能撞名 |
| R2 | `superpowers:<skill>` → `superpowers-<skill>`（全文件，含脚本） | 上游正文 49 处带冒号命名空间，不改则 `use_skill` 找不到 |
| R3 | `((?:\.\./)+)<skill>/` → `\1superpowers-<skill>/`（全文件） | 兄弟目录相对路径。**真实 bug**：`task-start`/`task-done` 里 `../../subagent-driven-development/scripts` 加前缀后 cd 失败 |
| R4 | 追加 `references/codebuddy-tools.md`，并在 `using-superpowers` 的 Platform Adaptation 表登记 CodeBuddy | 不登记则 CodeBuddy 专用说明永远不会被读到 |
| R5 | `writing-skills` 的技能存放路径补 `~/.codebuddy/skills/` | 否则它会指引用户写到 Claude 目录 |
| R6 | `brainstorming` 的 `run_in_background` 改为 `nohup ... &` | CodeBuddy 无该参数 |
| R7 | 保留其它 harness 的 `references/*-tools.md`，不删 | Platform Adaptation 表引用它们，删了会断链 |
| R8 | 生成前校验：上游存在 15 个预期技能目录；缺失/新增则**失败退出**并列出差异。基线锁定上游 tag（首版 `v7.0.1`）；工作区里的 `obra-superpowers/` 是 6.2.0 旧克隆（14 技能），**不可作为源** | 防静默腐烂（A3） |

R8 是防 A3 的关键：上游增删技能属于需要人工决策的变更，生成器不许自作主张。

## 9. 引导注入（bootstrap）

- 插件形态：`plugins/superpowers/hooks/hooks.json` 声明 `SessionStart`，命令走 `${CODEBUDDY_PLUGIN_ROOT}/hooks/session-start`。用户装插件即生效，**不动用户 settings.json**（满足 A1）。
- 技能包形态（SkillHub）：不含 hook。技能靠 `description` 被自动触发，能力略弱但零副作用。README 明说差异，并提供可选的手动注册片段。
- 注入内容：`using-superpowers/SKILL.md` 正文（剥离 frontmatter）+ 一段 CodeBuddy 工具词汇说明，长度约 3.5KB。
- 失败必须放行：任何异常走 `exit 0` + 空输出。

## 10. 命名与版本

- 仓库名 `superpowers-codebuddy`（owner `rohoqin`）；插件名 **`superpowers-codebuddy`**（必须避让官方已有的 `superpowers` 条目）；技能名 `superpowers-<skill>`；SkillHub 条目名 `Superpowers（CodeBuddy 适配版）`（一条目含 15 个嵌套子技能，依据 C6）。
- 版本：`<上游版本>-cb.<n>`，例如 `7.0.1-cb.1`。`adapt/upstream.json` 记录上游 tag 与 commit SHA。
- 发布前必须两个产物版本号一致，由 `verify.py` 断言。

## 10.1 与官方市场 4.0.3 的关系（新增，源自 C9）

官方市场的 `superpowers` 停在 **4.0.3**（上游已 7.0.1），14 个无前缀技能，自带 hook、3 个斜杠命令和 `lib/skills-core.js`。这不是空白市场，本项目是**版本跟进者**，不是开荒者。

处理方式（**待你确认**，我按此建议写入）：

- 插件名用 `superpowers-codebuddy`，与官方条目并存，不动官方包。
- 技能名保留 `superpowers-` 前缀 → 与官方的 `brainstorming` 等**不撞名**，但两套并存会同时被触发，流程互相打架。
- 因此：插件描述、README 安装步骤、以及 `SessionStart` 注入文案里都必须写一句「若已安装官方 `superpowers`，请先禁用，避免两套流程同时生效」。
- 同时提供「只装不使用旧版」的自检：`verify.py` 检查是否存在同名冲突技能（无前缀 `brainstorming` 等 14 个），存在则告警不阻断。
- 不主动向官方提 issue 请求升级（依赖第三方响应），但 README 里给出对比表，说明本项目对应上游版本，方便用户判断。
- 若将来官方升级到 v7，本项目退化为「上游有支持后的轻量中文适配层」，届时再评估是否停止维护。

## 11. 验证策略

种子来源：现有实现已在本机跑通（`~/.codebuddy/superpowers/` 的 `sync.sh`、`verify.py`、`hooks/session-start`，以及 `~/.codebuddy/skills/superpowers-*` 15 个技能），搬进仓库改造即可，**不重写**。

`adapt/verify.py` 现有 10 项（清单/frontmatter、相对引用可达、命名空间残留、hook 契约、hook 失败模式、hook 耗时、settings 注册、脚本语法、计划执行脚本真实链路、可视化伴侣脚本）。

迁移到仓库后调整：
- 与用户机器解耦：所有路径从仓库根推导，不写死 `$HOME`。
- CI 可跑：除"settings.json 注册"改为校验 `hooks.json` 结构外，其余全部可在 CI 跑。
- 增补：生成物一致性（重跑 `generate.py` 后 `git diff` 为空）、版本号一致、`NOTICE` 含上游 MIT 声明、skill 数量 == 15。
- 不可自动化的部分：IDE 真实触发 hook 与技能自动触发，需人工在 README 里写"三步自检"。

## 12. 发布流程

1. `python3 adapt/generate.py --upstream <tag>` → 生成技能
2. `python3 adapt/verify.py` 全绿
3. 更新 `adapt/upstream.json` 与两个清单版本号
4. 打 tag `<version>` → CI 产出 `dist/*.zip` 挂 Release
5. 插件市场：仓库根有 `.codebuddy-plugin/marketplace.json`，用户可 `/plugin marketplace add rohoqin/superpowers-codebuddy`；同时向 CodeBuddy 官方市场提交收录
6. SkillHub：提交 `dist/superpowers-skill-<version>.zip`（含 `.codebuddy-skill/marketplace.json` 与 `skills/` 嵌套结构）

## 13. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 上游重构 `skills/` 布局 | 生成失败或错位 | R8 显式失败 + CI 红灯；不许"尽量生成" |
| 市场审核不收第三方移植 | 无法进官方市场 | 先做自托管市场（C5）保证可用，再谈收录 |
| 与已有两个仓库同质 | 无人使用 | README 明确差异：跟随上游 + 双产物 + 回归测试；不贬低他人 |
| hook 注入内容过长拖慢首轮 | 首轮上下文变胖 | 实测 3.5KB / 59ms；如超预算改为只注入触发规则摘要 |
| 用户误以为可用代码 subagent | SDD 流程失败 | `codebuddy-tools.md` + 注入文案显式降级到 `executing-plans` |
| 用户同时装了官方 4.0.3 与本项目 | 两套技能同时触发，流程打架，用户以为"superpowers 不稳定" | 插件描述 + README + 注入文案三处声明互斥；`verify.py` 检测到无前缀技能时告警 |
| 自托管市场地址写错（owner 变更） | 所有安装命令失效 | owner 集中在 `adapt/upstream.json` 与 README 单一来源，CI 断言一致 |

## 14. 明确留给我（需求方）已定的

- 方案 C 双产物（已定）
- 发布出口：GitHub + SkillHub + CodeBuddy 插件市场（已定）
- 技能正文跟随上游、不自行改写语义（已定）

## 15. 留给 builder 的决定

- `generate.py` 用 Python 还是 Node（倾向 Python：CI 与本地都有，无 npm 依赖）
- 变换规则用硬编码函数还是可组合 rule 列表（倾向后者，便于单测）
- `dist/` 是否进版本库（倾向进，便于市场抓取）
- 插件清单里是否声明 `commands/`（当前上游无命令，暂不声明）
- 是否顺带上架"中文触发词增强版"（阶段二议题，阶段一不做）
- `sync-upstream.yml` 开 PR 的凭据：`GITHUB_TOKEN` 建的 PR 不触发 `verify.yml`，倾向用 fine-grained PAT（`gh` 当前 token 为 `gho_` 前缀的 OAuth token，scopes 已含 `repo`+`workflow`，可先手动验证一次再决定是否落 secret）

## 16. 待确认（阻塞开工）

- §10.1 的与官方 4.0.3 共存策略：确认「另立 `superpowers-codebuddy` + 三处互斥声明」，或改为只发 SkillHub、不碰插件市场。
