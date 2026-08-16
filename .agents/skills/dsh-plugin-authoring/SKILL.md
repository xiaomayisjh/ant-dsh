---
name: dsh-plugin-authoring
description: 'Use when creating a new plugin package in the deepseek-harness repo, adding a tool/LLM-adapter/command/UI plugin, wiring a package into profiles or bundles, or auditing an existing package against the harness package conventions (exports shape, package.json invariants, tsconfig layout, invariant companion, README gates).'
---

# Authoring a DeepSeek Harness Plugin

This skill walks a new `@deepseek-ai/dsh-<name>` package from an empty directory to a gated, bootable plugin. It condenses the binding contracts; the linked documents remain authoritative.

## Read before writing

- [packages/AGENTS.md](../../../packages/AGENTS.md) — the package conventions every harness plugin must satisfy (exports, events, invariants, README duties).
- [docs/architecture.md](../../../docs/architecture.md) — pick the extension point first; the "Where new behavior goes" table maps each goal to its mechanism.
- [docs/cookbook/adding-a-package.md](../../../docs/cookbook/adding-a-package.md) — the file-by-file checklist, manifest invariants, naming-role table, and README contract.
- [docs/testing.md](../../../docs/testing.md) — the REAL-composition and HMR-disposal test requirements.
- A sibling package in the same group is the living template. Copy its `package.json`/`tsconfig.json` shape and adjust; when this skill and the sibling drift, the sibling plus the cookbook win.

## Decide the design before the files

1. **Choose the extension point.** A model-facing tool registers on `ctx.tools`; a model provider on `ctx.llm`; a human command on `ctx.commands`; background work on `ctx.jobs`; interception on the documented `agent/*`/`tools/*` events. If the capability is swappable, design the full seam: Service Definition, Service Provider, Consumer — possibly split into separate packages (`packages/shell/` is the template).
2. **Choose the plugin form.** A service package default-exports its service class. A function plugin named-exports `name` / `inject` / `Config` / `apply` and has **no** default export. Never mix the forms in one entry; the Loader drops a function plugin's namespace when a default export is present ([postmortem](../../../docs/postmortem/0001-acp-default-export-drops-inject.md)).
3. **Declare injections precisely.** `inject` lists only required services, read through `ctx.<name>`. Optional services use `ctx.get(name)`; never read an undeclared service through the property proxy.
4. **Pick the group and name.** Reuse an existing `packages/<group>/` when the role matches. Name the stable current responsibility with the role table in the cookbook (`Registry`, `Runtime`, `Policy`, `Provider`…), not the first implementation or a hoped-for future. Match the `ctx` key number: singular for one engine/policy/store, plural for a registry of named members.

## Scaffold the package

Layout for `packages/<group>/<pkg>/`:

```text
package.json
tsconfig.json
src/index.ts        # plugin entry
src/invariant.ts    # invariant companion (mandatory)
src/types.ts        # types only, when needed — no runtime code
tests/              # package-level tests, never src/__tests__/
README.md
```

`package.json` invariants, gated by `pnpm run constraints`:

- `"type": "module"`, `"main": "lib/index.js"`, `"types": "lib/types/index.d.ts"`.
- `exports["."]` is `{ "types": "./lib/types/index.d.ts", "default": "./lib/index.js" }`; add `"./invariant"`, `"./package.json"`, and any documented subpaths.
- `files` is exactly `lib/index.js`, `lib/invariant.js`, `lib/types/**/*.d.ts`, plus the recognized extras the gate encodes (CLI bins add `lib/bin.js`; runtime defaults pointing into the emitted tree add `lib/types/**/*.js`). Never ship `src`, maps, or stale root declarations.
- `@deepseek-ai/cordis` appears in **both** `peerDependencies` and `devDependencies` with the same range; mirror every dsh peer in `devDependencies`; `@deepseek-ai/schemastery` goes in `dependencies` when you declare a `Config` schema.
- No `"private": true`; `publishConfig.access` is `"public"`; `version` matches the root `package.json`.

`tsconfig.json`: extends `../../../tsconfig.base.json` (client packages under `packages/client/` extend `tsconfig.base.client.json`), `rootDir: "src"`, `outDir: "lib/types"`, `include: ["src"]`, and `references` covering `../../../vendor/cordis`, `../../../vendor/cosmokit`, `../../../vendor/schemastery` when `Config` is used, every workspace dependency, and `../../runtime-diagnostics/invariants`.

