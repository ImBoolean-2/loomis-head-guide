# SPDX-FileCopyrightText: 2025 lm0ss
# SPDX-FileCopyrightText: 2026 Nedeljko Umjetnik
# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

import math
from collections.abc import Sequence

from .euclid import Vector2, Vector3
from .geom_polyline import (
    EPS,
    clip_to_side_band,
    path_str,
    split_by_plane_facing,
    split_front_back,
)
ZONE_COLORS = {
    "cranium": "#6A54E7",
    "jaw": "#E76A54",
    "cheek": "#54C4E7",
    "rhythm": "#D96A8A",
    "features": "#E7C454",
    "hair": "#B07A52",
    "side": "#8A8A9A",
    "arrow": "#E754A8",
}


from .linalg import (
    Poly2,
    Poly3,
    Quaternion,
    linspace,
    normalize,
    q_identity,
    q_normalize,
)


class LoomisHead3D:
    def __init__(self) -> None:
        self.radius: float = 1.0
        self.scale: float = 1.0
        # Absolute document-pixel coordinates for the head's center.
        self.position_x: float = 0.0
        self.position_y: float = 0.0
        self.side_cut: float = 0.66
        # These controls affect only the added jaw/chin/cheek guides.
        # 100 preserves the original added-guide proportions.
        self.face_age: float = 1.0
        self.chin_width: float = 1.0
        # Caricatura: proporciones del craneo frente a la mandibula y curvas.
        self.cranium: float = 1.0
        self.jaw_taper: float = 1.0
        self.cheek: float = 0.0
        self.face_width: float = 1.0
        self.jaw_drop: float = 1.0
        # Proporciones (0.6.0): frente, mandibula, craneo, pomulo y menton.
        self.forehead_height: float = 1.0
        self.jaw_angle: float = 0.0
        self.cranium_width: float = 1.0
        self.cranium_height: float = 1.0
        self.cheekbone_height: float = 0.5
        self.chin_sharpness: float = 0.0
        # Sexo y construccion de cuenca orbitaria, ceja y mejillas (0.6.1).
        self.head_sex: int = 0
        self.brow_ridge: float = 0.5
        self.eye_socket_depth: float = 0.5
        self.eye_socket_size: float = 0.55
        self.show_eye_socket: bool = True
        self.cheek_fullness: float = 0.5
        self.show_rhythm: bool = False
        self.rhythm_strength: float = 0.6
        # Rasgos faciales (lineas de Loomis, cuencas, nariz, orejas, boca, cejas).
        self.show_features: bool = False
        self.show_hair: bool = False
        self.hair_line: float = 0.68
        self.hair_arch: float = 0.04
        self.hair_tilt: float = 0.0
        self.hair_part: int = 1
        self.hair_part_pos: float = 0.32
        self.hair_texture: int = 0
        self.use_zone_colors: bool = False
        self.brow_line: float = 0.62
        self.eye_line: float = 0.50
        self.nose_line: float = 0.32
        self.mouth_line: float = 0.18
        self.eye_gap: float = 0.42
        self.eye_size: float = 0.11
        self.nose_length: float = 0.12
        self.nose_width: float = 0.20
        self.ear_size: float = 0.13
        self.ear_height: float = 0.48
        self.mouth_width: float = 0.26
        self.mouth_curve: float = 0.03
        self.brow_height: float = 0.05
        self.show_eyes: bool = True
        self.show_nose: bool = True
        self.show_ears: bool = True
        self.show_mouth: bool = True
        self.show_brows: bool = True
        self.show_face: bool = True
        # Lineas de guia independientes (0.6.0); show_features sigue apagando todas.
        self.show_brow_guide: bool = True
        self.show_eye_guide: bool = True
        self.show_nose_guide: bool = True
        self.show_mouth_guide: bool = True
        self.front_line_stroke: float = 10.0
        self.back_line_stroke: float = 7.0
        self.show_arrow: bool = True
        self.show_silhouette: bool = True
        self.show_side_rims: bool = True
        self.show_side_cross: bool = True
        self.stroke_color: str = "#6A54E7"
        self.q: Quaternion = q_identity()

    def set_quaternion(self, q: Quaternion) -> None:
        self.q = q_normalize(q)

    def set_scale(self, scale: float) -> None:
        self.scale = max(0.05, min(5.0, float(scale)))

    def set_position_x(self, position_x: float) -> None:
        self.position_x = float(position_x)

    def set_position_y(self, position_y: float) -> None:
        self.position_y = float(position_y)

    def set_sidecut(self, side_cut: float) -> None:
        self.side_cut = side_cut

    def set_face_age(self, face_age: float) -> None:
        self.face_age = max(0.0, min(1.0, float(face_age)))

    def set_chin_width(self, chin_width: float) -> None:
        self.chin_width = max(0.5, min(1.5, float(chin_width)))

    def set_cranium(self, value: float) -> None:
        self.cranium = max(0.6, min(1.6, float(value)))

    def set_jaw_taper(self, value: float) -> None:
        self.jaw_taper = max(0.4, min(1.6, float(value)))

    def set_cheek(self, value: float) -> None:
        self.cheek = max(0.0, min(1.0, float(value)))

    def set_face_width(self, value: float) -> None:
        self.face_width = max(0.6, min(1.4, float(value)))

    def set_jaw_drop(self, value: float) -> None:
        self.jaw_drop = max(0.6, min(1.4, float(value)))

    def set_forehead_height(self, value: float) -> None:
        self.forehead_height = max(0.6, min(1.4, float(value)))

    def set_jaw_angle(self, value: float) -> None:
        self.jaw_angle = self._clamp01(value)

    def set_cranium_width(self, value: float) -> None:
        self.cranium_width = max(0.8, min(1.2, float(value)))

    def set_cranium_height(self, value: float) -> None:
        self.cranium_height = max(0.8, min(1.2, float(value)))

    def set_cheekbone_height(self, value: float) -> None:
        self.cheekbone_height = self._clamp01(value)

    def set_chin_sharpness(self, value: float) -> None:
        self.chin_sharpness = self._clamp01(value)

    def set_head_sex(self, value: int) -> None:
        self.head_sex = max(0, min(1, int(value)))

    def set_brow_ridge(self, value: float) -> None:
        self.brow_ridge = self._clamp01(value)

    def set_eye_socket_depth(self, value: float) -> None:
        self.eye_socket_depth = self._clamp01(value)

    def set_eye_socket_size(self, value: float) -> None:
        self.eye_socket_size = max(0.2, min(0.9, float(value)))

    def set_show_eye_socket(self, enable: bool) -> None:
        self.show_eye_socket = bool(enable)

    def set_cheek_fullness(self, value: float) -> None:
        self.cheek_fullness = self._clamp01(value)

    def set_show_rhythm(self, enable: bool) -> None:
        self.show_rhythm = bool(enable)

    def set_rhythm_strength(self, value: float) -> None:
        self.rhythm_strength = self._clamp01(value)

    def set_show_features(self, enable: bool) -> None:
        self.show_features = bool(enable)

    def set_zone_colors(self, enable: bool) -> None:
        self.use_zone_colors = bool(enable)

    def set_show_hair(self, enable: bool) -> None:
        self.show_hair = bool(enable)

    def set_hair_line(self, value: float) -> None:
        self.hair_line = max(0.55, min(0.85, float(value)))

    def set_hair_arch(self, value: float) -> None:
        self.hair_arch = max(0.0, min(0.2, float(value)))

    def set_hair_tilt(self, value: float) -> None:
        self.hair_tilt = max(-0.2, min(0.2, float(value)))

    def set_hair_part(self, value: int) -> None:
        self.hair_part = max(0, min(2, int(value)))

    def set_hair_part_pos(self, value: float) -> None:
        self.hair_part_pos = max(-0.9, min(0.9, float(value)))

    def set_hair_texture(self, value: int) -> None:
        self.hair_texture = max(0, min(3, int(value)))

    def _clamp01(self, value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def set_brow_line(self, value: float) -> None:
        self.brow_line = self._clamp01(value)

    def set_eye_line(self, value: float) -> None:
        self.eye_line = self._clamp01(value)

    def set_nose_line(self, value: float) -> None:
        self.nose_line = self._clamp01(value)

    def set_mouth_line(self, value: float) -> None:
        self.mouth_line = self._clamp01(value)

    def set_eye_gap(self, value: float) -> None:
        self.eye_gap = self._clamp01(value)

    def set_eye_size(self, value: float) -> None:
        self.eye_size = max(0.02, min(0.4, float(value)))

    def set_nose_length(self, value: float) -> None:
        self.nose_length = max(0.02, min(0.35, float(value)))

    def set_nose_width(self, value: float) -> None:
        self.nose_width = max(0.02, min(0.5, float(value)))

    def set_ear_size(self, value: float) -> None:
        self.ear_size = max(0.02, min(0.4, float(value)))

    def set_ear_height(self, value: float) -> None:
        self.ear_height = self._clamp01(value)

    def set_mouth_width(self, value: float) -> None:
        self.mouth_width = max(0.02, min(0.6, float(value)))

    def set_mouth_curve(self, value: float) -> None:
        self.mouth_curve = max(-0.15, min(0.15, float(value)))

    def set_brow_height(self, value: float) -> None:
        self.brow_height = max(0.0, min(0.2, float(value)))

    def set_show_eyes(self, enable: bool) -> None:
        self.show_eyes = bool(enable)

    def set_show_nose(self, enable: bool) -> None:
        self.show_nose = bool(enable)

    def set_show_ears(self, enable: bool) -> None:
        self.show_ears = bool(enable)

    def set_show_mouth(self, enable: bool) -> None:
        self.show_mouth = bool(enable)

    def set_show_brows(self, enable: bool) -> None:
        self.show_brows = bool(enable)

    def set_show_face(self, enable: bool) -> None:
        self.show_face = bool(enable)

    def set_show_brow_guide(self, enable: bool) -> None:
        self.show_brow_guide = bool(enable)

    def set_show_eye_guide(self, enable: bool) -> None:
        self.show_eye_guide = bool(enable)

    def set_show_nose_guide(self, enable: bool) -> None:
        self.show_nose_guide = bool(enable)

    def set_show_mouth_guide(self, enable: bool) -> None:
        self.show_mouth_guide = bool(enable)

    def set_front_line_stroke(self, front_line_stroke: float) -> None:
        self.front_line_stroke = max(0.5, min(60.0, float(front_line_stroke)))

    def set_back_line_stroke(self, back_line_stroke: float) -> None:
        self.back_line_stroke = max(0.5, min(60.0, float(back_line_stroke)))

    def set_arrow(self, enable: bool) -> None:
        self.show_arrow = enable

    def set_silhouette(self, enable: bool) -> None:
        self.show_silhouette = enable

    def set_side_rims(self, enable: bool) -> None:
        self.show_side_rims = enable

    def set_side_cross(self, enable: bool) -> None:
        self.show_side_cross = enable

    def set_stroke_color(self, color: str) -> None:
        self.stroke_color = color

    def _effective_hair_line(self) -> float:
        """Linea de nacimiento del pelo ya escalada por forehead_height."""
        line = self.brow_line + (self.hair_line - self.brow_line) * self.forehead_height
        return max(0.55, min(0.85, line))

    def to_dict(self) -> dict:
        """Estado completo del cabezal, listo para un preset."""
        return {
            "version": 1,
            "generator": "loomis",
            "model": "loomis",
            "scale": self.scale,
            "positionX": self.position_x,
            "positionY": self.position_y,
            "rotation": [self.q.w, self.q.x, self.q.y, self.q.z],
            "sideCut": self.side_cut,
            "faceAge": self.face_age,
            "chinWidth": self.chin_width,
            "cranium": self.cranium,
            "jawTaper": self.jaw_taper,
            "cheek": self.cheek,
            "faceWidth": self.face_width,
            "jawDrop": self.jaw_drop,
            "foreheadHeight": self.forehead_height,
            "jawAngle": self.jaw_angle,
            "craniumWidth": self.cranium_width,
            "craniumHeight": self.cranium_height,
            "cheekboneHeight": self.cheekbone_height,
            "chinSharpness": self.chin_sharpness,
            "headSex": self.head_sex,
            "browRidge": self.brow_ridge,
            "eyeSocketDepth": self.eye_socket_depth,
            "eyeSocketSize": self.eye_socket_size,
            "showEyeSocket": self.show_eye_socket,
            "cheekFullness": self.cheek_fullness,
            "showRhythm": self.show_rhythm,
            "rhythmStrength": self.rhythm_strength,
            "showFeatures": self.show_features,
            "showHair": self.show_hair,
            "hairLine": self.hair_line,
            "hairArch": self.hair_arch,
            "hairTilt": self.hair_tilt,
            "hairPart": self.hair_part,
            "hairPartPos": self.hair_part_pos,
            "hairTexture": self.hair_texture,
            "useZoneColors": self.use_zone_colors,
            "browLine": self.brow_line,
            "eyeLine": self.eye_line,
            "noseLine": self.nose_line,
            "mouthLine": self.mouth_line,
            "eyeGap": self.eye_gap,
            "eyeSize": self.eye_size,
            "noseLength": self.nose_length,
            "noseWidth": self.nose_width,
            "earSize": self.ear_size,
            "earHeight": self.ear_height,
            "mouthWidth": self.mouth_width,
            "mouthCurve": self.mouth_curve,
            "browHeight": self.brow_height,
            "showEyes": self.show_eyes,
            "showNose": self.show_nose,
            "showEars": self.show_ears,
            "showMouth": self.show_mouth,
            "showBrows": self.show_brows,
            "showFace": self.show_face,
            "showBrowGuide": self.show_brow_guide,
            "showEyeGuide": self.show_eye_guide,
            "showNoseGuide": self.show_nose_guide,
            "showMouthGuide": self.show_mouth_guide,
            "showArrow": self.show_arrow,
            "showSilhouette": self.show_silhouette,
            "showSideRims": self.show_side_rims,
            "showSideCross": self.show_side_cross,
            "frontStroke": self.front_line_stroke,
            "backStroke": self.back_line_stroke,
            "strokeColor": self.stroke_color,
        }

    def from_dict(self, data: dict) -> None:
        """Carga un preset tolerando claves ausentes o de otra version."""
        src = data if isinstance(data, dict) else {}

        def num(key: str, default: float) -> float:
            try:
                return float(src.get(key, default))
            except (TypeError, ValueError):
                return default

        def flag(key: str, default: bool) -> bool:
            value = src.get(key, default)
            return bool(value)

        self.set_scale(num("scale", self.scale))
        self.set_position_x(num("positionX", self.position_x))
        self.set_position_y(num("positionY", self.position_y))
        rotation = src.get("rotation")
        if isinstance(rotation, (list, tuple)) and len(rotation) == 4:
            try:
                w, x, y, z = (float(v) for v in rotation)
                self.set_quaternion(Quaternion(w, x, y, z))
            except (TypeError, ValueError):
                pass
        self.set_sidecut(num("sideCut", self.side_cut))
        self.set_face_age(num("faceAge", self.face_age))
        self.set_chin_width(num("chinWidth", self.chin_width))
        self.set_cranium(num("cranium", self.cranium))
        self.set_jaw_taper(num("jawTaper", self.jaw_taper))
        self.set_cheek(num("cheek", self.cheek))
        self.set_face_width(num("faceWidth", self.face_width))
        self.set_jaw_drop(num("jawDrop", self.jaw_drop))
        self.set_forehead_height(num("foreheadHeight", self.forehead_height))
        self.set_jaw_angle(num("jawAngle", self.jaw_angle))
        self.set_cranium_width(num("craniumWidth", self.cranium_width))
        self.set_cranium_height(num("craniumHeight", self.cranium_height))
        self.set_cheekbone_height(num("cheekboneHeight", self.cheekbone_height))
        self.set_chin_sharpness(num("chinSharpness", self.chin_sharpness))
        self.set_head_sex(int(num("headSex", self.head_sex)))
        self.set_brow_ridge(num("browRidge", self.brow_ridge))
        self.set_eye_socket_depth(num("eyeSocketDepth", self.eye_socket_depth))
        self.set_eye_socket_size(num("eyeSocketSize", self.eye_socket_size))
        self.set_show_eye_socket(flag("showEyeSocket", self.show_eye_socket))
        self.set_cheek_fullness(num("cheekFullness", self.cheek_fullness))
        self.set_show_rhythm(flag("showRhythm", self.show_rhythm))
        self.set_rhythm_strength(num("rhythmStrength", self.rhythm_strength))
        self.set_show_features(flag("showFeatures", self.show_features))
        self.set_show_hair(flag("showHair", self.show_hair))
        self.set_hair_line(num("hairLine", self.hair_line))
        self.set_hair_arch(num("hairArch", self.hair_arch))
        self.set_hair_tilt(num("hairTilt", self.hair_tilt))
        self.set_hair_part(int(num("hairPart", self.hair_part)))
        self.set_hair_part_pos(num("hairPartPos", self.hair_part_pos))
        self.set_hair_texture(int(num("hairTexture", self.hair_texture)))
        self.set_zone_colors(flag("useZoneColors", self.use_zone_colors))
        self.set_brow_line(num("browLine", self.brow_line))
        self.set_eye_line(num("eyeLine", self.eye_line))
        self.set_nose_line(num("noseLine", self.nose_line))
        self.set_mouth_line(num("mouthLine", self.mouth_line))
        self.set_eye_gap(num("eyeGap", self.eye_gap))
        self.set_eye_size(num("eyeSize", self.eye_size))
        self.set_nose_length(num("noseLength", self.nose_length))
        self.set_nose_width(num("noseWidth", self.nose_width))
        self.set_ear_size(num("earSize", self.ear_size))
        self.set_ear_height(num("earHeight", self.ear_height))
        self.set_mouth_width(num("mouthWidth", self.mouth_width))
        self.set_mouth_curve(num("mouthCurve", self.mouth_curve))
        self.set_brow_height(num("browHeight", self.brow_height))
        self.set_show_eyes(flag("showEyes", self.show_eyes))
        self.set_show_nose(flag("showNose", self.show_nose))
        self.set_show_ears(flag("showEars", self.show_ears))
        self.set_show_mouth(flag("showMouth", self.show_mouth))
        self.set_show_brows(flag("showBrows", self.show_brows))
        self.set_show_face(flag("showFace", self.show_face))
        self.set_show_brow_guide(flag("showBrowGuide", self.show_brow_guide))
        self.set_show_eye_guide(flag("showEyeGuide", self.show_eye_guide))
        self.set_show_nose_guide(flag("showNoseGuide", self.show_nose_guide))
        self.set_show_mouth_guide(flag("showMouthGuide", self.show_mouth_guide))
        self.set_arrow(flag("showArrow", self.show_arrow))
        self.set_silhouette(flag("showSilhouette", self.show_silhouette))
        self.set_side_rims(flag("showSideRims", self.show_side_rims))
        self.set_side_cross(flag("showSideCross", self.show_side_cross))
        self.set_front_line_stroke(num("frontStroke", self.front_line_stroke))
        self.set_back_line_stroke(num("backStroke", self.back_line_stroke))
        color = src.get("strokeColor")
        if isinstance(color, str) and color.startswith("#") and len(color) in (4, 7):
            self.stroke_color = color

    def _basis_from_nnormal(self, n: Vector3 | Sequence[float]) -> tuple[Vector3, Vector3]:
        nn = n if isinstance(n, Vector3) else Vector3(*n)
        nn = normalize(nn)

        axes = [Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0), Vector3(0.0, 0.0, 1.0)]
        a = min(axes, key=lambda ax: abs(nn.dot(ax)))

        u = normalize(nn.cross(a))
        v = nn.cross(u)
        return u, v

    def _circle_on_plane(
        self,
        normal: Vector3 | Sequence[float],
        center: Sequence[float],
        radius: float,
        samples: int = 256,
    ) -> Poly3:
        u, v = self._basis_from_nnormal(normal)
        cx, cy, cz = center
        pts: Poly3 = []
        for t in linspace(0.0, 2.0 * math.pi, samples, endpoint=False):
            c, s = math.cos(t), math.sin(t)
            p = Vector3(cx, cy, cz) + u * (c * radius) + v * (s * radius)
            pts.append(p)
        return pts

    def _to_camera(self, pts: Sequence[Vector3]) -> Poly3:
        q = self.q
        # Craneo eliptico aproximado: escala anisotropa en espacio de cabeza.
        sx = self.cranium_width
        sy = self.cranium_height
        out: Poly3 = []
        for p in pts:
            pv = q * Vector3(p.x * sx, p.y * sy, p.z)
            out.append(pv)
        return out

    def _to_screen(
        self,
        pts_cam: Sequence[Vector3],
        w: float,
        h: float,
    ) -> Poly2:
        s = min(w, h) * 0.3 * self.scale
        xy: Poly2 = []
        for p in pts_cam:
            x_s = p.x * s + self.position_x
            y_s = self.position_y - p.y * s
            xy.append(Vector2(x_s, y_s))
        return xy

    def _emit_segments(
        self,
        segments: list[Poly3],
        width: float,
        height: float,
        front_paths: list[str],
        back_paths: list[str],
        plane_normal_cam: Vector3 | None = None,
    ) -> None:
        for segment in segments:
            segment_camera = self._to_camera(segment)
            if plane_normal_cam is None:
                fsegs, bsegs = split_front_back(segment_camera)
            else:
                fsegs, bsegs = split_by_plane_facing(segment_camera, plane_normal_cam)
            for s in bsegs:
                back_paths.append(path_str(self._to_screen(s, width, height)))
            for s in fsegs:
                front_paths.append(path_str(self._to_screen(s, width, height)))

    def _quadratic(self, p0: Vector3, p1: Vector3, p2: Vector3, samples: int = 33) -> Poly3:
        out: Poly3 = []
        for i in range(samples):
            u = 1.0 - i / (samples - 1)
            v = i / (samples - 1)
            out.append(p0 * (u * u) + p1 * (2.0 * u * v) + p2 * (v * v))
        return out

    def _catmull_rom(self, points: Sequence[Vector3], steps_per_segment: int = 24) -> Poly3:
        """Polilinea suave Catmull-Rom que pasa por todos los puntos dados."""
        if not points:
            return []
        if len(points) == 1:
            return [Vector3(points[0].x, points[0].y, points[0].z)]
        padded = [points[0], *points, points[-1]]
        out: Poly3 = []
        for i in range(len(padded) - 3):
            p0, p1, p2, p3 = padded[i], padded[i + 1], padded[i + 2], padded[i + 3]
            for s in range(steps_per_segment):
                t = s / float(steps_per_segment)
                t2 = t * t
                t3 = t2 * t
                out.append(Vector3(
                    0.5 * (2.0 * p1.x + (-p0.x + p2.x) * t
                           + (2.0 * p0.x - 5.0 * p1.x + 4.0 * p2.x - p3.x) * t2
                           + (-p0.x + 3.0 * p1.x - 3.0 * p2.x + p3.x) * t3),
                    0.5 * (2.0 * p1.y + (-p0.y + p2.y) * t
                           + (2.0 * p0.y - 5.0 * p1.y + 4.0 * p2.y - p3.y) * t2
                           + (-p0.y + 3.0 * p1.y - 3.0 * p2.y + p3.y) * t3),
                    0.5 * (2.0 * p1.z + (-p0.z + p2.z) * t
                           + (2.0 * p0.z - 5.0 * p1.z + 4.0 * p2.z - p3.z) * t2
                           + (-p0.z + 3.0 * p1.z - 3.0 * p2.z + p3.z) * t3),
                ))
        last = points[-1]
        out.append(Vector3(last.x, last.y, last.z))
        return out

    def _rhythm_curves(
        self,
        rc: float,
        jaw_front_endpoints: dict[float, Vector3] | None = None,
        chin_midpoint: Vector3 | None = None,
    ) -> list[Poly3]:
        """Curvas de ritmo de Reilly sobre la esfera del craneo.

        Perfil central corona -> ceja -> nariz -> boca -> menton, dos arcos
        laterales corona -> pomulo -> mandibula y el flujo de pelo. La
        intensidad `rhythm_strength` escala el desplazamiento lateral de los
        arcos y la curvatura del menton.
        """
        strength = max(0.0, min(1.0, self.rhythm_strength))

        def surf(x: float, y: float) -> Vector3:
            return Vector3(x, y, math.sqrt(max(rc * rc - x * x - y * y, EPS)))

        brow_y = (self.brow_line - 0.5) * 2.0 * rc
        nose_y = (self.nose_line - 0.5) * 2.0 * rc - self.nose_length * rc
        mouth_y = (self.mouth_line - 0.5) * 2.0 * rc

        crown = Vector3(0.0, rc, 0.0)
        brow = surf(0.0, brow_y)
        nose = surf(0.0, nose_y)
        mouth = surf(0.0, mouth_y)
        if chin_midpoint is None:
            chin_midpoint = Vector3(0.0, -1.22 * rc, rc)

        curves: list[Poly3] = []
        # Perfil central: pasa por ceja, nariz y boca pegandose a la esfera.
        profile = self._catmull_rom([crown, brow, nose, mouth], 24)
        for point in profile:
            y = max(point.y, mouth_y)
            point.y = y
            point.z = math.sqrt(max(rc * rc - point.x * point.x - y * y, EPS))
        # Del labio al menton la curva sale de la esfera: Bezier encadenada.
        chin_bow = 0.12 * rc * (0.35 + 0.65 * strength)
        chin_control = Vector3(
            0.0,
            (mouth.y + chin_midpoint.y) * 0.5,
            (mouth.z + chin_midpoint.z) * 0.5 + chin_bow,
        )
        profile.extend(self._quadratic(mouth, chin_control, chin_midpoint, 24)[1:])
        curves.append(profile)

        # Arcos laterales: corona -> pomulo -> mandibula.
        if jaw_front_endpoints is None:
            jaw_front_endpoints = {
                -1.0: Vector3(-0.55 * rc, -1.49 * rc, rc),
                1.0: Vector3(0.55 * rc, -1.49 * rc, rc),
            }
        for side in (-1.0, 1.0):
            crown_side = surf(side * (0.06 + 0.14 * strength) * rc, 0.96 * rc)
            cheek = surf(side * (0.38 + 0.22 * strength) * rc, brow_y - 0.18 * rc)
            jaw_end = jaw_front_endpoints[side]
            arc = self._catmull_rom([crown_side, cheek, jaw_end], 24)
            for point in arc:
                if point.y >= cheek.y:
                    point.z = math.sqrt(
                        max(rc * rc - point.x * point.x - point.y * point.y, EPS)
                    )
            curves.append(arc)

        # Flujo de pelo: corona hacia la raya.
        flow_start_y = (self._effective_hair_line() - 0.5) * 2.0 * rc
        flow_end_x = self.hair_part_pos * rc
        flow: Poly3 = []
        for i in range(33):
            t = i / 32.0
            y = rc * (1.0 - t) + flow_start_y * t
            x = flow_end_x * (t * t) + strength * 0.18 * rc * math.sin(math.pi * t)
            flow.append(surf(x, y))
        curves.append(flow)
        return curves

    def build_svg(self, width: float, height: float, dash_back: str | None = "5,6", samples: int = 256) -> str:
        r = self.radius
        rc = r * self.cranium
        d = max(0.05, min(0.9, float(self.side_cut))) * rc
        rim_r = math.sqrt(max(rc * rc - d * d, EPS))

        nx = Vector3(1.0, 0.0, 0.0)
        ny = Vector3(0.0, 1.0, 0.0)
        n_view = Vector3(0.0, 0.0, 1.0)
        n_sil_head = self.q.conjugated() * n_view

        n_plus_cam = self.q * nx
        n_minus_cam = self.q * (-nx)
        n_face_cam = self.q * n_view

        curves: list[Poly3] = []
        if self.show_silhouette:
            curves.append(self._circle_on_plane(n_sil_head, [0.0, 0.0, 0.0], rc, samples))

        curves.append(self._circle_on_plane(nx, [0.0, 0.0, 0.0], rc, samples))  # centerline
        curves.append(self._circle_on_plane(ny, [0.0, 0.0, 0.0], rc, samples))  # equator

        # Lineas clasicas de Loomis: ceja, ojos, nariz y boca.
        feature_curves: list[Poly3] = []
        if self.show_features:
            guides = (
                (self.show_brow_guide, self.brow_line),
                (self.show_eye_guide, self.eye_line),
                (self.show_nose_guide, self.nose_line),
                (self.show_mouth_guide, self.mouth_line),
            )
            for enabled, frac in guides:
                if not enabled:
                    continue
                y = (frac - 0.5) * 2.0 * rc
                radius = math.sqrt(max(rc * rc - y * y, EPS))
                circle = self._circle_on_plane(ny, [0.0, y, 0.0], radius, samples)
                # Solo el arco frontal: la nuca no lleva lineas de rasgos.
                feature_curves.append([point for point in circle if point.z >= -EPS])

        rims_plus: list[Poly3] = []
        rims_minus: list[Poly3] = []
        if self.show_side_rims:
            rims_plus.append(self._circle_on_plane(nx, [d, 0.0, 0.0], rim_r, samples))
            rims_minus.append(self._circle_on_plane(nx, [-d, 0.0, 0.0], rim_r, samples))

        crosses_plus: list[Poly3] = []
        crosses_minus: list[Poly3] = []
        if self.show_side_cross:
            crosses_plus.extend([
                [Vector3(d, -rim_r, 0.0), Vector3(d, rim_r, 0.0)],
                [Vector3(d, 0.0, -rim_r), Vector3(d, 0.0, rim_r)],
            ])
            crosses_minus.extend([
                [Vector3(-d, -rim_r, 0.0), Vector3(-d, rim_r, 0.0)],
                [Vector3(-d, 0.0, -rim_r), Vector3(-d, 0.0, rim_r)],
            ])

        # Jaw guide (con caricatura: craneo, caida, ancho y curva).
        jaw_curves: list[Poly3] = []
        jaw_front_endpoints: dict[float, Vector3] = {}
        age = self.face_age
        jaw_length = max(0.02, 0.8 * (1.22 * r - rim_r) * (0.65 + 0.35 * age) * self.jaw_drop)
        jaw_spread_angle = math.radians(10.0)
        front_extension_length = r
        front_down_angle = math.radians(12.0 + 8.0 * age)
        front_inward_angle = math.radians(15.0)
        taper = max(0.2, min(1.0, 0.9 * self.jaw_taper))
        # jaw_angle: 0 = curva actual, 1 = esquina marcada (control en el vertice).
        corner = taper + (1.0 - taper) * self.jaw_angle
        chin = self.chin_sharpness
        for side in (-1.0, 1.0):
            p0 = Vector3(side * d, -rim_r, 0.0)
            p1 = Vector3(
                (side * d - side * jaw_length * math.tan(jaw_spread_angle)) * self.face_width,
                -rim_r - jaw_length,
                0.0,
            )
            p2 = Vector3(
                (p1.x - side * front_extension_length * math.tan(front_inward_angle)) * self.chin_width,
                p1.y - front_extension_length * math.tan(front_down_angle),
                p1.z + front_extension_length,
            )
            if chin > 0.0:
                # Los dos extremos del menton convergen al centro y bajan.
                p2 = Vector3(p2.x * (1.0 - chin), p2.y - chin * 0.10 * rc, p2.z)
            c1 = p0 + (p1 - p0) * corner
            c2 = p2 - (p2 - p1) * corner
            curve: Poly3 = []
            for i in range(65):
                t = i / 64.0
                u = 1.0 - t
                curve.append(Vector3(
                    u*u*u*p0.x + 3*u*u*t*c1.x + 3*u*t*t*c2.x + t*t*t*p2.x,
                    u*u*u*p0.y + 3*u*u*t*c1.y + 3*u*t*t*c2.y + t*t*t*p2.y,
                    u*u*u*p0.z + 3*u*u*t*c1.z + 3*u*t*t*c2.z + t*t*t*p2.z,
                ))
            jaw_curves.append(curve)
            jaw_front_endpoints[side] = p2

        jaw_front_connector = [jaw_front_endpoints[-1.0], jaw_front_endpoints[1.0]]
        chin_midpoint = Vector3(
            (jaw_front_endpoints[-1.0].x + jaw_front_endpoints[1.0].x) * 0.5,
            (jaw_front_endpoints[-1.0].y + jaw_front_endpoints[1.0].y) * 0.5,
            (jaw_front_endpoints[-1.0].z + jaw_front_endpoints[1.0].z) * 0.5,
        )
        sphere_front_edge = Vector3(0.0, 0.0, rc)
        front_center_guide = [sphere_front_edge, chin_midpoint]

        # Cheekbone guides con pómulo ajustable.
        cheekbone_curves: list[Poly3] = []
        cheek_offset_y = (self.cheekbone_height - 0.5) * 0.8 * rim_r
        cheek_rim_z = math.sqrt(max(rim_r * rim_r - cheek_offset_y * cheek_offset_y, EPS))
        for side in (-1.0, 1.0):
            cheek_rim_touch = Vector3(side * d, cheek_offset_y, cheek_rim_z)
            cheek_end = jaw_front_endpoints[side]
            dx = cheek_end.x - cheek_rim_touch.x
            dy = cheek_end.y - cheek_rim_touch.y
            dz = cheek_end.z - cheek_rim_touch.z
            bow = side * self.cheek * 0.12 * r
            cheek_c1 = Vector3(
                cheek_rim_touch.x + 0.22 * dx + bow,
                cheek_rim_touch.y + 0.30 * dy,
                cheek_rim_touch.z + 0.22 * dz,
            )
            cheek_c2 = Vector3(
                cheek_rim_touch.x + 0.78 * dx + bow,
                cheek_rim_touch.y + 0.78 * dy,
                cheek_rim_touch.z + 0.78 * dz,
            )
            cheek_curve: Poly3 = [cheek_rim_touch]
            for i in range(1, 65):
                t = i / 64.0
                u = 1.0 - t
                cheek_curve.append(Vector3(
                    u*u*u*cheek_rim_touch.x + 3*u*u*t*cheek_c1.x + 3*u*t*t*cheek_c2.x + t*t*t*cheek_end.x,
                    u*u*u*cheek_rim_touch.y + 3*u*u*t*cheek_c1.y + 3*u*t*t*cheek_c2.y + t*t*t*cheek_end.y,
                    u*u*u*cheek_rim_touch.z + 3*u*u*t*cheek_c1.z + 3*u*t*t*cheek_c2.z + t*t*t*cheek_end.z,
                ))
            cheekbone_curves.append(cheek_curve)
            # Relleno de mejilla: arco cigomatico -> vertice de mandibula.
            fill_mid = (cheek_rim_touch + cheek_end) * 0.5 + Vector3(0.0, -0.06 * rc, 0.0)
            fill_bow = side * self.cheek_fullness * 0.10 * r
            fill_control = fill_mid + Vector3(fill_bow, 0.0, 0.0)
            cheekbone_curves.append(self._quadratic(cheek_rim_touch, fill_control, cheek_end))

        # Rasgos faciales opcionales.
        feature_front: list[Poly3] = []
        feature_side_plus: list[Poly3] = []
        feature_side_minus: list[Poly3] = []
        if self.show_features:
            def surf(x: float, y: float) -> Vector3:
                z = math.sqrt(max(rc * rc - x * x - y * y, EPS))
                return Vector3(x, y, z)

            eye_y = (self.eye_line - 0.5) * 2.0 * rc
            brow_y = (self.brow_line - 0.5) * 2.0 * rc
            nose_y = (self.nose_line - 0.5) * 2.0 * rc
            mouth_y = (self.mouth_line - 0.5) * 2.0 * rc
            eye_size = max(0.02, self.eye_size) * rc
            eye_gap = self.eye_gap * rc

            if self.show_eyes:
                for side in (-1.0, 1.0):
                    c = surf(side * eye_gap * 0.5, eye_y)
                    circle = self._circle_on_plane(n_view, [c.x, c.y, c.z], eye_size, 48)
                    feature_front.append([
                        Vector3(c.x + (point.x - c.x) * 1.35, point.y, point.z)
                        for point in circle
                    ])

            if self.show_eye_socket:
                # Cuenca orbitaria: rim exterior + fondo hundido + ticks de profundidad.
                depth = self.eye_socket_depth
                socket_size = self.eye_socket_size
                for side in (-1.0, 1.0):
                    c = surf(side * eye_gap * 0.5, eye_y)
                    rx = eye_size * (1.55 + 0.45 * self.brow_ridge)
                    ry = eye_size * (1.20 + 0.30 * self.brow_ridge)
                    rim = self._circle_on_plane(n_view, [c.x, c.y, c.z], 1.0, 48)
                    feature_front.append([
                        Vector3(c.x + (point.x - c.x) * rx,
                                c.y + (point.y - c.y) * ry,
                                point.z)
                        for point in rim
                    ])
                    inner_c = c + Vector3(
                        -side * eye_size * 0.28 * depth,
                        -eye_size * 0.18 * depth,
                        0.0,
                    )
                    rx2 = eye_size * (0.85 + 0.20 * socket_size)
                    ry2 = eye_size * (0.65 + 0.20 * socket_size)
                    bowl = self._circle_on_plane(
                        n_view, [inner_c.x, inner_c.y, inner_c.z], 1.0, 48
                    )
                    feature_front.append([
                        Vector3(inner_c.x + (point.x - inner_c.x) * rx2,
                                inner_c.y + (point.y - inner_c.y) * ry2,
                                point.z)
                        for point in bowl
                    ])
                    tick = eye_size * 0.20 * depth
                    if tick > EPS:
                        for sign in (1.0, -1.0):
                            rim_edge = Vector3(c.x, c.y + sign * ry, c.z)
                            bowl_edge = Vector3(inner_c.x, inner_c.y + sign * ry2, inner_c.z)
                            direction = bowl_edge - rim_edge
                            length = direction.magnitude()
                            if length > EPS:
                                feature_front.append([
                                    rim_edge,
                                    rim_edge + direction * (tick / length),
                                ])

            if self.show_brows:
                brow_w = eye_size * 2.2
                for side in (-1.0, 1.0):
                    cx = side * eye_gap * 0.5
                    p0b = surf(cx - brow_w * 0.5, brow_y)
                    p1b = surf(cx, brow_y + self.brow_height * rc)
                    p2b = surf(cx + brow_w * 0.5, brow_y)
                    feature_front.append(self._quadratic(p0b, p1b, p2b))
                    # Cresta superciliar por encima de la ceja.
                    ridge_y = brow_y + (self.brow_height + 0.05 * self.brow_ridge) * rc
                    r0 = surf(cx - brow_w * 0.5, ridge_y)
                    r1 = surf(cx, ridge_y + 0.01 * rc)
                    r2 = surf(cx + brow_w * 0.5, ridge_y)
                    feature_front.append(self._quadratic(r0, r1, r2))
                    ridge_tick = 0.02 * rc * self.brow_ridge
                    if ridge_tick > EPS:
                        apex = surf(cx, brow_y + self.brow_height * rc)
                        feature_front.append([
                            apex,
                            Vector3(apex.x, apex.y + ridge_tick, apex.z),
                        ])

            if self.show_nose:
                nose_w = max(0.02, self.nose_width) * rc
                tip_y = nose_y - self.nose_length * rc
                tip = surf(0.0, tip_y)
                tip = Vector3(tip.x, tip.y, tip.z + 0.10 * rc)
                bridge = surf(0.0, brow_y)
                left = surf(-nose_w * 0.5, nose_y)
                right = surf(nose_w * 0.5, nose_y)
                feature_front.extend([[bridge, tip], [tip, left], [tip, right], [left, right]])

            if self.show_ears:
                ear = max(0.02, self.ear_size) * rc
                ear_y = (self.ear_height - 0.5) * 2.0 * rc
                feature_side_minus.append(self._circle_on_plane(nx, [-d, ear_y, 0.0], ear, 48))
                feature_side_plus.append(self._circle_on_plane(nx, [d, ear_y, 0.0], ear, 48))

            if self.show_mouth:
                mouth_w = max(0.02, self.mouth_width) * rc
                p0m = surf(-mouth_w * 0.5, mouth_y)
                p1m = surf(0.0, mouth_y + self.mouth_curve * rc)
                p2m = surf(mouth_w * 0.5, mouth_y)
                feature_front.append(self._quadratic(p0m, p1m, p2m))

        hair_curves: list[Poly3] = []
        if self.show_hair:
            hy = (self._effective_hair_line() - 0.5) * 2.0 * rc
            hairline: Poly3 = []
            for i in range(65):
                t = -1.0 + 2.0 * i / 64.0
                y = hy - self.hair_arch * rc * (1.0 - t * t) + self.hair_tilt * rc * t
                if int(self.hair_texture) == 1:
                    y += 0.025 * rc * math.sin(t * 12.0)
                elif int(self.hair_texture) == 2:
                    y += 0.025 * rc * (1.0 if i % 2 else -1.0)
                elif int(self.hair_texture) == 3:
                    y += 0.02 * rc * math.sin(t * 24.0)
                max_x = min(math.sqrt(max(rc * rc - y * y, EPS)), d) * 0.98
                x = t * max_x
                z = math.sqrt(max(rc * rc - x * x - y * y, EPS))
                hairline.append(Vector3(x, y, z))
            hair_curves.append(hairline)
            crown = Vector3(0.0, rc, 0.0)
            target_x = self.hair_part_pos * rc
            target_y = hy
            target_z = math.sqrt(max(rc * rc - target_x * target_x - target_y * target_y, EPS))
            target = Vector3(target_x, target_y, target_z)
            part: Poly3 = []
            steps = 13 if int(self.hair_part) == 1 else 33
            for i in range(steps):
                t = i / float(steps - 1)
                point = crown * (1.0 - t) + target * t
                length = point.magnitude()
                if length > EPS:
                    point = point * (rc / length)
                if int(self.hair_part) == 1 and 0 < i < steps - 1:
                    sign = 1.0 if i % 2 else -1.0
                    point = Vector3(point.x + sign * 0.07 * rc, point.y, point.z)
                part.append(point)
            hair_curves.append(part)
            if int(self.hair_part) == 2:
                for side in (-1.0, 1.0):
                    tx = side * 0.55 * rc
                    tz = math.sqrt(max(rc * rc - tx * tx - target_y * target_y, EPS))
                    side_target = Vector3(tx, target_y, tz)
                    side_part: Poly3 = []
                    for i in range(33):
                        t = i / 32.0
                        point = crown * (1.0 - t) + side_target * t
                        length = point.magnitude()
                        if length > EPS:
                            point = point * (rc / length)
                        side_part.append(point)
                    hair_curves.append(side_part)

        # Curvas de ritmo de Reilly (perfil central, arcos laterales y flujo de pelo).
        rhythm_curves: list[Poly3] = []
        if self.show_rhythm:
            rhythm_curves = self._rhythm_curves(rc, jaw_front_endpoints, chin_midpoint)

        groups_front: dict[str, list[str]] = {key: [] for key in ZONE_COLORS if key != "arrow"}
        groups_back: dict[str, list[str]] = {key: [] for key in ZONE_COLORS if key != "arrow"}

        for c in curves:
            self._emit_segments(clip_to_side_band(c, d), width, height,
                                groups_front["cranium"], groups_back["cranium"])
        for c in rhythm_curves:
            self._emit_segments(clip_to_side_band(c, d), width, height,
                                groups_front["rhythm"], groups_back["rhythm"])
        for c in feature_curves:
            self._emit_segments(clip_to_side_band(c, d), width, height,
                                groups_front["features"], groups_back["features"])
        for c in hair_curves:
            self._emit_segments([c], width, height, groups_front["hair"], groups_back["hair"])
        if self.show_face:
            for jaw_curve in jaw_curves:
                self._emit_segments([jaw_curve], width, height,
                                    groups_front["jaw"], groups_back["jaw"])
            self._emit_segments([jaw_front_connector], width, height,
                                groups_front["jaw"], groups_back["jaw"])
            self._emit_segments([front_center_guide], width, height,
                                groups_front["jaw"], groups_back["jaw"])
            for cheekbone_curve in cheekbone_curves:
                self._emit_segments([cheekbone_curve], width, height,
                                    groups_front["cheek"], groups_back["cheek"])
        if self.show_features:
            for seg in feature_front:
                self._emit_segments([seg], width, height,
                                    groups_front["features"], groups_back["features"], n_face_cam)
            for seg in feature_side_plus:
                self._emit_segments([seg], width, height,
                                    groups_front["features"], groups_back["features"], n_plus_cam)
            for seg in feature_side_minus:
                self._emit_segments([seg], width, height,
                                    groups_front["features"], groups_back["features"], n_minus_cam)
        for rim in rims_plus:
            self._emit_segments([rim], width, height,
                                groups_front["side"], groups_back["side"], n_plus_cam)
        for rim in rims_minus:
            self._emit_segments([rim], width, height,
                                groups_front["side"], groups_back["side"], n_minus_cam)
        for seg in crosses_plus:
            self._emit_segments([seg], width, height,
                                groups_front["side"], groups_back["side"], n_plus_cam)
        for seg in crosses_minus:
            self._emit_segments([seg], width, height,
                                groups_front["side"], groups_back["side"], n_minus_cam)

        arrow_d = ""
        if self.show_arrow:
            base2 = self._to_screen(self._to_camera([Vector3(0.0, 0.0, 0.0)]), width, height)[0]
            tip2 = self._to_screen(self._to_camera([Vector3(0.0, 0.0, 1.15 * rc)]), width, height)[0]
            dv: Vector2 = tip2 - base2
            L = dv.magnitude()
            if L > 1.0:
                u = dv / L
                n = Vector2(-u.y, u.x)
                head_len = 0.04 * min(width, height)
                head_wid = 0.55 * head_len
                pL = tip2 - u * head_len + n * head_wid
                pR = tip2 - u * head_len - n * head_wid
                arrow_d = (
                    f"M {base2.x:.3f},{base2.y:.3f} L {tip2.x:.3f},{tip2.y:.3f} "
                    f"M {tip2.x:.3f},{tip2.y:.3f} L {pL.x:.3f},{pL.y:.3f} "
                    f"M {tip2.x:.3f},{tip2.y:.3f} L {pR.x:.3f},{pR.y:.3f} "
                )

        dash_attr = f' stroke-dasharray="{dash_back}"' if dash_back else ""
        order = ("cranium", "jaw", "cheek", "rhythm", "features", "hair", "side")
        svg: list[str] = ['<svg xmlns="http://www.w3.org/2000/svg">']
        if self.use_zone_colors:
            svg.append('<g title="head" fill="none">')
            for key in order:
                color = ZONE_COLORS[key]
                back = "".join(groups_back[key])
                front = "".join(groups_front[key])
                if back:
                    svg.append(
                        f'<path d="{back}" stroke="{color}" stroke-width="{self.back_line_stroke}" '
                        f'stroke-linecap="round" stroke-linejoin="round"{dash_attr} opacity="0.6"/>'
                    )
                if front:
                    svg.append(
                        f'<path d="{front}" stroke="{color}" stroke-width="{self.front_line_stroke}" '
                        f'stroke-linecap="round" stroke-linejoin="round"/>'
                    )
            if self.show_arrow and arrow_d:
                arrow_color = ZONE_COLORS["arrow"]
                svg.append(f'</g><g fill="none" title="arrow" stroke="{arrow_color}">')
                svg.append(f'<path d="{arrow_d}" stroke-width="{self.front_line_stroke + 1}"/>')
        else:
            back_all = "".join("".join(groups_back[key]) for key in order)
            front_all = "".join("".join(groups_front[key]) for key in order)
            svg.append(f'<g title="head" fill="none" stroke="{self.stroke_color}">')
            if back_all:
                svg.append(
                    f'<path d="{back_all}" stroke-width="{self.back_line_stroke}" '
                    f'stroke-linecap="round" stroke-linejoin="round"{dash_attr} opacity="0.6"/>'
                )
            if front_all:
                svg.append(
                    f'<path d="{front_all}" stroke-width="{self.front_line_stroke}" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>'
                )
            if self.show_arrow and arrow_d:
                svg.append(f'</g><g fill="none" title="arrow" stroke="{self.stroke_color}">')
                svg.append(f'<path d="{arrow_d}" stroke-width="{self.front_line_stroke + 1}"/>')
        svg.append("</g></svg>")
        return "".join(svg)
