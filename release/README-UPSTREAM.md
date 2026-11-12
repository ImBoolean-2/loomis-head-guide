# Loomis Head Guide 0.7.13 — handoff notes

For **Nedeljko Umjetnik**, upstream author of the Loomis Method Head Guide. This fork
starts from your 0.5.0 (`b8a762d`) and adds the work below. `release/UPSTREAM-DIFF-0.7.13.md`
explains the diff; this file is the short version: what you get, what to watch out for and
how to try it. The user-facing notes are in `RELEASE-NOTES-0.7.13.md` (Spanish).

## What is new since 0.5.0

1. **Tabbed docker with a fixed top block** (0.5.1): head selector, 3D preview, view
   selector, library and actions stay put; Settings, Move, Guides, Features and Hair
   scroll inside tabs. Panels follow the active head. QAM compatibility fixed.
2. **Parametric head** (0.6.0): forehead height, jaw angle, cranium width/height,
   cheekbone height and chin sharpness, all in JSON; independent brow/eye/nose/mouth guide
   toggles; optional Reilly rhythm curves.
3. **Head sex and structure** (0.6.1): male/female presets, orbital socket with rim and
   inner floor, superciliary brow ridge, cheek-fill curve.
4. **Two head models** (0.7.0): a model registry (`loomis_head/models.py`) and a second
   engine, **Asaro** (`asaro.py`), a low-poly planar head drawn as face contours.
5. **Model switch that keeps each model's state** (0.7.0): a **Model** combo above the
   Features panel; switching stashes the outgoing model's full state and restores the
   incoming one, then re-applies the shared transform so the guide never jumps. The
   inactive states travel in `guides.json` under `models`.
6. **PyQt5/PyQt6 shim** (0.7.0): every module imports Qt from `qt_compat.py`, which also
   maps the unscoped enums PyQt6 removed.
7. **Quieter undo** (0.7.0 → 0.7.5): redraw debounce 40 → 220 → **500 ms**, now exposed as a
   **Delay** spinbox (50–5000 ms). See the limits below.
8. **Asaro profile mesh** (0.7.1): the Asaro head was reshaped so the *profile* reads too —
   forehead, brow, socket, nose, cheekbone, jaw, chin and occiput, with measured landmarks
   (nose tip and nasion step, socket depth, chin/lip step, rounded occiput and nape).
9. **Asaro bust with neck** (0.7.2): the mesh is rebuilt as a proportioned bust — height
   1.5, ear-to-ear ~1.01 (ratio 1.485), crown-to-chin depth 0.714 of the head, face 44 % and
   neck 30 % — with a **Show neck** toggle (`showNeck`, on by default) that caps the jaw
   when off.
10. **Exact Asaro mesh** (0.7.3): the drawn mesh becomes a decimation of the real
    `Asaro_high.obj`, stored as static data in `asaro_mesh.py` (no OBJ at runtime), with
    per-face orientation shading and a per-face neck flag. 334 / 634 / 1195 faces.
11. **Clean retopology** (0.7.4): a hand retopo over the real silhouette replaces the
    decimation — **122 / 242 / 272 faces**, flow-line rows, three-row mouth band, ear with
    concha and banded temple/cheekbone/orbital/mastoid planes. `asaro_mesh.py` stays as the
    test reference.
12. **Invisible pivot and 1:1 Move** (0.7.4): `position_x/y` is the centre of the skull
    (Asaro: area centroid of the head faces, neck and base excluded) and an invisible
    `loomis-pivot` circle tracks a manual canvas Move, so rotating, switching model or
    touching the docker keeps the head where you put it.
13. **Delay input and sync before redraw** (0.7.5–0.7.6): `sync_manual_position()` runs
    before the shapes are deleted and rebuilt, and **Delay** (500 ms by default) is saved in
    `settings.json`. `pivot.log` records every sync and draw for diagnosis.
14. **Move persistence and layer reset** (0.7.7–0.7.8): the marker is the primary reference
    for a real Move, the user's transform is captured from `Shape.transformation()` and
    reapplied to every new shape, and it is stored as `transform` in `guides.json` and
    `layerTransform` in the head state/preset.
15. **Base/delta fix** (0.7.9–0.7.10): 0.7.9 mistook the SVG importer's layer scale
    (0.24 at 300 ppi) for the user's Move and squared it; 0.7.10 captures the **base** right
    after `addShapesFromSvg`, keeps only the **delta** (`current ∘ base⁻¹`) and applies
    `delta ∘ base` once. 0.7.8/0.7.9 absolute values are migrated on load. The docker X/Y
    is the effective position in document pixels.
16. **Cut head fixed** (0.7.11): rotating or moving drew the head cut by a vertical line
    until the document was reopened. The SVG was correct (a saved `.kra` had the full
    geometry in `content.svg`, x 1008–1279 px, while `mergedimage.png` was cut at x 1178);
    what was stale was the vector layer cache/projection. `_force_layer_rerender()` toggles
    `setAntialiased()` and calls `Document.refreshProjection()` after each rebuild.
17. **Grimoire of Color 0.7.0** (0.7.12): `grimorio.json` and its backup keep their **0600**
    mode instead of being downgraded to 0644, and the `head` block is **merged** instead of
    replaced, so `lightAzimuth`/`lightElevation`/`lightIntensity`/`shadowMode`/`showShadow`
    and unknown future keys survive a save from Loomis.
