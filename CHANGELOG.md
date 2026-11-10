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

## 0.7.0 — 2026-11-10

- **Head model registry** (`models.py`): `MODELS`, `DEFAULT_MODEL`, `create_model()` and
  `supported_models()`. It is the only module that knows the implementations; the
  generator and the models never import it, so there are no cycles. Unknown ids return
  `None` and the caller decides the message.
- **Asaro head** (`asaro.py`): a low-poly planar head (~40 faces: forehead, brow, socket,
  nose, cheekbone, jaw, chin) drawn as orthographic face contours with painter's algorithm.
  Front edges use `front_line_stroke`, back edges use `back_line_stroke` and `dash_back`.
  Own parameters: `show_planes`, `show_edges`, `detail` (0 coarse, 1 standard, 2 fine). The
  Loomis interface (`set_sidecut`, `set_show_face`, …) exists as a no-op so the shared UI
  does not break. No light or shadow.
- **Model switch with per-model stash**: a **Model** combo (Loomis / Asaro) above the
  Features panel and a `QStackedWidget` with the Loomis features and the new `AsaroPanel`.
  Switching stashes the outgoing model's full state and restores the incoming one, then
  re-applies the shared transform (scale, position, rotation, stroke, zone colours) so the
  guide does not jump. Inactive states are persisted in `guides.json` under each guide's
  `models` key and survive a restart. For Asaro the Guides and Hair tabs are disabled and
  the Loomis-only Settings rows (side cut, face age, chin width) are hidden.
- **Qt6 shim** (`qt_compat.py`): every module imports Qt from here. It maps the unscoped
  enums PyQt6 removed (`Qt.Horizontal`, `QSizePolicy.Expanding`, …), `exec_dialog()` and
  `activated_index()`. **PyQt5 is tested on Krita 5.3.4.1; PyQt6 is only simulated, not
  tested on a real Krita 6.**
- **Quieter undo (mitigation, not a macro)**: the vector-layer redraw debounce goes from
  40 ms to 220 ms and the canvas sliders flush on `sliderReleased`, so a drag leaves far
  fewer undo entries. Krita 5.3.4's `krita.pyi` exposes neither `beginUndo`/`endUndo` nor
  `KUndo2Command`, so a single undo step needs C++ (or a layer swap that Krita groups,
  which would break `Guide.layer`/`guides.json`). Documented as debt.
- **Share format**: `model` may be `loomis` or `asaro`; the loader resolves it through the
  registry. New `heads/example-asaro.json`.
- **Tests**: 53 unit tests (40 generator + 13 Asaro), plus the offscreen docker check with
  five tabs, the model combo, the Asaro panel and QAM action discovery.
- **No light/shadow**: still five tabs (Settings, Move, Guides, Features, Hair); the 0.6.0
  light stays withdrawn.

## 0.7.1 — 2026-11-10

- **Asaro mesh reshaped for the profile** (commit `d9eeeb5`): the forehead, brow, eye
  socket, nose, cheekbone, jaw, chin and occiput were re-placed so the head reads at 90°
  and not only at three quarters. At 90° the projection keeps only (z, y), so the
  silhouette is the face curve (forehead → brow → nasion → dorsum → tip → philtrum → lips
  → chin) and the back curve (crown → occiput → nape); the interior vertices only add
  creases.
- **Measured profile landmarks**: the nose tip protrudes ≥ 0.2 from the brow/chin plane
  with a 0.12 step under the nose (the dorsum starts in front of the nasion), the eye
  socket sits ≥ 0.12 behind the glabella, the chin comes out ≥ 0.03 past the lower lip
  with a 0.08 mental step, and the nape curves over ≥ 0.35 towards the neck instead of
  being a vertical wall.
- **Mesh grows with detail**: 32 / 62 / 68 faces at detail 0 / 1 / 2 (it was ~40 flat),
  still symmetric and without degenerate faces or dead vertices.
- **Tests**: 63 unit tests (40 generator + 23 Asaro). The 10 new Asaro tests check nose
  projection, face-wall dispersion, chin/lip step, cranium and nape curves, profile and
  three-quarter SVG validity, vertex/face symmetry, degenerate faces and finite values.
- **Known limit**: the profile is still the weakest Asaro view — it is a faceted low-poly
  study, so the silhouette is a chain of segments, not an anatomical curve.
