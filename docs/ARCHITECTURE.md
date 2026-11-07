# Architecture

The plugin is a Krita Python docker with a pure-Python head generator. Krita is only
needed by the docker and the preview widget; the geometry and its tests do not import it.

## Files

| File | Role |
| --- | --- |
| `loomis_head_generator.py` | Pure Python Loomis geometry, parameters, `to_dict`/`from_dict`, SVG |
| `loomis_head_plugin.py` | Docker, Krita integration, guide manager, presets, Grimoire bridge |
| `preview.py` | `QSvgRenderer` preview and arcball rotation |
| `features_dialog.py` | `FeaturePanel`: caricature, feature lines, hair; embedded in the docker |
| `i18n.py` + `translations/*.json` | Language override/locale and strings |
| `linalg.py`, `euclid.py`, `geom_polyline.py` | Math and SVG path helpers |
| `trackball.py` | Legacy widget kept for reference (the preview replaces it) |

## Guide manager

- A `Guide` is one head: a `LoomisHead3D`, one vector layer `Loomis Head N`, a name and
  the last known layer centre.
- `ensure_guide()` adopts existing `Loomis Head*` layers before creating anything. On the
  first run it migrates the old repeated `Loomis Method Head Guide` layers, keeping the
  topmost one and removing the duplicates (undoable in Krita).
- Each document has its own state, keyed by `Document.fileName()`. Unsaved documents use
  a session key and do not survive a restart.
- `_set_active_guide()` applies the delta between the layer's current centre and the
  saved centre, so a head moved while inactive does not jump back. It also calls
  `Document.setActiveNode()`.

## State files

In Krita's app data directory (`QStandardPaths.AppDataLocation`):

```text
loomis_head/
├── settings.json   language
├── presets.json    named presets and per-OC presets
└── guides.json     per-document guides: state + centre + active index
```

Positions in `guides.json` and presets are normalised (0–1 of the document size) so they
survive canvas size changes. The model stores document pixels; the docker converts.

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
- **Head models**: the share format has `model`; a new engine must expose
  `build_svg(width, height, samples)` and reject unknown models in the loader.
