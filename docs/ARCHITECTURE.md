# Architecture

The plugin is a Krita Python docker with a pure-Python head generator. Krita is only
needed by the docker and the preview widget; the geometry and its tests do not import it.

## Files

| File | Role |
| --- | --- |
| `loomis_head_generator.py` | Pure Python Loomis geometry, parameters, `to_dict`/`from_dict`, SVG |
| `asaro.py` | Pure Python Asaro planar head: mesh, projection, SVG |
| `asaro_clean_mesh.py` | Static hand retopology (0.7.4): 122 / 242 / 272 faces, mouth band, ear concha, banding, `PIVOT_LOCAL` |
| `asaro_mesh.py` | Static Asaro mesh data: three decimated levels from the real scan, `neck` flag, cut cap (reference for tests, not drawn) |
| `models.py` | Model registry: `MODELS`, `DEFAULT_MODEL`, `create_model`, `supported_models` |
| `qt_compat.py` | PyQt5/PyQt6 shim: every module imports Qt from here |
| `loomis_head_plugin.py` | Docker, Krita integration, guide manager, presets, Grimoire bridge |
| `preview.py` | `QSvgRenderer` preview and arcball rotation |
| `features_dialog.py` | `FeaturePanel` (sex, caricature, proportions, socket/brows, feature lines, hair, Reilly), `HairPanel` and `AsaroPanel`; embedded in the docker |
| `i18n.py` + `translations/*.json` | Language override/locale and strings |
| `linalg.py`, `euclid.py`, `geom_polyline.py` | Math and SVG path helpers |
| `trackball.py` | Legacy widget kept for reference (the preview replaces it) |
| `test_generator.py` | Pure-Python Loomis unit tests (no Krita/Qt needed) |
| `test_asaro.py` | Pure-Python Asaro unit tests and registry checks |
| `test_ui_offscreen.py` | Docker acceptance test: real Qt + `krita` stub, no document; skips with `SkipTest` without PyQt5/PyQt6 |

`models.py` is the only module that knows the implementations, and it imports them; neither
`loomis_head_generator.py` nor `asaro.py` imports `models.py`, so there is no cycle. The
docker asks `create_model(model_id)` and works against the common interface
(`set_scale`, `set_position_x/y`, `set_quaternion`, `set_stroke_color`,
`set_front_line_stroke`, `set_back_line_stroke`, `set_zone_colors`,
`build_svg(width, height, dash_back, samples)`, `to_dict`, `from_dict`). An unknown id
returns `None` and the caller shows the message.

`qt_compat.py` is the single Qt import point: it picks PyQt5 or PyQt6, maps the unscoped
enums PyQt6 removed (`Qt.Horizontal` → `Qt.Orientation.Horizontal`, `QSizePolicy.Expanding`,
`QStandardPaths`, `QColorDialog`, …), and exposes `exec_dialog()` and `activated_index()`.

## Models and the model switch

- `AsaroHead` (`asaro.py`) draws a low-poly head as face contours: orthographic
  projection with the same scale as the generator (`min(width, height) * 0.3 * scale`),
  painter's algorithm by mean z, front edges with `front_line_stroke`, back edges with
  `back_line_stroke` and `dash_back`. Own parameters: `show_planes`, `show_edges`,
  `show_neck`, `detail` (0..2). It also carries the Loomis attributes and setters as
  defaults/no-ops so `_sync_ui_from_model` does not break; the UI hides them for Asaro.
- **Asaro mesh (0.7.4)**: `asaro.py` reads the hand retopology in `asaro_clean_mesh.py`
  (static data, no OBJ, no external dependency). `ASARO_CLEAN_LEVELS` has three levels —
  **122 / 242 / 272 faces** (91 / 193 / 217 head faces plus neck+base) with 131 / 257 / 289
  vertices — and each level carries `verts` (oriented +90° Y, centred, height 1.5), `faces`
  (counter-clockwise from outside; head first, then neck), `head_faces`, `cap` (the fan that
  closes the cut) and `neck` (per-face flag). Rows are flow lines with their own height per
  column; the mouth is a three-row band, the ear has a hollow concha, and the intermediate
  columns band in the temple, cheekbone, orbital and mastoid planes. `NECK_Y` is the height
  threshold that splits head from neck. `asaro_mesh.py` (the 0.7.3 decimation: 334 / 634 /
  1195 faces) stays as reference for tests and comparisons and is no longer drawn.
