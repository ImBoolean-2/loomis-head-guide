# Changelog

## 0.5.0 — 2026-11-07

First public release of the imboolean fork.

- Real 3D head preview with arcball rotation, roll, zoom and view shortcuts.
- Independent X/Y/Z rotation and position sliders.
- Guide manager: several independent heads per document, one `Loomis Head N` layer each,
  automatic layer selection and per-document state in `guides.json`.
- Migration of the old repeated layers; no duplicate layers on restart; layer centre saved.
- Feature panel embedded in the docker (no separate window): features, caricature, head
  types and hair.
- Hair: arch, tilt, part position, straight/zigzag/spiky patterns and
  smooth/wavy/spiky/curly textures.
- Named presets and per-character presets; load/export heads as JSON; `heads/` template.
- Colours per zone; standalone use; optional Grimoire of Color integration.
- Languages: English, Spanish, Portuguese, French with a selector and `LOOMIS_LANG`.
- Credits and SPDX headers; GPL-3.0-only.

Based on Loomis Method Head Guide by Nedeljko Umjetnik and Loomis Head Generator by lm0ss.
