# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Capa de compatibilidad PyQt5 / PyQt6 para Krita 5 y Krita 6.

Krita 5.3.x trae PyQt5; Krita 6 pasa a PyQt6. Los modulos del plugin importan
todo desde aqui y nunca desde ``PyQt5``/``PyQt6`` directamente.

Diferencias que cubre este modulo:

- PyQt6 elimina los enums sin ambito: ``Qt.Horizontal`` deja de existir y hay
  que escribir ``Qt.Orientation.Horizontal``. El objeto ``Qt`` que se exporta
  en PyQt6 mapea los nombres cortos que usa el plugin.
- ``QColor.name(QColor.HexRgb)``: ``HexRgb`` es el formato por defecto en ambas
  versiones, asi que los modulos llaman a ``col.name()``.
- ``QDialog.exec_()`` desaparece en PyQt6 (queda ``exec()``): se usa
  ``exec_dialog(dlg)``.
- ``QSizePolicy.Expanding`` pasa a ``QSizePolicy.Policy.Expanding``: se usa
  ``EXPANDING``.
- Otros enums escopados que aparecen en el codigo (``QStandardPaths``,
  ``QColorDialog``, ``QFrame``, ``QPainter``) se reexportan como subclases con
  el nombre corto, para no tener que tocar esas lineas en los modulos.
"""
from __future__ import annotations

try:  # Krita 5.x
    from PyQt5 import QtCore, QtGui, QtSvg, QtWidgets, uic

    QT6 = False
except ImportError:  # Krita 6.x
    from PyQt6 import QtCore, QtGui, QtSvg, QtWidgets, uic

    QT6 = True

# --- QtCore -----------------------------------------------------------------
QByteArray = QtCore.QByteArray
QDateTime = QtCore.QDateTime
QLocale = QtCore.QLocale
QPointF = QtCore.QPointF
QRect = QtCore.QRect
QSignalBlocker = QtCore.QSignalBlocker
QStandardPaths = QtCore.QStandardPaths
QTimer = QtCore.QTimer
pyqtSignal = QtCore.pyqtSignal

# --- QtGui ------------------------------------------------------------------
QBrush = QtGui.QBrush
QColor = QtGui.QColor
QPainter = QtGui.QPainter
QPen = QtGui.QPen
QTransform = QtGui.QTransform

# --- QtWidgets --------------------------------------------------------------
QCheckBox = QtWidgets.QCheckBox
QColorDialog = QtWidgets.QColorDialog
QComboBox = QtWidgets.QComboBox
QFileDialog = QtWidgets.QFileDialog
QFormLayout = QtWidgets.QFormLayout
QFrame = QtWidgets.QFrame
QGridLayout = QtWidgets.QGridLayout
QGroupBox = QtWidgets.QGroupBox
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QScrollArea = QtWidgets.QScrollArea
QSizePolicy = QtWidgets.QSizePolicy
QSlider = QtWidgets.QSlider
QSpinBox = QtWidgets.QSpinBox
QStackedWidget = QtWidgets.QStackedWidget
QTabWidget = QtWidgets.QTabWidget
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget

# --- QtSvg ------------------------------------------------------------------
QSvgRenderer = QtSvg.QSvgRenderer


class _Qt6Namespace:
    """Nombres cortos de enum que usa el plugin, resueltos a PyQt6 escopado.

    Cualquier otro atributo se delega al ``Qt`` real de PyQt6.
    """

    Horizontal = QtCore.Qt.Orientation.Horizontal
    LeftButton = QtCore.Qt.MouseButton.LeftButton
    RightButton = QtCore.Qt.MouseButton.RightButton
    NoPen = QtCore.Qt.PenStyle.NoPen
    NoBrush = QtCore.Qt.BrushStyle.NoBrush
    OpenHandCursor = QtCore.Qt.CursorShape.OpenHandCursor
    ClosedHandCursor = QtCore.Qt.CursorShape.ClosedHandCursor
    ScrollBarAlwaysOff = QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    ShiftModifier = QtCore.Qt.KeyboardModifier.ShiftModifier

    def __getattr__(self, name):
        try:
            return getattr(QtCore.Qt, name)
        except AttributeError:
            raise AttributeError(f"Qt.{name} no existe en PyQt6") from None


if QT6:

    Qt = _Qt6Namespace()
    EXPANDING = QtWidgets.QSizePolicy.Policy.Expanding

    def exec_dialog(dlg):
        """Ejecuta un dialogo modal (``exec()`` en PyQt6)."""
        return dlg.exec()

    def activated_index(combo):
        """Senal ``activated`` con indice; en PyQt6 solo queda esa firma."""
        return combo.activated

    def activated_text(combo):
        """Senal ``activated`` con texto; en Qt6 se llama ``textActivated``."""
        return combo.textActivated

    class QStandardPaths(QtCore.QStandardPaths):  # noqa: N801
        """``QStandardPaths`` con los nombres cortos de ubicacion."""

        AppDataLocation = QtCore.QStandardPaths.StandardLocation.AppDataLocation

    class QColorDialog(QtWidgets.QColorDialog):  # noqa: N801
        """``QColorDialog`` con los nombres cortos de opcion."""

        DontUseNativeDialog = QtWidgets.QColorDialog.ColorDialogOption.DontUseNativeDialog

    class QFrame(QtWidgets.QFrame):  # noqa: N801
        """``QFrame`` con los nombres cortos de forma."""

        NoFrame = QtWidgets.QFrame.Shape.NoFrame

    class QPainter(QtGui.QPainter):  # noqa: N801
        """``QPainter`` con el nombre corto ``Antialiasing``."""

        Antialiasing = QtGui.QPainter.RenderHint.Antialiasing

else:

    Qt = QtCore.Qt
    EXPANDING = QtWidgets.QSizePolicy.Expanding

    def exec_dialog(dlg):
        """Ejecuta un dialogo modal (``exec_()`` en PyQt5)."""
        return dlg.exec_()

    def activated_index(combo):
        """Senal ``activated`` con indice (``activated[int]`` en PyQt5)."""
        return combo.activated[int]

    def activated_text(combo):
        """Senal ``activated`` con texto (``activated[str]`` en PyQt5)."""
        return combo.activated[str]


__all__ = [
    "QT6",
    "EXPANDING",
    "QBrush",
    "QByteArray",
    "QCheckBox",
    "QColor",
    "QColorDialog",
    "QComboBox",
    "QDateTime",
    "QFileDialog",
    "QFormLayout",
    "QFrame",
    "QGridLayout",
    "QGroupBox",
    "QHBoxLayout",
    "QLabel",
    "QLocale",
    "QPainter",
    "QPen",
    "QPointF",
    "QRect",
    "QScrollArea",
    "QSignalBlocker",
    "QSizePolicy",
    "QSlider",
    "QSpinBox",
    "QStackedWidget",
    "QStandardPaths",
    "QSvgRenderer",
    "QTabWidget",
    "QTimer",
    "QTransform",
    "QVBoxLayout",
    "QWidget",
    "Qt",
    "activated_index",
    "activated_text",
    "exec_dialog",
    "pyqtSignal",
    "uic",
]
