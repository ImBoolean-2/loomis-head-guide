# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Cabeza Asaro: retopo de planos del busto real, sin luz ni sombra.

La malla no se dibuja a mano: es un retopo de planos sobre la silueta del
``Asaro_high.obj`` (el busto de John Asaro con cuello y peana) que vive como
datos estaticos en :mod:`loomis_head.asaro_clean_mesh`. La decimacion exacta
del OBJ sigue en :mod:`loomis_head.asaro_mesh` como referencia para los tests y
las comparaciones, pero no se dibuja. Este modulo solo proyecta la malla:

* ``detail`` 0/1/2 elige el nivel de la malla (grueso, medio, fino);
* ``show_neck`` mete o quita el cuello y la peana; sin ellos la cabeza se
  cierra con el tapon que ya trae el nivel, asi que no queda hueco;
* ``show_planes`` dibuja las caras, ``show_edges`` las aristas de pliegue y de
  silueta (las de atras punteadas) y ``shade_planes`` rellena cada cara con un
  gris segun su orientacion.

Ejes del modelo: ``y`` arriba, ``z`` hacia delante (la cara mira a ``+z``),
``x`` lateral. Alto 1.5, ancho oreja a oreja ~0.8, fondo nariz-occipucio ~1.0.
El menton queda en ``asaro_clean_mesh.NECK_Y``; por debajo empieza el cuello.

Pivote: ``position_x/position_y`` es donde cae el **pivote** de la cabeza (el
centro del craneo entre orejas y ojos, :data:`asaro_clean_mesh.PIVOT_LOCAL`),
no el origen de la malla. Antes de rotar se resta ``pivot_local`` a cada
vertice, de modo que girar no desplaza la cabeza y la posicion del documento
no deriva. Loomis usa el mismo contrato con pivote ``(0, 0, 0)``.

``shade_planes`` no simula luz: clasifica cada cara por el azimut de su normal
respecto al frente del modelo y le da un tono plano (frontal, frontal-lateral,
lateral, trasera) con opacidades 0.18-0.28. No hay foco ni degradado.

La interfaz es la de :class:`LoomisHead3D` (escala, posicion, quaternion,
trazos, colores de zona y ``to_dict``/``from_dict``) para que el panel, la capa
vectorial y los presets funcionen sin cambios.

