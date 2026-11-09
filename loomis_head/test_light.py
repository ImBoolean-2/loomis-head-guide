# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Pruebas del modulo de luz (sin Krita).

Ejecutar desde esta carpeta:
    python3 test_light.py
    python3 -m unittest test_light.py -v
"""
import math
import re
import sys
import types
import unittest
from pathlib import Path

# El paquete real importa krita en __init__.py; aqui solo probamos el generador.
_pkg = types.ModuleType("loomis_head")
_pkg.__path__ = [str(Path(__file__).resolve().parent)]
sys.modules.setdefault("loomis_head", _pkg)

from loomis_head.linalg import q_axis_angle, q_identity  # noqa: E402
from loomis_head.light import SHADOW_FILL, shadow_svg  # noqa: E402
from loomis_head.euclid import Vector3  # noqa: E402
from loomis_head.geom_polyline import clip_to_side_band  # noqa: E402
from loomis_head.loomis_head_generator import LoomisHead3D  # noqa: E402

_PAIR = re.compile(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")


class _BareModel:
    """Modelo minimo: solo lo que el contrato exige (sin setters ni _to_screen)."""

    show_shadow = True
    q = q_identity()


class LightTests(unittest.TestCase):
    def _head(self) -> LoomisHead3D:
        head = LoomisHead3D()
        head.set_show_shadow(True)
        return head

    def test_no_shadow_returns_empty(self):
        head = LoomisHead3D()
        head.set_show_shadow(False)
        self.assertEqual(shadow_svg(head, 1000, 800), "")

    def test_shadow_returns_path_with_fill(self):
        head = self._head()
        svg = shadow_svg(head, 1000, 800)
        self.assertIn("<path", svg)
        self.assertIn('fill="', svg)
        self.assertIn(SHADOW_FILL, svg)
        self.assertIn("opacity=", svg)
        self.assertRegex(svg, r'd="M ')

    def test_intensity_zero_returns_empty(self):
        head = self._head()
        head.set_light_intensity(0.0)
        self.assertEqual(shadow_svg(head, 800, 800), "")

    def test_invalid_canvas_returns_empty(self):
        head = self._head()
        self.assertEqual(shadow_svg(head, 0, 800), "")
        self.assertEqual(shadow_svg(head, float("nan"), 800), "")

    def test_no_nan_or_inf(self):
        head = self._head()
        cases = [
            (-35.0, 35.0, 0),
            (0.0, 0.0, 0),
            (0.0, 0.0, 1),
            (90.0, -40.0, 0),
            (-180.0, 90.0, 1),
            (180.0, -90.0, 0),
            (135.0, 60.0, 1),
            (-90.0, 0.0, 0),
        ]
        for azimuth, elevation, mode in cases:
            head.set_light_azimuth(azimuth)
            head.set_light_elevation(elevation)
            head.set_shadow_mode(mode)
            for quaternion in (
                q_identity(),
                q_axis_angle([0, 1, 0], 1.2),
                q_axis_angle([1, 0, 0], -0.7),
            ):
                head.set_quaternion(quaternion)
                svg = shadow_svg(head, 800, 800)
                self.assertNotIn("nan", svg.lower())
                self.assertNotIn("inf", svg.lower())

    def test_shadow_inside_silhouette(self):
        head = self._head()
        width = height = 800
        for azimuth in (-135.0, -35.0, 0.0, 35.0, 135.0, 180.0):
            head.set_light_azimuth(azimuth)
            head.set_light_elevation(25.0)
            svg = shadow_svg(head, width, height)
            scale = min(width, height) * 0.3 * head.scale
            limit = head.radius * head.cranium * scale + 0.5
            for raw_x, raw_y in _PAIR.findall(svg):
                x = float(raw_x)
                y = float(raw_y)
                self.assertLessEqual(math.hypot(x, y), limit, msg=f"az={azimuth}")

    def test_terminator_and_cel(self):
        head = self._head()
        head.set_shadow_mode(0)
        terminator = shadow_svg(head, 800, 800)
        head.set_shadow_mode(1)
        cel = shadow_svg(head, 800, 800)
        self.assertEqual(terminator.count("<path"), 1)
        self.assertEqual(cel.count("<path"), 2)
        self.assertGreater(len(cel), len(terminator))

    def test_front_light_has_no_visible_shadow(self):
        head = self._head()
        head.set_light_azimuth(0.0)
        head.set_light_elevation(0.0)
        self.assertEqual(shadow_svg(head, 800, 800), "")

    def test_backlight_covers_visible_disk(self):
        head = self._head()
        head.set_light_azimuth(180.0)
        head.set_light_elevation(0.0)
        svg = shadow_svg(head, 800, 800)
        self.assertIn("<path", svg)
        self.assertIn("fill-rule=\"evenodd\"", svg)
        self.assertGreaterEqual(len(_PAIR.findall(svg)), 32)

    def test_invalid_geometry_returns_empty(self):
        bare = _BareModel()
        bare.radius = 0.0
        self.assertEqual(shadow_svg(bare, 800, 800), "")

    def test_build_svg_hook_adds_shadow(self):
        import xml.etree.ElementTree as ET

        head = LoomisHead3D()
        head.set_position_x(400)
        head.set_position_y(400)
        plain = head.build_svg(800, 800)
        self.assertNotIn(SHADOW_FILL, plain)
        head.set_show_shadow(True)
        shaded = head.build_svg(800, 800)
        self.assertIn(SHADOW_FILL, shaded)
        self.assertGreater(len(shaded), len(plain))
        ET.fromstring(shaded)  # SVG bien formado

    def test_bare_model_uses_defaults(self):
        svg = shadow_svg(_BareModel(), 640, 480)
        self.assertIn("<path", svg)
        self.assertNotIn("nan", svg.lower())

    def test_light_fields_roundtrip(self):
        head = LoomisHead3D()
        if not hasattr(head, "light_azimuth"):
            self.skipTest("el modelo aun no expone campos de luz")
        head.set_light_azimuth(120.0)
        head.set_light_elevation(-40.0)
        head.set_light_intensity(0.8)
        head.set_show_shadow(True)
        head.set_shadow_mode(1)

        payload = head.to_dict()
        self.assertEqual(payload["lightAzimuth"], 120.0)
        self.assertEqual(payload["lightElevation"], -40.0)
        self.assertAlmostEqual(payload["lightIntensity"], 0.8)
        self.assertTrue(payload["showShadow"])
        self.assertEqual(payload["shadowMode"], 1)

        clone = LoomisHead3D()
        clone.from_dict(payload)
        self.assertAlmostEqual(clone.light_azimuth, 120.0)
        self.assertAlmostEqual(clone.light_elevation, -40.0)
        self.assertAlmostEqual(clone.light_intensity, 0.8)
        self.assertTrue(clone.show_shadow)
        self.assertEqual(clone.shadow_mode, 1)
        self.assertEqual(shadow_svg(head, 900, 700), shadow_svg(clone, 900, 700))

    def test_legacy_dict_keeps_shadow_off(self):
        head = LoomisHead3D()
        head.from_dict({"version": 1, "model": "loomis", "radius": 1.0})
        self.assertFalse(head.show_shadow)
        self.assertEqual(shadow_svg(head, 800, 800), "")

    # -- Craneo eliptico (cranium_width/cranium_height) ---------------------

    def _elliptical(self, width: float = 1.2, height: float = 0.8) -> LoomisHead3D:
        head = LoomisHead3D()
        head.set_show_shadow(True)
        head.set_cranium_width(width)
        head.set_cranium_height(height)
        head.set_quaternion(q_axis_angle([0.3, 1.0, 0.2], 0.9))
        return head

    def _head_center(self, head, width: float, height: float) -> tuple[float, float]:
        origin = head._to_screen(head._to_camera([Vector3(0.0, 0.0, 0.0)]), width, height)[0]
        return float(origin.x), float(origin.y)

    def _silhouette_radius(self, head, width: float, height: float) -> float:
        """Radio maximo (documento) del contorno del craneo tal como se dibuja."""
        rc = head.radius * head.cranium
        n_sil_head = head.q.conjugated() * Vector3(0.0, 0.0, 1.0)
        circle = head._circle_on_plane(n_sil_head, [0.0, 0.0, 0.0], rc, 256)
        screen = head._to_screen(head._to_camera(circle), width, height)
        cx, cy = self._head_center(head, width, height)
        return max(math.hypot(float(p.x) - cx, float(p.y) - cy) for p in screen)

    def _shadow_radii(self, head, svg: str, width: float, height: float) -> list[float]:
        cx, cy = self._head_center(head, width, height)
        return [
            math.hypot(float(raw_x) - cx, float(raw_y) - cy)
            for raw_x, raw_y in _PAIR.findall(svg)
        ]

    def test_elliptical_cranium_has_no_nan(self):
        head = self._elliptical()
        for mode in (0, 1):
            head.set_shadow_mode(mode)
            svg = shadow_svg(head, 900, 700)
            self.assertIn("<path", svg, msg=f"modo {mode}")
            self.assertRegex(svg, r'd="M ')
            self.assertNotIn("nan", svg.lower())
            self.assertNotIn("inf", svg.lower())
            radii = self._shadow_radii(head, svg, 900, 700)
            self.assertGreater(len(radii), 8)
            self.assertTrue(all(math.isfinite(r) for r in radii))

    def test_elliptical_shadow_fits_drawn_cranium(self):
        width = height = 800
        for quaternion in (
            q_axis_angle([0.3, 1.0, 0.2], 0.9),
            q_axis_angle([0, 1, 0], 1.2),
            q_axis_angle([1, 0, 0], -0.7),
        ):
            head = self._elliptical()
            head.set_quaternion(quaternion)
            for azimuth in (-135.0, -35.0, 0.0, 60.0, 180.0):
                head.set_light_azimuth(azimuth)
                head.set_light_elevation(30.0)
                svg = shadow_svg(head, width, height)
                radii = self._shadow_radii(head, svg, width, height)
                self.assertTrue(radii, msg=f"az={azimuth}")
                # El contorno dibujado es un circulo proyectado, no la silueta
                # exacta de la elipse: 1% + 1 px cubre esa aproximacion.
                limit = self._silhouette_radius(head, width, height) * 1.01 + 1.0
                self.assertLessEqual(max(radii), limit, msg=f"az={azimuth}")

    def test_elliptical_backlight_reaches_drawn_cranium(self):
        """Luz de frente opuesta: la sombra cubre el craneo dibujado (misma proyeccion)."""
        head = self._elliptical()
        head.set_light_azimuth(180.0)
        head.set_light_elevation(0.0)
        width = height = 800
        svg = shadow_svg(head, width, height)
        radii = self._shadow_radii(head, svg, width, height)
        silhouette = self._silhouette_radius(head, width, height)
        self.assertTrue(radii)
        self.assertAlmostEqual(max(radii), silhouette, delta=1.0)

    def test_elliptical_shadow_uses_cranium_scale(self):
        """El ancho del craneo debe ensanchar la sombra (misma proyeccion)."""
        width = height = 800

        def shadow_width(cranium_width: float) -> float:
            head = LoomisHead3D()
            head.set_show_shadow(True)
            head.set_light_azimuth(-35.0)
            head.set_light_elevation(25.0)
            head.set_cranium_width(cranium_width)
            svg = shadow_svg(head, width, height)
            xs = [float(raw_x) for raw_x, _ in _PAIR.findall(svg)]
            self.assertTrue(xs)
            return max(xs) - min(xs)

        narrow = shadow_width(0.8)
        wide = shadow_width(1.2)
        self.assertGreater(wide, narrow * 1.2)

    def test_elliptical_show_shadow_false_is_empty(self):
        head = self._elliptical()
        head.set_show_shadow(False)
        self.assertEqual(shadow_svg(head, 800, 800), "")

    def test_elliptical_cel_has_two_paths(self):
        head = self._elliptical()
        head.set_shadow_mode(0)
        terminator = shadow_svg(head, 800, 800)
        head.set_shadow_mode(1)
        cel = shadow_svg(head, 800, 800)
        self.assertEqual(terminator.count("<path"), 1)
        self.assertEqual(cel.count("<path"), 2)
        self.assertNotIn("nan", cel.lower())

    # -- Recorte lateral (side_cut) -----------------------------------------

    def _drawn_max_abs_x(self, head, width: float, height: float) -> float:
        """Max |x - centro| del contorno del craneo tal como lo dibuja el generador.

        El generador recorta cada curva con ``clip_to_side_band`` al slab
        ``|x_head| <= d``; se replica aqui para medir el borde real dibujado.
        """
        rc = head.radius * head.cranium
        d = max(0.05, min(0.9, head.side_cut)) * rc
        n_sil_head = head.q.conjugated() * Vector3(0.0, 0.0, 1.0)
        circle = head._circle_on_plane(n_sil_head, [0.0, 0.0, 0.0], rc, 512)
        cx, cy = self._head_center(head, width, height)
        best = 0.0
        for segment in clip_to_side_band(circle, d):
            for point in head._to_screen(head._to_camera(segment), width, height):
                best = max(best, abs(float(point.x) - cx))
        return best

    def _shadow_max_abs_x(self, head, svg: str, width: float, height: float) -> float:
        cx, cy = self._head_center(head, width, height)
        xs = [abs(float(raw_x) - cx) for raw_x, _ in _PAIR.findall(svg)]
        self.assertTrue(xs, "el SVG no contiene puntos de path")
        return max(xs)

    def test_shadow_respects_side_cut(self):
        """La sombra no puede salir de la banda lateral del craneo dibujado."""
        width = height = 800
        for side_cut in (0.66, 0.05, 0.9):
            for mode in (0, 1):
                head = LoomisHead3D()
                head.set_show_shadow(True)
                head.set_sidecut(side_cut)
                head.set_shadow_mode(mode)
                head.set_light_azimuth(-35.0)
                head.set_light_elevation(35.0)
                svg = shadow_svg(head, width, height)
                self.assertIn("<path", svg, msg=f"side_cut={side_cut} mode={mode}")
                drawn = self._drawn_max_abs_x(head, width, height)
                shadow = self._shadow_max_abs_x(head, svg, width, height)
                limit = drawn * 1.005 + 1.0
                self.assertLessEqual(
                    shadow,
                    limit,
                    msg=f"side_cut={side_cut} mode={mode}: {shadow:.2f} > {limit:.2f}",
                )

    def test_side_cut_show_shadow_false_is_empty(self):
        for side_cut in (0.05, 0.66, 0.9):
            head = LoomisHead3D()
            head.set_sidecut(side_cut)
            head.set_show_shadow(False)
            self.assertEqual(shadow_svg(head, 800, 800), "", msg=f"side_cut={side_cut}")

    def test_side_cut_cel_keeps_two_paths(self):
        for side_cut in (0.05, 0.66, 0.9):
            head = LoomisHead3D()
            head.set_show_shadow(True)
            head.set_sidecut(side_cut)
            head.set_shadow_mode(0)
            terminator = shadow_svg(head, 800, 800)
            head.set_shadow_mode(1)
            cel = shadow_svg(head, 800, 800)
            self.assertEqual(terminator.count("<path"), 1, msg=f"side_cut={side_cut}")
            self.assertEqual(cel.count("<path"), 2, msg=f"side_cut={side_cut}")

    def test_side_cut_no_nan_or_inf(self):
        for side_cut in (0.05, 0.66, 0.9):
            head = LoomisHead3D()
            head.set_show_shadow(True)
            head.set_sidecut(side_cut)
            for mode in (0, 1):
                head.set_shadow_mode(mode)
                for azimuth in (-180.0, -35.0, 0.0, 90.0, 180.0):
                    head.set_light_azimuth(azimuth)
                    for quaternion in (
                        q_identity(),
                        q_axis_angle([0, 1, 0], 1.2),
                        q_axis_angle([1, 0, 0], -0.7),
                    ):
                        head.set_quaternion(quaternion)
                        svg = shadow_svg(head, 800, 800)
                        self.assertNotIn("nan", svg.lower())
                        self.assertNotIn("inf", svg.lower())
                        for raw_x, raw_y in _PAIR.findall(svg):
                            self.assertTrue(math.isfinite(float(raw_x)))
                            self.assertTrue(math.isfinite(float(raw_y)))

    def test_side_cut_clips_backlight_disk(self):
        """Luz de espaldas: el disco de sombra tambien queda dentro de la banda."""
        width = height = 800
        for side_cut in (0.05, 0.66, 0.9):
            head = LoomisHead3D()
            head.set_show_shadow(True)
            head.set_sidecut(side_cut)
            head.set_light_azimuth(180.0)
            head.set_light_elevation(0.0)
            svg = shadow_svg(head, width, height)
            drawn = self._drawn_max_abs_x(head, width, height)
            shadow = self._shadow_max_abs_x(head, svg, width, height)
            self.assertLessEqual(shadow, drawn * 1.005 + 1.0, msg=f"side_cut={side_cut}")


if __name__ == "__main__":
    unittest.main()
