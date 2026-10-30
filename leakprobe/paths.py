"""Repository paths shared by the package modules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"
NET3_DATA = DATA / "net3_full_high_signal"
FULL_PRESSURE_CHANNELS = 92
FULL_FLOW_CHANNELS = 117