- **Pivot and position semantics**: `LoomisHead3D.pivot_local` is `Vector3(0, 0, 0)` (the
  cranium sphere centre); `AsaroHead.pivot_local` is `asaro_clean_mesh.PIVOT_LOCAL`
  (`(0.0, 0.2852, -0.0354)`), the area centroid of the head faces of the finest level —
  the centre of the skull between ears and eyes, not the bust bbox centre (which includes
  neck and base). `position_x/y` is the **pivot position in the document**: `build_svg`
  subtracts `pivot_local` before rotating and projecting, so the pivot lands exactly on
  `position_x/y` and rotating or switching model/type/sex does not move the head (with a
  manual Move the X/Y the docker shows is `M·p + t`, see *Pivot marker and redraw*). The
  JSON schema is unchanged; only the documented semantics changed.
- **`show_neck`**: `AsaroHead.show_neck` (default `True`), `set_show_neck()`, `showNeck` in
  `to_dict`/`from_dict` and the **Show neck** checkbox in `AsaroPanel`
  (`asaro.show_neck`). With the neck off, the faces whose `neck` flag is set are filtered
  and the `cap` fan closes the jaw ring, so the head remains a closed solid without NaN.
  `shade_planes` (default `True`) fills each face by normal azimuth in neutral tones
  (opacity 0.18–0.28, no directional light) and round-trips as `shadePlanes`; `show_planes`,
  `show_edges` and `detail` (0..2 → level) still change the SVG. `test_asaro.py` locks the
  mesh sizes, the mouth band, the ear concha, the closed mesh, the pivot, `shade_planes`
  and the round-trip; the suite is 143 tests (66 generator + 77 Asaro), plus
  `test_ui_offscreen.py` for the docker.
- **License**: the code is **GPL-3.0-only**; the Asaro meshes are **CC BY 4.0**, not GPL —
  derivative of "Asaro-head" by **ivan4akir** (CC BY 4.0), design by **John Asaro**;
  "Simple Asaro Head" by **fabianoaraujo** (CC BY 4.0) reviewed and not used. Attribution
  and modification notice travel with the mesh (`LICENSE-ASSETS.md`, `CREDITS.md`). 0.7.9
  is a **local build**: no public ZIP or patch until it is validated in Krita; `release/`
  keeps the 0.7.2 artifacts, the last public build (0.7.3 to 0.7.9 are local).
- The docker adds a **Model** combo and a `QStackedWidget`: page 0 is `FeaturePanel`, page 1
  is `AsaroPanel` (planes, edges, shade, neck, detail). For Asaro the Guides and Hair tabs are
  disabled and the Loomis-only Settings rows (side cut, face age, chin width) are hidden.
- `_switch_model()` stashes the outgoing model (`to_dict()`) and restores the incoming one
  from the guide's `model_states`, then always re-applies `_COMMON_STATE_FIELDS` (scale,
  position, rotation, stroke, zone colours) from the outgoing model, so the guide keeps its
  place and the stash only contributes model-specific state. The first time a model is
  used, the outgoing `to_dict()` is fed to `from_dict()`, which ignores unknown keys.
