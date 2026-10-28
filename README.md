# Superpowers for CodeBuddy

[中文说明](README.zh.md) | English

[obra/superpowers](https://github.com/obra/superpowers) (**v7.0.1**, MIT) adapted for CodeBuddy: 15 skills, install and go.

> The skills are upstream work. This repo is only the adaptation layer — what it takes to make them run correctly on CodeBuddy.

## Why this exists

Upstream supports 15 harnesses (Claude Code, Codex, Cursor, Gemini CLI…), **not CodeBuddy**. Copying `skills/` over breaks in three places:

1. Skill names come from directory names and must be globally unique → they need a prefix.
2. 49 inline `superpowers:foo` namespace references → CodeBuddy has no namespaces, `use_skill` can't resolve them.
3. Scripts hardcode sibling paths like `../../subagent-driven-development/scripts` → after renaming, `cd` fails and plan execution silently dies.

The generator handles each of these, and a regression suite keeps them handled.

## Relationship to the marketplace `superpowers`

| | Marketplace `superpowers` | This repo |
|---|---|---|
| Upstream version | 4.0.3 | **7.0.1** |
| Form | plugin (commands, hooks, lib) | skills only |
| Skill names | unprefixed `brainstorming` | `superpowers-brainstorming` |
| Updates | marketplace-driven | generator follows upstream tags, CI checks weekly |

Both can be active at once — the skill names differ, so both sets trigger. If you already have the marketplace plugin, disable it first or the two workflows will fight.

## Install

```bash
git clone https://github.com/rohoqin/superpowers-codebuddy.git
cd superpowers-codebuddy
./install.sh
```

Installs into `~/.codebuddy/skills/`. Use `--project` to install into `./.codebuddy/skills/` instead.

### Optional: bootstrap injection

On Claude Code, upstream injects the full `using-superpowers` text at session start via a `SessionStart` hook, which is what makes skills mandatory rather than optional.

CodeBuddy skill frontmatter does **not** support hooks (only `name`/`description`/`allowed-tools`/`model`), so this can only live in `settings.json`:

```bash
./install.sh --with-hook
```

It backs up your `settings.json` and appends exactly one `hooks.SessionStart` entry pointing at `hooks/session-start`.
Without it, skills still work — they trigger off their `description`, just without the forced prelude.

## Verify

```bash
python3 adapt/verify.py        # 16 checks, must be green
```

Then start a new session and ask whether it has superpowers — if it names and uses `superpowers-*` skills, you're set.

## Uninstall

```bash
./install.sh --uninstall
```

Removes only the directories recorded in the install manifest, plus its own hook registration. Refuses to run if the manifest is missing, and never touches other people's skills.

## What's included

`brainstorming`, `diagnosing-superpowers`, `dispatching-parallel-agents`, `executing-plans`,
`finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`,
`subagent-driven-development`, `systematic-debugging`, `test-driven-development`,
`using-git-worktrees`, `using-superpowers`, `verification-before-completion`,
`writing-plans`, `writing-skills`

## Known limits

- **No writable subagents.** CodeBuddy's `task` tool only exposes a read-only `code-explorer`, so subagent-driven development degrades to `executing-plans` (inline execution). Documented in the runtime notes.
- **Visual companion** needs a long-running process; CodeBuddy has no `run_in_background`, so it uses `nohup ... &`.
- **Never edits global config by default.** Only `--with-hook` touches `settings.json`, and it backs it up first.

## Maintenance

```bash
python3 adapt/generate.py                  # regenerate against the tag pinned in adapt/upstream.json
python3 adapt/generate.py --ref v7.0.2     # try a newer tag
```

If upstream adds or removes a skill, the generator **fails loudly** and prints the diff instead of producing a misaligned package.

## License

Adaptation layer: MIT. Skill content is © [Jesse Vincent / Prime Radiant](https://github.com/obra/superpowers), also MIT. See [NOTICE](NOTICE).
