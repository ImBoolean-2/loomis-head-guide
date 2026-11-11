# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Paneles de rasgos, pelo y planos Asaro del Loomis Head Guide.

Se separan en widgets (rasgos, pelo y Asaro) para que el docker pueda mostrarlos
en pestanas independientes. Todos trabajan sobre el modelo activo y comparten
el callback de redibujo.
"""
from __future__ import annotations

from .qt_compat import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
    Qt,
    activated_index,
)

from .i18n import t


HEAD_TYPES = (
    ("headtype.realistic", dict(cranium=1.0, jaw_taper=1.0, cheek=0.2, face_width=1.0,
                                jaw_drop=1.0, eye_line=0.50, nose_line=0.32, mouth_line=0.18,
                                eye_size=0.11, eye_gap=0.42,
                                forehead_height=1.0, jaw_angle=0.30, cranium_width=1.0,
                                cranium_height=1.0, cheekbone_height=0.50,
                                chin_sharpness=0.0)),
    ("headtype.semi", dict(cranium=1.05, jaw_taper=0.9, cheek=0.35, face_width=1.0,
                           jaw_drop=0.95, eye_line=0.48, nose_line=0.31, mouth_line=0.17,
                           eye_size=0.12, eye_gap=0.43,
                           forehead_height=1.0, jaw_angle=0.40, cranium_width=1.02,
                           cranium_height=1.02, cheekbone_height=0.50,
                           chin_sharpness=0.10)),
    ("headtype.anime", dict(cranium=1.12, jaw_taper=0.7, cheek=0.5, face_width=0.97,
                            jaw_drop=0.8, eye_line=0.46, nose_line=0.30, mouth_line=0.16,
                            eye_size=0.14, eye_gap=0.44,
                            forehead_height=0.95, jaw_angle=0.25, cranium_width=1.08,
                            cranium_height=1.05, cheekbone_height=0.55,
                            chin_sharpness=0.60)),
    ("headtype.chibi", dict(cranium=1.3, jaw_taper=0.55, cheek=0.7, face_width=0.92,
                            jaw_drop=0.65, eye_line=0.42, nose_line=0.28, mouth_line=0.14,
                            eye_size=0.18, eye_gap=0.5,
                            forehead_height=1.05, jaw_angle=0.15, cranium_width=1.15,
                            cranium_height=1.12, cheekbone_height=0.60,
                            chin_sharpness=0.0)),
    ("headtype.caricature", dict(cranium=1.25, jaw_taper=0.6, cheek=0.8, face_width=0.95,
                                 jaw_drop=0.75, eye_line=0.44, nose_line=0.29, mouth_line=0.15,
                                 eye_size=0.15, eye_gap=0.46,
                                 forehead_height=1.0, jaw_angle=0.50, cranium_width=1.10,
                                 cranium_height=1.10, cheekbone_height=0.75,
                                 chin_sharpness=0.20)),
)


# Presets de sexo: se aplican encima del estilo de cabeza. El indice es
# head_sex (0 masculino, 1 femenino).
SEX_PRESETS = (
    dict(brow_ridge=0.80, eye_socket_depth=0.75, eye_socket_size=0.50,
         cheek_fullness=0.35, cheek=0.55, jaw_angle=0.55,
         chin_sharpness=0.20, forehead_height=0.95),
    dict(brow_ridge=0.35, eye_socket_depth=0.45, eye_socket_size=0.60,
         cheek_fullness=0.65, cheek=0.65, jaw_angle=0.25,
         chin_sharpness=0.10, forehead_height=1.05),
)


class _ModelPanel(QWidget):
    """Base para paneles que cambian de modelo (varias cabezas/documentos)."""

    def __init__(self, model, on_change, parent=None):
        super().__init__(parent)
        self.model = model
        self.on_change = on_change
        self._syncing = False
        self._sliders: list[tuple[QSlider, object]] = []
        self._form: QFormLayout | None = None

    def set_model(self, model) -> None:
        self.model = model
        self.sync_from_model()

    def _section(self, text: str) -> None:
        if self._form is not None:
            self._form.addRow(QLabel(f"<b>{text}</b>"))

    def _slider(self, label, low, high, getter, setter) -> None:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.setValue(int(round(getter())))
        slider.valueChanged.connect(lambda value: self._apply(setter, value))
        if self._form is not None:
            self._form.addRow(label, slider)
        self._sliders.append((slider, getter))

    def _slider_field(self, label, low, high, attr, default, scale=100.0) -> None:
        """Slider ligado a un campo del modelo que puede no existir todavia.

        Getter y setter se resuelven en cada llamada sobre self.model, de modo
        que cambiar de cabeza (set_model) escribe en el modelo activo y no en el
        que existia al construir el panel. Si el generador aun no tiene el campo,
        se usa `default` al leer y el setter se omite al escribir.
        """

        def getter():
            return float(getattr(self.model, attr, default)) * scale

        def setter(value):
            fn = getattr(self.model, "set_" + attr, None)
            if fn is not None:
                fn(value / scale)

        self._slider(label, low, high, getter, setter)

    def _apply(self, setter, value) -> None:
        if self._syncing:
            return
        setter(value)
        self.on_change()

    def sync_from_model(self) -> None:
        self._syncing = True
        for slider, getter in self._sliders:
            slider.setValue(int(round(getter())))
        self._syncing = False


class FeaturePanel(_ModelPanel):
    """Tipo de cabeza, caricatura, lineas de Loomis y rasgos dibujados."""

    def __init__(self, model, on_change, parent=None):
        super().__init__(model, on_change, parent)
        self._flags: list[tuple[QCheckBox, str]] = []
        self._flag_defaults: dict[str, bool] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.master = QCheckBox(t("features.master"))
        self.master.toggled.connect(self._set_master)
        outer.addWidget(self.master)

        self._form = QFormLayout()
        outer.addLayout(self._form)

        self.type_combo = QComboBox()
        for key, _ in HEAD_TYPES:
            self.type_combo.addItem(t(key))
        activated_index(self.type_combo).connect(self._apply_type)
        self._form.addRow(t("headtype.label"), self.type_combo)

        self.sex_combo = QComboBox()
        self.sex_combo.addItem(t("features.sex.male"))
        self.sex_combo.addItem(t("features.sex.female"))
        activated_index(self.sex_combo).connect(self._apply_sex)
        self._form.addRow(t("features.sex"), self.sex_combo)

        self._section(t("features.section.caricature"))
        self._slider(t("features.cranium"), 60, 160, lambda: self.model.cranium * 100, lambda v: self.model.set_cranium(v / 100))
        self._slider(t("features.jaw_taper"), 40, 160, lambda: self.model.jaw_taper * 100, lambda v: self.model.set_jaw_taper(v / 100))
        self._slider(t("features.cheek"), 0, 100, lambda: self.model.cheek * 100, lambda v: self.model.set_cheek(v / 100))
        self._slider(t("features.face_width"), 60, 140, lambda: self.model.face_width * 100, lambda v: self.model.set_face_width(v / 100))
        self._slider(t("features.jaw_drop"), 60, 140, lambda: self.model.jaw_drop * 100, lambda v: self.model.set_jaw_drop(v / 100))

        self._section(t("features.section.proportions"))
        self._slider(t("features.forehead_height"), 60, 140, lambda: self.model.forehead_height * 100, lambda v: self.model.set_forehead_height(v / 100))
        self._slider(t("features.jaw_angle"), 0, 100, lambda: self.model.jaw_angle * 100, lambda v: self.model.set_jaw_angle(v / 100))
        self._slider(t("features.cranium_width"), 80, 120, lambda: self.model.cranium_width * 100, lambda v: self.model.set_cranium_width(v / 100))
        self._slider(t("features.cranium_height"), 80, 120, lambda: self.model.cranium_height * 100, lambda v: self.model.set_cranium_height(v / 100))
        self._slider(t("features.cheekbone_height"), 0, 100, lambda: self.model.cheekbone_height * 100, lambda v: self.model.set_cheekbone_height(v / 100))

        self._section(t("features.section.style"))
        self._slider(t("features.chin_sharpness"), 0, 100, lambda: self.model.chin_sharpness * 100, lambda v: self.model.set_chin_sharpness(v / 100))
        self._add_flag_row(None, ((t("features.rhythm"), "show_rhythm"),))
        self._slider(t("features.rhythm_strength"), 0, 100, lambda: self.model.rhythm_strength * 100, lambda v: self.model.set_rhythm_strength(v / 100))

        self._section(t("features.section.lines"))
        self._slider(t("features.brow_line"), 40, 80, lambda: self.model.brow_line * 100, lambda v: self.model.set_brow_line(v / 100))
        self._slider(t("features.eye_line"), 35, 65, lambda: self.model.eye_line * 100, lambda v: self.model.set_eye_line(v / 100))
        self._slider(t("features.nose_line"), 15, 45, lambda: self.model.nose_line * 100, lambda v: self.model.set_nose_line(v / 100))
        self._slider(t("features.mouth_line"), 5, 30, lambda: self.model.mouth_line * 100, lambda v: self.model.set_mouth_line(v / 100))
        self._add_flag_row(t("features.guides"), (
            (t("features.guide_brow"), "show_brow_guide"),
            (t("features.guide_eye"), "show_eye_guide"),
            (t("features.guide_nose"), "show_nose_guide"),
            (t("features.guide_mouth"), "show_mouth_guide"),
        ))

        self._section(t("features.section.features"))
        self._slider(t("features.eye_gap"), 10, 90, lambda: self.model.eye_gap * 100, lambda v: self.model.set_eye_gap(v / 100))
        self._slider(t("features.eye_size"), 2, 30, lambda: self.model.eye_size * 100, lambda v: self.model.set_eye_size(v / 100))
        self._slider(t("features.brow_height"), 0, 20, lambda: self.model.brow_height * 100, lambda v: self.model.set_brow_height(v / 100))
        self._slider(t("features.nose_length"), 2, 35, lambda: self.model.nose_length * 100, lambda v: self.model.set_nose_length(v / 100))
        self._slider(t("features.nose_width"), 5, 50, lambda: self.model.nose_width * 100, lambda v: self.model.set_nose_width(v / 100))
        self._slider(t("features.ear_size"), 2, 40, lambda: self.model.ear_size * 100, lambda v: self.model.set_ear_size(v / 100))
        self._slider(t("features.ear_height"), 20, 80, lambda: self.model.ear_height * 100, lambda v: self.model.set_ear_height(v / 100))
        self._slider(t("features.mouth_width"), 5, 60, lambda: self.model.mouth_width * 100, lambda v: self.model.set_mouth_width(v / 100))
        self._slider(t("features.mouth_curve"), -15, 15, lambda: self.model.mouth_curve * 100, lambda v: self.model.set_mouth_curve(v / 100))

        self._add_flag_row(t("features.show"), (
            (t("features.eyes"), "show_eyes"),
            (t("features.brows"), "show_brows"),
            (t("features.nose"), "show_nose"),
            (t("features.ears"), "show_ears"),
            (t("features.mouth"), "show_mouth"),
        ))

        self._section(t("features.section.eye"))
        self._add_flag_row(None, (
            (t("features.eye_socket"), "show_eye_socket"),
        ), defaults={"show_eye_socket": True})
        self._slider_field(t("features.eye_socket_depth"), 0, 100,
                           "eye_socket_depth", 0.5)
        self._slider_field(t("features.eye_socket_size"), 20, 90,
                           "eye_socket_size", 0.55)
        self._slider_field(t("features.brow_ridge"), 0, 100, "brow_ridge", 0.5)
        self._slider_field(t("features.cheek_fullness"), 0, 100,
                           "cheek_fullness", 0.5)

        self.sync_from_model()

    def _add_flag_row(self, label, items, defaults=None) -> None:
        defaults = defaults or {}
        box = QWidget()
        layout = QHBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        for text, attr in items:
            default = bool(defaults.get(attr, False))
            self._flag_defaults[attr] = default
            checkbox = QCheckBox(text)
            checkbox.setChecked(bool(getattr(self.model, attr, default)))
            # El setter se resuelve en tiempo de llamada: al cambiar de cabeza
            # (set_model) los checkboxes deben escribir en el modelo activo,
            # no en el que existia al construir el panel.
            checkbox.toggled.connect(lambda checked, name=attr: self._apply_flag(name, checked))
            layout.addWidget(checkbox)
            self._flags.append((checkbox, attr))
        if label is None:
            self._form.addRow(box)
        else:
            self._form.addRow(label, box)

    def _apply_flag(self, attr: str, checked: bool) -> None:
        if self._syncing:
            return
        setter = getattr(self.model, "set_" + attr, None)
        if setter is not None:
            setter(checked)
        self.on_change()

    def _set_master(self, checked: bool) -> None:
        if self._syncing:
            return
        self.model.set_show_features(checked)
        self.on_change()

    def _apply_type(self, index: int) -> None:
        if not 0 <= index < len(HEAD_TYPES):
            return
        params = HEAD_TYPES[index][1]
        # Si un preset no trae una clave, o el modelo no tiene su setter,
        # se omite en vez de fallar: los presets y el modelo evolucionan aparte.
        for key, value in params.items():
            setter = getattr(self.model, "set_" + key, None)
            if setter is not None:
                setter(value)
        # El estilo define la base; el sexo elegido se reaplica encima para que
        # cambiar de tipo de cabeza no borre la eleccion.
        self._apply_sex_preset(self.sex_combo.currentIndex())
        self.on_change()
        self.sync_from_model()

    def _apply_sex(self, index: int) -> None:
        if not 0 <= index < len(SEX_PRESETS):
            return
        self._apply_sex_preset(index)
        self.on_change()
        self.sync_from_model()

    def _apply_sex_preset(self, index: int) -> None:
        if not 0 <= index < len(SEX_PRESETS):
            return
        setter = getattr(self.model, "set_head_sex", None)
        if setter is not None:
            setter(index)
        for key, value in SEX_PRESETS[index].items():
            fn = getattr(self.model, "set_" + key, None)
            if fn is not None:
                fn(value)

    def sync_from_model(self) -> None:
        self._syncing = True
        self.master.setChecked(bool(self.model.show_features))
        self.type_combo.setCurrentIndex(self._type_index())
        # Si el modelo aun no tiene head_sex se conserva la eleccion del combo.
        sex = getattr(self.model, "head_sex", self.sex_combo.currentIndex())
        try:
            sex = int(sex)
        except (TypeError, ValueError):
            sex = self.sex_combo.currentIndex()
        self.sex_combo.setCurrentIndex(max(0, min(sex, self.sex_combo.count() - 1)))
        for slider, getter in self._sliders:
            slider.setValue(int(round(getter())))
        for checkbox, attr in self._flags:
            default = self._flag_defaults.get(attr, False)
            checkbox.setChecked(bool(getattr(self.model, attr, default)))
        self._syncing = False

    def _type_index(self) -> int:
        # No hay un tipo "activo" guardado: se mantiene el que el usuario eligio.
        return self.type_combo.currentIndex() if self.type_combo.count() else 0


class HairPanel(_ModelPanel):
    """Pelo parametrico: linea, arco, inclinacion, raya, patron y textura."""

    def __init__(self, model, on_change, parent=None):
        super().__init__(model, on_change, parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.master = QCheckBox(t("hair.show"))
        self.master.toggled.connect(self._set_master)
        outer.addWidget(self.master)

        self._form = QFormLayout()
        outer.addLayout(self._form)

        self._section(t("hair.section"))
        self._slider(t("hair.line"), 55, 85, lambda: self.model.hair_line * 100, lambda v: self.model.set_hair_line(v / 100))
        self._slider(t("hair.arch"), 0, 20, lambda: self.model.hair_arch * 100, lambda v: self.model.set_hair_arch(v / 100))
        self._slider(t("hair.tilt"), -20, 20, lambda: self.model.hair_tilt * 100, lambda v: self.model.set_hair_tilt(v / 100))
        self._slider(t("hair.part_pos"), -100, 100, lambda: self.model.hair_part_pos * 100, lambda v: self.model.set_hair_part_pos(v / 100))

        self.part_combo = QComboBox()
        for key in ("hair.straight", "hair.zigzag", "hair.spiky"):
            self.part_combo.addItem(t(key))
        activated_index(self.part_combo).connect(self._set_part)
        self._form.addRow(t("hair.part"), self.part_combo)

        self.texture_combo = QComboBox()
        for key in ("hair.smooth", "hair.wavy", "hair.texture_spiky", "hair.curly"):
            self.texture_combo.addItem(t(key))
        activated_index(self.texture_combo).connect(self._set_texture)
        self._form.addRow(t("hair.texture"), self.texture_combo)

        self.sync_from_model()

    def _set_master(self, checked: bool) -> None:
        if self._syncing:
            return
        self.model.set_show_hair(checked)
        self.on_change()

    def _set_part(self, index: int) -> None:
        if self._syncing:
            return
        self.model.set_hair_part(index)
        self.on_change()

    def _set_texture(self, index: int) -> None:
        if self._syncing:
            return
        self.model.set_hair_texture(index)
        self.on_change()

    def sync_from_model(self) -> None:
        self._syncing = True
        self.master.setChecked(bool(self.model.show_hair))
        self.part_combo.setCurrentIndex(int(self.model.hair_part))
        self.texture_combo.setCurrentIndex(int(self.model.hair_texture))
        for slider, getter in self._sliders:
            slider.setValue(int(round(getter())))
        self._syncing = False


class AsaroPanel(_ModelPanel):
    """Planos, aristas y nivel de detalle de la cabeza Asaro."""

    def __init__(self, model, on_change, parent=None):
        super().__init__(model, on_change, parent)
        self._flags: list[tuple[QCheckBox, str, bool]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._form = QFormLayout()
        outer.addLayout(self._form)

        self.planes_check = self._add_flag(t("asaro.show_planes"), "show_planes", True)
        # Sombrear planos es opcional: si el modelo aun no tiene el campo se
        # muestra activado y el setter se omite hasta que exista.
        self.shade_planes_check = self._add_flag(
            t("asaro.shade_planes"), "shade_planes", True)
        self.edges_check = self._add_flag(t("asaro.show_edges"), "show_edges", True)
        self.neck_check = self._add_flag(t("asaro.show_neck"), "show_neck", True)

        self.detail_combo = QComboBox()
        for key, level in (
            ("asaro.detail.low", 0),
            ("asaro.detail.medium", 1),
            ("asaro.detail.high", 2),
        ):
            self.detail_combo.addItem(t(key), level)
        activated_index(self.detail_combo).connect(self._apply_detail)
        self._form.addRow(t("asaro.detail"), self.detail_combo)

        self.sync_from_model()

    def _add_flag(self, text: str, attr: str, default: bool) -> QCheckBox:
        checkbox = QCheckBox(text)
        checkbox.setChecked(bool(getattr(self.model, attr, default)))
        # Setter en tiempo de llamada: al cambiar de modelo (set_model) el
        # checkbox escribe en el modelo activo y no en el de construccion.
        checkbox.toggled.connect(lambda checked, name=attr: self._apply_flag(name, checked))
        self._form.addRow(checkbox)
        self._flags.append((checkbox, attr, default))
        return checkbox

    def _apply_flag(self, attr: str, checked: bool) -> None:
        if self._syncing:
            return
        setter = getattr(self.model, "set_" + attr, None)
        if setter is not None:
            setter(checked)
        self.on_change()

    def _apply_detail(self, index: int) -> None:
        if self._syncing:
            return
        level = self.detail_combo.itemData(index)
        if level is None:
            level = index
        setter = getattr(self.model, "set_detail", None)
        if setter is not None:
            setter(int(level))
        self.on_change()

    def sync_from_model(self) -> None:
        self._syncing = True
        for checkbox, attr, default in self._flags:
            checkbox.setChecked(bool(getattr(self.model, attr, default)))
        try:
            detail = int(getattr(self.model, "detail", 1))
        except (TypeError, ValueError):
            detail = 1
        index = self.detail_combo.findData(max(0, min(detail, 2)))
        self.detail_combo.setCurrentIndex(index if index >= 0 else 1)
        self._syncing = False
