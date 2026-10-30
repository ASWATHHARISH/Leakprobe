"""Keep the existing private Cloud app's entry-point path, without activation modes."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.py"), run_name="__main__")
