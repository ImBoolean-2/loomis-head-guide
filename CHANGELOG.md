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

## 0.7.5 — 2026-11-11

- **Fix B→C: el sync del pivote va antes del redibujo** (`draw_lines_with_vectors`).
  Redibujar borra los shapes y crea uno nuevo en `(position_x, position_y)`; si el usuario
  había movido la capa con Move/Transform y X/Y seguían viejos, el canvas volvía a la
  posición anterior en cuanto se tocaba cualquier control del docker (B→C roto). Ahora el
  método llama `sync_manual_position()` **antes** de borrar y crear, así que el marcador se
  adopta y el SVG nuevo se dibuja donde está el usuario. Aplica también al redibujo que
  dispara el debounce, el cambio de modelo y el de tipo/sexo.
- **Input Delay**: nuevo `QSpinBox` **Delay** (0–5000 ms, paso 50, sufijo `ms`, default
  **500**) bajo **Vista**, en la fila del selector de vista. Guarda `redrawDelay` en
  `settings.json` y cambia el intervalo del timer del canvas en caliente; `0` redibuja en
  cuanto se suelta y los valores altos agrupan más cambios en una sola entrada de undo. El
  valor se fija con clamp (`_clamp_delay`) y el arranque no reescribe el archivo.
- **Sin flush en `sliderReleased`**: soltar un slider ya no fuerza un redibujo inmediato; el
  retardo configurado manda y se respeta. La preview del docker (`trackball.update()`) sigue
  en vivo en cada `valueChanged`.
- **Tests**: **121** unit tests (44 generador + 77 Asaro) en verde; `test_draw_sync.py`
  (32 checks, incluido sync-antes-del-draw), `test_dashboard_070.py`, `check_neck_ui.py`,
  `check_shade_planes_ui.py` y `check_pivot_marker.py` PASS. Sin cubrir todavía: el
  marcador bajo undo y un Move real de canvas (necesitan documento de Krita).
- **Aviso — build local**: 0.7.5 es **solo local**. No hay **ZIP ni patch 0.7.5**; el ZIP
  público se genera solo después de validar este build en Krita. `release/` sigue con los
  artefactos **0.7.2**, que son la última build pública (0.7.3, 0.7.4 y 0.7.5 son locales).

## 0.7.6 — 2026-11-11

- **Fix B→C: la posición de la capa es la fuente primaria** (`Node.position()`). El
  marcador `loomis-pivot` deja de ser la única referencia: al mover el lienzo con
  Move/Transform la capa cambia de posición aunque la transformación absoluta del marcador
  no lo refleje de forma fiable. `_layer_position()` lee `Node.position()` y
  `sync_manual_position()` aplica su delta **una sola vez** a `position_x/y` (≥ 0,5 px); en
  esa pasada no se suma también el delta del marcador. El marcador queda como **respaldo**
  cuando la capa no cambió o no expone posición, y sin capa ni marcador no se toca nada
  (nunca `bounds`, que deriva al rotar).
- **Sync antes del draw**: `draw_lines_with_vectors()` sigue llamando
  `sync_manual_position()` **antes** de borrar y recrear los shapes, y ahora reajusta
  **ambas** referencias (capa y marcador) después del draw. Al cambiar de guía se toma la
  capa nueva como baseline sin aplicar delta; al resetear no queda ninguna referencia.
- **`pivot.log` de diagnóstico**: cada sync con delta y cada draw anotan una línea con
  timestamp en `QStandardPaths.AppDataLocation/loomis_head/pivot.log`
  (`~/.var/app/org.kde.krita/data/krita/loomis_head/pivot.log` dentro del flatpak). Incluye
  la fuente (`layer`/`marker`), ambas posiciones, `dx/dy` y `pos_before`/`pos_after`, para
  ver qué cambia realmente en un Move. Se rota a `pivot.log.1` al pasar de 200 KB y nunca
  lanza: es diagnóstico, no funcionalidad.
- **Tests**: **121** unit tests (44 generador + 77 Asaro) en verde; `test_draw_sync.py`
  ampliado con layer-position, respaldo de marcador, capa+marcador a la vez y `pivot.log`
  (creación, anotación, rotación y fallo de path); `test_dashboard_070.py`,
  `check_neck_ui.py`, `check_shade_planes_ui.py` y `check_pivot_marker.py` PASS. Sin cubrir
  todavía: el marcador bajo undo y un Move real de canvas (necesitan documento de Krita).
