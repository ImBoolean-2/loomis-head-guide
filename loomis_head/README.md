# Loomis Method Head Guide — presets y rasgos faciales

Fork de trabajo sobre el plugin de Nedeljko Umjetnik (a su vez basado en el Loomis Head
Generator de lm0ss). Licencia GPL-3.0, la misma del original; `euclid.py` es LGPL-2.1.
El texto completo está en `LICENSE`.

## Qué añade esta versión

- **Biblioteca de presets**: guarda y carga el estado completo de la cabeza (escala,
  posición normalizada, rotación, cortes, rasgos, grosores y color) con un nombre.
  Archivo: `QStandardPaths.AppDataLocation/loomis_head/presets.json`.
- **Escritura en la ficha**: al guardar en un OC, el bloque `head` se escribe también en
  `grimorio.json` (solo ese campo, con backup `grimorio.json.loomis.bak`). El Grimorio lo
  conserva como bloque opaco y viaja en Export/Import; el sidecar sigue siendo el respaldo.
- **Panel desplazable**: todo el contenido va en un `QScrollArea`, así los controles
  nuevos no se salen en pantallas bajas.
- **i18n**: español, inglés, portugués y francés por `QLocale` o `LOOMIS_LANG=es|en|pt|fr`
  (por defecto, el idioma del sistema). Las cadenas viven en `translations/*.json`.
- **Cabezas compartibles**: `Cargar cabeza…` / `Exportar cabeza…` leen y escriben un JSON
  con `format`, `model`, `name`, `author`, `license`, `tags` y `head`. La carpeta `heads/`
  trae plantilla, ejemplo y preview; los usuarios pueden subirlos a GitHub y cargarlos
  aquí. El cargador rechaza modelos distintos de `loomis`.
- **Colores por zona**: cráneo violeta, mandíbula naranja, pómulo cian, rasgos amarillo y
  guías laterales gris, para distinguir cada parte de un vistazo.
- **Previsualización 3D**: la bola del trackball se sustituyó por la cabeza renderizada.
  Arrastra para orbitar en cualquier dirección (arcball, sin ejes bloqueados), Shift o
  botón derecho para el roll, rueda para zoom y doble clic para volver al frente. La
  posición de la guía sigue en X/Y y en el Move tool.
- **Ejes X/Y/Z**: tres spinboxes a la izquierda del render para girar un eje sin tocar los
  otros; el arcball sigue libre.
- **Transformación**: sliders para posición X/Y y rotación X/Y/Z, sincronizados con los
  spinboxes y con la capa de Krita.
- **Vistas**: frontal, 3/4, perfil, trasera y superior desde un combo. Las líneas de
  rasgos solo se dibujan en el hemisferio frontal; desde atrás quedan punteadas.
- **Varias cabezas**: el combo «Cabeza» selecciona la guía activa y su capa en Krita; `+`
  crea otra capa independiente y `−` la elimina. Cada capa `Loomis Head N` es una cabeza
  con su modelo, posición, ángulo y parámetros. Al cambiar de cabeza se aplica el
  desplazamiento hecho en la capa inactiva; no vuelve a la posición original.
- **Estado por documento**: `guides.json` guarda el estado de cada cabeza y el centro de
  su capa por ruta del `.kra`. Al reiniciar se adoptan las capas existentes (no se crean
  duplicados) y se limpian una vez las capas viejas repetidas. Los documentos sin guardar
  no conservan el estado entre sesiones; guarda el `.kra` para que viaje.
- **UI por secciones**: rasgos, caricatura, pelo y transformación están dentro del panel
  con scroll; el botón que abría una ventana aparte ya no se usa. El pelo tiene arco,
  inclinación, posición de raya, patrón y textura (lisa, ondulada, puntas, rizada).
- **Pelo**: línea del pelo y raya al centro, lado, zigzag o puntas; se pinta con su propio
  color cuando están los colores por zona.
- **Tipos de cabeza**: realista, semi, anime, chibi y caricatura como presets de
  proporciones (cráneo, mandíbula, pómulo, ojos), ajustables después con los sliders.
- **Presets por personaje**: el mismo archivo tiene un mapa `characters` con clave = id
  del OC del Grimorio de Color. Al guardar en un OC se escribe además `head` en
  `grimorio.json` (solo ese campo, con backup), así que el bloque viaja en Export/Import;
  el sidecar queda como respaldo. Si el panel del Grimorio está abierto, recárgalo después.
- **Rasgos faciales**: líneas de ceja, ojos, nariz y boca; cuencas de los ojos, cejas,
  nariz, orejas y boca. Todo opcional y con sliders propios.
- **Caricatura**: cráneo, mandíbula, pómulo, ancho de cara y caída de mandíbula.
- **Docker**: el panel se registra en `setup()` y se abre solo desde
  `Settings → Configure Krita → Dockers`; no hay acción en Tools.
- **Correcciones**: el botón «Aplicar al lienzo» ya no destruye el modelo; los redibujados
  se agrupan cada 40 ms; el temporizador de posición se detiene con el panel oculto; los
  setters validan rangos y la posición se guarda normalizada (0–1) para sobrevivir a
  cambios de tamaño de lienzo. Si borras la capa guía, el panel la recrea en el siguiente
  cambio en vez de tocar el nodo muerto (causa del crash anterior).

## Formato del preset

```json
{
  "version": 1,
  "presets": {"Cabeza base": {"scale": 0.4, "positionX": 0.5, "positionUnit": "normalized"}},
  "characters": {"spinela-v1-human": {"scale": 0.42, "cranium": 1.1}}
}
```

`positionUnit: "normalized"` significa fracción del ancho/alto del documento. Los presets
antiguos en píxeles siguen cargando y se centran si no hay documento.

## Cabeza compartible

```json
{
  "format": "loomis-head",
  "version": 1,
  "model": "loomis",
  "name": "Cabeza de Aria",
  "author": "",
  "license": "",
  "tags": [],
  "head": {
    "version": 1,
    "generator": "loomis",
    "model": "loomis",
    "scale": 0.42,
    "positionUnit": "normalized",
    "cranium": 1.0,
    "useZoneColors": true
  }
}
```

El bloque `head` es el mismo que se guarda en la ficha del Grimorio. `model` permite
añadir otros métodos (Reilly, planos de Asaro, anime) sin romper los ficheros actuales:
el cargador de esta versión solo acepta `loomis`.

## Pruebas

```bash
cd ~/.var/app/org.kde.krita/data/krita/pykrita/loomis_head
python3 -m unittest test_generator.py -v
```

No necesitan Krita: el generador es Python puro. Cubren SVG en valores extremos,
roundtrip de serialización, tolerancia a JSON incompleto y clamps.

## Diagnóstico

Si el docker no aparece, el plugin escribe dos logs en
`QStandardPaths.AppDataLocation/loomis_head/`: `setup.log` (registro del docker) e
`init.log` (arranque del panel y traceback si falla). Son los primeros ficheros que hay
que mirar antes de tocar el código.

## Compatibilidad

Probado en Krita 5.3.4.1 (Flatpak, PyQt5). Krita 6 usa PyQt6 y aún no está soportado;
haría falta un shim `qt_compat` como el del Grimorio de Color.

## Créditos

- Loomis Head Generator: lm0ss (GPL-3.0).
- Versión base y mejoras de UI: Nedeljko Umjetnik.
- Presets, rasgos, caricatura, vistas, i18n e integración con el Grimorio: **imboolean**
  (fork privado, 2026). Linaje completo en `CREDITS.md`.
