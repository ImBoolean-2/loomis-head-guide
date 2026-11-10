# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Cabeza Asaro: malla low-poly de planos, sin luz ni sombra.

El plugin usa la misma interfaz que :class:`LoomisHead3D` (escala, posicion,
quaternion, trazos, toggles y ``to_dict``/``from_dict``) para que el panel y la
capa vectorial funcionen sin cambios. Lo propio de Asaro es la malla de planos:
frente, ceja, cuenca, nariz, pomulo, maxilar, mandibula, menton, oreja,
occipucio y cuello, dibujada solo con aristas (sin relleno).

Construccion
------------
La malla se describe como un busto completo con el eje ``y`` hacia arriba, ``z``
hacia delante (la cara mira a ``+z``) y ``x`` lateral. Se modela solo la mitad
derecha (``x >= 0``); los vertices de ``x == 0`` son la linea central y se
comparten con la mitad izquierda.

Las columnas van del centro de la cara al centro de la nuca:

    F  centro de la cara: frente, nasion, dorso, punta, filtro, labios, surco,
       menton y garganta (es la silueta del perfil)
    G  ala de la nariz / comisura   H  pomulo / maxilar / mejilla
    J  lateral (sien, oreja, gonion)   K  centro de la nuca (occipucio)
    T, P  coronilla y frente laterales (filas del craneo)

La clave para que el perfil se lea: a 90 grados la silueta la forman
exclusivamente las columnas ``F`` y ``K`` (x == 0), porque el resto queda
detras. El perfil se disena, por tanto, moviendo ``F`` y ``K``; las demas
columnas solo agregan pliegues al frente y a los tres cuartos.

Proporciones (unidades del modelo, alto total 1.5):

    coronilla y=+0.75   ceja y=+0.40   menton y=-0.30   base y=-0.75
    ancho oreja a oreja 1.01   fondo nariz-occipucio 0.75

es decir, cara (ceja-menton) 44 % del alto, cuello 30 %, craneo 26 %. El fondo
(0.75) es 0.71 del alto de la cabeza sola (coronilla-menton, 1.05), que es la
proporcion real de un craneo; contra el alto del busto seria 0.50.

