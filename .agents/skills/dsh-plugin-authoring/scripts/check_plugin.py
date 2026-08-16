#!/usr/bin/env python3
"""Static convention checker for deepseek-harness plugin packages.

Fast local pre-pass for the conventions documented in
.agents/skills/dsh-plugin-authoring/SKILL.md. The repository `pnpm` gates
(constraints, doc-sync, package-invariants) remain authoritative; this script
exists so an authoring agent gets actionable feedback without a full install.

Usage:
    python check_plugin.py packages/<group>/<pkg> [more dirs...]
    python check_plugin.py --all

Exit code 0 means every checked package passed; 1 lists every violation found.
Pure stdlib; Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CANONICAL_MODEL_EXPERIENCE = '## Model Experience'
CANONICAL_LIMITATIONS = '## Known Limitations and Deferred Work'
MODEL_EXPERIENCE_FIELDS = (
    '#### What the model sees',
    '#### Token effect',
    '#### KV Cache effect',
)
LIMITATIONS_LIKE = re.compile(
    r'limitations?|deferred work|what is not here|^deferred\b|^non-goals?', re.IGNORECASE,
)
ALLOWED_FILES_BASE = {'lib/index.js', 'lib/invariant.js', 'lib/types/**/*.d.ts'}
# Allowlisted extras mirrored from scripts/check-workspace-constraints.ts
# (packageFileExtras and the conditional bundle entries). Keep in sync.
EXTRA_FILE_PATTERNS = (
    'cordis.patch.yml', 'lib/styles', 'lib/packaged-bin.js', 'lib/runner.js',
    'lib/types-*.js', 'assets', 'scripts/ensure-spawn-helper.mjs',
    'lib/client.js', 'lib/loader.js', 'lib/store/index.js', 'lib/startup.js',
    'lib/worker.cjs', 'lib/bin.js', 'lib/typert.host.js', 'lib/typert.host.d.ts',
    'lib/typert.client.js', 'lib/typert.client.d.ts', 'lib/typert.remote-client.js',
    'lib/typert.remote-client.d.ts',
)

# Packages audited as model-agnostic or sentence-short in
# scripts/verify-package-readme-model-experience.ts omit the structured
# section; the authoritative gate owns the list, so the checker only requires
# the two canonical headings when a Model Experience section is present.
def files_entries_recognized(files: list) -> list:
    unknown = []
    for entry in files:
        if entry in ALLOWED_FILES_BASE or entry in EXTRA_FILE_PATTERNS:
            continue
        if entry.startswith('lib/types/') and (entry.endswith('.js') or entry.endswith('.d.ts') or '**' in entry):
            continue
        unknown.append(entry)
    return unknown


@dataclass
class Violation:
    path: str
    message: str


@dataclass
class PackageReport:
    directory: Path
    violations: list[Violation] = field(default_factory=list)

    def fail(self, path: Path, message: str) -> None:
        self.violations.append(Violation(str(path), message))


def repo_root(script_path: Path) -> Path:
    # .agents/skills/dsh-plugin-authoring/scripts/check_plugin.py -> repo root
    return script_path.resolve().parents[4]


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments so json.loads accepts the repo's tsconfig files."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return re.sub(r'(^|\s)//[^\n]*', r'\1', text)


def read_json(report: PackageReport, path: Path, *, jsonc: bool = False) -> dict | None:
    try:
        text = path.read_text(encoding='utf-8')
        return json.loads(strip_jsonc(text) if jsonc else text)
    except FileNotFoundError:
        report.fail(path, 'required file is missing')
    except json.JSONDecodeError as error:
        report.fail(path, f'invalid JSON: {error}')
    return None


def heading_lines(text: str) -> list[tuple[int, str]]:
    """(line number, raw heading) pairs outside fenced code blocks."""
    headings: list[tuple[int, str]] = []
    in_fence = False
    for number, line in enumerate(text.split('\n'), start=1):
        if line.startswith('```'):
            in_fence = not in_fence
            continue
        if not in_fence and re.match(r'^#{1,6} \S', line):
            headings.append((number, line.rstrip()))
    return headings


def check_manifest(report: PackageReport, root: Path) -> None:
    manifest_path = report.directory / 'package.json'
    manifest = read_json(report, manifest_path)
    if manifest is None:
        return
    label = manifest.get('name', report.directory.name)

    if not isinstance(manifest.get('name'), str) or not manifest['name'].startswith('@deepseek-ai/dsh-'):
        report.fail(manifest_path, f'name must be @deepseek-ai/dsh-<name>, got {manifest.get("name")!r}')
    if manifest.get('private') is True:
        report.fail(manifest_path, 'release members must not set "private": true')
    if manifest.get('publishConfig', {}).get('access') != 'public':
        report.fail(manifest_path, 'publishConfig.access must be "public"')

    root_version = json.loads((root / 'package.json').read_text(encoding='utf-8'))['version']
    if manifest.get('version') != root_version:
        report.fail(manifest_path, f'version must match the root package.json ({root_version})')
    if manifest.get('type') != 'module':
        report.fail(manifest_path, '"type" must be "module"')
    if manifest.get('main') != 'lib/index.js':
        report.fail(manifest_path, '"main" must be "lib/index.js"')
    if manifest.get('types') != 'lib/types/index.d.ts':
        report.fail(manifest_path, '"types" must be "lib/types/index.d.ts"')

    exports = manifest.get('exports', {})
    dot = exports.get('.')
    if not isinstance(dot, dict) or dot.get('types') != './lib/types/index.d.ts' or dot.get('default') != './lib/index.js':
        report.fail(manifest_path, 'exports["."] must be {"types": "./lib/types/index.d.ts", "default": "./lib/index.js"}')
    invariant = exports.get('./invariant')
    if not isinstance(invariant, dict) or invariant.get('default') != './lib/invariant.js':
        report.fail(manifest_path, 'exports must expose "./invariant" -> ./lib/invariant.js (every package owns an invariant companion)')

    files = manifest.get('files')
    if not isinstance(files, list) or not {'lib/index.js', 'lib/invariant.js'} <= set(files):
        report.fail(manifest_path, 'files must include lib/index.js and lib/invariant.js')
    elif 'lib/types/**/*.d.ts' not in files:
        report.fail(manifest_path, 'files must include lib/types/**/*.d.ts')
    if isinstance(files, list):
        disallowed = [entry for entry in files if entry.startswith('src') or entry.endswith('.map')]
        if disallowed:
            report.fail(manifest_path, f'files must not publish src or declaration maps: {disallowed}')
        unknown = files_entries_recognized(files)
        if unknown:
            report.fail(manifest_path,
                        f'files entries not recognized by the constraints gate: {unknown} '
                        '(add them to scripts/check-workspace-constraints.ts in the same change)')

    peer = manifest.get('peerDependencies', {})
    dev = manifest.get('devDependencies', {})
    if '@deepseek-ai/cordis' not in peer:
        report.fail(manifest_path, '@deepseek-ai/cordis must be a peerDependency')
    if '@deepseek-ai/cordis' not in dev:
        report.fail(manifest_path, '@deepseek-ai/cordis must also be a devDependency')
    cordis_peer, cordis_dev = peer.get('@deepseek-ai/cordis'), dev.get('@deepseek-ai/cordis')
    if cordis_peer and cordis_dev and cordis_peer != cordis_dev:
        report.fail(manifest_path, f'@deepseek-ai/cordis peer ({cordis_peer}) and dev ({cordis_dev}) ranges must match')

    if label != report.directory.name and not label.startswith('@deepseek-ai/'):
        report.fail(manifest_path, f'unexpected package name {label!r}')


def check_tsconfig(report: PackageReport, root: Path) -> None:
    tsconfig_path = report.directory / 'tsconfig.json'
    tsconfig = read_json(report, tsconfig_path, jsonc=True)
    if tsconfig is None:
        return

    # Split host/client packages use a root tsconfig that only references the
    # two per-face configs (api/remotes, client/connection); the face configs
    # carry the real shape and the checker does not descend into them.
    if 'files' in tsconfig and 'extends' not in tsconfig:
        return

    # The invariants package itself cannot reference its own directory.
    is_invariants_pkg = report.directory.name == 'invariants' and 'runtime-diagnostics' in report.directory.parts

    is_client = is_client_package(report, root)
    extends = tsconfig.get('extends', '')
    base = extends.split('/')[-1]
    if base not in ('tsconfig.base.json', 'tsconfig.base.client.json'):
        report.fail(tsconfig_path, f'"extends" must resolve to tsconfig.base.json or tsconfig.base.client.json, got {extends!r}')
    options = tsconfig.get('compilerOptions', {})
    if options.get('rootDir') != 'src':
        report.fail(tsconfig_path, 'compilerOptions.rootDir must be "src"')
    if options.get('outDir') != 'lib/types':
        report.fail(tsconfig_path, 'compilerOptions.outDir must be "lib/types"')

    references = {entry.get('path') for entry in tsconfig.get('references', []) if isinstance(entry, dict)}
    if not is_invariants_pkg and not any(ref.endswith('runtime-diagnostics/invariants') for ref in references):
        report.fail(tsconfig_path, 'references must include ../../runtime-diagnostics/invariants')


def is_client_package(report: PackageReport, root: Path) -> bool:
    return 'client' in report.directory.relative_to(root).parts


def is_ui_surface_plugin(report: PackageReport) -> bool:
    """A client package whose browser half ships via ./client is a UI surface plugin.

    Its node-half apply may be an empty placeholder (packages/client/AGENTS.md),
    so the function-plugin named-export contract does not apply to it.
    """
    manifest_path = report.directory / 'package.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    return './client' in manifest.get('exports', {})


def check_source(report: PackageReport) -> None:
    src = report.directory / 'src'
    index = src / 'index.ts'
    if not index.is_file():
        report.fail(index, 'plugin entry is missing')
    else:
        text = index.read_text(encoding='utf-8')
        has_default = re.search(r'^export\s+default', text, re.MULTILINE) is not None
        named_apply = re.search(r'^export\s+(?:async\s+)?function\s+apply\b|^export\s+const\s+apply\b', text, re.MULTILINE) is not None
        if has_default and named_apply:
            report.fail(index, 'mixes a service default export with a function-plugin apply export; '
                               'the Loader drops the function plugin namespace — pick exactly one form')
        has_name = re.search(r'^export\s+const\s+name\b|^export\s*\{[^}]*\bname\b[^}]*\}', text, re.MULTILINE) is not None
        has_inject = re.search(r'^export\s+const\s+inject\b|^export\s*\{[^}]*\binject\b[^}]*\}', text, re.MULTILINE) is not None
        if named_apply and not has_default and not is_ui_surface_plugin(report):
            if not has_name:
                report.fail(index, 'function plugin must named-export `name`')

    invariant = src / 'invariant.ts'
    if not invariant.is_file():
        report.fail(invariant, 'every package owns an invariant companion (mounted through the ./invariant subpath)')
    else:
        text = invariant.read_text(encoding='utf-8')
        if 'invariants.register(' not in text and 'No runtime invariant:' not in text:
            report.fail(invariant, 'invariant companion must call ctx.invariants.register(<package name>, install) '
                                   'or state a package-specific `No runtime invariant:` reason')

    types = src / 'types.ts'
    if types.is_file():
        text = re.sub(r'//[^\n]*', '', types.read_text(encoding='utf-8'))
        # Brand constructors, error subclasses, and version/prefix constants are
        # type-domain members; the rule targets logic, not these keywords.
        logic = re.search(r'^export\s+(?:async\s+)?(?:function|const|class)\b(?!.*(?:Error|Key|Id|Version|Brand|Locator|PREFIX|_VERSION))',
                          text, re.MULTILINE)
        if logic:
            report.fail(types, 'src/types.ts appears to contain runtime logic; keep it type-only '
                               '(brand constructors, error subclasses, and version constants are exempt)')

    stray_tests = list(src.glob('**/__tests__/**'))
    if stray_tests:
        report.fail(stray_tests[0], 'tests live at package level under tests/, not src/__tests__/')


def extract_allowlist(root: Path, script: str, constant: str) -> set[str]:
    """Pull one audited package allowlist out of an authoritative gate script."""
    path = root / 'scripts' / script
    if not path.is_file():
        return set()
    text = path.read_text(encoding='utf-8')
    match = re.search(rf'const {constant}[^=]*= \{{(.*?)\}}', text, re.DOTALL)
    if match is None:
        return set()
    return set(re.findall(r"'(packages/[^']+)'", match.group(1)))


def load_readme_exemptions(root: Path) -> tuple[set[str], set[str]]:
    """Return (no_model_experience, no_limitations) as repo-relative package dirs.

    Packages on the model-experience sentence short form keep their section, so
    only NO_MODEL_EXPERIENCE_SECTION exempts the heading entirely.
    """
    no_model = extract_allowlist(root, 'verify-package-readme-model-experience.ts', 'NO_MODEL_EXPERIENCE_SECTION')
    no_limitations = extract_allowlist(root, 'verify-package-readme-limitations.ts', 'NO_LIMITATIONS')
    return no_model, no_limitations


def check_readme(report: PackageReport, root: Path) -> None:
    readme = report.directory / 'README.md'
    if not readme.is_file():
        report.fail(readme, 'package README is missing')
        return
    rel = report.directory.relative_to(root).as_posix()
    no_model_experience, no_limitations = load_readme_exemptions(root)
    text = readme.read_text(encoding='utf-8')
    headings = heading_lines(text)

    limitations = [(n, raw) for n, raw in headings if LIMITATIONS_LIKE.search(raw.lstrip('#').strip())]
    if rel in no_limitations:
        if limitations:
            report.fail(readme, f'whitelisted in NO_LIMITATIONS but carries {limitations[0][1]!r}; '
                                'drop the section or remove the allowlist entry')
    elif not limitations:
        report.fail(readme, f'missing the `{CANONICAL_LIMITATIONS}` section '
                            '(or justify an entry in NO_LIMITATIONS in scripts/verify-package-readme-limitations.ts)')
    elif len(limitations) > 1:
        report.fail(readme, f'{len(limitations)} limitations-like headings; keep exactly one `{CANONICAL_LIMITATIONS}`')
    else:
        number, raw = limitations[0]
        if raw != CANONICAL_LIMITATIONS:
            report.fail(readme, f'line {number}: non-canonical heading {raw!r}; use {CANONICAL_LIMITATIONS!r}')

    model = [raw for _, raw in headings if 'model experience' in raw.lstrip('#').strip().lower()]
    if rel in no_model_experience:
        if model:
            report.fail(readme, f'audited allowlist package must omit every Model Experience heading; found {model[0]!r}')
        model = []
    elif not model:
        report.fail(readme, f'missing {CANONICAL_MODEL_EXPERIENCE} '
                            '(structured entries, an audited short-form sentence, or a NO_MODEL_EXPERIENCE_SECTION entry)')
    elif CANONICAL_MODEL_EXPERIENCE not in model:
        report.fail(readme, f'non-canonical Model Experience heading {model[0]!r}; use exactly {CANONICAL_MODEL_EXPERIENCE!r}')

    if model and limitations:
        h2s = [raw for _, raw in headings if raw.startswith('## ')]
        if len(h2s) >= 2 and (h2s[-2] != CANONICAL_MODEL_EXPERIENCE or h2s[-1] != CANONICAL_LIMITATIONS):
            report.fail(readme, f'{CANONICAL_MODEL_EXPERIENCE} and {CANONICAL_LIMITATIONS} '
                                'must be the final two H2 sections, in that order')


# Packages legitimately referenced by both aggregates: the vendored-framework
# compaction service, the BFF webserver, and the Typert remote registry. The
# cookbook's exactly-one-aggregate rule targets ordinary packages; these three
# are repository-specific exceptions the aggregates carry deliberately.
DUAL_AGGREGATE_PACKAGES = {
    'packages/compaction/compaction',
    'packages/host/webserver',
    'packages/typert/registry',
}


def check_aggregate_registration(report: PackageReport, root: Path) -> None:
    rel = report.directory.relative_to(root).as_posix()

    # A split package (root tsconfig with files: [] + per-face references) is
    # registered through its face configs, not directly.
    root_tsconfig = report.directory / 'tsconfig.json'
    if root_tsconfig.is_file():
        data = read_json(report, root_tsconfig, jsonc=True)
        if data and 'files' in data and 'extends' not in data:
            face_hits = 0
            for aggregate in ('tsconfig.host.json', 'tsconfig.client.json'):
                path = root / aggregate
                if not path.is_file():
                    continue
                try:
                    agg = json.loads(strip_jsonc(path.read_text(encoding='utf-8')))
                except json.JSONDecodeError:
                    continue
                for entry in agg.get('references', []):
                    if isinstance(entry, dict) and entry.get('path', '').replace('\\', '/').removeprefix('./').startswith(rel + '/'):
                        face_hits += 1
            if face_hits == 0:
                report.fail(root / 'tsconfig.host.json',
                            f'{rel} (split package) has no face config referenced by tsconfig.host.json/tsconfig.client.json')
            return

    hits = []
    for aggregate in ('tsconfig.host.json', 'tsconfig.client.json'):
        path = root / aggregate
        if not path.is_file():
            continue
        try:
            data = json.loads(strip_jsonc(path.read_text(encoding='utf-8')))
        except json.JSONDecodeError:
            continue
        for entry in data.get('references', []):
            if isinstance(entry, dict) and entry.get('path', '').replace('\\', '/').removeprefix('./') == rel:
                hits.append(aggregate)
    if not hits:
        report.fail(root / 'tsconfig.host.json',
                    f'{rel} is not referenced by tsconfig.host.json or tsconfig.client.json; '
                    'register it in exactly one aggregate')
    elif len(hits) > 1 and rel not in DUAL_AGGREGATE_PACKAGES:
        report.fail(report.directory / 'tsconfig.json',
                    f'{rel} is referenced by both aggregates {hits}; an ordinary package belongs to exactly one')


def check_package(directory: Path, root: Path) -> PackageReport:
    report = PackageReport(directory=directory)
    check_manifest(report, root)
    check_tsconfig(report, root)
    check_source(report)
    check_readme(report, root)
    check_aggregate_registration(report, root)
    return report


def all_package_dirs(root: Path) -> list[Path]:
    return sorted(
        path.parent for path in (root / 'packages').glob('*/*/package.json')
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('packages', nargs='*', help='package directories, e.g. packages/core/tools')
    parser.add_argument('--all', action='store_true', help='check every packages/<group>/<pkg> directory')
    args = parser.parse_args(argv)

    root = repo_root(Path(__file__))
    if args.all:
        directories = all_package_dirs(root)
    elif args.packages:
        directories = [(root / package).resolve() for package in args.packages]
    else:
        parser.error('name at least one package directory or pass --all')

    failures = 0
    for directory in directories:
        if not (directory / 'package.json').is_file():
            print(f'{directory.relative_to(root)}: not a package directory (no package.json)', file=sys.stderr)
            failures += 1
            continue
        report = check_package(directory, root)
        for violation in report.violations:
            rel = Path(violation.path)
            try:
                rel = rel.relative_to(root)
            except ValueError:
                pass
            print(f'{report.directory.relative_to(root)}: {rel}: {violation.message}', file=sys.stderr)
        failures += len(report.violations)

    if failures:
        print(f'check_plugin: {failures} violation(s) across {len(directories)} package(s)', file=sys.stderr)
        return 1
    print(f'check_plugin: {len(directories)} package(s) checked, all conform.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))