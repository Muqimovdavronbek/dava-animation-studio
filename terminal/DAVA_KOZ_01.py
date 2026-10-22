#!/usr/bin/env python3
"""DAVA KO'Z 01 — animated binary eye for Linux and Windows terminals.

One Python 3.9+ file. Standard library only. No pip, GUI, account or internet.
Linux:   python3 DAVA_KOZ_01.py
Windows: py DAVA_KOZ_01.py

Keys (no visible panels):
  Space     pause / resume
  C         next color
  + / -     zoom in / out
  ] / [     faster / slower
  R         reset
  Q / Esc   exit (Ctrl+C also works)

Options:
  --color amber|green|blue|violet|white
  --fps 24       target FPS (5–60)
  --no-color     plain binary animation
  --cell-aspect 0.48  character width / line height
  --snapshot --size 120x40 --time 8 --no-color

Only 0, 1 and spaces are drawn. Terminal state is restored on exit.
The pupil looks around; the eyelids blink. Only the eye is shown.

Windows VT:
https://learn.microsoft.com/windows/console/setconsolemode
POSIX cbreak:
https://docs.python.org/3/library/tty.html

Copyright (c) 2026 Dava Developer. MIT License:
Permission is granted to use, copy, modify, merge, publish, distribute,
sublicense and/or sell this software, provided this notice is retained.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
"""
from __future__ import annotations

import argparse
import math
import os
import shutil
import signal
import sys
import time

ESC = "\x1b["
THEMES = {
    "amber": (255, 157, 70),
    "green": (75, 238, 131),
    "blue": (98, 178, 255),
    "violet": (194, 126, 255),
    "white": (225, 234, 245),
}
RESET = ESC + "0m"


def clamp(value, low, high):
    return max(low, min(high, value))


def positive_size(value):
    try:
        cols, rows = map(int, value.lower().split("x"))
        if not (10 <= cols <= 400 and 5 <= rows <= 150):
            raise ValueError
        return cols, rows
    except ValueError:
        raise argparse.ArgumentTypeError("O'lcham 120x40 ko'rinishida bo'lsin (10–400 x 5–150).")


