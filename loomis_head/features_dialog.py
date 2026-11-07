# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Panel de rasgos, caricatura y pelo del Loomis Head Guide.

Se incrusta en el docker (no abre una ventana aparte) y trabaja sobre el modelo
activo. El contenedor con scroll es el panel principal.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .i18n import t


HEAD_TYPES = (
    ("headtype.realistic", dict(cranium=1.0, jaw_taper=1.0, cheek=0.2, face_width=1.0,
                                jaw_drop=1.0, eye_line=0.50, nose_line=0.32, mouth_line=0.18,
                                eye_size=0.11, eye_gap=0.42)),
    ("headtype.semi", dict(cranium=1.05, jaw_taper=0.9, cheek=0.35, face_width=1.0,
                           jaw_drop=0.95, eye_line=0.48, nose_line=0.31, mouth_line=0.17,
                           eye_size=0.12, eye_gap=0.43)),
    ("headtype.anime", dict(cranium=1.12, jaw_taper=0.7, cheek=0.5, face_width=0.97,
                            jaw_drop=0.8, eye_line=0.46, nose_line=0.30, mouth_line=0.16,
                            eye_size=0.14, eye_gap=0.44)),
    ("headtype.chibi", dict(cranium=1.3, jaw_taper=0.55, cheek=0.7, face_width=0.92,
                            jaw_drop=0.65, eye_line=0.42, nose_line=0.28, mouth_line=0.14,
                            eye_size=0.18, eye_gap=0.5)),
    ("headtype.caricature", dict(cranium=1.25, jaw_taper=0.6, cheek=0.8, face_width=0.95,
                                 jaw_drop=0.75, eye_line=0.44, nose_line=0.29, mouth_line=0.15,
                                 eye_size=0.15, eye_gap=0.46)),
)


