#!/usr/bin/env python3
"""DAVA Space Studio — one application source for Windows and Linux.

Software rendered ASCII space art; no OpenGL, account, network or API key.
The scenes are artistic illustrations, not physical or astronomical simulations.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np
import pygame as pg

VERSION = "1.0.0"
BASE = (1440, 900)
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
ASSETS = ROOT / "assets"
BG = (9, 13, 19)
PANEL = (14, 20, 28)
LINE = (32, 42, 54)
INK = (226, 233, 240)
MUTED = (123, 140, 159)
ACCENT = (126, 237, 202)
SCENES = [
    ("Qora tuynuk", "Hodisa ufqi", "Gravitatsiya ritmi", "BH-01"),
    ("Halqali sayyora", "Sokin orbita", "Halqalar geometriyasi", "PL-02"),
    ("Spiral galaktika", "Yulduzlar raqsi", "Cheksizlikka bir nazar", "GX-03"),
]
THEMES = [
    ("Quyosh", (255, 162, 77)),
    ("Yalpiz", (93, 233, 194)),
    ("Muz", (109, 183, 255)),
    ("Binafsha", (198, 137, 255)),
]
RAMP = " .,:;irsXA253hMHGS#9B&@"


def config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) if sys.platform == "win32" else Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "DavaSpaceStudio" / "settings.json"


def export_dir() -> Path:
    # XDG user-dirs may translate Pictures, e.g. "Rasmlar".
    pictures = Path.home() / "Pictures"
    if sys.platform != "win32":
        userdirs = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "user-dirs.dirs"
        try:
            for line in userdirs.read_text(encoding="utf-8").splitlines():
                if line.startswith("XDG_PICTURES_DIR="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    candidate = Path(value.replace("$HOME", str(Path.home())))
                    if candidate.is_absolute():
                        pictures = candidate
        except OSError:
            pass
    return pictures / "DAVA Space Studio"


@dataclass
class Settings:
    scene: int = 0
    theme: int = 0
    speed: float = 1.0
    zoom: float = 1.0
    tilt: float = 0.28
    quality: int = 1
    glow: bool = True
    stars: bool = True
    dots: bool = False

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        settings = cls()
        try:
            data = json.loads((path or config_path()).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return settings
            ranges = {"scene": (0, 2), "theme": (0, 3), "speed": (0.1, 3.0),
                      "zoom": (0.55, 1.8), "tilt": (0.12, 0.7), "quality": (0, 2)}
            for field in fields(cls):
                value = data.get(field.name)
                if field.name in ranges and type(value) in (int, float) and math.isfinite(value):
                    low, high = ranges[field.name]
                    value = max(low, min(high, value))
                    setattr(settings, field.name, int(value) if field.name in ("scene", "theme", "quality") else float(value))
                elif field.name not in ranges and type(value) is bool:
                    setattr(settings, field.name, value)
        except (OSError, ValueError, TypeError):
            pass
        return settings

    def save(self, path: Path | None = None) -> None:
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        temporary.replace(path)


class SpaceEngine:
    """Deterministic vectorized scenes. Rendering has no GPU dependency."""
    def __init__(self) -> None:
        self._grids: dict[tuple[int, int, float], tuple] = {}

    def grid(self, cols: int, rows: int, aspect: float) -> tuple:
        key = (cols, rows, round(aspect, 5))
        if key not in self._grids:
            y, x = np.mgrid[-1.4:1.4:complex(rows), -1.4*aspect:1.4*aspect:complex(cols)]
            rng = np.random.default_rng(247)
            stars = np.zeros((rows, cols), dtype=np.float32)
            mask = rng.random((rows, cols)) < 0.018
            stars[mask] = rng.uniform(0.025, 0.19, int(mask.sum()))
            self._grids[key] = (x.astype(np.float32), y.astype(np.float32), stars)
        return self._grids[key]

    def sample(self, cols: int, rows: int, aspect: float, t: float, s: Settings, orbit: float = 0.0) -> np.ndarray:
        x0, y0, stars = self.grid(cols, rows, aspect)
        x, y = x0 / s.zoom, y0 / s.zoom
        angle = orbit
        x, y = x * math.cos(angle) + y * math.sin(angle), -x * math.sin(angle) + y * math.cos(angle)
        r = np.sqrt(x*x + y*y) + 1e-5
        if s.scene == 0:
            q = s.tilt
            disk_r = np.sqrt(x*x + (y/q)**2) + 1e-5
            phi = np.arctan2(y/q, x)
            turbulence = (0.72 + 0.16*np.sin(34*disk_r - 2.5*t + 5*phi)
                          + 0.10*np.sin(69*disk_r + 10*phi - 3.1*t))
            disk = np.exp(-((disk_r-1.24)/0.93)**2) * turbulence
            disk *= (disk_r > 0.81) & (disk_r < 2.75)
            disk *= 0.75 + 0.35*np.tanh(-x)
            # A curved rear image and a narrow photon ring evoke lensing.
            lens = np.exp(-((r-0.78)/0.105)**2) * (0.7 + 0.2*np.sin(48*r + np.arctan2(y, x)*4 - t))
            lens *= np.where(y < 0, 0.88, 0.48)
            photon = np.exp(-((r-0.666)/0.026)**2)*0.83
            haze = np.exp(-((r-0.80)/0.28)**2)*0.09
            light = np.maximum(disk, lens) + photon + haze
            light[r < 0.635] = 0
            shadow = r < 0.64
        elif s.scene == 1:
            # A rotating striped planet and independently shaded tilted rings.
            radius = 0.68
            z = np.sqrt(np.clip(radius*radius-r*r, 0, None))
            longitude = np.arctan2(x, z+1e-4) + t*0.26
            band = 0.65 + 0.13*np.sin(47*y+1.4*np.sin(longitude*3))
            band += 0.07*np.sin(103*y + longitude*2)
            shade = np.clip((-x*0.6-y*0.35+z*1.3)/radius, 0.06, 1.0)
            planet = band*shade*(r < radius)
            ring_r = np.sqrt(x*x + (y/s.tilt)**2)
            rings = np.exp(-((ring_r-1.18)/0.42)**6)*(0.46+0.16*np.sin(ring_r*90))
            rings *= (ring_r > 0.87) & (ring_r < 1.72)
            rings *= 1 - 0.82*np.exp(-((ring_r-1.28)/0.025)**2)
            light = np.maximum(planet, rings * ((r > radius) | (y > 0.12)))
            shadow = r < radius
        else:
            q = 0.57 + s.tilt*0.4
            rr = np.sqrt(x*x+(y/q)**2) + 0.04
            phi = np.arctan2(y/q, x)
            arm = np.cos(3*phi-5.5*np.log(rr)-t*0.30)
            arm = np.clip((arm-0.15)/0.85, 0, 1)**2
            flecks = 0.6+0.4*np.sin(x*101+y*37)*np.sin(y*89-x*21)
            light = np.exp(-rr*1.1)*(0.07+0.68*arm*flecks)
            light += np.exp(-(rr/0.27)**2)*0.95
            light *= rr < 2.5
            shadow = np.zeros_like(r, dtype=bool)
        if s.stars:
            twinkle = 0.85 + 0.15*np.sin(t*0.6+x0*19+y0*7)
            light = np.maximum(light, stars*twinkle*(~shadow))
        return np.clip(light, 0, 1).astype(np.float32)


class Renderer:
    def __init__(self) -> None:
        self.engine = SpaceEngine()
        self.atlases: dict[tuple, tuple] = {}
        self.last_text = ""

    def atlas(self, size: int, theme: int) -> tuple:
        key = (size, theme)
        if key not in self.atlases:
            font = pg.font.Font(str(ASSETS / "Mono.ttf"), size)
            cw, ch = font.size("M")[0], font.get_linesize()
            base = np.array(THEMES[theme][1], dtype=float)
            colors = []
            for i in range(32):
                level = i/31
                color = base*(0.36+0.64*math.sqrt(level))
                color += (255-color)*max(0, (level-0.58)/0.42)*0.82
                colors.append(tuple(color.astype(int)))
            glyphs = [[font.render(c, True, color) for c in RAMP] for color in colors]
            self.atlases[key] = (cw, ch, colors, glyphs)
        return self.atlases[key]

    def render(self, size: tuple[int, int], t: float, settings: Settings, orbit: float = 0.0) -> pg.Surface:
        width, height = size
        font_size = (15, 12, 10)[settings.quality]
        cw, ch, colors, glyphs = self.atlas(font_size, settings.theme)
        cols, rows = max(8, width//cw), max(8, height//ch)
        values = self.engine.sample(cols, rows, width/height, t, settings, orbit)
        surface = pg.Surface(size)
        surface.fill((7, 11, 17))
        levels = np.minimum((values*31).astype(np.int32), 31)
        chars = np.minimum((np.power(values, 0.72)*(len(RAMP)-1)).astype(np.int32), len(RAMP)-1)
        encoded = np.frombuffer(RAMP.encode("ascii"), dtype=np.uint8)[chars]
        self.last_text = "\n".join(row.tobytes().decode("ascii") for row in encoded)
        if settings.glow:
            rgb = np.array([THEMES[settings.theme][1]], dtype=np.float32)[None, ...]
            glow = np.clip(values[..., None]**1.8 * rgb*0.20, 0, 255).astype(np.uint8)
            low = pg.surfarray.make_surface(glow.transpose(1, 0, 2))
            low = pg.transform.smoothscale(low, (max(1, width//8), max(1, height//8)))
            surface.blit(pg.transform.smoothscale(low, size), (0, 0), special_flags=pg.BLEND_RGB_ADD)
        ox, oy = (width-cols*cw)//2, (height-rows*ch)//2
        yy, xx = np.nonzero(chars)
        if settings.dots:
            for x, y, level, value in zip(xx.tolist(), yy.tolist(), levels[yy, xx].tolist(), values[yy, xx].tolist()):
                pg.draw.circle(surface, colors[level], (ox+x*cw+cw//2, oy+y*ch+ch//2), max(1, int(value*cw*0.35)))
        else:
            surface.blits([(glyphs[level][char], (ox+x*cw, oy+y*ch)) for x, y, level, char in
                           zip(xx.tolist(), yy.tolist(), levels[yy, xx].tolist(), chars[yy, xx].tolist())], doreturn=False)
        return surface


class App:
    def __init__(self, settings: Settings | None = None, *, headless: bool = False, output_dir: Path | None = None) -> None:
        pg.display.init()
        pg.font.init()
        self.screen = pg.display.set_mode(BASE, pg.RESIZABLE)
        pg.display.set_caption(f"DAVA Space Studio {VERSION}")
        self.canvas = pg.Surface(BASE)
        self.settings = settings or Settings.load()
        self.renderer = Renderer()
        self.fonts: dict[tuple, pg.font.Font] = {}
        self.text_cache: dict[tuple, pg.Surface] = {}
        self.clock = pg.time.Clock()
        self.running = True
        self.paused = False
        self.fullscreen = False
        self.help = False
        self.clean = False
        self.t = 8.0
        self.orbit = 0.0
        self.dragging: str | None = None
        self.drag_anchor = (0, 0)
        self.mouse = (0, 0)
        self.buttons: list[tuple[pg.Rect, str, object]] = []
        self.sliders: dict[str, tuple[pg.Rect, float, float]] = {}
        self.toast = ""
        self.toast_until = 0.0
        self.art_rect = pg.Rect(281, 214, 814, 474)
        self.last_art: pg.Surface | None = None
        self.headless = headless
        self.output_dir = output_dir or export_dir()
        self.frame_ms = 0.0
        icon = pg.Surface((64, 64), pg.SRCALPHA)
        pg.draw.circle(icon, ACCENT, (32, 32), 22, 4)
        pg.draw.ellipse(icon, (255, 166, 84), (4, 23, 56, 18), 3)
        pg.display.set_icon(icon)

    def font(self, size: int, bold: bool = False, mono: bool = False) -> pg.font.Font:
        key = (size, bold, mono)
        if key not in self.fonts:
            self.fonts[key] = pg.font.Font(str(ASSETS / ("Mono.ttf" if mono else "Interface-Bold.ttf" if bold else "Interface.ttf")), size)
        return self.fonts[key]

    def text(self, value: str, x: int, y: int, size: int = 14, color: tuple = INK, bold: bool = False, mono: bool = False) -> None:
        self.canvas.blit(self.label(value, size, color, bold, mono), (x, y))

    def label(self, value: str, size: int, color: tuple, bold: bool = False, mono: bool = False) -> pg.Surface:
        key = (value, size, color, bold, mono)
        if key not in self.text_cache:
            if len(self.text_cache) > 512:
                self.text_cache.clear()
            self.text_cache[key] = self.font(size, bold, mono).render(value, True, color)
        return self.text_cache[key]

    def panel(self, rect: tuple, fill: tuple = PANEL, border: tuple = LINE, radius: int = 14) -> pg.Rect:
        rect = pg.Rect(rect)
        pg.draw.rect(self.canvas, fill, rect, border_radius=radius)
        pg.draw.rect(self.canvas, border, rect, 1, border_radius=radius)
        return rect

    def button(self, rect: tuple, label: str, action: str, value: object = None, active: bool = False, primary: bool = False, size: int = 13) -> None:
        rect = pg.Rect(rect)
        hovered = rect.collidepoint(self.mouse)
        fill = ACCENT if primary else (28, 44, 45) if active else (29, 39, 51) if hovered else (19, 27, 37)
        self.panel(rect, fill, ACCENT if active else fill, 8)
        rendered = self.label(label, size, BG if primary else ACCENT if active else INK, primary or active)
        self.canvas.blit(rendered, rendered.get_rect(center=rect.center))
        self.buttons.append((rect, action, value))

    def slider(self, name: str, label: str, y: int, low: float, high: float, display: str) -> None:
        x, w = 1148, 240
        value = getattr(self.settings, name)
        self.text(label, x, y, 13, MUTED)
        rendered = self.font(13, mono=True).render(display, True, INK)
        self.canvas.blit(rendered, (x+w-rendered.get_width(), y))
        rect = pg.Rect(x, y+29, w, 18)
        cy = rect.centery
        pg.draw.line(self.canvas, (40, 51, 65), (x, cy), (x+w, cy), 3)
        end = x+int((value-low)/(high-low)*w)
        pg.draw.line(self.canvas, ACCENT, (x, cy), (end, cy), 3)
        pg.draw.circle(self.canvas, ACCENT, (end, cy), 6)
        pg.draw.circle(self.canvas, BG, (end, cy), 2)
        self.sliders[name] = (rect.inflate(8, 12), low, high)

    def toggle(self, y: int, label: str, key: str) -> None:
        value = getattr(self.settings, key)
        self.text(label, 1148, y, 13, MUTED)
        rect = pg.Rect(1350, y-1, 38, 21)
        pg.draw.rect(self.canvas, (42, 94, 80) if value else (40, 49, 60), rect, border_radius=11)
        pg.draw.circle(self.canvas, ACCENT if value else MUTED, (rect.x+(27 if value else 11), rect.centery), 7)
        self.buttons.append((rect.inflate(8, 10), "toggle", key))

    def scene_icon(self, x: int, y: int, scene: int, color: tuple) -> None:
        if scene == 0:
            pg.draw.circle(self.canvas, color, (x, y), 13, 2)
            pg.draw.ellipse(self.canvas, color, (x-22, y-5, 44, 10), 1)
            pg.draw.circle(self.canvas, (9, 15, 22), (x, y), 9)
        elif scene == 1:
            pg.draw.circle(self.canvas, color, (x, y), 11, 1)
            pg.draw.ellipse(self.canvas, color, (x-22, y-7, 44, 14), 2)
        else:
            for a in range(3):
                pts = [(x+int((2+i*0.40)*math.cos(i*0.16+a*2.094)), y+int((2+i*0.40)*math.sin(i*0.16+a*2.094)*0.65)) for i in range(42)]
                pg.draw.lines(self.canvas, color, False, pts, 1)
            pg.draw.circle(self.canvas, color, (x, y), 3)

    def draw(self) -> None:
        started = time.perf_counter()
        self.buttons.clear()
        self.sliders.clear()
        c = self.canvas
        c.fill(BG)
        if self.clean:
            rect = pg.Rect(0, 0, *BASE)
            self.last_art = self.renderer.render(rect.size, self.t, self.settings, self.orbit)
            c.blit(self.last_art, rect)
            self.text("DAVA / SPACE STUDIO", 34, 30, 13, MUTED, mono=True)
            self.text("Tab: panelga qaytish", 34, 850, 12, MUTED)
            return
        # Header.
        pg.draw.circle(c, ACCENT, (51, 55), 17, 2)
        pg.draw.ellipse(c, ACCENT, (27, 49, 48, 12), 2)
        pg.draw.circle(c, BG, (51, 55), 9)
        self.text("DAVA", 83, 29, 25, INK, True)
        self.text("S P A C E   S T U D I O", 84, 62, 10, MUTED)
        self.text("Belgilar. Harakat. Cheksizlik.", 390, 44, 15, MUTED)
        self.button((1057, 34, 75, 40), "Yordam", "help")
        self.button((1144, 34, 95, 40), "Toza ekran", "clean")
        self.button((1251, 34, 161, 40), "PNG saqlash  ↗", "export", "png", primary=True)
        pg.draw.line(c, LINE, (28, 100), (1412, 100))

        # Left library.
        self.panel((28, 124, 222, 698))
        self.text("KOINOT KUTUBXONASI", 47, 146, 10, MUTED, True)
        for i, scene in enumerate(SCENES):
            y = 183+i*82
            active = i == self.settings.scene
            rect = pg.Rect(41, y, 196, 70)
            self.panel(rect, (24, 39, 40) if active else PANEL, (45, 81, 74) if active else PANEL, 10)
            self.scene_icon(73, y+34, i, ACCENT if active else MUTED)
            self.text(scene[0], 104, y+17, 12, INK if active else MUTED, active)
            self.text(scene[3]+"   /   0"+str(i+1), 105, y+39, 9, ACCENT if active else (84, 103, 122), mono=True)
            self.buttons.append((rect, "scene", i))
        pg.draw.line(c, LINE, (47, 449), (231, 449))
        self.text("KODDAN SAN'ATGA", 47, 473, 10, ACCENT, True)
        self.text("Har bir belgi —", 47, 501, 15, INK)
        self.text("koinotning bir bo'lagi.", 47, 524, 14, INK)
        self.text("Rang va harakatni tanlang.", 47, 562, 11, MUTED)
        self.text("O'z koinotingizni yarating.", 47, 582, 11, MUTED)
        self.panel((44, 630, 190, 171), (11, 17, 24), (25, 35, 47), 9)
        self.text("TEZKOR TUGMALAR", 58, 646, 9, MUTED, True)
        for n, (key, label) in enumerate([("SPACE", "Pauza / davom"), ("1 / 2 / 3", "Sahnani tanlash"), ("S", "PNG saqlash"), ("F11", "To'liq ekran")]):
            yy = 674+n*27
            self.text(key, 58, yy, 10, ACCENT, mono=True)
            self.text(label, 118, yy, 10, MUTED)

        # Main artwork viewport.
        self.panel((270, 124, 835, 698), (10, 16, 23))
        scene = SCENES[self.settings.scene]
        self.text(scene[3]+"  /  GENERATIV SAN'AT", 295, 147, 10, MUTED, mono=True)
        self.text(scene[1], 295, 174, 25, INK, True)
        pg.draw.circle(c, (248, 180, 94) if self.paused else ACCENT, (1000, 160), 3)
        self.text("PAUZA" if self.paused else "JONLI", 1011, 152, 10, MUTED, mono=True)
        self.last_art = self.renderer.render(self.art_rect.size, self.t, self.settings, self.orbit)
        c.blit(self.last_art, self.art_rect)
        # Fine framing marks, kept outside the illustration.
        for x, y, dx, dy in [(293, 228, 1, 1), (1081, 228, -1, 1), (293, 673, 1, -1), (1081, 673, -1, -1)]:
            pg.draw.line(c, (61, 78, 93), (x, y), (x+dx*11, y), 1)
            pg.draw.line(c, (61, 78, 93), (x, y), (x, y+dy*11), 1)
        self.text("Sichqoncha bilan aylantiring  /  G'ildirak: masshtab", 295, 704, 11, MUTED)
        self.text("Badiiy vizualizatsiya", 932, 704, 10, (84, 103, 122))
        pg.draw.line(c, LINE, (295, 741), (1081, 741))
        self.button((295, 760, 100, 38), "▶ Davom" if self.paused else "Ⅱ Pauza", "pause", size=12)
        self.button((405, 760, 40, 38), "↺", "reset_time", size=20)
        self.text(f"{int(self.t)//60:02d}:{int(self.t)%60:02d}", 464, 768, 15, INK, mono=True)
        self.text(scene[2], 570, 769, 12, MUTED)
        self.button((1003, 760, 78, 38), "TXT ↗", "export", "txt")

        # Inspector.
        self.panel((1125, 124, 287, 698))
        self.text("SIZNING KOINOTINGIZ", 1148, 147, 10, MUTED, True)
        self.text("Ko'rinish", 1148, 180, 18, INK, True)
        self.button((1148, 217, 116, 35), "ASCII", "mode", False, active=not self.settings.dots)
        self.button((1272, 217, 116, 35), "Nuqtalar", "mode", True, active=self.settings.dots)
        self.text("Rang palitrasi", 1148, 276, 13, MUTED)
        for i, (label, color) in enumerate(THEMES):
            x = 1166+i*63
            pg.draw.circle(c, color, (x, 322), 13)
            if i == self.settings.theme:
                pg.draw.circle(c, INK, (x, 322), 19, 1)
                pg.draw.circle(c, BG, (x, 322), 4)
            self.buttons.append((pg.Rect(x-22, 300, 44, 45), "theme", i))
        self.text(THEMES[self.settings.theme][0], 1148, 352, 11, THEMES[self.settings.theme][1])
        self.slider("speed", "Harakat tezligi", 389, 0.1, 3.0, f"{self.settings.speed:.1f}x")
        self.slider("zoom", "Masshtab", 462, 0.55, 1.8, f"{int(self.settings.zoom*100)}%")
        self.slider("tilt", "Orbita qiyaligi", 535, 0.12, 0.7, f"{int(self.settings.tilt*90)}°")
        self.text("Detal darajasi", 1148, 612, 13, MUTED)
        for i, label in enumerate(("Yengil", "Muvozanat", "Yuqori")):
            self.button((1148+i*82, 641, 76, 31), label, "quality", i, active=self.settings.quality == i, size=10)
        self.toggle(696, "Yumshoq yorug'lik", "glow")
        self.toggle(731, "Yulduzlar", "stars")
        self.button((1148, 774, 240, 28), "Sozlamalarni tiklash", "reset", size=11)

        # Status line.
        pg.draw.circle(c, ACCENT, (35, 856), 3)
        self.text("OFFLINE  /  DAVA DEVELOPER", 47, 849, 10, MUTED, mono=True)
        self.text("Bir kod. Ikki platforma. Cheksiz ijod.", 494, 848, 12, MUTED)
        self.text(f"v{VERSION}  ·  {self.frame_ms:.0f} ms", 1260, 849, 10, MUTED, mono=True)
        if self.toast and time.monotonic() < self.toast_until:
            rendered = self.font(13).render(self.toast, True, ACCENT)
            box = rendered.get_rect(center=(720, 719)).inflate(32, 22)
            self.panel(box, (22, 42, 37), (58, 113, 93), 9)
            c.blit(rendered, rendered.get_rect(center=box.center))
        if self.help:
            self.draw_help()
        self.frame_ms = (time.perf_counter()-started)*1000

    def draw_help(self) -> None:
        shade = pg.Surface(BASE, pg.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        self.canvas.blit(shade, (0, 0))
        self.panel((410, 204, 620, 498), PANEL, (55, 78, 89))
        self.text("Koinotni boshqaring", 445, 236, 24, INK, True)
        rows = [("Space", "Pauza / davom ettirish"), ("1 / 2 / 3", "Qora tuynuk / sayyora / galaktika"),
                ("S / T", "PNG rasm / TXT belgilarini saqlash"), ("C / G", "Keyingi rang / yorug'lik"),
                ("R / Tab", "Sozlamalarni tiklash / toza ekran"), ("F11 / Esc", "To'liq ekran / orqaga qaytish"),
                ("Sichqoncha", "Sudrash: aylantirish; g'ildirak: masshtab")]
        for n, (key, desc) in enumerate(rows):
            y = 295+n*38
            self.text(key, 445, y, 12, ACCENT, mono=True)
            self.text(desc, 583, y, 12, INK)
        self.text("Eksport: "+str(self.output_dir), 445, 580, 10, MUTED)
        self.text("Tasvirlar badiiy talqin; ilmiy o'lchov emas.", 445, 606, 11, MUTED)
        self.button((445, 643, 166, 35), "Eksport papkasi ↗", "folder", size=11)
        self.button((854, 643, 140, 35), "Tushunarli", "help", primary=True)

    def notify(self, message: str) -> None:
        self.toast, self.toast_until = message, time.monotonic()+5

    def export(self, kind: str) -> Path | None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            name = f"DAVA_{SCENES[self.settings.scene][3]}_{stamp}.{kind}"
            path = self.output_dir / name
            art = self.renderer.render((1600, 1000), self.t, self.settings, self.orbit)
            if kind == "txt":
                path.write_text(self.renderer.last_text+"\n", encoding="utf-8")
            else:
                label = self.font(15, mono=True).render("DAVA / SPACE STUDIO   ·   "+SCENES[self.settings.scene][0], True, MUTED)
                art.blit(label, (32, 958))
                pg.image.save(art, str(path))
            self.notify("Saqlandi: "+name)
            return path
        except OSError as exc:
            self.notify("Saqlanmadi: "+str(exc)[:80])
            return None

    def action(self, action: str, value: object = None) -> None:
        s = self.settings
        if action == "scene":
            s.scene = int(value)
            self.orbit = 0.0
        elif action == "theme":
            s.theme = int(value)
        elif action == "mode":
            s.dots = bool(value)
        elif action == "quality":
            s.quality = int(value)
        elif action == "toggle":
            setattr(s, str(value), not getattr(s, str(value)))
        elif action == "pause":
            self.paused = not self.paused
        elif action == "reset_time":
            self.t = 0.0
        elif action == "reset":
            self.settings = Settings()
            self.orbit = 0.0
            self.t = 8.0
            self.paused = False
        elif action == "export":
            self.export(str(value))
        elif action == "help":
            self.help = not self.help
        elif action == "clean":
            self.clean = not self.clean
        elif action == "folder":
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                if sys.platform == "win32":
                    os.startfile(str(self.output_dir))
                else:
                    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(self.output_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                self.notify("Papka: "+str(self.output_dir))

    def logical_position(self, pos: tuple) -> tuple:
        w, h = self.screen.get_size()
        return (int(pos[0]*BASE[0]/w), int(pos[1]*BASE[1]/h))

    def move_slider(self, key: str, x: int) -> None:
        _, low, high = self.sliders[key]
        ratio = max(0, min(1, (x-1148)/240))
        setattr(self.settings, key, low+ratio*(high-low))

    def handle(self, event: pg.event.Event) -> None:
        if event.type == pg.QUIT:
            self.running = False
        elif event.type == pg.VIDEORESIZE and not self.fullscreen:
            self.screen = pg.display.set_mode((max(900, event.w), max(570, event.h)), pg.RESIZABLE)
        elif event.type == pg.KEYDOWN:
            key = event.key
            if key == pg.K_ESCAPE:
                if self.help:
                    self.help = False
                elif self.clean:
                    self.clean = False
                elif self.fullscreen:
                    self.toggle_fullscreen()
                else:
                    self.running = False
            elif key in (pg.K_h, pg.K_F1):
                self.action("help")
            elif self.help:
                return
            elif key == pg.K_SPACE:
                self.action("pause")
            elif key == pg.K_r:
                self.action("reset")
            elif key in (pg.K_1, pg.K_2, pg.K_3):
                self.action("scene", key-pg.K_1)
            elif key == pg.K_c:
                self.action("theme", (self.settings.theme+1)%4)
            elif key == pg.K_g:
                self.action("toggle", "glow")
            elif key == pg.K_s:
                self.export("png")
            elif key == pg.K_t:
                self.export("txt")
            elif key == pg.K_TAB:
                self.action("clean")
            elif key == pg.K_F11:
                self.toggle_fullscreen()
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            pos = self.logical_position(event.pos)
            if self.help:
                for rect, action, value in reversed(self.buttons):
                    if action in ("folder", "help") and rect.collidepoint(pos) and rect.y > 600:
                        self.action(action, value)
                        break
                return
            for key, (rect, _, _) in self.sliders.items():
                if rect.collidepoint(pos):
                    self.dragging = key
                    self.move_slider(key, pos[0])
                    return
            for rect, action, value in reversed(self.buttons):
                if rect.collidepoint(pos):
                    self.action(action, value)
                    return
            if self.art_rect.collidepoint(pos) or self.clean:
                self.dragging = "orbit"
                self.drag_anchor = pos
        elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.dragging = None
        elif event.type == pg.MOUSEMOTION:
            pos = self.logical_position(event.pos)
            self.mouse = pos
            if self.dragging == "orbit":
                self.orbit += (pos[0]-self.drag_anchor[0])*0.004
                self.settings.tilt = max(0.12, min(0.7, self.settings.tilt+(pos[1]-self.drag_anchor[1])*0.002))
                self.drag_anchor = pos
            elif self.dragging in self.sliders:
                self.move_slider(self.dragging, pos[0])
        elif event.type == pg.MOUSEWHEEL and not self.help:
            if self.art_rect.collidepoint(self.mouse) or self.clean:
                self.settings.zoom = max(0.55, min(1.8, self.settings.zoom+event.y*0.05))

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.screen = pg.display.set_mode((0, 0) if self.fullscreen else BASE, pg.FULLSCREEN if self.fullscreen else pg.RESIZABLE)

    def run(self, frames: int = 0, screenshot: Path | None = None) -> None:
        count = 0
        # First draw registers controls before the first input event.
        self.draw()
        while self.running:
            dt = min(self.clock.tick((24, 30, 30)[self.settings.quality])/1000, 0.1)
            for event in pg.event.get():
                self.handle(event)
            if not self.paused and not self.help:
                self.t += dt*self.settings.speed
            self.draw()
            pg.transform.smoothscale(self.canvas, self.screen.get_size(), self.screen)
            pg.display.flip()
            count += 1
            if frames and count >= frames:
                break
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            pg.image.save(self.canvas, str(screenshot))
        if not self.headless:
            try:
                self.settings.save()
            except OSError:
                pass
        pg.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="DAVA Space Studio — Windows / Linux")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--headless", action="store_true", help="Offscreen render for QA")
    parser.add_argument("--frames", type=int, default=0)
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--scene", type=int, choices=(0, 1, 2))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fresh", action="store_true", help="Ignore saved preferences")
    args = parser.parse_args()
    if args.headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    settings = Settings() if args.fresh else Settings.load()
    if args.scene is not None:
        settings.scene = args.scene
    try:
        App(settings, headless=args.headless, output_dir=args.output_dir).run(
            frames=args.frames or (1 if args.headless else 0), screenshot=args.screenshot)
    except pg.error as exc:
        print("DAVA Space Studio: "+str(exc), file=sys.stderr)
        print("Linux: grafik ish stolida (GNOME/KDE/Xfce) ishga tushiring.", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
