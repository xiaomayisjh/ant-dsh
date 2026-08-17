#!/usr/bin/env bash
set -euo pipefail

PROFILE="${PROFILE:-web}"
REPOSITORY="${REPOSITORY:-xiaomayisjh/dsh-ant-sword}"
REF="${REF:-dev}"
RELEASE="${RELEASE:-}"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --repository) REPOSITORY="$2"; shift 2 ;;
    --ref) REF="$2"; shift 2 ;;
    --release) RELEASE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "$RELEASE" ]]; then
  command -v node >/dev/null 2>&1 || { echo "Required command not found: node" >&2; exit 1; }
  installer="$SCRIPT_DIR/packages/bundle/ant-sword-harness/scripts/install-profile.mjs"
  [[ -f "$installer" ]] || { echo "Installer module not found: $installer" >&2; exit 1; }
  node "$installer" --profile "$PROFILE" --release "$RELEASE"
  if [[ "$PROFILE" == web ]]; then start_command='dsh web'; else start_command="dsh --profile $PROFILE"; fi
  echo "Ant Sword deployment completed. Start with: $start_command"
  exit 0
fi

for command in node corepack curl; do
  command -v "$command" >/dev/null 2>&1 || { echo "Required command not found: $command" >&2; exit 1; }
done
command -v dsh >/dev/null 2>&1 || { echo "Required command not found: dsh" >&2; exit 1; }

workspace="$(mktemp -d "${TMPDIR:-/tmp}/ant-dsh-install.XXXXXX")"
cleanup() { rm -rf "$workspace"; }
trap cleanup EXIT INT TERM

archive="$workspace/source.zip"
source_root="$workspace/source"
mkdir -p "$source_root"
curl --fail --location --silent --show-error \
  "https://github.com/$REPOSITORY/archive/refs/heads/$REF.zip" \
  --output "$archive"

if command -v unzip >/dev/null 2>&1; then
  unzip -q "$archive" -d "$source_root"
elif command -v python3 >/dev/null 2>&1; then
  python3 -m zipfile -e "$archive" "$source_root"
else
  echo "Required archive extractor not found: install unzip or Python 3" >&2
  exit 1
fi

source_dir="$(find "$source_root" -mindepth 1 -maxdepth 1 -type d -print -quit)"
[[ -n "$source_dir" ]] || { echo "Downloaded archive contains no repository directory" >&2; exit 1; }

cd "$source_dir"
corepack pnpm install --frozen-lockfile
corepack pnpm run build

artifacts="$workspace/artifacts"
mkdir -p "$artifacts"
corepack pnpm --dir packages/bundle/ant-sword-harness pack --pack-destination "$artifacts"
corepack pnpm --dir packages/client/ui-autograph pack --pack-destination "$artifacts"

bundle="$(find "$artifacts" -maxdepth 1 -name 'deepseek-ai-dsh-ant-sword-harness-*.tgz' -print -quit)"
ui="$(find "$artifacts" -maxdepth 1 -name 'deepseek-ai-dsh-client-ui-autograph-*.tgz' -print -quit)"
[[ -n "$bundle" && -n "$ui" ]] || { echo "Expected package tarballs were not produced" >&2; exit 1; }

node packages/bundle/ant-sword-harness/scripts/install-profile.mjs \
  --profile "$PROFILE" \
  --bundle "$bundle" \
  --ui "$ui"

echo "Ant Sword deployment completed. Start with: $([[ "$PROFILE" == web ]] && echo 'dsh web' || echo "dsh --profile $PROFILE")"