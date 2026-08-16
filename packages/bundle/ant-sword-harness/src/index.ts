/**
 * @deepseek-ai/dsh-ant-sword-harness — a security-research profile bundle. Its
 * composition is the `cordis.patch.yml` declared by `dsh.bundle.patch`: this
 * single Cordis plugin row mounts the bundled reverse/CTF skill pack and the
 * self-contained rewind capability, and the patch additionally mounts the
 * third-party agent-teams and plugin-market bundles.
 *
 * @module @deepseek-ai/dsh-ant-sword-harness
 */

import type { Context } from '@deepseek-ai/cordis'
import z from '@deepseek-ai/schemastery'
import { skillProvider } from './skills.ts'
import { syncRedTeamPreset, syncRedTeamAutoPreset } from './preset-sync.ts'
import { applyRewind, RewindConfigSchema } from './rewind/index.ts'
import type { RewindPluginConfig } from './rewind/index.ts'
import { applyAutoLoop, AutoLoopConfigSchema } from './auto/index.ts'
import type { AutoLoopConfig } from './auto/index.ts'

/** Cordis plugin name. */
export const name = 'ant-sword-harness'

/** Services required by the bundled skill provider, rewind, and the auto loop. */
export const inject = ['skills', 'sessions', 'storageDomain', 'commands', 'tools', 'agents']

/** Plugin config: rewind under `rewind`, the autonomous loop under `autoLoop`. */
export interface Config {
  /** Rewind configuration; omitted mounts rewind with its defaults. */
  rewind?: RewindPluginConfig
  /** Auto-loop configuration; omitted mounts the loop with its defaults. */
  autoLoop?: AutoLoopConfig
  /** Sync the bundled presets into the user preset root. Default true. */
  syncRedTeamPreset?: boolean
}

/** Schemastery validation for {@link Config}. */
export const Config: z<Config> = z.object({
  rewind: RewindConfigSchema,
  autoLoop: AutoLoopConfigSchema,
  syncRedTeamPreset: z.boolean(),
})

/**
 * Mount the bundled skill pack, the rewind capability, and the red-team preset.
 * All register on their owning services and dispose with ctx.
 * @param ctx - plugin context carrying skills, sessions, storageDomain, commands.
 * @param config - validated plugin config.
 */
export function apply(ctx: Context, config: Config): void {
  ctx.skills.registerProvider(() => skillProvider)
  applyRewind(ctx, config.rewind ?? {})
  applyAutoLoop(ctx, config.autoLoop ?? {})
  if (config.syncRedTeamPreset ?? true) {
    // Materialize both presets into the harness's writable preset root so the
    // roster discovers them; a sync failure never blocks the composition.
    void syncRedTeamPreset().catch(() => undefined)
    void syncRedTeamAutoPreset().catch(() => undefined)
  }
}
