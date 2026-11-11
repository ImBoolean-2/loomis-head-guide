# Cabezas para compartir

Cada archivo es una cabeza exportada desde el plugin (**Exportar cabeza…**). Se puede
cargar con **Cargar cabeza…** y también pegar su bloque `head` en la ficha de un OC del
Grimorio de Color.

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

- `model`: `loomis` o `asaro`. El cargador resuelve el modelo con el registro de
  `loomis_head/models.py` (`create_model`); si no lo entiende, avisa y no carga la cabeza.
- `head`: el bloque completo del generador que corresponda al `model`.
  - `loomis`: escala, posición normalizada, rotación (quaternion), cortes, rasgos, pelo,
    caricatura, colores y toggles. Es el mismo bloque que guarda el Grimorio.
  - `asaro`: escala, posición, rotación, trazos y color, más `showPlanes` (contornos de
    planos), `showEdges` (aristas de pliegue y silueta) y `detail` (0 grueso, 1 estándar,
    2 fino). Los campos de Loomis viajan igual para no romper la interfaz, pero en Asaro
    no cambian la malla.
- `author`, `license` y `tags` son libres; sirven para acreditar y filtrar.

### Posición (`positionUnit`)

`positionX`/`positionY` se interpretan según `positionUnit`:

| `positionUnit` | Rango | Significado |
|---|---|---|
| `"normalized"` | `0`..`1` | Fracción del lienzo. `0.5 / 0.5` es el **centro**, sea cual sea el tamaño del documento. Es lo que guarda el plugin cuando hay documento y lo que llevan los ejemplos. |
| `"pixels"` | `-100000`..`100000` | Píxeles absolutos del lienzo, origen en la esquina superior izquierda. Es lo que emite un preset guardado sin documento. |

- Si falta `positionUnit`, la posición se trata como **píxeles**. Si tampoco hay
  `positionX`/`positionY`, se conserva la posición actual del modelo (no se centra).
- Los dos ejemplos de esta carpeta (`example-head.json`, `example-asaro.json`) usan
  `"positionUnit": "normalized"` con `positionX: 0.5` y `positionY: 0.5`: la cabeza se
  coloca en el centro del lienzo, no en la esquina.
- Para compartir cabezas, usa `normalized`: el mismo JSON sirve para un lienzo de 1000 px
  y para uno de 4000 px sin retocar números.

## Convención sugerida

```text
heads/
├── README.md
├── example-head.json
├── example-head.png     (preview 400x400)
├── example-asaro.json
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
