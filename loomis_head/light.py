# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Sombra direccional del craneo (terminador y modo cel).

Modulo independiente del generador: solo lee campos publicos del modelo con
``getattr`` (para tolerar modelos de versiones anteriores) y usa sus
``_circle_on_plane``/``_to_camera``/``_to_screen`` cuando existen, de modo que
la sombra caiga exactamente sobre el craneo dibujado, tambien cuando el craneo
es eliptico (``cranium_width``/``cranium_height``).

La region de sombra se construye sobre la esfera unidad en **espacio de
cabeza** (donde la geometria es exacta) y se proyecta con la misma cadena que
el generador: ``_to_camera`` (escala anisotropa + rotacion) y ``_to_screen``.
Sin esos metodos se cae al camino antiguo: circulos construidos con una base
local y rotados con ``q``.

Convenio de camara (el mismo del generador): +X derecha, +Y arriba, +Z hacia
el observador. El azimut se mide alrededor de +Y (0 = luz de frente, -35 =
luz desde la izquierda del espectador) y la elevacion sobre el horizonte.
"""

import math

from .euclid import Vector3
from .linalg import q_identity

# Tinte de sombra: violeta oscuro de la paleta, nunca negro puro.
SHADOW_FILL = "#2B2350"
# Puntos por circulo (terminador y contorno visible).
_SAMPLES = 96
# Terminador del nucleo de sombra en modo cel (n·L < c).
_CEL_CORE = -0.55
_TINY = 1e-9
_CUT = 1e-6


def _num(model, name: str, default: float) -> float:
    """Campo numerico del modelo, tolerante a ausencias y valores rotos."""
    try:
        value = float(getattr(model, name, default))
    except (TypeError, ValueError):
        return float(default)
    return value if math.isfinite(value) else float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _dist2(a: Vector3, b: Vector3) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z
    return dx * dx + dy * dy + dz * dz


def _basis(normal: Vector3) -> tuple[Vector3, Vector3]:
    """Dos ejes unitarios perpendiculares a ``normal``."""
    axes = (Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0), Vector3(0.0, 0.0, 1.0))
    helper = min(axes, key=lambda axis: abs(normal.dot(axis)))
    u = normal.cross(helper)
    magnitude = u.magnitude()
    if magnitude < _TINY:
        return Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0)
    u = u / magnitude
    return u, normal.cross(u)


def _basis_circle(
    normal: Vector3,
    center: Vector3,
    radius: float,
    samples: int,
) -> list[Vector3]:
    """Circunferencia de la esfera en espacio de cabeza (fallback sin modelo)."""
    u, v = _basis(normal)
    out: list[Vector3] = []
    for i in range(samples):
        t = 2.0 * math.pi * i / samples
        out.append(center + u * (radius * math.cos(t)) + v * (radius * math.sin(t)))
    return out


def _model_circle(
    model,
    normal: Vector3,
    center: Vector3,
    radius: float,
    samples: int,
) -> list[Vector3] | None:
    """Circunferencia con el ``_circle_on_plane`` del modelo; ``None`` si no hay."""
    circle = getattr(model, "_circle_on_plane", None)
    if not callable(circle):
        return None
    try:
        raw = circle(normal, center, radius, samples)
        out = [Vector3(float(p.x), float(p.y), float(p.z)) for p in raw]
    except Exception:
        return None
    if len(out) < 3:
        return None
    if any(not (math.isfinite(p.x) and math.isfinite(p.y) and math.isfinite(p.z)) for p in out):
        return None
    return out


def _limb_circle(model, normal: Vector3, rc: float, samples: int) -> list[Vector3]:
    """Contorno visible de la esfera (plano perpendicular a la vista)."""
    out = _model_circle(model, normal, Vector3(0.0, 0.0, 0.0), rc, samples)
    if out is not None:
        return out
    return _basis_circle(normal, Vector3(0.0, 0.0, 0.0), rc, samples)


def _level_circle(
    model,
    light_head: Vector3,
    threshold: float,
    rc: float,
    samples: int,
) -> list[Vector3]:
    """Circunferencia de la esfera donde n·L = threshold, en espacio de cabeza."""
    center = light_head * (threshold * rc)
    radius = rc * math.sqrt(max(0.0, 1.0 - threshold * threshold))
    out = _model_circle(model, light_head, center, radius, samples)
    if out is not None:
        return out
    return _basis_circle(light_head, center, radius, samples)


def _to_camera(model, poly: list[Vector3]) -> list[Vector3]:
    """Espacio de cabeza -> camara; usa el ``_to_camera`` del modelo si existe."""
    to_camera = getattr(model, "_to_camera", None)
    if callable(to_camera):
        try:
            raw = to_camera(poly)
            out = [Vector3(float(p.x), float(p.y), float(p.z)) for p in raw]
        except Exception:
            out = []
        if len(out) == len(poly) and all(
            math.isfinite(p.x) and math.isfinite(p.y) and math.isfinite(p.z) for p in out
        ):
            return out
    q = getattr(model, "q", None)
    if q is None or not hasattr(q, "conjugated"):
        q = q_identity()
    try:
        return [q * p for p in poly]
    except Exception:
        return list(poly)


def _view_head(model) -> Vector3:
    """Direccion de vista (normal del plano de silueta) en espacio de cabeza."""
    q = getattr(model, "q", None)
    if q is None or not hasattr(q, "conjugated"):
        q = q_identity()
    try:
        normal = q.conjugated() * Vector3(0.0, 0.0, 1.0)
    except Exception:
        return Vector3(0.0, 0.0, 1.0)
    magnitude = normal.magnitude()
    if not math.isfinite(magnitude) or magnitude < _TINY:
        return Vector3(0.0, 0.0, 1.0)
    return normal / magnitude


def _circular_run(flags: list[bool]) -> tuple[int, int] | None:
    """Arco True mas largo de una lista circular: (inicio, longitud)."""
    count = len(flags)
    if count == 0:
        return None
    if all(flags):
        return (0, count)
    if not any(flags):
        return None
    start = flags.index(False)
    best_start = 0
    best_len = 0
    run_start = None
    run_len = 0
    for step in range(1, count + 1):
        index = (start + step) % count
        if flags[index]:
            if run_start is None:
                run_start = index
                run_len = 0
            run_len += 1
            if run_len > best_len:
                best_len = run_len
                best_start = run_start
        else:
            run_start = None
            run_len = 0
    return (best_start, best_len) if best_len else None


def _extract_run(points: list[Vector3], run: tuple[int, int]) -> list[Vector3]:
    start, length = run
    count = len(points)
    return [points[(start + i) % count] for i in range(length)]


def _region_polys(
    model,
    light_head: Vector3,
    view_head: Vector3,
    threshold: float,
    rc: float,
) -> list[list[Vector3]]:
    """Poligonos (espacio de cabeza) de la zona visible con n·L < threshold.

    La region se corta con el disco visible: su frontera son el arco visible
    del terminador (o de la circunferencia de nivel) y el arco del contorno en
    sombra. Los agujeros se resuelven con ``fill-rule="evenodd"``.

    Todo se calcula sobre la esfera de radio ``rc`` en espacio de cabeza, donde
    ``view_head`` es la normal del plano de silueta; el resultado se proyecta
    luego con ``_to_camera``, que aplica el craneo eliptico.
    """
    # light_cam.z == light_head · view_head: positivo si la luz viene de delante.
    cos_view = _clamp(light_head.dot(view_head), -1.0, 1.0)
    s2 = max(0.0, 1.0 - cos_view * cos_view)
    s = math.sqrt(s2)
    limb = _limb_circle(model, view_head, rc, _SAMPLES)

    if threshold >= 1.0 - _CUT:
        return []
    if threshold <= -1.0 + _CUT:
        return [limb]

    if s < _TINY:
        # Luz sobre el eje de vista: el nivel proyecta un circulo concentrico
        # y la region es un disco, un anillo o un casquete.
        level = _level_circle(model, light_head, threshold, rc, _SAMPLES)
        if cos_view >= 0.0:
            return [] if threshold <= 0.0 else [limb, level]
        return [limb] if threshold >= 0.0 else [level]

    if threshold >= s - _CUT:
        # Todo el contorno en sombra; solo queda agujero si el nivel es visible.
        if cos_view > 0.0:
            return [limb, _level_circle(model, light_head, threshold, rc, _SAMPLES)]
        return [limb]

    if threshold <= -s + _CUT:
        # Todo el contorno iluminado; la sombra solo existe si el nivel se ve.
        if cos_view < 0.0:
            return [_level_circle(model, light_head, threshold, rc, _SAMPLES)]
        return []

    # Caso general: el nivel cruza el contorno en dos puntos exactos.
    # p·L = threshold y p·V = 0 sobre |p| = rc.
    foot = light_head * (threshold / s2) - view_head * (threshold * cos_view / s2)
    half2 = rc * rc - threshold * threshold / s2
    if half2 <= 0.0:
        return []
    half = math.sqrt(half2)
    axis = light_head.cross(view_head)
    axis_len = axis.magnitude()
    if axis_len < _TINY:
        return []
    axis = axis / axis_len
    p1 = foot + axis * half
    p2 = foot - axis * half

    terminator = _level_circle(model, light_head, threshold, rc, _SAMPLES)
    run = _circular_run([point.dot(view_head) >= -_CUT for point in terminator])
    if run is None:
        return []
    arc = _extract_run(terminator, run)
    if _dist2(arc[0], p1) > _dist2(arc[-1], p1):
        arc.reverse()
    arc[0] = p1
    arc[-1] = p2

    run = _circular_run([point.dot(light_head) < threshold for point in limb])
    if run is None:
        return []
    shadow_limb = _extract_run(limb, run)
    if _dist2(shadow_limb[0], p2) > _dist2(shadow_limb[-1], p2):
        shadow_limb.reverse()
    shadow_limb[0] = p2
    shadow_limb[-1] = p1

    return [arc + shadow_limb[1:]]


def _clip_slab(poly: list[Vector3], d: float) -> list[Vector3]:
    """Recorta un poligono cerrado al slab ``-d <= x <= d`` en espacio de cabeza.

    El generador dibuja el craneo solo dentro de esa banda (``side_cut``); sin
    este recorte la sombra se saldria por los lados hasta ``|x| = rc``. Se usa
    Sutherland-Hodgman para conservar el poligono cerrado (una region convexa
    recortada sigue siendo un unico poligono valido para ``fill-rule``).
    """
    out = list(poly)
    # Dos semiplanos: x <= d y x >= -d.
    for bound, keep_low in ((d, True), (-d, False)):
        if not out:
            return []
        clipped: list[Vector3] = []
        prev = out[-1]
        prev_in = prev.x <= bound + _CUT if keep_low else prev.x >= bound - _CUT
        for cur in out:
            cur_in = cur.x <= bound + _CUT if keep_low else cur.x >= bound - _CUT
            if cur_in != prev_in:
                dx = cur.x - prev.x
                if abs(dx) > _TINY:
                    t = (bound - prev.x) / dx
                    clipped.append(
                        Vector3(
                            prev.x + (cur.x - prev.x) * t,
                            prev.y + (cur.y - prev.y) * t,
                            prev.z + (cur.z - prev.z) * t,
                        )
                    )
                else:
                    clipped.append(Vector3(bound, cur.y, cur.z))
            if cur_in:
                clipped.append(cur)
            prev = cur
            prev_in = cur_in
        out = clipped
    return out


def _screen_points(
    model,
    poly: list[Vector3],
    width: float,
    height: float,
) -> list[tuple[float, float]] | None:
    """Proyeccion a documento; usa la del modelo para no desalinearse."""
    to_screen = getattr(model, "_to_screen", None)
    if callable(to_screen):
        try:
            return [(float(v.x), float(v.y)) for v in to_screen(poly, width, height)]
        except Exception:
            return None
    scale = min(width, height) * 0.3 * _num(model, "scale", 1.0)
    if not math.isfinite(scale) or scale == 0.0:
        return None
    pos_x = _num(model, "position_x", 0.0)
    pos_y = _num(model, "position_y", 0.0)
    return [(point.x * scale + pos_x, pos_y - point.y * scale) for point in poly]


def _path_data(model, polys: list[list[Vector3]], width: float, height: float) -> str:
    chunks: list[str] = []
    for poly in polys:
        if len(poly) < 3:
            continue
        points = _screen_points(model, poly, width, height)
        if points is None or len(points) < 3:
            continue
        if any(not (math.isfinite(x) and math.isfinite(y)) for x, y in points):
            continue
        chunks.append("M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points) + " Z")
    return " ".join(chunks)


def shadow_svg(model, width: float, height: float) -> str:
    """SVG de la sombra del craneo para ``model``; ``""`` si no aplica."""
    if not getattr(model, "show_shadow", False):
        return ""
    try:
        w = float(width)
        h = float(height)
    except (TypeError, ValueError):
        return ""
    if not (math.isfinite(w) and math.isfinite(h)) or w <= 0.0 or h <= 0.0:
        return ""

    intensity = _clamp(_num(model, "light_intensity", 0.35), 0.0, 1.0)
    if intensity <= 0.0:
        return ""
    rc = _num(model, "radius", 1.0) * _num(model, "cranium", 1.0)
    if not math.isfinite(rc) or rc <= 0.0:
        return ""

    azimuth = math.radians(_num(model, "light_azimuth", -35.0))
    elevation = math.radians(_clamp(_num(model, "light_elevation", 35.0), -90.0, 90.0))
    light_cam = Vector3(
        math.cos(elevation) * math.sin(azimuth),
        math.sin(elevation),
        math.cos(elevation) * math.cos(azimuth),
    )
    magnitude = light_cam.magnitude()
    if not math.isfinite(magnitude) or magnitude < _TINY:
        return ""
    light_cam = light_cam / magnitude

    q = getattr(model, "q", None)
    if q is None or not hasattr(q, "conjugated"):
        q = q_identity()
    try:
        light_head = q.conjugated() * light_cam
    except Exception:
        return ""
    magnitude = light_head.magnitude()
    if not math.isfinite(magnitude) or magnitude < _TINY:
        return ""
    light_head = light_head / magnitude
    view_head = _view_head(model)

    if _num(model, "shadow_mode", 0.0) >= 1.0:
        # Cel: dos bandas de valor; la segunda oscurece el nucleo.
        bands = ((0.0, intensity * 0.5), (_CEL_CORE, intensity * 0.8))
    else:
        bands = ((0.0, intensity),)

    # Mismo recorte lateral que el generador (espacio de cabeza): el craneo se
    # dibuja solo en |x_head| <= d, asi que la sombra no puede salir de ahi.
    d = _clamp(_num(model, "side_cut", 0.66), 0.05, 0.9) * rc

    parts: list[str] = []
    for threshold, opacity in bands:
        polys = _region_polys(model, light_head, view_head, threshold, rc)
        clipped: list[list[Vector3]] = []
        for poly in polys:
            cut = _clip_slab(poly, d)
            if len(cut) >= 3:
                clipped.append(cut)
        if not clipped:
            continue
        # Misma cadena que el generador: escala del craneo + rotacion + documento.
        polys = [_to_camera(model, poly) for poly in clipped]
        data = _path_data(model, polys, w, h)
        if not data:
            continue
        parts.append(
            f'<path d="{data}" fill="{SHADOW_FILL}" stroke="none" '
            f'fill-rule="evenodd" opacity="{opacity:.3f}"/>'
        )
    return "".join(parts)
