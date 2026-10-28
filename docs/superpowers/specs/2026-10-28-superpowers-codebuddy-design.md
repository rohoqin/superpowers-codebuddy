# superpowers-codebuddy 设计文档

日期：2026-10-28
状态：待批准（v2）
方案：自包含技能包 + 上游跟随机制（**仅 SkillHub / GitHub，不进插件市场**）

**变更记录**
- v1：方案 C 双产物（插件 + 技能包），准备进 CodeBuddy 插件市场。
- v2：需求方选择**只发 SkillHub、不碰插件市场**。删除全部插件产物（`.codebuddy-plugin/`、`plugins/`、插件清单），引导注入降级为可选能力。其余（生成器、跟随上游、回归测试）保留。

## 1. 意图与缘由

`obra/superpowers` 是一套给编码 Agent 用的开发方法论技能库（MIT，v7.0.1），上游支持 15 个 harness，**不支持 CodeBuddy**。

本机已有一份跑通的适配（15 个技能、引导注入 hook、10 项回归测试全绿），现在要把它变成可公开分发的开源项目：GitHub 仓库 + SkillHub 技能包。

两个已知的"不是空白"的事实决定了定位：
- CodeBuddy 官方插件市场里已有 `superpowers` **4.0.3**（14 个无前缀技能，带 hook 与 3 个斜杠命令）；
- GitHub 上已有两个同类移植仓库。

所以本项目不是开荒，而是**版本跟进 + 可维护性**：把"跟着上游不腐烂"做成机制，把"上游结构变化会显式报错"做成测试。

## 2. 目标

- G1 装上即用：一条命令装完 15 个技能，不需要用户手工改任何配置。
- G2 跟上上游：上游发新版后，产物能被自动重新生成并提交 PR。
- G3 可验证：仓库自带回归测试，上游结构变化时**显式失败**，不静默降级。
- G4 单一出口：产物是 SkillHub 技能包（同时可从 GitHub 直接安装），**不产出任何插件形态文件**。
- G5 诚实归属：技能内容署名 obra/superpowers，本项目只声明适配层贡献。

## 3. 非目标

- N1 不修改技能的方法论语义，不做"我们的增强流程"。
- N2 阶段一不做完整中文化（README 与适配文档用中文；技能正文保持上游英文）。
- N3 不做 GUI、不做浏览器演示站。
- N4 不代替上游处理 issue。
- N5 不进 CodeBuddy 插件市场，不做 `.codebuddy-plugin` 产物，不提供斜杠命令。
- N6 不默认修改用户全局配置（`settings.json`）。

## 4. 反目标（做到即失败）

- A1 用户"装个技能"结果被静默改写了 `~/.codebuddy/settings.json`。
- A2 半年后产物停在旧版本，用户以为在用最新 superpowers。
- A3 上游改了目录结构，生成"成功"但内容错位（静默腐烂）。
- A4 与上游行为不一致却未声明，用户拿本项目的表现去向上游报 bug。

## 5. 约束（已实测）

| # | 事实 | 来源 |
|---|---|---|
| C1 | CodeBuddy 工具词汇与 Claude 不同：`Skill`→`use_skill`、`TodoWrite`→`todo_write`、`Bash`→`execute_command`、`Edit`→`replace_in_file`、`Grep`→`search_content` | genie `TOOL_NAME_CRAFT_TO_CLI` |
| C2 | 技能目录：用户级 `~/.codebuddy/skills/<name>/SKILL.md`，项目级 `.codebuddy/skills/`；技能名 = 目录名，全局唯一 | 运行时 |
| C3 | **技能 frontmatter 不支持 hooks**，只认 `name`/`description`/`allowed-tools`/`model` 等字段 | genie 技能加载器（无 `skillHooks`/`frontmatter.hooks`） |
| C4 | `SessionStart` 引导注入只能通过 `settings.json` 的 `hooks.SessionStart`（或插件自带 `hooks/hooks.json`）实现；本项目既不做插件，就只能让用户显式选择是否注册 | genie `SessionHookManager` |
| C5 | hook 通过 `shell:true` 执行、stdin 传事件 JSON、默认超时 60s；实测注册后动态加载并触发 | 探针实验 |
| C6 | 技能市场条目允许"一条目含多个嵌套子技能"（现存 `cloudbase` 23 个、`marketing-skills` 24 个） | 本地市场缓存 `~/.codebuddy/skills-marketplace/.codebuddy-skill/marketplace.json`（293 条目） |
| C7 | `task` 工具只暴露只读的 `code-explorer`，没有可写代码的通用 implementer subagent | 当前运行时 |
| C8 | 官方插件市场已有 `superpowers` 4.0.3：14 个无前缀技能 + hooks + 3 个命令 + `lib/skills-core.js` | `codebuddy-plugins-official/external_plugins/superpowers/` |
| C9 | GitHub 账号 `rohoqin`（Roho Qin），token 含 `repo` + `workflow`；`gho_` 前缀为 OAuth token，会过期，不能当长期 secret | `gh auth status` |
| C10 | 工作区里的 `obra-superpowers/` 是上游 6.2.0 旧克隆（14 技能），**不可作为生成源** | `package.json` version |

