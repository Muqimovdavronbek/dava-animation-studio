#!/usr/bin/env python3
"""Cross-platform bootstrap. All application logic remains in main.py."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    if not (3, 10) <= sys.version_info[:2] <= (3, 13):
        print("Python 3.10–3.13 kerak. Tavsiya: Python 3.12.")
        return 1
    os.chdir(ROOT)
    target = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    build = "--build" in sys.argv[1:]
    args = [arg for arg in sys.argv[1:] if arg != "--build"]
    if not target.exists():
        print("DAVA Space Studio uchun alohida muhit tayyorlanmoqda...", flush=True)
        result = subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")])
        if result.returncode:
            print("Linux: distributivingiz paket menejeridan python3-venv o'rnating.")
            return result.returncode
    modules = "import pygame, numpy" + (", PyInstaller" if build else "")
    result = subprocess.run([str(target), "-c", modules], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode:
        print("Birinchi ishga tushirish: kerakli paketlar internetdan o'rnatiladi.", flush=True)
        result = subprocess.run([str(target), "-m", "pip", "install", "--disable-pip-version-check", "-r",
                                 "requirements-build.txt" if build else "requirements.txt"])
        if result.returncode:
            print("Paketlar o'rnatilmadi. Internetni tekshirib, yana ishga tushiring.")
            return result.returncode
    return subprocess.call([str(target), "build.py" if build else "main.py", *args])


if __name__ == "__main__":
    raise SystemExit(main())
