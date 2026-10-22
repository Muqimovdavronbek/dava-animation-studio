"""Behavior tests for the numerical engine, input, preferences and file exports."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pygame as pg

from main import App, Settings, SpaceEngine


class EngineTests(unittest.TestCase):
    def test_scenes_are_finite_and_distinct_at_control_extremes(self):
        engine = SpaceEngine()
        images = []
        for scene in range(3):
            for tilt in (0.12, 0.7):
                for zoom in (0.55, 1.8):
                    result = engine.sample(120, 48, 1.7, 2.3, Settings(scene=scene, tilt=tilt, zoom=zoom))
                    self.assertEqual(result.shape, (48, 120))
                    self.assertTrue(np.isfinite(result).all())
                    self.assertGreater(float(result.max()), 0.4)
                    self.assertGreaterEqual(float(result.min()), 0)
                    self.assertLessEqual(float(result.max()), 1)
            images.append(engine.sample(120, 48, 1.7, 0, Settings(scene=scene)))
        self.assertFalse(np.allclose(images[0], images[1]))
        self.assertFalse(np.allclose(images[1], images[2]))

    def test_motion_changes_all_three_scenes(self):
        engine = SpaceEngine()
        for scene in range(3):
            settings = Settings(scene=scene)
            a = engine.sample(120, 48, 1.7, 0, settings)
            b = engine.sample(120, 48, 1.7, 3, settings)
            self.assertGreater(float(np.abs(a-b).sum()), 1)


class SettingsTests(unittest.TestCase):
    def test_saved_preferences_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            expected = Settings(scene=2, theme=3, speed=2.1, zoom=0.9, dots=True)
            expected.save(path)
            self.assertEqual(expected, Settings.load(path))

    def test_invalid_values_are_rejected_or_clamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text(json.dumps({"zoom": 900, "scene": -10, "theme": "bad", "speed": float("nan"), "glow": "false"}))
            actual = Settings.load(path)
            self.assertEqual(actual.zoom, 1.8)
            self.assertEqual(actual.scene, 0)
            self.assertEqual(actual.theme, 0)
            self.assertEqual(actual.speed, 1)
            self.assertTrue(actual.glow)
            path.write_text("{broken")
            self.assertEqual(Settings.load(path), Settings())


class InteractionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = App(Settings(), headless=True, output_dir=Path(self.tmp.name))
        self.app.draw()

    def tearDown(self):
        pg.quit()
        self.tmp.cleanup()

    def key(self, key):
        self.app.handle(pg.event.Event(pg.KEYDOWN, key=key))

    def click(self, pos):
        self.app.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=pos))
        self.app.handle(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=pos))

    def test_keyboard_scene_pause_theme_and_reset(self):
        self.key(pg.K_3)
        self.assertEqual(self.app.settings.scene, 2)
        self.key(pg.K_SPACE)
        self.assertTrue(self.app.paused)
        self.key(pg.K_c)
        self.assertEqual(self.app.settings.theme, 1)
        self.key(pg.K_r)
        self.assertEqual(self.app.settings, Settings())
        self.assertFalse(self.app.paused)

    def test_sidebar_slider_and_modal_blocks_background(self):
        self.click((149, 302))
        self.assertEqual(self.app.settings.scene, 1)
        self.click((1388, 426))
        self.assertAlmostEqual(self.app.settings.speed, 3)
        self.key(pg.K_h)
        self.app.draw()
        self.click((150, 385))
        self.assertEqual(self.app.settings.scene, 1)
        self.key(pg.K_ESCAPE)
        self.assertFalse(self.app.help)

    def test_exports_contain_real_scene_data(self):
        image = self.app.export("png")
        text = self.app.export("txt")
        self.assertEqual(pg.image.load(str(image)).get_size(), (1600, 1000))
        data = text.read_text()
        self.assertGreater(len(data), 1000)
        self.assertIn("@", data)
        self.assertNotEqual(image.stem, text.stem)
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())), 2)


if __name__ == "__main__":
    unittest.main()
