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
    _HALF_CLOSED_FACES,
    _HALF_FACES,
    _HALF_FINE,
    _HALF_NECK_FACES,
    _HALF_VERTICES,
    _MIRROR,
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


def _all_half_faces() -> set[tuple[str, ...]]:
    """Todas las caras de la mitad derecha, en cualquier nivel de detalle."""
    faces = {names for _level, names in _HALF_FACES}
    faces |= {names for _level, names in _HALF_NECK_FACES}
    faces |= {names for _level, names in _HALF_CLOSED_FACES}
    for _original, _centre, halves in _HALF_FINE:
        faces |= set(halves)
    return faces


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
        counts = []
        for detail in (0, 1, 2):
            head.set_detail(detail)
            counts.append(len(head._faces()))
        self.assertLess(counts[0], counts[1])
        self.assertLess(counts[1], counts[2])
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
        head.set_show_neck(False)
        head.set_detail(2)
        data = head.to_dict()
        self.assertEqual(data["model"], "asaro")
        self.assertEqual(data["generator"], "asaro")
        self.assertEqual(data["version"], 1)
        self.assertIs(data["showNeck"], False)

        clone = AsaroHead()
        clone.from_dict(data)
        self.assertEqual(data, clone.to_dict())
        self.assertEqual(head.build_svg(800, 800), clone.build_svg(800, 800))

    def test_show_neck_toggle(self):
        head = AsaroHead()
        with_neck = len(head._faces())
        neck_svg = head.build_svg(800, 800)
        cap = frozenset(next(iter(_HALF_CLOSED_FACES))[1])
        facing_neck = {frozenset(names) for names in head._faces()}
        self.assertNotIn(cap, facing_neck)

        head.set_show_neck(False)
        without_neck = len(head._faces())
        no_neck_svg = head.build_svg(800, 800)
        self.assertLess(without_neck, with_neck)
        self.assertNotEqual(neck_svg, no_neck_svg)
        _valid_svg(self, neck_svg)
        _valid_svg(self, no_neck_svg)
        # Sin cuello no queda un agujero: el anillo de la mandibula se tapa.
        capped = {frozenset(names) for names in head._faces()}
        self.assertIn(cap, capped)
        used = {name for names in head._faces() for name in names}
        self.assertNotIn("G10", used)  # la base del busto ya no esta
        self.assertIn("F11", used)     # el borde de la mandibula sigue
        head.set_show_neck(True)
        self.assertEqual(len(head._faces()), with_neck)

    def test_closed_cap_matches_neck_ring(self):
        # El tapon sin cuello y la primera fila del cuello comparten anillo: si
        # se separan aparece una costura (hueco) al apagar el cuello.
        cap = next(names for _l, names in _HALF_CLOSED_FACES)
        neck_ring = set()
        for _level, names in _HALF_NECK_FACES:
            neck_ring |= set(names)
        self.assertTrue(set(cap) <= neck_ring, "el tapon no coincide con el anillo del cuello")

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
        head.set_show_neck(True)
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
        head.set_show_neck(False)
        for detail in (0, 1, 2):
            head.set_detail(detail)
            _valid_svg(self, head.build_svg(800, 800))

    def test_svg_follows_position_and_scale(self):
        head = AsaroHead()
        small = head.build_svg(800, 800)
        head.set_scale(2.0)
        big = head.build_svg(800, 800)
        self.assertNotEqual(small, big)
        _valid_svg(self, big)


