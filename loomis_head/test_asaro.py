# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas de la cabeza Asaro y del registro de modelos (sin Krita).

Ejecutar desde esta carpeta:
    python3 -m unittest test_asaro.py -v
"""
import math
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# El paquete real importa krita en __init__.py; aqui solo probamos los modelos.
_pkg = types.ModuleType("loomis_head")
_pkg.__path__ = [str(Path(__file__).resolve().parent)]
sys.modules.setdefault("loomis_head", _pkg)

from loomis_head.asaro import (  # noqa: E402
    EDGE_COLOR,
    PLANE_COLOR,
    _HALF_FACES,
    _HALF_VERTICES,
    _VERTICES,
    AsaroHead,
)
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


def _profile(angle_deg: float = 90.0) -> dict:
    """Proyecta la malla como la camara del perfil.

    Con el quaternion de 90 grados sobre Y la profundidad z pasa a ser la x de
    pantalla y la altura y se conserva, asi que ``p[name].x`` leido aqui es
    directamente "cuanto sobresale" cada vertice en el perfil.
    """
    head = AsaroHead()
    head.set_quaternion(q_axis_angle([0, 1, 0], math.radians(angle_deg)))
    return {name: head._to_camera(point) for name, point in _VERTICES.items()}


def _chord_z(a: tuple[float, float, float], b: tuple[float, float, float], y: float) -> float:
    """Profundidad de la recta a-b a la altura y (para medir si un punto sobresale)."""
    return a[2] + (y - a[1]) / (b[1] - a[1]) * (b[2] - a[2])


def _face_area(names) -> float:
    """Area de un poligono (abanico de triangulos), sin depender de que sea plano."""
    pts = [_VERTICES[name] for name in names]
    area = 0.0
    for i in range(1, len(pts) - 1):
        ax = [pts[i][k] - pts[0][k] for k in range(3)]
        bx = [pts[i + 1][k] - pts[0][k] for k in range(3)]
        cx = (
            ax[1] * bx[2] - ax[2] * bx[1],
            ax[2] * bx[0] - ax[0] * bx[2],
            ax[0] * bx[1] - ax[1] * bx[0],
        )
        area += 0.5 * math.sqrt(sum(c * c for c in cx))
    return area


def _flip_name(name: str) -> str:
    """Nombre del vertice espejado (los de x == 0 son su propio espejo)."""
    if name.endswith("L"):
        return name[:-1]
    if abs(_HALF_VERTICES[name][0]) < 1e-9:
        return name
    return name + "L"


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


class AsaroProfileTests(unittest.TestCase):
    """El perfil a 90 grados es el caso que la 0.7.0 aprobo flojo: parecia una
    piedra facetada porque la cara era un muro vertical (ceja y labio a la misma
    profundidad) y la nariz apenas sobresalia de el.

    Metrica (perfil): se proyecta con 90 grados sobre Y, de modo que x en
    pantalla == profundidad z. Un vertice "sobresale" si su x supera la recta
    ceja-menton; la nariz se lee si la punta (D5) les gana por >= 0.25, que es
    ~15 % de la profundidad del craneo (1.64) y deja una muesca visible bajo la
    punta y otra en el nasion. Antes de este cambio la ceja y el labio inferior
    estaban a la misma profundidad (diferencia 0.02) y el menton quedaba 0.06
    por detras del labio: eso era el muro que hacia parecer piedra al perfil.
    """

    def test_nose_protrudes_from_brow_chin_plane(self):
        p = _profile(90.0)
        tip = p["D5"]
        face_plane = max(p["B1"].x, p["G2"].x)  # glabela / menton
        self.assertGreaterEqual(
            tip.x - face_plane,
            0.25,
            f"la nariz solo sobresale {tip.x - face_plane:.3f} del plano ceja-menton",
        )
        # La punta es el punto mas adelantado de toda la malla en el perfil.
        self.assertAlmostEqual(tip.x, max(v.x for v in p.values()), places=6)
        # Muesca bajo la punta (subnasal) y por encima del dorso (nasion).
        self.assertGreaterEqual(tip.x - p["D6"].x, 0.12, "falta la muesca bajo la nariz")
        self.assertGreater(p["D2"].x, p["D1"].x, "el dorso debe arrancar por delante del nasion")

    def test_face_is_not_a_flat_wall(self):
        # Sin contar la nariz: ceja, cuenca, pomulo y labio deben estar a
        # profundidades distintas o el perfil vuelve a leerse como un bloque.
        p = _profile(90.0)
        non_nose = [p[name].x for name in ("B1", "C1", "E2", "F3")]
        spread = max(non_nose) - min(non_nose)
        self.assertGreaterEqual(
            spread, 0.15, f"ceja/cuenca/pomulo/labio casi al ras ({spread:.3f})"
        )
        # Cuenca hundida respecto de la ceja.
        self.assertGreaterEqual(p["B1"].x - p["C1"].x, 0.12, "la cuenca no esta hundida")
        # El menton gana al labio inferior (antes quedaba por detras).
        self.assertGreater(p["G2"].x, p["F5"].x + 0.03, "el menton queda metido")
        # El labio inferior retrocede respecto de la ceja (antes eran iguales).
        self.assertGreaterEqual(p["B1"].x - p["F5"].x, 0.06)

    def test_cranium_and_chin_have_curves(self):
        p = _profile(90.0)
        # Occipucio: el vertice de la nuca alta sobresale de la cuerda I9-I6.
        bulge = _chord_z(_HALF_VERTICES["I9"], _HALF_VERTICES["I6"], _HALF_VERTICES["I13"][1])
        self.assertLessEqual(
            _HALF_VERTICES["I13"][2],
            bulge - 0.05,
            "la coronilla cae en linea recta hasta el occipucio",
        )
        # Nuca: baja y avanza hacia el cuello en pasos, no en un unico plano.
        nape = [p[name].x for name in ("I10", "I12", "I11", "I8")]
        self.assertEqual(nape, sorted(nape), "la nuca no curva hacia el cuello")
        self.assertGreater(nape[-1] - nape[0], 0.35, "la nuca es un plano vertical")
        # Menton: surco -> barba -> bajo el menton, con el punto medio adelantado.
        self.assertGreater(p["G2"].x, p["G5"].x + 0.08, "falta el escalon del menton")
        self.assertGreater(p["G2"].x, p["G3"].x + 0.15, "el menton no cierra en curva")

    def test_profile_and_threequarter_svg_are_valid(self):
        head = AsaroHead()
        for angle in (90.0, 45.0):
            head.set_quaternion(q_axis_angle([0, 1, 0], math.radians(angle)))
            for detail in (0, 1, 2):
                head.set_detail(detail)
                svg = head.build_svg(800, 800)
                _valid_svg(self, svg)
                self.assertIn("<path", svg)
                self.assertIn('title="asaro-planes"', svg)
                self.assertIn('title="asaro-edges"', svg)


class AsaroMeshTests(unittest.TestCase):
    """Integridad de la malla: simetrica, sin caras degeneradas ni vertices muertos."""

    def test_vertex_symmetry(self):
        central = 0
        for name, (x, y, z) in _HALF_VERTICES.items():
            mirror = _VERTICES[_flip_name(name)]
            self.assertAlmostEqual(mirror[0], -x, places=9, msg=name)
            self.assertAlmostEqual(mirror[1], y, places=9, msg=name)
            self.assertAlmostEqual(mirror[2], z, places=9, msg=name)
            if abs(x) < 1e-9:
                central += 1
        self.assertEqual(len(_VERTICES), 2 * len(_HALF_VERTICES) - central)

    def test_faces_are_mirrored(self):
        head = AsaroHead()
        head.set_detail(2)
        faces = head._faces()
        keys = {frozenset(face) for face in faces}
        for face in faces:
            self.assertIn(frozenset(_flip_name(n) for n in face), keys, f"{face} sin espejo")

    def test_no_degenerate_faces(self):
        head = AsaroHead()
        head.set_detail(2)
        for face in head._faces():
            self.assertGreaterEqual(len(face), 3, f"{face} tiene menos de un triangulo")
            self.assertEqual(len(set(face)), len(face), f"{face} repite vertices")
            self.assertGreater(_face_area(face), 1e-3, f"{face} degenerada")
            nx, ny, nz = head._face_normal(face)
            self.assertAlmostEqual(math.sqrt(nx * nx + ny * ny + nz * nz), 1.0, places=6)
            for name in face:
                self.assertIn(name, _VERTICES)

    def test_no_dead_vertices(self):
        used = {name for _level, names in _HALF_FACES for name in names}
        self.assertEqual(used, set(_HALF_VERTICES))

    def test_face_counts_per_detail(self):
        head = AsaroHead()
        counts = []
        for detail in (0, 1, 2):
            head.set_detail(detail)
            counts.append(len(head._faces()))
        self.assertGreaterEqual(counts[0], 14)  # 24 de referencia, +-10
        self.assertLessEqual(counts[0], 34)
        self.assertGreaterEqual(counts[1], 42)
        self.assertLessEqual(counts[1], 62)
        self.assertGreaterEqual(counts[2], 52)
        self.assertLessEqual(counts[2], 72)
        self.assertEqual(counts, sorted(set(counts)), "el detalle debe crecer")

    def test_all_vertices_are_finite(self):
        for name, point in _VERTICES.items():
            for value in point:
                self.assertTrue(math.isfinite(value), f"{name} tiene un valor no finito")


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
