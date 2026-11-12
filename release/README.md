# Release

`loomis-head-guide-0.7.12.zip` is the installable package, and the **last public build**:
0.7.3 to 0.7.11 stayed local, so there is no ZIP or patch for them. Its root contains
`loomis_head/` and `loomis_head.desktop`, so Krita's **Tools → Scripts → Import Python
Plugins** accepts it directly.

The ZIP is built from the `loomis_head/` folder in this repository:

```bash
cd ..
zip -r release/loomis-head-guide-0.7.12.zip loomis_head loomis_head.desktop \
  -x '*/__pycache__/*' '*.pyc' '*.bak*'
```

## What changed since 0.7.2

- **Real Asaro mesh**: the drawn mesh is a hand retopology over the real bust, **122 / 242 /
  272 faces** at detail 0 / 1 / 2, with a mouth band, an ear with concha, plane banding and
  **Shade planes**. The 0.7.3 decimation stays in `asaro_mesh.py` as a test reference.
- **Invisible pivot**: rotating or switching model/type/sex keeps the head in place; an
  invisible `loomis-pivot` marker tracks a manual canvas Move 1:1.
- **Move survives a redraw**: the SVG importer's layer **base** scale and the user's Move
  **delta** are kept apart, so the Move survives rotations, model switches, presets and a
  reopened `.kra`. The docker X/Y is the effective position in document pixels.
- **Delayed redraw**: the canvas redraws after the **Delay** set in the panel (500 ms by
  default, 50–5000 ms); the 3D preview stays live.
- **Cut head fixed**: a vector-layer cache/projection refresh ends the head drawn cut by a
  vertical line until the document was reopened.
- **Grimoire of Color 0.7.0**: keeps `grimorio.json` at 0600 and merges the `head` block
  instead of replacing it, so unknown keys (the 0.6.0 light) are not lost.

> **Asaro is still a work in progress.** The profile, the cranium vault and the ear are
> low-poly, the plane transitions are coarse at detail 0 and its panel is minimal. Use it as
> a plane block-in; Loomis is the main engine. Details in `RELEASE-NOTES-0.7.12.md`.

## Other files

- `loomis-head-guide-0.7.12.patch` — cumulative diff from the 0.5.0 base (`b8a762d`) to
  0.7.12, including the uncommitted 0.7.12 fixes. See `UPSTREAM-DIFF-0.7.12.md` for how to
  apply it and what it excludes.
- `UPSTREAM-DIFF-0.7.12.md` — per-area summary of the diff and its base.
- `README-UPSTREAM.md` — handoff for the upstream author: features, compatibility, how to
  test and known limits (PyQt6 untested, undo without a macro, Asaro still low-poly).
- `RELEASE-NOTES-0.7.12.md` — user-facing release notes, **in Spanish**.
- `loomis-head-guide-0.7.2.*` and older (`0.7.1`, `0.7.0`, `0.6.x`, `0.5.x`, their
  `UPSTREAM-DIFF-*.md`) — kept as history.

## Checks before publishing

```bash
cd loomis_head && python3 -m unittest test_generator test_asaro   # 153 tests in 0.7.12

# docker test: SKIP on a host without PyQt5, real offscreen run in Krita's flatpak
flatpak run --env=QT_QPA_PLATFORM=offscreen --env=QT_QPA_PLATFORMTHEME= \
  --command=python3 --filesystem=home --filesystem=/tmp org.kde.krita \
  loomis_head/test_ui_offscreen.py                                # 9 tests in 0.7.12

cd .. && unzip -l release/loomis-head-guide-0.7.12.zip | grep -E 'models|asaro|qt_compat'
```

The patch is verified on a clean export, not on the working tree:

```bash
rm -rf /tmp/apply && mkdir -p /tmp/apply
git archive b8a762d | tar -x -C /tmp/apply
cd /tmp/apply && git init -q . && git add -A && git commit -qm base
git apply --check -p1 /path/to/release/loomis-head-guide-0.7.12.patch
git apply -p1 /path/to/release/loomis-head-guide-0.7.12.patch
cd loomis_head && python3 -m unittest test_generator test_asaro   # 153 OK
```
