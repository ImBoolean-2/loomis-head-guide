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

## 0.7.2 — 2026-11-10

- **Asaro rebuilt as a proportioned bust** (commit `7051243`): the old faceted sphere with a
  small face mask is gone. The mesh is now a head plus neck on a single axis: total height
  1.5, ear-to-ear width ~1.01 (height/width 1.485), crown-to-chin depth 0.75 (0.714 of the
  head height, 0.50 of the bust), face (brow→chin) 44 % of the height and neck/base 30 %.
- **Full anatomy in planes**: crown, forehead, brow, orbital socket, nose (nasion, dorsum,
  tip, base), maxilla, upper/lower lip, mental groove, chin, jaw, ear, occiput and neck. The
  ear is a lateral wedge at brow/nose height; the profile runs forehead → brow → nasion →
  dorsum → tip → philtrum → lips → chin and the nape curves into the neck instead of ending
  in a vertical wall.
- **Measured profile landmarks**: the nose tip is the most forward point and stands 0.09+
  beyond the brow–chin plane; the socket sits behind the brow and the cheekbone stands out
  from the orbital rim; the lips beat the mental groove and the chin closes under the jaw
  with a throat hollow.
- **Neck toggle**: new `show_neck` parameter (default `True`) with `set_show_neck()`, a
  **Show neck** checkbox in the Asaro panel (`asaro.show_neck` in en/es/pt/fr) and
  `showNeck` in `to_dict`/`from_dict`; 0.7.1 heads without the key load with the neck on.
  Without the neck the jaw is capped, so the head stays a closed solid (no hole, no NaN).
- **Mesh sizes**: 60 / 80 / 100 faces at detail 0 / 1 / 2 with the neck (52 / 72 / 92
  without it), still symmetric and without degenerate faces or dead vertices.
- **Tests**: 73 unit tests (40 generator + 33 Asaro). The 10 new Asaro tests cover height,
  width and depth ratios, face/neck share, landmark heights, nose and socket relief,
  lips/chin step, occiput and nape curves, ear position, neck toggle, closed cap and the
  neck not changing the head faces.
- **Known limits**: the cranium is still boxy (it is a low-poly plane study, not a smooth
  sculpt), the ear is a wedge and the mesh is faceted in every view; no light or shadow.

## 0.7.3 — 2026-11-10

- **Exact Asaro mesh from the real scan** (commit `fa2acfb`): the hand-built mesh is replaced
  by a decimated version of `Asaro_high.obj` (10,416 vertices, 20,828 triangles, Cinema 4D:
  the planar bust with neck and base). It is stored as static data in the new
  `loomis_head/asaro_mesh.py`: no external dependencies, no OBJ at runtime. The pipeline
  orients (+90° Y), centres, scales to height 1.5, clusters the vertices on a grid denser
  at the features (chin, lips, nose, eyes, ear) than at the cranium, neck and base, drops
  degenerate/duplicate/sliver faces, splits the neck by height (`NECK_Y`) and closes the
  cut with a fan cap.
- **Three detail levels** (head / neck+base): detail 0 = 283 / 51 = **334 faces** (209
  vertices), detail 1 = 503 / 131 = **634** (390), detail 2 = 1028 / 167 = **1195** (765).
  Each level carries `verts`, `faces`, `head_faces`, `cap` and `bbox`; the profile, the 3/4
  and the front now follow the real bust silhouette instead of a drawn one.
- **`show_neck`** filters the neck/base faces (`neck` flag per face, stored at the end of
  `faces`); the head stays solid because the cut is capped. **`shade_planes`** is now
  implemented with a neutral fill per face orientation (azimuth of the normal, no
  directional light, opacity 0.18–0.28) and round-trips as `shadePlanes`;
  **`show_planes`**, **`show_edges`** and **`detail`** keep driving the SVG.
- **Tests**: 82 unit tests (40 generator + 42 Asaro). The Asaro suite locks the mesh
  proportions, the profile landmarks, the neck toggle and cap, `shade_planes` on/off
  (`fill` present/absent), `show_planes`/`show_edges`/`detail`, the JSON round-trip and the
  absence of degenerate faces and NaN. The offscreen docker check (72 checks) passes plus
  the new `check_neck_ui.py` and `check_shade_planes_ui.py` checks.
