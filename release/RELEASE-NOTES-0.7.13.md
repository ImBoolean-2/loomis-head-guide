# Loomis Head Guide 0.7.13 — notas de la versión

Primera build **pública** desde la 0.7.2. Agrupa once versiones de trabajo interno
(0.7.3 a 0.7.13) y cierra dos regresiones que hicieron inservible el plugin en Krita
durante un tiempo: la cabeza que se encogía al moverla y la cabeza que se dibujaba
cortada al rotarla; además recorta la pestaña Rasgos para que quepa en el docker.

- **Plugin:** `loomis_head/` + `loomis_head.desktop`
- **Instalación:** Krita → *Herramientas → Scripts → Importar plugin de Python* → elegir
  el ZIP → reiniciar Krita. El docker aparece en *Ajustes → Docker → Guía de cabezas Loomis*.
- **Requisitos:** Krita 5.3 o superior (probado en 5.3.4.1, flatpak). Krita 6 / PyQt6
  está soportado por el *shim* `qt_compat.py`, pero **no se ha probado**.
- **Licencia:** GPL-3.0-only. La malla Asaro es un derivado **CC BY 4.0**
  (ver *Créditos*).

---

## 1. Qué mejora, y por qué se hizo así

### 1.1 La malla Asaro pasa a ser la real (0.7.3 y 0.7.4)

Antes era una malla dibujada a mano con anillos apilados. Se sustituyó por una
**decimación del `Asaro_high.obj` real** y, en la versión siguiente, por un **retopo
manual quad-dominante** de 122 / 242 / 272 caras.

**Por qué:** el objetivo del modelo es estudiar los *planos* de la cabeza. Una malla
inventada enseña planos inventados; la decimación conserva la silueta real y el retopo
la ordena en líneas de flujo que siguen la anatomía. La decimación original se queda en
`asaro_mesh.py` como referencia para tests y comparaciones.

### 1.2 La posición de la cabeza sobrevive al Move/Transform (0.7.5 – 0.7.10)

El docker tiene un pivote lógico (centro del cráneo). Si movías la capa con la
herramienta *Move* de Krita, el siguiente redibujado devolvía la cabeza a su sitio.
Se arregló en varias iteraciones, y la solución final separa dos cosas:

- **base**: la escala que el importador SVG de Krita aplica a los shapes al crearlos
  (a 300 ppp es 72/300 = 0.24). No es un movimiento del usuario.
- **delta**: el desplazamiento real del *Move*, guardado aparte y reaplicado una sola vez
  como `delta ∘ base`.

**Por qué:** la versión intermedia trataba la escala del importador como si fuera el Move
y la reaplicaba; el resultado era `0.24² = 0.0576`, una cabeza invisible o incompleta.
Separar base y delta deja el Move intacto al rotar, cambiar de modelo o reabrir el `.kra`.

### 1.3 La cabeza ya no sale cortada al rotar (0.7.11)

Síntoma: al rotar o mover, el lienzo dibujaba la cabeza cortada por una línea vertical
recta, o directamente no la dibujaba, hasta cerrar y reabrir el `.kra`. El docker la
mostraba bien.

**Causa:** el SVG y los shapes eran correctos; lo que fallaba era el refresco de la capa
**vectorial** de Krita. Cada redibujado borra todos los shapes y reimporta el SVG en una
sola pasada, y Krita solo reinvalida el rectángulo que le avisa cada shape: la parte
nueva que caía fuera de ese rectángulo no llegaba ni al lienzo ni al guardado. Se
comprobó abriendo un `.kra` con el síntoma: su `content.svg` tenía la geometría completa
(x 1008–1279 px) mientras su `mergedimage.png` estaba cortado en x 1178.

**Arreglo:** tras reconstruir el SVG se limpia la caché entera de la capa (cambio y
restauración de `setAntialiased`, que es el recurso que usa la propia Krita para rehacer
una capa vectorial) y se refresca la proyección. Ya no hay que cerrar y reabrir el
documento.

### 1.4 Convivencia con Grimorio de Color (0.7.12)

El plugin comparte un único bloque con el Grimorio de Color: `characters[].head` dentro de
`grimorio.json`. Se corrigieron dos detalles que solo aparecen con datos reales:

- **Permisos:** al reescribir el JSON, Loomis creaba un temporal nuevo y el fichero
  acababa en `0644` aunque estuviera en `0600`. Ese JSON guarda `privateMode`, así que
  ahora se conserva el modo del original (fichero y backup).
- **Claves que Loomis no conoce:** antes se sustituía el bloque `head` entero y se perdían
  las claves antiguas (las cinco de luz de la 0.6.0) o de una versión futura. Ahora se
  **fusiona**: lo desconocido se conserva y los valores nuevos ganan.

