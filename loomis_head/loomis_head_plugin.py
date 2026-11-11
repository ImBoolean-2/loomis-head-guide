# SPDX-FileCopyrightText: 2025 lm0ss
# SPDX-FileCopyrightText: 2026 Nedeljko Umjetnik
# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

import copy
import json
import math
import os
from pathlib import Path

from krita import DockWidget, DockWidgetFactory, DockWidgetFactoryBase, Extension, Krita
from .qt_compat import (
    EXPANDING,
    QColor,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSignalBlocker,
    QSlider,
    QStackedWidget,
    QStandardPaths,
    QTabWidget,
    QTimer,
    QVBoxLayout,
    QWidget,
    Qt,
    activated_index,
    activated_text,
    exec_dialog,
    uic,
)
from . import qt_compat

# ``QPointF`` no se reexporta en qt_compat; se toma del mismo binding para no
# importar PyQt5/PyQt6 aqui. Si no estuviera, se mapea por traslacion.
try:
    QPointF = qt_compat.QtCore.QPointF
except AttributeError:  # pragma: no cover - bindings sin QtCore expuesto
    QPointF = None

# ``QSpinBox`` tampoco se reexporta en qt_compat; mismo binding, mismo motivo.
QSpinBox = qt_compat.QtWidgets.QSpinBox

from . import i18n
from .features_dialog import AsaroPanel, FeaturePanel, HairPanel
from .preview import HeadPreviewWidget
from .i18n import t
from .models import DEFAULT_MODEL, create_model, supported_models
from .linalg import (
    angles_from_quaternion,
    q_axis_angle,
    q_identity,
    q_mul,
    quaternion_from_angles,
)
from .loomis_head_generator import LoomisHead3D

# Nombre del marcador invisible que fija el pivote en el documento. El id del
# SVG se conserva como nombre de shape en Krita; si el binding no lo hiciera,
# el marcador se reconoce por la referencia que devuelve addShapesFromSvg (es
# el ultimo elemento del SVG y una caja de 1 px).
PIVOT_SHAPE_NAME = "loomis-pivot"
# Debounce del canvas: solo se redibuja al parar (500 ms sin cambios). La
# preview del docker sigue en vivo en cada ``valueChanged``.
REDRAW_INTERVAL_MS = 500
# Rango del "Input Delay" del docker (ms). 0 = redibujo inmediato al soltar;
# el valor se guarda en settings.json como ``redrawDelay``.
DELAY_MIN_MS = 0
DELAY_MAX_MS = 5000
DELAY_STEP_MS = 50