- **Aviso — build local**: 0.7.6 es **solo local**. No hay **ZIP ni patch 0.7.6**; el ZIP
  público se genera solo después de validar este build en Krita. `release/` sigue con los
  artefactos **0.7.2**, que son la última build pública (0.7.3, 0.7.4, 0.7.5 y 0.7.6 son
  locales).

## 0.7.7 — 2026-11-11

- **Fix B→C: el marcador `loomis-pivot` vuelve a ser la fuente primaria** del Move real.
  La medición en Krita 5.3.4 del build 0.7.6 desmintió la hipótesis anterior: un Move de
  canvas desplaza el contenido `+486/+588` px mientras `Node.position()` solo cambia
  `+116/+161` px, y la rotación devuelve la capa cerca del pivote. `sync_manual_position()`
  lee primero el delta del centro absoluto del marcador (≥ 0,5 px) y lo aplica **una sola
  vez** a `position_x/y`; `_layer_position()`/`Node.position()` queda como **fallback**
  cuando la capa no tiene marcador (documento legacy, capa sin dibujo). Sin ninguna de las
  dos fuentes no se toca nada (nunca `bounds`, que deriva al rotar).
- **Reset de capa antes de borrar/crear**: un Move deja el desplazamiento en la capa y/o
  en la transformación de cada shape, y el SVG nuevo se creaba en `position_x/y` sumándolo
  otra vez, así que la cabeza salía a medio camino. `_reset_layer_transform()` aplica
  `Shape.setTransformation(QTransform())` a cada shape y `Node.move(0, 0)` antes del
  borrado; después del draw las referencias se reajustan sobre la capa ya en el origen.
- **`pivot.log` con el reset**: la línea de cada draw añade `reset_layer_before` y
  `reset_layer_after` (posición de la capa antes y después del reset) además de
  `pos_before`/`pos_after`, `source`, `layer` y `marker`, para ver en el log si el offset
  se limpió de verdad. Sigue en `QStandardPaths.AppDataLocation/loomis_head/pivot.log`
  (`~/.var/app/org.kde.krita/data/krita/loomis_head/pivot.log` en el flatpak), rota a
  `pivot.log.1` a los 200 KB y nunca lanza.
- **Semántica — pivote ≠ Transform Position**: el **X/Y del docker es el pivote**, el punto
  alrededor del cual gira la cabeza (centro del cráneo). El **Position** que muestra Krita
  en la barra de Transform es el **origen de la capa o de la selección**, no el mismo
  punto; compararlos da un desfase que no es un bug. El sync mueve el pivote, no el origen.
- **Tests**: **121** unit tests (44 generador + 77 Asaro) en verde.
  Las comprobaciones offscreen de la UI (`test_draw_sync.py` con 63 checks, más
  `test_dashboard_070.py`, `check_neck_ui.py`, `check_shade_planes_ui.py` y
  `check_pivot_marker.py`) fueron **scripts ad hoc lanzados dentro del flatpak de Krita;
  nunca se añadieron al repositorio**, así que no son reproducibles por terceros. Sin
  cubrir todavía: el marcador bajo undo y un Move real de canvas (necesitan documento de
  Krita).
- **Aviso — build local**: 0.7.7 es **solo local**. No hay **ZIP ni patch 0.7.7**; el ZIP
  público se genera solo después de validar este build en Krita. `release/` sigue con los
  artefactos **0.7.2**, que son la última build pública (0.7.3 a 0.7.7 son locales).

## 0.7.8 — 2026-11-11

- **Se elimina el reset de la 0.7.7**: `_reset_layer_transform()` neutralizaba el Move
  antes de cada dibujo y la cabeza volvía al pivote del modelo. Ahora
  `_capture_manual_transform()` lee la transformación manual (`Shape.transformation()`,
  excluyendo el marcador) y `_apply_manual_transform()` la reaplica a **todos** los shapes
  nuevos del SVG, marcador incluido. `_set_shapes_identity()` queda solo para el reset
  explícito (`reset_position`).
