# Loomis Head Guide — Handoff 2026-11-12

Este documento es para el siguiente chat/agente. Resume el estado real del proyecto
después de la migración al disco Share, lo que está cerrado, lo que falta validar y
dónde están las cosas. El detalle histórico está en `CHANGELOG.md` y
`docs/ARCHITECTURE.md`.

## Dónde está

- **Proyecto:** `/mnt/shared/krita-plugins/projects/loomis-head-guide`
  (antes `~/proyectos/loomis-head-guide`; el original se movió).
- **Plugin instalado en Krita:** `~/.var/app/org.kde.krita/data/krita/pykrita/loomis_head`
  → versión **0.7.12**, backups `.bak-0.7.12-<fecha>` (18 ficheros), `.bak-0.7.11-…` y anteriores.
- **Repo git:** mismo proyecto, HEAD `9fb4332` más los cambios 0.7.11 y 0.7.12 (sin commit ni push).
- **Release pública:** `release/` solo hasta **0.7.2** (`loomis-head-guide-0.7.2.zip`
  + `.patch` + `UPSTREAM-DIFF-0.7.2.md`). **No hay ZIP/patch 0.7.3–0.7.12**: son
  builds locales.

## Estado actual (0.7.12 local)

Plugin Krita 5.3.4 + PyQt5, con shim PyQt6. 5 pestañas: Ajustes, Mover, Guías,
Rasgos, Pelo.

Cerrado:

- **Asaro real:** malla decimada del OBJ `Asaro_high.obj` (`asaro_mesh.py`) y retopo
  limpio quad-dominante (`asaro_clean_mesh.py`, 122/242/272 caras). Boca, oreja con
  concha, cuello/base, `show_neck`, `show_planes`, `show_edges`, `shade_planes`,
  `detail` 0/1/2.
- **Licencia:** código GPL-3.0-only; mallas Asaro **CC BY 4.0** con atribución
  (`LICENSE-ASSETS.md`, `CREDITS.md`, README). Fuente: “Asaro-head” de **ivan4akir**
  (Sketchfab); “Simple Asaro Head” de **fabianoaraujo** se descartó; diseño original
  de **John Asaro**. La malla limpia es un derivado con modificaciones (decimación/
  retopo) y no se relicencia como GPL.
- **Pivote invisible:** centro del cráneo; `position_x/y` es el pivote. Marcador
  `loomis-pivot` en la capa.
- **Move/Transform manual:** 0.7.10 captura la **base** de los shapes
  (`Shape.transformation()`), guarda el **delta** del Move y lo reaplica una sola vez
  (`total = delta ∘ base`); un delta identidad **no toca** los shapes. El X/Y visible
  es la transformación total aplicada al pivote, convertida de unidades de capa (pt)
  a píxeles de documento (factor 0.24 en el caso del usuario).
- **Persistencia:** `guides.json → transform` y `head.layerTransform` guardan el delta
  con `transformIsDelta`; los absolutos de 0.7.8/0.7.9 se migran una vez. La última
  posición manual sobrevive a cerrar/reabrir.
- **Cabeza cortada al rotar/mover (0.7.11):** los shapes y `content.svg` eran correctos,
  pero Krita no reinvalidaba la caché/proyección de la capa vectorial al borrar y
  reimportar el SVG en la misma pasada: `mergedimage.png` del `.kra` salía cortado por una
  línea vertical (bbox x 1008..1178 en vez de 1008..1279) y el lienzo no se arreglaba hasta
  reabrir. `_force_layer_rerender()` limpia la caché con el toggle de
  `setAntialiased()` (se deja como estaba) y llama a `Document.refreshProjection()` tras el
  delta; la línea `draw` de `pivot.log` acaba en `rerender=aa=…,refresh=…`.
- **Delay:** input `Retardo` 50–5000 ms (default 500) bajo Vista; el canvas solo
  redibuja tras la inactividad; la preview del docker va en vivo. `redrawDelay` en
  `settings.json`.
- **Revisión de código (0.7.9):** corregidos los HIGH A (X/Y con matriz completa),
  B (JSON malformado no aborta Krita) y C (transform guardado con shapes a identidad);
  y los MEDIUM D–G/L8–L15 (delay mínimo, doble conexión X/Y, `positionUnit` píxeles,
  `OSError` en presets, logs con rotación, settings debounce, sliders negativos,
  renombrado de guías, color duplicado, shim `QPointF/QSpinBox/QTransform`, regex de
  color, backup Grimorio).
- **Tests:** `python3 -m unittest test_generator test_asaro` → **153 OK**
  (76 generador + 77 Asaro). `test_ui_offscreen.py` → **9 OK** en el flatpak
  (PyQt5; 5 previos + 2 de `_force_layer_rerender` + 2 de Grimorio 0.7.12); en host
  sin PyQt5 se salta. El UI test y `test_generator` en el **mismo proceso** con el stub
  de `krita` chocan (pre-existente): ejecutar el UI aparte.
- **Compatibilidad con Grimorio de Color 0.7.0 (0.7.12):** `_write_head_to_grimorio()`
  conserva el modo del fichero (0600 del `mkstemp` del Grimorio) en el JSON y en su
  `.loomis.bak`, y **fusiona** el `head` previo con el nuevo para no perder claves
  desconocidas (legacy de luz, claves futuras). QA: 110/110 PASS; E2E sobre copia del
  JSON real 10/10.
- **Logs:** `init.log`, `setup.log` y `pivot.log` en
  `~/.var/app/org.kde.krita/data/krita/loomis_head/`; rotan a `.1`.
  `pivot.log` registra `base=`, `delta=`, `total=`, `marker=`, `visible=` y, en las líneas
  `draw`, `rerender=aa=…,refresh=…`.

