# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas de la cabeza Asaro y del registro de modelos (sin Krita).

La malla ya no se dibuja a mano: es una decimacion del OBJ real guardada en
``asaro_mesh``. Las pruebas miden la malla (proporciones, perfil, cuello) y el
SVG (toggles, relleno de planos, ida y vuelta del preset).

Ejecutar desde esta carpeta:
    python3 -m unittest test_asaro.py -v
"""
import math
import re
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

# El paquete real importa krita en __init__.py; aqui solo probamos los modelos.
_pkg = types.ModuleType("loomis_head")
_pkg.__path__ = [str(Path(__file__).resolve().parent)]
sys.modules.setdefault("loomis_head", _pkg)

from loomis_head import asaro_mesh  # noqa: E402
from loomis_head.asaro import (  # noqa: E402
    EDGE_COLOR,
    PLANE_COLOR,
    _SHADE_TONES,
    AsaroHead,
    _newell,
)
from loomis_head.linalg import q_axis_angle  # noqa: E402
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


def _profile_depth(point: tuple[float, float, float]) -> float:
    """Cuanto sobresale un vertice hacia delante (la cara mira a +z)."""
    return point[2]


def _band(vertices, low: float, high: float, half_width: float = 0.12):
    """Vertices de una franja de altura cerca del plano sagital."""
    return [p for p in vertices if low <= p[1] < high and abs(p[0]) < half_width]


def _front(vertices, low: float, high: float) -> float:
    """Profundidad maxima (lo que mas sobresale) en una franja de altura."""
    band = _band(vertices, low, high)
    return max((p[2] for p in band), default=float("-inf"))


def _face_area(vertices, face) -> float:
    """Area de un poligono (abanico de triangulos), sin depender de que sea plano."""
    pts = [vertices[i] for i in face]
    area = 0.0
    for i in range(1, len(pts) - 1):
        ax = [pts[i][k] - pts[0][k] for k in range(3)]
        bx = [pts[i + 1][k] - pts[0][k] for k in range(3)]
        cross = (
            ax[1] * bx[2] - ax[2] * bx[1],
            ax[2] * bx[0] - ax[0] * bx[2],
            ax[0] * bx[1] - ax[1] * bx[0],
        )
        area += 0.5 * math.sqrt(sum(c * c for c in cross))
    return area


def _edge_use(faces) -> dict[tuple[int, int], int]:
    use: dict[tuple[int, int], int] = {}
    for face in faces:
        n = len(face)
        for i in range(n):
            a, b = face[i], face[(i + 1) % n]
            key = (a, b) if a < b else (b, a)
            use[key] = use.get(key, 0) + 1
    return use


class AsaroMeshDataTests(unittest.TestCase):
    """Integridad de los datos de la malla decimada."""

    def test_levels_and_counts(self):
        self.assertEqual(asaro_mesh.LEVEL_COUNT, 3)
        self.assertEqual([d["detail"] for d in asaro_mesh.ASARO_LEVELS], [0, 1, 2])
        heads = [d["head_faces"] for d in asaro_mesh.ASARO_LEVELS]
        # Contrato 0.7.3: ~200-300, ~400-600 y ~800-1200 caras de cabeza.
        self.assertGreaterEqual(heads[0], 200)
        self.assertLessEqual(heads[0], 300)
        self.assertGreaterEqual(heads[1], 400)
        self.assertLessEqual(heads[1], 600)
        self.assertGreaterEqual(heads[2], 800)
        self.assertLessEqual(heads[2], 1200)
        self.assertEqual(heads, sorted(set(heads)), "el detalle debe crecer")

    def test_every_level_has_neck_and_cap(self):
        for data in asaro_mesh.ASARO_LEVELS:
            total = len(data["faces"])
            self.assertGreater(total, data["head_faces"], "falta el cuello")
            self.assertTrue(data["cap"], "falta el tapon del corte")
            self.assertEqual(data["detail"], asaro_mesh.ASARO_LEVELS.index(data))

    def test_vertices_are_finite(self):
        for data in asaro_mesh.ASARO_LEVELS:
            for point in data["verts"]:
                self.assertEqual(len(point), 3)
                for value in point:
                    self.assertTrue(math.isfinite(value), f"{point} no es finito")

    def test_faces_are_valid(self):
        for data in asaro_mesh.ASARO_LEVELS:
            verts = data["verts"]
            for face in data["faces"]:
                self.assertGreaterEqual(len(face), 3, f"{face} tiene menos de un triangulo")
                self.assertEqual(len(set(face)), len(face), f"{face} repite vertices")
                for index in face:
                    self.assertTrue(0 <= index < len(verts), f"{face} apunta fuera de la malla")
                self.assertGreater(_face_area(verts, face), 1e-5, f"{face} degenerada")
                nx, ny, nz = _newell([verts[i] for i in face])
                self.assertAlmostEqual(math.sqrt(nx * nx + ny * ny + nz * nz), 1.0, places=6)

    def test_no_duplicate_faces(self):
        for data in asaro_mesh.ASARO_LEVELS:
            seen = set()
            for face in data["faces"]:
                key = frozenset(face)
                self.assertNotIn(key, seen, f"cara repetida {face}")
                seen.add(key)

    def test_cap_faces_are_valid(self):
        for data in asaro_mesh.ASARO_LEVELS:
            verts = data["verts"]
            for face in data["cap"]:
                self.assertEqual(len(set(face)), 3, f"{face} no es un triangulo")
                for index in face:
                    self.assertTrue(0 <= index < len(verts))
                nx, ny, nz = _newell([verts[i] for i in face])
                self.assertLess(ny, 0.0, f"{face} no mira hacia abajo")
                # El tapon va en el plano del corte, no repartido por la cabeza.
                for index in face:
                    self.assertLess(verts[index][1], data["neck_y"] + 0.15)

    def test_cap_closes_the_neck_cut(self):
        """El tapon cubre el borde del corte de cuello.

        La decimacion deja ademas grietas de junctions en T por toda la
        superficie; esas no se tapan (no son el corte) y se cuentan aparte.
        """
        for data in asaro_mesh.ASARO_LEVELS:
            verts = data["verts"]
            head = data["faces"][:data["head_faces"]]
            use = _edge_use(head)
            border = {edge for edge, count in use.items() if count == 1}
            cut = {
                edge for edge in border
                if all(verts[i][1] < data["neck_y"] + 0.10 for i in edge)
            }
            self.assertTrue(cut, "no hay borde de corte")
            self.assertFalse(cut - set(_edge_use(data["cap"])), "el tapon no cubre el corte")

    def test_no_dead_vertices(self):
        for data in asaro_mesh.ASARO_LEVELS:
            used = {index for face in data["faces"] for index in face}
            cap_used = {index for face in data["cap"] for index in face}
            self.assertEqual(used | cap_used, set(range(len(data["verts"]))))

    def test_neck_y_matches_the_declared_plane(self):
        self.assertLess(asaro_mesh.NECK_Y, 0.0)
        for data in asaro_mesh.ASARO_LEVELS:
            self.assertAlmostEqual(data["neck_y"], asaro_mesh.NECK_Y, delta=0.01)

    def test_neck_flag_is_the_cut(self):
        for data in asaro_mesh.ASARO_LEVELS:
            verts = data["verts"]
            flags = asaro_mesh.neck_flags(data["detail"])
            self.assertEqual(len(flags), len(data["faces"]))
            for face, is_neck in zip(data["faces"], flags):
                height = sum(verts[i][1] for i in face) / len(face)
                if is_neck:
                    self.assertLess(height, data["neck_y"] + 1e-6, f"{face} deberia ser cuello")
                else:
                    self.assertGreaterEqual(height, data["neck_y"] - 1e-6)


class AsaroProportionTests(unittest.TestCase):
    """Proporciones medidas sobre la malla normalizada (alto 1.5)."""

    def bounds(self, detail: int = 2):
        head = AsaroHead()
        head.set_detail(detail)
        verts = head._vertices()
        xs = [p[0] for p in verts]
        ys = [p[1] for p in verts]
        zs = [p[2] for p in verts]
        return (min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs))

    def test_height_is_exactly_the_contract_height(self):
        for detail in (0, 1, 2):
            _xs, (y0, y1), _zs = self.bounds(detail)
            self.assertAlmostEqual(y1 - y0, asaro_mesh.HEIGHT, places=6)
            self.assertAlmostEqual(y0, -asaro_mesh.HEIGHT / 2, places=6)

    def test_width_and_depth(self):
        (x0, x1), _ys, (z0, z1) = self.bounds()
        width = x1 - x0
        depth = z1 - z0
        # Ancho oreja a oreja y fondo nariz-occipucio del busto real.
        self.assertAlmostEqual(width, 0.80, delta=0.05)
        self.assertAlmostEqual(depth, 0.99, delta=0.05)
        self.assertAlmostEqual(depth / width, 1.24, delta=0.1)
        self.assertAlmostEqual(x0, -x1, places=5, msg="la malla no esta centrada en x")

    def test_head_and_neck_share_of_height(self):
        _xs, (y0, y1), _zs = self.bounds()
        height = y1 - y0
        head = y1 - asaro_mesh.NECK_Y
        neck = asaro_mesh.NECK_Y - y0
        self.assertAlmostEqual(head / height, 0.63, delta=0.03)
        self.assertAlmostEqual(neck / height, 0.37, delta=0.03)

    def test_depth_is_bigger_than_width(self):
        _xs, (y0, y1), (z0, z1) = self.bounds()
        self.assertGreater(z1 - z0, (y1 - y0) * 0.6, "el craneo es una losa")

    def test_levels_share_the_same_scale(self):
        heights = []
        for detail in (0, 1, 2):
            _xs, (y0, y1), _zs = self.bounds(detail)
            heights.append(y1 - y0)
        for height in heights:
            self.assertAlmostEqual(height, heights[2], delta=0.001)


class AsaroProfileTests(unittest.TestCase):
    """El perfil a 90 grados: la silueta la forman los vertices centrales."""

    def setUp(self):
        self.head = AsaroHead()
        self.head.set_detail(2)
        self.verts = self.head._vertices()

    def test_nose_protrudes(self):
        tip = _front(self.verts, 0.13, 0.21)   # punta de la nariz
        brow = _front(self.verts, 0.27, 0.33)  # ceja
        lips = _front(self.verts, -0.09, 0.0)  # labios
        chin = _front(self.verts, -0.19, -0.11)
        self.assertGreaterEqual(tip, 0.48, "la malla no tiene punta de nariz")
        self.assertGreaterEqual(tip - brow, 0.04, "la nariz no sobresale de la ceja")
        self.assertGreaterEqual(tip - lips, 0.06, "la nariz no sobresale de los labios")
        self.assertLess(chin, tip - 0.08, "el menton queda por delante de la nariz")

    def test_nose_tip_is_the_frontmost_vertex(self):
        widest = max(self.verts, key=lambda p: p[2])
        self.assertGreater(widest[2], 0.48)
        self.assertAlmostEqual(widest[1], 0.17, delta=0.06, msg="la punta no esta a la altura de la nariz")

    def test_lips_and_chin_step(self):
        lips = _front(self.verts, -0.09, 0.0)
        chin = _front(self.verts, -0.19, -0.11)
        throat = _front(self.verts, -0.24, -0.19)
        self.assertGreater(lips, chin - 0.05, "los labios no ganan al menton")
        self.assertGreater(chin, 0.30, "el menton no existe en el perfil")
        self.assertLess(throat, chin, "falta la muesca bajo el menton")

    def test_occiput_is_the_back_of_the_head(self):
        back = min(self.verts, key=lambda p: p[2])
        self.assertLess(back[2], -0.45)
        self.assertTrue(0.1 < back[1] < 0.35, "el occipucio no esta a la altura del craneo")

    def test_skull_is_round_not_a_box(self):
        # A media altura del craneo el fondo tiene que abombar: mas fondo que
        # en la coronilla y que en la nuca.
        mid = min(_band(self.verts, 0.15, 0.30, 0.2), key=lambda p: p[2])[2]
        crown = min(_band(self.verts, 0.55, 0.70, 0.2), key=lambda p: p[2])[2]
        neck = min(_band(self.verts, -0.30, -0.20, 0.2), key=lambda p: p[2])[2]
        self.assertLess(mid, crown)
        self.assertLess(mid, neck)

    def test_ear_is_lateral_and_at_eye_height(self):
        widest = max(self.verts, key=lambda p: abs(p[0]))
        self.assertGreaterEqual(abs(widest[0]), 0.39)
        self.assertTrue(0.10 < widest[1] < 0.32, "la oreja no esta a la altura del ojo")
        self.assertLess(widest[2], 0.0, "la oreja no va detras de la cara")
        skull_top = max(abs(p[0]) for p in self.verts if p[1] > 0.55)
        self.assertGreater(abs(widest[0]) - skull_top, 0.05, "la oreja no sobresale del craneo")

    def test_profile_and_threequarter_svg_are_valid(self):
        for angle in (90.0, 45.0):
            self.head.set_quaternion(q_axis_angle([0, 1, 0], math.radians(angle)))
            for detail in (0, 1, 2):
                self.head.set_detail(detail)
                svg = self.head.build_svg(800, 800)
                _valid_svg(self, svg)
                self.assertIn("<path", svg)
                self.assertIn('title="asaro-planes"', svg)
                self.assertIn('title="asaro-edges"', svg)

    def test_profile_outline_is_drawn(self):
        # La silueta (arista entre cara que mira a camara y cara que no) tiene
        # que estar dibujada o el perfil sale abierto.
        self.head.set_quaternion(q_axis_angle([0, 1, 0], math.radians(90.0)))
        kinds = self.head._edge_kinds(self.head._faces())
        silhouettes = {(a, b) for a, b, kind in kinds if kind == "silhouette"}
        self.assertTrue(silhouettes)
        # Todas las aristas de la silueta son pliegues del contorno: su cara
        # visible tiene que estar en el borde de la proyeccion.
        verts = self.verts
        xs = [verts[i][2] for a, b in silhouettes for i in (a, b)]
        self.assertGreater(max(xs) - min(xs), 0.5, "la silueta no recorre el perfil")


class AsaroHeadTests(unittest.TestCase):
    """Interfaz del modelo: toggles, preset y SVG."""

    def test_default_svg(self):
        svg = AsaroHead().build_svg(1000, 800)
        _valid_svg(self, svg)
        self.assertIn("<path", svg)

    def test_detail_levels_change_the_svg(self):
        head = AsaroHead()
        svgs = []
        for detail in (0, 1, 2):
            head.set_detail(detail)
            svgs.append(head.build_svg(800, 800))
        self.assertEqual(len(set(svgs)), 3, "el detalle no cambia el dibujo")
        self.assertLess(len(svgs[0]), len(svgs[1]))
        self.assertLess(len(svgs[1]), len(svgs[2]))

    def test_show_planes_toggles_the_face_outlines(self):
        head = AsaroHead()
        with_planes = head.build_svg(800, 800)
        head.set_show_planes(False)
        without = head.build_svg(800, 800)
        self.assertIn('title="asaro-planes"', with_planes)
        self.assertNotIn('title="asaro-planes"', without)
        _valid_svg(self, without)

    def test_show_edges_toggles_the_lines(self):
        head = AsaroHead()
        with_edges = head.build_svg(800, 800)
        head.set_show_edges(False)
        without = head.build_svg(800, 800)
        self.assertIn('title="asaro-edges"', with_edges)
        self.assertNotIn('title="asaro-edges"', without)
        _valid_svg(self, without)

    def test_shade_planes_toggles_the_fill(self):
        head = AsaroHead()
        self.assertTrue(head.shade_planes)
        filled = head.build_svg(800, 800)
        self.assertIn("fill-opacity", filled)
        self.assertIn('title="asaro-shade-frontal"', filled)
        head.set_shade_planes(False)
        plain = head.build_svg(800, 800)
        self.assertNotIn("fill-opacity", plain)
        self.assertNotIn("asaro-shade", plain)
        # Sin relleno el dibujo pesa menos, pero las aristas siguen.
        self.assertLess(len(plain), len(filled))
        self.assertIn('title="asaro-edges"', plain)

    def test_shade_uses_orientation_not_light(self):
        # Cuatro tonos planos por azimut, con la opacidad del contrato.
        self.assertEqual(len(_SHADE_TONES), 4)
        for _name, colour, opacity, _limit in _SHADE_TONES:
            self.assertTrue(0.18 <= opacity <= 0.28, opacity)
            self.assertTrue(colour.startswith("#") and len(colour) == 7)
        svg = AsaroHead().build_svg(800, 800)
        for name, _colour, opacity, _limit in _SHADE_TONES:
            if f'asaro-shade-{name}' in svg:
                self.assertIn(f'fill-opacity="{opacity}"', svg)

    def test_show_neck_toggles_the_bust(self):
        head = AsaroHead()
        with_neck = head.build_svg(800, 800)
        faces_with = len(head._faces())
        head.set_show_neck(False)
        without = head.build_svg(800, 800)
        faces_without = len(head._faces())
        self.assertLess(faces_without, faces_with)
        self.assertEqual(faces_without, head._level()["head_faces"] + len(head._level()["cap"]))
        self.assertGreater(len(with_neck), len(without))
        _valid_svg(self, without)
        self.assertTrue(head._neck_faces())

    def test_show_neck_keeps_the_head_closed(self):
        # Con el cuello oculto no queda agujero: el tapon va en el corte.
        head = AsaroHead()
        head.set_show_neck(False)
        faces = head._faces()
        bottom = [f for f in faces[-len(head._level()["cap"]):]]
        self.assertTrue(bottom)
        verts = head._vertices()
        lowest = min(sum(verts[i][1] for i in f) / 3.0 for f in bottom)
        self.assertLess(lowest, asaro_mesh.NECK_Y + 0.01)

    def test_rotation_changes_svg(self):
        head = AsaroHead()
        front = head.build_svg(800, 800)
        head.set_quaternion(q_axis_angle([0, 1, 0], math.radians(90.0)))
        profile = head.build_svg(800, 800)
        self.assertNotEqual(front, profile)
        _valid_svg(self, profile)

    def test_dict_roundtrip(self):
        head = AsaroHead()
        head.set_detail(0)
        head.set_show_neck(False)
        head.set_shade_planes(False)
        head.set_show_planes(False)
        head.set_show_edges(True)
        head.set_scale(1.4)
        head.set_position_x(30.0)
        head.set_position_y(-12.0)
        head.set_quaternion(q_axis_angle([0, 0, 1], math.radians(30.0)))
        data = head.to_dict()
        self.assertIn("showNeck", data)
        self.assertIn("shadePlanes", data)
        self.assertFalse(data["showNeck"])
        self.assertFalse(data["shadePlanes"])

        other = AsaroHead()
        other.from_dict(data)
        self.assertEqual(other.detail, 0)
        self.assertFalse(other.show_neck)
        self.assertFalse(other.shade_planes)
        self.assertFalse(other.show_planes)
        self.assertTrue(other.show_edges)
        self.assertAlmostEqual(other.scale, 1.4)
        self.assertAlmostEqual(other.position_x, 30.0)
        self.assertAlmostEqual(other.position_y, -12.0)
        self.assertAlmostEqual(other.q.w, head.q.w, places=9)
        self.assertEqual(other.to_dict(), data)

    def test_from_dict_tolerates_garbage(self):
        head = AsaroHead()
        head.from_dict({})
        head.from_dict({"detail": "no", "scale": "grande", "rotation": [1, 2]})
        head.from_dict({"showNeck": 0, "shadePlanes": 0, "detail": 99})
        self.assertEqual(head.detail, 2)
        self.assertFalse(head.show_neck)
        self.assertFalse(head.shade_planes)
        _valid_svg(self, head.build_svg(600, 600))

    def test_from_dict_accepts_loomis_preset(self):
        head = AsaroHead()
        head.from_dict(
            {
                "generator": "loomis",
                "scale": 0.9,
                "sideCut": 0.4,
                "faceAge": 0.3,
                "chinWidth": 1.2,
                "showFace": False,
                "showArrow": False,
                "showSilhouette": False,
                "showSideRims": False,
                "showSideCross": False,
            }
        )
        self.assertAlmostEqual(head.side_cut, 0.4)
        self.assertAlmostEqual(head.face_age, 0.3)
        self.assertAlmostEqual(head.chin_width, 1.2)
        self.assertFalse(head.show_face)
        self.assertFalse(head.show_arrow)
        self.assertFalse(head.show_silhouette)
        self.assertFalse(head.show_side_rims)
        self.assertFalse(head.show_side_cross)
        _valid_svg(self, head.build_svg(600, 600))

    def test_interface_setters(self):
        head = AsaroHead()
        head.set_front_line_stroke(12.0)
        head.set_back_line_stroke(4.0)
        head.set_stroke_color("#123456")
        head.set_zone_colors(True)
        self.assertAlmostEqual(head.front_line_stroke, 12.0)
        self.assertAlmostEqual(head.back_line_stroke, 4.0)
        self.assertEqual(head.stroke_color, "#123456")
        self.assertTrue(head.use_zone_colors)
        svg = head.build_svg(700, 700)
        self.assertIn(PLANE_COLOR, svg)
        self.assertIn(EDGE_COLOR, svg)

    def test_clamps(self):
        head = AsaroHead()
        head.set_scale(0.0001)
        self.assertAlmostEqual(head.scale, 0.05)
        head.set_scale(99.0)
        self.assertAlmostEqual(head.scale, 5.0)
        head.set_detail(-4)
        self.assertEqual(head.detail, 0)
        head.set_detail(7)
        self.assertEqual(head.detail, 2)
        head.set_front_line_stroke(float("nan"))
        self.assertAlmostEqual(head.front_line_stroke, 10.0)
        head.set_position_x(float("inf"))
        self.assertTrue(math.isfinite(head.position_x))
        head.set_scale(float("nan"))
        self.assertAlmostEqual(head.scale, 1.0)

    def test_extremes_keep_svg_finite(self):
        head = AsaroHead()
        for scale in (0.05, 5.0):
            head.set_scale(scale)
            head.set_position_x(-1e5)
            head.set_position_y(1e5)
            for detail in (0, 1, 2):
                head.set_detail(detail)
                _valid_svg(self, head.build_svg(10, 10))
                _valid_svg(self, head.build_svg(5000, 300))

    def test_svg_follows_position_and_scale(self):
        head = AsaroHead()
        base = head.build_svg(800, 800)
        head.set_scale(2.0)
        bigger = head.build_svg(800, 800)
        self.assertNotEqual(base, bigger)
        head.set_scale(1.0)
        head.set_position_x(120.0)
        moved = head.build_svg(800, 800)
        self.assertNotEqual(base, moved)
        numbers = [float(v) for v in re.findall(r"-?\d+\.\d+", moved)]
        self.assertTrue(numbers)
        self.assertTrue(all(math.isfinite(v) for v in numbers))

    def test_neck_faces_are_below_head_faces(self):
        head = AsaroHead()
        verts = head._vertices()
        head_faces = head._faces()[: head._level()["head_faces"]]
        neck_faces = head._neck_faces()
        head_bottom = min(sum(verts[i][1] for i in f) / len(f) for f in head_faces)
        neck_top = max(sum(verts[i][1] for i in f) / len(f) for f in neck_faces)
        self.assertGreater(head_bottom, neck_top - 0.02)


class RegistryTests(unittest.TestCase):
    def test_registry_contents(self):
        self.assertIn("asaro", MODELS)
        self.assertIn("loomis", MODELS)
        self.assertEqual(DEFAULT_MODEL, "loomis")
        self.assertEqual(set(supported_models()), {"loomis", "asaro"})

    def test_create_model(self):
        head = create_model("asaro")
        self.assertIsInstance(head, AsaroHead)
        self.assertEqual(head.model_id, "asaro")
        default = create_model()
        self.assertEqual(getattr(default, "model_id", "loomis"), "loomis")


if __name__ == "__main__":
    unittest.main()
