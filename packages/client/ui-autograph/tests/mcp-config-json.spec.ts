import { describe, expect, it } from 'vitest'
import { formatMcpJson, parseMcpJson } from '../src/client/mcp-config-json.ts'

describe('MCP config JSON conversion', () => {
  it('imports Claude-style stdio entries and infers transport', () => {
    expect(parseMcpJson(JSON.stringify({
      mcpServers: {
        filesystem: { command: 'npx', args: ['-y', '@modelcontextprotocol/server-filesystem', '.'] },
      },
    }))).toEqual([{
      serverName: 'filesystem',
      enabled: true,
      transport: 'stdio',
      command: 'npx',
      args: ['-y', '@modelcontextprotocol/server-filesystem', '.'],
      cwd: '',
      env: {},
      toolCallTimeoutMs: 60_000,
    }])
  })

  it('imports legacy SSE and Streamable HTTP entries', () => {
    const servers = parseMcpJson(JSON.stringify({
      legacy: { type: 'sse', url: 'http://localhost:3000/sse' },
      current: { transport: 'streamable-http', url: 'http://localhost:3001/mcp' },
    }))
    expect(servers.map(server => server.transport)).toEqual(['sse', 'streamable-http'])
  })

  it('round-trips visual configuration through a named catalog', () => {
    const source = [{
      serverName: 'remote',
      enabled: true,
      transport: 'streamable-http' as const,
      url: 'https://example.test/mcp',
      headers: { Authorization: 'Bearer token' },
      toolCallTimeoutMs: 30_000,
    }]
    expect(parseMcpJson(formatMcpJson(source))).toEqual(source)
  })

  it('rejects entries without a command or URL', () => {
    expect(() => parseMcpJson('{"mcpServers":{"broken":{}}}')).toThrow('requires command or url')
  })
})
