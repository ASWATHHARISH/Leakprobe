"""Community Cloud entry point for the offline, session-isolated product demo."""
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def configure_demo(profile='offline'):
    if profile not in ('offline', 'restricted_live'):
        raise ValueError('Unknown deployment profile.')
    os.environ['LEAKPROBE_DEPLOYMENT_PROFILE'] = profile
    os.environ.setdefault('LEAKPROBE_DEMO_MODE', '1')
    os.environ.setdefault('LEAKPROBE_ENABLE_LIVE_AI', '0')
    os.environ.setdefault('LEAKPROBE_SAVED_TRACES', str(ROOT / 'demo_assets' / 'traces'))
    os.environ.setdefault('LEAKPROBE_MONITORING_CACHE', str(ROOT / 'demo_assets' / 'monitoring_cache'))


if __name__ == '__main__':
    configure_demo()
    runpy.run_path(str(ROOT / 'streamlit_app.py'), run_name='__main__')
