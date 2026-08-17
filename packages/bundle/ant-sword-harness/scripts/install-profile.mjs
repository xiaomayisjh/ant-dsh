#!/usr/bin/env node

import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import { isAbsolute, join, resolve } from 'node:path'
import { homedir } from 'node:os'
import { parseArgs } from 'node:util'

function run(command, args, cwd = process.cwd()) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: 'inherit',
    shell: process.platform === 'win32',
  })
  if (result.error !== undefined) throw result.error
  if (result.status !== 0) throw new Error(`${command} ${args.join(' ')} exited ${String(result.status)}`)
}

function dshHome() {
  const configured = process.env.DSH_HOME
  return configured === undefined || configured === '' ? join(homedir(), '.dsh') : configured
}

function installSpec(spec) {
  if (isAbsolute(spec)) return spec
  if (/^(?:\.{1,2})(?:[/\\]|$)/.test(spec)) return resolve(process.cwd(), spec)
  return spec
}

function stripBundleLayers(profileDir, packageNames) {
  const manifestPath = join(profileDir, 'package.json')
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
  const bundles = manifest.dsh?.profile?.bundles
  if (!Array.isArray(bundles)) return
  manifest.dsh.profile.bundles = bundles.filter(name => !packageNames.includes(name))
  writeFileSync(manifestPath, `${JSON.stringify(manifest, undefined, 2)}\n`)

  const persisted = JSON.parse(readFileSync(manifestPath, 'utf8')).dsh?.profile?.bundles
  const duplicates = Array.isArray(persisted) ? persisted.filter(name => packageNames.includes(name)) : []
  if (duplicates.length > 0) throw new Error(`failed to remove duplicate bundle layers: ${duplicates.join(', ')}`)
}

const { values } = parseArgs({
  options: {
    profile: { type: 'string', default: 'web' },
    bundle: { type: 'string' },
    ui: { type: 'string' },
  },
  allowPositionals: false,
})

if (values.bundle === undefined || values.ui === undefined) {
  throw new Error('usage: dsh-ant-sword-install --bundle <bundle-tarball-or-path> --ui <ui-tarball-or-path> [--profile web]')
}

const profileDir = join(dshHome(), 'profiles', values.profile)
run('dsh', ['plugin', '--profile', values.profile, 'add', values.bundle])
if (!existsSync(join(profileDir, 'package.json'))) throw new Error(`profile was not created at ${profileDir}`)
run('pnpm', ['add', '@nanmicoder/dsh-agent-teams@^0.1.4', 'dshmarket@^1.4.1', installSpec(values.ui)], profileDir)
stripBundleLayers(profileDir, ['@nanmicoder/dsh-agent-teams', 'dshmarket'])
console.log(`ant-sword: installed complete bundle into profile ${values.profile}`)
console.log(`ant-sword: start with dsh ${values.profile === 'web' ? 'web' : `--profile ${values.profile}`}`)