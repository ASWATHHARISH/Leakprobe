"""Read-only standalone release checker. Uses no providers or scientific scoring."""
import hashlib
import json
from pathlib import Path
import re

DOCUMENTATION_OVERRIDES = {'README.md', 'docs/DEPLOYMENT.md'}
INTEGRATION_OVERRIDES = {'.gitignore', 'deploy/app.py', 'leakprobe/ui/ai_service.py',
                         'leakprobe/ui/employee_dashboard.py', 'leakprobe/ui/runtime_settings.py'}
SECRET_PATTERNS = (
    re.compile(rb'\b(?:sk-|nvapi-)[A-Za-z0-9_-]{20,}'),
    re.compile(rb'Bearer\s+[A-Za-z0-9._-]{24,}', re.I),
    re.compile(rb'["\'](?:api_key|access_token|password|authorization)["\']\s*:\s*["\'][^"\']{8,}["\']', re.I),
)


def checked_path(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or '.git' in relative.parts:
        raise ValueError('Unsafe manifest path: ' + name)
    path = root / relative
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Missing or unsafe release file: ' + name)
    return path


def check_public_file(name, payload):
    path = Path(name)
    if (path.suffix.lower() in ('.db', '.sqlite', '.sqlite3', '.pem', '.key', '.pkl', '.joblib')
            or path.name == 'secrets.toml'
            or path.name.startswith('.env') and path.name != '.env.example'):
        raise ValueError('Private file in release: ' + name)
    if any(pattern.search(payload) for pattern in SECRET_PATTERNS):
        raise ValueError('Possible credential in ' + name + '; values are not printed.')


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'release-manifest.json').read_text(encoding='utf-8'))
    upstream_path = checked_path(root, 'deploy/upstream-release-manifest.json')
    if hashlib.sha256(upstream_path.read_bytes()).hexdigest() != manifest['source_manifest_sha256']:
        raise ValueError('Upstream manifest hash changed.')
    upstream = json.loads(upstream_path.read_text(encoding='utf-8'))
    for name, row in manifest['files'].items():
        payload = checked_path(root, name).read_bytes()
        check_public_file(name, payload)
        if len(payload) != row['bytes'] or hashlib.sha256(payload).hexdigest() != row['sha256']:
            raise ValueError('Release integrity failure: ' + name)
    preserved = 0
    for name, row in upstream['files'].items():
        if name in DOCUMENTATION_OVERRIDES | INTEGRATION_OVERRIDES:
            continue
        if hashlib.sha256(checked_path(root, name).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Verified upstream file changed: ' + name)
        preserved += 1
    # Local Git/virtualenv/bytecode directories are not deployable application files.
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if any(part in ('.git', '.venv', '__pycache__') for part in relative.parts):
            continue
        if path.is_file() and relative.as_posix() not in {*manifest['files'], 'release-manifest.json'}:
            raise ValueError('Unexpected release file: ' + relative.as_posix())
    cases = json.loads((root / 'data/net3_full_high_signal/cases.json').read_text())
    index = json.loads((root / 'demo_assets/monitoring_cache/index.json').read_text())
    cache = json.loads(checked_path(root, 'demo_assets/monitoring_cache/' + index['cache_file']).read_text())
    records = cache['records']
    digest = hashlib.sha256(json.dumps(records, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if (digest != index['records_digest'] or digest != cache['records_digest']
            or cache['source_digest'] != index['legacy_source_digest']
            or len(cases) != 500 or len({c['case_id'] for c in cases}) != 500
            or [c['case_id'] for c in cases] != [r['case_id'] for r in records]):
        raise ValueError('Monitoring case/cache identity failure.')
    for name, sha in index['sources'].items():
        if hashlib.sha256(checked_path(root, name).read_bytes()).hexdigest() != sha:
            raise ValueError('Portable source binding failure: ' + name)
    counts = {name: sum(r['prediction'] == name for r in records) for name in ('leak', 'normal', 'uncertain')}
    if counts != {'leak': 417, 'normal': 83, 'uncertain': 0}:
        raise ValueError('Monitoring assessments changed.')
    traces = list((root / 'demo_assets/traces').glob('*.json'))
    if len(traces) != 5:
        raise ValueError('Expected all five original investigation traces.')
    return {'passed': True, 'files_verified': len(manifest['files']), 'upstream_files_preserved': preserved,
            'source_files': len(upstream['files']), 'documentation_overrides': sorted(DOCUMENTATION_OVERRIDES),
            'authorized_integration_overrides': sorted(INTEGRATION_OVERRIDES),
            'records': 500, 'assessments': counts, 'traces': len(traces),
            'bytes': sum(row['bytes'] for row in manifest['files'].values()), 'secrets_or_databases': 0}


if __name__ == '__main__':
    print(json.dumps(verify(Path(__file__).resolve().parents[1]), indent=2))
