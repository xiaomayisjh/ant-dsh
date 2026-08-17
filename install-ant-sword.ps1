param(
  [string]$Profile = 'web',
  [string]$Repository = 'xiaomayisjh/dsh-ant-sword',
  [string]$Ref = 'dev',
  [string]$Release
)

$ErrorActionPreference = 'Stop'

if ($Release) {
  if (-not $PSScriptRoot) { throw 'Local release mode requires running install-ant-sword.ps1 from a checkout, not piping it to iex.' }
  $installer = Join-Path $PSScriptRoot 'packages/bundle/ant-sword-harness/scripts/install-profile.mjs'
  if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw "Installer module not found: $installer" }
  node $installer --profile $Profile --release $Release
  if ($LASTEXITCODE -ne 0) { throw 'Profile installation failed.' }
  Write-Host "Ant Sword deployment completed. Start with: $(if ($Profile -eq 'web') { 'dsh web' } else { "dsh --profile $Profile" })"
  return
}

$workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("ant-dsh-install-" + [guid]::NewGuid().ToString('N'))
$archive = "$workspace.zip"

try {
  Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/$Repository/archive/refs/heads/$Ref.zip" -OutFile $archive
  Expand-Archive -Path $archive -DestinationPath $workspace
  $source = Get-ChildItem -Path $workspace -Directory | Select-Object -First 1
  if ($null -eq $source) { throw 'Downloaded archive contains no repository directory.' }

  Push-Location $source.FullName
  try {
    corepack pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'pnpm install failed.' }
    corepack pnpm run build
    if ($LASTEXITCODE -ne 0) { throw 'repository build failed.' }

    $artifacts = Join-Path $workspace 'artifacts'
    New-Item -ItemType Directory -Path $artifacts | Out-Null
    corepack pnpm --dir packages/bundle/ant-sword-harness pack --pack-destination $artifacts
    if ($LASTEXITCODE -ne 0) { throw 'Ant Sword bundle pack failed.' }
    corepack pnpm --dir packages/client/ui-autograph pack --pack-destination $artifacts
    if ($LASTEXITCODE -ne 0) { throw 'Autograph UI pack failed.' }

    $bundle = Get-ChildItem $artifacts -Filter 'deepseek-ai-dsh-ant-sword-harness-*.tgz' | Select-Object -First 1
    $ui = Get-ChildItem $artifacts -Filter 'deepseek-ai-dsh-client-ui-autograph-*.tgz' | Select-Object -First 1
    if ($null -eq $bundle -or $null -eq $ui) { throw 'Expected package tarballs were not produced.' }

    node packages/bundle/ant-sword-harness/scripts/install-profile.mjs --profile $Profile --bundle $bundle.FullName --ui $ui.FullName
    if ($LASTEXITCODE -ne 0) { throw 'Profile installation failed.' }
  } finally {
    Pop-Location
  }
} finally {
  Remove-Item -Recurse -Force $workspace -ErrorAction SilentlyContinue
  Remove-Item -Force $archive -ErrorAction SilentlyContinue
}

Write-Host "Ant Sword deployment completed. Start with: dsh web"