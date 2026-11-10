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

## 0.5.1 — 2026-11-09

- Docker UI: head, 3D preview, view selector, library and action buttons stay fixed;
  Settings, Move, Guides, Features and Hair now live in scrollable tabs.
- Fixed the feature and hair panels: after switching heads they wrote to the previous
  model, so hiding mouth/ears/eyes or showing hair appeared to do nothing.
- Fixed Quick Access Manager compatibility: the `actions` layout in the `.ui` shadowed
  `QWidget.actions()` and broke QAM's action discovery for every quick action.
- Preview: the head is scaled and centred so the chin is no longer clipped.

## 0.6.0 — 2026-11-09

- **Parametric proportions**: new `forehead_height`, `jaw_angle`, `cranium_width` and
  `cranium_height` (head width/height), `cheekbone_height` and `chin_sharpness`
  parameters, with setters, clamps and JSON round-trip. The five head presets were
  updated to carry the new fields.
- **Independent guide lines**: brow, eye, nose and mouth lines can be shown or hidden
  separately. The existing mouth checkbox is now labelled "Mouth curve".
- **Reilly rhythm curves**: an optional `rhythm` zone draws the Reilly flow lines
  (crown → brow → nose → mouth → chin plus the lateral arches) with adjustable strength.
- **Directional light**: azimuth, elevation and intensity, a terminator (or cel) shadow
  clipped to the lateral band, and a new **Light** tab to drive it.
- JSON compatibility with 0.5.1: missing keys fall back to the current defaults;
  `jaw_angle` now defaults to `0.0`.
- Tests: 31 generator tests plus 25 light tests, and an offscreen docker check with six
  tabs.

## 0.6.1 — 2026-11-09

- **Light removed**: the directional light/shadow and the **Light** tab are gone (it was a
  different product). The docker is back to five tabs: Settings, Move, Guides, Features,
  Hair. `light.py`, `test_light.py`, `LightPanel`, `tabs.light` and the `light.*` strings
  were deleted.
- **Head sex**: new `head_sex` (male/female) with presets that combine with the head style;
  changing the style re-applies the current sex.
- **Eye socket**: sunken orbit (rim + displaced inner floor + depth ticks) drawn as a front
  feature, independent of the eye circle.
- **Brow ridge and cheeks**: a superciliary ridge curve above the brow with a projection
  tick, and a cheek-fill curve from the cheekbone arch to the jaw.
- New controls in **Features**: Sex combo and a "Socket and brows" section (socket
  checkbox, socket depth/size, brow ridge, cheek fullness).
- Tests: 40 generator tests, and an offscreen docker check with five tabs, no Light tab,
  QAM action discovery, sex presets and socket controls.
- Compatibility: head JSON from 0.5.1 and 0.6.0 loads with the new keys at their defaults.
- Note: the 0.6.0 entry is kept as history; 0.6.1 withdraws the light.
