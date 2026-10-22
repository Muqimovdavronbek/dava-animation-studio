import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "DAVA_KOZ_01.py"
spec = importlib.util.spec_from_file_location("dava_eye", SCRIPT)
eye = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eye)


class EyeTests(unittest.TestCase):
    def test_only_binary_digits_and_exact_dimensions(self):
        for cols, rows in [(1, 1), (20, 8), (79, 23), (120, 40), (160, 49)]:
            lines = eye.BinaryEye(cols, rows).frame(8, color=False)
            self.assertEqual(len(lines), rows)
            self.assertTrue(all(len(line) == cols for line in lines))
            self.assertLessEqual(set("".join(lines)), set("01 "))

    def test_pupil_moves_and_eye_blinks(self):
        engine = eye.BinaryEye(120, 40)
        first = "".join(engine.frame(0, color=False))
        moved = "".join(engine.frame(3, color=False))
        closed = "".join(engine.frame(5.4, color=False))
        self.assertNotEqual(first, moved)
        self.assertLess(sum(c in "01" for c in closed), sum(c in "01" for c in first) * 0.4)

    def test_colored_frames_keep_background_and_binary_characters(self):
        frame = "\n".join(eye.BinaryEye(80, 24).frame(8))
        self.assertNotIn("\x1b[0m", frame)
        self.assertEqual(frame.count("\x1b[39m"), 24)
        plain = re.sub(r"\x1b\[[0-9;]*m", "", frame)
        self.assertLessEqual(set(plain), set("01 \n"))

    def test_snapshot_works_without_a_terminal(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--snapshot", "--no-color", "--size", "80x24"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 24)
        self.assertLessEqual(set(result.stdout), set("01 \n"))

    @unittest.skipIf(os.name == "nt", "POSIX PTY lifecycle; Windows uses its native console API")
    def test_q_restores_terminal_and_cursor(self):
        import fcntl
        import pty
        import select
        import struct
        import termios
        import time
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        original = termios.tcgetattr(slave)
        process = subprocess.Popen([sys.executable, str(SCRIPT)], stdin=slave, stdout=slave, stderr=slave)
        data = bytearray()
        try:
            deadline = time.monotonic() + 8
            while b"\x1b[?25l" not in data and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    data.extend(os.read(master, 65536))
            self.assertIn(b"\x1b[?25l", data)
            os.write(master, b"q")
            while process.poll() is None and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    data.extend(os.read(master, 65536))
            self.assertEqual(process.wait(timeout=2), 0)
            while select.select([master], [], [], 0.05)[0]:
                data.extend(os.read(master, 65536))
            self.assertEqual(termios.tcgetattr(slave), original)
            self.assertIn(b"\x1b[?25h", data)
            self.assertIn(b"\x1b[?1049l", data)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)


if __name__ == "__main__":
    unittest.main()