class BinaryEye:
    """CPU renderer; stable spatial dithering makes monochrome work too."""
    def __init__(self, cols, rows, cell_aspect=0.48):
        self.cols, self.rows = cols, rows
        aspect = cols * cell_aspect / rows
        span = max(2.8, 6.2 / aspect)
        self.grid = []
        for row in range(rows):
            points = []
            for col in range(cols):
                x = ((col + 0.5) / cols - 0.5) * span * aspect
                y = ((row + 0.5) / rows - 0.5) * span
                h = ((col * 374761393 + row * 668265263 + 247) ^ (col * row * 31)) & 0xffffffff
                h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
                noise = (h & 65535) / 65535.0
                points.append((x, y, noise, h & 1))
            self.grid.append(points)
        self._palette_key = None
        self._palette = None

    def palette(self, theme):
        if self._palette_key != theme:
            result = []
            # Lids / sclera / iris / small corneal reflections.
            for base in [(178, 112, 72), (225, 218, 205), THEMES[theme], (255, 255, 255)]:
                shades = []
                for level in range(24):
                    v = level / 23.0
                    whitening = max(0, (v - 0.68) / 0.32) * 0.7
                    rgb = []
                    for channel in base:
                        c = channel * (0.30 + 0.70 * math.sqrt(v))
                        rgb.append(int(c + (255 - c) * whitening))
                    rr, gg, bb = (int(channel / 255 * 5 + 0.5) for channel in rgb)
                    shades.append(ESC + "38;5;" + str(16 + 36 * rr + 6 * gg + bb) + "m")
                result.append(shades)
            self._palette_key, self._palette = theme, result
        return self._palette

    def frame(self, t, theme="amber", color=True, zoom=1.0):
        exp, sin, atan2, hypot = math.exp, math.sin, math.atan2, math.hypot
        phase = t % 6.8
        blink = exp(-((phase - 5.4) / 0.115) ** 2)
        blink = max(blink, 0.64 * exp(-((phase - 5.78) / 0.09) ** 2))
        opening = max(0.012, 1.0 - blink)
        gaze_x = 0.38 * sin(t * 0.7) + 0.16 * sin(t * 0.23)
        gaze_y = 0.075 * sin(t * 0.53)
        pupil = 0.265 + 0.018 * sin(t * 0.9)
        palette = self.palette(theme) if color else None
        lines = []
        for points in self.grid:
            line, last_level = [], -1
            for x0, y0, noise, bit in points:
                x, y = x0 / zoom, y0 / zoom
                nx = x / 2.64
                if abs(nx) >= 1.10 or y < -1.28 or y > 0.98:
                    line.append(" ")
                    continue
                arc = max(0, 1 - nx * nx)
                mid = -0.035 * x
                upper = mid - 0.84 * arc ** 0.64 * opening
                lower = mid + 0.68 * arc ** 0.82 * opening
                material, theta, radius = 0, 0.0, 0.0
                if abs(nx) < 1 and upper < y < lower:
                    dx, dy = x - gaze_x, y - gaze_y
                    radius = hypot(dx, dy)
                    theta = atan2(dy, dx)
                    if radius < pupil:
                        v = 0.0
                    elif radius < 0.745:
                        material = 2
                        fiber = (0.5 + 0.5 * sin(theta * 67 + radius * 26 + 1.4 * sin(theta * 11)))
                        rings = 0.5 + 0.5 * sin(radius * 43 + sin(theta * 8))
                        edge = min(1.0, max(0, (0.745 - radius) / 0.10))
                        v = (0.28 + fiber * 0.31 + rings * 0.12) * (0.28 + 0.72 * edge)
                        v += 0.14 * exp(-((radius - pupil - 0.03) / 0.055) ** 2)
                    else:
                        material = 1
                        v = 0.46 + 0.20 * (1 - abs(nx)) - 0.10 * max(0, y)
                        v -= 0.16 * exp(-((y - upper) / 0.15) ** 2)
                        v -= 0.08 * exp(-((y - lower) / 0.12) ** 2)
                    # White reflections stay attached to the cornea.
                    if ((dx + 0.24) / 0.085) ** 2 + ((dy + 0.27) / 0.115) ** 2 < 1:
                        v, material = 1.0, 3
                    if ((dx - 0.19) / 0.045) ** 2 + ((dy - 0.19) / 0.065) ** 2 < 1:
                        v, material = 0.87, 3
                else:
                    top_lid = exp(-((y - upper) / 0.065) ** 2) * 0.67
                    bottom_lid = exp(-((y - lower) / 0.057) ** 2) * 0.46
                    crease = exp(-((y - upper + 0.21) / 0.075) ** 2) * 0.23
                    v = max(top_lid, bottom_lid, crease) * max(0, 1 - abs(nx) ** 8)
                v = clamp(v, 0, 1)
                if v < 0.052 or noise > min(1.0, v ** 0.46 + 0.17):
                    line.append(" ")
                    continue
                digit = "1" if sin(theta * 9 + radius * 19 - t * 1.4 + bit + x * 3) > 0 else "0"
                if color:
                    level = min(23, int(v * 23))
                    color_key = (material, level)
                    if color_key != last_level:
                        line.append(palette[material][level])
                        last_level = color_key
                line.append(digit)
            if color:
                line.append(ESC + "39m")
            lines.append("".join(line))
        return lines


class Terminal:
    """Save console state and restore it even after Ctrl+C or an exception."""
    def __init__(self):
        self.posix_state = None
        self.win_state = None
        self.stdin_fd = None

    def __enter__(self):
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.GetStdHandle.argtypes = [wintypes.DWORD]
            kernel.GetStdHandle.restype = wintypes.HANDLE
            kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.GetConsoleMode.restype = wintypes.BOOL
            kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel.SetConsoleMode.restype = wintypes.BOOL
            handle = kernel.GetStdHandle(-11)
            original = wintypes.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(original)):
                raise RuntimeError("Windows Terminal yoki PowerShell oynasida oching.")
            if not kernel.SetConsoleMode(handle, original.value | 0x0004 | 0x0001):
                raise RuntimeError("Rangli terminal rejimi yoqilmadi. Windows Terminal'da oching.")
            self.win_state = (kernel, handle, original.value)
        elif sys.stdin.isatty():
            import termios
            import tty
            self.stdin_fd = sys.stdin.fileno()
            self.posix_state = termios.tcgetattr(self.stdin_fd)
            tty.setcbreak(self.stdin_fd)
        try:
            sys.stdout.write(ESC + "?1049h" + ESC + "?25l" + ESC + "37;40m" + ESC + "2J" + ESC + "H")
            sys.stdout.flush()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def keys(self):
        keys = []
        if os.name == "nt":
            import msvcrt
            while msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in ("\x00", "\xe0"):
                    if msvcrt.kbhit():
                        msvcrt.getwch()
                    continue
                keys.append(char)
        elif self.stdin_fd is not None:
            import select
            while select.select([self.stdin_fd], [], [], 0)[0]:
                data = os.read(self.stdin_fd, 64)
                if not data:
                    self.stdin_fd = None
                    break
                keys.extend(data.decode("utf-8", errors="ignore"))
        return keys

    def __exit__(self, *_):
        try:
            sys.stdout.write(RESET + ESC + "?25h" + ESC + "?1049l")
            sys.stdout.flush()
        except (OSError, ValueError):
            pass
        finally:
            if self.posix_state is not None:
                import termios
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.posix_state)
            if self.win_state is not None:
                kernel, handle, original = self.win_state
                kernel.SetConsoleMode(handle, original)


