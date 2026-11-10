# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Cabeza Asaro: malla low-poly de planos, sin luz ni sombra.

El plugin usa la misma interfaz que :class:`LoomisHead3D` (escala, posicion,
quaternion, trazos, toggles y ``to_dict``/``from_dict``) para que el panel y la
capa vectorial funcionen sin cambios. Lo propio de Asaro es la malla de planos:
frente, ceja, cuenca, nariz, pomulo, mandibula y menton, dibujada solo con
aristas (sin relleno).

La malla esta pensada para leerse en los tres cuartos y, sobre todo, de perfil:
a 90 grados la proyeccion solo conserva (z, y), asi que la silueta la definen
las dos curvas descriptas en ``_HALF_VERTICES`` (cara y craneo). Los vertices
interiores solo agregan pliegues; si se mueve uno de la linea central de la
cara o de la nuca, el perfil cambia y hay que volver a mirarlo.
"""

import math
from collections.abc import Sequence

from .euclid import Vector2, Vector3
from .geom_polyline import path_str, split_front_back
from .linalg import Poly3, Quaternion, q_identity, q_normalize

# Colores de zona (mismos que el generador Loomis para no romper la paleta).
PLANE_COLOR = "#6A54E7"
EDGE_COLOR = "#54C4E7"

# Un plano solo se dibuja si su normal mira a camara con este margen.
_FACING_EPS = 1e-6
# Diferencia de normal (grados) para considerar una arista un pliegue real.
_CREASE_DEG = 25.0

# Vertices de la mitad derecha (x >= 0). Los de x == 0 son la linea central y
# se comparten con la mitad izquierda; el resto se refleja.
#
# Ejes: x lateral (+ derecha), y arriba, z hacia camara (+ delante). El perfil
# a 90 grados solo ve (z, y): la silueta de la cara es, por tanto, la curva
# frente -> ceja -> nasion -> dorso -> punta -> filtro -> labios -> menton, y
# la de atras la curva coronilla -> occipucio -> nuca. Esas dos curvas mandan
# la lectura; el resto de vertices solo matiza los planos interiores.
_HALF_VERTICES: dict[str, tuple[float, float, float]] = {
    "A1": (0.00, 0.90, 0.30),   # frente, coronilla delantera
    "A2": (0.36, 0.84, 0.44),   # frente, medio
    "A3": (0.60, 0.62, 0.24),   # frente, lateral (sien)
    "B1": (0.00, 0.44, 0.62),   # ceja, centro (glabela, sobresale)
    "B2": (0.26, 0.42, 0.60),   # ceja, medio
    "B3": (0.52, 0.36, 0.46),   # ceja, lateral (borde orbitario)
    "C1": (0.10, 0.30, 0.42),   # cuenca, interior (hundida)
    "C2": (0.44, 0.24, 0.36),   # cuenca, exterior (hundida)
    "C3": (0.27, 0.14, 0.38),   # cuenca, fondo (hundida)
    "D1": (0.00, 0.36, 0.54),   # nariz, nasion (muesca bajo la ceja)
    "D2": (0.09, 0.26, 0.66),   # nariz, dorso alto
    "D3": (0.12, 0.06, 0.78),   # nariz, dorso bajo
    "D4": (0.20, -0.16, 0.74),  # nariz, ala
    "D5": (0.00, -0.04, 0.92),  # nariz, punta
    "D6": (0.00, -0.22, 0.72),  # nariz, base (subnasal)
    "E1": (0.50, 0.06, 0.36),   # pomulo (cuerpo)
    "E2": (0.33, -0.06, 0.52),  # mejilla, frontal
    "E3": (0.37, -0.30, 0.38),  # mejilla, baja (hueco sobre la mandibula)
    "E4": (0.64, 0.22, 0.06),   # arco cigomatico (escalon hacia la oreja)
    "F1": (0.20, -0.36, 0.50),  # boca, comisura
    "F2": (0.00, -0.22, 0.60),  # filtro
    "F3": (0.00, -0.32, 0.56),  # labio superior
    "F4": (0.11, -0.46, 0.50),  # labio inferior, lateral
    "F5": (0.00, -0.44, 0.53),  # labio inferior, centro
    "G1": (0.16, -0.76, 0.44),  # menton, lateral
    "G2": (0.00, -0.70, 0.60),  # menton, frontal (sobresale del labio)
    "G3": (0.00, -0.94, 0.30),  # menton, bajo
    "G4": (0.24, -0.84, 0.02),  # mandibula, bajo
    "G5": (0.00, -0.55, 0.46),  # surco mentoniano (muesca bajo el labio)
    "H1": (0.52, -0.54, -0.06), # mandibula, angulo (gonion)
    "H2": (0.39, -0.70, 0.10),  # mandibula, lateral
    "H3": (0.39, -0.48, -0.28), # mandibula, detras del angulo
    "M1": (0.62, -0.18, 0.06),  # lateral del maxilar (masseter)
    "I1": (0.64, 0.50, 0.02),   # sien
    "I2": (0.57, 0.66, -0.44),  # parietal, lateral
    "I3": (0.60, 0.34, -0.12),  # oreja, arriba
    "I4": (0.58, -0.20, -0.14), # oreja, abajo
    "I5": (0.70, 0.08, -0.38),  # oreja, helix (borde posterior)
    "I6": (0.46, 0.26, -0.60),  # occipucio, lateral
    "I7": (0.31, 0.08, -0.68),  # nuca, media
    "I8": (0.18, -0.78, -0.20), # cuello, lateral
    "I9": (0.00, 0.80, -0.36),  # coronilla, atras
    "I10": (0.00, 0.06, -0.72), # nuca, centro (punto mas atras)
    "I11": (0.00, -0.50, -0.34), # nuca, baja
    "I12": (0.00, -0.20, -0.62), # nuca, media (redondea el occipucio)
    "I13": (0.00, 0.52, -0.56), # occipucio, alto (redondea la coronilla)
}

# (nivel de detalle minimo, vertices en orden). Nivel 0 = planos grandes (con la
# nariz ya unida a la mejilla), 1 = construccion estandar (oreja, occipucio,
# cuenca, mandibula), 2 = planos finos (sien, coronilla).
_HALF_FACES: tuple[tuple[int, tuple[str, ...]], ...] = (
    (0, ("A1", "A2", "B2", "B1")),
    (0, ("A2", "A3", "B3", "B2")),
    (0, ("B1", "B2", "D2", "D1")),
    (0, ("B2", "B3", "C2", "C1")),
    (0, ("D1", "D2", "D3", "D5")),
    (0, ("D5", "D3", "D4", "D6")),
    (0, ("C2", "E1", "E2", "C3")),
    (0, ("E1", "E4", "H1", "E3")),
    (0, ("F2", "E2", "F1", "F3")),
    (0, ("F3", "F1", "F4", "F5")),
    (0, ("E3", "H1", "H2", "G1")),
    (0, ("F4", "G1", "G2", "G5")),
    (0, ("F5", "F4", "G5")),
    (0, ("C3", "E2", "D3")),
    (0, ("D3", "D4", "E2")),
    (0, ("D6", "D4", "E2", "F2")),
    (1, ("C1", "C2", "C3")),
    (1, ("C1", "C3", "D2", "D1")),
    (1, ("G1", "G4", "G3", "G2")),
    (1, ("H1", "H3", "H2")),
    (1, ("H2", "H3", "I8", "G4")),
    (1, ("I1", "I2", "I3", "E4")),
    (1, ("E4", "I5", "M1", "H1")),
    (1, ("I5", "I4", "I8", "H3")),
    (1, ("I2", "I9", "I13", "I6")),
    (1, ("I3", "I4", "I5")),
    (1, ("I6", "I7", "I10")),
    (1, ("I7", "I10", "I12", "I11")),
    (1, ("I7", "I11", "I8")),
    (1, ("A1", "A3", "I9")),
    (1, ("A3", "I2", "I9")),
    (2, ("A3", "I1", "B3")),
    (2, ("I9", "I6", "I7")),
    (2, ("I9", "I7", "I10")),
)


def _mirrored_name(name: str) -> str:
    x = _HALF_VERTICES[name][0]
    return name if abs(x) < 1e-9 else name + "L"


def _build_vertices() -> dict[str, tuple[float, float, float]]:
    out: dict[str, tuple[float, float, float]] = {}
    for name, (x, y, z) in _HALF_VERTICES.items():
        out[name] = (x, y, z)
        if abs(x) >= 1e-9:
            out[name + "L"] = (-x, y, z)
    return out


_VERTICES = _build_vertices()
_MIRROR = {name: _mirrored_name(name) for name in _HALF_VERTICES}


def _newell(points: Sequence[tuple[float, float, float]]) -> tuple[float, float, float]:
    """Normal de un poligono (puede no ser plano), por el metodo de Newell."""
    nx = ny = nz = 0.0
    n = len(points)
    for i in range(n):
        x0, y0, z0 = points[i]
        x1, y1, z1 = points[(i + 1) % n]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length < 1e-12:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def _finite(value: object, default: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp(value: object, low: float, high: float, default: float) -> float:
    number = _finite(value, default)
    return max(low, min(high, number))


class AsaroHead:
    """Cabeza Asaro con la interfaz del generador Loomis."""

    model_id = "asaro"

    def __init__(self) -> None:
        self.radius: float = 1.0
        self.scale: float = 1.0
        self.position_x: float = 0.0
        self.position_y: float = 0.0
        # Atributos propios de Asaro.
        self.show_planes: bool = True
        self.show_edges: bool = True
        self.detail: int = 1
        # Trazos y color.
        self.front_line_stroke: float = 10.0
        self.back_line_stroke: float = 7.0
        self.stroke_color: str = "#6A54E7"
        self.use_zone_colors: bool = False
        # Compatibilidad con la interfaz Loomis: la UI de Asaro los oculta y
        # estos valores no cambian la malla, solo viajan en el preset.
        self.side_cut: float = 0.66
        self.face_age: float = 1.0
        self.chin_width: float = 1.0
        self.show_face: bool = True
        self.show_arrow: bool = True
        self.show_silhouette: bool = True
        self.show_side_rims: bool = True
        self.show_side_cross: bool = True
        self.show_features: bool = False
        self.q: Quaternion = q_identity()

    # --- interfaz comun ---------------------------------------------------
    def set_quaternion(self, q: Quaternion) -> None:
        self.q = q_normalize(q)

    def set_scale(self, scale: float) -> None:
        self.scale = _clamp(scale, 0.05, 5.0, 1.0)

    def set_position_x(self, position_x: float) -> None:
        self.position_x = _finite(position_x, self.position_x)

    def set_position_y(self, position_y: float) -> None:
        self.position_y = _finite(position_y, self.position_y)

    def set_stroke_color(self, color: str) -> None:
        if isinstance(color, str):
            self.stroke_color = color

    def set_front_line_stroke(self, front_line_stroke: float) -> None:
        self.front_line_stroke = _clamp(front_line_stroke, 0.5, 60.0, 10.0)

    def set_back_line_stroke(self, back_line_stroke: float) -> None:
        self.back_line_stroke = _clamp(back_line_stroke, 0.5, 60.0, 7.0)

    def set_zone_colors(self, enable: bool) -> None:
        self.use_zone_colors = bool(enable)

    # --- propios ----------------------------------------------------------
    def set_show_planes(self, enable: bool) -> None:
        self.show_planes = bool(enable)

    def set_show_edges(self, enable: bool) -> None:
        self.show_edges = bool(enable)

    def set_detail(self, detail: int) -> None:
        try:
            level = int(round(float(detail)))
        except (TypeError, ValueError):
            level = 1
        self.detail = max(0, min(2, level))

    # --- compatibilidad Loomis (sin efecto en la malla) -------------------
    def set_sidecut(self, side_cut: float) -> None:
        self.side_cut = _clamp(side_cut, 0.05, 0.95, 0.66)

    def set_face_age(self, face_age: float) -> None:
        self.face_age = _clamp(face_age, 0.0, 1.0, 1.0)

    def set_chin_width(self, chin_width: float) -> None:
        self.chin_width = _clamp(chin_width, 0.5, 1.5, 1.0)

    def set_show_face(self, enable: bool) -> None:
        self.show_face = bool(enable)

    def set_arrow(self, enable: bool) -> None:
        self.show_arrow = bool(enable)

    def set_silhouette(self, enable: bool) -> None:
        self.show_silhouette = bool(enable)

    def set_side_rims(self, enable: bool) -> None:
        self.show_side_rims = bool(enable)

    def set_side_cross(self, enable: bool) -> None:
        self.show_side_cross = bool(enable)

    def set_show_features(self, enable: bool) -> None:
        self.show_features = bool(enable)

    # --- preset -----------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "version": 1,
            "generator": "asaro",
            "model": "asaro",
            "scale": self.scale,
            "positionX": self.position_x,
            "positionY": self.position_y,
            "rotation": [self.q.w, self.q.x, self.q.y, self.q.z],
            "showPlanes": self.show_planes,
            "showEdges": self.show_edges,
            "detail": self.detail,
            "frontStroke": self.front_line_stroke,
            "backStroke": self.back_line_stroke,
            "strokeColor": self.stroke_color,
            "useZoneColors": self.use_zone_colors,
            # Compatibilidad con presets y UI de Loomis.
            "sideCut": self.side_cut,
            "faceAge": self.face_age,
            "chinWidth": self.chin_width,
            "showFace": self.show_face,
            "showArrow": self.show_arrow,
            "showSilhouette": self.show_silhouette,
            "showSideRims": self.show_side_rims,
            "showSideCross": self.show_side_cross,
        }

    def from_dict(self, data: dict) -> None:
        src = data if isinstance(data, dict) else {}

        def num(key: str, default: float) -> float:
            return _finite(src.get(key, default), default)

        def flag(key: str, default: bool) -> bool:
            return bool(src.get(key, default))

        self.set_scale(num("scale", self.scale))
        self.set_position_x(num("positionX", self.position_x))
        self.set_position_y(num("positionY", self.position_y))
        rotation = src.get("rotation")
        if isinstance(rotation, (list, tuple)) and len(rotation) == 4:
            try:
                w, x, y, z = (_finite(v, 0.0) for v in rotation)
                quaternion = Quaternion(w, x, y, z)
                if abs(quaternion.magnitude()) > 1e-9:
                    self.set_quaternion(quaternion)
            except (TypeError, ValueError):
                pass
        self.set_show_planes(flag("showPlanes", self.show_planes))
        self.set_show_edges(flag("showEdges", self.show_edges))
        self.set_detail(num("detail", self.detail))
        self.set_front_line_stroke(num("frontStroke", self.front_line_stroke))
        self.set_back_line_stroke(num("backStroke", self.back_line_stroke))
        self.set_zone_colors(flag("useZoneColors", self.use_zone_colors))
        color = src.get("strokeColor")
        if isinstance(color, str) and color.startswith("#") and len(color) in (4, 7):
            self.stroke_color = color
        self.set_sidecut(num("sideCut", self.side_cut))
        self.set_face_age(num("faceAge", self.face_age))
        self.set_chin_width(num("chinWidth", self.chin_width))
        self.set_show_face(flag("showFace", self.show_face))
        self.set_arrow(flag("showArrow", self.show_arrow))
        self.set_silhouette(flag("showSilhouette", self.show_silhouette))
        self.set_side_rims(flag("showSideRims", self.show_side_rims))
        self.set_side_cross(flag("showSideCross", self.show_side_cross))

    # --- malla ------------------------------------------------------------
    def _faces(self) -> list[tuple[str, ...]]:
        """Caras completas (derecha + reflejada) hasta el nivel de detalle."""
        faces: list[tuple[str, ...]] = []
        for level, names in _HALF_FACES:
            if level > self.detail:
                continue
            faces.append(names)
            faces.append(tuple(_MIRROR[name] for name in names))
        return faces

    def _face_normal(self, names: Sequence[str]) -> tuple[float, float, float]:
        points = [_VERTICES[name] for name in names]
        nx, ny, nz = _newell(points)
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        cz = sum(p[2] for p in points) / len(points)
        if nx * cx + ny * cy + nz * cz < 0.0:
            return (-nx, -ny, -nz)
        return (nx, ny, nz)

    def _edges(self, faces: Sequence[Sequence[str]]) -> list[tuple[str, str]]:
        """Aristas unicas de pliegue o silueta, cada una una sola vez."""
        adjacency: dict[tuple[str, str], list[tuple[float, float, float]]] = {}
        for names in faces:
            normal = self._face_normal(names)
            n = len(names)
            for i in range(n):
                a = names[i]
                b = names[(i + 1) % n]
                key = (a, b) if a < b else (b, a)
                adjacency.setdefault(key, []).append(normal)

        cos_limit = math.cos(math.radians(_CREASE_DEG))
        out: list[tuple[str, str]] = []
        for key, normals in adjacency.items():
            if len(normals) == 1:
                out.append(key)
                continue
            if len(normals) > 2:
                out.append(key)
                continue
            n0, n1 = normals
            dot = n0[0] * n1[0] + n0[1] * n1[1] + n0[2] * n1[2]
            if dot < cos_limit:
                out.append(key)
        return out

    def _to_camera(self, point: tuple[float, float, float]) -> Vector3:
        x, y, z = point
        return self.q * Vector3(x, y, z)

    def _to_screen(self, point: Vector3, s: float) -> Vector2:
        return Vector2(point.x * s + self.position_x, self.position_y - point.y * s)

    # --- SVG --------------------------------------------------------------
    def build_svg(
        self,
        width: float,
        height: float,
        dash_back: str | None = "5,6",
        samples: int = 256,
    ) -> str:
        del samples  # La malla no tiene curvas; se acepta por compatibilidad.
        w = _finite(width, 800.0)
        h = _finite(height, 800.0)
        s = min(w, h) * 0.3 * self.scale

        faces = self._faces()
        visible: list[tuple[float, list[Vector2]]] = []
        for names in faces:
            nx, ny, nz = self._face_normal(names)
            normal_cam = self.q * Vector3(nx, ny, nz)
            if normal_cam.z <= _FACING_EPS:
                continue
            points = [self._to_camera(_VERTICES[name]) for name in names]
            mean_z = sum(p.z for p in points) / len(points)
            visible.append((mean_z, [self._to_screen(p, s) for p in points]))
        # Painter's algorithm: primero lo que esta mas lejos de camara.
        visible.sort(key=lambda item: item[0])

        plane_paths: list[str] = []
        if self.show_planes:
            for _, screen in visible:
                if len(screen) < 3:
                    continue
                plane_paths.append(path_str([*screen, screen[0]]))

        front_paths: list[str] = []
        back_paths: list[str] = []
        if self.show_edges:
            for a, b in self._edges(faces):
                segment: Poly3 = [
                    self._to_camera(_VERTICES[a]),
                    self._to_camera(_VERTICES[b]),
                ]
                front_segments, back_segments = split_front_back(segment)
                for part in back_segments:
                    back_paths.append(path_str([self._to_screen(p, s) for p in part]))
                for part in front_segments:
                    front_paths.append(path_str([self._to_screen(p, s) for p in part]))

        plane_color = PLANE_COLOR if self.use_zone_colors else self.stroke_color
        edge_color = EDGE_COLOR if self.use_zone_colors else self.stroke_color
        dash_attr = f' stroke-dasharray="{dash_back}"' if dash_back else ""

        svg: list[str] = ['<svg xmlns="http://www.w3.org/2000/svg">']
        if plane_paths:
            svg.append(
                f'<g title="asaro-planes" fill="none" stroke="{plane_color}">'
            )
            svg.append(
                f'<path d="{"".join(plane_paths)}" stroke-width="{self.front_line_stroke}" '
                'stroke-linecap="round" stroke-linejoin="round"/>'
            )
            svg.append("</g>")
        if back_paths or front_paths:
            svg.append(
                f'<g title="asaro-edges" fill="none" stroke="{edge_color}">'
            )
            if back_paths:
                svg.append(
                    f'<path d="{"".join(back_paths)}" stroke-width="{self.back_line_stroke}" '
                    f'stroke-linecap="round" stroke-linejoin="round"{dash_attr} opacity="0.6"/>'
                )
            if front_paths:
                svg.append(
                    f'<path d="{"".join(front_paths)}" stroke-width="{self.front_line_stroke}" '
                    'stroke-linecap="round" stroke-linejoin="round"/>'
                )
            svg.append("</g>")
        svg.append("</svg>")
        return "".join(svg)
