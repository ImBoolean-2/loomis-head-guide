# Créditos y linaje

## Autor original
- **lm0ss** — *Loomis Head Generator* (2025), GPL-3.0.
  - https://github.com/lm0ss/loomis-head-krita
  - https://krita-artists.org/t/loomis-head-generator-plugin/138278

## Fork del que parte este trabajo
- **Nedeljko Umjetnik** — *Loomis Method Head Guide* (2026), derivado del anterior.
  - https://nedeljko-umjetnik.itch.io/loomis-method-head-guide-plugin-for-krita
  - https://krita-artists.org/t/loomis-method-head-guide-plugin/192938

## Este fork
- **imboolean** (2026), fork. Mejoras implementadas:
  - Docker estable en `Settings → Dockers`, sin acción en Tools, y recreación de la capa
    guía si el usuario la borra.
  - Presets con nombre y por personaje del Grimorio de Color; carga/exportación de
    cabezas en JSON (`format`, `model`, `head`) para compartirlas.
  - Rasgos faciales paramétricos (líneas Loomis, cuencas, cejas, nariz, orejas, boca),
    caricatura (cráneo, mandíbula, pómulo, ancho, caída) y tipos de cabeza
    (realista, semi, anime, chibi, caricatura).
  - Vistas frontal, 3/4, perfil, trasera y superior; líneas de rasgos limitadas al
    hemisferio frontal para que la nuca no las muestre.
  - Previsualización 3D real con arcball (órbita libre, roll, zoom) en lugar del trackball
    de bola; sincronizada con el modelo y con las vistas.
  - Ejes X/Y/Z independientes y varias cabezas por documento: una capa `Loomis Head N`
    por guía, estado persistente en `guides.json` con el centro de la capa, selección
    automática de la capa activa, adopción al reiniciar y limpieza de duplicados.
  - Sliders de transformación (posición X/Y y rotación X/Y/Z) y panel de rasgos, pelo y
    caricatura integrado en el docker (sin ventana aparte). Pelo con arco, inclinación,
    posición de raya, patrón y textura.
  - Pelo paramétrico: línea del pelo y raya centro/lado/zigzag/puntas, con color propio.
  - Colores por zona (cráneo, mandíbula, pómulo, rasgos, pelo, guías), panel desplazable,
    i18n ES/EN/PT/FR y posición normalizada.
  - Carpeta `heads/` con plantilla, ejemplo y preview para compartir cabezas.
  - Bloque `head` en la ficha del Grimorio y escritura con backup.

## Licencia
GPL-3.0-only, la misma familia que el original (GPL-3.0). `euclid.py` es LGPL-2.1.
El texto completo está en `LICENSE`.