Register the package in exactly **one** aggregate: `tsconfig.host.json` or `tsconfig.client.json` `references`. Never copy the `api/remotes` split. In-package relative imports keep explicit `.ts` specifiers (`export * from './types.ts'`).

## Write the plugin

Function-plugin skeleton (see `packages/context/time-context` for a full example):

```ts
import type { Context } from '@deepseek-ai/cordis'
import z from '@deepseek-ai/schemastery'

export const name = 'my-plugin'
export const inject = ['agents']

export interface Config {
  /** What this option changes for the model or user. */
  option?: number
}
export const Config: z<Config> = z.object({ option: z.number() })

export function apply(ctx: Context, config: Config): void {
  // Register listeners/effects; they dispose with ctx.
}
```

Service plugins instead `export default class MyService extends CordisService { ... }` and declare `Context.mixin` / events in `src/types.ts`.

Behavior rules that review and gates enforce:

- Every registration must dispose: listeners, timers, and registry entries unwind with the plugin's fiber; registry contributions need the HMR-safety test (dispose the fiber, observe removal).
- Publish state only at its commit point; emit notifications after the operation succeeds.
- Enforce decisions in the operation that makes them — facades and listener order are not enforcement.
- Model-facing text is written from the model's perspective: task concepts only, no UI/transport vocabulary. Pin stable model-visible strings verbatim in tests.
- A public service method with exactly one internal caller is a smell — pass a private capability closure instead.
- Tool-schema, Loader, UI, and transport behavior stays in the Consumer; one consumer must not dictate the service contract.

## Write the invariant companion

Every package owns `src/invariant.ts`, mounted through the `./invariant` subpath (see `packages/core/tools/src/invariant.ts` for the canonical shape):

- Named-export `name = '<pkg>-invariant'`, `inject = ['invariants']`, and an `apply(ctx)` returning `ctx.invariants.register('<full package name>', install)`.
- The installer checks a real event/data relation of the package (frozen snapshots, event ordering, non-empty identifiers). A package with genuinely nothing to check gives a package-specific `No runtime invariant:` reason; generated companions and unexplained empties fail `verify-package-invariants`.

## Write the tests

Per [docs/testing.md](../../../docs/testing.md):

- Product-visible plugins need a REAL-composition test: boot a test-only `cordis.yml` through the Loader and app/process, mock only external services or nondeterministic inputs, and assert model-visible, durable, or user-visible output. Hand-built `ctx.plugin(...)` suites are not sufficient on their own.
- Test configs live under `examples/<agent>/tests/fixtures/<group>/<package>/cordis.yml` when a package owns a checked-in config ([examples rules](../../../examples/AGENTS.md)).
- Keep opt-ins out of shipped defaults; tests may enable them.

## Write the README

End the README with the canonical trailing sequence (both gates run under `doc-sync`):

1. `## Model Experience` — either one H3 model-context entry per direct/conditional/capped contribution with the ordered H4 fields `#### What the model sees` / `#### Token effect` / `#### KV Cache effect` (verbatim system-prompt text in a titled H5 + ` ```markdown ` fence; tool-schema entries link an anchored section of `docs/tool-catalog.md`), or the audited one-sentence `None, as …` / `Indirectly, through …` short form followed by the KV-cache H4 — the short form requires an entry in `SENTENCE_MODEL_EXPERIENCE` or `NO_MODEL_EXPERIENCE_SECTION` in [scripts/verify-package-readme-model-experience.ts](../../../scripts/verify-package-readme-model-experience.ts), added in the same commit.
2. `## Known Limitations and Deferred Work` — at least one top-level `- ` bullet recording durable consumer gaps, or a justified entry in `NO_LIMITATIONS` in [scripts/verify-package-readme-limitations.ts](../../../scripts/verify-package-readme-limitations.ts).

These two sections are the final two H2s, in that order. Behavior changes (config keys, defaults, error codes, wire fields) update the README in the same commit.

## Verify locally

Run the static checker over the new package first:

```sh
python .agents/skills/dsh-plugin-authoring/scripts/check_plugin.py packages/<group>/<pkg>
python .agents/skills/dsh-plugin-authoring/scripts/check_plugin.py --all
```

Then the repository gates:

```sh
pnpm install
pnpm run doc-sync
pnpm run constraints && pnpm run typecheck && pnpm run lint
pnpm run build && pnpm run hygiene
```

Add the behavior-specific tests from the testing policy; before pushing, follow [dsh-pre-push-checks](../dsh-pre-push-checks/SKILL.md). The checker is a fast local pre-pass — the `pnpm` gates remain authoritative, and when they disagree, the gates win and the checker should be updated.