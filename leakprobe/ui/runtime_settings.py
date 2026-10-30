"""Hosting policy and storage locations; no detector settings or scientific inputs."""
import os
from pathlib import Path
import tempfile
import uuid

from leakprobe.paths import OUTPUTS


def enabled(name):
    return os.getenv(name, '').strip().lower() in ('1', 'true', 'yes')


def demo_mode():
    return enabled('LEAKPROBE_DEMO_MODE')


def live_ai_enabled():
    # The public demo never accepts paid requests, even with an accidentally present key.
    return enabled('LEAKPROBE_ENABLE_LIVE_AI') and not demo_mode()


def review_database():
    if demo_mode():
        import streamlit as st
        if 'leakprobe_review_session' not in st.session_state:
            st.session_state['leakprobe_review_session'] = uuid.uuid4().hex
        return Path(tempfile.gettempdir()) / 'leakprobe-demo' / st.session_state['leakprobe_review_session'] / 'reviews.sqlite3'
    return Path(os.getenv('LEAKPROBE_REVIEW_DB') or OUTPUTS / 'operations' / 'alerts.sqlite3')


def monitoring_cache_directory():
    return Path(os.getenv('LEAKPROBE_MONITORING_CACHE') or OUTPUTS / 'operations')


def saved_trace_directories(output_directory=OUTPUTS):
    paths = [Path(output_directory) / 'traces']
    if os.getenv('LEAKPROBE_SAVED_TRACES'):
        paths.append(Path(os.environ['LEAKPROBE_SAVED_TRACES']))
    return list(dict.fromkeys(paths))