**Por qué:** para el Grimorio el bloque `head` es opaco (lo copia sin interpretarlo). Si
Loomis lo recorta, el otro plugin pierde datos que sí estaba guardando bien.

**Independencia:** los dos plugins funcionan por separado. Sin `grimorio.json`, Loomis
entra en *modo independiente* (el selector de personaje se deshabilita y los presets se
guardan en su propio directorio). El Grimorio no importa ni necesita nada de Loomis.

### 1.5 La pestaña Rasgos cabe en el docker (0.7.13)

- La fila **Mostrar** pedía **~690 px** de ancho y el docker mide **~520**, así que los
  últimos checkboxes (Orejas, Curva de boca) quedaban fuera del marco y se recortaban en
  silencio. Ahora los flags van en un **grid de 2 columnas** (5 → 2+2+1) que baja el
  mínimo del panel de **678 a 458 px**, sin cambiar el orden ni el comportamiento.

---

## 2. Asaro sigue en proceso (importante)

**El modelo Asaro es un estudio de planos, no una referencia de proporciones.** Está
incluido para practicar el bloqueo de planos, y su diseño y su configuración todavía son
pobres:

- el **perfil**, la **bóveda del cráneo** y la **oreja** siguen siendo low-poly y no
  aguantan una vista de perfil exigente;
- la malla va por 122 / 242 / 272 caras y las transiciones entre planos son bastas en
  detalle 0;
- los controles del panel Asaro (detalle, aristas, planos, cuello) son mínimos: no hay
  ajuste fino de planos ni de proporciones como en Loomis;
- la malla es un derivado con modificaciones (decimación y retopo) del busto de
  **John Asaro** escaneado por **ivan4akir**, **CC BY 4.0**, y no se relicencia como GPL.

Trátalo como un **bloque de planos para calcar**, no como el modelo que usarás para
proporciones. Loomis es el motor principal y el que recibe los ajustes finos.

---

## 3. Compatibilidad

| Qué | Estado |
|---|---|
| Krita 5.3.4.1 (flatpak) | Probado |
| Krita 6 / PyQt6 | Soportado por el shim, **sin probar** |
| Cabezas JSON 0.5.1 / 0.6.0 / 0.6.1 | Cargan sin migración; las claves que faltan usan el valor por defecto |
| `heads/*.json` | `format: "loomis-head"`; `model` es `loomis` o `asaro` |
| Grimorio de Color **0.7.0 pública** | Verificado en los dos sentidos (bloque `head` intacto en 3 round-trips) |
| Grimorio de Color sin instalar | Modo independiente, sin errores |

---

## 4. Límites conocidos

- **Undo:** cada redibujado deja sus propias entradas en el historial (borrar + crear
  shapes). Agruparlas en un solo paso necesita C++; está documentado como deuda.
- **Retardo de dibujo:** el lienzo redibuja tras la inactividad (500 ms por defecto,
  ajustable de 50 a 5000 ms). Es deliberado: redibujar en cada tick del slider llenaba el
  historial y bloqueaba la UI. La previsualización del docker sí va en vivo.
- **Sin luz ni sombra direccional:** se retiró en la 0.6.1 a propósito. Esto es una guía
  de construcción, no un render; el sombreado confundía la lectura de los planos. El
  relleno de Asaro es orientación de planos, no una luz.
- **Asaro low-poly** (ver sección 2).

---

## 5. Verificación de esta build

- **153 tests** de generador y malla Asaro (`python3 -m unittest test_generator test_asaro`).
- **11 tests** de UI offscreen del docker en el flatpak de Krita (PyQt5 real).
- **QA de compatibilidad** con el ZIP público del Grimorio 0.7.0: 110 comprobaciones
  (escritura del `head`, preservación del resto del JSON, round-trips, permisos, backup,
  independencia), más la revalidación de los dos arreglos de la 0.7.12.
- El síntoma del corte se comprobó sobre un `.kra` guardado real (`content.svg` completo
  frente a `mergedimage.png` cortado) antes de aplicar el arreglo.

---

## 6. Créditos y licencia

- **Proyecto:** GPL-3.0-only (`LICENSE`).
- **Linaje:** Loomis Head Generator de **lm0ss** (2025) → Loomis Method Head Guide de
  **Nedeljko Umjetnik** (2026) → este fork de **imboolean** (2026).
- **Malla Asaro:** diseño de **John Asaro**; derivado de *Asaro-head* de **ivan4akir**
  (Sketchfab, **CC BY 4.0**), decimado y retopologizado. Se mantiene la atribución y el
  aviso de modificación (`LICENSE-ASSETS.md`, `CREDITS.md`).
- **`euclid.py`:** LGPL-2.1 (fichero original del upstream, sin cambios).
