# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas de la cabeza Asaro y del registro de modelos (sin Krita).

El modelo dibuja el retopo de planos de ``asaro_clean_mesh``; la decimacion
exacta del OBJ queda en ``asaro_mesh`` como referencia para medir la silueta.
Las pruebas cubren las dos mallas (manifold, simetria, conteo, silueta) y el
SVG que sale de la cabeza (toggles, relleno de planos, ida y vuelta).

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

from loomis_head import asaro_clean_mesh, asaro_mesh  # noqa: E402
from loomis_head.asaro import (  # noqa: E402
    EDGE_COLOR,
    PLANE_COLOR,
    _SHADE_TONES,
    AsaroHead,
    _newell,
)
from loomis_head.linalg import q_axis_angle  # noqa: E402
from loomis_head.euclid import Vector3  # noqa: E402
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


def _rasterize(verts, faces, yaw_deg, size=400, span=1.62) -> bytearray:
    """Silueta rasterizada (relleno de scanline par-impar, sin dependencias).

    Misma camara ortografica que los renders: giro en Y, alto 1.5 centrado y
    ``span`` de margen. Devuelve una mascara de ``size * size`` bytes.
    """
    yaw = math.radians(yaw_deg)
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    scale = size / span
    projected = [
        (size / 2.0 + (x * cos_y + z * sin_y) * scale,
         size / 2.0 - (y + 0.02) * scale)
        for x, y, z in verts
    ]
    mask = bytearray(size * size)
    for face in faces:
        points = [projected[i] for i in face]
        ys = [p[1] for p in points]
        first = max(0, int(math.ceil(min(ys))))
        last = min(size - 1, int(math.floor(max(ys))))
        for row in range(first, last + 1):
            line = row + 0.5
            crossings = []
            n = len(points)
            for i in range(n):
                ax, ay = points[i]
                bx, by = points[(i + 1) % n]
                if (ay <= line < by) or (by <= line < ay):
                    t = (line - ay) / (by - ay)
                    crossings.append(ax + (bx - ax) * t)
            crossings.sort()
            base = row * size
            for k in range(0, len(crossings) - 1, 2):
                x0 = max(0, int(math.ceil(crossings[k])))
                x1 = min(size - 1, int(math.floor(crossings[k + 1])))
                for column in range(x0, x1 + 1):
                    mask[base + column] = 1
    return mask


def _iou(a: bytearray, b: bytearray) -> float:
    inter = union = 0
    for va, vb in zip(a, b):
        if va or vb:
            union += 1
            if va and vb:
                inter += 1
    return inter / union if union else 0.0


def _row_spans(mask: bytearray, size: int):
    spans = []
    for row in range(size):
        base = row * size
        line = mask[base:base + size]
        if not any(line):
            continue
        left = line.index(1)
        right = size - 1 - line[::-1].index(1)
        spans.append((row, left, right))
    return spans


def _row_deltas(mask_a, mask_b, size, span=1.62):
    """Diferencia de borde izquierdo/derecho por fila, en unidades de modelo."""
    left = {row: (a, b) for row, a, b in _row_spans(mask_a, size)}
    right = {row: (a, b) for row, a, b in _row_spans(mask_b, size)}
    deltas = []
    for row in sorted(set(left) & set(right)):
        la, ra = left[row]
        lb, rb = right[row]
        deltas.append(max(abs(la - lb), abs(ra - rb)) * span / size)
    return deltas


_EXACT_MASKS: dict[tuple[float, int, float], bytearray] = {}


def _exact_mask(yaw, size=400, span=1.62) -> bytearray:
    """Mascara de la malla exacta (cacheada: rasterizarla es lo caro)."""
    key = (yaw, size, span)
    if key not in _EXACT_MASKS:
        exact = asaro_mesh.get_level(2)
        _EXACT_MASKS[key] = _rasterize(exact["verts"], exact["faces"], yaw, size, span)
    return _EXACT_MASKS[key]


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


