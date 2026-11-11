# Licenses: code vs. Asaro mesh assets

This repository contains **two kinds of material under two different licenses**. They are
not interchangeable, and the mesh assets are **not** relicensed as GPL.

| Material | Files | License |
| --- | --- | --- |
| Plugin code | `loomis_head/*.py` (logic, generator, UI), `loomis_head.desktop`, tests, docs | **GPL-3.0-only** (see [LICENSE](LICENSE)) |
| Third-party library | `loomis_head/euclid.py` | **LGPL-2.1** (as shipped upstream) |
| Asaro mesh data | `loomis_head/asaro_mesh.py` (decimation), `loomis_head/asaro_clean_mesh.py` (hand retopo) | **CC BY 4.0** |
| Head JSON presets | `heads/*.json` | Each file's own `license` field; they contain **no mesh data** |

## Code — GPL-3.0-only

The plugin is free software under the GNU General Public License v3.0 only. The full text
is in [LICENSE](LICENSE). `euclid.py` keeps its upstream **LGPL-2.1** license.

## Asaro head mesh — CC BY 4.0

The planar head used by the **Asaro** model is derived from third-party Sketchfab models
published under **Creative Commons Attribution 4.0 International (CC BY 4.0)**:
<https://creativecommons.org/licenses/by/4.0/>.

### Source models

| Model | Author | License | Source |
| --- | --- | --- | --- |
| **Asaro-head** | **ivan4akir** | CC BY 4.0 | <https://sketchfab.com/3d-models/asaro-head-27a3328095ca412eaa5dde8a5da9ff3b> |
| **Simple Asaro Head** (reference only, not used) | **fabianoaraujo** | CC BY 4.0 | <https://sketchfab.com/3d-models/simple-asaro-head-fd74ad764a4e4619b72733316dc574b4> |

The design of the planar head itself is by **John Asaro** (Asaro head, the classic plane
study). Neither Sketchfab upload is the original author of the design; both are derivative
scans/models of it, and this project credits the designer separately from the uploaders.

The mesh actually used comes from **Asaro-head** (ivan4akir): the file `Asaro_high.obj`
(a bust with neck and base). **Simple Asaro Head** (fabianoaraujo) was evaluated as a
reference and **discarded**; no vertex or face of it is in this repository.

The original `.obj` files are **not redistributed**. What this repository ships is derived
data embedded in Python modules.

### Modifications (required notice under CC BY 4.0)

- `loomis_head/asaro_mesh.py` — **decimated** derivative of `Asaro_high.obj`: reoriented
  (+90° in Y, face towards +Z), box-centred, scaled to height 1.5, vertex-clustered on an
  axis grid that is denser at the features, degenerate/duplicate/sliver faces dropped, neck
  and base split by height, and the neck cut capped. Three detail levels
  (334 / 634 / 1195 faces).
- `loomis_head/asaro_clean_mesh.py` — **hand retopology** of the plane structure, measured
  on the same silhouette and in the same frame as the decimation above.
- No colour, texture or material from the source models is used; the plugin shades faces
  procedurally from their orientation.

### What you may and may not do with the mesh

- **You may** use, share and adapt the mesh, including commercially, **as long as you give
  the attribution below** and state any changes you make (CC BY 4.0).
- **You may not** present the mesh as GPL-3.0-only, or drop the attribution. The code
  around it is GPL; the mesh data itself stays under CC BY 4.0 with its own terms. If you
  redistribute the plugin, keep this file and [CREDITS.md](CREDITS.md) with it.
- Drawings you make with the plugin are yours; the licenses here cover the code and the
  mesh data, not your artwork.

### Attribution text (copy this)

> This work includes a decimated and retopologised derivative of the **Asaro head** plane
> model. Original design: **John Asaro**. Source model: "Asaro-head" by **ivan4akir**,
> licensed CC BY 4.0,
> <https://sketchfab.com/3d-models/asaro-head-27a3328095ca412eaa5dde8a5da9ff3b>.
> Reference model reviewed and not used: "Simple Asaro Head" by **fabianoaraujo**, CC BY 4.0,
> <https://sketchfab.com/3d-models/simple-asaro-head-fd74ad764a4e4619b72733316dc574b4>.
> Changes: decimation, reorientation and re-scaling of the source mesh; hand retopology of
> the plane structure; neck/base split and capping. License of the derivative mesh:
> CC BY 4.0, <https://creativecommons.org/licenses/by/4.0/>. Plugin code: GPL-3.0-only.

Short form, for one line in a README or an about box:

> Asaro mesh: derivative of "Asaro-head" by ivan4akir (CC BY 4.0), design by John Asaro;
> decimated/retopologised — see LICENSE-ASSETS.md.

## Reporting a problem

If you are a rights holder and believe an attribution or a permission is missing, open an
issue in this repository and the asset will be corrected or removed.