## 6. 方案选择

| 方案 | 内容 | 取舍 |
|---|---|---|
| A 薄适配层 | 仓库只含生成脚本与测试，安装时 clone 上游再跑脚本 | 永不腐烂；但需联网跑脚本，SkillHub 要自包含包，审核会卡 |
| **B 自包含技能包（选定）** | 15 个适配后技能全部进仓库，一键安装 / 一条 SkillHub 条目 | 零门槛、符合市场形态、可离线安装；但裸 B 半年后会停在旧版 |
| C 双产物 | B + 插件形态双出口 | 已否决：不进插件市场（N5） |

**选定 B，并补上 A 的机制**：产物是自包含包，但包由生成器从指定上游 tag 产出，配一条每周探测上游的 CI。这样"开箱即用"和"不腐烂"同时成立，且不产生任何插件产物。

## 7. 目录结构

```
superpowers-codebuddy/
├── skills/                         # 【生成物】15 个 superpowers-* 技能（市场与 GitHub 抓取都认这里）
├── hooks/
│   └── session-start               # 可选：引导注入脚本（默认不注册）
├── install.sh                      # 一键安装（默认只装技能；--with-hook 才写 settings.json）
├── adapt/                          # 适配层源码（人工维护）
│   ├── generate.py                 # 上游 skills/ → 仓库 skills/
│   ├── rules/                      # 变换规则（见 §8）
│   ├── assets/codebuddy-tools.md   # 运行时对照文档
│   ├── upstream.json               # 上游 tag / commit / 预期技能清单
│   └── verify.py                   # 回归测试
├── dist/                           # 【生成物】SkillHub 提交用 zip
│   └── superpowers-skill-<ver>.zip
├── .github/workflows/
│   ├── verify.yml                  # PR/push：跑 verify.py
│   ├── sync-upstream.yml           # 每周一 03:00 UTC + 手动：探测上游新 tag，重新生成，开 PR
│   └── release.yml                 # 打 tag：生成 dist zip 并挂 Release
├── docs/superpowers/specs/         # 设计文档
├── README.md / README.zh.md
├── LICENSE                         # MIT（本项目适配层）
└── NOTICE                          # 上游归属与 MIT 声明
```

`skills/` 与 `dist/` 是生成物：**进版本库**（市场与用户要能直接看、直接下），但 CI 断言"重跑生成器后 `git diff` 为空"，防手改漂移。

## 8. 生成规则（核心，来自实测）

输入：指定上游 tag 的 `skills/`。输出：`skills/superpowers-*/`。按序应用：

| R# | 规则 | 为什么必须有 |
|---|---|---|
| R1 | 目录名与 frontmatter `name` 都加 `superpowers-` 前缀 | 技能名全局唯一；与官方 4.0.3 的无前缀技能不撞名 |
| R2 | `superpowers:<skill>` → `superpowers-<skill>`（全文件，含脚本） | 上游正文 49 处带冒号命名空间，不改则 `use_skill` 找不到 |
| R3 | `((?:\.\./)+)<skill>/` → `\1superpowers-<skill>/`（全文件） | 兄弟目录相对路径。**真实 bug**：`task-start`/`task-done` 里 `../../subagent-driven-development/scripts` 加前缀后 cd 失败 |
| R4 | 追加 `references/codebuddy-tools.md`，并在 `using-superpowers` 的 Platform Adaptation 表登记 CodeBuddy | 不登记则 CodeBuddy 专用说明永远读不到 |
| R5 | `writing-skills` 的技能存放路径补 `~/.codebuddy/skills/` | 否则会指引用户写到 Claude 目录 |
| R6 | `brainstorming` 的 `run_in_background` 改为 `nohup ... &` | CodeBuddy 无该参数 |
| R7 | 保留其它 harness 的 `references/*-tools.md` | Platform Adaptation 表引用它们，删了会断链 |
| R8 | 生成前校验：上游必须存在 `adapt/upstream.json` 里列出的 15 个技能目录；缺失/新增则**失败退出**并打印差异 | 防静默腐烂（A3）。增删技能是需人工决策的变更 |

## 9. 引导注入（可选能力，默认关闭）

- 技能形态拿不到 `SessionStart`（C3），所以注入**不能默认发生**（N6/A1）。
- `install.sh` 默认只往 `~/.codebuddy/skills/` 复制技能；加 `--with-hook` 才把 `hooks/session-start` 注册进 `~/.codebuddy/settings.json`，并在输出里明确打印"将修改哪个文件的哪个字段"，同时备份原文件。
- 卸载：`install.sh --uninstall` 删除 15 个技能目录，`--uninstall --with-hook` 一并移除 hook 注册。
- 不加 hook 时，技能靠 `description` 被自动触发 —— 可用，但少了"每次会话开头强制生效"的强度。README 用一句话说清差异，不夸大。
- 注入内容：`using-superpowers/SKILL.md` 正文（剥离 frontmatter）+ CodeBuddy 工具词汇说明，约 3.5KB。失败必须放行（`exit 0` + 空输出）。

