__version__ = "0.6.0"

# SPDX-FileCopyrightText: 2025 lm0ss
# SPDX-FileCopyrightText: 2026 Nedeljko Umjetnik
# SPDX-FileCopyrightText: 2026 imboolean
# SPDX-License-Identifier: GPL-3.0-only

from krita import Krita

from .loomis_head_plugin import LoomisHeadPlugin

app = Krita.instance()
extension = LoomisHeadPlugin(app)
app.addExtension(extension)