def _clamp_delay(value) -> int:
    """Entero de ms dentro del rango del spinbox; el default si no es valido."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return REDRAW_INTERVAL_MS
    return max(DELAY_MIN_MS, min(DELAY_MAX_MS, number))


def _map_shape_point(shape, x: float, y: float):
    """Punto ``(x, y)`` del shape en coordenadas del documento.

    Usa ``absoluteTransformation()`` (o ``transformation()`` si el binding no
    la expone) para que el marcador se lea donde el usuario lo dejo aunque la
    capa se haya movido con Move/Transform.
    """
    try:
        transform = shape.absoluteTransformation()
    except AttributeError:
        transform = shape.transformation()
    if QPointF is not None:
        point = transform.map(QPointF(x, y))
        return (float(point.x()), float(point.y()))
    return (x + transform.dx(), y + transform.dy())


def _shape_document_center(shape):
    """Centro de la caja del shape en coordenadas del documento."""
    try:
        box = shape.boundingBox()
        if box is None or box.isNull():
            return None
        center = _map_shape_point(
            shape, box.x() + box.width() / 2.0, box.y() + box.height() / 2.0
        )
    except (AttributeError, RuntimeError, TypeError):
        return None
    return center


def _find_pivot_shape(layer):
    """Shape del marcador de pivote en la capa, por nombre, o ``None``.

    Al cargar un documento no se adivina por tamano: una capa de una version
    anterior puede tener trazos diminutos (escala muy baja) que no son el
    pivote. Sin nombre reconocible se devuelve ``None`` y se espera al primer
    dibujo, que recrea el marcador.
    """
    try:
        shapes = list(layer.shapes())
    except (AttributeError, RuntimeError, TypeError):
        return None
    for shape in shapes:
        try:
            name = str(shape.name() or "").lower()
        except (AttributeError, RuntimeError, TypeError):
            continue
        if PIVOT_SHAPE_NAME in name:
            return shape
    return None


def _is_pivot_shape(shape) -> bool:
    """True si el shape parece el marcador: nombre ``loomis-pivot`` o 1 px."""
    try:
        if PIVOT_SHAPE_NAME in str(shape.name() or "").lower():
            return True
        box = shape.boundingBox()
    except (AttributeError, RuntimeError, TypeError):
        return False
    return box is not None and box.width() <= 3 and box.height() <= 3


def _pivot_position(layer, shape=None):
    """Pivote en el documento leido del marcador, o ``None`` si no hay.

    ``shape`` es la referencia que devolvio ``addShapesFromSvg`` al dibujar
    (evita depender del nombre que Krita ponga al shape); si falta o ya no es
    valida se busca el marcador en la capa.
    """
    if layer is None:
        return None
    if shape is not None and _is_pivot_shape(shape):
        point = _shape_document_center(shape)
        if point is not None:
            return point
    found = _find_pivot_shape(layer)
    if found is None:
        return None
    return _shape_document_center(found)


class Guide:
    """Una cabeza independiente: modelo + capa vectorial + nombre."""

    __slots__ = ("model", "layer", "name", "last_center", "model_states", "pivot_shape")

    def __init__(self, model, layer, name):
        self.model = model
        self.layer = layer
        self.name = name
        self.last_center = None
        # Shape del marcador de pivote que devolvio addShapesFromSvg en el
        # ultimo dibujo de esta guia (None hasta el primer dibujo).
        self.pivot_shape = None
        # Estado completo por modelo (``to_dict``), para que cambiar de Loomis
        # a Asaro y volver no pierda los campos propios de cada uno.
        self.model_states = {}


class LoomisProportionsDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self._log_init("init:start")
        try:
            self._build()
        except Exception:
            import traceback
            self._log_init(traceback.format_exc())
            raise

    def _build(self):
        self._settings = self._load_settings()
        i18n.set_language(self._settings.get("language") or None)
        self.doc = None
        self.loomis_head = create_model(DEFAULT_MODEL) or LoomisHead3D()
        self.loomis_layer = None
        self.guides = []
        self.active_index = 0
        self._doc_key = None
        self._guides_path = self._guides_state_path()
        self._state = self._load_guides_state()
        self.update_scheduled = False
        self._last_layer_bounds_center = None
        # Ultima posicion absoluta del marcador de pivote: la referencia para
        # medir el desplazamiento manual del lienzo (1:1, sin bounds).
        self._last_pivot_position = None
        # Shape del marcador devuelto por addShapesFromSvg (se rehace en cada
        # dibujo; None equivale a "buscarlo por nombre o por caja").
        self._pivot_shape = None
        self._drawing = False
        self._pending_position = None
        self._presets = {"version": 1, "presets": {}, "characters": {}}
        self._presets_path = self._preset_path()
        self.feature_panel = None
        self.hair_panel = None
        self.asaro_panel = None
        self.feature_stack = None
        self.model_combo = None
        self.model_label = None
        self._slider_sync = False
        self._characters = []
        self._heads = {}
        self._active_character = ""

        # Estado por modelo cuando no hay guia activa (misma idea que
        # ``Guide.model_states``).
        self._model_stash = {}

        self.setWindowTitle("Loomis Method Head Guide")
        self.setMinimumSize(320, 420)
        self.connect_ui()
        self._load_presets()
        self._bind_library()
        self._refresh_presets()
        self._load_characters()
        self._refresh_oc_combo()
        self.feature_panel = FeaturePanel(self.loomis_head, self.schedule_update, self)
        self.hair_panel = HairPanel(self.loomis_head, self.schedule_update, self)
        self.asaro_panel = AsaroPanel(self.loomis_head, self.schedule_update, self)
        self.transform_group = self._build_transform_panel()
        self.language_group = self._build_language_panel()
        self._build_dashboard()
        self._set_model_ui(self._current_model_id())
        self.ui.featuresButton.hide()
        self._log_init("init:ok")

        # Krita does not expose a dependable cross-tool signal for every vector
        # shape move/transform, so poll the pivot marker (docs: 1:1, no bounds).
        self.position_sync_timer = QTimer(self)
        self.position_sync_timer.setInterval(120)
        self.position_sync_timer.timeout.connect(self.sync_manual_position)
        self.position_sync_timer.start()

        # El canvas solo se redibuja al parar: Input Delay (500 ms por defecto).
        # Krita 5.3.4 no expone beginUndo/endUndo (ni KUndo2Command) a Python,
        # asi que cada addShapesFromSvg deja su propia entrada de undo; espaciar
        # los redibujos es la unica mitigacion desde el plugin. La preview del
        # docker (trackball) se repinta en vivo en cada cambio.
        self._redraw_timer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(
            _clamp_delay(self._settings.get("redrawDelay", REDRAW_INTERVAL_MS))
        )
        self._redraw_timer.timeout.connect(self.draw_lines_with_vectors)

        self._state_timer = QTimer(self)
        self._state_timer.setSingleShot(True)
        self._state_timer.setInterval(800)
        self._state_timer.timeout.connect(self._save_doc_state)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_characters()
        self._refresh_oc_combo()
        self.ensure_guide()
        self.position_sync_timer.start()
        self.activateWindow()
        self.raise_()

    def hideEvent(self, event):
        self._save_doc_state()
        self.position_sync_timer.stop()
        super().hideEvent(event)

    def _log_init(self, text: str) -> None:
        try:
            base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            path = Path(base or ".") / "loomis_head" / "init.log"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError:
            pass

    def _guides_state_path(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        root = Path(base) if base else Path.home() / ".local" / "share" / "krita"
        return root / "loomis_head" / "guides.json"

    def _load_guides_state(self) -> dict:
        try:
            raw = json.loads(self._guides_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "documents": {}}
        if not isinstance(raw, dict):
            return {"version": 1, "documents": {}}
        if not isinstance(raw.get("documents"), dict):
            raw["documents"] = {}
        raw.setdefault("version", 1)
        return raw

    def _save_guides_state(self) -> None:
        try:
            self._guides_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self._guides_path.with_name(self._guides_path.name + ".tmp")
            temp.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self._guides_path)
        except OSError:
            pass

    def _node_alive(self, layer) -> bool:
        if layer is None:
            return False
        try:
            if layer.parentNode() is not None:
                return True
        except (AttributeError, RuntimeError, TypeError):
            pass
        try:
            return bool(self.doc and self.doc.nodeByName(layer.name()) is not None)
        except (AttributeError, RuntimeError, TypeError):
            return False

    def _find_guide_layers(self, doc) -> list:
        found = []

        def walk(node) -> None:
            try:
                children = node.childNodes()
            except (AttributeError, RuntimeError, TypeError):
                return
            for child in children:
                try:
                    name = str(child.name())
                except (AttributeError, RuntimeError, TypeError):
                    continue
                if name.startswith("Loomis"):
                    found.append(child)
                else:
                    walk(child)

        root = doc.rootNode()
        if root is not None:
            walk(root)
        return found

    def _next_guide_name(self, used) -> str:
        n = 1
        while f"Loomis Head {n}" in used:
            n += 1
        return f"Loomis Head {n}"

    def _center_from_layer(self, layer):
        try:
            bounds = layer.bounds()
            if bounds is None or bounds.isNull() or bounds.isEmpty():
                return None
            return (bounds.x() + bounds.width() / 2.0, bounds.y() + bounds.height() / 2.0)
        except (AttributeError, RuntimeError, TypeError):
            return None

    def _apply_state_position(self, model, doc, state: dict) -> None:
        """Posicion normalizada del estado -> posicion del pivote en pixeles."""
        if state.get("positionUnit") != "normalized":
            return
        try:
            width, height = doc.width(), doc.height()
            if width and height:
                model.set_position_x(float(state.get("positionX", 0.5)) * width)
                model.set_position_y(float(state.get("positionY", 0.5)) * height)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def _sync_document(self, doc) -> None:
        key = doc.fileName() or f"unsaved:{id(doc)}"
        if doc is self.doc and key == self._doc_key:
            return
        self._save_doc_state()
        self.doc = doc
        self._doc_key = key
        self._refresh_transform_ranges()
        self.guides = []
        self.active_index = 0
        saved = {}
        documents = self._state.get("documents")
        if isinstance(documents, dict):
            entry = documents.get(key)
            if isinstance(entry, dict):
                saved = entry
        self._load_guides(doc, saved)
        self._refresh_guide_combo()
        if self.guides:
            active = saved.get("active", 0) if isinstance(saved, dict) else 0
            try:
                active = int(active)
            except (TypeError, ValueError):
                active = 0
            self._set_active_guide(max(0, min(active, len(self.guides) - 1)))
        else:
            model, model_id = self._fresh_model()
            self.loomis_head = model
            self.loomis_layer = None
            self.active_index = 0
            self.trackball.set_model(self.loomis_head)
            self.trackball.set_quaternion(self.loomis_head.q)
            self._sync_euler_from_model()
            self._sync_panels_for_model(model_id)
        self._save_doc_state()

    def _load_guides(self, doc, saved: dict) -> None:
        layers = self._find_guide_layers(doc)
        states = {}
        centers = {}
        model_states = {}
        if isinstance(saved, dict):
            for item in saved.get("guides", []):
                if isinstance(item, dict) and item.get("name"):
                    name = str(item["name"])
                    states[name] = item.get("state")
                    centers[name] = item.get("center")
                    # Estados de los modelos inactivos (el activo esta en
                    # ``state``); si falta o no es dict, la guia arranca vacia.
                    extra = item.get("models")
                    model_states[name] = extra if isinstance(extra, dict) else {}

        legacy = []
        for layer in layers:
            try:
                if str(layer.name()) == "Loomis Method Head Guide":
                    legacy.append(layer)
            except (AttributeError, RuntimeError, TypeError):
                pass
        if states:
            for layer in list(legacy):
                try:
                    name = str(layer.name())
                except (AttributeError, RuntimeError, TypeError):
                    continue
                if name in states:
                    continue
                try:
                    parent = layer.parentNode()
                    if parent is not None:
                        parent.removeChildNode(layer)
                    else:
                        root = doc.rootNode()
                        if root is not None:
                            root.removeChildNode(layer)
                except (AttributeError, RuntimeError, TypeError):
                    pass
                try:
                    layers.remove(layer)
                except ValueError:
                    pass
        if len(layers) > 1 and not states and len(legacy) == len(layers):
            keep = legacy[-1]
            for layer in layers:
                if layer is keep:
                    continue
                try:
                    parent = layer.parentNode()
                    if parent is not None:
                        parent.removeChildNode(layer)
                    else:
                        root = doc.rootNode()
                        if root is not None:
                            root.removeChildNode(layer)
                except (AttributeError, RuntimeError, TypeError):
                    pass
            layers = [keep]

        used = set()
        for layer in layers:
            try:
                name = str(layer.name())
            except (AttributeError, RuntimeError, TypeError):
                continue
            if name in used or name == "Loomis Method Head Guide":
                name = self._next_guide_name(used)
                try:
                    layer.setName(name)
                except (AttributeError, RuntimeError, TypeError):
                    pass
            used.add(name)
            state = states.get(name)
            model = None
            if isinstance(state, dict):
                model = create_model(state.get("model", DEFAULT_MODEL))
            if model is None:
                model = create_model(DEFAULT_MODEL) or LoomisHead3D()
            if isinstance(state, dict):
                model.from_dict(state)
                self._apply_state_position(model, doc, state)
            else:
                center = self._center_from_layer(layer)
                if center is None:
                    center = (doc.width() / 2.0, doc.height() / 2.0)
                model.set_position_x(center[0])
                model.set_position_y(center[1])
            # El marcador de pivote manda: si la capa lo trae, la posicion real
            # del pivote es la del dibujo. No se recalcula por bounds (el centro
            # del bbox depende de la rotacion y hacia derivar la cabeza).
            marker = _find_pivot_shape(layer)
            pivot = _pivot_position(layer, marker)
            if pivot is not None:
                model.set_position_x(pivot[0])
                model.set_position_y(pivot[1])
            current = self._center_from_layer(layer)
            guide_center = current
            if guide_center is None:
                saved_center = centers.get(name)
                if (
                    isinstance(saved_center, (list, tuple))
                    and len(saved_center) == 2
                ):
                    try:
                        guide_center = (
                            float(saved_center[0]) * doc.width(),
                            float(saved_center[1]) * doc.height(),
                        )
                    except (TypeError, ValueError):
                        guide_center = None
            guide = Guide(model, layer, name)
            guide.last_center = guide_center
            guide.pivot_shape = marker
            guide.model_states = model_states.get(name) or {}
            self.guides.append(guide)

    def _create_guide(self, doc) -> None:
        if not doc:
            return
        name = self._next_guide_name({guide.name for guide in self.guides})
        try:
            layer = doc.createVectorLayer(name)
            root = doc.rootNode()
            if layer is None or root is None:
                return
            root.addChildNode(layer, None)
        except (AttributeError, RuntimeError, TypeError):
            return
        model = create_model(self._current_model_id()) or create_model(DEFAULT_MODEL)
        if self.loomis_head is not None:
            model.from_dict(self.loomis_head.to_dict())
        model.set_position_x(doc.width() / 2.0)
        model.set_position_y(doc.height() / 2.0)
        self.guides.append(Guide(model, layer, name))
        self._set_active_guide(len(self.guides) - 1)
        self._save_doc_state()

    def _refresh_guide_combo(self) -> None:
        combo = self.ui.guideCombo
        combo.blockSignals(True)
        combo.clear()
        if not self.guides:
            combo.addItem("—")
        for guide in self.guides:
            combo.addItem(guide.name)
        if 0 <= self.active_index < combo.count():
            combo.setCurrentIndex(self.active_index)
        combo.blockSignals(False)

    def _set_active_guide(self, index: int) -> None:
        if not 0 <= index < len(self.guides):
            return
        # Si hay un dibujo pendiente (el usuario acaba de mover un control),
        # se vuelca antes de cambiar: el marcador del pivote tiene que reflejar
        # la posicion del modelo, no la del dibujo anterior.
        if self.update_scheduled:
            self._redraw_now()
        self.active_index = index
        guide = self.guides[index]
        # Si la capa se movio mientras esta guia estaba inactiva, el marcador
        # del pivote lo refleja: se adopta su posicion exacta, sin bounds.
        self._pivot_shape = guide.pivot_shape
        pivot = _pivot_position(guide.layer, self._pivot_shape)
        if pivot is not None:
            guide.model.set_position_x(pivot[0])
            guide.model.set_position_y(pivot[1])
        self._last_pivot_position = pivot
        self._remember_center(self._center_from_layer(guide.layer))
        self.loomis_head = guide.model
        self.loomis_layer = guide.layer
        self._last_layer_bounds_center = guide.last_center
        self._sync_panels_for_model()
        try:
            if self.doc is not None:
                self.doc.setActiveNode(guide.layer)
        except (AttributeError, RuntimeError, TypeError):
            pass
        self.trackball.set_model(self.loomis_head)
        self.trackball.set_quaternion(self.loomis_head.q)
        self._sync_ui_from_model()
        self._sync_euler_from_model()
        self._refresh_guide_combo()
        self.schedule_update()

    def _on_guide_selected(self, index: int) -> None:
        if 0 <= index < len(self.guides):
            self._save_doc_state()
            self._set_active_guide(index)
            self._save_doc_state()

    def _new_guide(self, *_args) -> None:
        doc = Krita.instance().activeDocument()
        if not doc:
            self.ui.presetStatus.setText(t("error.no_canvas"))
            return
        if doc is not self.doc:
            self._sync_document(doc)
        self._create_guide(doc)

    def _delete_guide(self, *_args) -> None:
        guide = self.active_guide()
        if guide is None:
            return
        self._save_doc_state()
        try:
            parent = guide.layer.parentNode()
            if parent is not None:
                parent.removeChildNode(guide.layer)
            else:
                root = self.doc.rootNode() if self.doc else None
                if root is not None:
                    root.removeChildNode(guide.layer)
        except (AttributeError, RuntimeError, TypeError):
            pass
        self.guides.remove(guide)
        if self.guides:
            self._set_active_guide(min(self.active_index, len(self.guides) - 1))
        else:
            model, model_id = self._fresh_model()
            self.loomis_head = model
            self.loomis_layer = None
            self.active_index = 0
            self.trackball.set_model(self.loomis_head)
            self._refresh_guide_combo()
            self._sync_ui_from_model()
            self._sync_euler_from_model()
            self._sync_panels_for_model(model_id)
            self.schedule_update()
        self._save_doc_state()

    def active_guide(self):
        if 0 <= self.active_index < len(self.guides):
            return self.guides[self.active_index]
        return None

    def _drop_active_guide(self) -> None:
        if not self.guides:
            return
        self.guides.pop(self.active_index)
        if self.active_index >= len(self.guides) and self.guides:
            self.active_index = len(self.guides) - 1
        self._save_doc_state()

    def _save_doc_state(self) -> None:
        if not self.doc or not self._doc_key:
            return
        try:
            width, height = self.doc.width(), self.doc.height()
        except (AttributeError, RuntimeError, TypeError):
            return
        entries = []
        for guide in self.guides:
            if not self._node_alive(guide.layer):
                continue
            data = guide.model.to_dict()
            if width and height:
                # positionX/Y es la posicion del pivote del modelo (Loomis:
                # centro de la esfera; Asaro: centro del craneo), no el origen
                # de la malla: al cambiar de modelo o de tamano de lienzo no
                # hay conversion, el pivote sigue en el mismo sitio.
                data["positionX"] = guide.model.position_x / width
                data["positionY"] = guide.model.position_y / height
                data["positionUnit"] = "normalized"
            entry = {"name": guide.name, "state": data}
            # Estados de los modelos inactivos de esta guia: el activo ya va en
            # ``state``. Copia profunda para que el JSON no comparta referencias
            # con ``guide.model_states``, que se reescribe en cada cambio.
            active_id = self._model_id_of(guide.model)
            entry["models"] = {
                key: copy.deepcopy(value)
                for key, value in guide.model_states.items()
                if key != active_id and isinstance(value, dict)
            }
            if guide.last_center and width and height:
                entry["center"] = [guide.last_center[0] / width, guide.last_center[1] / height]
            entries.append(entry)
        documents = self._state.setdefault("documents", {})
        documents[self._doc_key] = {"guides": entries, "active": self.active_index}
        self._save_guides_state()

    def _remember_center(self, center) -> None:
        self._last_layer_bounds_center = center
        guide = self.active_guide()
        if guide is not None:
            guide.last_center = center

    def _layer_is_alive(self) -> bool:
        return self._node_alive(self.loomis_layer)

    def ensure_guide(self):
        """Adopta las capas existentes o crea una guia; nunca duplica."""
        doc = Krita.instance().activeDocument()
        if not doc:
            self.doc = None
            self._doc_key = None
            self.guides = []
            self.active_index = 0
            model, model_id = self._fresh_model()
            self.loomis_head = model
            self.loomis_layer = None
            self.trackball.set_model(self.loomis_head)
            self.trackball.set_quaternion(self.loomis_head.q)
            self._sync_euler_from_model()
            self._sync_panels_for_model(model_id)
            self._refresh_guide_combo()
            return
        key = doc.fileName() or f"unsaved:{id(doc)}"
        if doc is not self.doc or key != self._doc_key:
            self._sync_document(doc)
        if not self.guides:
            self._create_guide(doc)
            return
        if not self._layer_is_alive():
            self._drop_active_guide()
            if self.guides:
                self._set_active_guide(min(self.active_index, len(self.guides) - 1))
            else:
                self._create_guide(doc)
            return
        if self._pending_position is not None:
            nx, ny = self._pending_position
            self.loomis_head.set_position_x(nx * doc.width())
            self.loomis_head.set_position_y(ny * doc.height())
            self._pending_position = None
            self._sync_ui_from_model()
            self.schedule_update()
        if self._last_layer_bounds_center is None:
            self._last_layer_bounds_center = self._layer_bounds_center()
            guide = self.active_guide()
            if guide is not None:
                guide.last_center = self._last_layer_bounds_center

    def canvasChanged(self, canvas):
        if self.isVisible():
            self.ensure_guide()

    def with_schedule_update(self, fn):
        fn()
        self.schedule_update()

    def pick_stroke_color(self):
        old_hex = self.loomis_head.stroke_color
        old_qcolor = QColor(old_hex)

        dlg = QColorDialog(self)
        dlg.setOption(QColorDialog.DontUseNativeDialog, True)
        dlg.setCurrentColor(old_qcolor)

        def apply_color(col: QColor):
            if not col.isValid():
                return
            hex_rgb = col.name()
            self.loomis_head.set_stroke_color(hex_rgb)
            self.ui.strokeColorSwatch.setStyleSheet(f"background-color: {hex_rgb}; border: 1px solid #666;")
            self.schedule_update()

        dlg.currentColorChanged.connect(apply_color)
        dlg.colorSelected.connect(apply_color)

        def revert():
            self.loomis_head.set_stroke_color(old_hex)
            self.ui.strokeColorSwatch.setStyleSheet(f"background-color: {old_hex}; border: 1px solid #666;")
            self.schedule_update()

        dlg.rejected.connect(revert)
        exec_dialog(dlg)

    def _build_transform_panel(self) -> QGroupBox:
        group = QGroupBox(t("transform.section"))
        form = QFormLayout(group)
        self.posXSlider = QSlider(Qt.Horizontal)
        self.posYSlider = QSlider(Qt.Horizontal)
        self.posXValue = QLabel("0 px")
        self.posYValue = QLabel("0 px")
        for label, slider, value in (
            (t("transform.x"), self.posXSlider, self.posXValue),
            (t("transform.y"), self.posYSlider, self.posYValue),
        ):
            row = QHBoxLayout()
            row.addWidget(slider, 1)
            row.addWidget(value)
            form.addRow(label, row)
            slider.setRange(0, 1000)
        self.rotXSlider = QSlider(Qt.Horizontal)
        self.rotYSlider = QSlider(Qt.Horizontal)
        self.rotZSlider = QSlider(Qt.Horizontal)
        self.rotXValue = QLabel("0°")
        self.rotYValue = QLabel("0°")
        self.rotZValue = QLabel("0°")
        for label, slider, value in (
            (t("transform.rx"), self.rotXSlider, self.rotXValue),
            (t("transform.ry"), self.rotYSlider, self.rotYValue),
            (t("transform.rz"), self.rotZSlider, self.rotZValue),
        ):
            row = QHBoxLayout()
            row.addWidget(slider, 1)
            row.addWidget(value)
            form.addRow(label, row)
            slider.setRange(-180, 180)
        self.posXSlider.valueChanged.connect(self._on_pos_x_slider)
        self.posYSlider.valueChanged.connect(self._on_pos_y_slider)
        for signal, slot in (
            (self.ui.positionXSpinBox.valueChanged, self._on_pos_x_spin),
            (self.ui.positionYSpinBox.valueChanged, self._on_pos_y_spin),
        ):
            try:
                signal.disconnect(slot)
            except TypeError:
                pass
        self.ui.positionXSpinBox.valueChanged.connect(self._on_pos_x_spin)
        self.ui.positionYSpinBox.valueChanged.connect(self._on_pos_y_spin)
        for slider in (self.rotXSlider, self.rotYSlider, self.rotZSlider):
            slider.valueChanged.connect(self._on_rot_slider)
        # Sin flush al soltar: el desplazamiento se respeta y el canvas se
        # redibuja solo cuando expira ``_redraw_timer`` (Input Delay).
        return group

    def _refresh_transform_ranges(self) -> None:
        if not hasattr(self, "posXSlider"):
            return
        width = self.doc.width() if self.doc else 1000
        height = self.doc.height() if self.doc else 1000
        self.posXSlider.setRange(0, max(1, width))
        self.posYSlider.setRange(0, max(1, height))

    def _on_pos_x_slider(self, value: int) -> None:
        if self._slider_sync or self.loomis_head is None:
            return
        self.loomis_head.set_position_x(value)
        self.ui.positionXSpinBox.blockSignals(True)
        self.ui.positionXSpinBox.setValue(value)
        self.ui.positionXSpinBox.blockSignals(False)
        self.posXValue.setText(f"{value} px")
        self.schedule_update()

    def _on_pos_y_slider(self, value: int) -> None:
        if self._slider_sync or self.loomis_head is None:
            return
        self.loomis_head.set_position_y(value)
        self.ui.positionYSpinBox.blockSignals(True)
        self.ui.positionYSpinBox.setValue(value)
        self.ui.positionYSpinBox.blockSignals(False)
        self.posYValue.setText(f"{value} px")
        self.schedule_update()

    def _on_pos_x_spin(self, value: int) -> None:
        if self._slider_sync:
            return
        self._slider_sync = True
        self.posXSlider.setValue(int(value))
        self._slider_sync = False
        self.posXValue.setText(f"{int(value)} px")

    def _on_pos_y_spin(self, value: int) -> None:
        if self._slider_sync:
            return
        self._slider_sync = True
        self.posYSlider.setValue(int(value))
        self._slider_sync = False
        self.posYValue.setText(f"{int(value)} px")

    def _on_rot_slider(self, *_args) -> None:
        if self._slider_sync or self.loomis_head is None:
            return
        self._slider_sync = True
        for spin, slider in (
            (self.ui.rotXSpin, self.rotXSlider),
            (self.ui.rotYSpin, self.rotYSlider),
            (self.ui.rotZSpin, self.rotZSlider),
        ):
            spin.blockSignals(True)
            spin.setValue(slider.value())
            spin.blockSignals(False)
        self._slider_sync = False
        self._apply_euler()

    def _sync_transform_sliders(self) -> None:
        if self.loomis_head is None or not hasattr(self, "posXSlider"):
            return
        self._slider_sync = True
        self.posXSlider.setValue(round(self.loomis_head.position_x))
        self.posYSlider.setValue(round(self.loomis_head.position_y))
        self.rotXSlider.setValue(self.ui.rotXSpin.value())
        self.rotYSlider.setValue(self.ui.rotYSpin.value())
        self.rotZSlider.setValue(self.ui.rotZSpin.value())
        self.posXValue.setText(f"{round(self.loomis_head.position_x)} px")
        self.posYValue.setText(f"{round(self.loomis_head.position_y)} px")
        self.rotXValue.setText(f"{self.ui.rotXSpin.value()}°")
        self.rotYValue.setText(f"{self.ui.rotYSpin.value()}°")
        self.rotZValue.setText(f"{self.ui.rotZSpin.value()}°")
        self._slider_sync = False

    def _apply_language(self) -> None:
        self.setWindowTitle(t("window.title"))
        self.ui.groupGuides.setTitle(t("group.guides"))
        self.ui.presetGroup.setTitle(t("group.library"))
        for widget, key in (
            (self.ui.labelScale, "label.scale"),
            (self.ui.labelSideCut, "label.side_cut"),
            (self.ui.labelFrontStroke, "label.front_stroke"),
            (self.ui.labelBackStroke, "label.back_stroke"),
            (self.ui.labelFaceAge, "label.face_age"),
            (self.ui.labelChinWidth, "label.chin_width"),
            (self.ui.labelPositionX, "label.position_x"),
            (self.ui.labelPositionY, "label.position_y"),
            (self.ui.labelStrokeColor, "label.stroke_color"),
            (self.ui.labelView, "view.label"),
            (self.ui.labelGuide, "guide.label"),
            (self.ui.labelRot, "rot.label"),
        ):
            widget.setText(t(key))
        for widget, key in (
            (self.ui.showFace, "check.face"),
            (self.ui.showSilhouette, "check.silhouette"),
            (self.ui.showSideRims, "check.side_rims"),
            (self.ui.showSideCross, "check.side_cross"),
            (self.ui.showArrow, "check.arrow"),
            (self.ui.zoneColors, "check.zone_colors"),
        ):
            widget.setText(t(key))
        for widget, key in (
            (self.ui.resetButton, "button.reset_rotation"),
            (self.ui.resetPositionButton, "button.reset_position"),
            (self.ui.resetSettingsButton, "button.reset_settings"),
            (self.ui.saveButton, "button.apply"),
            (self.ui.featuresButton, "button.features"),
            (self.ui.presetSaveButton, "button.save"),
            (self.ui.presetDeleteButton, "button.delete"),
            (self.ui.ocSaveButton, "button.save_oc"),
            (self.ui.headLoadButton, "button.load_head"),
            (self.ui.headSaveButton, "button.export_head"),
        ):
            widget.setText(t(key))
        line_edit = self.ui.presetCombo.lineEdit()
        if line_edit is not None:
            line_edit.setPlaceholderText(t("preset.placeholder"))
        if self.ui.ocCombo.count():
            self.ui.ocCombo.setItemText(0, t("combo.oc"))
        self.ui.guideNewButton.setToolTip(t("button.new_head"))
        self.ui.guideDeleteButton.setToolTip(t("button.delete_head"))
        self.ui.creditLabel.setText(t("credit.text"))
        self.trackball.setToolTip(t("preview.hint"))
        if hasattr(self, "tabs"):
            for index, key in enumerate((
                "tabs.settings",
                "tabs.transform",
                "tabs.guides",
                "tabs.features",
                "tabs.hair",
            )):
                if index < self.tabs.count():
                    self.tabs.setTabText(index, t(key))
        if hasattr(self, "language_group"):
            self.language_group.setTitle(t("language.section"))
            self.languageLabel.setText(t("language.label"))
            self.languageCombo.setItemText(0, t("language.auto"))
        if hasattr(self, "delayLabel"):
            self.delayLabel.setText(t("delay.label"))
            self.delaySpin.setToolTip(t("delay.tooltip"))
        if hasattr(self.ui, "viewCombo"):
            current = self.ui.viewCombo.currentIndex()
            self.ui.viewCombo.blockSignals(True)
            self.ui.viewCombo.clear()
            for key in ("view.front", "view.three_quarter", "view.profile", "view.back", "view.top"):
                self.ui.viewCombo.addItem(t(key))
            if 0 <= current < self.ui.viewCombo.count():
                self.ui.viewCombo.setCurrentIndex(current)
            self.ui.viewCombo.blockSignals(False)
        if hasattr(self, "_characters"):
            self._refresh_oc_combo()
        if self.model_label is not None:
            self.model_label.setText(t("model.label"))
        if self.model_combo is not None:
            self.model_combo.blockSignals(True)
            for index in range(self.model_combo.count()):
                model_id = self.model_combo.itemData(index)
                if model_id:
                    self.model_combo.setItemText(index, t("model." + str(model_id)))
            self.model_combo.blockSignals(False)

    def connect_ui(self):
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "LoomisDocker.ui")
        self.ui: QWidget = uic.loadUi(ui_path)
        self.setWidget(self.ui)
        # Initialize the model from the default scale and canvas-center position.
        self.loomis_head.set_scale(self.ui.sizeSlider.value() * 0.01)
        if self.doc:
            self.ui.positionXSpinBox.setValue(self.doc.width() // 2)
            self.ui.positionYSpinBox.setValue(self.doc.height() // 2)
        self.loomis_head.set_position_x(self.ui.positionXSpinBox.value())
        self.loomis_head.set_position_y(self.ui.positionYSpinBox.value())

        host = self.ui.findChild(QWidget, "trackballHost")
        self.trackball = HeadPreviewWidget(self.loomis_head, host)
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        self.trackball.setSizePolicy(EXPANDING, EXPANDING)
        lay.addWidget(self.trackball)

        self.trackball.orientation_changed.connect(self._on_preview_rotation)

        self.ui.sizeSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_scale(v * 0.01)))
        self.ui.sideCutSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_sidecut(v * 0.01)))
        self.ui.faceAgeSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_face_age(v * 0.01)))
        self.ui.positionXSpinBox.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_position_x(v)))
        self.ui.positionYSpinBox.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_position_y(v)))
        self.ui.chinWidthSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_chin_width(v * 0.01)))
        self.ui.showFace.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_show_face(v)))
        self.ui.frontStrokeSlider.valueChanged.connect(
            lambda v: self.with_schedule_update(lambda: self.loomis_head.set_front_line_stroke(v))
        )
        self.ui.backStrokeSlider.valueChanged.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_back_line_stroke(v)))
        # Sin flush en ``sliderReleased``: el retardo configurado manda y el
        # canvas solo se redibuja al expirar ``_redraw_timer``. La preview del
        # docker ya se repinta en vivo en cada ``valueChanged``.

        self.ui.showArrow.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_arrow(v)))
        self.ui.zoneColors.toggled.connect(self._set_zone_colors)
        self.ui.showSilhouette.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_silhouette(v)))
        self.ui.showSideRims.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_side_rims(v)))
        self.ui.showSideCross.toggled.connect(lambda v: self.with_schedule_update(lambda: self.loomis_head.set_side_cross(v)))
        self.ui.strokeColorButton.clicked.connect(self.pick_stroke_color)
        self.ui.resetButton.clicked.connect(self.reset_view)
        self.ui.resetPositionButton.clicked.connect(self.reset_position)
        self.ui.resetSettingsButton.clicked.connect(self.reset_settings)
        self.ui.saveButton.clicked.connect(self.save_head)
        self._apply_language()

    def _build_dashboard(self) -> None:
        """Deja fijos cabeza, preview, vista y biblioteca; el resto en pestanas."""
        outer = self.ui.layout()
        scroll = self.ui.scrollArea
        if outer is not None:
            outer.removeWidget(scroll)

        fixed = QWidget()
        fixed_layout = QVBoxLayout(fixed)
        fixed_layout.setContentsMargins(10, 10, 10, 6)
        fixed_layout.setSpacing(6)

        head_row = QHBoxLayout()
        head_row.addWidget(self.ui.labelGuide)
        head_row.addWidget(self.ui.guideCombo, 1)
        head_row.addWidget(self.ui.guideNewButton)
        head_row.addWidget(self.ui.guideDeleteButton)
        fixed_layout.addLayout(head_row)

        preview_row = QHBoxLayout()
        axis = QVBoxLayout()
        axis.addWidget(self.ui.labelRot)
        axis.addWidget(self.ui.rotXSpin)
        axis.addWidget(self.ui.rotYSpin)
        axis.addWidget(self.ui.rotZSpin)
        axis.addStretch(1)
        preview_row.addLayout(axis)
        self.ui.trackballHost.setFixedHeight(240)
        preview_row.addWidget(self.ui.trackballHost, 1)
        fixed_layout.addLayout(preview_row, 1)

        view_row = QHBoxLayout()
        view_row.addWidget(self.ui.labelView)
        view_row.addWidget(self.ui.viewCombo, 1)
        fixed_layout.addLayout(view_row)

        self.delayLabel = QLabel(t("delay.label"))
        self.delaySpin = QSpinBox()
        self.delaySpin.setRange(DELAY_MIN_MS, DELAY_MAX_MS)
        self.delaySpin.setSingleStep(DELAY_STEP_MS)
        self.delaySpin.setSuffix(" ms")
        self.delaySpin.setValue(
            _clamp_delay(self._settings.get("redrawDelay", REDRAW_INTERVAL_MS))
        )
        self.delaySpin.setToolTip(t("delay.tooltip"))
        # Conectar despues de fijar el valor: el arranque no reescribe settings.
        self.delaySpin.valueChanged.connect(self._on_delay_changed)
        delay_row = QHBoxLayout()
        delay_row.addWidget(self.delayLabel)
        delay_row.addWidget(self.delaySpin, 1)
        fixed_layout.addLayout(delay_row)

        fixed_layout.addWidget(self.ui.presetGroup)

        actions_row = QGridLayout()
        actions_row.addWidget(self.ui.resetButton, 0, 0)
        actions_row.addWidget(self.ui.resetPositionButton, 0, 1)
        actions_row.addWidget(self.ui.resetSettingsButton, 1, 0)
        actions_row.addWidget(self.ui.saveButton, 1, 1)
        fixed_layout.addLayout(actions_row)

        if outer is not None:
            outer.addWidget(fixed, 0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(True)
        if outer is not None:
            outer.addWidget(self.tabs, 1)

        settings_layout = scroll.widget().layout() if scroll.widget() is not None else None
        if settings_layout is not None:
            if hasattr(self.ui, "separatorTop"):
                settings_layout.removeWidget(self.ui.separatorTop)
                self.ui.separatorTop.deleteLater()
            if self.language_group is not None:
                index = settings_layout.indexOf(self.ui.creditLabel)
                settings_layout.insertWidget(
                    index if index >= 0 else settings_layout.count(),
                    self.language_group,
                )
        self.tabs.addTab(scroll, t("tabs.settings"))

        self.transform_page, self.transform_page_layout = self._page(self.transform_group)
        self.tabs.addTab(self.transform_page, t("tabs.transform"))

        self.guides_page, self.guides_page_layout = self._page(self.ui.groupGuides)
        self.tabs.addTab(self.guides_page, t("tabs.guides"))

        self.feature_stack = QStackedWidget()
        self.feature_stack.addWidget(self.feature_panel)
        self.feature_stack.addWidget(self.asaro_panel)
        self.feature_page, self.feature_page_layout = self._page(self.feature_stack)
        model_row = self._build_model_row()
        self.feature_page_layout.insertWidget(0, model_row)
        self.tabs.addTab(self.feature_page, t("tabs.features"))

        self.hair_page, self.hair_page_layout = self._page(self.hair_panel)
        self.tabs.addTab(self.hair_page, t("tabs.hair"))

    def _page(self, widget: QWidget):
        """Envuelve un panel en una pestana con scroll propio."""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(widget)
        layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll, layout

    # --- modelos (Loomis / Asaro) -----------------------------------------
    def _model_id_of(self, model) -> str:
        """Identificador de un modelo; cae en Loomis si no se reconoce."""
        if model is None:
            return DEFAULT_MODEL
        model_id = getattr(model, "model_id", None)
        if not model_id:
            try:
                model_id = model.to_dict().get("model")
            except (AttributeError, TypeError, ValueError):
                model_id = None
        model_id = str(model_id or DEFAULT_MODEL).strip().lower()
        return model_id if model_id in supported_models() else DEFAULT_MODEL

    def _current_model_id(self) -> str:
        """Identificador del modelo activo; cae en Loomis si no se reconoce."""
        return self._model_id_of(getattr(self, "loomis_head", None))

    def _state_owner(self, guide=None):
        """Guia que guarda el estado; la activa si no se indica otra."""
        return guide if guide is not None else self.active_guide()

    def _stash_model(self, model, guide=None) -> None:
        """Guarda ``model.to_dict()`` en el stash de la guia (o el global)."""
        if model is None:
            return
        try:
            state = model.to_dict()
        except (AttributeError, TypeError, ValueError):
            return
        model_id = self._model_id_of(model)
        owner = self._state_owner(guide)
        if owner is not None:
            owner.model_states[model_id] = state
        else:
            self._model_stash[model_id] = state

    def _restore_model_state(self, model_id: str, guide=None):
        """Estado guardado del modelo: el de la guia, o el global sin guia.

        Con guia activa no se cae al stash global a proposito: ese estado
        puede venir de otro documento y traeria una posicion en pixeles ajena.
        """
        model_id = str(model_id or "").strip().lower()
        owner = self._state_owner(guide)
        if owner is not None:
            return owner.model_states.get(model_id)
        return self._model_stash.get(model_id)

    # Campos que no son de un modelo concreto: transformacion y aspecto del
    # trazo. Se copian siempre del modelo saliente al entrante para que la guia
    # no salte de sitio al cambiar de modelo.
    _COMMON_STATE_FIELDS = (
        ("scale", "set_scale"),
        ("position_x", "set_position_x"),
        ("position_y", "set_position_y"),
        ("q", "set_quaternion"),
        ("stroke_color", "set_stroke_color"),
        ("front_line_stroke", "set_front_line_stroke"),
        ("back_line_stroke", "set_back_line_stroke"),
        ("use_zone_colors", "set_zone_colors"),
    )

    def _copy_common_state(self, source, target) -> None:
        """Copia transformacion/trazos de ``source`` a ``target``."""
        if source is None or target is None:
            return
        for attr, setter_name in self._COMMON_STATE_FIELDS:
            if not hasattr(source, attr) or not hasattr(target, attr):
                continue
            value = getattr(source, attr)
            setter = getattr(target, setter_name, None)
            if setter is None:
                setattr(target, attr, value)
                continue
            try:
                setter(value)
            except (AttributeError, TypeError, ValueError):
                pass

    def _switch_model(self, model_id: str, guide=None):
        """Cambia el modelo activo conservando el estado de cada modelo.

        Guarda el estado completo del modelo saliente y restaura el del
        entrante si ya se habia usado. Despues **siempre** reaplica los campos
        comunes del saliente: el stash solo aporta lo propio de cada modelo
        (``head_sex``, ``cranium``, ``show_planes``, ``detail``...), asi que
        mover/rotar/escalar y cambiar de modelo no devuelve la transformacion
        vieja del stash.
        """
        model_id = str(model_id or "").strip().lower()
        new = create_model(model_id)
        if new is None:
            return None
        owner = self._state_owner(guide)
        old = self.loomis_head
        state = self._restore_model_state(model_id, owner)
        if old is not None:
            self._stash_model(old, owner)
        if state is not None:
            try:
                new.from_dict(state)
            except (AttributeError, TypeError, ValueError):
                pass
        elif old is not None:
            # Primera vez con este modelo: cada clase ignora las claves que no
            # conoce (p. ej. showPlanes al volver a Loomis).
            try:
                new.from_dict(old.to_dict())
            except (AttributeError, TypeError, ValueError):
                pass
        self._copy_common_state(old, new)
        if owner is not None:
            owner.model = new
        self.loomis_head = new
        self.trackball.set_model(new)
        self._sync_panels_for_model(model_id)
        self._sync_ui_from_model()
        self._sync_euler_from_model()
        self.schedule_update()
        return new

    def _fresh_model(self):
        """Nueva instancia del modelo activo y su id (Loomis como respaldo)."""
        model_id = self._current_model_id()
        model = create_model(model_id)
        if model is None:
            model_id = DEFAULT_MODEL
            model = create_model(model_id) or LoomisHead3D()
        return model, model_id

    def _loomis_model(self):
        """Instancia Loomis para construir paneles que solo existen en Loomis."""
        return create_model(DEFAULT_MODEL) or LoomisHead3D()

    def _sync_panels_for_model(self, model_id: str | None = None) -> None:
        """Alinea combo/stack y los paneles con el modelo activo.

        Los paneles de rasgos y pelo son exclusivos de Loomis: con Asaro se
        ocultan (el stack muestra AsaroPanel) y no se tocan.
        """
        model_id = model_id or self._current_model_id()
        self._set_model_ui(model_id)
        if model_id == "asaro":
            if self.asaro_panel is not None:
                self.asaro_panel.set_model(self.loomis_head)
            return
        if self.feature_panel is not None:
            self.feature_panel.set_model(self.loomis_head)
        if self.hair_panel is not None:
            self.hair_panel.set_model(self.loomis_head)

    def _set_model_ui(self, model_id: str) -> None:
        """Combo, stack de Rasgos, pestanas y filas Loomis-only segun modelo."""
        is_asaro = model_id == "asaro"
        if self.model_combo is not None:
            index = self.model_combo.findData(model_id)
            if index >= 0 and index != self.model_combo.currentIndex():
                self.model_combo.blockSignals(True)
                self.model_combo.setCurrentIndex(index)
                self.model_combo.blockSignals(False)
        if self.feature_stack is not None:
            self.feature_stack.setCurrentIndex(1 if is_asaro else 0)
        if hasattr(self, "tabs"):
            for tab in (2, 4):  # Guias y Pelo
                if tab < self.tabs.count():
                    self.tabs.setTabEnabled(tab, not is_asaro)
        # Filas de Ajustes que solo existen en Loomis.
        for name in (
            "labelSideCut", "sideCutSlider",
            "labelFaceAge", "faceAgeSlider",
            "labelChinWidth", "chinWidthSlider",
        ):
            widget = getattr(self.ui, name, None)
            if widget is not None:
                widget.setVisible(not is_asaro)

    def _build_model_row(self) -> QWidget:
        """Fila con el combo de modelo, encima del panel de Rasgos."""
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        self.model_label = QLabel(t("model.label"))
        self.model_combo = QComboBox()
        for model_id in supported_models():
            self.model_combo.addItem(t("model." + model_id), model_id)
        current = self.model_combo.findData(self._current_model_id())
        if current >= 0:
            self.model_combo.setCurrentIndex(current)
        activated_index(self.model_combo).connect(self._on_model_changed)
        row.addWidget(self.model_label)
        row.addWidget(self.model_combo, 1)
        return box

    def _on_model_changed(self, index: int) -> None:
        """Cambia el modelo activo conservando el estado de cada modelo."""
        if self.model_combo is None:
            return
        model_id = str(self.model_combo.itemData(index) or "").strip().lower()
        if not model_id:
            return
        if model_id == self._current_model_id():
            self._set_model_ui(model_id)
            return
        if self._switch_model(model_id) is None:
            self.ui.presetStatus.setText(t("error.model_unknown", model=model_id))
            previous = self.model_combo.findData(self._current_model_id())
            if previous >= 0:
                self.model_combo.blockSignals(True)
                self.model_combo.setCurrentIndex(previous)
                self.model_combo.blockSignals(False)
            return
        self._save_doc_state()
        self.ui.presetStatus.setText(t("status.model_switched", model=t("model." + model_id)))

    def schedule_update(self):
        # Preview en vivo: el repintado 3D no espera al debounce del canvas.
        self.trackball.update()
        if hasattr(self, "_state_timer"):
            self._state_timer.start()
        # Cada cambio reinicia el debounce: el canvas se redibuja 500 ms
        # despues del ULTIMO cambio (no durante el arrastre).
        self.update_scheduled = True
        self._redraw_timer.start()

    def _on_delay_changed(self, value: int) -> None:
        """Guarda el Input Delay y cambia el intervalo del debounce.

        No redibuja: el retardo es solo la espera antes de mandar al canvas.
        """
        delay = _clamp_delay(value)
        if delay != value:
            self.delaySpin.blockSignals(True)
            self.delaySpin.setValue(delay)
            self.delaySpin.blockSignals(False)
        if hasattr(self, "_redraw_timer"):
            self._redraw_timer.setInterval(delay)
        self._settings["redrawDelay"] = delay
        self._save_settings()

    # create_loomis_layer se sustituyo por _create_guide/ensure_guide.

    def _layer_bounds_center(self):
        """Return vector layer content center in document pixels, if available."""
        if not self.loomis_layer:
            return None
        try:
            bounds = self.loomis_layer.bounds()
            if bounds is None or bounds.isNull() or bounds.isEmpty():
                return None
            return (bounds.x() + bounds.width() / 2.0,
                    bounds.y() + bounds.height() / 2.0)
        except (AttributeError, RuntimeError, TypeError):
            return None

    def sync_manual_position(self):
        """Mueve X/Y con el lienzo segun el marcador del pivote (1:1).

        El marcador ``loomis-pivot`` se desplaza con la capa cuando el usuario
        usa Move/Transform. El delta que se lee aqui se suma **una sola vez** a
        ``position_x/position_y`` (que son la posicion del pivote) y se toma el
        marcador como nueva referencia, asi que no hay division por 2 ni
        conversion por bounds: mover el lienzo +100 px mueve X/Y +100 px.

        Si la capa no trae marcador (version anterior, o documento recien
        cargado antes del primer draw) no se sincroniza nada: la posicion se
        resuelve al redibujar, que recrea el marcador.
        """
        if (not self.doc or not self.loomis_layer or not self.loomis_head
                or self._drawing):
            return

        pivot = _pivot_position(self.loomis_layer, self._pivot_shape)
        if pivot is None:
            return
        if self._last_pivot_position is None:
            self._last_pivot_position = pivot
            return

        dx = pivot[0] - self._last_pivot_position[0]
        dy = pivot[1] - self._last_pivot_position[1]
        # Ignora ruido subpixel del redondeo de la caja del marcador.
        if abs(dx) < 0.5 and abs(dy) < 0.5:
            return

        self.loomis_head.set_position_x(self.loomis_head.position_x + dx)
        self.loomis_head.set_position_y(self.loomis_head.position_y + dy)
        x_blocker = QSignalBlocker(self.ui.positionXSpinBox)
        y_blocker = QSignalBlocker(self.ui.positionYSpinBox)
        self.ui.positionXSpinBox.setValue(round(self.loomis_head.position_x))
        self.ui.positionYSpinBox.setValue(round(self.loomis_head.position_y))
        del x_blocker, y_blocker
        self._sync_transform_sliders()
        # Do not redraw here: allow Krita's active tool to finish moving the
        # existing shapes. The next Loomis control change uses the synced X/Y.
        self._last_pivot_position = pivot
        self._remember_center(self._layer_bounds_center())
        if hasattr(self, "_state_timer"):
            self._state_timer.start()

    def _redraw_now(self, *_args) -> None:
        """Flush a pending redraw at once (slider released)."""
        if hasattr(self, "_redraw_timer"):
            self._redraw_timer.stop()
        self.update_scheduled = False
        self.draw_lines_with_vectors()

    # Limitation: Krita 5.3.4's krita.pyi exposes neither beginUndo/endUndo nor
    # KUndo2Command, so the plugin cannot open an undo macro around this call.
    # Each redraw (shape.remove + addShapesFromSvg) therefore leaves its own
    # entries in the undo history. Mitigation only: redraw after the Input Delay
    # (500 ms by default) with no flush on sliderReleased. Grouping them into a
    # single undo step needs C++ (or a layer swap Krita groups, which would break
    # Guide.layer/guides.json) and stays as debt.
    def draw_lines_with_vectors(self, samples: int = 512):
        if not self.doc:
            self.update_scheduled = False
            return
        if not self._layer_is_alive():
            self.ensure_guide()
            self.update_scheduled = False
            return

        # Antes de leer cualquier posicion: si el usuario movio la capa con
        # Move/Transform, el marcador esta desplazado y X/Y siguen viejos. Se
        # adopta el marcador (1:1) para que build_svg y el marcador nuevo se
        # creen donde el usuario lo dejo, no en la posicion anterior.
        self.sync_manual_position()

        self._drawing = True
        try:
            svg = self.loomis_head.build_svg(
                width=self.doc.width(),
                height=self.doc.height(),
                dash_back="8,8",
                samples=samples,
            )
            svg = self._with_pivot_marker(svg)

            for shape in self.loomis_layer.shapes():
                shape.remove()

            # ``addShapesFromSvg`` devuelve los shapes creados en orden de
            # documento; el marcador es el ultimo elemento del SVG. Guardar esa
            # referencia evita depender del nombre que Krita le asigne.
            try:
                added = list(self.loomis_layer.addShapesFromSvg(svg) or [])
            except (AttributeError, RuntimeError, TypeError):
                added = []
            self._pivot_shape = next(
                (shape for shape in reversed(added) if _is_pivot_shape(shape)), None
            )
            # El marcador recien creado es la nueva referencia de posicion: se
            # lee su centro en el documento (no el bbox de la capa, que cambia
            # al rotar) para que el siguiente movimiento manual sea 1:1.
            self._last_pivot_position = _pivot_position(self.loomis_layer, self._pivot_shape)
            self._last_layer_bounds_center = self._layer_bounds_center()
            guide = self.active_guide()
            if guide is not None:
                guide.last_center = self._last_layer_bounds_center
                guide.pivot_shape = self._pivot_shape
        except (AttributeError, RuntimeError, TypeError):
            self._last_pivot_position = None
            self._pivot_shape = None
            self.ensure_guide()
        finally:
            self._drawing = False
            self.update_scheduled = False

    def _with_pivot_marker(self, svg: str) -> str:
        """Anade al SVG el marcador invisible del pivote (1 px, id fijo).

        El pivote es ``position_x/position_y`` en el documento, asi que el
        marcador se dibuja ahi mismo. No cambia el render: sin relleno visible
        ni trazo (``fill-opacity=0``), y su caja de 1 px queda dentro de la
        cabeza. Se usa para leer la posicion real cuando el usuario mueve la
        capa con Move/Transform.
        """
        if self.loomis_head is None or not svg.endswith("</svg>"):
            return svg
        x = self.loomis_head.position_x
        y = self.loomis_head.position_y
        marker = (
            f'<circle id="{PIVOT_SHAPE_NAME}" cx="{x:.3f}" cy="{y:.3f}" r="0.5" '
            'fill="#000000" fill-opacity="0" stroke="none"/>'
        )
        return svg[:-6] + marker + "</svg>"

    def reset_view(self):
        # Reset rotation only; leave the scale slider and current scale untouched.
        self.trackball.reset(emit=False)
        self.loomis_head.set_quaternion(q_identity())
        self._sync_euler_from_model()
        self.schedule_update()

    def reset_position(self):
        """Return the guide to the center of the current document without changing other settings."""
        center_x = self.doc.width() // 2 if self.doc else 0
        center_y = self.doc.height() // 2 if self.doc else 0
        self.loomis_head.set_position_x(center_x)
        self.loomis_head.set_position_y(center_y)
        x_blocker = QSignalBlocker(self.ui.positionXSpinBox)
        y_blocker = QSignalBlocker(self.ui.positionYSpinBox)
        self.ui.positionXSpinBox.setValue(center_x)
        self.ui.positionYSpinBox.setValue(center_y)
        del x_blocker, y_blocker
        self.schedule_update()

    def reset_settings(self):
        """Restore default visual settings without changing position or rotation."""
        self.ui.sizeSlider.setValue(40)
        self.ui.sideCutSlider.setValue(66)
        self.ui.faceAgeSlider.setValue(75)
        self.ui.chinWidthSlider.setValue(100)
        self.ui.showFace.setChecked(True)
        self.ui.frontStrokeSlider.setValue(10)
        self.ui.backStrokeSlider.setValue(7)

        # Also sync the model if a slider was already at its default value.
        self.loomis_head.set_scale(0.40)
        self.loomis_head.set_sidecut(0.66)
        self.loomis_head.set_face_age(0.75)
        self.loomis_head.set_chin_width(1.0)
        self.loomis_head.set_show_face(True)
        self.loomis_head.set_front_line_stroke(10)
        self.loomis_head.set_back_line_stroke(7)
        self.schedule_update()

    def _preset_path(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        root = Path(base) if base else Path.home() / ".local" / "share" / "krita"
        return root / "loomis_head" / "presets.json"

    def _load_presets(self) -> None:
        try:
            raw = json.loads(self._presets_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        if isinstance(raw.get("presets"), dict):
            self._presets["presets"] = raw["presets"]
        if isinstance(raw.get("characters"), dict):
            self._presets["characters"] = raw["characters"]

    def _write_presets(self) -> None:
        self._presets_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._presets_path.with_name(self._presets_path.name + ".tmp")
        temp.write_text(json.dumps(self._presets, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, self._presets_path)

    def _bind_library(self) -> None:
        activated_text(self.ui.presetCombo).connect(self._on_preset_activated)
        self.ui.presetSaveButton.clicked.connect(self._save_preset)
        self.ui.presetDeleteButton.clicked.connect(self._delete_preset)
        activated_index(self.ui.ocCombo).connect(self._on_oc_activated)
        self.ui.ocSaveButton.clicked.connect(self._save_to_character)
        self.ui.headLoadButton.clicked.connect(self._load_head_file)
        self.ui.headSaveButton.clicked.connect(self._export_head_file)
        self.ui.viewCombo.blockSignals(True)
        self.ui.viewCombo.clear()
        for key in ("view.front", "view.three_quarter", "view.profile", "view.back", "view.top"):
            self.ui.viewCombo.addItem(t(key))
        self.ui.viewCombo.setCurrentIndex(0)
        self.ui.viewCombo.blockSignals(False)
        activated_index(self.ui.viewCombo).connect(self._apply_view)
        activated_index(self.ui.guideCombo).connect(self._on_guide_selected)
        self.ui.guideNewButton.clicked.connect(self._new_guide)
        self.ui.guideDeleteButton.clicked.connect(self._delete_guide)
        for spin in (self.ui.rotXSpin, self.ui.rotYSpin, self.ui.rotZSpin):
            spin.valueChanged.connect(self._apply_euler)

    def _refresh_presets(self, select: str | None = None) -> None:
        combo = self.ui.presetCombo
        current = select if select is not None else combo.currentText().strip()
        names = sorted(self._presets.get("presets", {}))
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(names)
        if current:
            combo.setEditText(current)
        combo.blockSignals(False)
        self.ui.presetStatus.setText(t("status.presets", n=len(names)) if names else t("status.no_presets"))

    def _settings_path(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        root = Path(base) if base else Path.home() / ".local" / "share" / "krita"
        return root / "loomis_head" / "settings.json"

    def _load_settings(self) -> dict:
        try:
            raw = json.loads(self._settings_path().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"language": ""}
        return raw if isinstance(raw, dict) else {"language": ""}

    def _save_settings(self) -> None:
        try:
            path = self._settings_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + ".tmp")
            temp.write_text(json.dumps(self._settings, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, path)
        except OSError:
            pass

    def _build_language_panel(self) -> QGroupBox:
        group = QGroupBox(t("language.section"))
        form = QFormLayout(group)
        self.languageLabel = QLabel(t("language.label"))
        self.languageCombo = QComboBox()
        self.languageCombo.addItem(t("language.auto"), "")
        self.languageCombo.addItem("English", "en")
        self.languageCombo.addItem("Español", "es")
        self.languageCombo.addItem("Português", "pt")
        self.languageCombo.addItem("Français", "fr")
        code = self._settings.get("language") or ""
        index = self.languageCombo.findData(code)
        self.languageCombo.setCurrentIndex(index if index >= 0 else 0)
        activated_index(self.languageCombo).connect(self._on_language_changed)
        form.addRow(self.languageLabel, self.languageCombo)
        return group

    def _on_language_changed(self, index: int) -> None:
        code = self.languageCombo.itemData(index) or None
        i18n.set_language(code)
        self._settings["language"] = code or ""
        self._save_settings()
        self._apply_language()
        self._reload_localized_panels()

    def _reload_localized_panels(self) -> None:
        """Recrea los paneles traducidos tras cambiar de idioma."""
        if self.feature_stack is not None:
            old_feature = self.feature_panel
            old_asaro = self.asaro_panel
            if old_feature is not None:
                self.feature_stack.removeWidget(old_feature)
            if old_asaro is not None:
                self.feature_stack.removeWidget(old_asaro)
            self.feature_panel = FeaturePanel(self._loomis_model(), self.schedule_update, self)
            self.asaro_panel = AsaroPanel(self.loomis_head, self.schedule_update, self)
            self.feature_stack.insertWidget(0, self.feature_panel)
            self.feature_stack.insertWidget(1, self.asaro_panel)
            for old in (old_feature, old_asaro):
                if old is not None:
                    old.deleteLater()
        if self.hair_panel is not None and hasattr(self, "hair_page_layout"):
            self.hair_page_layout.removeWidget(self.hair_panel)
            self.hair_panel.deleteLater()
            self.hair_panel = HairPanel(self._loomis_model(), self.schedule_update, self)
            self.hair_page_layout.insertWidget(0, self.hair_panel)
        if hasattr(self, "transform_page_layout"):
            old = getattr(self, "transform_group", None)
            if old is not None:
                self.transform_page_layout.removeWidget(old)
                old.deleteLater()
            self.transform_group = self._build_transform_panel()
            self.transform_page_layout.insertWidget(0, self.transform_group)
        if self.model_label is not None:
            self.model_label.setText(t("model.label"))
        if self.model_combo is not None:
            self.model_combo.blockSignals(True)
            for index in range(self.model_combo.count()):
                model_id = self.model_combo.itemData(index)
                if model_id:
                    self.model_combo.setItemText(index, t("model." + str(model_id)))
            self.model_combo.blockSignals(False)
        self.ui.featuresButton.hide()
        self._sync_panels_for_model()
        self._sync_ui_from_model()
        self._sync_euler_from_model()

    def _grimorio_file(self) -> Path:
        base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        root = Path(base) if base else Path.home() / ".local" / "share" / "krita"
        candidates = [
            root / "krita" / "grimorio-color" / "grimorio.json",
            root / "grimorio-color" / "grimorio.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _load_characters(self) -> None:
        self._characters = []
        self._heads = {}
        self._active_character = ""
        try:
            raw = json.loads(self._grimorio_file().read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        for item in raw.get("characters", []):
            if isinstance(item, dict) and item.get("id") and item.get("name"):
                cid = str(item["id"])
                self._characters.append((cid, str(item["name"])))
                head = item.get("head")
                if isinstance(head, dict) and head:
                    self._heads[cid] = head
        self._active_character = str(raw.get("activeCharacterId") or "")

    def _grimorio_available(self) -> bool:
        try:
            return self._grimorio_file().exists()
        except OSError:
            return False

    def _refresh_oc_combo(self) -> None:
        combo = self.ui.ocCombo
        available = self._grimorio_available()
        combo.setEnabled(available)
        self.ui.ocSaveButton.setEnabled(available)
        current = combo.currentData() or self._active_character
        combo.blockSignals(True)
        combo.clear()
        if not available:
            combo.addItem(t("status.no_grimorio"), "")
            combo.blockSignals(False)
            return
        combo.addItem(t("combo.oc"), "")
        for cid, name in self._characters:
            combo.addItem(name, cid)
        index = combo.findData(current) if current else -1
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _on_oc_activated(self, index: int) -> None:
        cid = self.ui.ocCombo.itemData(index)
        data = (self._heads.get(cid) or self._presets.get("characters", {}).get(cid)) if cid else None
        if isinstance(data, dict):
            self.apply_preset(data)
            self.ui.presetStatus.setText(t("status.loaded_oc", name=self.ui.ocCombo.currentText()))
        elif cid:
            self.ui.presetStatus.setText(t("status.no_oc_preset", name=self.ui.ocCombo.currentText()))

    def _write_head_to_grimorio(self, character_id: str, data: dict) -> bool:
        """Escribe solo character.head en grimorio.json; conserva el resto."""
        path = self._grimorio_file()
        if not path.exists():
            return False
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if not isinstance(raw, dict):
            return False
        target = None
        for item in raw.get("characters", []):
            if isinstance(item, dict) and item.get("id") == character_id:
                target = item
                break
        if target is None:
            return False
        target["head"] = data
        backup = path.with_name(path.name + ".loomis.bak")
        temp = path.with_name(path.name + ".loomis.tmp")
        try:
            if not backup.exists():
                backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            temp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, path)
        except OSError:
            return False
        return True

    def _save_to_character(self) -> None:
        if not self._grimorio_available():
            self.ui.presetStatus.setText(t("status.no_grimorio"))
            return
        cid = self.ui.ocCombo.currentData()
        if not cid:
            self.ui.presetStatus.setText(t("status.choose_oc"))
            return
        data = self._capture_preset()
        self._presets.setdefault("characters", {})[cid] = data
        self._write_presets()
        self._heads[cid] = data
        wrote_json = self._write_head_to_grimorio(cid, data)
        key = "status.saved_oc_json" if wrote_json else "status.saved_oc_sidecar"
        self.ui.presetStatus.setText(t(key, name=self.ui.ocCombo.currentText()))

    def _on_preset_activated(self, name: str) -> None:
        data = self._presets.get("presets", {}).get(name)
        if isinstance(data, dict):
            self.apply_preset(data)
            self.ui.presetStatus.setText(t("status.loaded", name=name))

    def _doc_size(self):
        doc = Krita.instance().activeDocument() or self.doc
        if not doc:
            return None, 0, 0
        try:
            return doc, doc.width(), doc.height()
        except (AttributeError, RuntimeError):
            return None, 0, 0

    def _capture_preset(self) -> dict:
        data = self.loomis_head.to_dict()
        doc, width, height = self._doc_size()
        if doc and width and height:
            data["positionX"] = self.loomis_head.position_x / width
            data["positionY"] = self.loomis_head.position_y / height
            data["positionUnit"] = "normalized"
        else:
            data["positionUnit"] = "pixels"
        return data

    def _save_preset(self) -> None:
        name = self.ui.presetCombo.currentText().strip() or "Preset"
        self._presets.setdefault("presets", {})[name] = self._capture_preset()
        self._write_presets()
        self._refresh_presets(name)
        self.ui.presetStatus.setText(t("status.saved", name=name))

    def _delete_preset(self) -> None:
        name = self.ui.presetCombo.currentText().strip()
        presets = self._presets.get("presets", {})
        if name in presets:
            del presets[name]
            self._write_presets()
            self._refresh_presets("")
            self.ui.presetStatus.setText(t("status.deleted", name=name))
        else:
            self.ui.presetStatus.setText(t("status.missing", name=name))

    def apply_preset(self, data: dict) -> None:
        data = data if isinstance(data, dict) else {}
        target = str(data.get("model") or self._current_model_id() or DEFAULT_MODEL).strip().lower()
        if target not in supported_models():
            target = self._current_model_id()
        if target != self._current_model_id():
            self._switch_model(target)
        self.loomis_head.from_dict(data)
        doc, width, height = self._doc_size()
        normalized = data.get("positionUnit") == "normalized"
        nx = float(data.get("positionX", 0.5)) if normalized else 0.5
        ny = float(data.get("positionY", 0.5)) if normalized else 0.5
        if doc and width and height and self.loomis_layer is not None:
            self.loomis_head.set_position_x(nx * width)
            self.loomis_head.set_position_y(ny * height)
            self._pending_position = None
        else:
            self._pending_position = (nx, ny)
        self.trackball.set_quaternion(self.loomis_head.q)
        self._sync_ui_from_model()
        self._sync_euler_from_model()
        self._sync_panels_for_model()
        self.schedule_update()

    def _sync_ui_from_model(self) -> None:
        if self.loomis_head is None:
            return
        blockers = []

        def put(widget, value):
            blockers.append(QSignalBlocker(widget))
            widget.setValue(value)

        put(self.ui.sizeSlider, round(self.loomis_head.scale * 100))
        put(self.ui.sideCutSlider, round(self.loomis_head.side_cut * 100))
        put(self.ui.faceAgeSlider, round(self.loomis_head.face_age * 100))
        put(self.ui.chinWidthSlider, round(self.loomis_head.chin_width * 100))
        put(self.ui.frontStrokeSlider, round(self.loomis_head.front_line_stroke))
        put(self.ui.backStrokeSlider, round(self.loomis_head.back_line_stroke))
        put(self.ui.positionXSpinBox, round(self.loomis_head.position_x))
        put(self.ui.positionYSpinBox, round(self.loomis_head.position_y))
        for widget, value in (
            (self.ui.showFace, self.loomis_head.show_face),
            (self.ui.showArrow, self.loomis_head.show_arrow),
            (self.ui.zoneColors, self.loomis_head.use_zone_colors),
            (self.ui.showSilhouette, self.loomis_head.show_silhouette),
            (self.ui.showSideRims, self.loomis_head.show_side_rims),
            (self.ui.showSideCross, self.loomis_head.show_side_cross),
        ):
            blockers.append(QSignalBlocker(widget))
            widget.setChecked(value)
        self.ui.strokeColorSwatch.setStyleSheet(
            f"background-color: {self.loomis_head.stroke_color}; border: 1px solid #666;")
        del blockers
        self._sync_transform_sliders()

    def _apply_view(self, index: int) -> None:
        views = ((0.0, 0.0), (0.55, 0.0), (math.pi / 2, 0.0), (math.pi, 0.0), (0.0, -0.9))
        if not 0 <= index < len(views):
            return
        yaw, pitch = views[index]
        q = q_mul(q_axis_angle([0.0, 1.0, 0.0], yaw), q_axis_angle([1.0, 0.0, 0.0], pitch))
        self.loomis_head.set_quaternion(q)
        self.trackball.set_quaternion(q)
        self._sync_euler_from_model()
        self.schedule_update()

    def _on_preview_rotation(self, q) -> None:
        if self.loomis_head is None:
            return
        self.loomis_head.set_quaternion(q)
        self._sync_euler_from_model()
        self.schedule_update()

    def _sync_euler_from_model(self) -> None:
        if self.loomis_head is None:
            return
        yaw, pitch, roll = angles_from_quaternion(self.loomis_head.q)
        for spin, angle in (
            (self.ui.rotXSpin, pitch),
            (self.ui.rotYSpin, yaw),
            (self.ui.rotZSpin, roll),
        ):
            degrees = (math.degrees(angle) + 180.0) % 360.0 - 180.0
            spin.blockSignals(True)
            spin.setValue(round(degrees))
            spin.blockSignals(False)
        self._sync_transform_sliders()

    def _apply_euler(self, *_args) -> None:
        if self.loomis_head is None:
            return
        yaw = math.radians(self.ui.rotYSpin.value())
        pitch = math.radians(self.ui.rotXSpin.value())
        roll = math.radians(self.ui.rotZSpin.value())
        q = quaternion_from_angles(yaw, pitch, roll)
        self.loomis_head.set_quaternion(q)
        self.trackball.set_quaternion(q)
        self._sync_euler_from_model()
        self._sync_transform_sliders()
        self.schedule_update()

    def _set_zone_colors(self, enabled: bool) -> None:
        self.loomis_head.set_zone_colors(enabled)
        self.schedule_update()

    def _load_head_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("file.load_title"), str(Path.home()), t("file.filter"))
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.ui.presetStatus.setText(t("error.bad_head"))
            return
        if not isinstance(raw, dict):
            self.ui.presetStatus.setText(t("error.bad_head"))
            return
        data = raw.get("head") if isinstance(raw.get("head"), dict) else raw
        if not isinstance(data, dict) or ("head" not in raw and "scale" not in data):
            self.ui.presetStatus.setText(t("error.bad_head"))
            return
        model = str(
            raw.get("model") or data.get("model")
            or raw.get("generator") or data.get("generator") or DEFAULT_MODEL
        ).strip().lower()
        # Nombres antiguos del generador que siguen significando Loomis.
        if model in ("", "loomis-head", "loomis method head guide"):
            model = DEFAULT_MODEL
        if create_model(model) is None:
            self.ui.presetStatus.setText(t("error.model_unknown", model=model))
            return
        data = dict(data)
        data["model"] = model
        self.apply_preset(data)
        self.ui.presetStatus.setText(t("status.head_loaded", name=Path(path).name))

    def _export_head_file(self) -> None:
        name = self.ui.presetCombo.currentText().strip() or "loomis-head"
        suggested = str(Path.home() / f"{name}.json")
        path, _ = QFileDialog.getSaveFileName(
            self, t("file.save_title"), suggested, t("file.filter"))
        if not path:
            return
        head = self._capture_preset()
        model_id = str(head.get("model") or DEFAULT_MODEL)
        wrapper = {
            "format": "loomis-head",
            "version": 1,
            "model": model_id,
            "generator": str(head.get("generator") or model_id),
            "name": name,
            "author": "",
            "license": "",
            "tags": [],
            "head": head,
        }
        try:
            Path(path).write_text(json.dumps(wrapper, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.ui.presetStatus.setText(t("error.bad_head"))
            return
        self.ui.presetStatus.setText(t("status.head_saved", name=Path(path).name))

    def save_head(self):
        """
        Redrawing the head with higher accuracy.
        Can't test it on low end devices, so I may need to tone it down. 
        """

        samples = 256; """Default samples"""
        samples *= 4; """Higher rendering pass"""

        self.draw_lines_with_vectors(samples)
        self._save_doc_state()
        self.ui.presetStatus.setText(t("status.applied"))
        self.close()


class LoomisHeadPlugin(Extension):
    def __init__(self, parent):
        super().__init__(parent)

    def setup(self):
        # Los dockers se registran en setup(), no al importar el paquete.
        log_path = None
        try:
            base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            log_dir = Path(base or ".") / "loomis_head"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "setup.log"
            Krita.instance().addDockWidgetFactory(
                DockWidgetFactory(
                    "loomis_head",
                    DockWidgetFactoryBase.DockPosition.DockRight,
                    LoomisProportionsDocker,
                )
            )
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("docker registered\n")
        except Exception:
            import traceback
            if log_path is not None:
                try:
                    with log_path.open("a", encoding="utf-8") as handle:
                        handle.write(traceback.format_exc() + "\n")
                except OSError:
                    pass
            raise

    def createActions(self, window):
        # Sin accion en Tools: el docker se abre desde Settings > Dockers.
        pass
