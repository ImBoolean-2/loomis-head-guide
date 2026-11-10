# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas de la cabeza Asaro y del registro de modelos (sin Krita).

Ejecutar desde esta carpeta:
    python3 -m unittest test_asaro.py -v
"""
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# El paquete real importa krita en __init__.py; aqui solo probamos los modelos.
_pkg = types.ModuleType("loomis_head")
_pkg.__path__ = [str(Path(__file__).resolve().parent)]
sys.modules.setdefault("loomis_head", _pkg)

from loomis_head.asaro import EDGE_COLOR, PLANE_COLOR, AsaroHead  # noqa: E402
from loomis_head.linalg import q_axis_angle  # noqa: E402
from loomis_head.loomis_head_generator import LoomisHead3D  # noqa: E402
from loomis_head.models import (  # noqa: E402
    DEFAULT_MODEL,
    MODELS,
    create_model,
    supported_models,
)


def _valid_svg(test: unittest.TestCase, svg: str) -> None:
    test.assertIn("<svg", svg)
    test.assertTrue(svg.endswith("</svg>"))
    test.assertNotIn("nan", svg.lower())
    test.assertNotIn("inf", svg.lower())
    ET.fromstring(svg)  # XML bien formado


class AsaroTests(unittest.TestCase):
    def test_default_svg(self):
        svg = AsaroHead().build_svg(1000, 800)
        _valid_svg(self, svg)
        self.assertIn("<path", svg)

    def test_planes_and_edges_toggle(self):
        head = AsaroHead()
        both = head.build_svg(800, 800)
        head.set_show_edges(False)
        planes_only = head.build_svg(800, 800)
        self.assertLess(len(planes_only), len(both))
        head.set_show_planes(False)
        nothing = head.build_svg(800, 800)
        self.assertNotIn("<path", nothing)
        _valid_svg(self, nothing)
        head.set_show_edges(True)
        edges_only = head.build_svg(800, 800)
        _valid_svg(self, edges_only)
        self.assertNotIn('title="asaro-planes"', edges_only)
        self.assertIn('title="asaro-edges"', edges_only)

    def test_detail_levels(self):
        head = AsaroHead()
        head.set_detail(0)
        coarse = head.build_svg(800, 800)
        head.set_detail(1)
        standard = head.build_svg(800, 800)
        head.set_detail(2)
        fine = head.build_svg(800, 800)
        self.assertLess(len(coarse), len(standard))
        self.assertLess(len(standard), len(fine))
        for svg in (coarse, standard, fine):
            _valid_svg(self, svg)

    def test_rotation_changes_svg(self):
        head = AsaroHead()
        front = head.build_svg(800, 800)
        head.set_quaternion(q_axis_angle([0, 1, 0], 0.7))
        turned = head.build_svg(800, 800)
        self.assertNotEqual(front, turned)
        _valid_svg(self, turned)
        head.set_quaternion(q_axis_angle([1, 0, 0], -0.5))
        _valid_svg(self, head.build_svg(800, 800))

    def test_dict_roundtrip(self):
        head = AsaroHead()
        head.set_scale(1.4)
        head.set_position_x(320)
        head.set_position_y(210)
        head.set_quaternion(q_axis_angle([0, 1, 0], 0.4))
        head.set_front_line_stroke(12)
        head.set_back_line_stroke(5)
        head.set_stroke_color("#112233")
        head.set_zone_colors(True)
        head.set_show_planes(False)
        head.set_show_edges(True)
        head.set_detail(2)
        data = head.to_dict()
        self.assertEqual(data["model"], "asaro")
        self.assertEqual(data["generator"], "asaro")
        self.assertEqual(data["version"], 1)

        clone = AsaroHead()
        clone.from_dict(data)
        self.assertEqual(data, clone.to_dict())
        self.assertEqual(head.build_svg(800, 800), clone.build_svg(800, 800))

    def test_from_dict_tolerates_garbage(self):
        head = AsaroHead()
        head.from_dict({})
        _valid_svg(self, head.build_svg(800, 800))
        head.from_dict({"scale": "no", "rotation": [1, 2], "detail": None})
        _valid_svg(self, head.build_svg(800, 800))
        head.from_dict({"rotation": [0, 0, 0, 0], "strokeColor": "azul"})
        _valid_svg(self, head.build_svg(800, 800))
        self.assertEqual(head.model_id, "asaro")

    def test_from_dict_accepts_loomis_preset(self):
        # Un preset Loomis no debe romper la carga: se leen las claves comunes.
        loomis = LoomisHead3D()
        head = AsaroHead()
        head.from_dict(loomis.to_dict())
        self.assertEqual(head.model_id, "asaro")
        self.assertAlmostEqual(head.side_cut, loomis.side_cut)
        _valid_svg(self, head.build_svg(800, 800))

    def test_interface_setters(self):
        head = AsaroHead()
        head.set_scale(0.8)
        head.set_position_x(100)
        head.set_position_y(-50)
        head.set_quaternion(q_axis_angle([0, 0, 1], 0.2))
        head.set_front_line_stroke(9)
        head.set_back_line_stroke(6)
        head.set_stroke_color("#ABCDEF")
        head.set_zone_colors(True)
        head.set_sidecut(0.5)
        head.set_face_age(0.6)
        head.set_chin_width(1.2)
        head.set_show_face(False)
        head.set_arrow(False)
        head.set_silhouette(False)
        head.set_side_rims(False)
        head.set_side_cross(False)
        head.set_show_planes(True)
        head.set_show_edges(True)
        head.set_detail(1)
        svg = head.build_svg(800, 800)
        _valid_svg(self, svg)
        self.assertIn(PLANE_COLOR, svg)
        self.assertIn(EDGE_COLOR, svg)

    def test_clamps(self):
        head = AsaroHead()
        head.set_scale(0)
        self.assertGreaterEqual(head.scale, 0.05)
        head.set_scale(99)
        self.assertLessEqual(head.scale, 5.0)
        head.set_front_line_stroke(999)
        self.assertLessEqual(head.front_line_stroke, 60.0)
        head.set_back_line_stroke(0)
        self.assertGreaterEqual(head.back_line_stroke, 0.5)
        head.set_detail(9)
        self.assertEqual(head.detail, 2)
        head.set_detail(-4)
        self.assertEqual(head.detail, 0)
        head.set_position_x(float("nan"))
        self.assertTrue(head.position_x == head.position_x)  # no NaN

    def test_extremes_keep_svg_finite(self):
        head = AsaroHead()
        for scale in (0.05, 1.0, 5.0):
            for angle in (-3.0, 0.0, 3.0):
                head.set_scale(scale)
                head.set_quaternion(q_axis_angle([0, 1, 0], angle))
                _valid_svg(self, head.build_svg(800, 800))
                head.set_detail(2)
                _valid_svg(self, head.build_svg(1200, 400))

    def test_svg_follows_position_and_scale(self):
        head = AsaroHead()
        small = head.build_svg(800, 800)
        head.set_scale(2.0)
        big = head.build_svg(800, 800)
        self.assertNotEqual(small, big)
        _valid_svg(self, big)


class RegistryTests(unittest.TestCase):
    def test_registry_contents(self):
        self.assertEqual(MODELS["loomis"], LoomisHead3D)
        self.assertEqual(MODELS["asaro"], AsaroHead)
        self.assertEqual(DEFAULT_MODEL, "loomis")
        self.assertEqual(supported_models(), ("loomis", "asaro"))

    def test_create_model(self):
        self.assertIsInstance(create_model("loomis"), LoomisHead3D)
        self.assertIsInstance(create_model("asaro"), AsaroHead)
        self.assertIsInstance(create_model(" ASARO "), AsaroHead)
        self.assertIsInstance(create_model(), LoomisHead3D)
        self.assertIsNone(create_model("nope"))
        self.assertIsNone(create_model(""))
        self.assertIsNone(create_model(42))


if __name__ == "__main__":
    unittest.main()