Licencia: el codigo es GPL-3.0-only; la malla va aparte, bajo **CC BY 4.0**. Es
un derivado (decimado y retopologizado) de "Asaro-head" de **ivan4akir**
(CC BY 4.0), cuyo diseno es de **John Asaro**; "Simple Asaro Head" de
**fabianoaraujo** (CC BY 4.0) se reviso y no se uso. La atribucion y el aviso de
modificacion acompanan a la malla (ver ``LICENSE-ASSETS.md`` y
``CREDITS.md``). Esta version 0.7.10 es **local**: no se publica ZIP ni patch
hasta validarla en Krita.
"""

import math
from collections.abc import Sequence

from . import asaro_clean_mesh
from .euclid import Vector2, Vector3
from .geom_polyline import path_str
from .linalg import Quaternion, q_identity, q_normalize

# Colores de zona (mismos que el generador Loomis para no romper la paleta).
PLANE_COLOR = "#6A54E7"
EDGE_COLOR = "#54C4E7"

# Un plano solo se dibuja si su normal mira a camara con este margen.
_FACING_EPS = 1e-6
# Diferencia de normal (grados) para considerar una arista un pliegue real.
_CREASE_DEG = 25.0

# Relleno neutro por orientacion del plano, NO luz direccional: la cara se
# clasifica por su normal respecto al frente del modelo (azimut) y recibe un
# gris calido claro. Opacidades bajas, dentro del rango 0.18-0.28 del contrato.
# (clase, relleno, opacidad, azimut maximo en grados)
_SHADE_TONES: tuple[tuple[str, str, float, float], ...] = (
    ("frontal", "#f2efe9", 0.18, 35.0),
    ("frontal-lateral", "#b4aea2", 0.22, 70.0),
    ("lateral", "#857e72", 0.25, 115.0),
    ("trasera", "#625d54", 0.28, 180.1),
)


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


def _shade_index(normal: tuple[float, float, float]) -> int:
    """Clase de orientacion del plano respecto al frente del modelo.

    0 frontal (mira a +z), 1 frontal-lateral, 2 lateral (mira al costado),
    3 trasera (mira a la nuca). Es orientacion, no luz: no hay direccion de
    foco ni gradiente, solo cuatro tonos planos.
    """
    nx, ny, nz = normal
    if nz >= 0.0:
        azimuth = math.degrees(math.atan2(abs(nx), nz))
    else:
        azimuth = 180.0 - math.degrees(math.atan2(abs(nx), -nz))
    # Los planos horizontales (coronilla, suelo de la peana) no son "traseros"
    # aunque su normal no tenga componente z: se quedan en el tono lateral.
    if abs(ny) > 0.55:
        azimuth = min(azimuth, 90.0)
    for index, tone in enumerate(_SHADE_TONES):
        if azimuth <= tone[3]:
            return index
    return len(_SHADE_TONES) - 1


def _polygon_d(points: Sequence[Vector2]) -> str:
    """Subpath cerrado de un poligono, en el formato que acepta el plugin."""
    head = f"M{points[0].x:.3f} {points[0].y:.3f}"
    tail = "".join(f"L{p.x:.3f} {p.y:.3f}" for p in points[1:])
    return head + tail + "Z"


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
    # Pivote en coordenadas de la malla limpia: centro del craneo (no el bbox
    # del busto, que incluye cuello y peana). Ver asaro_clean_mesh.PIVOT_LOCAL.
    pivot_local = Vector3(*asaro_clean_mesh.PIVOT_LOCAL)

    def __init__(self) -> None:
        self.radius: float = 1.0
        self.scale: float = 1.0
        self.position_x: float = 0.0
        self.position_y: float = 0.0
        # Atributos propios de Asaro.
        self.show_planes: bool = True
        self.show_edges: bool = True
        self.show_neck: bool = True
        self.shade_planes: bool = True
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

    def set_show_neck(self, enable: bool) -> None:
        self.show_neck = bool(enable)

    def set_shade_planes(self, enable: bool) -> None:
        self.shade_planes = bool(enable)

    def set_detail(self, detail: int) -> None:
        try:
            level = int(round(float(detail)))
        except (TypeError, ValueError):
            level = 1
        self.detail = max(0, min(asaro_clean_mesh.LEVEL_COUNT - 1, level))

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
            "showNeck": self.show_neck,
            "shadePlanes": self.shade_planes,
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
        self.set_show_neck(flag("showNeck", self.show_neck))
        self.set_shade_planes(flag("shadePlanes", self.shade_planes))
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
    def _level(self) -> dict:
        """Nivel de la malla para el detalle actual."""
        return asaro_clean_mesh.get_level(self.detail)

    def _vertices(self) -> tuple[tuple[float, float, float], ...]:
        return self._level()["verts"]

    def _faces(self) -> list[tuple[int, ...]]:
        """Caras a dibujar: cabeza + (cuello visible o tapon del corte).

        En los datos, las primeras ``head_faces`` caras son la cabeza y el
        resto el cuello y la peana. Sin cuello se cambian por el tapon, de modo
        que la cabeza sigue cerrada.
        """
        level = self._level()
        faces = level["faces"]
        head = level["head_faces"]
        if self.show_neck:
            return list(faces)
        return list(faces[:head]) + list(level["cap"])

    def _neck_faces(self) -> list[tuple[int, ...]]:
        """Solo las caras del cuello y la peana (para los tests y el conteo)."""
        level = self._level()
        return list(level["faces"][level["head_faces"]:])

    def _face_normal(self, face: Sequence[int]) -> tuple[float, float, float]:
        """Normal exterior de la cara, orientada respecto al eje del busto.

        El busto es estrellado alrededor del eje vertical (x=z=0): el exterior
        de una cara siempre tiene componente radial positiva. Las caras
        horizontales (coronilla, suelo de la peana) se orientan por su altura.
        """
        vertices = self._vertices()
        points = [vertices[i] for i in face]
        nx, ny, nz = _newell(points)
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        cz = sum(p[2] for p in points) / len(points)
        if abs(ny) > 0.7:
            outward = ny * cy > 0.0
        else:
            outward = nx * cx + nz * cz >= 0.0
        if outward:
            return (nx, ny, nz)
        return (-nx, -ny, -nz)

    def _edge_kinds(
        self, faces: Sequence[Sequence[int]]
    ) -> list[tuple[int, int, str]]:
        """Aristas a dibujar, con su tipo: ``front``, ``back`` o ``silhouette``.

        ``front``/``back`` dicen de que lado de la cabeza queda la arista (las de
        atras se dibujan punteadas). ``silhouette`` es el contorno: la arista
        entre una cara que mira a camara y otra que no. Sin ese caso el perfil
        quedaria abierto, porque en el centro de la cara las caras vecinas son
        casi coplanares y el pliegue no llega al umbral.
        """
        normals: list[tuple[float, float, float]] = []
        facing: list[bool] = []
        for face in faces:
            nx, ny, nz = self._face_normal(face)
            normal_cam = self.q * Vector3(nx, ny, nz)
            normals.append((nx, ny, nz))
            facing.append(normal_cam.z > _FACING_EPS)

        adjacency: dict[tuple[int, int], list[int]] = {}
        for index, face in enumerate(faces):
            n = len(face)
            for i in range(n):
                a = face[i]
                b = face[(i + 1) % n]
                key = (a, b) if a < b else (b, a)
                adjacency.setdefault(key, []).append(index)

        cos_limit = math.cos(math.radians(_CREASE_DEG))
        out: list[tuple[int, int, str]] = []
        for key, owners in adjacency.items():
            if len(owners) == 1:
                kind = "front" if facing[owners[0]] else "back"
                out.append((key[0], key[1], kind))
                continue
            if len(owners) > 2:
                kind = "front" if any(facing[i] for i in owners) else "back"
                out.append((key[0], key[1], kind))
                continue
            first, second = owners
            if facing[first] != facing[second]:
                out.append((key[0], key[1], "silhouette"))
                continue
            n0, n1 = normals[first], normals[second]
            dot = n0[0] * n1[0] + n0[1] * n1[1] + n0[2] * n1[2]
            if dot < cos_limit:
                kind = "front" if facing[first] else "back"
                out.append((key[0], key[1], kind))
        return out

    def _edges(self, faces: Sequence[Sequence[int]]) -> list[tuple[int, int]]:
        """Aristas unicas de pliegue o silueta, cada una una sola vez."""
        return [(a, b) for a, b, _kind in self._edge_kinds(faces)]

    def _to_camera(self, point: tuple[float, float, float]) -> Vector3:
        """Vertice en espacio de camara, con el pivote en el origen.

        Restar ``pivot_local`` antes de rotar es lo que hace que
        ``position_x/position_y`` sea la posicion del pivote: el pivote se
        proyecta exactamente ahi con cualquier rotacion.
        """
        pivot = self.pivot_local
        x, y, z = point
        return self.q * Vector3(x - pivot.x, y - pivot.y, z - pivot.z)

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

        vertices = self._vertices()
        faces = self._faces()
        visible: list[tuple[float, tuple[float, float, float], list[Vector2]]] = []
        for face in faces:
            normal = self._face_normal(face)
            normal_cam = self.q * Vector3(*normal)
            if normal_cam.z <= _FACING_EPS:
                continue
            points = [self._to_camera(vertices[i]) for i in face]
            mean_z = sum(p.z for p in points) / len(points)
            visible.append(
                (mean_z, normal, [self._to_screen(p, s) for p in points])
            )
        # Painter's algorithm: primero lo que esta mas lejos de camara.
        visible.sort(key=lambda item: item[0])

        # Rellenos neutros por orientacion. Van antes que las aristas y no
        # llevan trazo: son valor de plano, no luz.
        shade: list[list[str]] = [[] for _ in _SHADE_TONES]
        if self.show_planes and self.shade_planes:
            for _z, normal, screen in visible:
                if len(screen) < 3:
                    continue
                shade[_shade_index(normal)].append(_polygon_d(screen))

        plane_paths: list[str] = []
        if self.show_planes:
            for _z, _normal, screen in visible:
                if len(screen) < 3:
                    continue
                plane_paths.append(path_str([*screen, screen[0]]))

        front_paths: list[str] = []
        back_paths: list[str] = []
        if self.show_edges:
            for a, b, kind in self._edge_kinds(faces):
                segment = [
                    self._to_camera(vertices[a]),
                    self._to_camera(vertices[b]),
                ]
                path = path_str([self._to_screen(p, s) for p in segment])
                if kind == "back":
                    back_paths.append(path)
                else:
                    front_paths.append(path)

        plane_color = PLANE_COLOR if self.use_zone_colors else self.stroke_color
        edge_color = EDGE_COLOR if self.use_zone_colors else self.stroke_color
        dash_attr = f' stroke-dasharray="{dash_back}"' if dash_back else ""

        svg: list[str] = ['<svg xmlns="http://www.w3.org/2000/svg">']
        for (name, fill, opacity, _limit), polygons in zip(_SHADE_TONES, shade):
            if not polygons:
                continue
            svg.append(f'<g title="asaro-shade-{name}" stroke="none">')
            svg.append(
                f'<path d="{"".join(polygons)}" fill="{fill}" '
                f'fill-opacity="{opacity}" stroke="none"/>'
            )
            svg.append("</g>")
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
