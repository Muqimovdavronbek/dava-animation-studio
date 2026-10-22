#!/usr/bin/env python3
"""Run on the target OS, or let the included GitHub Actions matrix build both."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile",
            "--name", "DAVA_Space_Studio", "--add-data", f"assets{os.pathsep}assets",
            "--exclude-module", "tkinter", "--exclude-module", "matplotlib",
            "--exclude-module", "IPython", "--exclude-module", "pytest"]
    if sys.platform == "win32":
        args += ["--windowed"]
    args += ["main.py"]
    subprocess.run(args, check=True)
    target = ROOT / "dist" / ("DAVA_Space_Studio.exe" if os.name == "nt" else "DAVA_Space_Studio")
    if os.name != "nt":
        run_file = target.with_suffix(".run")
        shutil.copy2(target, run_file)
        run_file.chmod(0o755)
    print(f"\nTayyor: {target}")


if __name__ == "__main__":
    main()
