# Credits and lineage

## Original author

- **lm0ss** — [Loomis Head Generator](https://github.com/lm0ss/loomis-head-krita) (2025),
  GPL-3.0. Also published on
  [Krita Artists](https://krita-artists.org/t/loomis-head-generator-plugin/138278).

## Fork this work starts from

- **Nedeljko Umjetnik** — [Loomis Method Head Guide](https://nedeljko-umjetnik.itch.io/loomis-method-head-guide-plugin-for-krita)
  (2026), a derivative of lm0ss's plugin. Also on
  [Krita Artists](https://krita-artists.org/t/loomis-method-head-guide-plugin/192938).

## This fork

- **imboolean** (2026). Improvements in this repository:
  - Stable docker registered from `Extension.setup()`, no Tools action, and guide-layer
    recovery if the user deletes it.
  - Real 3D preview with arcball rotation, roll, zoom, view shortcuts and independent
    X/Y/Z rotation/position sliders.
  - Guide manager: one `Loomis Head N` layer per head, several independent heads per
    document, automatic layer selection and per-document state in `guides.json`.
  - Migration of the old repeated layers and layer-centre persistence, so switching or
    restarting does not reset a head.
  - Feature panel embedded in the docker (no separate window): feature lines, eye sockets,
    brows, nose, ears, mouth, caricature and head-type presets.
  - Hair: line, arch, tilt, part position, straight/zigzag/spiky patterns and
    smooth/wavy/spiky/curly textures.
  - Named and per-character presets; load/export head JSON; `heads/` template; colours per
    zone; i18n EN/ES/PT/FR with a language selector; optional Grimoire of Color
    integration.
  - Tests, CI, SPDX headers and contribution templates.

## License

GPL-3.0-only, the same family as the original GPL-3.0. `euclid.py` is LGPL-2.1. See
[LICENSE](LICENSE).
