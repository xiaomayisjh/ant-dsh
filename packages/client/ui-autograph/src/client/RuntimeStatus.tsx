import { useSyncExternalStore } from 'react'
import type { SnapshotStore } from '@deepseek-ai/dsh-client-runtime/client'
import css from './RuntimeStatus.module.css'

export type RuntimeAvailability = 'available' | 'missing' | 'configured' | 'disabled'

export interface McpRuntimeStatus {
  readonly serverName: string
  readonly transport: 'stdio' | 'streamable-http'
  readonly availability: RuntimeAvailability
  readonly target: string
  readonly installCommand?: string
  readonly installHint: string
}

export interface RedTeamRuntimeStatus {
  readonly checkedAt: number
  readonly skills: {
    readonly available: number
    readonly provider: string
    readonly state: 'ready' | 'error'
    readonly error?: string
  }
  readonly mcp: readonly McpRuntimeStatus[]
}

export interface RuntimeStatusProps {
  readonly runtimeStatus: SnapshotStore<RedTeamRuntimeStatus>
  readonly compact?: boolean
}

const STATE_LABEL: Record<RuntimeAvailability, string> = {
  available: '可用',
  configured: '已配置',
  missing: '未安装',
  disabled: '已停用',
}

export const INITIAL_RUNTIME_STATUS: RedTeamRuntimeStatus = {
  checkedAt: 0,
  skills: { available: 0, provider: 'ant-sword-skills', state: 'ready' },
  mcp: [
    ['kali', 'stdio', 'kali-server-mcp', 'pip install kali-server-mcp', '安装 kali-server-mcp，并确保命令已加入 PATH。'],
    ['metasploit', 'stdio', 'metasploitmcp', 'pip install metasploit-mcp', '安装 Metasploit MCP bridge，并先完成 Metasploit 初始化。'],
    ['hexstrike', 'stdio', 'hexstrike-ai', 'pip install hexstrike-ai', '安装 HexStrike AI MCP 服务并将命令加入 PATH。'],
    ['pentestswarm', 'stdio', 'pentestswarm', 'pip install pentestswarm', '安装 PentestSwarm，并配置编排器 API key。'],
    ['jshook', 'stdio', 'npx', 'npm install -g @jshookmcp/jshook', '需要 Node.js；也可保留 npx 按需下载模式。'],
    ['anything', 'streamable-http', 'http://localhost:23816/mcp', undefined, '启动 AnythingLLM MCP 服务。'],
    ['idapro', 'streamable-http', 'http://127.0.0.1:13337/mcp', undefined, '在 IDA Pro 中启动 MCP 插件。'],
    ['ghidra', 'streamable-http', 'http://localhost:8765/mcp', undefined, '在 Ghidra 中启动 MCP 插件。'],
  ].map(([serverName, transport, target, installCommand, installHint]) => ({
    serverName: serverName as string,
    transport: transport as 'stdio' | 'streamable-http',
    availability: 'missing' as const,
    target: target as string,
    ...(installCommand === undefined ? {} : { installCommand: installCommand as string }),
    installHint: installHint as string,
  })),
}

export function RuntimeStatus({ runtimeStatus, compact = false }: RuntimeStatusProps) {
  const snapshot = useSyncExternalStore(runtimeStatus.subscribe, runtimeStatus.getSnapshot)
  const available = snapshot.mcp.filter(item => item.availability === 'available' || item.availability === 'configured').length
  const missing = snapshot.mcp.filter(item => item.availability === 'missing').length

  if (compact) {
    return (
      <div className={css.rail} data-runtime-status>
        <span className={css.metric}>Skills <strong>{snapshot.skills.available}</strong></span>
        <span className={css.metric}>MCP <strong>{available}/{snapshot.mcp.length}</strong></span>
        {missing > 0 && <span className={css.warning}>{missing} 项待安装</span>}
      </div>
    )
  }

  return (
    <section className={css.settings} data-runtime-settings>
      <header className={css.settingsHeader}>
        <div>
          <h2>Red Team 运行环境</h2>
          <p>Skill 与 MCP 使用同一实时状态源；缺失组件不会从配置中消失。</p>
        </div>
        <div className={css.summary}>
          <span>Skills {snapshot.skills.available}</span>
          <span>MCP {available}/{snapshot.mcp.length}</span>
        </div>
      </header>
      <div className={css.skillCard} data-state={snapshot.skills.state}>
        <strong>Skills</strong>
        <span>{snapshot.skills.state === 'ready' ? `${snapshot.skills.available} 个已发现` : '加载异常'}</span>
        <small>{snapshot.skills.error ?? `Provider: ${snapshot.skills.provider}`}</small>
      </div>
      <div className={css.grid}>
        {snapshot.mcp.map(server => (
          <article key={server.serverName} className={css.card} data-state={server.availability}>
            <div className={css.cardTitle}>
              <strong>{server.serverName}</strong>
              <span>{STATE_LABEL[server.availability]}</span>
            </div>
            <code>{server.target}</code>
            <p>{server.installHint}</p>
            {server.installCommand !== undefined && <pre>{server.installCommand}</pre>}
          </article>
        ))}
      </div>
    </section>
  )
}
