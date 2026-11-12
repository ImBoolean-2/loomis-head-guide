# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Prueba de aceptacion offscreen del docker, sin Krita y sin documento.

Monta ``LoomisProportionsDocker`` con PyQt5 real (el que trae Krita 5.x en el
flatpak) y un stub del modulo ``krita``, y comprueba el contrato que se rompe
facil al tocar la UI: las cinco pestanas, el rango del Input Delay (50..5000,
500 por defecto, el mismo intervalo en ``_redraw_timer``), el modelo Loomis con
sus paneles y que ``_visible_position()`` no dependa de un documento abierto.

Sin PyQt5/PyQt6 (host normal) el modulo entero se salta con ``SkipTest``: es
una prueba manual del docker, no parte de la suite pura.

Ejecutar dentro del flatpak de Krita, desde la raiz del repo::

    flatpak run --env=QT_QPA_PLATFORM=offscreen --env=QT_QPA_PLATFORMTHEME= \
        --command=python3 --filesystem=home --filesystem=/tmp org.kde.krita \
        loomis_head/test_ui_offscreen.py

Tambien vale ``cd loomis_head && python3 -m unittest test_ui_offscreen``. El
nombre con paquete (``-m unittest loomis_head.test_ui_offscreen``) no sirve:
``loomis_head/__init__.py`` importa ``krita`` antes de llegar al stub.
"""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# El docker escribe settings/presets/guides bajo QStandardPaths.AppDataLocation:
# se manda a un temporal para no tocar los datos reales del plugin en Krita.
os.environ["XDG_DATA_HOME"] = tempfile.mkdtemp(prefix="loomis-offscreen-")


def _qt_binding():
    """Devuelve el modulo ``QtWidgets`` del binding disponible, o SkipTest."""
    try:  # Krita 5.x
        from PyQt5 import QtWidgets

        return QtWidgets
    except ImportError:
        pass
    try:  # Krita 6.x
        from PyQt6 import QtWidgets

        return QtWidgets
    except ImportError:
        raise unittest.SkipTest(
            "PyQt5/PyQt6 no disponible: ejecutar en el flatpak de Krita"
        )


def _install_krita_stub(qtw):
    """Instala un ``krita`` minimo si no existe (fuera de Krita no lo hay)."""
    try:
        import krita  # noqa: F401

        return
    except ImportError:
        pass

    class DockWidget(qtw.QWidget):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self._widget = None

        def setWidget(self, widget):
            self._widget = widget

        def widget(self):
            return self._widget

    class Extension:
        def __init__(self, parent=None):
            self.parent = parent

    class DockWidgetFactory:
        def __init__(self, *args, **kwargs):
            self.args = args

    class DockWidgetFactoryBase:
        class DockPosition:
            DockRight = 1

    class _Krita:
        @staticmethod
        def instance():
            return types.SimpleNamespace(
                activeDocument=lambda: None,
                addExtension=lambda *args, **kwargs: None,
                addDockWidgetFactory=lambda *args, **kwargs: None,
            )

    module = types.ModuleType("krita")
    module.DockWidget = DockWidget
    module.Extension = Extension
    module.DockWidgetFactory = DockWidgetFactory
    module.DockWidgetFactoryBase = DockWidgetFactoryBase
    module.Krita = _Krita
    sys.modules["krita"] = module


def _load():
    """Importa el docker con el binding Qt real y el stub de ``krita``."""
    qtw = _qt_binding()
    # El stub va antes de importar el paquete: ``loomis_head/__init__.py``
    # importa ``krita`` y registra la extension.
    _install_krita_stub(qtw)
    app = qtw.QApplication.instance() or qtw.QApplication([])
    from loomis_head import loomis_head_plugin, qt_compat

    return qt_compat, app, loomis_head_plugin


class DockerOffscreenTests(unittest.TestCase):
    """Contrato del docker que no necesita documento ni shapes."""

    @classmethod
    def setUpClass(cls):
        cls.qt_compat, cls.app, cls.plugin = _load()

    def setUp(self):
        self.docker = self.plugin.LoomisProportionsDocker()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        docker = self.docker
        try:
            docker.hide()
            docker.deleteLater()
            self.app.processEvents()
        except (AttributeError, RuntimeError):
            pass

    def test_five_tabs(self):
        tabs = self.docker.tabs
        self.assertEqual(tabs.count(), 5)
        texts = [tabs.tabText(index) for index in range(tabs.count())]
        self.assertEqual(
            [text for text in texts if text.strip()],
            texts,
            "alguna pestana quedo sin titulo",
        )
        self.assertEqual(
            texts,
            [
                self.plugin.t("tabs.settings"),
                self.plugin.t("tabs.transform"),
                self.plugin.t("tabs.guides"),
                self.plugin.t("tabs.features"),
                self.plugin.t("tabs.hair"),
            ],
        )

    def test_delay_range_and_timer(self):
        spin = self.docker.delaySpin
        self.assertEqual(spin.minimum(), self.plugin.DELAY_MIN_MS)
        self.assertEqual(spin.maximum(), self.plugin.DELAY_MAX_MS)
        self.assertEqual(self.plugin.DELAY_MIN_MS, 50)
        self.assertEqual(self.plugin.DELAY_MAX_MS, 5000)
        self.assertEqual(spin.singleStep(), 50)
        self.assertEqual(spin.value(), self.plugin.REDRAW_INTERVAL_MS)
        self.assertEqual(spin.value(), 500)
        timer = self.docker._redraw_timer
        self.assertTrue(timer.isSingleShot())
        self.assertEqual(timer.interval(), spin.value())
        # Sin flush al soltar el slider: mover el spin cambia el timer en vivo.
        spin.setValue(1500)
        self.assertEqual(timer.interval(), 1500)
        spin.setValue(self.plugin.REDRAW_INTERVAL_MS)

    def test_loomis_model_and_panels(self):
        docker = self.docker
        self.assertIsNotNone(docker.loomis_head)
        self.assertEqual(docker._current_model_id(), "loomis")
        self.assertIsInstance(docker.feature_panel, self.plugin.FeaturePanel)
        self.assertIsInstance(docker.asaro_panel, self.plugin.AsaroPanel)
        self.assertIsNotNone(docker.hair_panel)
        # El combo de modelo ofrece Loomis y Asaro.
        combo = docker.model_combo
        ids = [combo.itemData(index) for index in range(combo.count())]
        self.assertIn("loomis", ids)
        self.assertIn("asaro", ids)

    def test_asaro_model_id(self):
        self.assertIn("asaro", self.plugin.supported_models())
        model = self.plugin.create_model("asaro")
        self.assertIsNotNone(model)
        self.assertEqual(model.to_dict().get("model"), "asaro")
        # El panel de Asaro se puede rebindear al modelo sin documento.
        self.docker.asaro_panel.set_model(model)
        self.assertIs(self.docker.asaro_panel.model, model)

    def test_visible_position_without_document(self):
        docker = self.docker
        self.assertIsNone(docker.doc)
        self.assertIsNone(docker.loomis_layer)
        visible = docker._visible_position()
        self.assertEqual(len(visible), 2)
        for value in visible:
            self.assertIsInstance(float(value), float)
        # Sin transformacion manual, el X/Y visible es el pivote del modelo.
        self.assertAlmostEqual(visible[0], docker.loomis_head.position_x)
        self.assertAlmostEqual(visible[1], docker.loomis_head.position_y)
        # El sondeo (120 ms) no puede romper con la capa o el documento a None.
        docker.sync_manual_position()
        self.assertEqual(len(docker._visible_position()), 2)

    def test_force_layer_rerender_resets_antialias_and_projection(self):
        """Invalida la cache de la capa (toggle de antialias) y la proyeccion.

        Krita solo reinvalida el rectangulo que le avisa cada shape; al
        reconstruir el SVG entero en la misma pasada la cabeza puede quedar
        cortada hasta reabrir el documento. El remedio es limpiar la cache de
        la capa y refrescar la proyeccion, sin dejar el antialias cambiado.
        """
        docker = self.docker
        calls = []

        class FakeLayer:
            def isAntialiased(self):
                return True

            def setAntialiased(self, value):
                calls.append(value)

        class FakeDoc:
            def __init__(self):
                self.refreshed = 0

            def refreshProjection(self):
                self.refreshed += 1

        layer = FakeLayer()
        doc = FakeDoc()
        docker.loomis_layer = layer
        docker.doc = doc
        try:
            summary = docker._force_layer_rerender()
        finally:
            docker.loomis_layer = None
            docker.doc = None
        # Cambia el valor y lo deja como estaba: el final es el original.
        self.assertEqual(calls, [False, True])
        self.assertTrue(calls[-1])
        self.assertEqual(doc.refreshed, 1)
        self.assertIsInstance(summary, str)
        self.assertIn("aa=1", summary)
        self.assertIn("refresh=1", summary)

    def test_force_layer_rerender_tolera_capa_sin_api(self):
        """Sin antialias ni refreshProjection no lanza: devuelve el resumen."""
        docker = self.docker

        class FakeLayer:
            def isAntialiased(self):
                raise AttributeError("capa sin antialias")

        docker.loomis_layer = FakeLayer()
        # Sin ``refreshProjection``: el documento real siempre la tiene, pero
        # un wrapper muerto o un stub no pueden romper el dibujo.
        docker.doc = types.SimpleNamespace()
        try:
            summary = docker._force_layer_rerender()
        finally:
            docker.loomis_layer = None
            docker.doc = None
        self.assertIsInstance(summary, str)
        self.assertIn("aa=0", summary)
        self.assertIn("refresh=0", summary)

    def _seed_grimorio(self, head):
        """Crea el grimorio.json del sandbox (XDG_DATA_HOME temporal)."""
        path = self.docker._grimorio_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 2,
            "characters": [{"id": "kai-marquez", "name": "Kai", "head": head}],
            "activeCharacterId": "kai-marquez",
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        backup = path.with_name(path.name + ".loomis.bak")
        self.addCleanup(backup.with_name(backup.name + ".tmp").unlink, missing_ok=True)
        self.addCleanup(path.with_name(path.name + ".loomis.tmp").unlink, missing_ok=True)
        self.addCleanup(backup.unlink, missing_ok=True)
        self.addCleanup(path.unlink, missing_ok=True)
        return path, backup

    def test_write_head_preserva_modo_del_json(self):
        """Escribir el head no rebaja el 0600 que pone el Grimorio.

        El JSON tiene ``privateMode``: el Grimorio lo crea con ``mkstemp``. Al
        pasar por un temporal nuevo, Loomis no debe dejarlo en 0644 ni el backup.
        """
        path, backup = self._seed_grimorio({})
        os.chmod(path, 0o600)
        wrote = self.docker._write_head_to_grimorio(
            "kai-marquez", {"model": "loomis", "scale": 1.0}
        )
        self.assertTrue(wrote)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)

    def test_write_head_conserva_claves_desconocidas(self):
        """El head es compartido y opaco: lo que Loomis no conoce no se tira."""
        path, _backup = self._seed_grimorio(
            {"lightAzimuth": 0.3, "futureKey": {"nested": [1, 2]}, "scale": 9.0}
        )
        wrote = self.docker._write_head_to_grimorio(
            "kai-marquez", {"model": "loomis", "scale": 1.0}
        )
        self.assertTrue(wrote)
        head = json.loads(path.read_text(encoding="utf-8"))["characters"][0]["head"]
        self.assertEqual(head["lightAzimuth"], 0.3)
        self.assertEqual(head["futureKey"], {"nested": [1, 2]})
        self.assertEqual(head["scale"], 1.0)
        self.assertEqual(head["model"], "loomis")


if __name__ == "__main__":
    unittest.main(verbosity=2)
