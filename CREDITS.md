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

## Asaro head mesh

The **Asaro** model is not written from scratch: it is a derivative of a Sketchfab model
of the classic plane head. Two licenses apply to this repository, so read
[LICENSE-ASSETS.md](LICENSE-ASSETS.md) before redistributing the mesh.

- **John Asaro** — designer of the original Asaro head, the planar bust this model studies.
  The mesh is an interpretation of his design; he is credited as the author of it.
- **ivan4akir** — [Asaro-head](https://sketchfab.com/3d-models/asaro-head-27a3328095ca412eaa5dde8a5da9ff3b)
  (Sketchfab), **CC BY 4.0**. Source of the mesh used here (`Asaro_high.obj`, the bust with
  neck and base).
- **fabianoaraujo** — [Simple Asaro Head](https://sketchfab.com/3d-models/simple-asaro-head-fd74ad764a4e4619b72733316dc574b4)
  (Sketchfab), **CC BY 4.0**. Reviewed as a reference and **discarded**: no geometry from it
  is used. Credited because it was part of the comparison and its license is acknowledged.

Changes made in this repository (the notice CC BY 4.0 requires):

- `loomis_head/asaro_mesh.py`: decimated from `Asaro_high.obj` — reoriented (+90° in Y,
  face towards +Z), box-centred, scaled to height 1.5, vertex clustering denser at the
  features, degenerate/duplicate/sliver faces removed, neck and base split by height and the
  neck cut capped. Three detail levels (334 / 634 / 1195 faces).
- `loomis_head/asaro_clean_mesh.py`: hand retopology of the plane structure, measured on the
  same silhouette and frame.

The original `.obj` files are not in this repository, and the mesh data stays under
**CC BY 4.0** with the attribution above; it is not relicensed as GPL. The code around it
is GPL-3.0-only.

## License

- Code: **GPL-3.0-only**, the same family as the original GPL-3.0. `euclid.py` is
  **LGPL-2.1**. See [LICENSE](LICENSE).
- Asaro mesh assets: **CC BY 4.0**, © their respective authors, with the attribution and
  modification notice above. See [LICENSE-ASSETS.md](LICENSE-ASSETS.md).
