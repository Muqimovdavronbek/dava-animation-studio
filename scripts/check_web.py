#!/usr/bin/env python3
"""Validate a buildless site without installing frontend dependencies."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def main():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'\bid="([^"]+)"', html)
    assert len(ids) == len(set(ids)), "Duplicate DOM IDs"
    for target in re.findall(r"\$\('([^']+)'\)", html):
        assert target in ids, f"Missing control: {target}"
    for href in re.findall(r'(?:href|src)="([^"]+)"', html):
        if href.startswith(("http:", "https:", "#", "data:")):
            continue
        assert not href.startswith("/"), f"Root-relative link breaks subdirectory hosting: {href}"
        assert (WEB / href).exists(), f"Missing web asset: {href}"
    manifest = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["start_url"].startswith("./")
    assert manifest["scope"].startswith("./")
    assert shutil.which("node"), "Install Node.js for JavaScript syntax checks"
    with tempfile.TemporaryDirectory() as tmp:
        for index, script in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
            path = Path(tmp) / f"inline-{index}.js"
            path.write_text(script, encoding="utf-8")
            subprocess.run(["node", "--check", str(path)], check=True)
    subprocess.run(["node", "--check", str(WEB / "sw.js")], check=True)
    print("PASS: JavaScript, service worker, manifest, DOM controls and relative asset links")


if __name__ == "__main__":
    main()
