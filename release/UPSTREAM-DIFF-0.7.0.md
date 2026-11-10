# Upstream diff: 0.5.0 → 0.7.0

This document describes `release/loomis-head-guide-0.7.0.patch`, a cumulative diff of the
imboolean fork on top of **Nedeljko Umjetnik's Loomis Method Head Guide 0.5.0**.

## Base of the diff

- Base commit: `b8a762d` — *Loomis Head Guide 0.5.0: independent fork with multi-head
  state, 3D preview and i18n*.
- Generated with `git diff b8a762d`, with `git add -N` for the new files so they appear as
  additions.
- Size: **28 files, +2973 / −227** lines.
- The patch is cumulative: it contains 0.5.1, 0.6.0, 0.6.1 and 0.7.0 in one step. It is
  meant to be applied on a clean 0.5.0 tree, not on an already-patched one.

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

### 0.7.0 — head models, Asaro, Qt6 shim (this patch)

| Area | Files | What |
| --- | --- | --- |
| Model registry | `loomis_head/models.py` (new) | `MODELS`, `DEFAULT_MODEL`, `create_model()`, `supported_models()`; the only module that knows every implementation |
| Asaro head | `loomis_head/asaro.py` (new) | Low-poly planar head (~40 faces), orthographic projection, painter's algorithm, `show_planes` / `show_edges` / `detail`, JSON round-trip, Loomis-compatible no-op interface |
| Asaro tests | `loomis_head/test_asaro.py` (new) | 13 tests (round-trip, SVG validity, rotation, flags, interface compatibility, registry) |
| Qt5/Qt6 shim | `loomis_head/qt_compat.py` (new) | Single import point for Qt; maps the unscoped enums PyQt6 removed, `exec_dialog()`, `EXPANDING`, `activated_index()` |
| Model switch | `loomis_head/loomis_head_plugin.py` | Model combo + `QStackedWidget`, `AsaroPanel`, per-model stash (`guides.json` → `models`), common transform copied on switch, Guides/Hair tabs disabled and Loomis-only rows hidden for Asaro |
| Asaro panel | `loomis_head/features_dialog.py` | `AsaroPanel` (planes, edges, detail) next to `FeaturePanel`/`HairPanel` |
| Undo mitigation | `loomis_head/loomis_head_plugin.py` | Redraw debounce 40 → 220 ms, immediate flush on `sliderReleased`; no real undo macro (see limits) |
| i18n | `loomis_head/i18n.py`, `translations/*.json` | Imports through `qt_compat`; `model.*`, `asaro.*`, `status.model_switched`, `error.model_unknown` in en/es/pt/fr |
| Share format | `heads/README.md`, `heads/example-asaro.json`, `loomis_head/heads/*` | `model` may be `loomis` or `asaro`; the loader resolves it through the registry; packaged copy kept in sync |
| Docs | `README.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `release/README.md` | Version, features, architecture and release notes |

## How to apply

```bash
git clone <fork-url> loomis-head-guide
cd loomis-head-guide
git checkout b8a762d

# Preferred: git knows about new files and modes
git apply --check release/loomis-head-guide-0.7.0.patch
git apply release/loomis-head-guide-0.7.0.patch

# GNU patch also works (the patch is plain text, no binary hunks)
patch -p1 < release/loomis-head-guide-0.7.0.patch
```

The patch creates `loomis_head/models.py`, `asaro.py`, `qt_compat.py`, `test_asaro.py`,
`heads/example-asaro.json` and the packaged `loomis_head/heads/example-asaro.json`, and
edits the existing sources in place. No file is deleted (0.6.1 already deleted the light
module before this base-to-tip range; nothing in the range needs a deletion).

If you only want the new head engine without the fork's UI changes, take `models.py`,
`asaro.py`, `qt_compat.py` and `test_asaro.py`; they do not import the docker.

## What this patch does NOT include

- `docs/media/promo.png` (636 KB binary cover) and `release/*.zip` (built artifacts). They
  are excluded so the patch stays pure text and applies with `patch -p1`; the binaries add
  nothing to a code review. The cover lives in the fork's repository.
- **The Grimoire of Color plugin.** The fork only *detects* `grimorio.json`, lists its
  characters and writes the `head` block (with a `.bak`). No Grimoire code ships here and
  the plugin works fully standalone.
- **The directional light / shadow.** It existed in 0.6.0 and was removed in 0.6.1; it is
  not part of this tip. The docker has five tabs: Settings, Move, Guides, Features, Hair.
- No Krita C++ changes. The undo limitation is documented, not fixed (see
  `README-UPSTREAM.md`).

## License

- Project: **GPL-3.0-only** (`LICENSE`). Contributions are accepted under the same license.
- `euclid.py`: **LGPL-2.1** (upstream file, kept as is).
- Lineage: Loomis Head Generator by **lm0ss** (2025) → Loomis Method Head Guide by
  **Nedeljko Umjetnik** (2026) → this fork by **imboolean** (2026). See `CREDITS.md`.