def animate(args):
    if not sys.stdout.isatty():
        raise RuntimeError("Haqiqiy terminalda oching. Bitta kadr uchun --snapshot ishlating.")
    themes = list(THEMES)
    theme, speed, zoom = args.color, 1.0, 1.0
    paused, shape, engine = False, None, None
    t, previous, count = 8.0, time.perf_counter(), 0
    with Terminal() as terminal:
        while True:
            started = time.perf_counter()
            t += 0 if paused else min(started - previous, 0.2) * speed
            previous = started
            for key in terminal.keys():
                if key.lower() == "q" or key in ("\x1b", "\x03"):
                    return
                if key == " ":
                    paused = not paused
                elif key.lower() == "c":
                    theme = themes[(themes.index(theme) + 1) % len(themes)]
                elif key in ("+", "="):
                    zoom = min(1.8, zoom + 0.08)
                elif key in ("-", "_"):
                    zoom = max(0.5, zoom - 0.08)
                elif key == "]":
                    speed = min(3, speed + 0.2)
                elif key == "[":
                    speed = max(0.2, speed - 0.2)
                elif key.lower() == "r":
                    theme, speed, zoom, t, paused = args.color, 1.0, 1.0, 8.0, False
            size = shutil.get_terminal_size((100, 34))
            cols = max(1, min(240, size.columns - 1))
            rows = max(1, min(90, size.lines - 1))
            if (cols, rows) != shape:
                engine = BinaryEye(cols, rows, args.cell_aspect)
                shape = (cols, rows)
                sys.stdout.write(ESC + "2J")
            lines = engine.frame(t, theme, not args.no_color, zoom)
            # One buffered write; no clear command and no scrolling per frame.
            left = max(0, (size.columns - cols) // 2)
            top = max(0, (size.lines - rows) // 2)
            position = ESC + str(top + 1) + ";" + str(left + 1) + "H"
            # Position each row explicitly so terminal newline translation
            # cannot create scrolling or an incorrect left margin.
            frame = position + lines[0]
            for row, line in enumerate(lines[1:], top + 2):
                frame += ESC + str(row) + ";" + str(left + 1) + "H" + line
            sys.stdout.write(frame)
            sys.stdout.flush()
            count += 1
            if args.frames and count >= args.frames:
                return
            time.sleep(max(0, 1.0 / args.fps - (time.perf_counter() - started)))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="DAVA KO'Z 01: Linux va Windows terminalida faqat 0/1 ko'z animatsiyasi.",
        epilog="Space: pauza | C: rang | +/-: masshtab | [/]: tezlik | R: tiklash | Q/Ctrl+C: chiqish")
    parser.add_argument("--color", choices=list(THEMES), default="amber")
    parser.add_argument("--fps", type=int, choices=range(5, 61), metavar="5-60", default=24)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--cell-aspect", type=float, default=0.48, metavar="RATIO")
    parser.add_argument("--snapshot", action="store_true", help="Animatsiya o'rniga bitta kadr")
    parser.add_argument("--size", type=positive_size, default=(120, 40), metavar="COLSxROWS", help="Snapshot o'lchami")
    parser.add_argument("--time", type=float, default=8.0, help="Snapshot vaqti")
    parser.add_argument("--frames", type=int, default=0, help="0: cheksiz; musbat son: belgilangan kadrlar")
    args = parser.parse_args(argv)
    if not math.isfinite(args.cell_aspect) or not 0.2 <= args.cell_aspect <= 1:
        parser.error("--cell-aspect 0.2 va 1 orasida bo'lsin.")
    if not math.isfinite(args.time) or args.frames < 0:
        parser.error("--time chekli son, --frames esa manfiy bo'lmagan son bo'lsin.")
    if args.snapshot:
        lines = BinaryEye(*args.size, args.cell_aspect).frame(args.time, args.color, not args.no_color)
        print("\n".join(lines))
        return 0
    try:
        animate(args)
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError) as error:
        print("DAVA 01: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    if hasattr(signal, "SIGTERM"):
        def stop_on_term(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop_on_term)
    raise SystemExit(main())