## Lo que falta (bloqueante antes de publicar 0.7.12)

**Validar en Krita real el 0.7.12.** El bug de base era la caché/proyección de la capa
vectorial: los shapes y `content.svg` estaban bien, pero `mergedimage.png` del `.kra` salía
cortado por una línea vertical y el lienzo no se arreglaba hasta reabrir el documento.
`_force_layer_rerender()` lo corrige (toggle de `setAntialiased()` + `refreshProjection()`
tras reaplicar el delta), pero no se ha podido probar con un `.kra` real desde este
entorno. Prueba, con Krita **reiniciado** para cargar 0.7.12:

1. Rotar (X/Y/Z) y mover con Move/Transform (A→B): la cabeza debe quedar **completa**, sin
   corte vertical, y el X/Y del docker debe coincidir con el “Position” de Krita.
2. Cambiar de modelo/sexo/tipo (B→C): no debe desaparecer ni quedar cortada.
3. Guardar, cerrar y reabrir el `.kra`: el Move debe conservarse y la cabeza seguir
   completa (mirar también `mergedimage.png` del `.kra`, que es lo que pinta Krita).
4. Si falla, adjunta `~/.var/app/org.kde.krita/data/krita/loomis_head/pivot.log` y los
   X/Y de A/B/C. Las líneas `draw` acaban en `rerender=aa=…,refresh=…`: si sale
   `refresh=0` la API no llegó a llamarse en esa build de Krita.

Con eso validado: generar ZIP/patch 0.7.12, actualizar `release/README`, `CHANGELOG`
global y `doc_change.sh`. **0.7.2 sigue siendo la última release pública.**

## Comandos útiles

```bash
cd /mnt/shared/krita-plugins/projects/loomis-head-guide/loomis_head
python3 -m unittest test_generator test_asaro          # 153
python3 -m py_compile *.py

# UI test fuera del proceso de test_generator (flatpak Krita; necesita /mnt/shared)
flatpak run --env=QT_QPA_PLATFORM=offscreen --env=QT_QPA_PLATFORMTHEME= \
  --command=python3 --filesystem=home --filesystem=/mnt/shared \
  org.kde.krita /mnt/shared/krita-plugins/projects/loomis-head-guide/loomis_head/test_ui_offscreen.py

# Instalación local (si hace falta)
cp -r loomis_head/* ~/.var/app/org.kde.krita/data/krita/pykrita/loomis_head/
```

## Qué NO tocar / qué no hacer

- No publiques 0.7.12 hasta validar rotar/mover/guardar/reabrir en Krita real; 0.7.2
  sigue siendo el último público.
- No escribas el head con `target["head"] = data` ni sin `chmod`: se pierden las claves
  que Loomis no conoce y el JSON baja a 0644 (lo cubren los tests de 0.7.12).
- No sustituyas `_force_layer_rerender()` por `refreshProjection()` sola: sin el toggle de
  `setAntialiased()` no se limpia la caché de la capa y el corte vertical del lienzo
  vuelve. Es la caché de la capa, no solo la proyección.
- No refactorices el `loomis_head_plugin.py` de ~100 KB en el mismo cambio que el bug;
  la revisión lo desaconseja.
- No cachees la preview ni toques `copy.deepcopy` sin medir: el coste es ~0.01 ms;
  el coste real es `build_svg`/`QSvgRenderer` (1–3 ms).
- No cambies `_capture_manual_transform` a “el shape más grande” sin test; el contrato
  es transformación más común, marcador excluido.
- No toques `asaro_mesh.py`/`asaro_clean_mesh.py` datos sin actualizar `CREDITS.md`/
  `LICENSE-ASSETS.md`; la malla es CC BY 4.0 y derivada.
- No metas luz/sombra direccional en Loomis; se retiró a propósito (0.6.1). El
  `shade_planes` de Asaro es relleno neutro por orientación, no una luz.
- No publiques `asaro_mesh.py`/`asaro_clean_mesh.py` sin la atribución CC BY.

## Siguientes pasos (después de validar)

1. ZIP/patch 0.7.12 y release pública; actualizar `release/README`.
2. Krita 6/PyQt6 smoke test (shim `qt_compat`; no hay Krita 6 instalado).
3. Asaro: perfil/cranium/oreja siguen siendo low-poly; el retopo limpio está en 242
   caras; un pulido fino es opcional.
4. Bridgman/elipsoide solo-cráneo: extras opcionales.
5. Asistentes de perspectiva nativos: bloqueados en Python (C++).
6. Grimorio de Color: el bloque `head` es opaco; `LOOMIS-0.6.1.md` en
   `~/proyectos/grimorio-color/docs/` sigue siendo el handoff de integración
   (Grimorio 0.7.0 verificado). El proyecto Loomis movido no cambia el JSON.

## Historial resumido

- 0.5.0 fork, 0.6.0 proporciones/guías/Reilly (sin luz), 0.6.1 sexo/cuenca/ceja,
  0.7.2 release pública con retopo exacto, 0.7.4 pivote, 0.7.5 delay, 0.7.6 layer/log,
  0.7.7 reset (regresión), 0.7.8 transform manual (regresión), 0.7.9 revisión,
  0.7.10 base+delta (fix de la regresión), 0.7.11 caché/proyección de la capa vectorial
  (cabeza cortada al rotar/mover), 0.7.12 compatibilidad con Grimorio 0.7.0 (modo 0600
  y head fusionado).