- **License notice — local build only**: the mesh is derived from a scan downloaded by the
  user, and the rights of the original model are **not confirmed**. This release is for
  local use: **do not redistribute the ZIP or the patch until the model licence is cleared
  and John Asaro is credited**. `release/` keeps the 0.7.2 artifacts; there is no 0.7.3 ZIP
  or patch.

## 0.7.4 — 2026-11-11

- **Clean retopo v2, hand-built** (`asaro_clean_mesh.py`): the 0.7.3 decimation is replaced
  by a hand retopology over the silhouette of `Asaro_high.obj`, measured in the same frame
  (+90° Y, centred, height 1.5). Each row is a flow line with its own height per column
  instead of a stacked ring, so the planes follow the anatomy: **122 / 242 / 272 faces** at
  detail 0 / 1 / 2 (head + neck and base), with 131 / 257 / 289 vertices. `asaro_mesh.py`
  stays as the decimated reference for tests and comparisons; it is no longer drawn.
- **Mouth band**: three rows on the front (lower lip, sunken centre line, upper lip) open
  towards the cheek and the occiput, so the lips read in the front and the profile without
  filling the face with rings.
- **Ear with concha**: the helix at 116° stands out, the concha at 124° sinks and the
  antihelix at 140° rises again; the ear is a four-face hollow with a rim, not a wedge.
  **Banding** (columns at intermediate angles) adds the temple, cheekbone, orbital and
  mastoid planes, and the mesh stays closed (every internal edge shared by two faces).
- **Invisible pivot at the centre of the skull**: `LoomisHead3D.pivot_local` is the sphere
  centre `(0, 0, 0)`; `AsaroHead.pivot_local` is the area centroid of the head faces
  (neck and base excluded) of the finest level, `(0.0, 0.2852, -0.0354)`, so the pivot is
  not the bust bbox centre and does not jump between detail levels. `position_x/y` now means
  **the pivot position in the document**: `build_svg` subtracts `pivot_local` before
  rotating and projecting, so rotating or switching model/type/sex keeps the pivot where it
  is. The JSON schema is unchanged; only the semantics are documented.
- **Pivot marker `loomis-pivot`**: an invisible `<circle>` (1 px, no stroke, opacity 0) is
  added after the head SVG inside the layer, so it does not change the render or the visible
  bounds. `sync_manual_position` reads the marker's absolute position instead of the layer
  bounds centre; a manual canvas move adds its delta **once** to `position_x/y` and updates
  the spinboxes without redrawing. Without a marker (legacy load) it waits for the next draw
  instead of drifting with the bounds.
- **1:1 movement**: the marker delta is applied exactly to `position_x/y` (no factor of 2,
  no bounds). Move the canvas +100 px → X/Y +100; then the docker +50 px → X/Y +150 and the
  head lands at +150.
- **Redraw when you stop**: the canvas debounce is now **500 ms** (single shot) and every
  slider/spin/rotation change restarts it; the docker preview (`trackball.update()`) still
  runs live. `valueChanged` no longer redraws the canvas; `sliderReleased` can flush
  immediately.
- **Tests**: **121** unit tests (44 generator + 77 Asaro), plus the offscreen docker check
  (`test_dashboard_070.py`) and the `check_neck_ui.py`, `check_shade_planes_ui.py` and
  `check_pivot_marker.py` checks, all passing. What is not covered without a real Krita
  document: the marker under undo and a real canvas Move.
- **License — Asaro meshes CC BY 4.0**: the code stays **GPL-3.0-only**; the meshes are
  **CC BY 4.0** with attribution and a modification notice — derivative of "Asaro-head" by
  **ivan4akir** (CC BY 4.0), design by **John Asaro**; "Simple Asaro Head" by
  **fabianoaraujo** (CC BY 4.0) reviewed and not used. See `LICENSE-ASSETS.md` and
  `CREDITS.md`.
- **Warning — local build**: 0.7.4 is **local only**. There is **no 0.7.4 ZIP or patch**;
  the public ZIP ships only after validating this build in Krita. `release/` still holds
  the **0.7.2** artifacts, which remain the last public build.
