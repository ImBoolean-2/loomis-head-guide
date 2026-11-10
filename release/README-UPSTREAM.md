# Loomis Head Guide 0.7.0 — handoff notes

For **Nedeljko Umjetnik**, upstream author of the Loomis Method Head Guide. This fork
starts from your 0.5.0 (`b8a762d`) and adds the work below. `release/UPSTREAM-DIFF-0.7.0.md`
explains the diff; this file is the short version: what you get, what to watch out for and
how to try it.

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
   incoming one, then re-applies the shared transform (scale, position, rotation, strokes)
   so the guide never jumps. The inactive states travel in `guides.json` under `models`.
6. **PyQt5/PyQt6 shim** (0.7.0): every module imports Qt from `qt_compat.py`, which also
   maps the unscoped enums PyQt6 removed.
7. **Quieter undo** (0.7.0): redraw debounce 40 → 220 ms with an immediate flush on
   `sliderReleased`. See the limits below.

## Compatibility

- **Head JSON**: 0.5.1, 0.6.0 and 0.6.1 heads load unchanged; missing keys fall back to
  defaults. Asaro heads use the same wrapper with `"model": "asaro"` and
  `generator: "asaro"` inside `head`.
- **Share format**: `format: "loomis-head"`, `model` is now `loomis` **or** `asaro`. The
  loader resolves the model through `create_model()`; an unknown model is reported and the
  head is not loaded.
- **Grimoire of Color**: the `head` block stays opaque and unchanged in shape, so the
  Grimoire keeps storing, exporting and importing it.
- **Krita**: tested on Krita **5.3.4.1** (Flatpak, PyQt5). Krita 6 / PyQt6 is supported in
  code but **not tested on a real Krita 6** (no PyQt6 build available here).

## How to test

```bash
# 1. Unit tests, no Krita/Qt needed (53 tests: 40 Loomis + 13 Asaro)
cd loomis_head
python3 -m unittest test_generator test_asaro

# 2. Install
cp -r loomis_head loomis_head.desktop \
  ~/.var/app/org.kde.krita/data/krita/pykrita/
# or: Tools → Scripts → Import Python Plugins → release/loomis-head-guide-0.7.0.zip
```

Then in Krita:

1. Enable the docker and check the **Model** combo says *Loomis*.
2. Rotate/move/scale the head, switch to **Asaro**: the guide keeps its place and size.
3. In Asaro, toggle **planes** and **edges** and change **detail**; the mesh contours change.
   Guides and Hair tabs are disabled, and the Loomis-only rows (side cut, face age, chin
   width) are hidden.
4. Switch back to Loomis: your Loomis features and hair are still there.
5. Save the `.kra`, restart Krita, reopen it: both models' states come back.
6. Drag a slider: the 3D preview follows live, the vector layer redraws once you pause or
   release the slider.

## Known limits

- **PyQt6 is untested on Krita 6.** `qt_compat.py` was checked by simulating the PyQt6
  enum/signature differences, not by running Krita 6. Expect small fixes; the shim is the
  single place to make them.
- **No real undo macro.** `krita.pyi` in 5.3.4 exposes neither `beginUndo`/`endUndo` nor
  `KUndo2Command`, so each redraw (`shape.remove` + `addShapesFromSvg`) still leaves its own
  undo entries. The 220 ms debounce and the flush on release reduce the noise; grouping them
  into one step needs C++ (or a layer swap that Krita groups, which would break
  `Guide.layer`/`guides.json`). This is documented debt, not a silent bug.
- **The Asaro head is intentionally loose.** It is a ~40-face planar study for construction,
  not an anatomical model: no ears, no neck, no hair, no light/shadow. Its Loomis setters
  (`set_sidecut`, `set_show_face`, …) are no-ops so the shared UI does not crash.
- **No light/shadow.** The 0.6.0 directional light was withdrawn in 0.6.1 and is not
  coming back in this fork.
- `euclid.py` is still LGPL-2.1; everything else in the fork is GPL-3.0-only.

## Feedback

If you want any of this upstream, the pieces are independent: `models.py` + `asaro.py` +
`qt_compat.py` + `test_asaro.py` do not import the docker, so they can be lifted alone.
