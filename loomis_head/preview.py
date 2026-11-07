# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Previsualizacion 3D de la cabeza con arcball (sin OpenGL)."""
from __future__ import annotations

import copy
import math

from PyQt5.QtCore import QByteArray, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QWidget

from .euclid import Vector3
from .linalg import q_axis_angle, q_identity, q_mul, q_normalize


class HeadPreviewWidget(QWidget):
    """Muestra la cabeza y la rota con el raton.

    - Arrastrar: orbita libre (arcball, 3 ejes de rotacion).
    - Shift + arrastrar o boton derecho: roll alrededor del eje de vision.
    - Rueda: zoom de la previsualizacion (no cambia la escala de la guia).
    - Doble clic: vuelve a la vista frontal.
    """

    orientation_changed = pyqtSignal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._q = q_identity()
        self._zoom = 1.0
        self._start = None
        self._q_start = None
        self._roll = False
        self.setMinimumSize(220, 220)
        self.setCursor(Qt.OpenHandCursor)

    def set_model(self, model) -> None:
        self.model = model
        self.update()

    def set_quaternion(self, q) -> None:
        self._q = q_normalize(q)
        self.update()

    def reset(self, emit: bool = True) -> None:
        self._q = q_identity()
        if emit:
            self.orientation_changed.emit(self._q)
        self.update()

    def _project(self, x: float, y: float) -> Vector3:
        width, height = max(1, self.width()), max(1, self.height())
        radius = 0.45 * min(width, height)
        vx = (x - width * 0.5) / radius
        vy = (height * 0.5 - y) / radius
        d2 = vx * vx + vy * vy
        if d2 <= 1.0:
            vz = math.sqrt(max(0.0, 1.0 - d2))
        else:
            # Hoja hiperbolica: fuera de la esfera el giro sigue siendo estable.
            scale = 1.0 / math.sqrt(d2)
            vx, vy, vz = vx * scale, vy * scale, 0.0
        return Vector3(vx, vy, vz)

    @staticmethod
    def _rotation(v0: Vector3, v1: Vector3):
        ax = v0.y * v1.z - v0.z * v1.y
        ay = v0.z * v1.x - v0.x * v1.z
        az = v0.x * v1.y - v0.y * v1.x
        dot = max(-1.0, min(1.0, v0.x * v1.x + v0.y * v1.y + v0.z * v1.z))
        if ax * ax + ay * ay + az * az < 1e-10 or dot > 0.999999:
            return q_identity()
        return q_axis_angle([ax, ay, az], math.acos(dot))

    def mousePressEvent(self, event) -> None:
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._start = event.pos()
            self._q_start = self._q
            self._roll = bool(event.button() == Qt.RightButton or event.modifiers() & Qt.ShiftModifier)
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._start is None or self._q_start is None:
            super().mouseMoveEvent(event)
            return
        if self._roll:
            angle = (event.x() - self._start.x()) * 0.01
            delta = q_axis_angle([0.0, 0.0, 1.0], angle)
        else:
            v0 = self._project(self._start.x(), self._start.y())
            v1 = self._project(event.x(), event.y())
            delta = self._rotation(v0, v1)
        self._q = q_normalize(q_mul(delta, self._q_start))
        self.orientation_changed.emit(self._q)
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._start = None
        self._q_start = None
        self.setCursor(Qt.OpenHandCursor)
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        self.reset()
        event.accept()

    def wheelEvent(self, event) -> None:
        step = 1.1 if event.angleDelta().y() > 0 else 0.9
        self._zoom = max(0.6, min(1.6, self._zoom * step))
        self.update()
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(127, 127, 127, 18))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 10, 10)

        width, height = self.width(), self.height()
        if width < 8 or height < 8:
            painter.end()
            return

        preview = copy.deepcopy(self.model)
        preview.set_position_x(width * 0.5)
        preview.set_position_y(height * 0.5)
        preview.set_scale(1.05 * self._zoom)
        preview.set_front_line_stroke(2.0)
        preview.set_back_line_stroke(1.4)
        preview.set_quaternion(self._q)
        svg = preview.build_svg(width, height, samples=64)
        svg = svg.replace(
            '<svg xmlns="http://www.w3.org/2000/svg">',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">',
            1,
        )
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if renderer.isValid():
            renderer.render(painter)
        painter.end()
