"""Read an identical frozen assessment cache in the public demo; never cold-score it."""
import hashlib
import json
import streamlit as st

from leakprobe.ui import alert_queue
from leakprobe.ui.runtime_settings import demo_mode, monitoring_cache_directory


def monitoring_source_files():
    """Same inputs as the original cache, with platform-independent relative names."""
    root, data = alert_queue.ROOT, alert_queue.NET3_DATA
    cases = alert_queue.load_case_index()
    paths = [data / name for name in ('cases.json', 'metadata.json', 'hypotheses.json')]
    paths += [data / c['observations_file'] for c in cases]
    paths += [root / 'leakprobe' / name for name in ('net3_tools.py', 'coverage.py', 'ui/operations.py', 'ui/alert_queue.py')]
    return {p.relative_to(root).as_posix(): p for p in paths}


def load_monitoring_queue():
    if not demo_mode():
        return alert_queue.load_monitoring_queue()
    return _load_frozen_monitoring_queue(str(monitoring_cache_directory()))


@st.cache_data(show_spinner=False, max_entries=1)
def _load_frozen_monitoring_queue(directory):
    cases = alert_queue.load_case_index()
    from pathlib import Path
    index = json.loads((Path(directory) / 'index.json').read_text(encoding='utf-8'))
    sources = monitoring_source_files()
    if set(index['sources']) != set(sources) or any(
            hashlib.sha256(path.read_bytes()).hexdigest() != index['sources'][name]
            for name, path in sources.items()):
        raise ValueError('Packaged assessment sources changed. Rebuild the deployment bundle; no rescoring was performed.')
    if Path(index['cache_file']).name != index['cache_file']:
        raise ValueError('Invalid packaged assessment path.')
    path = Path(directory) / index['cache_file']
    saved = json.loads(path.read_text(encoding='utf-8'))
    rows = saved['records']
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if (saved['source_digest'] != index['legacy_source_digest'] or saved['records_digest'] != digest
            or digest != index['records_digest']
            or [r['case_id'] for r in rows] != [c['case_id'] for c in cases]
            or len({r['case_id'] for r in rows}) != len(cases)
            or any(r['prediction'] not in alert_queue.ASSESSMENTS for r in rows)):
        raise ValueError('The packaged monitoring assessments do not match the current feed. Rebuild the deployment bundle.')
    return rows