class AsaroCleanMeshTests(unittest.TestCase):
    """Integridad del retopo de planos (``asaro_clean_mesh``)."""

    def setUp(self):
        self.levels = asaro_clean_mesh.ASARO_CLEAN_LEVELS

    def test_levels_and_counts(self):
        self.assertEqual(asaro_clean_mesh.LEVEL_COUNT, 3)
        self.assertEqual([d["detail"] for d in self.levels], [0, 1, 2])
        self.assertEqual([d["ring_verts"] for d in self.levels], [10, 16, 18])
        heads = [d["head_faces"] for d in self.levels]
        # Contrato 0.7.4 v2: ~90 / ~200 / ~220 caras de cabeza.
        self.assertGreaterEqual(heads[0], 80)
        self.assertLessEqual(heads[0], 105)
        self.assertGreaterEqual(heads[1], 180)
        self.assertLessEqual(heads[1], 210)
        self.assertGreaterEqual(heads[2], 205)
        self.assertLessEqual(heads[2], 235)
        self.assertEqual(heads, sorted(set(heads)), "el detalle debe crecer")

    def test_detail_one_fits_the_face_budget(self):
        # El contrato pide ~100-200 caras en detalle 1 y el pase v2 no debe
        # pasar de ~240 con cuello y peana incluidos.
        total = len(self.levels[1]["faces"])
        self.assertGreaterEqual(total, 200)
        self.assertLessEqual(total, 245)
        self.assertLess(len(self.levels[0]["faces"]), total)
        self.assertLess(total, len(self.levels[2]["faces"]))

    def test_closed_manifold(self):
        """Malla cerrada: cada arista la comparten exactamente dos caras."""
        for data in self.levels:
            use = _edge_use(data["faces"])
            bad = {edge: count for edge, count in use.items() if count != 2}
            self.assertFalse(bad, f"aristas que no son de dos caras: {bad}")

    def test_no_t_junctions(self):
        """Ningun vertice cae en el interior de una arista que no es suya."""
        for data in self.levels:
            verts = data["verts"]
            for face in data["faces"]:
                n = len(face)
                for i in range(n):
                    a = verts[face[i]]
                    b = verts[face[(i + 1) % n]]
                    ax, ay, az = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                    length2 = ax * ax + ay * ay + az * az
                    for index, point in enumerate(verts):
                        if index in (face[i], face[(i + 1) % n]):
                            continue
                        px, py, pz = point[0] - a[0], point[1] - a[1], point[2] - a[2]
                        t = (px * ax + py * ay + pz * az) / length2
                        if not 0.02 < t < 0.98:
                            continue
                        dx = px - ax * t
                        dy = py - ay * t
                        dz = pz - az * t
                        self.assertGreater(dx * dx + dy * dy + dz * dz, 1e-8,
                                           f"{point} esta sobre la arista {face[i]}-{face[(i + 1) % n]}")

    def test_quad_dominant(self):
        for data in self.levels:
            quads = sum(1 for face in data["faces"] if len(face) == 4)
            self.assertGreater(quads / len(data["faces"]), 0.9,
                               "el retopo tiene que ser quad-dominante")

    def test_faces_are_valid(self):
        for data in self.levels:
            verts = data["verts"]
            seen = set()
            for face in data["faces"]:
                self.assertGreaterEqual(len(face), 3, f"{face} no es un poligono")
                self.assertEqual(len(set(face)), len(face), f"{face} repite vertices")
                for index in face:
                    self.assertTrue(0 <= index < len(verts))
                self.assertGreater(_face_area(verts, face), 1e-4, f"{face} degenerada")
                key = frozenset(face)
                self.assertNotIn(key, seen, f"cara repetida {face}")
                seen.add(key)

    def test_vertices_are_finite_and_used(self):
        for data in self.levels:
            used = {index for face in data["faces"] for index in face}
            cap_used = {index for face in data["cap"] for index in face}
            self.assertEqual(used | cap_used, set(range(len(data["verts"]))))
            for point in data["verts"]:
                self.assertEqual(len(point), 3)
                for value in point:
                    self.assertTrue(math.isfinite(value), f"{point} no es finito")

    def test_symmetry_in_x(self):
        for data in self.levels:
            table = {(round(-p[0], 5), round(p[1], 5), round(p[2], 5))
                     for p in data["verts"]}
            for point in data["verts"]:
                key = (round(point[0], 5), round(point[1], 5), round(point[2], 5))
                self.assertIn(key, table, f"{point} no tiene reflejo en x")

    def test_levels_share_the_silhouette(self):
        boxes = [data["bbox"] for data in self.levels]
        for box in boxes:
            for index, value in enumerate(box):
                self.assertAlmostEqual(value, boxes[1][index], delta=0.004)

    def test_cap_closes_the_neck_cut(self):
        for data in self.levels:
            verts = data["verts"]
            head = data["faces"][:data["head_faces"]]
            border = {edge for edge, count in _edge_use(head).items() if count == 1}
            self.assertTrue(border, "el corte de cuello no tiene borde")
            self.assertFalse(border - set(_edge_use(data["cap"])),
                             "el tapon no cubre el corte")
            for face in data["cap"]:
                self.assertEqual(len(face), 3)
                nx, ny, nz = _newell([verts[i] for i in face])
                self.assertLess(ny, 0.0, f"{face} no mira hacia abajo")

    def test_neck_flag_is_the_cut(self):
        for data in self.levels:
            verts = data["verts"]
            flags = asaro_clean_mesh.neck_flags(data["detail"])
            self.assertEqual(len(flags), len(data["faces"]))
            self.assertEqual(list(flags), list(data["neck"]))
            self.assertEqual(data["head_faces"], flags.count(False))
            for face, is_neck in zip(data["faces"], flags):
                height = sum(verts[i][1] for i in face) / len(face)
                if is_neck:
                    self.assertLess(height, asaro_clean_mesh.NECK_Y + 1e-6)
                else:
                    self.assertGreaterEqual(height, asaro_clean_mesh.NECK_Y - 1e-6)

    def test_neck_y_matches_the_declared_plane(self):
        self.assertLess(asaro_clean_mesh.NECK_Y, 0.0)
        for data in self.levels:
            self.assertAlmostEqual(data["neck_y"], asaro_clean_mesh.NECK_Y, delta=1e-6)


