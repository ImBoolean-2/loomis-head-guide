# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Registro de modelos de cabeza.

Es el unico punto que conoce todas las implementaciones. Ni
``loomis_head_generator`` ni ``asaro`` importan este modulo, para no crear
ciclos: el plugin pide aqui la clase y trabaja contra la interfaz comun.
"""

from .asaro import AsaroHead
from .loomis_head_generator import LoomisHead3D

MODELS = {
    "loomis": LoomisHead3D,
    "asaro": AsaroHead,
}

DEFAULT_MODEL = "loomis"


def create_model(model_id: str | None = None):
    """Instancia del modelo pedido, o ``None`` si no existe.

    ``None`` usa ``DEFAULT_MODEL``. Un identificador desconocido devuelve
    ``None`` para que el llamador decida el error (aviso en la UI, cabeza
    ignorada al cargar un preset, etc.).
    """
    key = DEFAULT_MODEL if model_id is None else str(model_id).strip().lower()
    cls = MODELS.get(key)
    return None if cls is None else cls()


def supported_models() -> tuple[str, ...]:
    """Identificadores aceptados por :func:`create_model`."""
    return tuple(MODELS)
