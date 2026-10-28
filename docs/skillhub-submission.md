# SkillHub 提交信息

> 状态：**待你本人提交**。SkillHub 的 `/dashboard/publish` 是登录后路由（游客态 `uin` 为空会被重定向到登录页），且发布前需完成**腾讯云实名认证**，这两步只能由账号持有人完成。

## 需要上传的文件

`dist/superpowers-skill-7.0.1-cb.1.zip`（也可直接从 [Release](https://github.com/rohoqin/superpowers-codebuddy/releases) 下载）

内含：

```
skills/superpowers-*/            15 个技能
.codebuddy-skill/marketplace.json 市场清单
README.md
```

## 可直接复制的字段

| 字段 | 值 |
|---|---|
| 名称 | Superpowers for CodeBuddy |
| slug | `superpowers-codebuddy` |
| 版本 | `7.0.1-cb.1` |
| 分类 | 开发工具 / 效率工具 |
| 仓库 | https://github.com/rohoqin/superpowers-codebuddy |
| 上游 | obra/superpowers v7.0.1 |

**一句话简介**

> 把 obra/superpowers 的 15 个开发方法论技能适配到 CodeBuddy：需求澄清、实施计划、TDD、系统化调试、代码评审全流程。

**详细描述**

> Superpowers 是给编码 Agent 用的完整开发方法论：动手前先澄清意图，再拆成可验收的小任务，开发过程强制红绿重构，任务间做代码评审，收尾验证后合并。
>
> 本条目是它在 CodeBuddy 上的适配版，对应上游 v7.0.1。上游未支持 CodeBuddy，直接复制会因为三处差异失效：技能名需全局唯一、正文里的 `superpowers:` 命名空间在 CodeBuddy 不存在、部分脚本硬编码了兄弟目录路径。这三处已由生成器处理，并有 17 项回归测试盯着。
>
> 注意：插件市场里已有一个 `superpowers` 4.0.3（技能名无前缀）。两者同时启用会同时触发，建议只留一个。
>
> 引导注入（每次会话开头强制加载技能规则）需要写 `settings.json`，不在技能包默认行为里，见仓库 README 的 `--with-hook`。

**变更说明（首个版本）**

> 首个版本，对应上游 v7.0.1（commit 2ce8aa1）。包含 15 个技能。

## 提交前要核对的一件事

`.codebuddy-skill/marketplace.json` 与 zip 的目录布局是按现有市场缓存里的结构推出来的（市场允许一个条目含多个嵌套子技能，现存 `cloudbase` 23 个、`marketing-skills` 24 个），**没有对照官方提交 schema 核验过**。

如果上传页提示格式不对，改 `adapt/package.py` 一处即可：

```bash
python3 adapt/package.py && python3 adapt/verify.py
```

## 图标

仓库内暂无图标。SkillHub 若要求 512×512 图标，可用项目名首字母设计，或复用上游 `assets/` 里的素材（注意上游素材的授权同为 MIT）。
