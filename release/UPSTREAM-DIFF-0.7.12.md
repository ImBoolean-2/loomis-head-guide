# Upstream diff: 0.5.0 → 0.7.12

This document describes `release/loomis-head-guide-0.7.12.patch`, a cumulative diff of the
imboolean fork on top of **Nedeljko Umjetnik's Loomis Method Head Guide 0.5.0**.

## Base of the diff

- Base commit: `b8a762d` — *Loomis Head Guide 0.5.0: independent fork with multi-head
  state, 3D preview and i18n*.
- Generated with `git diff b8a762d`, with the exclusions listed at the end.
- Size: **35 files, +9193 / −398** lines (592,164 bytes of patch text).
- The patch is cumulative: it contains 0.5.1, 0.6.0, 0.6.1 and 0.7.0 to 0.7.12 in one
  step. It is meant to be applied on a clean 0.5.0 tree, not on an already-patched one.
- Checked with `git apply --check -p1` on a fresh `b8a762d` export; after applying, the
  unit suite gives **153 OK** (`python3 -m unittest test_generator test_asaro`).

## What changed, by area

### 0.5.0 — base (already in `b8a762d`)

Multi-head state, real 3D preview, tabbed-free docker, i18n, presets, `heads/` share
format, optional Grimoire of Color bridge. Nothing to apply; it is the starting point.

### 0.5.1 — docker usability (commits `75fae91`, `c1cd747`, `8f6c4e6`)

- Fixed top block (head selector, preview, view selector, library, actions) plus
  scrollable tabs; the docker no longer scrolls as a whole.
- Feature and hair panels follow the active head (they wrote to the previous model).
- Quick Access Manager compatibility: the `actions` layout in the `.ui` shadowed
  `QWidget.actions()` and broke QAM discovery for every quick action.
- Preview: head scaled and centred so the chin is not clipped.
- Promotional cover in `docs/media/`.

### 0.6.0 — parametric head (commit `b9e9547`)

- New parameters `forehead_height`, `jaw_angle`, `cranium_width`, `cranium_height`,
  `cheekbone_height`, `chin_sharpness`, with setters, clamps and JSON round-trip.
- Independent guide lines: brow, eye, nose and mouth can be shown/hidden separately.
- Reilly rhythm curves (`rhythm` zone) with adjustable strength.
- Directional light with azimuth/elevation/intensity and a **Light** tab.
- 31 generator tests + 25 light tests.

### 0.6.1 — light withdrawn, head sex (commit `f091f57`)

- **Light removed**: `light.py`, `test_light.py`, `LightPanel`, `tabs.light` and the
  `light.*` strings are gone. Five tabs again.
- `head_sex` (male/female) presets combined with the head style.
- Eye socket: orbital rim, displaced inner floor and depth ticks.
- Brow ridge (superciliary curve + projection tick) and cheek-fill curve.
- 40 generator tests.

### 0.7.0 — head models, Asaro, Qt6 shim (commit `64e9c43`)

