# Loomis Head Guide for Krita

A free, local **Loomis-method head construction guide** for Krita: rotate a 3D head,
customize the skull, face features, hair and caricature, save per-character presets and
share head files with other artists.

This is a fork of [Nedeljko Umjetnik's Loomis Method Head Guide](https://nedeljko-umjetnik.itch.io/loomis-method-head-guide-plugin-for-krita),
which is based on [lm0ss's Loomis Head Generator](https://github.com/lm0ss/loomis-head-krita).
The improvements in this fork are by **imboolean** (see [CREDITS.md](CREDITS.md)).

![Animated head preview](docs/media/hero.gif)

| Front | 3/4 | Back |
| --- | --- | --- |
| ![Front](docs/media/head-front.png) | ![3/4](docs/media/head-three-quarter.png) | ![Back](docs/media/head-back.png) |

| Hair patterns | Zone colours |
| --- | --- |
| ![Hair patterns](docs/media/hair-patterns.png) | ![Zone colours](docs/media/zone-colors.png) |

![Panel mockup](docs/media/panel.png)

> The head images and GIF are real renders produced by the plugin's generator. The panel
> image is an HTML mockup of the docker layout (a real Krita screenshot would be even
> better; contributions welcome). The HTML source is in
> [`docs/media/panel-preview.html`](docs/media/panel-preview.html).

## Features

- **Tabbed docker**: the head, 3D preview, view selector, library and action buttons stay
  fixed; Settings, Move, Guides, Features and Hair live in scrollable tabs.
- **Real 3D preview**: drag to orbit freely (arcball), `Shift`/right-drag to roll, wheel to
  zoom, double-click to reset. View shortcuts for front, 3/4, profile, back and top.
- **Individual axes**: X/Y/Z rotation sliders and spinboxes; moving one axis does not
  touch the others.
- **Loomis construction**: sphere, side cut, jaw, chin, cheekbones, brow/eye/nose/mouth
  lines, eye sockets, brows, nose, ears and mouth. Brow, eye, nose and mouth guide lines
  can be shown or hidden independently.
- **Head sex and structure**: male/female presets that combine with the head style; a
  sunken orbital socket (rim, inner floor and depth ticks), a superciliary brow ridge and a
  cheek-fill curve make the skull read in 3D.
- **Parametric proportions**: forehead height, jaw angle, cranium width/height, cheekbone
  height and chin sharpness, plus caricature and head-type presets.
- **Reilly rhythm curves**: optional crown→brow→nose→mouth→chin flow lines and lateral
  arches, with adjustable strength.
- **Caricature and head types**: realistic, semi, anime, chibi and caricature presets;
  cranium, jaw, cheek, face width and jaw drop are adjustable.
- **Custom hair**: hairline, arch, tilt, part position, part pattern (straight, zigzag,
  spiky) and texture (smooth, wavy, spiky, curly).
- **Zone colours**: cranium, jaw, cheek, features, hair and side guides use different
  colours so each part reads at a glance.
- **Several independent heads per document**: one vector layer (`Loomis Head N`) per
  head, a head selector, add/delete, and automatic selection of its layer in Krita.
- **Per-document state**: position, rotation, scale, features and hair are saved in
  `guides.json` and restored after restart for saved `.kra` files.
- **Presets**: named presets and presets linked to a Grimoire of Color character.
- **Shareable heads**: load/export a head as JSON (`format`, `model`, `name`, `author`,
  `license`, `tags`, `head`). See [`heads/`](heads/README.md).
- **Languages**: English, Spanish, Portuguese and French with a language selector in the
  panel; the choice is remembered.
- **Standalone or integrated**: works on its own; if
  [Grimoire of Color](https://github.com/ImBoolean-2/color-grimoire) is installed it can
  also save the head into the active OC.

## Install

### ZIP (recommended)

1. Download `release/loomis-head-guide-0.6.1.zip`.
2. In Krita: **Tools → Scripts → Import Python Plugins** and choose the ZIP.
3. Restart Krita and open **Settings → Configure Krita → Python Plugin Manager**; enable
   **Loomis Method Head Guide**.

### Manual

Copy `loomis_head/` and `loomis_head.desktop` into Krita's `pykrita` directory, restart
Krita and open **Settings → Dockers → Loomis Head Guide**.

Linux Flatpak example:

```bash
cp -r loomis_head loomis_head.desktop \
  ~/.var/app/org.kde.krita/data/krita/pykrita/
```

Tested with Krita **5.3.4.1** (Flatpak, PyQt5). Krita 6 (PyQt6) is not supported yet.

## Languages

The panel has a **Language** selector (`Auto`, English, Español, Português, Français)
and remembers the choice in `settings.json`. `LOOMIS_LANG=es|en|pt|fr` still works as an
override. Translations are plain JSON files in `loomis_head/translations/`; adding a
language is a JSON file plus one entry in `SUPPORTED` in `i18n.py`.

## Standalone and with Grimoire of Color

- **Standalone**: presets (`presets.json`), head state (`guides.json`), settings
  (`settings.json`) and head JSON files live in Krita's app data directory. Nothing from
  the Grimoire is required. The OC row is disabled with a "Grimoire not detected" message.
- **Together**: if `grimorio.json` exists, the panel lists its characters; saving to an OC
  writes only the character's `head` block (with a `grimorio.json.loomis.bak` backup) and
  also keeps the sidecar preset. The Grimoire treats `head` as an opaque block, so it
  travels in Export/Import and the web app shows a small summary.

Data paths (Flatpak example):

```text
~/.var/app/org.kde.krita/data/loomis_head/
├── presets.json    named presets + per-OC presets
├── guides.json     per-document head state (position, rotation, parameters)
└── settings.json   language
```

## Share a head

Use **Export head…** in the Library section. The JSON looks like:

```json
{
  "format": "loomis-head",
  "version": 1,
  "model": "loomis",
  "name": "Loomis base",
  "author": "your-name",
  "license": "CC0-1.0",
  "tags": ["loomis", "base"],
  "head": { "scale": 0.42, "rotation": [1, 0, 0, 0] }
}
```

Put a JSON and a 400×400 preview PNG in `heads/<author>/` (see
[`heads/README.md`](heads/README.md)). `model` is reserved for future head engines; this
version only accepts `loomis`.

## Development

```bash
cd loomis_head
python3 -m unittest test_generator.py -v
```

The 40 generator tests do not need Krita, Qt or PyQt5. The UI/docker needs Krita; load it
with `Tools → Scripts → Import Python Plugins` or by copying the folder.

Repository layout:

```text
loomis_head/            plugin source (the ZIP root is this folder + .desktop)
loomis_head.desktop
heads/                  shareable head presets and format
docs/media/             GIF and screenshots
docs/ARCHITECTURE.md    code map and state files
release/                installable ZIP
```

## Contributing

Contributions are welcome: languages, hair patterns, head presets, features and fixes.
Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. The project is
GPL-3.0-only, so contributions are accepted under the same license.

## Credits and license

- Original **Loomis Head Generator**: lm0ss (2025), GPL-3.0.
- **Loomis Method Head Guide**: Nedeljko Umjetnik (2026).
- This fork and improvements: **imboolean** (2026).

See [CREDITS.md](CREDITS.md) for the full lineage. The project is licensed under
**GPL-3.0-only**; `euclid.py` is LGPL-2.1. The plugin works offline: no telemetry, no
network, no accounts.
