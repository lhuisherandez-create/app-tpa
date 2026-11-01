"""Compatibilidad: delega toda la preparación a la configuración T05 vigente."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name("render_setup_v2.py")), run_name="__main__")