class AsaroCleanFeatureTests(unittest.TestCase):
    """Boca con labios, oreja en concha y cara sin apilado de anillos."""

    def setUp(self):
        self.head = AsaroHead()
        self.head.set_detail(1)
        self.verts = self.head._vertices()
        self.faces = self.head._faces()
        self.level = self.head._level()

    # --- boca -------------------------------------------------------------
    def test_mouth_has_two_lips_and_a_recessed_line(self):
        """En el plano medio hay tres vertices de boca y el central se hunde."""
        middle = sorted(
            (p for p in self.verts
             if abs(p[0]) < 1e-6 and -0.09 < p[1] < 0.01 and p[2] > 0.30),
            key=lambda p: p[1],
        )
        self.assertGreaterEqual(len(middle), 3, "falta la banda de la boca")
        lower, centre, upper = middle[-3], middle[-2], middle[-1]
        # El surco central esta entre los dos labios y va por detras.
        self.assertLess(lower[1], centre[1])
        self.assertLess(centre[1], upper[1])
        self.assertLess(centre[2], lower[2] - 0.010, "la linea de la boca no se hunde")
        self.assertLess(centre[2], upper[2] - 0.010, "la linea de la boca no se hunde")
        # El labio superior vuela sobre el inferior.
        self.assertGreater(upper[2], lower[2])
        # La boca esta en su sitio: entre el menton y la nariz.
        self.assertGreater(centre[1], -0.09)
        self.assertLess(centre[1], -0.02)

    def test_mouth_band_is_wide_and_tilted(self):
        """La banda de la boca se abre hacia las comisuras y no es horizontal."""
        band = [
            p for p in self.verts
            if -0.09 < p[1] < 0.0 and 0.09 < abs(p[0]) < 0.14
        ]
        self.assertTrue(band, "la boca no llega a las comisuras")
        widths = {round(abs(p[0]), 2) for p in band}
        self.assertGreaterEqual(max(widths), 0.10, "la boca es demasiado estrecha")
        # Las comisuras quedan por detras del labio: la boca se cierra.
        front = max((p[2] for p in self.verts if abs(p[0]) < 1e-6 and -0.09 < p[1] < 0.0),
                    default=0.0)
        self.assertLess(max(p[2] for p in band), front, "la comisura no retrocede")

    def test_mouth_rows_exist_as_faces(self):
        mouth = [
            face for face in self.faces
            if all(abs(self.verts[i][0]) < 0.15 and -0.10 < self.verts[i][1] < 0.01
                   and self.verts[i][2] > 0.30 for i in face)
        ]
        self.assertGreaterEqual(len(mouth), 3, "no hay caras de labios")
        for face in mouth:
            self.assertGreater(_face_area(self.verts, face), 1e-4)

    # --- oreja ------------------------------------------------------------
    def ear_zone(self, sign=1):
        return [p for p in self.verts
                if sign * p[0] > 0.30 and 0.12 < p[1] < 0.35 and -0.34 < p[2] < -0.10]

    def test_ear_rim_protrudes(self):
        for sign in (1, -1):
            zone = self.ear_zone(sign)
            self.assertTrue(zone, "no hay oreja")
            rim = max(abs(p[0]) for p in zone)
            self.assertGreaterEqual(rim, 0.39, "la oreja no sobresale")
            skull = max(abs(p[0]) for p in self.verts
                        if 0.12 < p[1] < 0.35 and abs(p[0]) < 0.36)
            self.assertGreater(rim - skull, 0.02, "la oreja queda pegada al craneo")

    def test_ear_has_a_concha(self):
        """Caras hundidas: el suelo de la concha queda por dentro de la helice."""
        for sign in (1, -1):
            zone = self.ear_zone(sign)
            rim = max(abs(p[0]) for p in zone)
            inner = [p for p in zone if abs(p[0]) < rim - 0.035]
            self.assertGreaterEqual(len(inner), 2, "la oreja no tiene concha")
            self.assertGreaterEqual(rim - min(abs(p[0]) for p in inner), 0.03)
            faces = [
                face for face in self.faces
                if all(sign * self.verts[i][0] > 0.30 and 0.12 < self.verts[i][1] < 0.35
                       and -0.34 < self.verts[i][2] < -0.10 for i in face)
            ]
            self.assertGreaterEqual(len(faces), 3, "faltan caras en la oreja")
            concha = [face for face in faces
                      if abs(sum(self.verts[i][0] for i in face) / len(face)) < rim - 0.02]
            self.assertGreaterEqual(len(concha), 2, "no hay caras hundidas")
            self.assertLessEqual(len(faces), 8, "la oreja ocupa media cabeza")

    def test_ear_is_symmetric(self):
        for point in self.verts:
            if point[0] > 0.30 and 0.12 < point[1] < 0.35 and -0.34 < point[2] < -0.10:
                mirror = (-round(point[0], 5), round(point[1], 5), round(point[2], 5))
                table = {(-round(p[0], 5), round(p[1], 5), round(p[2], 5)) for p in self.verts}
                self.assertIn(mirror, table, f"{point} no tiene oreja al otro lado")

    # --- bandeado ---------------------------------------------------------
    def _rows(self):
        n = self.level["ring_verts"]
        return [self.verts[i * n:(i + 1) * n] for i in range(len(self.verts) // n)]

    def test_face_rows_follow_anatomical_lines(self):
        """Ninguna fila de la cara es horizontal: la boca y la nariz se curvan."""
        curved = 0
        for band in self._rows():
            face = [p for p in band if abs(p[0]) < 0.30 and -0.16 < p[1] < 0.33]
            if len(face) < 3:
                continue
            heights = [p[1] for p in face]
            if max(heights) - min(heights) >= 0.02:
                curved += 1
        self.assertGreaterEqual(curved, 6, "las filas de la cara siguen siendo anillos planos")

    def test_face_keeps_few_rows(self):
        """La cara no gana filas: como mucho ocho niveles del menton a la ceja."""
        rows = []
        for band in self._rows():
            face = [p for p in band if abs(p[0]) < 0.30]
            if face:
                rows.append(sum(p[1] for p in face) / len(face))
        face_rows = [y for y in rows if -0.16 < y < 0.32]
        self.assertLessEqual(len(face_rows), 8, "demasiadas filas horizontales en la cara")

    def test_face_has_vertical_and_diagonal_columns(self):
        """Columnas que recorren la cara y planos en diagonal (nariz, pomulo...)."""
        edges = set()
        for face in self.faces:
            n = len(face)
            for i in range(n):
                a, b = face[i], face[(i + 1) % n]
                edges.add((a, b) if a < b else (b, a))
        vertical = diagonal = 0
        for a, b in edges:
            pa, pb = self.verts[a], self.verts[b]
            centre_x = (pa[0] + pb[0]) / 2.0
            centre_y = (pa[1] + pb[1]) / 2.0
            if abs(centre_x) > 0.26 or not (-0.16 < centre_y < 0.32):
                continue
            dy = abs(pa[1] - pb[1])
            dx = abs(pa[0] - pb[0])
            dz = abs(pa[2] - pb[2])
            if dy < 0.02:
                continue
            vertical += 1
            if dx >= 0.01 or dz >= 0.015:
                diagonal += 1
        self.assertGreaterEqual(vertical, 60, "no hay columnas verticales en la cara")
        self.assertGreaterEqual(diagonal, 30, "no hay planos en diagonal en la cara")


class AsaroSilhouetteTests(unittest.TestCase):
    """La silueta del retopo no se separa de la malla exacta del OBJ."""

    TOLERANCE = 0.045  # 3 % del alto (1.5)

    def setUp(self):
        exact = asaro_mesh.get_level(2)
        clean = asaro_clean_mesh.get_level(1)
        self.exact = exact["verts"]
        self.clean = clean["verts"]

    def _front(self, verts, low, high, half_width=0.12):
        return _front(verts, low, high) if half_width == 0.12 else max(
            (p[2] for p in _band(verts, low, high, half_width)), default=float("-inf"))

    def test_bounding_box(self):
        def box(verts):
            xs = [p[0] for p in verts]
            ys = [p[1] for p in verts]
            zs = [p[2] for p in verts]
            return (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs),
                    min(xs), min(ys), min(zs))

        exact, clean = box(self.exact), box(self.clean)
        for index in range(3):
            self.assertAlmostEqual(clean[index], exact[index], delta=self.TOLERANCE)
        self.assertAlmostEqual(clean[3], exact[3], delta=0.02)
        self.assertAlmostEqual(clean[4], exact[4], delta=1e-4)
        self.assertAlmostEqual(clean[5], exact[5], delta=0.02)

    def test_nose_and_brow(self):
        tip = self._front(self.clean, 0.13, 0.21)
        self.assertAlmostEqual(tip, self._front(self.exact, 0.13, 0.21),
                               delta=self.TOLERANCE)
        brow = self._front(self.clean, 0.30, 0.35)
        self.assertGreaterEqual(tip - brow, 0.04, "la nariz no sobresale de la ceja")

    def test_chin_and_lips(self):
        lips = self._front(self.clean, -0.09, 0.0)
        chin = self._front(self.clean, -0.19, -0.11)
        self.assertAlmostEqual(chin, self._front(self.exact, -0.19, -0.11),
                               delta=self.TOLERANCE)
        self.assertGreater(lips, chin - 0.05)
        self.assertGreater(chin, 0.30)

    def test_occiput(self):
        for verts in (self.exact, self.clean):
            back = min(verts, key=lambda p: p[2])
            self.assertLess(back[2], -0.45)
            self.assertTrue(0.1 < back[1] < 0.35, "el occipucio no esta en el craneo")

    def test_width_and_ear(self):
        def widest(verts):
            point = max(verts, key=lambda p: abs(p[0]))
            return abs(point[0]), point[1], point[2]

        exact, clean = widest(self.exact), widest(self.clean)
        self.assertAlmostEqual(clean[0], exact[0], delta=0.02)
        self.assertTrue(0.10 < clean[1] < 0.32, "la oreja no esta a la altura del ojo")
        self.assertLess(clean[2], 0.0, "la oreja no va detras de la cara")

    def test_profile_band_by_band(self):
        """El borde de la silueta por franjas no se separa de la malla exacta."""
        size, span = 400, 1.62
        clean = asaro_clean_mesh.get_level(1)
        for yaw in (0, 90):
            exact = _exact_mask(yaw, size, span)
            raster = _rasterize(clean["verts"], clean["faces"], yaw, size, span)
            deltas = sorted(_row_deltas(exact, raster, size, span))
            self.assertGreater(len(deltas), 300)
            mean = sum(deltas) / len(deltas)
            p95 = deltas[int(0.95 * len(deltas))]
            self.assertLess(mean, 0.035, f"yaw {yaw}: media {mean:.3f}")
            self.assertLess(p95, 0.085, f"yaw {yaw}: p95 {p95:.3f}")

    def test_silhouette_iou_by_view(self):
        """IoU rasterizado contra la malla exacta en frontal, 3/4 y perfil."""
        size, span = 400, 1.62
        # 3 % del alto de margen: la limpieza visual manda, la silueta aguanta.
        minimum = {0: 0.96, 45: 0.92, 90: 0.95}
        for detail in (0, 1, 2):
            data = asaro_clean_mesh.get_level(detail)
            for yaw, limit in minimum.items():
                exact = _exact_mask(yaw, size, span)
                raster = _rasterize(data["verts"], data["faces"], yaw, size, span)
                iou = _iou(exact, raster)
                self.assertGreaterEqual(
                    iou, limit, f"detalle {detail} yaw {yaw}: IoU {iou:.4f} < {limit}")


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


class AsaroPivotTests(unittest.TestCase):
    """El pivote es el centro del craneo y ``position_x/y`` es su posicion.

    No es el centro del bbox del busto (incluye cuello y peana): el pivote se
    calcula del centroide de area de las caras de la cabeza y es el mismo en
    los tres niveles de detalle.
    """

    def test_pivot_is_skull_center_not_bust_center(self):
        pivot = AsaroHead.pivot_local
        self.assertAlmostEqual(pivot.x, 0.0, places=6)
        level = asaro_clean_mesh.get_level(2)
        head = [level["verts"][i] for f in level["faces"][: level["head_faces"]]
                for i in f]
        low = min(p[1] for p in head)
        high = max(p[1] for p in head)
        self.assertGreater(pivot.y, low)
        self.assertLess(pivot.y, high)
        # Por encima del menton (nunca dentro del cuello).
        self.assertGreater(pivot.y, asaro_clean_mesh.NECK_Y + 0.2)
        bbox = level["bbox"]
        bust_center_y = (bbox[2] + bbox[3]) / 2.0
        self.assertNotAlmostEqual(pivot.y, bust_center_y, places=2)
        # La profundidad cae entre la cara y la nuca.
        self.assertGreater(pivot.z, bbox[4])
        self.assertLess(pivot.z, bbox[5])

    def test_pivot_matches_clean_mesh_constant(self):
        self.assertEqual(
            tuple(AsaroHead.pivot_local), tuple(asaro_clean_mesh.PIVOT_LOCAL)
        )

    def test_pivot_is_the_same_at_every_detail(self):
        values = [asaro_clean_mesh._pivot_local(level)
                  for level in asaro_clean_mesh.ASARO_CLEAN_LEVELS]
        for value in values:
            for got, want in zip(value, asaro_clean_mesh.PIVOT_LOCAL):
                self.assertAlmostEqual(got, want, delta=0.01)

    def test_pivot_projects_to_position_x_y(self):
        """Con dos posiciones y dos rotaciones el pivote cae en X/Y."""
        head = AsaroHead()
        head.set_scale(0.7)
        pivot = head.pivot_local
        rotations = (
            q_axis_angle([0.0, 1.0, 0.0], 0.0),
            q_axis_angle([0.3, 1.0, 0.2], 1.1),
        )
        for x, y in ((0.0, 0.0), (413.0, 257.0), (-90.5, 700.25)):
            head.set_position_x(x)
            head.set_position_y(y)
            for q in rotations:
                head.set_quaternion(q)
                s = min(800.0, 700.0) * 0.3 * head.scale
                point = head._to_screen(head._to_camera(tuple(pivot)), s)
                self.assertAlmostEqual(point.x, x, places=6)
                self.assertAlmostEqual(point.y, y, places=6)

    def test_rotation_keeps_the_pivot_still_but_moves_the_mesh(self):
        head = AsaroHead()
        head.set_position_x(300.0)
        head.set_position_y(400.0)
        s = min(800.0, 800.0) * 0.3 * head.scale
        face = head._vertices()[0]

        head.set_quaternion(q_axis_angle([0.0, 1.0, 0.0], 0.0))
        pivot_a = head._to_screen(head._to_camera(tuple(head.pivot_local)), s)
        face_a = head._to_screen(head._to_camera(face), s)

        head.set_quaternion(q_axis_angle([0.0, 1.0, 0.0], 0.9))
        pivot_b = head._to_screen(head._to_camera(tuple(head.pivot_local)), s)
        face_b = head._to_screen(head._to_camera(face), s)

        self.assertAlmostEqual(pivot_a.x, pivot_b.x, places=6)
        self.assertAlmostEqual(pivot_a.y, pivot_b.y, places=6)
        self.assertGreater(abs(face_a.x - face_b.x) + abs(face_a.y - face_b.y), 1.0)

    def test_detail_and_neck_do_not_move_the_pivot(self):
        head = AsaroHead()
        head.set_position_x(512.0)
        head.set_position_y(384.0)
        s = min(1000.0, 800.0) * 0.3 * head.scale
        seen = []
        for detail in (0, 1, 2):
            for neck in (True, False):
                head.set_detail(detail)
                head.set_show_neck(neck)
                point = head._to_screen(head._to_camera(tuple(head.pivot_local)), s)
                seen.append((round(point.x, 6), round(point.y, 6)))
        self.assertEqual(len(set(seen)), 1)

    def test_model_switch_keeps_the_pivot_position(self):
        """Loomis -> Asaro -> Loomis conserva la posicion del pivote."""
        asaro = AsaroHead()
        asaro.set_position_x(640.0)
        asaro.set_position_y(360.0)
        asaro.set_scale(0.45)
        asaro.set_quaternion(q_axis_angle([0.0, 1.0, 0.0], 0.4))

        loomis = create_model("loomis")
        # El plugin copia la transformacion comun; aqui se replica ese contrato.
        loomis.set_position_x(asaro.position_x)
        loomis.set_position_y(asaro.position_y)
        loomis.set_scale(asaro.scale)
        loomis.set_quaternion(asaro.q)

        loomis_pivot = loomis._to_screen(loomis._to_camera([Vector3(0.0, 0.0, 0.0)]),
                                        900.0, 900.0)[0]
        self.assertAlmostEqual(loomis_pivot.x, 640.0, places=6)
        self.assertAlmostEqual(loomis_pivot.y, 360.0, places=6)

        asaro2 = AsaroHead()
        asaro2.from_dict(asaro.to_dict())
        s2 = min(900.0, 900.0) * 0.3 * asaro2.scale
        pivot_up = asaro2._to_screen(asaro2._to_camera(tuple(asaro2.pivot_local)), s2)
        self.assertAlmostEqual(pivot_up.x, 640.0, places=6)
        self.assertAlmostEqual(pivot_up.y, 360.0, places=6)


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
