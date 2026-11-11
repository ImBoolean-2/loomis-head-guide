# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas del generador Loomis (sin Krita).

Ejecutar desde esta carpeta:
    python3 -m unittest test_generator.py -v
"""
import json
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
        head.set_head_sex(1)
        head.set_brow_ridge(0.8)
        head.set_eye_socket_depth(0.2)
        head.set_eye_socket_size(0.75)
        head.set_show_eye_socket(False)
        head.set_cheek_fullness(0.9)
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
        self.assertEqual(head.head_sex, 0)
        self.assertEqual(head.brow_ridge, 0.5)
        self.assertEqual(head.eye_socket_depth, 0.5)
        self.assertEqual(head.eye_socket_size, 0.55)
        self.assertTrue(head.show_eye_socket)
        self.assertEqual(head.cheek_fullness, 0.5)

    def test_dict_060_ignores_light_keys(self):
        # Preset de 0.6.0: trae claves de luz que 0.6.1 ya no usa.
        payload = LoomisHead3D().to_dict()
        payload.update({
            "lightAzimuth": 120.0,
            "lightElevation": -40.0,
            "lightIntensity": 0.8,
            "showShadow": True,
            "shadowMode": 1,
        })
        for key in ("headSex", "browRidge", "eyeSocketDepth", "eyeSocketSize",
                    "showEyeSocket", "cheekFullness"):
            payload.pop(key)
        head = LoomisHead3D()
        head.from_dict(payload)
        svg = head.build_svg(800, 800)
        self.assertIn("<svg", svg)
        self.assertNotIn("nan", svg.lower())
        self.assertFalse(hasattr(head, "light_azimuth"))
        self.assertFalse(hasattr(head, "show_shadow"))

    # --- 0.6.1: sexo, cuenca orbitaria, ceja y mejillas -------------------

    def test_sex_and_socket_defaults(self):
        head = LoomisHead3D()
        self.assertEqual(head.head_sex, 0)
        self.assertEqual(head.brow_ridge, 0.5)
        self.assertEqual(head.eye_socket_depth, 0.5)
        self.assertEqual(head.eye_socket_size, 0.55)
        self.assertTrue(head.show_eye_socket)
        self.assertEqual(head.cheek_fullness, 0.5)

    def test_sex_and_socket_clamps(self):
        head = LoomisHead3D()
        head.set_head_sex(7)
        self.assertEqual(head.head_sex, 1)
        head.set_head_sex(-3)
        self.assertEqual(head.head_sex, 0)
        head.set_brow_ridge(9)
        self.assertEqual(head.brow_ridge, 1.0)
        head.set_eye_socket_depth(-1)
        self.assertEqual(head.eye_socket_depth, 0.0)
        head.set_eye_socket_size(99)
        self.assertEqual(head.eye_socket_size, 0.9)
        head.set_eye_socket_size(0.0)
        self.assertEqual(head.eye_socket_size, 0.2)
        head.set_cheek_fullness(2)
        self.assertEqual(head.cheek_fullness, 1.0)
        head.set_show_eye_socket(False)
        self.assertFalse(head.show_eye_socket)

    def test_new_keys_in_dict(self):
        payload = LoomisHead3D().to_dict()
        for key in ("headSex", "browRidge", "eyeSocketDepth", "eyeSocketSize",
                    "showEyeSocket", "cheekFullness"):
            self.assertIn(key, payload)
        for key in ("lightAzimuth", "lightElevation", "lightIntensity",
                    "showShadow", "shadowMode"):
            self.assertNotIn(key, payload)

    def test_eye_socket_toggle(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        with_socket = head.build_svg(800, 800)
        head.set_show_eye_socket(False)
        without = head.build_svg(800, 800)
        self.assertLess(len(without), len(with_socket))
        self.assertNotIn("nan", without.lower())
        head.set_show_features(False)
        self.assertLess(len(head.build_svg(800, 800)), len(without))

    def test_eye_socket_hidden_without_features(self):
        head = LoomisHead3D()
        head.set_show_features(False)
        head.set_show_eye_socket(True)
        bare = head.build_svg(800, 800)
        head.set_show_eye_socket(False)
        self.assertEqual(bare, head.build_svg(800, 800))

    def test_eye_socket_depth_and_size_change_svg(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_eye_socket_depth(0.0)
        shallow = head.build_svg(800, 800)
        head.set_eye_socket_depth(1.0)
        deep = head.build_svg(800, 800)
        self.assertNotEqual(shallow, deep)
        head.set_eye_socket_size(0.2)
        small = head.build_svg(800, 800)
        head.set_eye_socket_size(0.9)
        big = head.build_svg(800, 800)
        self.assertNotEqual(small, big)
        for svg in (shallow, deep, small, big):
            self.assertNotIn("nan", svg.lower())
            self.assertNotIn("inf", svg.lower())

    def test_brow_ridge_changes_svg(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        head.set_brow_ridge(0.0)
        flat = head.build_svg(800, 800)
        head.set_brow_ridge(1.0)
        strong = head.build_svg(800, 800)
        self.assertNotEqual(flat, strong)
        self.assertNotIn("nan", strong.lower())

    def test_cheek_fullness_changes_svg(self):
        head = LoomisHead3D()
        head.set_show_face(True)
        head.set_cheek_fullness(0.0)
        lean = head.build_svg(800, 800)
        head.set_cheek_fullness(1.0)
        full = head.build_svg(800, 800)
        self.assertNotEqual(lean, full)
        self.assertNotIn("nan", full.lower())

    def test_socket_extremes_render(self):
        head = LoomisHead3D()
        head.set_show_features(True)
        cases = [
            (head.set_brow_ridge, (0.0, 1.0)),
            (head.set_eye_socket_depth, (0.0, 1.0)),
            (head.set_eye_socket_size, (0.2, 0.9)),
            (head.set_cheek_fullness, (0.0, 1.0)),
        ]
        for setter, values in cases:
            for value in values:
                setter(value)
                svg = head.build_svg(800, 800)
                self.assertIn("<svg", svg)
                self.assertNotIn("nan", svg.lower())
                self.assertNotIn("inf", svg.lower())


class PivotTests(unittest.TestCase):
    """El pivote Loomis es el centro de la esfera: ``pivot_local`` = origen."""

    def test_pivot_local_is_the_origin(self):
        head = LoomisHead3D()
        self.assertEqual(
            (head.pivot_local.x, head.pivot_local.y, head.pivot_local.z),
            (0.0, 0.0, 0.0),
        )
        self.assertEqual(head.pivot_local, Vector3(0.0, 0.0, 0.0))

    def test_pivot_projects_to_position_x_y(self):
        head = LoomisHead3D()
        head.set_scale(0.8)
        rotations = (
            q_axis_angle([0.0, 1.0, 0.0], 0.0),
            q_axis_angle([0.2, 1.0, -0.4], 1.3),
        )
        for x, y in ((0.0, 0.0), (510.0, 289.0)):
            head.set_position_x(x)
            head.set_position_y(y)
            for q in rotations:
                head.set_quaternion(q)
                point = head._to_screen(
                    head._to_camera([Vector3(0.0, 0.0, 0.0)]), 800.0, 640.0
                )[0]
                self.assertAlmostEqual(point.x, x, places=6)
                self.assertAlmostEqual(point.y, y, places=6)

    def test_sex_and_cranium_changes_keep_the_pivot(self):
        head = LoomisHead3D()
        head.set_position_x(400.0)
        head.set_position_y(320.0)
        seen = []
        for sex in (0, 1):
            for cranium in (0.6, 1.0, 1.6):
                for width in (0.8, 1.2):
                    head.set_head_sex(sex)
                    head.set_cranium(cranium)
                    head.set_cranium_width(width)
                    point = head._to_screen(
                        head._to_camera([Vector3(0.0, 0.0, 0.0)]), 800.0, 640.0
                    )[0]
                    seen.append((round(point.x, 6), round(point.y, 6)))
                    self.assertEqual((head.position_x, head.position_y), (400.0, 320.0))
        self.assertEqual(len(set(seen)), 1)

    def test_rotation_around_pivot_keeps_the_head_centered(self):
        """El centro del craneo no se desplaza al rotar (sin deriva por bounds)."""
        head = LoomisHead3D()
        head.set_position_x(500.0)
        head.set_position_y(400.0)
        first = head._to_screen(head._to_camera([Vector3(0.0, 0.0, 0.0)]), 900.0, 900.0)[0]
        head.set_quaternion(q_axis_angle([1.0, 0.0, 0.0], 0.7))
        second = head._to_screen(head._to_camera([Vector3(0.0, 0.0, 0.0)]), 900.0, 900.0)[0]
        self.assertAlmostEqual(first.x, second.x, places=6)
        self.assertAlmostEqual(first.y, second.y, places=6)


# --- Move/Transform manual (capa vectorial) ---------------------------------
#
# El docker no se puede instanciar fuera de Krita (necesita Qt y el dock), asi
# que estas pruebas montan un objeto con ``object.__new__`` y stubs minimos de
# ``krita``/``qt_compat``. Cubren el flujo real de ``draw_lines_with_vectors``:
# capturar la transformacion de los shapes viejos, reaplicarla a los nuevos y
# guardarla en el estado de la guia.

_plugin_module = None


class _FakePoint:
    def __init__(self, x=0.0, y=0.0):
        self._x = float(x)
        self._y = float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def __repr__(self):
        return f"({self._x}, {self._y})"


class _FakeRect:
    def __init__(self, x=0.0, y=0.0, width=0.0, height=0.0):
        self._x, self._y = float(x), float(y)
        self._w, self._h = float(width), float(height)

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._w

    def height(self):
        return self._h

    def isNull(self):
        return self._w == 0.0 and self._h == 0.0

    def isEmpty(self):
        return self._w <= 0.0 or self._h <= 0.0


class _FakeTransform:
    """QTransform afin 2D minimo: m11..dy, map y setMatrix."""

    def __init__(self, m11=1.0, m12=0.0, m21=0.0, m22=1.0, dx=0.0, dy=0.0):
        self._m = [float(v) for v in (m11, m12, m21, m22, dx, dy)]

    def m11(self):
        return self._m[0]

    def m12(self):
        return self._m[1]

    def m21(self):
        return self._m[2]

    def m22(self):
        return self._m[3]

    def dx(self):
        return self._m[4]

    def dy(self):
        return self._m[5]

    def map(self, point):
        x, y = point.x(), point.y()
        m11, m12, m21, m22, dx, dy = self._m
        return _FakePoint(m11 * x + m21 * y + dx, m12 * x + m22 * y + dy)

    def setMatrix(self, m11, m12, _m13, m21, m22, _m23, m31, m32, _m33):
        self._m = [float(v) for v in (m11, m12, m21, m22, m31, m32)]

    def translate(self, dx, dy):
        self._m[4] += float(dx)
        self._m[5] += float(dy)


class _FakeShape:
    def __init__(self, name="shape", box=(0.0, 0.0, 10.0, 10.0)):
        self._name = name
        self._box = _FakeRect(*box)
        self._transform = _FakeTransform()
        self.removed = False

    def name(self):
        return self._name

    def boundingBox(self):
        return self._box

    def transformation(self):
        return self._transform

    def absoluteTransformation(self):
        return self._transform

    def setTransformation(self, transform):
        self._transform = transform

    def remove(self):
        self.removed = True


class _FakeLayer:
    def __init__(self, shapes=None):
        self._shapes = list(shapes or [])
        self._parent = object()
        self.rects = []

    def parentNode(self):
        return self._parent

    def name(self):
        return "Loomis Head 1"

    def shapes(self):
        return [shape for shape in self._shapes if not shape.removed]

    def addShapesFromSvg(self, svg):
        import re

        match = re.search(r'id="loomis-pivot" cx="([-0-9.]+)" cy="([-0-9.]+)"', svg)
        if match is None:  # pragma: no cover - el SVG siempre trae el marcador
            raise AssertionError("el SVG no trae el marcador del pivote")
        cx, cy = float(match.group(1)), float(match.group(2))
        created = [
            _FakeShape("path-front", (cx - 40.0, cy - 40.0, 80.0, 80.0)),
            _FakeShape("path-back", (cx - 30.0, cy - 30.0, 60.0, 60.0)),
            _FakeShape("loomis-pivot", (cx - 0.5, cy - 0.5, 1.0, 1.0)),
        ]
        self._shapes.extend(created)
        return created

    def position(self):
        return _FakePoint(0.0, 0.0)

    def bounds(self):
        shapes = self.shapes()
        if not shapes:
            return _FakeRect()
        xs = [shape.boundingBox().x() for shape in shapes]
        ys = [shape.boundingBox().y() for shape in shapes]
        right = max(shape.boundingBox().x() + shape.boundingBox().width() for shape in shapes)
        bottom = max(shape.boundingBox().y() + shape.boundingBox().height() for shape in shapes)
        return _FakeRect(min(xs), min(ys), right - min(xs), bottom - min(ys))


class _FakeNode:
    def __init__(self, children=None):
        self._children = list(children or [])

    def childNodes(self):
        return self._children


class _FakeDoc:
    def __init__(self, width=2000, height=1000, layers=None):
        self._width = width
        self._height = height
        self._root = _FakeNode(layers or [])

    def width(self):
        return self._width

    def height(self):
        return self._height

    def rootNode(self):
        return self._root

    def fileName(self):
        return "unit.kra"


class _FakeSpinBox:
    def __init__(self, value=0):
        self._value = int(value)
        self.signals_blocked = False

    def value(self):
        return self._value

    def setValue(self, value):
        # QSignalBlocker no bloquea setValue, solo las senales.
        self._value = int(value)

    def blockSignals(self, blocked):
        self.signals_blocked = bool(blocked)
        return False


def _plugin():
    """Importa ``loomis_head_plugin`` con stubs de Qt y Krita (sin Krita)."""
    global _plugin_module
    if _plugin_module is not None:
        return _plugin_module

    class _Widget:
        def __init__(self, *args, **kwargs):
            pass

    class _Signal:
        def connect(self, *args, **kwargs):
            return None

    qt = types.ModuleType("loomis_head.qt_compat")
    qt.QtCore = types.SimpleNamespace(QPointF=_FakePoint, QLocale=None)
    qt.QtWidgets = types.SimpleNamespace(QSpinBox=_Widget)
    qt.QtGui = types.SimpleNamespace(QTransform=_FakeTransform)
    qt.QPointF = _FakePoint
    qt.QSpinBox = _Widget
    qt.QTransform = _FakeTransform
    qt.EXPANDING = object()
    qt.Qt = types.SimpleNamespace()
    qt.pyqtSignal = lambda *args, **kwargs: _Signal()
    qt.activated_index = lambda combo: _Signal()
    qt.activated_text = lambda combo: _Signal()
    qt.exec_dialog = lambda dialog: dialog.exec_()
    qt.uic = types.SimpleNamespace(loadUi=lambda *args, **kwargs: None)
    qt.QSignalBlocker = _Widget
    qt.QTimer = _Widget
    qt.QStandardPaths = types.SimpleNamespace(
        AppDataLocation="AppDataLocation",
        writableLocation=lambda *args, **kwargs: "/tmp/loomis-head-tests",
    )
    for name in (
        "QByteArray", "QCheckBox", "QColor", "QColorDialog", "QComboBox",
        "QFileDialog", "QFormLayout", "QFrame", "QGridLayout", "QGroupBox",
        "QHBoxLayout", "QLabel", "QPainter", "QScrollArea", "QSvgRenderer",
        "QSlider", "QStackedWidget", "QTabWidget", "QVBoxLayout", "QWidget",
        "QLocale",
    ):
        setattr(qt, name, _Widget)
    sys.modules.setdefault("loomis_head.qt_compat", qt)

    krita_stub = types.ModuleType("krita")
    krita_stub.DockWidget = _Widget
    krita_stub.Extension = _Widget
    krita_stub.DockWidgetFactory = _Widget
    krita_stub.DockWidgetFactoryBase = _Widget
    krita_stub.Krita = types.SimpleNamespace(
        instance=lambda: types.SimpleNamespace(activeDocument=lambda: None)
    )
    sys.modules.setdefault("krita", krita_stub)

    import importlib

    _plugin_module = importlib.import_module("loomis_head.loomis_head_plugin")
    return _plugin_module


class LayerTransformTests(unittest.TestCase):
    """El Move/Transform manual se captura, se reaplica y se persiste."""

    def setUp(self):
        import tempfile

        self.plugin = _plugin()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.model = LoomisHead3D()
        self.model.set_position_x(1660.0)
        self.model.set_position_y(447.0)
        self.layer = _FakeLayer([])
        self.doc = _FakeDoc(layers=[self.layer])
        self.docker = self._make_docker(self.layer, self.model, self.doc)

    def _make_docker(self, layer, model, doc, guides=True):
        plugin = self.plugin
        docker = object.__new__(plugin.LoomisProportionsDocker)
        docker.doc = doc
        docker.loomis_head = model
        docker.loomis_layer = layer
        docker.guides = [plugin.Guide(model, layer, "Loomis Head 1")] if guides else []
        docker.active_index = 0
        docker._manual_transform = plugin.IDENTITY_TRANSFORM
        docker._transform_pending_apply = False
        docker._pivot_shape = None
        docker._last_pivot_position = None
        docker._last_layer_position = None
        docker._last_layer_bounds_center = None
        docker._drawing = False
        docker.update_scheduled = False
        docker._doc_key = "unit.kra"
        docker._state = {"version": 1, "documents": {}}
        docker._guides_path = Path(self.tmp.name) / "guides.json"
        docker.ui = types.SimpleNamespace(
            positionXSpinBox=_FakeSpinBox(), positionYSpinBox=_FakeSpinBox()
        )
        docker._log_pivot = lambda text: None
        docker.schedule_update = lambda: None
        docker.ensure_guide = lambda: None
        # Dependencias de UI que ``_set_active_guide``/``_switch_model`` tocan;
        # aqui solo interesa la logica de transformacion.
        docker.trackball = types.SimpleNamespace(
            set_model=lambda model: None,
            set_quaternion=lambda q: None,
        )
        docker._sync_panels_for_model = lambda *args: None
        docker._sync_ui_from_model = lambda: None
        docker._sync_euler_from_model = lambda: None
        docker._refresh_guide_combo = lambda: None
        return docker

    def _move_by(self, dx, dy):
        """Simula la herramienta Move: la transformacion va a cada shape."""
        for shape in self.layer.shapes():
            shape.setTransformation(_FakeTransform(1.0, 0.0, 0.0, 1.0, dx, dy))

    def test_draw_keeps_the_manual_move(self):
        self.docker.draw_lines_with_vectors(samples=16)
        self._move_by(120.0, 60.0)

        self.docker.sync_manual_position()
        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))
        # El modelo (pivote) no se desplaza por el Move manual.
        self.assertEqual((self.model.position_x, self.model.position_y), (1660.0, 447.0))
        # X/Y visible = modelo + Move manual.
        self.assertEqual(self.docker.ui.positionXSpinBox.value(), 1780)
        self.assertEqual(self.docker.ui.positionYSpinBox.value(), 507)

        self.docker.draw_lines_with_vectors(samples=16)
        shapes = self.layer.shapes()
        self.assertTrue(shapes)
        for shape in shapes:
            self.assertAlmostEqual(shape.transformation().dx(), 120.0)
            self.assertAlmostEqual(shape.transformation().dy(), 60.0)
        self.assertEqual((self.model.position_x, self.model.position_y), (1660.0, 447.0))
        # El marcador reaplicado queda en la posicion efectiva.
        self.assertAlmostEqual(self.docker._last_pivot_position[0], 1780.0, places=3)
        self.assertAlmostEqual(self.docker._last_pivot_position[1], 507.0, places=3)
        self.assertEqual(self.docker.ui.positionXSpinBox.value(), 1780)

    def test_second_redraw_does_not_lose_the_manual_move(self):
        self.docker.draw_lines_with_vectors(samples=16)
        self._move_by(120.0, 60.0)
        self.docker.draw_lines_with_vectors(samples=16)

        # Rotacion + tipo/modelo: el siguiente dibujo no puede perder el Move.
        self.model.set_quaternion(q_axis_angle([0.0, 1.0, 0.0], 0.6))
        self.model.set_scale(0.7)
        self.docker.draw_lines_with_vectors(samples=16)

        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))
        for shape in self.layer.shapes():
            self.assertAlmostEqual(shape.transformation().dx(), 120.0)
            self.assertAlmostEqual(shape.transformation().dy(), 60.0)
        self.assertEqual((self.model.position_x, self.model.position_y), (1660.0, 447.0))
        self.assertAlmostEqual(self.docker._visible_position()[0], 1780.0)
        self.assertAlmostEqual(self.docker._visible_position()[1], 507.0)
        self.assertEqual(self.docker.ui.positionXSpinBox.value(), 1780)
        self.assertEqual(self.docker.ui.positionYSpinBox.value(), 507)

    def test_editing_xy_moves_the_model_not_the_manual_offset(self):
        self.docker.draw_lines_with_vectors(samples=16)
        self._move_by(120.0, 60.0)
        self.docker.sync_manual_position()

        self.docker._set_visible_position(x=1600.0, y=400.0)

        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))
        self.assertAlmostEqual(self.model.position_x, 1480.0)
        self.assertAlmostEqual(self.model.position_y, 340.0)
        self.assertAlmostEqual(self.docker._visible_position()[0], 1600.0)
        self.assertAlmostEqual(self.docker._visible_position()[1], 400.0)

    def test_save_and_load_keep_the_transform(self):
        self.docker.guides[0].manual_transform = (1.0, 0.0, 0.0, 1.0, 120.0, 60.0)
        self.docker._manual_transform = (1.0, 0.0, 0.0, 1.0, 120.0, 60.0)
        self.docker._save_doc_state()

        saved = json.loads(Path(self.tmp.name, "guides.json").read_text(encoding="utf-8"))
        entry = saved["documents"]["unit.kra"]["guides"][0]
        self.assertEqual(entry["transform"], [1.0, 0.0, 0.0, 1.0, 120.0, 60.0])

        other = self._make_docker(_FakeLayer([]), LoomisHead3D(), self.doc, guides=False)
        other._load_guides(self.doc, saved["documents"]["unit.kra"])
        self.assertEqual(len(other.guides), 1)
        self.assertEqual(other.guides[0].manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))

    def test_entry_without_transform_loads_identity(self):
        other = self._make_docker(_FakeLayer([]), LoomisHead3D(), self.doc, guides=False)
        entry = {"guides": [{"name": "Loomis Head 1", "state": {"scale": 0.5}}]}
        other._load_guides(self.doc, entry)
        self.assertEqual(len(other.guides), 1)
        self.assertEqual(other.guides[0].manual_transform, self.plugin.IDENTITY_TRANSFORM)

    def _stub_preset_dependencies(self):
        self.docker.trackball = types.SimpleNamespace(set_quaternion=lambda q: None)
        self.docker._sync_ui_from_model = lambda: None
        self.docker._sync_euler_from_model = lambda: None
        self.docker._sync_panels_for_model = lambda *args: None

    def test_preset_roundtrip_includes_the_layer_transform(self):
        self._stub_preset_dependencies()
        self.docker._manual_transform = (1.0, 0.0, 0.0, 1.0, -120.0, 0.0)
        self.docker.guides[0].manual_transform = (1.0, 0.0, 0.0, 1.0, -120.0, 0.0)

        captured = self.docker._capture_preset()
        self.assertEqual(captured["layerTransform"], [1.0, 0.0, 0.0, 1.0, -120.0, 0.0])

        data = dict(captured)
        data["layerTransform"] = [1.0, 0.0, 0.0, 1.0, 40.0, -20.0]
        self.docker.apply_preset(data)
        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 40.0, -20.0))
        self.assertEqual(
            self.docker.guides[0].manual_transform, (1.0, 0.0, 0.0, 1.0, 40.0, -20.0)
        )

    def test_preset_transform_survives_the_next_sync(self):
        self.docker.draw_lines_with_vectors(samples=16)
        self._move_by(120.0, 60.0)
        self.docker.sync_manual_position()
        self._stub_preset_dependencies()

        self.docker.apply_preset({
            "model": "loomis",
            "positionUnit": "normalized",
            "positionX": 0.5,
            "positionY": 0.5,
            "layerTransform": [1.0, 0.0, 0.0, 1.0, -40.0, -10.0],
        })
        # El sondeo de sync lee la transformacion del canvas: si el preset no se
        # hubiera aplicado tambien ahi, el Move viejo volveria.
        self.docker.sync_manual_position()

        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, -40.0, -10.0))
        for shape in self.layer.shapes():
            self.assertAlmostEqual(shape.transformation().dx(), -40.0)
            self.assertAlmostEqual(shape.transformation().dy(), -10.0)

    # --- 0.7.8: matriz completa, presets tolerantes, reapertura ------------

    @staticmethod
    def _rotated(degrees, dx=0.0, dy=0.0):
        angle = math.radians(degrees)
        return (
            math.cos(angle), math.sin(angle),
            -math.sin(angle), math.cos(angle),
            float(dx), float(dy),
        )

    def test_visible_xy_matches_the_marker_with_rotation(self):
        """X/Y es ``M·p + t``, no ``p + t`` (una capa rotada no engaña)."""
        self.docker._manual_transform = self._rotated(30.0)
        visible_x, visible_y = self.docker._visible_position()

        angle = math.radians(30.0)
        expected_x = math.cos(angle) * 1660.0 - math.sin(angle) * 447.0
        expected_y = math.sin(angle) * 1660.0 + math.cos(angle) * 447.0
        self.assertAlmostEqual(visible_x, expected_x, places=6)
        self.assertAlmostEqual(visible_y, expected_y, places=6)
        self.assertNotAlmostEqual(visible_x, 1660.0, places=1)

        # El marcador reaplicado queda en el punto que muestra el docker.
        self.docker.draw_lines_with_vectors(samples=16)
        self.assertAlmostEqual(self.docker._last_pivot_position[0], visible_x, places=3)
        self.assertAlmostEqual(self.docker._last_pivot_position[1], visible_y, places=3)

    def test_editing_xy_with_rotation_keeps_the_marker_at_the_value(self):
        """Editar X/Y invierte la parte lineal: el marcador cae en el valor."""
        self.docker._manual_transform = self._rotated(30.0)
        self.docker._set_visible_position(x=900.0, y=300.0)

        visible_x, visible_y = self.docker._visible_position()
        self.assertAlmostEqual(visible_x, 900.0, places=6)
        self.assertAlmostEqual(visible_y, 300.0, places=6)
        # No se llego por traslacion pura: el modelo no esta en el valor.
        self.assertFalse(
            math.isclose(self.model.position_x, 900.0)
            and math.isclose(self.model.position_y, 300.0)
        )

        # Editar solo X conserva la Y visible.
        self.docker._set_visible_position(x=1000.0)
        visible_x, visible_y = self.docker._visible_position()
        self.assertAlmostEqual(visible_x, 1000.0, places=6)
        self.assertAlmostEqual(visible_y, 300.0, places=6)

    def test_preset_with_non_numeric_position_does_not_raise(self):
        """``positionX: "abc"``/null/lista no lanza dentro del slot Qt."""
        self._stub_preset_dependencies()
        for value in ("abc", None, []):
            with self.subTest(value=value):
                self.docker.apply_preset({
                    "model": "loomis",
                    "positionUnit": "normalized",
                    "positionX": value,
                    "positionY": value,
                })
                self.assertAlmostEqual(self.model.position_x, 1000.0)
                self.assertAlmostEqual(self.model.position_y, 500.0)

    def test_malformed_guides_entry_is_ignored(self):
        """``{"guides": 5}`` o un ``center`` invalido no rompen la carga."""
        other = self._make_docker(_FakeLayer([]), LoomisHead3D(), self.doc, guides=False)
        other._load_guides(self.doc, {"guides": 5})
        self.assertEqual(len(other.guides), 1)
        self.assertEqual(other.guides[0].manual_transform, self.plugin.IDENTITY_TRANSFORM)

        other = self._make_docker(_FakeLayer([]), LoomisHead3D(), self.doc, guides=False)
        other._load_guides(
            self.doc, {"guides": [{"name": "Loomis Head 1", "center": "x"}]}
        )
        self.assertEqual(len(other.guides), 1)

    def test_saved_transform_survives_a_layer_with_identity_shapes(self):
        """Reabrir: capa a identidad + Move guardado conserva el Move."""
        layer = _FakeLayer([
            _FakeShape("path-front", (0.0, 0.0, 10.0, 10.0)),
            _FakeShape("path-back", (0.0, 0.0, 10.0, 10.0)),
        ])
        docker = self._make_docker(layer, self.model, self.doc)
        docker.guides[0].manual_transform = (1.0, 0.0, 0.0, 1.0, 120.0, 60.0)

        docker._set_active_guide(0)
        self.assertEqual(docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))
        self.assertTrue(docker._transform_pending_apply)

        # El sondeo ve identidad y no debe pisar el transform guardado.
        docker.sync_manual_position()
        self.assertEqual(docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))

        # El primer draw lo reaplica y limpia el pendiente.
        docker.draw_lines_with_vectors(samples=16)
        self.assertFalse(docker._transform_pending_apply)
        for shape in layer.shapes():
            self.assertAlmostEqual(shape.transformation().dx(), 120.0)
            self.assertAlmostEqual(shape.transformation().dy(), 60.0)

    def test_empty_layer_keeps_the_saved_transform(self):
        docker = self._make_docker(_FakeLayer([]), self.model, self.doc)
        docker.guides[0].manual_transform = (1.0, 0.0, 0.0, 1.0, -40.0, -20.0)

        docker._set_active_guide(0)
        self.assertEqual(docker._manual_transform, (1.0, 0.0, 0.0, 1.0, -40.0, -20.0))

        docker.draw_lines_with_vectors(samples=16)
        self.assertEqual(docker._manual_transform, (1.0, 0.0, 0.0, 1.0, -40.0, -20.0))
        self.assertAlmostEqual(docker._last_pivot_position[0], 1620.0, places=3)
        self.assertAlmostEqual(docker._last_pivot_position[1], 427.0, places=3)

    def test_capture_ignores_a_marker_with_its_own_transform(self):
        """El marcador del pivote no entra en el "transform mas comun"."""
        common = _FakeTransform(1.0, 0.0, 0.0, 1.0, 30.0, 40.0)
        marker = _FakeShape("loomis-pivot", (0.0, 0.0, 1.0, 1.0))
        marker.setTransformation(_FakeTransform(1.0, 0.0, 0.0, 1.0, 999.0, 999.0))
        first = _FakeShape("path-front", (0.0, 0.0, 10.0, 10.0))
        first.setTransformation(common)
        second = _FakeShape("path-back", (0.0, 0.0, 10.0, 10.0))
        second.setTransformation(common)

        captured = self.docker._capture_manual_transform(_FakeLayer([marker, first, second]))
        self.assertEqual(captured, (1.0, 0.0, 0.0, 1.0, 30.0, 40.0))

    def test_capture_returns_the_most_common_transform(self):
        common = _FakeTransform(1.0, 0.0, 0.0, 1.0, 10.0, 20.0)
        rare = _FakeTransform(1.0, 0.0, 0.0, 1.0, -10.0, -20.0)
        shapes = []
        for index in range(2):
            shape = _FakeShape(f"path-{index}", (0.0, 0.0, 10.0, 10.0))
            shape.setTransformation(common)
            shapes.append(shape)
        odd = _FakeShape("path-rare", (0.0, 0.0, 10.0, 10.0))
        odd.setTransformation(rare)
        shapes.append(odd)

        captured = self.docker._capture_manual_transform(_FakeLayer(shapes))
        self.assertEqual(captured, (1.0, 0.0, 0.0, 1.0, 10.0, 20.0))

    def test_preset_with_pixel_position_uses_it(self):
        """``positionUnit: "pixels"`` no se fuerza al centro."""
        self._stub_preset_dependencies()
        self.docker.apply_preset({
            "model": "loomis",
            "positionUnit": "pixels",
            "positionX": 123.0,
            "positionY": 456.0,
        })
        self.assertAlmostEqual(self.model.position_x, 123.0)
        self.assertAlmostEqual(self.model.position_y, 456.0)

    def test_preset_without_position_keeps_the_current_one(self):
        """Un preset sin positionX/Y (guardado sin documento) no salta a 0,0."""
        self._stub_preset_dependencies()
        self.docker.apply_preset({"model": "loomis", "scale": 0.5})
        self.assertAlmostEqual(self.model.position_x, 1660.0)
        self.assertAlmostEqual(self.model.position_y, 447.0)
        self.assertAlmostEqual(self.model.scale, 0.5)

    def test_preset_with_invalid_stroke_color_is_dropped(self):
        """Un color inyectado en un head JSON no llega al SVG."""
        self._stub_preset_dependencies()
        self.docker.apply_preset({
            "model": "loomis",
            "strokeColor": '#"><svg',
        })
        self.assertTrue(self.plugin._valid_stroke_color(self.model.stroke_color))
        self.assertNotIn('"', self.model.stroke_color)

    def test_loaded_state_with_invalid_stroke_color_is_sanitized(self):
        other = self._make_docker(_FakeLayer([]), LoomisHead3D(), self.doc, guides=False)
        other._load_guides(self.doc, {"guides": [{
            "name": "Loomis Head 1",
            "state": {"model": "loomis", "strokeColor": '#"><svg'},
        }]})
        self.assertEqual(len(other.guides), 1)
        self.assertTrue(
            self.plugin._valid_stroke_color(other.guides[0].model.stroke_color)
        )

    def test_reset_position_clears_the_transform_and_centers(self):
        self.docker.draw_lines_with_vectors(samples=16)
        self._move_by(120.0, 60.0)
        self.docker.sync_manual_position()
        self.docker.guides[0].manual_transform = self.docker._manual_transform

        self.docker.reset_position()

        self.assertEqual(self.docker._manual_transform, self.plugin.IDENTITY_TRANSFORM)
        self.assertEqual(
            self.docker.guides[0].manual_transform, self.plugin.IDENTITY_TRANSFORM
        )
        self.assertEqual((self.model.position_x, self.model.position_y), (1000.0, 500.0))
        for shape in self.layer.shapes():
            transform = shape.transformation()
            self.assertEqual(
                (transform.m11(), transform.m12(), transform.m21(),
                 transform.m22(), transform.dx(), transform.dy()),
                (1.0, 0.0, 0.0, 1.0, 0.0, 0.0),
            )
        self.assertFalse(self.docker._transform_pending_apply)

    def test_switch_model_keeps_position_scale_and_transform(self):
        """El bug de 0.7.7: cambiar Loomis<->Asaro no mueve la cabeza."""
        self.model.set_scale(0.63)
        self.docker._manual_transform = (1.0, 0.0, 0.0, 1.0, 120.0, 60.0)
        self.docker.guides[0].manual_transform = self.docker._manual_transform

        asaro = self.docker._switch_model("asaro")
        self.assertIsNotNone(asaro)
        self.assertEqual(self.docker._current_model_id(), "asaro")
        self.assertAlmostEqual(asaro.position_x, 1660.0)
        self.assertAlmostEqual(asaro.position_y, 447.0)
        self.assertAlmostEqual(asaro.scale, 0.63)
        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))

        loomis = self.docker._switch_model("loomis")
        self.assertIsNotNone(loomis)
        self.assertAlmostEqual(loomis.position_x, 1660.0)
        self.assertAlmostEqual(loomis.position_y, 447.0)
        self.assertAlmostEqual(loomis.scale, 0.63)
        self.assertEqual(self.docker._manual_transform, (1.0, 0.0, 0.0, 1.0, 120.0, 60.0))


class EventPositionTests(unittest.TestCase):
    """``preview.event_xy`` con los eventos de PyQt5 y PyQt6."""

    def test_event_xy_qt5_and_qt6(self):
        _plugin()
        from loomis_head.preview import event_xy

        class Qt6Event:
            def position(self):
                return _FakePoint(12.5, 34.5)

        class Qt5Event:
            def localPos(self):
                return _FakePoint(-3.0, 7.25)

        self.assertEqual(event_xy(Qt6Event()), (12.5, 34.5))
        self.assertEqual(event_xy(Qt5Event()), (-3.0, 7.25))


if __name__ == "__main__":
    unittest.main()
