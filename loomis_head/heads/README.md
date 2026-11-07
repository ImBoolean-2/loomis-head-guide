# Cabezas para compartir

Cada archivo es una cabeza Loomis exportada desde el plugin (**Exportar cabeza…**). Se
puede cargar con **Cargar cabeza…** y también pegar su bloque `head` en la ficha de un OC
del Grimorio de Color.

## Formato

```json
{
  "format": "loomis-head",
  "version": 1,
  "model": "loomis",
  "name": "Loomis base",
  "author": "imboolean",
  "license": "CC0-1.0",
  "tags": ["loomis", "base"],
  "head": { "...": "parámetros completos del generador" }
}
```

- `model`: solo `loomis` en esta versión. Los modelos futuros (Reilly, Asaro, anime) usarán
  el mismo envoltorio y el cargador avisará si no los entiende.
- `head`: escala, posición normalizada, rotación (quaternion), cortes, rasgos, pelo,
  caricatura, colores y toggles. Es el mismo bloque que guarda el Grimorio.
- `author`, `license` y `tags` son libres; sirven para acreditar y filtrar.

## Convención sugerida

```text
heads/
├── README.md
├── example-head.json
├── example-head.png     (preview 400x400)
└── <autor>/<nombre>.json
```

- Un JSON por cabeza y un PNG de preview con el mismo nombre.
- No incluyas datos personales; usa un alias si quieres.
- Si la cabeza está pensada para un OC, ponlo en `tags` (`["oc", "aria"]`).

## Repo

Este plugin es un fork de **imboolean**; la carpeta `heads/` es la plantilla para
que la comunidad publique sus cabezas en su propio repositorio (GitHub, Codeberg, etc.).
La licencia del plugin es GPL-3.0-only; los datos de cada cabeza usan la licencia que
indique su autor en `license`.
