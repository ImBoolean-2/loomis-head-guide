# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas del generador Loomis (sin Krita).

Ejecutar desde esta carpeta:
    python3 -m unittest test_generator.py -v
"""
import math
import sys
import types
import unittest
from pathlib import Path

# El paquete real importa krita en __init__.py; aqui solo probamos el generador.
_pkg = types.ModuleType("loomis_head")
_pkg.__path__ = [str(Path(__file__).resolve().parent)]
sys.modules.setdefault("loomis_head", _pkg)

from loomis_head.euclid import Vector3  # noqa: E402
from loomis_head.linalg import (  # noqa: E402
    angles_from_quaternion,
    mat3_mul_vec,
    q_axis_angle,
    q_mul,
    q_to_mat3,
)
from loomis_head.loomis_head_generator import LoomisHead3D  # noqa: E402


class GeneratorTests(unittest.TestCase):
    def test_default_svg(self):
        svg = LoomisHead3D().build_svg(1000, 800)
        self.assertIn("<svg", svg)
        self.assertIn("<path", svg)
        self.assertNotIn("nan", svg.lower())
        self.assertNotIn("inf", svg.lower())

    def test_features_add_geometry(self):
        head = LoomisHead3D()
        plain = head.build_svg(1000, 800)
        head.set_show_features(True)
        rich = head.build_svg(1000, 800)
        self.assertGreater(len(rich), len(plain))

    def test_feature_toggles_reduce(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        all_on = head.build_svg(1000, 800)
        head.set_show_eyes(False)
        head.set_show_ears(False)
        head.set_show_nose(False)
        head.set_show_mouth(False)
        head.set_show_brows(False)
        off = head.build_svg(1000, 800)
        self.assertLess(len(off), len(all_on))

    def test_dict_roundtrip(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_cranium(1.3)
        head.set_cheek(0.6)
        head.set_eye_line(0.45)
        before = head.build_svg(1000, 800)
        clone = LoomisHead3D()
        clone.from_dict(head.to_dict())
        self.assertEqual(before, clone.build_svg(1000, 800))
        self.assertEqual(head.to_dict(), clone.to_dict())

    def test_from_dict_tolerates_garbage(self):
        head = LoomisHead3D()
        head.from_dict({})
        head.from_dict({"scale": "no", "rotation": [1, 2], "eyeSize": None})
        svg = head.build_svg(800, 800)
        self.assertIn("<svg", svg)
        self.assertNotIn("nan", svg.lower())

    def test_extremes(self):
        head = LoomisHead3D()
        cases = [
            (head.set_cranium, (0.6, 1.6)),
            (head.set_jaw_taper, (0.4, 1.6)),
            (head.set_cheek, (0.0, 1.0)),
            (head.set_face_width, (0.6, 1.4)),
            (head.set_jaw_drop, (0.6, 1.4)),
            (head.set_sidecut, (0.05, 0.95)),
            (head.set_eye_size, (0.02, 0.4)),
            (head.set_mouth_curve, (-0.15, 0.15)),
        ]
        head.set_show_features(True)
        for setter, values in cases:
            for value in values:
                setter(value)
                svg = head.build_svg(800, 800)
                self.assertIn("<svg", svg)
                self.assertNotIn("nan", svg.lower())

    def test_clamps(self):
        head = LoomisHead3D()
        head.set_cranium(-5)
        self.assertEqual(head.cranium, 0.6)
        head.set_scale(0)
        self.assertGreaterEqual(head.scale, 0.05)
        head.set_eye_size(99)
        self.assertLessEqual(head.eye_size, 0.4)

    def test_trackball_angles(self):
        q = q_mul(q_axis_angle([0, 1, 0], 0.3), q_axis_angle([1, 0, 0], -0.2))
        yaw, pitch, roll = angles_from_quaternion(q)
        self.assertAlmostEqual(yaw, 0.3, places=5)
        self.assertAlmostEqual(pitch, -0.2, places=5)
        self.assertAlmostEqual(roll, 0.0, places=5)

    def test_trackball_roll(self):
        q_turn = q_mul(q_axis_angle([0, 1, 0], 0.3), q_axis_angle([1, 0, 0], -0.2))
        fwd = mat3_mul_vec(q_to_mat3(q_turn), Vector3(0.0, 0.0, 1.0))
        q = q_mul(q_axis_angle(fwd, 0.4), q_turn)
        yaw, pitch, roll = angles_from_quaternion(q)
        self.assertAlmostEqual(yaw, 0.3, places=5)
        self.assertAlmostEqual(pitch, -0.2, places=5)
        self.assertAlmostEqual(roll, 0.4, places=5)

    def test_hair_patterns(self):
        head = LoomisHead3D()
        head.set_show_hair(True)
        head.set_zone_colors(True)
        head.set_hair_part(2)
        svg = head.build_svg(800, 800)
        self.assertIn("#B07A52", svg)
        head.set_show_hair(False)
        svg = head.build_svg(800, 800)
        self.assertNotIn("#B07A52", svg)

    def test_euler_roundtrip(self):
        from loomis_head.linalg import quaternion_from_angles
        q = quaternion_from_angles(0.3, -0.2, 0.4)
        yaw, pitch, roll = angles_from_quaternion(q)
        self.assertAlmostEqual(yaw, 0.3, places=5)
        self.assertAlmostEqual(pitch, -0.2, places=5)
        self.assertAlmostEqual(roll, 0.4, places=5)

    def test_hair_custom(self):
        head = LoomisHead3D()
        head.set_show_hair(True)
        head.set_hair_arch(0.12)
        head.set_hair_tilt(-0.08)
        head.set_hair_part_pos(-0.4)
        head.set_hair_part(1)
        head.set_hair_texture(2)
        svg = head.build_svg(800, 800)
        self.assertIn("<svg", svg)
        self.assertNotIn("nan", svg.lower())
        clone = LoomisHead3D()
        clone.from_dict(head.to_dict())
        self.assertEqual(head.to_dict(), clone.to_dict())

    def test_back_view(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_quaternion(q_axis_angle([0, 1, 0], math.pi))
        svg = head.build_svg(800, 800)
        self.assertIn("<svg", svg)
        self.assertNotIn("nan", svg.lower())

    def test_zone_colors(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_zone_colors(True)
        svg = head.build_svg(1000, 800)
        for color in ("#6A54E7", "#E76A54", "#54C4E7", "#E7C454", "#8A8A9A"):
            self.assertIn(color, svg)
        self.assertGreater(svg.count("<path"), 2)
        head.set_zone_colors(False)
        svg = head.build_svg(1000, 800)
        self.assertNotIn("#E76A54", svg)

    def test_share_wrapper_roundtrip(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_zone_colors(True)
        head.set_cranium(1.2)
        wrapper = {"format": "loomis-head", "version": 1, "model": "loomis",
                   "head": head.to_dict()}
        clone = LoomisHead3D()
        clone.from_dict(wrapper["head"])
        self.assertEqual(head.build_svg(900, 700), clone.build_svg(900, 700))
        self.assertEqual(clone.to_dict()["model"], "loomis")

    def test_json_serializable(self):
        import json
        payload = json.dumps(LoomisHead3D().to_dict())
        self.assertIn('"version": 1', payload)


if __name__ == "__main__":
    unittest.main()