class AsaroProportionTests(unittest.TestCase):
    """Proporciones del contrato 0.7.2 (unidades del modelo).

    Alto 1.5 (coronilla a base), ancho oreja a oreja 1.0, fondo 0.75; cara
    (ceja-menton) ~50 % del alto y cuello ~30 %. El fondo se compara con el
    alto de la cabeza sola (coronilla-menton), que es la proporcion craneal
    real (~0.7); contra el busto entero seria 0.5.
    """

    def bounds(self):
        xs = [p[0] for p in _VERTICES.values()]
        ys = [p[1] for p in _VERTICES.values()]
        zs = [p[2] for p in _VERTICES.values()]
        return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))

    def test_height_and_width(self):
        (x0, x1), (y0, y1), _zs = self.bounds()
        height = y1 - y0
        width = x1 - x0
        self.assertAlmostEqual(height, 1.5, places=6)
        self.assertAlmostEqual(width, 1.0, delta=0.02)
        self.assertAlmostEqual(height / width, 1.5, delta=0.15)

    def test_depth(self):
        _xs, (y0, y1), (z0, z1) = self.bounds()
        depth = z1 - z0
        self.assertAlmostEqual(depth, 0.75, delta=0.05)
        head_height = y1 - _VERTICES["F10"][1]  # coronilla -> menton
        self.assertAlmostEqual(depth / head_height, 0.7, delta=0.1)

    def test_face_and_neck_share_of_height(self):
        _xs, (y0, y1), _zs = self.bounds()
        height = y1 - y0
        face = _VERTICES["F2"][1] - _VERTICES["F10"][1]  # ceja -> menton
        neck = _VERTICES["F10"][1] - y0                  # menton -> base
        self.assertAlmostEqual(face / height, 0.5, delta=0.1)
        self.assertAlmostEqual(neck / height, 0.30, delta=0.06)

    def test_profile_landmarks_are_at_their_heights(self):
        # Ojo, nariz y boca tienen que caer donde caen en un craneo real.
        crown = _VERTICES["F0"][1]
        chin = _VERTICES["F10"][1]
        head = crown - chin
        eye = _VERTICES["G2"][1]
        nose_base = _VERTICES["F6"][1]
        mouth = _VERTICES["F8"][1]
        self.assertAlmostEqual((eye - chin) / head, 0.5, delta=0.1)
        self.assertAlmostEqual((nose_base - chin) / head, 0.33, delta=0.1)
        self.assertAlmostEqual((mouth - chin) / head, 0.16, delta=0.08)


