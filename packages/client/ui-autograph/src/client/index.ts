/**
 * Autonomous-loop graph plugin, browser half: contributes one entry to the
 * conversation view slot — a React Flow view of the red-team-auto blackboard
 * (the `board` session projection) with Pause / Resume / Inject-hint controls
 * driven through the `/auto` command Remote. The tab reads its live graph via
 * the session-standard `useProjection`; it mounts like any view and renders
 * the empty state when the session has no blackboard.
 */
import type { Context } from '@deepseek-ai/cordis'
import type { SessionId } from '@deepseek-ai/dsh-client-runtime/client'
// Type-only: pulls the locale plugin's Context merge (ctx.locale).
import type {} from '@deepseek-ai/dsh-client-locale/client'
// Type-only: the 'conversation.view' SlotMap row, declared by the owning package.
import type {} from '@deepseek-ai/dsh-client-ui-conversation/client'
// Type-only: pulls the generated command Remote (ctx.remote.commands).
import type {} from '@deepseek-ai/dsh-api-remotes/client'
import { AutoGraphView, type AutoGraphActions } from './AutoGraphView.tsx'
import { en, zh, type AutographKey } from './locales.ts'

declare module '@deepseek-ai/dsh-client-ui-slots' {
  interface LocaleNamespaceMap {
    /** The autonomous graph view's copy. */
    autograph: AutographKey
  }
}

/** Dictionary namespace owned by this plugin. */
const NS = 'autograph'

/** Required services: view slot, sessions binding, command Remote, locale. */
export const inject = ['slots', 'sessions', 'remote', 'remote.commands', 'locale']

/**
 * Client plugin body: register the autonomous graph view tab. The
 * registration rides the slot service's effect wrapper, so plugin unload
 * removes the tab.
 * @param ctx - client root context.
 */
export function apply(ctx: Context): void {
  ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'ui-autograph: dictionaries')
  const t = ctx.locale.bind(NS)

  ctx.slots.inject('conversation.view', () => ctx.slots.register({
    name: 'conversation.view',
    id: 'autograph',
    order: 20,
    locale: NS,
    label: () => t('panel.title'),
    inject: (sessionId: SessionId): AutoGraphActions => {
      const run = async (input: string): Promise<string | null> => {
        const result = await ctx.remote.commands.execute(sessionId, input)
        if (!result.ok) return `${result.error.message} (${result.error.code})`
        return null
      }
      return {
        onPause: () => run('/auto pause'),
        onResume: () => run('/auto resume'),
        onHint: (text) => run(`/auto hint ${text}`),
      }
    },
  }, AutoGraphView))
}