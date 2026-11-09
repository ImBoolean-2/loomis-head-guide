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

    # --- 0.6.0: proporciones, guias, ritmo y luz -------------------------

    def test_proportion_defaults(self):
        head = LoomisHead3D()
        self.assertEqual(head.forehead_height, 1.0)
        self.assertEqual(head.jaw_angle, 0.0)
        self.assertEqual(head.cranium_width, 1.0)
        self.assertEqual(head.cranium_height, 1.0)
        self.assertEqual(head.cheekbone_height, 0.5)
        self.assertEqual(head.chin_sharpness, 0.0)
        self.assertFalse(head.show_rhythm)
        self.assertEqual(head.rhythm_strength, 0.6)

    def test_proportion_clamps(self):
        head = LoomisHead3D()
        head.set_forehead_height(99)
        self.assertEqual(head.forehead_height, 1.4)
        head.set_forehead_height(-99)
        self.assertEqual(head.forehead_height, 0.6)
        head.set_jaw_angle(9)
        self.assertEqual(head.jaw_angle, 1.0)
        head.set_cranium_width(0.0)
        self.assertEqual(head.cranium_width, 0.8)
        head.set_cranium_height(9.0)
        self.assertEqual(head.cranium_height, 1.2)
        head.set_cheekbone_height(-1)
        self.assertEqual(head.cheekbone_height, 0.0)
        head.set_chin_sharpness(2)
        self.assertEqual(head.chin_sharpness, 1.0)
        head.set_rhythm_strength(2)
        self.assertEqual(head.rhythm_strength, 1.0)

    def test_proportion_extremes_render(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_show_hair(True)
        cases = [
            (head.set_forehead_height, (0.6, 1.4)),
            (head.set_jaw_angle, (0.0, 1.0)),
            (head.set_cranium_width, (0.8, 1.2)),
            (head.set_cranium_height, (0.8, 1.2)),
            (head.set_cheekbone_height, (0.0, 1.0)),
            (head.set_chin_sharpness, (0.0, 1.0)),
        ]
        for setter, values in cases:
            for value in values:
                setter(value)
                svg = head.build_svg(800, 800)
                self.assertIn("<svg", svg)
                self.assertNotIn("nan", svg.lower())
                self.assertNotIn("inf", svg.lower())

    def test_cranium_scales_geometry(self):
        head = LoomisHead3D()
        base = head.build_svg(800, 800)
        head.set_cranium_width(1.2)
        wide = head.build_svg(800, 800)
        self.assertNotEqual(base, wide)
        head.set_cranium_width(1.0)
        head.set_cranium_height(1.2)
        tall = head.build_svg(800, 800)
        self.assertNotEqual(base, tall)
        self.assertNotIn("nan", tall.lower())

    def test_forehead_height_moves_hairline(self):
        head = LoomisHead3D()
        head.set_show_hair(True)
        head.set_forehead_height(0.6)
        low = head.build_svg(800, 800)
        head.set_forehead_height(1.4)
        high = head.build_svg(800, 800)
        self.assertNotEqual(low, high)
        self.assertNotIn("nan", high.lower())

    def test_chin_sharpness_changes_jaw(self):
        head = LoomisHead3D()
        round_chin = head.build_svg(800, 800)
        head.set_chin_sharpness(1.0)
        point_chin = head.build_svg(800, 800)
        self.assertNotEqual(round_chin, point_chin)
        self.assertNotIn("nan", point_chin.lower())

    def test_rhythm_zone(self):
        head = LoomisHead3D()
        head.set_zone_colors(True)
        head.set_show_rhythm(True)
        svg = head.build_svg(800, 800)
        self.assertIn("#D96A8A", svg)
        head.set_show_rhythm(False)
        svg = head.build_svg(800, 800)
        self.assertNotIn("#D96A8A", svg)

    def test_rhythm_strength_changes_curves(self):
        head = LoomisHead3D()
        head.set_show_rhythm(True)
        head.set_rhythm_strength(0.0)
        weak = head.build_svg(800, 800)
        head.set_rhythm_strength(1.0)
        strong = head.build_svg(800, 800)
        self.assertNotEqual(weak, strong)

    def test_rhythm_central_curve_passes_landmarks(self):
        head = LoomisHead3D()
        head.set_show_rhythm(True)
        rc = head.radius * head.cranium
        brow_y = (head.brow_line - 0.5) * 2.0 * rc
        nose_y = (head.nose_line - 0.5) * 2.0 * rc - head.nose_length * rc
        mouth_y = (head.mouth_line - 0.5) * 2.0 * rc
        curves = head._rhythm_curves(rc)
        self.assertGreaterEqual(len(curves), 4)
        central = curves[0]
        self.assertTrue(central)
        for target in (brow_y, nose_y, mouth_y):
            nearest = min(abs(point.y - target) for point in central)
            self.assertLess(nearest, 0.02 * rc)
        # La curva central baja de la corona al menton y no se va de la esfera
        # en el tramo de los rasgos.
        self.assertGreater(central[0].y, 0.9 * rc)
        self.assertLess(central[-1].y, mouth_y)
        for point in central:
            self.assertFalse(math.isnan(point.x + point.y + point.z))

    def test_rhythm_strength_changes_arcs(self):
        head = LoomisHead3D()
        head.set_show_rhythm(True)
        rc = head.radius * head.cranium
        head.set_rhythm_strength(0.0)
        weak = head._rhythm_curves(rc)
        head.set_rhythm_strength(1.0)
        strong = head._rhythm_curves(rc)
        self.assertNotEqual(weak[1][0].x, strong[1][0].x)
        self.assertNotEqual([p.z for p in weak[0]], [p.z for p in strong[0]])

    def test_guide_toggles(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        all_on = head.build_svg(800, 800)
        for setter in (
            head.set_show_brow_guide,
            head.set_show_eye_guide,
            head.set_show_nose_guide,
            head.set_show_mouth_guide,
        ):
            before = head.build_svg(800, 800)
            setter(False)
            after = head.build_svg(800, 800)
            self.assertLess(len(after), len(before))
        self.assertLess(len(head.build_svg(800, 800)), len(all_on))
        head.set_show_features(False)
        self.assertLess(len(head.build_svg(800, 800)), len(all_on))

    def test_guide_defaults(self):
        head = LoomisHead3D()
        for name in ("show_brow_guide", "show_eye_guide",
                     "show_nose_guide", "show_mouth_guide"):
            self.assertTrue(getattr(head, name))

    def test_light_defaults_and_clamps(self):
        head = LoomisHead3D()
        self.assertEqual(head.light_azimuth, -35.0)
        self.assertEqual(head.light_elevation, 35.0)
        self.assertEqual(head.light_intensity, 0.35)
        self.assertFalse(head.show_shadow)
        self.assertEqual(head.shadow_mode, 0)
        head.set_light_azimuth(-999)
        self.assertEqual(head.light_azimuth, -180.0)
        head.set_light_elevation(999)
        self.assertEqual(head.light_elevation, 90.0)
        head.set_light_intensity(9)
        self.assertEqual(head.light_intensity, 1.0)
        head.set_shadow_mode(5)
        self.assertEqual(head.shadow_mode, 1)
        head.set_show_shadow(True)
        self.assertTrue(head.show_shadow)

    def test_new_fields_roundtrip(self):
        head = LoomisHead3D()
        head.set_forehead_height(1.25)
        head.set_jaw_angle(0.8)
        head.set_cranium_width(1.1)
        head.set_cranium_height(0.9)
        head.set_cheekbone_height(0.7)
        head.set_chin_sharpness(0.6)
        head.set_show_rhythm(True)
        head.set_rhythm_strength(0.9)
        head.set_show_brow_guide(False)
        head.set_show_nose_guide(False)
        head.set_light_azimuth(40.0)
        head.set_light_elevation(-10.0)
        head.set_light_intensity(0.8)
        head.set_show_shadow(True)
        head.set_shadow_mode(1)
        clone = LoomisHead3D()
        clone.from_dict(head.to_dict())
        self.assertEqual(head.to_dict(), clone.to_dict())
        self.assertEqual(head.build_svg(900, 700), clone.build_svg(900, 700))

    def test_dict_051_compatibility(self):
        # Preset de 0.5.1: sin ninguna clave nueva.
        legacy = {
            "version": 1,
            "generator": "loomis",
            "model": "loomis",
            "scale": 1.0,
            "sideCut": 0.66,
            "faceAge": 1.0,
            "chinWidth": 1.0,
            "cranium": 1.0,
            "jawTaper": 1.0,
            "cheek": 0.0,
            "faceWidth": 1.0,
            "jawDrop": 1.0,
            "showFeatures": True,
            "browLine": 0.62,
            "eyeLine": 0.5,
            "noseLine": 0.32,
            "mouthLine": 0.18,
        }
        head = LoomisHead3D()
        head.from_dict(legacy)
        svg = head.build_svg(800, 800)
        self.assertIn("<svg", svg)
        self.assertNotIn("nan", svg.lower())
        self.assertEqual(head.forehead_height, 1.0)
        self.assertEqual(head.jaw_angle, 0.0)
        self.assertEqual(head.cranium_width, 1.0)
        self.assertEqual(head.cranium_height, 1.0)
        self.assertEqual(head.cheekbone_height, 0.5)
        self.assertEqual(head.chin_sharpness, 0.0)
        self.assertFalse(head.show_rhythm)
        self.assertEqual(head.rhythm_strength, 0.6)
        self.assertTrue(head.show_brow_guide)
        self.assertFalse(head.show_shadow)
        self.assertEqual(head.shadow_mode, 0)


if __name__ == "__main__":
    unittest.main()