class AsaroProfileTests(unittest.TestCase):
    """El perfil a 90 grados es el caso que hay que sostener: la silueta la
    forman las columnas centrales F (cara) y K (nuca), porque el resto queda
    detras. Un vertice "sobresale" si su profundidad gana a la recta que une
    ceja y menton.
    """

    def test_nose_protrudes(self):
        p = _profile(90.0)
        tip = p["F5"]
        plane = _chord_z(_HALF_VERTICES["F2"], _HALF_VERTICES["F10"], _HALF_VERTICES["F5"][1])
        self.assertGreaterEqual(tip.x - plane, 0.09, "la nariz no sobresale del plano ceja-menton")
        # La punta es el punto mas adelantado de toda la malla.
        self.assertAlmostEqual(tip.x, max(v.x for v in p.values()), places=6)
        # Muescas: bajo la punta (filtro) y sobre el dorso (nasion).
        self.assertGreaterEqual(tip.x - p["F6"].x, 0.10, "falta la muesca bajo la nariz")
        self.assertGreater(p["F4"].x, p["F3"].x, "el dorso debe arrancar por delante del nasion")

    def test_eye_socket_is_recessed(self):
        p = _profile(90.0)
        self.assertGreaterEqual(p["F2"].x - p["F3"].x, 0.06, "la ceja no vuela sobre el nasion")
        # La cuenca (G2/H2) queda por detras de la ceja y del pomulo.
        self.assertGreaterEqual(p["G1"].x - p["G2"].x, 0.09, "la cuenca no esta hundida")
        self.assertGreaterEqual(p["H3"].x - p["H2"].x, 0.10, "el pomulo no sobresale del borde orbitario")

    def test_lips_and_chin_step(self):
        p = _profile(90.0)
        self.assertGreater(p["F7"].x, p["F9"].x + 0.05, "los labios no ganan al surco")
        self.assertGreater(p["F10"].x, p["F9"].x + 0.03, "el menton queda metido")
        self.assertGreater(p["F10"].x, p["F11"].x + 0.12, "el menton no cierra bajo la mandibula")
        self.assertGreater(p["F11"].x - p["F12"].x, 0.10, "falta el hueco de la garganta")

    def test_occiput_is_curved(self):
        back = [_VERTICES[name][2] for name in ("K1", "K2", "K3", "K4", "K5", "K6")]
        # Del occipucio (K2) a la nuca la profundidad solo avanza hacia delante.
        self.assertEqual(back[1:], sorted(back[1:]), "la nuca no curva hacia el cuello")
        self.assertLess(back[1], back[0], "el occipucio no abomba por detras")
        self.assertLessEqual(_VERTICES["K3"][2], min(_VERTICES["K2"][2], _VERTICES["K4"][2]))
        self.assertGreater(back[-1] - back[0], 0.07, "la nuca es un plano vertical")
        # Coronilla: no cae en linea recta hasta el occipucio.
        bulge = _chord_z(_HALF_VERTICES["K0"], _HALF_VERTICES["K2"], _HALF_VERTICES["K1"][1])
        self.assertLessEqual(_HALF_VERTICES["K1"][2], bulge - 0.02)

    def test_ear_is_lateral_and_at_eye_height(self):
        widest = max(abs(p[0]) for p in _VERTICES.values())
        self.assertAlmostEqual(widest, abs(_VERTICES["E2"][0]), places=6)
        ear_top = max(_VERTICES[name][1] for name in ("E1", "E2", "E3", "E4"))
        ear_bottom = min(_VERTICES[name][1] for name in ("E1", "E2", "E3", "E4"))
        self.assertGreater(ear_top, _VERTICES["G2"][1])   # por encima del ojo
        self.assertGreater(ear_top, _VERTICES["F6"][1])   # por encima de la nariz
        self.assertLess(ear_bottom, _VERTICES["F6"][1])
        # La oreja sobresale de la pared lateral del craneo (J).
        self.assertGreater(_VERTICES["E2"][0], _VERTICES["J3"][0] + 0.03)

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

    def test_profile_outline_is_drawn(self):
        # La silueta (arista entre cara que mira a camara y cara que no) tiene
        # que estar dibujada o el perfil sale abierto.
        head = AsaroHead()
        head.set_quaternion(q_axis_angle([0, 1, 0], math.radians(90.0)))
        kinds = head._edge_kinds(head._faces())
        silhouettes = {(a, b) for a, b, kind in kinds if kind == "silhouette"}
        self.assertTrue(silhouettes)
        self.assertIn(("F4", "F5"), silhouettes)   # dorso -> punta
        self.assertIn(("K2", "K3"), silhouettes)   # occipucio


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
        for detail in (0, 1, 2):
            head.set_detail(detail)
            faces = head._faces()
            keys = {frozenset(face) for face in faces}
            for face in faces:
                self.assertIn(frozenset(_flip_name(n) for n in face), keys, f"{face} sin espejo")

    def test_no_degenerate_faces(self):
        head = AsaroHead()
        for detail in (0, 1, 2):
            head.set_detail(detail)
            for face in head._faces():
                self.assertGreaterEqual(len(face), 3, f"{face} tiene menos de un triangulo")
                self.assertEqual(len(set(face)), len(face), f"{face} repite vertices")
                self.assertGreater(_face_area(face), 1e-3, f"{face} degenerada")
                nx, ny, nz = head._face_normal(face)
                self.assertAlmostEqual(math.sqrt(nx * nx + ny * ny + nz * nz), 1.0, places=6)
                for name in face:
                    self.assertIn(name, _VERTICES)

    def test_no_dead_vertices(self):
        used = {name for names in _all_half_faces() for name in names}
        self.assertEqual(used, set(_HALF_VERTICES))

    def test_face_counts_per_detail(self):
        head = AsaroHead()
        counts = []
        for detail in (0, 1, 2):
            head.set_detail(detail)
            counts.append(len(head._faces()))
        self.assertGreaterEqual(counts[0], 40)
        self.assertLessEqual(counts[0], 62)
        self.assertGreaterEqual(counts[1], 60)   # contrato: 60-80 en detalle 1
        self.assertLessEqual(counts[1], 80)
        self.assertGreaterEqual(counts[2], counts[1] + 8)
        self.assertEqual(counts, sorted(set(counts)), "el detalle debe crecer")

    def test_neck_does_not_change_the_head(self):
        head = AsaroHead()
        head.set_show_neck(True)
        with_neck = {tuple(sorted(names)) for names in head._faces()}
        head.set_show_neck(False)
        without_neck = {tuple(sorted(names)) for names in head._faces()}
        # Lo unico que cambia es el cuello (fuera) y el tapon de la mandibula
        # (dentro): el craneo y la cara son las mismas caras.
        removed = without_neck - with_neck
        cap = next(iter(_HALF_CLOSED_FACES))[1]
        expected = {
            tuple(sorted(cap)),
            tuple(sorted(_MIRROR[name] for name in cap)),
        }
        self.assertEqual(removed, expected)
        self.assertTrue(with_neck - without_neck)

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
