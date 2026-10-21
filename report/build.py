"""Build report.html — one file that opens by double-clicking, anywhere.

Everything the report needs is inlined: the two fonts the app uses, every
screenshot, and the stylesheet. The source lives in `report/source.html` with
`{{FONT:…}}` and `{{IMG:…}}` tokens, so the prose stays readable and this
script does the encoding.

    ./.venv/bin/python report/build.py

Screenshots are capped at 1000px wide before encoding: they are shown about
6.5 inches across on letter paper, so anything wider is bytes nobody sees.
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "report" / "source.html"
OUT = ROOT / "report.html"
# Cropped copies first: several screenshots carry a lot of empty page below
# the content, which is invisible on screen and a third of a printed page here.
CROPS = ROOT / "report" / "crops"
SHOTS = ROOT / "screenshots"
FONTS = ROOT / "frontend" / "dist" / "fonts"

MAX_WIDTH = 1000


def font(name: str) -> str:
    data = (FONTS / name).read_bytes()
    return "data:font/woff2;base64," + base64.b64encode(data).decode()


def image(name: str) -> str:
    """A screenshot as a data URI, resized down first when it is oversized."""
    path = CROPS / f"{name}.jpg"
    if not path.exists():
        path = SHOTS / f"{name}.jpg"
    if not path.exists():
        raise SystemExit(f"missing screenshot: {name}.jpg")

    with tempfile.TemporaryDirectory() as tmp:
        small = Path(tmp) / path.name
        # `sips` ships with macOS; -Z only shrinks, never enlarges.
        done = subprocess.run(
            ["sips", "-Z", str(MAX_WIDTH), str(path), "--out", str(small)],
            capture_output=True,
        )
        source = small if done.returncode == 0 and small.exists() else path
        if source is path:
            print(f"  (could not resize {name}, using it whole)")
        data = source.read_bytes()
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()


def main() -> None:
    html = SOURCE.read_text(encoding="utf-8")

    used: list[str] = []

    def swap(match: re.Match) -> str:
        kind, name = match.group(1), match.group(2)
        used.append(f"{kind}:{name}")
        return font(name) if kind == "FONT" else image(name)

    html = re.sub(r"\{\{(FONT|IMG):([^}]+)\}\}", swap, html)

    left = re.findall(r"\{\{[^}]+\}\}", html)
    assert not left, f"unreplaced tokens: {sorted(set(left))}"

    OUT.write_text(html, encoding="utf-8")
    size = OUT.stat().st_size / 1_000_000
    print(f"{OUT.relative_to(ROOT)} — {size:.1f} MB, {len(used)} assets inlined")
    for name in used:
        print(f"  {name}")


if __name__ == "__main__":
    if shutil.which("sips") is None:
        print("note: `sips` not found, screenshots will be embedded full size")
    main()