- The stash persists per guide in `guides.json` under `models` (the active model is the
  guide's `state`); `_save_doc_state()` deep-copies it so the JSON never shares references.

## Docker UI

`LoomisProportionsDocker` (`loomis_head_plugin.py`) keeps a fixed top block (head
selector, 3D preview, view selector, library and actions) and five scrollable tabs:
**Settings**, **Move**, **Guides**, **Features** and **Hair**. The Features page hosts a
**Model** combo and a `QStackedWidget` with `FeaturePanel` (Loomis) and `AsaroPanel`
(planes, edges, shade, neck, detail) from `features_dialog.py`; the Hair page hosts `HairPanel`.
Each panel is bound to the active model with `set_model`/`sync_from_model` when the guide or
the model changes. With Asaro active, the Guides and Hair tabs are disabled and the Loomis-only
Settings rows are hidden.

## Pivot marker and redraw

- After each SVG draw the docker adds an invisible `<circle>` named **`loomis-pivot`**
  (1 px, no stroke, opacity 0) at `(position_x, position_y)` in **SVG coordinates** inside
  the layer; the manual matrix is then applied to the marker like to any other shape, so its
  absolute centre is the effective X/Y. It does not change the render or the visible bounds,
  and it is recreated at the pivot on every draw.
- **Capture of the Move/Transform (0.7.8)**: Krita stores a canvas Move/Transform in each
  shape's `Shape.transformation()`; a vector layer keeps `Node.position()` at 0 and
  `Node.bounds()` drifts when the layer is rotated, so neither is the source anymore.
  `_capture_manual_transform()` takes the **most common non-identity** 6-float matrix
  (`m11, m12, m21, m22, dx, dy`) among the layer's shapes, skips the pivot marker, and
  returns `None` for a layer with no drawing shape so an empty layer never overwrites a
  saved transform. The capture runs in `sync_manual_position()` (120 ms timer) **before**
  the draw and only stores the matrix: it never moves the model.
- **Reapply (0.7.8)**: `draw_lines_with_vectors()` captures first, removes the old shapes,
  builds the new SVG at `(position_x, position_y)` and `_apply_manual_transform()` applies
  the matrix to **every** shape returned by `addShapesFromSvg()`, the marker included, so
  the marker's absolute centre is already the effective position. The layer transform is
  **no longer reset** before a redraw (that was the 0.7.7 bug); `_set_shapes_identity()`
  only runs on the explicit `reset_position`, which also clears `guide.manual_transform`.
- **Persistence**: each `guides.json` guide entry carries
  `"transform": [m11, m12, m21, m22, dx, dy]` (missing → identity for older documents),
  restored into `guide.manual_transform`; presets and the head state carry
  `layerTransform` in the same block as the model, so loading a preset re-applies the Move
  to the current shapes. The field is opaque to the Grimoire of Color and to older
  versions. If a reopened document has a saved transform but every shape is still at
  identity, `_transform_pending_apply` (0.7.9, review finding C) keeps it: the 120 ms poll
  does not overwrite it with identity and the first draw applies it.
- **X/Y is the effective position (0.7.9)**: the docker shows `M·p + t` — the model pivot
  passed through the **full** matrix, not `p + (dx, dy)`. `_visible_position()` is the only
  reader; `_refresh_visible_position()` writes the value into the sliders/spinboxes without
  emitting signals, and `_set_visible_position()` solves `p = M_lin⁻¹·(target − t)` (with a
  `|det| < 1e-6` fallback to pure translation) before `set_position_x/y`, so editing X/Y
  moves the model and never touches the manual Move. Ignoring the linear part was the
  0.7.8 review finding A: with a 30° rotation the old formula was off by hundreds of pixels.
- **Sync before the draw (0.7.5)**: `draw_lines_with_vectors()` calls `sync_manual_position()`
  **first**, before removing and recreating the shapes. The redraw builds the SVG at
  `(position_x, position_y)`, so without that call touching any docker control would snap a
  manually moved head back to its old X/Y. After the draw the marker and layer references
  are re-read; switching guides takes the new layer as baseline without a delta.
- **`pivot.log` (0.7.6, `manual`/`reapplied` in 0.7.8)**: every sync that changes the matrix
  and every draw append one line with a timestamp to `loomis_head/pivot.log` under
  `QStandardPaths.AppDataLocation` (`~/.var/app/org.kde.krita/data/krita/loomis_head/pivot.log`
  in the flatpak): a `sync transform` line records `old=`/`new=` (the captured matrix) and
  the model `pos=`; each `draw` line records `pos=`, `visible=` (effective X/Y),
  `manual=<6 floats>`, `reapplied=<True|False>`, plus `layer=`, `marker=`, `last_layer=`
  and `last_marker=`. `init.log` and `setup.log` use the same rotation helper
  (`_append_log`): each rotates to `<name>.1` past 200 KB and swallows any OS error.
  Diagnostics only, never a functional path.
- **History — 0.7.7, superseded by 0.7.8**: `sync_manual_position()` read the marker's
  absolute centre delta and applied it **once** to `position_x/y`, with
  `_layer_position()`/`Node.position()` as the fallback; a `_reset_layer_transform()` ran
  before each draw. Both are gone: the sync no longer moves the model and
  `_last_pivot_position` / `_last_layer_position` are log references only.
- The canvas redraws after the **Input Delay** (`redrawDelay` in `settings.json`): a
  `QSpinBox` **Delay** under View, **50–5000 ms** in 50 ms steps, default
  `REDRAW_INTERVAL_MS` (500 ms). The single-shot timer restarts on every slider/spin/rotation
  change and its interval changes live when the spinbox changes; the docker preview runs
  live. `valueChanged` only updates the preview and `sliderReleased` does **not** flush: the
  delay always wins. The 50 ms floor stops a drag from rebuilding the layer on every tick
  (dozens of undo entries per second), and `settings.json` is written on a 600 ms debounce
  plus a flush in `hideEvent`.

## Head structure

`FeaturePanel` drives the skull structure on the active model:

- **Sex** combo (`head_sex`): applies the male or female preset (`SEX_PRESETS`) and stores
  the choice. Switching head style (`_apply_type`) re-applies the current sex afterwards.
- **Eye socket** (`show_eye_socket`, `eye_socket_depth`, `eye_socket_size`): the generator
  draws the orbital rim, a smaller floor displaced towards the nose and down, and two depth
  ticks, as `feature_front`. It is independent of the eye circle (`show_eyes`).
- **Brow ridge** (`brow_ridge`): a superciliary ridge curve above the brow plus a central
  projection tick.
- **Cheek fullness** (`cheek_fullness`): a quadratic fill curve from the cheekbone arch
  (`cheek_rim_touch`) to the jaw corner, in the `cheek` zone; `cheek` still controls the
  zygomatic prominence.

## Guide manager

- A `Guide` is one head: a model instance (`LoomisHead3D` or `AsaroHead`), one vector layer
  `Loomis Head N`, a name, the last known layer centre and `model_states`, the stash of the
  models that are not active for that guide.
- `ensure_guide()` adopts existing `Loomis Head*` layers before creating anything. On the
  first run it migrates the old repeated `Loomis Method Head Guide` layers, keeping the
  topmost one and removing the duplicates (undoable in Krita).
- Each document has its own state, keyed by `Document.fileName()`. Unsaved documents use
  a session key and do not survive a restart.
- `_set_active_guide()` applies the delta between the layer's current centre and the
  saved centre, so a head moved while inactive does not jump back; the marker is then
  recreated at the pivot. It also calls `Document.setActiveNode()`.

## State files

In Krita's app data directory (`QStandardPaths.AppDataLocation`):

```text
loomis_head/
├── settings.json   language and redraw delay
├── presets.json    named presets and per-OC presets
├── guides.json     per-document guides: state + transform + models stash + centre + active index
├── pivot.log       diagnostics: sync source/positions and draws (rotates to .1, 200 KB)
├── init.log        docker start/build failures and init:ok (rotates to .1, 200 KB)
└── setup.log       extension setup: paths and registration (rotates to .1, 200 KB)
```

`pivot.log` is written only on a sync with a delta and on each draw, so it appears after the
first move/redraw. All three logs are diagnostics, hold no document data and can be deleted
at any time; each rotates to `<name>.1` past 200 KB.

Positions in `guides.json` and presets are normalised (0–1 of the document size) so they
survive canvas size changes. The model stores document pixels; the docker converts.
`transform`/`layerTransform` (6 floats) are **not** normalised: they are a canvas-space
matrix in document pixels, saved and restored verbatim.
A shared head file declares which one it carries: `positionUnit: "normalized"` means
`positionX/positionY` are 0–1 of the canvas, anything else (or missing, which is what
`to_dict()` emits without a document) means document **pixels** and is used as-is. The two
`heads/example-*.json` templates carry `"positionUnit": "normalized"` with `0.5/0.5`, the
canvas centre.

## Optional Grimoire of Color

The plugin does not import Grimoire modules. It reads `grimorio.json` only to list
characters and to write `head` into a character (read-modify-write with
`grimorio.json.loomis.bak`). If the file is absent the OC row is disabled and the rest of
the plugin works standalone.

## Extension points

- **Language**: add `translations/<code>.json`, add the code to `SUPPORTED` and the
  selector.
- **Hair/features**: generator parameter + setter + `to_dict`/`from_dict` + panel control +
  test.
- **Head models**: add the class, register it in `MODELS` in `models.py`, and expose the
  common interface (`build_svg(width, height, dash_back, samples)`, `to_dict`, `from_dict`,
  the transform and stroke setters). The share format already carries `model` and the loader
  resolves it through `create_model()`; unknown ids are refused with a message.