18. **Features tab fits the docker** (0.7.13): the *Show* row of the Features tab asked for
    ~690 px while the docker is ~520 px wide, so its last checkboxes were clipped; the flags
    now wrap in a 2-column grid (panel minimum 678 → 458 px) with the order and toggles
    unchanged.

> **Asaro is still a work in progress: low-poly profile, cranium and ear; configuration is
> minimal.** It is a plane block-in, not a proportion reference. Loomis is the main engine.

## Compatibility

- **Head JSON**: 0.5.1, 0.6.0 and 0.6.1 heads load unchanged; missing keys fall back to
  defaults. Asaro heads use the same wrapper with `"model": "asaro"` and
  `generator: "asaro"` inside `head`; a 0.7.1 Asaro head without `showNeck` loads with the
  neck on, and 0.7.8/0.7.9 `transform` values are migrated to the base/delta form once
  (`"transformIsDelta": true`), so they are never migrated twice.
- **Share format**: `format: "loomis-head"`, `model` is `loomis` **or** `asaro`. The
  loader resolves the model through `create_model()`; an unknown model is reported and the
  head is not loaded.
- **Grimoire of Color**: the `head` block stays opaque and unchanged in shape, so the
  Grimoire keeps storing, exporting and importing it; 0.7.12 also preserves its file mode
  and unknown keys.
- **Krita**: tested on Krita **5.3.4.1** (Flatpak, PyQt5). Krita 6 / PyQt6 is supported in
  code but **not tested on a real Krita 6** (no PyQt6 build available here).

## How to test

```bash
# 1. Unit tests, no Krita/Qt needed (153 tests: 76 Loomis + 77 Asaro)
cd loomis_head
python3 -m unittest test_generator test_asaro

# 2. Docker test, needs Qt but not Krita (11 tests in Krita's flatpak; SKIP otherwise)
flatpak run --env=QT_QPA_PLATFORM=offscreen --env=QT_QPA_PLATFORMTHEME= \
  --command=python3 --filesystem=home --filesystem=/tmp org.kde.krita \
  loomis_head/test_ui_offscreen.py

# 3. Install
cp -r loomis_head loomis_head.desktop \
  ~/.var/app/org.kde.krita/data/krita/pykrita/
# or: Tools → Scripts → Import Python Plugins → release/loomis-head-guide-0.7.13.zip
```

Then in Krita:

1. Enable the docker and check the **Model** combo says *Loomis*.
2. Rotate/move/scale the head, switch to **Asaro**: the guide keeps its place and size.
3. In Asaro, toggle **planes**, **edges** and **Shade planes** and change **detail**; the
   mesh contours change (122 / 242 / 272 faces). Toggle **Show neck**: the bust gains or
   loses the neck and the head stays closed. Guides and Hair tabs are disabled, and the
   Loomis-only rows are hidden.
4. Switch back to Loomis: your Loomis features and hair are still there.
5. Move the layer with Krita's **Move** tool, then rotate: the head stays where you put it
   and X/Y shows the effective position. Set **Delay** to 50 ms and drag a slider: the
   canvas redraws almost immediately; at 500 ms it waits until you stop.
6. Save the `.kra`, restart Krita, reopen it: both models' states and the Move come back.
7. If the Grimoire of Color is installed, save a head to a character and check that
   `grimorio.json` is still `0600` and keeps keys Loomis does not know.

## Known limits

- **PyQt6 is untested on Krita 6.** `qt_compat.py` was checked by simulating the PyQt6
  enum/signature differences, not by running Krita 6. Expect small fixes; the shim is the
  single place to make them.
- **No real undo macro.** `krita.pyi` in 5.3.4 exposes neither `beginUndo`/`endUndo` nor
  `KUndo2Command`, so each redraw (`shape.remove` + `addShapesFromSvg`) still leaves its own
  undo entries. The 500 ms delay reduces the noise; grouping them into one step needs C++
  (or a layer swap that Krita groups, which would break `Guide.layer`/`guides.json`). This
  is documented debt, not a silent bug.
- **The Asaro head is still a work in progress.** Since 0.7.4 it is a hand retopology over
  the real bust with 122 / 242 / 272 faces, but it remains a low-poly plane study: the
  profile, the cranium vault and the ear are faceted, the transitions between planes are
  coarse at detail 0, and its panel offers only planes, edges, shading, detail and neck —
  no fine control of planes or proportions. It is a block-in reference, not a smooth
  sculpt. Its Loomis setters are no-ops so the shared UI does not crash.
- **No light/shadow.** The 0.6.0 directional light was withdrawn in 0.6.1 and is not
  coming back in this fork. Asaro's neutral per-face shade is a plane reading, not a light.
- **Licences.** `euclid.py` is still LGPL-2.1 and the code is GPL-3.0-only. The Asaro mesh
  data in `asaro_mesh.py` / `asaro_clean_mesh.py` is **CC BY 4.0**, not GPL: it is a
  decimated and retopologised derivative of "Asaro-head" by **ivan4akir** (CC BY 4.0),
  design by **John Asaro** (`LICENSE-ASSETS.md`).

## Feedback

If you want any of this upstream, the pieces are independent: `models.py` + `asaro.py` +
`asaro_mesh.py` + `asaro_clean_mesh.py` + `qt_compat.py` + `test_asaro.py` do not import
the docker, so they can be lifted alone.