- **Persistencia del Move**: la guía guarda `transform` (6 floats: `m11, m12, m21, m22,
  dx, dy`) dentro de su entrada de `guides.json`, y el preset/estado de la cabeza guarda
  `head.layerTransform`. Al reabrir el documento o cargar un preset se restaura el
  desplazamiento; si falta (documento o JSON anterior), se usa la identidad.
- **Semántica X/Y efectiva**: el X/Y del docker pasa a ser `modelo + transformación manual`
  — el **Position** que muestra la herramienta de Krita al mover la capa. Editar X/Y
  desplaza el pivote del modelo por la diferencia y **no toca** el Move manual, así que la
  cabeza no salta ni pierde el desplazamiento. `_visible_position()`,
  `_refresh_visible_position()` y `_set_visible_position()` son la única ruta de lectura y
  escritura de esos campos, sliders y spinboxes incluidos.
- **`pivot.log` con el Move manual**: la línea de `draw` añade `manual=<6 floats>` y
  `reapplied=<True|False>`, y `sync transform` registra `old=`/`new=`; sigue en
  `QStandardPaths.AppDataLocation/loomis_head/pivot.log`
  (`~/.var/app/org.kde.krita/data/krita/loomis_head/pivot.log` en el flatpak).
- **Tests**: **128** unit tests (51 generador + 77 Asaro) en verde, 7 nuevos que montan el
  docker con stubs de `krita`/Qt y cubren captura, reaplicación, reset explícito,
  persistencia y X/Y efectivo. El build offscreen del docker (`test_build_078.py`) también
  fue un **script ad hoc dentro del flatpak, no incluido en el repositorio**.
- **Aviso — build local**: 0.7.8 es **solo local**. No hay **ZIP ni patch 0.7.8**; el ZIP
  público se genera solo después de validar este build en Krita. `release/` sigue con los
  artefactos **0.7.2**, que son la última build pública (0.7.3 a 0.7.8 son locales).

## 0.7.9 — 2026-11-11

Fixes de la revisión de 0.7.8. Todo local, sin ZIP ni patch hasta validar en Krita.

- **X/Y con la matriz completa (hallazgo A)**: `_visible_position()` devuelve
  `M·p + t` (parte lineal incluida), no `p + (dx, dy)`. Con Transform-rotar/escalar el
  marcador real está en `M·p + t` y la fórmula anterior se desviaba cientos de píxeles.
  Al editar X/Y, `_set_visible_position()` resuelve `p = M_lin⁻¹·(objetivo − t)`
  (`det = m11·m22 − m21·m12`; si `|det| < 1e-6` cae a traslación pura), así que la cabeza
  no salta y el Move manual no se toca. Helpers nuevos `_transform_point()` y
  `_untransform_point()`.
- **JSON a mano que no aborta Krita (hallazgo B)**: `_num()` tolera `"abc"`, `null` y
  listas al leer `positionX/Y`; un `guides.json` con `"guides": 5` se ignora en vez de
  lanzar `TypeError` desde un slot Qt; `_safe_state()` descarta un `strokeColor` que no
  cumple `#[0-9a-fA-F]{3,8}` (un `#"><svg` rompía el SVG y `from_dict` lo aceptaba).
- **El Move guardado sobrevive a una capa a identidad (hallazgo C)**: al reabrir, si
  `guides.json` trae `transform` pero los shapes siguen a identidad,
  `_transform_pending_apply` conserva el valor, el sondeo de 120 ms no lo pisa y el primer
  draw lo reaplica. Sigue mandando el canvas cuando la capa tiene un Move real. Una capa
  vacía nunca sobrescribe el transform guardado.
- **Input Delay 50–5000 ms (hallazgo D)**: `DELAY_MIN_MS` pasa de 0 a 50. A 0 ms cada tick
  del slider reconstruía la capa (decenas de entradas de undo por segundo). Sigue sin
  flush en `sliderReleased`: el retardo configurado manda. El valor se guarda en
  `settings.json` con debounce de 600 ms (flush en `hideEvent`), no en cada paso.
- **X/Y de un solo dueño (hallazgo E)**: se quitan los lambdas de
  `positionXSpinBox`/`positionYSpinBox` de `connect_ui` y el bloque `disconnect` muerto de
  `_build_transform_panel`; el panel de Mover es la única vía de lectura/escritura de X/Y.