## 10. 命名与版本

- 仓库 `rohoqin/superpowers-codebuddy`；技能目录与 `name` 均为 `superpowers-<skill>`；SkillHub 条目名 `Superpowers（CodeBuddy 适配版）`，**一条目含 15 个嵌套子技能**（依据 C6）。
- 版本 `<上游版本>-cb.<n>`，如 `7.0.1-cb.1`；`adapt/upstream.json` 记录上游 tag、commit SHA、预期技能清单。
- 发布前 `verify.py` 断言：仓库版本 == zip 内清单版本 == upstream.json 对应版本。

## 10.1 与官方 4.0.3 的关系

官方插件市场那个 `superpowers` 停在 4.0.3，14 个无前缀技能。本项目是**技能包**，与它不构成文件级冲突，但两者同时存在时**两套流程都会触发**，会互相打架。

处理方式：
- README 首屏给一张对比表：官方 4.0.3（插件，含命令/hook）vs 本项目（技能包，对应上游 7.0.1）。
- 明确一句：「若已安装插件市场的 superpowers，建议先禁用，避免两套技能同时生效」。
- `install.sh` 安装前检测 `~/.codebuddy/skills/` 下是否存在无前缀的同名技能（`brainstorming` 等 14 个），存在则**告警并要求确认**，不自动删除别人的目录。
- 不主动向官方提 issue 请求升级；若官方将来升到 v7，本项目退化为中文适配层，届时评估是否停维护。

## 11. 验证策略

种子来源：本机已跑通的 `~/.codebuddy/superpowers/`（`sync.sh`、`verify.py`、`hooks/session-start`）与 `~/.codebuddy/skills/superpowers-*`，搬进仓库改造，**不重写**。

现有 10 项（清单/frontmatter、相对引用可达、命名空间残留、hook 契约、hook 失败模式、hook 耗时、settings 注册、脚本语法、计划执行脚本真实链路、可视化伴侣脚本）。迁移调整：

- 与用户机器解耦：路径一律从仓库根推导，不写死 `$HOME`。
- CI 可跑：`settings.json 注册`项改为校验 `install.sh --with-hook` 生成的片段结构（在临时目录里跑，不碰真实配置）。
- 增补：生成物一致性（重跑 `generate.py` 后 `git diff --exit-code` 为空）、版本三方一致（§10）、`NOTICE` 含上游 MIT 声明、技能数 == 15、`install.sh` 卸载后目录干净。
- 不可自动化：IDE 内真实触发 hook 与技能自动触发。README 写"三步自检"，不假装 CI 覆盖了。

## 12. 发布流程

1. `python3 adapt/generate.py --ref v<上游tag>` → 重新生成 `skills/`
2. `python3 adapt/verify.py` 全绿
3. 更新 `adapt/upstream.json` 与 README 对比表版本号
4. 打 tag `<版本>` → `release.yml` 产出 `dist/superpowers-skill-<ver>.zip` 挂 Release
5. SkillHub：提交该 zip（含 `.codebuddy-skill/marketplace.json` 与嵌套 `skills/`）。**提交前按官方 SkillHub 提交指引核对 zip 布局与清单字段** —— 目前 C6 只证明了"嵌套子技能可被收录"，未证明提交包的确切 schema。
6. GitHub 用户路径：`git clone` + `./install.sh`（README 主推），或让 CodeBuddy 直接读取仓库里的 `skills/`。

## 13. 风险

| 风险 | 影响 | 缓解 |
|---|---|---|
| 上游重构 `skills/` | 生成失败或错位 | R8 显式失败 + CI 红灯，不许"尽量生成" |
| SkillHub 提交 schema 与假设不符 | 打包重做、审核驳回 | 提交前先按官方指引核对；`dist` 布局集中在一处生成，改起来只动一个文件 |
| 用户同时装官方 4.0.3 | 两套技能同时触发 | 安装前检测 + README 告警（§10.1） |
| 不加 hook 导致"技能没被触发" | 用户觉得没用 | README 写清 `--with-hook` 的作用与代价，并给自检三步 |
| `gho_` token 过期 | CI 自动 PR 失效 | CI 用 fine-grained PAT；`sync-upstream.yml` 失败要显式通知 |
| 与已有两个移植仓库同质 | 无人使用 | README 突出：对应上游 7.0.1、生成器跟随、回归测试、可卸载 |

## 14. 需求方已定

- 只发 SkillHub / GitHub，**不进插件市场**（v2 变更）
- 双出口改为单出口，插件产物全部不做
- 技能正文跟随上游，不改写语义
- GitHub owner：`rohoqin`

## 15. 留给 builder 的决定

- `generate.py` 用 Python（无 npm 依赖）还是 Node
- 变换规则用硬编码函数还是可组合 rule 列表（倾向后者，便于单测）
- `dist/` 是否进版本库（倾向进，便于市场抓取与人工核对）
- `install.sh` 是否提供 `--project` 装到项目级 `.codebuddy/skills/`（倾向提供）
- 中文化范围（阶段二议题）

## 16. 待确认

无。批准后进入实施计划（`superpowers-writing-plans`）。
