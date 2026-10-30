"""Explicit restricted-live entrypoint; configuration alone never initiates inference."""
from pathlib import Path
import runpy

root = Path(__file__).resolve().parents[2]
bootstrap = runpy.run_path(str(root / 'deploy/app.py'))
bootstrap['configure_demo'](profile='restricted_live')
runpy.run_path(str(root / 'streamlit_app.py'), run_name='__main__')