Las tiras laterales (``G-H``, ``H-J``, ``J-K``) tienen menos filas que la
central a proposito: donde una tira salta un vertice de la vecina queda una
esquina en T. Es intencional (malla de planos, no superficie subdividida): no
abre ningun hueco visible y ahorra caras para mantener el low-poly.
"""

import math
from collections.abc import Sequence

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

# Vertices de la mitad derecha (x >= 0). Los de x == 0 son la linea central y
# se comparten con la mitad izquierda; el resto se refleja.
#
# Ejes: x lateral (+ derecha), y arriba, z hacia delante (la cara mira a +z).
# El perfil a 90 grados solo ve (z, y): la silueta de la cara es la polilinea
# F (frente -> ceja -> nasion -> dorso -> punta -> filtro -> labios -> surco ->
# menton) y la de atras la polilinea K (coronilla -> occipucio -> nuca).
_HALF_VERTICES: dict[str, tuple[float, float, float]] = {
    # --- linea central de la cara (silueta del perfil) -------------------
    "F0": (0.000, 0.750, 0.030),    # coronilla, delante
    "F1": (0.000, 0.575, 0.255),    # frente (plano alto)
    "F2": (0.000, 0.360, 0.272),    # ceja / glabela (sobresale)
    "F3": (0.000, 0.285, 0.190),    # nasion (hundido bajo la ceja)
    "F4": (0.000, 0.195, 0.288),    # dorso de la nariz
    "F5": (0.000, 0.100, 0.415),    # punta de la nariz (punto mas adelante)
    "F6": (0.000, 0.020, 0.280),    # filtro / base nasal (muesca)
    "F7": (0.000, -0.050, 0.340),   # labio superior
    "F8": (0.000, -0.140, 0.316),   # labio inferior
    "F9": (0.000, -0.198, 0.272),   # surco mentoniano (escalon)
    "F10": (0.000, -0.300, 0.320),  # menton
    "F11": (0.000, -0.375, 0.170),  # bajo el menton
    "F12": (0.000, -0.560, 0.020),  # garganta (hueco bajo la mandibula)
    "F13": (0.000, -0.750, 0.110),  # base del busto, delante
    # --- linea central de la nuca ----------------------------------------
    "K0": (0.000, 0.725, -0.135),   # coronilla, detras
    "K1": (0.000, 0.565, -0.300),   # occipucio alto
    "K2": (0.000, 0.400, -0.335),   # occipucio
    "K3": (0.000, 0.200, -0.335),   # occipucio medio (punto mas atras)
    "K4": (0.000, -0.020, -0.310),  # occipucio bajo
    "K5": (0.000, -0.240, -0.255),  # nuca (arranca el cuello)
    "K6": (0.000, -0.520, -0.225),  # cuello, detras
    "K7": (0.000, -0.750, -0.165),  # base del busto, detras
    # --- coronilla (fila L0) ---------------------------------------------
    "T1": (0.165, 0.740, 0.005),
    "T2": (0.275, 0.690, -0.095),
    "T3": (0.250, 0.675, -0.225),
    # --- frente (fila L1) ------------------------------------------------
    "P1": (0.205, 0.575, 0.195),
    "P2": (0.355, 0.552, 0.045),
    "P3": (0.405, 0.545, -0.105),
    # --- columna G: ala de la nariz, comisura, menton --------------------
    "G1": (0.125, 0.360, 0.232),    # ceja, interior
    "G2": (0.098, 0.285, 0.105),    # cuenca, fondo (hundida)
    "G3": (0.078, 0.200, 0.258),    # lado del dorso
    "G4": (0.106, 0.105, 0.345),    # ala de la nariz
    "G5": (0.116, 0.022, 0.268),    # base nasal
    "G6": (0.155, -0.050, 0.310),   # comisura, arriba
    "G7": (0.160, -0.140, 0.290),   # comisura, abajo
    "G8": (0.140, -0.300, 0.282),   # menton, lateral
    "G9": (0.145, -0.375, 0.155),   # mandibula, bajo el menton
    "G10": (0.185, -0.750, 0.095),  # base del busto
    # --- columna H: borde de la cuenca, pomulo, mejilla ------------------
    "H1": (0.300, 0.340, 0.215),    # ceja, extremo exterior
    "H2": (0.340, 0.265, 0.070),    # borde orbitario exterior (hundido)
    "H3": (0.350, 0.190, 0.235),    # pomulo (bajo la cuenca)
    "H4": (0.320, 0.020, 0.190),    # mejilla
    "H5": (0.295, -0.285, 0.160),   # maxilar
    "H6": (0.235, -0.380, 0.115),   # mandibula, bajo el maxilar
    "H7": (0.260, -0.750, 0.000),   # base del busto
    # --- columna J: sien, oreja, gonion ----------------------------------
    "J1": (0.442, 0.405, -0.030),   # sien (ancho maximo del craneo)
    "J3": (0.442, 0.205, -0.120),   # delante de la oreja
    "J4": (0.410, 0.000, -0.190),   # gonion (angulo de la mandibula)
    "J5": (0.335, -0.245, -0.175),  # detras del angulo
    "J6": (0.255, -0.378, -0.075),  # mandibula, bajo la oreja
    "J7": (0.270, -0.750, -0.115),  # base del busto
    # --- oreja (cuna lateral; isla aparte, como en el modelo real) -------
    "E1": (0.476, 0.295, -0.100),   # oreja, arriba
    "E2": (0.505, 0.185, -0.160),   # helix (punto mas lateral del busto)
    "E3": (0.482, 0.005, -0.160),   # lobulo
    "E4": (0.470, 0.140, -0.275),   # raiz posterior
    # --- vertices solo del detalle 2 (centros de plano) ------------------
    "N1": (0.277, 0.637, 0.041),    # centro del plano de la frente
    "N2": (0.057, -0.095, 0.314),   # centro del plano del labio
    "N3": (0.170, 0.115, 0.245),    # centro del plano de la mejilla
}

# (nivel de detalle minimo, vertices en orden). Nivel 0 = planos grandes (malla
# minima: sin oreja ni pliegues finos), 1 = construccion estandar, 2 = planos
# subdivididos (ver ``_HALF_FINE``).
#
# Columnas y tiras, de delante a detras: F (centro), G, H, J, K (centro nuca).
# Una tira puede saltarse un vertice de la columna vecina: la arista larga que
# dibuja es un pliegue real (pomulo, comisura, mandibula), no un error.
_HALF_FACES: tuple[tuple[int, tuple[str, ...]], ...] = (
    # --- coronilla: tapa y dos filas hasta la ceja -----------------------
    (0, ("F0", "T1", "T2", "T3", "K0")),           # tapa de la coronilla
    (0, ("F0", "T1", "P1", "F1")),
    (0, ("T1", "T2", "P2", "P1")),
    (0, ("T2", "T3", "P3", "P2")),
    (0, ("T3", "K0", "K1", "P3")),
    (0, ("F1", "F2", "G1", "P1")),
    (0, ("P1", "G1", "H1", "P2")),
    (1, ("P2", "H1", "J1", "P3")),                 # sien
    (0, ("P3", "J1", "K2", "K1")),
    # --- tira F-G: perfil de la cara (hasta la mandibula) ----------------
    (0, ("F2", "F3", "G2", "G1")),                 # ceja -> nasion
    (0, ("F3", "F4", "G3", "G2")),                 # nasion -> dorso
    (0, ("F4", "F5", "G4", "G3")),                 # dorso -> punta
    (0, ("F5", "F6", "G5", "G4")),                 # punta -> base nasal
    (0, ("F6", "F7", "G6", "G5")),                 # base -> labio superior
    (0, ("F7", "F8", "G7", "G6")),                 # labio superior -> inferior
    (1, ("F8", "F9", "G7")),                       # surco mentoniano
    (0, ("F9", "F10", "G8", "G7")),                # surco -> menton
    (0, ("F10", "F11", "G9", "G8")),               # menton -> mandibula
    # --- tira G-H: cuenca, pomulo, mejilla, maxilar ----------------------
    (1, ("G1", "G2", "H2", "H1")),                 # cuenca (hundida)
    (0, ("G2", "G3", "H3", "H2")),                 # pomulo
    (0, ("G3", "G4", "G5", "H4", "H3")),           # mejilla (con el ala nasal)
    (1, ("G5", "G6", "G7", "H4")),                 # comisura
    (0, ("G7", "G8", "H5", "H4")),                 # maxilar
    (1, ("G8", "G9", "H6", "H5")),                 # mandibula
    # --- tira H-J: lateral del craneo y del maxilar ----------------------
    (1, ("H1", "H2", "J3", "J1")),                 # sien -> delante de la oreja
    (0, ("H2", "H3", "J3")),                       # pomulo
    (0, ("H3", "H4", "J4", "J3")),                 # pomulo -> mejilla
    (0, ("H4", "H5", "J5", "J4")),                 # mejilla -> gonion
    (1, ("H5", "H6", "J6", "J5")),                 # mandibula
    # --- tira J-K: occipucio ---------------------------------------------
    (0, ("J1", "J3", "K3", "K2")),
    (0, ("J3", "J4", "K4", "K3")),
    (0, ("J4", "J5", "K5", "K4")),
    (1, ("J5", "J6", "K5")),
    # --- oreja -----------------------------------------------------------
    (1, ("E1", "E2", "E4")),
    (1, ("E2", "E3", "E4")),
)

# Cuello y base del busto: solo con ``show_neck``. La fila superior es el anillo
# de la mandibula (F11, G9, H6, J6, K5); la inferior, la base.
_HALF_NECK_FACES: tuple[tuple[int, tuple[str, ...]], ...] = (
    (0, ("F11", "F12", "G10", "G9")),              # garganta
    (0, ("F12", "F13", "G10")),                    # garganta -> base
    (0, ("G9", "G10", "H7", "H6")),                # lateral del cuello
    (0, ("H6", "H7", "J7", "J6")),
    (0, ("J6", "J7", "K7", "K6", "K5")),           # nuca del cuello
)

# Tapon cuando no hay cuello: la mandibula se cierra y la cabeza queda maciza.
_HALF_CLOSED_FACES: tuple[tuple[int, tuple[str, ...]], ...] = (
    (0, ("F11", "G9", "H6", "J6", "K5")),
)

# Detalle 2: cada cara se parte en abanico desde un vertice central. Se declara
# (cara original, vertice nuevo, caras nuevas); la original se sustituye, de
# modo que el nivel 2 subdivide planos grandes sin duplicar superficie.
_HALF_FINE: tuple[
    tuple[tuple[str, ...], str, tuple[tuple[str, ...], ...]], ...
] = (
    (
        ("T1", "T2", "P2", "P1"),
        "N1",
        (
            ("T1", "N1", "P1"),
            ("T1", "T2", "N1"),
            ("T2", "P2", "N1"),
            ("P2", "P1", "N1"),
        ),
    ),
    (
        ("F7", "F8", "G7", "G6"),
        "N2",
        (
            ("F7", "N2", "G6"),
            ("F7", "F8", "N2"),
            ("F8", "G7", "N2"),
            ("G7", "G6", "N2"),
        ),
    ),
    (
        ("G3", "G4", "G5", "H4", "H3"),
        "N3",
        (
            ("G3", "N3", "H3"),
            ("G3", "G4", "N3"),
            ("G4", "G5", "N3"),
            ("G5", "H4", "N3"),
            ("H4", "H3", "N3"),
        ),
    ),
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
        self.show_neck: bool = True
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
            "showNeck": self.show_neck,
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
    def _half_faces(self) -> list[tuple[str, ...]]:
        """Caras de la mitad derecha para el detalle y el cuello actuales."""
        out: list[tuple[str, ...]] = []
        for level, names in _HALF_FACES:
            if level <= self.detail:
                out.append(names)
        if self.detail >= 2:
            for original, _centre, halves in _HALF_FINE:
                if original in out:
                    out.remove(original)
                    out.extend(halves)
        if self.show_neck:
            for level, names in _HALF_NECK_FACES:
                if level <= self.detail:
                    out.append(names)
        else:
            for level, names in _HALF_CLOSED_FACES:
                if level <= self.detail:
                    out.append(names)
        return out

    def _faces(self) -> list[tuple[str, ...]]:
        """Caras completas (derecha + reflejada)."""
        faces: list[tuple[str, ...]] = []
        for names in self._half_faces():
            faces.append(names)
            mirrored = tuple(_MIRROR[name] for name in names)
            if mirrored != names:
                faces.append(mirrored)
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

    def _edge_kinds(
        self, faces: Sequence[Sequence[str]]
    ) -> list[tuple[str, str, str]]:
        """Aristas a dibujar, con su tipo: ``front``, ``back`` o ``silhouette``.

        ``front``/``back`` dicen de que lado de la cabeza queda la arista (las de
        atras se dibujan punteadas). ``silhouette`` es el contorno: la arista
        entre una cara que mira a camara y otra que no. Sin ese caso el perfil
        quedaria abierto, porque en el centro de la cara las dos mitades son
        coplanares y el pliegue no llega al umbral.
        """
        normals: list[tuple[float, float, float]] = []
        facing: list[bool] = []
        for names in faces:
            nx, ny, nz = self._face_normal(names)
            normal_cam = self.q * Vector3(nx, ny, nz)
            normals.append((nx, ny, nz))
            facing.append(normal_cam.z > _FACING_EPS)

        adjacency: dict[tuple[str, str], list[int]] = {}
        for index, names in enumerate(faces):
            n = len(names)
            for i in range(n):
                a = names[i]
                b = names[(i + 1) % n]
                key = (a, b) if a < b else (b, a)
                adjacency.setdefault(key, []).append(index)

        cos_limit = math.cos(math.radians(_CREASE_DEG))
        out: list[tuple[str, str, str]] = []
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

    def _edges(self, faces: Sequence[Sequence[str]]) -> list[tuple[str, str]]:
        """Aristas unicas de pliegue o silueta, cada una una sola vez."""
        return [(a, b) for a, b, _kind in self._edge_kinds(faces)]

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
            for a, b, kind in self._edge_kinds(faces):
                segment = [
                    self._to_camera(_VERTICES[a]),
                    self._to_camera(_VERTICES[b]),
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