| Area | Files | What |
| --- | --- | --- |
| Model registry | `loomis_head/models.py` (new) | `MODELS`, `DEFAULT_MODEL`, `create_model()`, `supported_models()`; the only module that knows every implementation |
| Asaro head | `loomis_head/asaro.py` (new) | Low-poly planar head, orthographic projection, painter's algorithm, `show_planes` / `show_edges` / `detail`, JSON round-trip, Loomis-compatible no-op interface |
| Asaro tests | `loomis_head/test_asaro.py` (new) | Round-trip, SVG validity, rotation, flags, interface compatibility, registry |
| Qt5/Qt6 shim | `loomis_head/qt_compat.py` (new) | Single import point for Qt; maps the unscoped enums PyQt6 removed, `exec_dialog()`, `EXPANDING`, `activated_index()` |
| Model switch | `loomis_head/loomis_head_plugin.py` | Model combo + `QStackedWidget`, `AsaroPanel`, per-model stash (`guides.json` → `models`), common transform copied on switch, Guides/Hair tabs disabled and Loomis-only rows hidden for Asaro |
| Asaro panel | `loomis_head/features_dialog.py` | `AsaroPanel` (planes, edges, detail) next to `FeaturePanel`/`HairPanel` |
| Undo mitigation | `loomis_head/loomis_head_plugin.py` | Redraw debounce 40 → 220 ms, immediate flush on `sliderReleased`; no real undo macro (see limits) |
| i18n | `loomis_head/i18n.py`, `translations/*.json` | Imports through `qt_compat`; `model.*`, `asaro.*`, `status.model_switched`, `error.model_unknown` in en/es/pt/fr |
| Share format | `heads/README.md`, `heads/example-asaro.json`, `loomis_head/heads/*` | `model` may be `loomis` or `asaro`; the loader resolves it through the registry; packaged copy kept in sync |
| Docs | `README.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `release/README.md` | Version, features, architecture and release notes |

### 0.7.1 — Asaro profile mesh (commit `d9eeeb5`)

| Area | Files | What |
| --- | --- | --- |
| Profile mesh | `loomis_head/asaro.py` | Forehead, brow, socket, nose, cheekbone, jaw, chin and occiput re-placed for the 90° view: at 90° the projection keeps only (z, y), so the silhouette is the face curve and the back curve. Nose tip and nasion step, socket depth, chin/lip mental step, rounded occiput and nape. Faces go from ~40 flat to 32 / 62 / 68 at detail 0 / 1 / 2. |
| Mesh tests | `loomis_head/test_asaro.py` | 10 new tests: nose projection, face-wall dispersion, chin/lip step, cranium/nape curves, profile and three-quarter SVG validity, vertex/face symmetry, degenerate faces, dead vertices, face counts per detail, finite values. Suite: 63 (40 generator + 23 Asaro). |

The interior vertices only add creases; the profile is driven by the `x == 0` vertices of
`_HALF_VERTICES`. Profile remains the **weakest** Asaro view: the mesh is faceted, so its
silhouette is a chain of segments rather than an anatomical curve.

### 0.7.2 — Asaro proportioned bust with neck (commit `7051243`)

| Area | Files | What |
| --- | --- | --- |
| Mesh rebuild | `loomis_head/asaro.py` | The faceted sphere plus small face mask is replaced by a single-axis bust: height 1.5, ear-to-ear ~1.01 (height/width 1.485), crown-to-chin depth 0.75 (0.714 of the head height, 0.50 of the bust), face (brow→chin) 44 % of the height, neck/base 30 %. New vertices/zones: forehead, brow, orbital socket, nose nasion/dorsum/tip/base, maxilla, upper and lower lip, mental groove, chin, jaw, ear (lateral wedge at brow/nose height), occiput and neck. The nape curves into the neck instead of ending in a vertical wall. |
| Neck toggle | `loomis_head/asaro.py`, `loomis_head/features_dialog.py`, `translations/*.json` | `show_neck` (default `True`), `set_show_neck()`, `showNeck` in `to_dict`/`from_dict`; **Show neck** checkbox in `AsaroPanel`, string `asaro.show_neck` in en/es/pt/fr. Without the neck, `_HALF_CLOSED_FACES` caps the jaw ring so the head stays a closed solid (no hole, no NaN); the cranial and facial faces are unchanged. |
| Mesh sizes | `loomis_head/asaro.py` | 60 / 80 / 100 faces at detail 0 / 1 / 2 (52 / 72 / 92 without the neck), symmetric, no degenerate faces or dead vertices. Lateral strips use T-junctions on purpose to save faces. |
| Mesh tests | `loomis_head/test_asaro.py` | 10 new tests: height/width, depth, face and neck share of height, landmark heights (eye, nose base, mouth), nose protrusion, socket recess, lips/chin step, occiput and nape curves, ear position, neck toggle, closed cap matching the neck ring, and the neck not changing the head faces. Suite: 73 (40 generator + 33 Asaro). |
| Sample head | `heads/example-asaro.json`, `loomis_head/heads/example-asaro.json` | Carry `"showNeck": true`. |

### 0.7.3 — exact mesh from the real scan (commit `fa2acfb`)

| Area | Files | What |
| --- | --- | --- |
| Decimated mesh | `loomis_head/asaro_mesh.py` (new) | The drawn mesh is replaced by a decimation of `Asaro_high.obj` (10,416 vertices / 20,828 triangles) stored as static data, no OBJ at runtime. Orients +90° Y, centres, scales to height 1.5, clusters vertices denser at the features, drops degenerate/duplicate/sliver faces, splits the neck by `NECK_Y` and closes the cut with a fan cap. Detail 0/1/2: 334 / 634 / 1195 faces. |
| Shading and neck | `loomis_head/asaro.py`, `loomis_head/features_dialog.py` | Per-face orientation (azimuth of the normal, no directional light) neutral fill for **Shade planes** (`shadePlanes`, opacity 0.18–0.28), `show_neck` filtering per-face `neck` flags. |
| Mesh tests | `loomis_head/test_asaro.py` | Suite 82 (40 generator + 42 Asaro): proportions, profile landmarks, neck toggle and cap, shade on/off, detail levels, JSON round-trip, no degenerate faces/NaN. |

### 0.7.4 — clean retopology, invisible pivot, 500 ms redraw (commit `3123829`)

| Area | Files | What |
| --- | --- | --- |
| Retopo mesh | `loomis_head/asaro_clean_mesh.py` (new) | Hand retopology over the silhouette of the real bust: each row is a flow line with its own height per column instead of a stacked ring. **122 / 242 / 272 faces** at detail 0 / 1 / 2 (head + neck and base), 131 / 257 / 289 vertices. Mouth band of three rows, ear with a hollow concha and a standing helix, and banded temple/cheekbone/orbital/mastoid planes; the mesh stays closed. `asaro_mesh.py` stays as the decimated reference for tests and is no longer drawn. |
| Pivot | `loomis_head/loomis_head_generator.py`, `loomis_head/asaro.py` | `pivot_local`: sphere centre for Loomis; area centroid of the head faces (neck and base excluded) for Asaro, `(0.0, 0.2852, -0.0354)` in mesh coordinates, so it does not jump between detail levels. `position_x/y` is the **pivot position in the document**; `build_svg` subtracts it before rotating. |
| Pivot marker | `loomis_head/loomis_head_plugin.py` | An invisible `loomis-pivot` circle is added to the layer after the head SVG; its absolute centre tracks manual canvas moves, and the delta is applied **once** to `position_x/y` (1:1, no factor of 2, no bounds). |
| Redraw delay | `loomis_head/loomis_head_plugin.py`, `features_dialog.py`, `translations/*.json` | Canvas debounce 220 → **500 ms**, single shot, restarted on every change; `valueChanged` no longer redraws, the docker preview stays live. |
| Tests | `loomis_head/test_generator.py`, `loomis_head/test_asaro.py` | 121 tests (44 generator + 77 Asaro). |
| Assets licence | `LICENSE-ASSETS.md` (new), `CREDITS.md` | Asaro meshes are **CC BY 4.0** (derivative of "Asaro-head" by ivan4akir, design by John Asaro); code stays GPL-3.0-only. |

### 0.7.5 – 0.7.10 — Move, pivot and base/delta (commits `39c8b12` … `01ca3ac`)

| Area | Files | What |
| --- | --- | --- |
| Sync before redraw | `loomis_head/loomis_head_plugin.py` | `draw_lines_with_vectors()` calls `sync_manual_position()` **before** deleting and recreating the shapes (0.7.5), so touching the docker no longer sends the head back to its old X/Y. |
| Delay input | `loomis_head/loomis_head_plugin.py`, `features_dialog.py` | **Delay** spinbox (50–5000 ms, step 50, default 500) under View, saved as `redrawDelay` in `settings.json`, changes the timer interval live; no flush on `sliderReleased`. |
| Move source | `loomis_head/loomis_head_plugin.py` | The pivot marker is the primary reference for a manual Move (0.7.7; layer `Node.position()` alone under-read a real move) and the layer position is the fallback. `pivot.log` records every sync/draw. |
| Manual transform | `loomis_head/loomis_head_plugin.py` | `_capture_manual_transform()` / `_apply_manual_transform()` reapply the user's Move to every new shape; `transform` in `guides.json` and `layerTransform` in the head state/preset persist it (0.7.8). |
| Base + delta | `loomis_head/loomis_head_plugin.py` | 0.7.9 treated the SVG importer's layer scale (0.24 at 300 ppi) as the user's Move and squared it; 0.7.10 separates **base** (captured right after `addShapesFromSvg`, never persisted) from **delta** (`current ∘ base⁻¹`), applies `delta ∘ base` once, migrates 0.7.8/0.7.9 absolute values on load and keeps X/Y in document pixels. |
| Regression tests | `loomis_head/test_generator.py`, `loomis_head/test_ui_offscreen.py` | 153 tests (76 generator + 77 Asaro) plus a reproducible docker test; the 0.7.5–0.7.8 checks were ad hoc flatpak scripts and are not in the repo. |

### 0.7.11 — vector-layer refresh fix (local, no commit message id)

| Area | Files | What |
| --- | --- | --- |
| Layer re-render | `loomis_head/loomis_head_plugin.py` | Rotating or moving drew the head cut by a straight vertical line (or not at all) until the `.kra` was reopened. The SVG and the shapes were correct; Krita only invalidated the rectangle each shape reports, so new geometry outside it never reached the canvas or the save. `_force_layer_rerender()` toggles `setAntialiased()` to drop the layer cache and calls `Document.refreshProjection()`, right after the delta is reapplied; it never raises and logs `rerender=aa=…,refresh=…`. |
| Evidence | — | A saved `.kra` (2560×1440 at 300 ppi) had `layers/layer2.shapelayer/content.svg` with the full geometry (bbox x 1008–1279 px) while its `mergedimage.png` was cut at x 1178: the file was right, the projection was stale. |
| Tests | `loomis_head/test_ui_offscreen.py` | 7 OK offscreen (was 5): the antialias toggle restores the original value and refreshes the projection once, and a layer without `isAntialiased()` with a document without `refreshProjection()` does not raise. |

### 0.7.12 — Grimoire of Color compatibility (working tree)

| Area | Files | What |
| --- | --- | --- |
| File mode | `loomis_head/loomis_head_plugin.py` | `_write_head_to_grimorio()` recreated `grimorio.json` through a new temp file and left it at **0644**, downgrading the 0600 that the Grimoire sets (`privateMode` and private data live there). It now reads the original mode and applies it to the temp file before `os.replace()` and to `grimorio.json.loomis.bak`, falling back to `0o600`. |
| Head block merge | `loomis_head/loomis_head_plugin.py` | `target["head"] = data` replaced the whole block and dropped `lightAzimuth`, `lightElevation`, `lightIntensity`, `shadowMode`, `showShadow` and any unknown key. The previous block is now **merged** with the new one, new values win. |
| Tests | `loomis_head/test_ui_offscreen.py` | 9 OK offscreen (was 7): preserves 0600 on JSON and backup, and keeps `lightAzimuth`/`futureKey` while `scale` becomes 1.0. The unit suite stays at 153 OK. |

## How to apply

```bash
git clone <fork-url> loomis-head-guide
cd loomis-head-guide
git checkout b8a762d

# Preferred: git knows about new files and modes
git apply --check release/loomis-head-guide-0.7.12.patch
git apply release/loomis-head-guide-0.7.12.patch

# GNU patch also works (the patch is plain text, no binary hunks)
patch -p1 < release/loomis-head-guide-0.7.12.patch
```

The patch creates `loomis_head/models.py`, `asaro.py`, `asaro_mesh.py`,
`asaro_clean_mesh.py`, `qt_compat.py`, `test_asaro.py`, `test_ui_offscreen.py`,
`heads/example-asaro.json`, `loomis_head/heads/example-asaro.json`, `LICENSE-ASSETS.md`
and the CI workflow changes, and edits the existing sources in place. No file is deleted
(0.6.1 already deleted the light module before this base-to-tip range; nothing in the
range needs a deletion).

If you only want the new head engine without the fork's UI changes, take `models.py`,
`asaro.py`, `asaro_mesh.py`, `asaro_clean_mesh.py`, `qt_compat.py` and `test_asaro.py`;
they do not import the docker.

## What this patch does NOT include

- `docs/media/promo.png` (636 KB binary cover), `release/*.zip` and `release/*.patch`
  (built artifacts), and `release/UPSTREAM-*` / `release/README*` (handoff notes). They are
  excluded so the patch stays pure text and applies with `patch -p1`; the binaries add
  nothing to a code review. They live in the fork's repository.
- **The Grimoire of Color plugin.** The fork only *detects* `grimorio.json`, lists its
  characters and writes the `head` block (with a `.bak`). No Grimoire code ships here and
  the plugin works fully standalone.
- **The directional light / shadow.** It existed in 0.6.0 and was removed in 0.6.1; it is
  not part of this tip. The docker has five tabs: Settings, Move, Guides, Features, Hair.
  The neutral per-face shade of Asaro is a plane reading, not a directional light.
- **No Krita C++ changes.** The undo limitation is documented, not fixed (see
  `README-UPSTREAM.md`).

## License

- Project: **GPL-3.0-only** (`LICENSE`). Contributions are accepted under the same license.
- `euclid.py`: **LGPL-2.1** (upstream file, kept as is).
- **Asaro mesh**: **CC BY 4.0**, not relicensed as GPL. It is a decimated and
  retopologised derivative of "Asaro-head" by **ivan4akir** (CC BY 4.0), whose design is by
  **John Asaro**. Keep the attribution and the modification notice (`LICENSE-ASSETS.md`).
- Lineage: Loomis Head Generator by **lm0ss** (2025) → Loomis Method Head Guide by
  **Nedeljko Umjetnik** (2026) → this fork by **imboolean** (2026). See `CREDITS.md`.
