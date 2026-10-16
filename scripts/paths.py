"""Shared folder locations for the chart scripts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"                # hand-transcribed, corrected tables (inputs)
CHARTS = ROOT / "output" / "charts"  # generated PNGs
TABLES = ROOT / "output" / "tables"  # generated CSVs
