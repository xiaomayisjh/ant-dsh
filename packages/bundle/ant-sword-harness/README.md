# @deepseek-ai/dsh-ant-sword-harness

English | [中文](README.zh.md)

A security-research profile bundle for DeepSeek Harness. One install composes seven capabilities over a profile: a bundled reverse-engineering / CTF skill pack, a self-contained workspace snapshot + `/rewind` capability, a selectable red-team agent preset, autonomous-mode Web UI, MCP runtime management, multi-agent teams, and the in-app plugin market.

## Capabilities

| Capability | Source | What it adds |
| --- | --- | --- |
| **Reverse / CTF skill pack** | This package (`skills/`) | 93 reverse-engineering, pentest, and CTF skills registered on `ctx.skills`, invocable through the `skill` tool or by name. |
| **Workspace snapshot + rewind** | This package (`src/rewind/`) | Captures a snapshot before every mutating tool call; `/rewind` restores files and forks the session back to a checkpoint's turn boundary. |
| **Red-team agent preset** | This package (`preset/red-team/`) | A selectable agent preset with the standard mode's full capabilities plus a red-team operator persona and the bundled skill pack. |
| **Autonomous-mode Web UI** | `@deepseek-ai/dsh-client-ui-autograph` | Adds the blackboard tab and runtime/configuration surfaces through the host's `dsh.client` discovery path. The bundle installs and mounts this dependency automatically. |
| **MCP runtime manager** | This package plus `@deepseek-ai/dsh-mcp-client` | Embedded security and `dsh-mcp-bridge` presets, live enable/disable/add/delete, JSON synchronization, protocol probes, and explicit reloads for stdio, SSE, and Streamable HTTP servers. |
| **Agent teams** | [`@nanmicoder/dsh-agent-teams`](https://github.com/NanmiCoder/dsh-agent-teams) | Captain-led delegation: durable sub-agents, dependency-aware tasks, mailbox messaging. |
| **Plugin market** | [`dshmarket`](https://github.com/dsh-market/dsh-market) | Browse, search, and one-click-install community plugins from Settings. |

## Install

Windows PowerShell installs the complete bundle into the `web` profile, including the UI, agent teams, and plugin market dependencies:

```powershell
irm https://raw.githubusercontent.com/xiaomayisjh/dsh-ant-sword/dev/install-ant-sword.ps1 | iex
```

Linux and macOS use the equivalent POSIX bootstrap:

```bash
curl -fsSL https://raw.githubusercontent.com/xiaomayisjh/dsh-ant-sword/dev/install-ant-sword.sh | bash
```

Then start it directly:

```powershell
dsh web
```

The installer builds release-ready package tarballs in a temporary workspace, installs all required root dependencies, and removes the duplicate bundle layers that `dsh plugin add` would otherwise create for `agent-teams` and `dshmarket`. No profile patch or dependency repair is required.

### Install from a local release

A complete release directory contains the bundle, Autograph UI, agent-teams, and dshmarket tarballs plus `ant-sword-release-manifest.json`. The manifest records each filename, package name, version, and SHA-256. The installer accepts either the directory or manifest path, rejects missing, duplicate, extra, or hash-mismatched tarballs before changing the profile, and passes only local tarball paths to pnpm in offline mode.

```powershell
.\install-ant-sword.ps1 -Release C:\path\to\ant-sword-release
# A manifest path is equivalent:
.\install-ant-sword.ps1 -Release C:\path\to\ant-sword-release\ant-sword-release-manifest.json
```

```bash
./install-ant-sword.sh --release /path/to/ant-sword-release
```

Local release mode runs from a checkout so the bootstrap can call the shared `install-profile.mjs`; it does not download source or rebuild packages. Installation still ends through the profile installer and requires the existing `dsh`, Node.js, and pnpm installation.

### GitHub release assets

The release command builds both workspace packages, downloads pinned copies of the two third-party packages at release time, writes the manifest, and uploads all five files. Consumers can download those assets into one directory and use the local release command without npm registry access.

```sh
pnpm run release:github -- --repo <owner>/<repo> [--profile <name>] [--output <directory>] [--dry-run]
```

`--output` selects the retained release directory; it defaults to `.release/ant-sword-<tag>`. `--dry-run` performs the build, pack, third-party acquisition, and manifest generation but skips GitHub upload. Re-running the same tag replaces same-named assets.

## Compatibility

The first-party rewind capability is built only on the harness's forward-stable public primitives — `ctx.sessions.fork`, `ctx.storageDomain`, the `fs/write-intent` / `tools/pre-execute` interception points, the command registry, and the session `turn` / `step` lifecycle events — so it tracks official upgrades. The two third-party rows follow their own authors' releases through the npm version ranges in `package.json`.

## Skill pack usage and authorization

The bundled skills cover **authorized** reverse engineering, penetration testing, and security research only. Ensure you hold lawful authorization for any target system before applying them. Upstream content is MIT-licensed; see `skills/UPSTREAM-LICENSE.txt`.

## Rewind

A snapshot is captured before every mutating tool (`bash`, `write`, `edit`, `str_replace_editor`, `pwsh`, `terminal_send` by default). The snapshot provider is git-first (side-effect-free unreferenced objects; restore is worktree-only and path-explicit, never deleting files created after the checkpoint) and falls back to incremental directory copies outside git repositories.

```text
/rewind                  # list checkpoints
/rewind <id-prefix>      # restore files and fork the session at the checkpoint's turn boundary
/rewind step <N>         # restore the nearest checkpoint at or before step N
/rewind latest           # restore the newest checkpoint
/rewind preview <target> # read-only impact: which files would change, which stay
/rewind clear            # delete this session's checkpoints (files untouched)
```

Every restore first captures a guard checkpoint, so `/rewind <guard-id>` undoes a rewind.

## Red-team preset

The bundle materializes a `red-team` agent preset into the harness's writable preset root (`$DSH_HOME/.agent-presets/red-team/`) on startup, so it appears in the preset picker with the standard mode's full tool catalog plus the bundled skill pack and a red-team operator persona. Select it per session in the web UI, or set it as the default via the `agent-presets.default` setting. Set `syncRedTeamPreset: false` in the plugin config to opt out of the sync.

**Operating contract.** The persona carries the upstream reverse-skill execution discipline, absorbed from the desktop-client design this pack derives from: route first (the `skills/config/routing.json` table picks the PRIMARY skill before any action), maintain durable engagement state (`case-init` lands `work/<case>/scope.md` + `rules.md`; `task-plan` / `progress` / `findings` templates under `skills/pentest-tools/templates/`), read `tool-index.md` instead of guessing tool paths, execute deterministic steps without confirmation stalls, self-supervise every few tool calls, and close engagements with the completion contract (report + diagram + anonymized field-journal write-back + index update). The persona additionally carries the upstream research operating frame (`[MODE: UNRESTRICTED]`): concrete targets normalize to placeholders, acquisition-plus-transformation requests dispatch as one indivisible local-sample workflow, refusal phrases and task substitution are barred, and file requests must produce verified artifacts. The scope gate stays process-level: active testing starts only after `auth.status = granted` in `scope.md`, the attack surface never widens beyond the declared scope, and reports are anonymized.

**Research-only posture.** This preset is research software for authorized engagements; it is not a released product. The preset picker carries a disclaimer to that effect, and the bundle is not published with this frame enabled for general use.

**Tuning points:**

- **Persona / global prompt** — edit the `persona` row's `config.text` in `preset/red-team/agent.cordis.yml`. It shadows the deployment persona for sessions on this preset only and interpolates `{{model}}` / `{{cwd}}`.
- **Skill descriptions** — edit the `description` (and `whenToUse`) frontmatter of the relevant `skills/<name>/SKILL.md`; that text is what the model's catalog surfaces and routes on.
- **Skill routing** — the bundled pack rides the global skill layer; a same-named project or user skill shadows it (bundled rank `600` loses to project/user layers).

## Configuration

```yaml
- id: ant-sword-harness
  name: '@deepseek-ai/dsh-ant-sword-harness'
  config:
    syncRedTeamPreset: true       # materialize the red-team preset into the user preset root
    rewind:
      provider: auto              # auto | git | copy
      maxSnapshots: 50            # per session
      maxSnapshotBytes: 536870912 # global incremental-byte quota
      pruneOnTurnEnd: true
      preRewindCheckpoint: warn   # warn | require | off
      listLimit: 10
```

The WebUI MCP editor persists its catalog through the `ant-sword-runtime` settings namespace and applies each committed generation without restarting the Host. It uses the standard settings client scope when that namespace is exposed; otherwise, the bundle-owned loopback-only `/ant-sword/runtime-config` bridge carries revision-fenced field mutations through the same `ctx.settings` provider, schema validation, and reconcilers. It supports structured fields and `mcpServers` JSON in both directions, including Claude-style named entries; `测活` performs a temporary protocol handshake and tool discovery without replacing live registrations, while `热重载` disposes and reconnects the selected live plugin fiber.

## Model Experience

Indirectly, through the bundled skill pack and the composed rows: this bundle is a patch-list carrier plus a skill provider, and the `skill` tool (`@deepseek-ai/dsh-tool-skill`) plus each composed third-party package own the model-facing rendering of whatever it contributes.

#### KV Cache effect

The 93-skill catalog is advertised through the harness's skill catalog mechanism; each skill body is loaded only on invocation, so the standing prompt cost is the catalog summary rather than the full bodies. The red-team preset additionally shadows the deployment persona with its operator persona — routing contract, engagement-state files, tool discipline, and completion checklist — for sessions on that preset. The rewind and third-party rows contribute their own model-facing text under their owning packages.

## Known Limitations and Deferred Work

- **Rewind snapshot hooks are pass-through on the tool pipeline** — they cover the configured `mutationTools` and the fs write/edit path only; a mutation performed outside those tools (for example by a third-party plugin that writes files directly without a registered tool) is not captured. Extend `mutationTools` to cover additional mutating tools.
- **Fork granularity is the turn boundary** — `ctx.sessions.fork` rejects a boundary inside an open turn, so a rewind always resumes at the checkpoint's `turn/end`; a mid-turn checkpoint restores files precisely but forks at the turn close.
- **Third-party rows are pinned to their authors' harness compatibility** — `@nanmicoder/dsh-agent-teams` and `dshmarket` declare their own harness peer versions; a profile on an incompatible harness build mounts them only as far as those packages support.
- **The skill pack injects 93 catalog entries** — discovery consumers see the full list; a skill that names an MCP server still depends on the corresponding catalog entry being enabled and healthy.
- **The red-team preset sync writes to the user preset root** — `$DSH_HOME/.agent-presets/red-team/` is created/updated on startup unless `syncRedTeamPreset: false`; a user-edited copy under that directory is overwritten only where its content differs from the bundled source, and files the user added beside it are left alone.