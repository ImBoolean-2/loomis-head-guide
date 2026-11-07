# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

"""Traducciones del Loomis Head Guide: JSON + locale, sin Qt Linguist."""
from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from PyQt5.QtCore import QLocale
except ImportError:  # pruebas fuera de Krita
    QLocale = None

DEFAULT = "en"
SUPPORTED = ("en", "es", "pt", "fr")
_cache: dict[str, dict] = {}
_override: str | None = None


def set_language(lang: str | None) -> None:
    """Fuerza un idioma (None = automatico por entorno/locale)."""
    global _override
    _override = lang if lang in SUPPORTED else None


def _read(lang: str) -> dict:
    path = Path(__file__).resolve().parent / "translations" / f"{lang}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def language() -> str:
    if _override:
        return _override
    forced = os.environ.get("LOOMIS_LANG", "").strip().lower().split("_")[0]
    if forced in SUPPORTED:
        return forced
    if QLocale is not None:
        name = QLocale.system().name().split("_")[0].lower()
        if name in SUPPORTED:
            return name
    return DEFAULT


def t(key: str, **kwargs) -> str:
    lang = language()
    if lang not in _cache:
        _cache[lang] = _read(lang)
    text = _cache[lang].get(key)
    if text is None:
        if DEFAULT not in _cache:
            _cache[DEFAULT] = _read(DEFAULT)
        text = _cache[DEFAULT].get(key, key)
    if kwargs:
        try:
            return str(text).format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return str(text)
    return str(text)