- **`positionUnit` respetado (hallazgo F)**: un preset con `positionUnit` distinto de
  `normalized` usa `positionX/Y` como **píxeles** del lienzo (lo que emite `to_dict()` sin
  documento) en vez de forzar el centro, y sin valor conserva la posición actual. Los dos
  `heads/example-*.json` (y sus copias empaquetadas) llevan `"positionUnit": "normalized"`
  con `0.5/0.5`, el centro del lienzo.
- **Guardar preset no aborta (hallazgo G)**: `_write_presets()` captura `OSError` y avisa
  con `error.save_failed`; es la única escritura de disco de un slot que no lo hacía.
  Clave nueva en los cuatro idiomas: en “Could not save the presets.”, es “No se pudieron
  guardar los presets.”, fr “Impossible d’enregistrer les préréglages.”, pt “Não foi
  possível salvar os presets.”.
- **Higiene aplicada (L1–L3, L8–L15)**: fuera el segundo capture redundante del draw y la
  matriz construida dentro del bucle por shape; `_layer_bounds_center()` reutiliza
  `_center_from_layer()`; versión de los docstrings de `asaro*.py` al día; `QPointF`,
  `QSpinBox` y `QTransform` salen de `qt_compat` (`__all__` incluido); `init.log` y
  `setup.log` rotan con el mismo helper que `pivot.log`; `_load_guides()` mapea el estado
  por el nombre original antes de renombrar duplicadas; solo `currentColorChanged` dispara
  el color (adiós al doble `schedule_update`); sliders X/Y con rango `-1000..2000` para
  admitir posiciones negativas; `_model_stash` documentado como caso residual.
- **CI**: `python -m unittest test_generator test_asaro` (antes solo corría el generador,
  los 77 tests de Asaro nunca se ejecutaban) y `python -m py_compile loomis_head/*.py`.
- **Tests**: **143** unit tests (66 generador + 77 Asaro) en verde, con 15 nuevos: X/Y con
  rotación (lectura y edición), transform guardado sobre capa a identidad, capa vacía,
  marcador con transform propio, transform más común, preset con posición no numérica,
  preset en píxeles, preset sin posición, `strokeColor` inválido en preset y en estado
  guardado, `guides` malformado, reset explícito, cambio de modelo y `event_xy` en Qt5/Qt6.
  Nuevo `loomis_head/test_ui_offscreen.py`: monta el docker con PyQt5 real y un stub de
  `krita`, sin documento (5 pestañas, Delay 50–5000/500 con el mismo intervalo en
  `_redraw_timer`, modelo Loomis con `FeaturePanel`/`AsaroPanel`, `asaro` en el registro,
  `_visible_position()` sin documento); da `SkipTest` en un host sin PyQt5. Las
  comprobaciones offscreen anteriores eran ad hoc y no están en el repositorio.
- **Docs**: `docs/ARCHITECTURE.md` describe el flujo real (captura de
  `Shape.transformation()`, reaplicación, `guides.json → transform`, `head.layerTransform`,
  X/Y = `M·p + t`, deltas de `pivot.log`, Delay) y deja 0.7.7 como historia; README con 143
  tests, 0.7.9 local y la semántica nueva del Move.
- **Licencia**: código **GPL-3.0-only**; malla Asaro **CC BY 4.0** con atribución a
  ivan4akir/John Asaro y aviso de modificación (`LICENSE-ASSETS.md`, `CREDITS.md`).
  Sin cambios de licencia en este release.
- **Aviso — build local**: 0.7.9 es **solo local**. No hay **ZIP ni patch 0.7.9**; se
  generan solo después de validar el build en Krita (Move real, guardar y reabrir el
  `.kra`). `release/` sigue con los artefactos **0.7.2**, la última build pública
  (0.7.3 a 0.7.9 son locales).

## 0.7.10 — 2026-11-11

Corrige la regresión de 0.7.9 con la escala base. Todo local, sin ZIP ni patch hasta
validar en Krita.