class FeaturePanel(QWidget):
    def __init__(self, model, on_change, parent=None):
        super().__init__(parent)
        self.model = model
        self.on_change = on_change
        self._syncing = False
        self._sliders: list[tuple[QSlider, object]] = []
        self._flags: list[tuple[QCheckBox, object]] = []

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
        self.type_combo.activated[int].connect(self._apply_type)
        self._form.addRow(t("headtype.label"), self.type_combo)

        self._section(t("features.section.caricature"))
        self._slider(t("features.cranium"), 60, 160, lambda: self.model.cranium * 100, lambda v: self.model.set_cranium(v / 100))
        self._slider(t("features.jaw_taper"), 40, 160, lambda: self.model.jaw_taper * 100, lambda v: self.model.set_jaw_taper(v / 100))
        self._slider(t("features.cheek"), 0, 100, lambda: self.model.cheek * 100, lambda v: self.model.set_cheek(v / 100))
        self._slider(t("features.face_width"), 60, 140, lambda: self.model.face_width * 100, lambda v: self.model.set_face_width(v / 100))
        self._slider(t("features.jaw_drop"), 60, 140, lambda: self.model.jaw_drop * 100, lambda v: self.model.set_jaw_drop(v / 100))

        self._section(t("features.section.lines"))
        self._slider(t("features.brow_line"), 40, 80, lambda: self.model.brow_line * 100, lambda v: self.model.set_brow_line(v / 100))
        self._slider(t("features.eye_line"), 35, 65, lambda: self.model.eye_line * 100, lambda v: self.model.set_eye_line(v / 100))
        self._slider(t("features.nose_line"), 15, 45, lambda: self.model.nose_line * 100, lambda v: self.model.set_nose_line(v / 100))
        self._slider(t("features.mouth_line"), 5, 30, lambda: self.model.mouth_line * 100, lambda v: self.model.set_mouth_line(v / 100))

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

        flags = QWidget()
        flags_layout = QHBoxLayout(flags)
        flags_layout.setContentsMargins(0, 0, 0, 0)
        for text, getter, setter in (
            (t("features.eyes"), lambda: self.model.show_eyes, self.model.set_show_eyes),
            (t("features.brows"), lambda: self.model.show_brows, self.model.set_show_brows),
            (t("features.nose"), lambda: self.model.show_nose, self.model.set_show_nose),
            (t("features.ears"), lambda: self.model.show_ears, self.model.set_show_ears),
            (t("features.mouth"), lambda: self.model.show_mouth, self.model.set_show_mouth),
        ):
            checkbox = QCheckBox(text)
            checkbox.setChecked(bool(getter()))
            checkbox.toggled.connect(lambda checked, s=setter: self._apply(s, checked))
            flags_layout.addWidget(checkbox)
            self._flags.append((checkbox, getter))
        self._form.addRow(t("features.show"), flags)

        self._section(t("hair.section"))
        self.hair_master = QCheckBox(t("hair.show"))
        self.hair_master.toggled.connect(self._set_hair)
        self._form.addRow(self.hair_master)
        self._slider(t("hair.line"), 55, 85, lambda: self.model.hair_line * 100, lambda v: self.model.set_hair_line(v / 100))
        self._slider(t("hair.arch"), 0, 20, lambda: self.model.hair_arch * 100, lambda v: self.model.set_hair_arch(v / 100))
        self._slider(t("hair.tilt"), -20, 20, lambda: self.model.hair_tilt * 100, lambda v: self.model.set_hair_tilt(v / 100))
        self._slider(t("hair.part_pos"), -100, 100, lambda: self.model.hair_part_pos * 100, lambda v: self.model.set_hair_part_pos(v / 100))
        self.hair_part_combo = QComboBox()
        for key in ("hair.straight", "hair.zigzag", "hair.spiky"):
            self.hair_part_combo.addItem(t(key))
        self.hair_part_combo.activated[int].connect(self._set_hair_part)
        self._form.addRow(t("hair.part"), self.hair_part_combo)
        self.hair_texture_combo = QComboBox()
        for key in ("hair.smooth", "hair.wavy", "hair.texture_spiky", "hair.curly"):
            self.hair_texture_combo.addItem(t(key))
        self.hair_texture_combo.activated[int].connect(self._set_hair_texture)
        self._form.addRow(t("hair.texture"), self.hair_texture_combo)

        self.sync_from_model()

    def set_model(self, model) -> None:
        self.model = model
        self.sync_from_model()

    def _section(self, text: str) -> None:
        self._form.addRow(QLabel(f"<b>{text}</b>"))

    def _slider(self, label, low, high, getter, setter) -> None:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.setValue(int(round(getter())))
        slider.valueChanged.connect(lambda value: self._apply(setter, value))
        self._form.addRow(label, slider)
        self._sliders.append((slider, getter))

    def _apply(self, setter, value) -> None:
        if self._syncing:
            return
        setter(value)
        self.on_change()

    def _set_master(self, checked: bool) -> None:
        if self._syncing:
            return
        self.model.set_show_features(checked)
        self.on_change()

    def _set_hair(self, checked: bool) -> None:
        if self._syncing:
            return
        self.model.set_show_hair(checked)
        self.on_change()

    def _set_hair_part(self, index: int) -> None:
        if self._syncing:
            return
        self.model.set_hair_part(index)
        self.on_change()

    def _set_hair_texture(self, index: int) -> None:
        if self._syncing:
            return
        self.model.set_hair_texture(index)
        self.on_change()

    def _apply_type(self, index: int) -> None:
        if not 0 <= index < len(HEAD_TYPES):
            return
        params = HEAD_TYPES[index][1]
        self.model.set_cranium(params["cranium"])
        self.model.set_jaw_taper(params["jaw_taper"])
        self.model.set_cheek(params["cheek"])
        self.model.set_face_width(params["face_width"])
        self.model.set_jaw_drop(params["jaw_drop"])
        self.model.set_eye_line(params["eye_line"])
        self.model.set_nose_line(params["nose_line"])
        self.model.set_mouth_line(params["mouth_line"])
        self.model.set_eye_size(params["eye_size"])
        self.model.set_eye_gap(params["eye_gap"])
        self.on_change()
        self.sync_from_model()

    def sync_from_model(self) -> None:
        self._syncing = True
        self.master.setChecked(bool(self.model.show_features))
        self.hair_master.setChecked(bool(self.model.show_hair))
        self.hair_part_combo.setCurrentIndex(int(self.model.hair_part))
        self.hair_texture_combo.setCurrentIndex(int(self.model.hair_texture))
        for slider, getter in self._sliders:
            slider.setValue(int(round(getter())))
        for checkbox, getter in self._flags:
            checkbox.setChecked(bool(getter()))
        self._syncing = False