- **Regresión de 0.7.9: la base se trataba como Move**. El importador de SVG
  (`addShapesFromSvg`) deja en `Shape.transformation()` la escala de la capa (0.24 en un
  lienzo a 300 ppp). 0.7.9 la capturaba como si fuese el Move/Transform del usuario y la
  reaplicaba a los shapes nuevos, así que la base se multiplicaba por sí misma
  (0.24² = 0.0576): la cabeza salía invisible o reducida a una mota en una esquina, y el
  X/Y del docker se desviaba.
- **Base + delta**: `_capture_base_transform()` lee la transformación común de los shapes
  recién añadidos, justo después de `addShapesFromSvg` y antes de tocar nada; esa es la
  base de la capa (`guide.base_transform`, no se persiste: se vuelve a capturar en cada
  dibujo). `_capture_manual_transform()` devuelve solo el **delta** (`actual ∘ base⁻¹`) y
  `_apply_manual_transform()` compone **delta ∘ base** una sola vez; helpers nuevos
  `_compose_transforms()` e `_invert_transform()`. El marcador del pivote se excluye de la
  captura (se recrea en cada dibujo).
- **Delta identidad no toca los shapes**: con el Move a cero no se llama a
  `setTransformation()`; la base que puso el importador ya dibuja bien. Se deja de
  reescribir la transformación de cada shape en cada redibujo.
- **Unidades de capa, no píxeles**: `Shape.transformation()` está en unidades de la capa
  (puntos), no en píxeles del documento. `_document_scale()` = `1/base` y
  `_visible_position()` = `total·pivote / base`; al editar X/Y,
  `_set_visible_position()` deshace la base antes de invertir (`M_lin⁻¹·(target/base − t)`).
  Con esto el X/Y del docker vuelve a ser el "Position" real y editar X/Y no mueve la
  cabeza. `_total_transform()` = `delta ∘ base` es el único punto que compone.
- **Migración de 0.7.8/0.7.9**: `transform` (guía) y `layerTransform` (preset y estado de
  la cabeza) de esas versiones eran **absolutos** (incluían la base). Al cargar,
  `_migrate_transform()` los convierte una sola vez con `delta = guardado ∘ base⁻¹`
  (sin base capturada se deduce del propio valor, porque la base del importador es una
  escala uniforme sin traslación) y se vuelven a guardar con `"transformIsDelta": true`,
  de modo que al recargar no se migran dos veces. Los documentos de 0.7.9 no pierden el
  Move ni encogen la cabeza.
- **`_set_shapes_to_base()`**: el reset explícito (`reset_position`, cambio de modelo)
  devuelve los shapes a la **base** del SVG, no a identidad; con identidad la cabeza se
  quedaba a escala 1 (cuatro veces más grande). Sigue limpiando el delta de la guía.
- **Reabrir un `.kra`**: sin base capturada en la sesión, `_guess_base_transform()` la
  deduce de la transformación común de los shapes guardados, así el X/Y es correcto antes
  del primer dibujo; el primer `draw` la vuelve a capturar del importador.
- **Log**: la línea `sync` pasa a `sync delta old=… new=… base=…` y la de `draw` a
  `base=… delta=…` (antes `manual=`); diagnóstico, nunca camino funcional.
- **Tests**: **153** unit tests (143 + 10 nuevos): base capturada tras el importador y
  reaplicada sin cuadruplicar la escala, edición de X/Y con base, rotación y cambio de
  modelo (Loomis → Asaro) conservando el delta sobre la base nueva, migración del absoluto
  de 0.7.8/0.7.9 una sola vez, no migrar dos veces un delta, base deducida al reabrir,
  preset con transform absoluto y con delta, y composición/inversa de matrices.
  `test_ui_offscreen.py` sigue aparte (5 OK en el flatpak).
- **Docs**: README y `docs/ARCHITECTURE.md` con 153 tests, 0.7.10 local y la semántica
  base/delta/unidades + migración; 0.7.7–0.7.9 quedan como historia.
- **Aviso — build local**: 0.7.10 es **solo local**. No hay **ZIP ni patch 0.7.10**; se
  generan solo después de validar el build en Krita (Move real, rotar, cambiar de modelo,
  guardar y reabrir el `.kra`). `release/` sigue con los artefactos **0.7.2**, la última
  build pública (0.7.3 a 0.7.10 son locales).
