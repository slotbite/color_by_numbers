# Documento de Requisitos

## Introducción

Este documento describe los requisitos para `run_interactive.py`, un script Python de menú interactivo en terminal que reemplaza los scripts bash `run.sh` y `run_gpu.sh`. El script detecta automáticamente las imágenes disponibles en el directorio `in/`, permite al usuario elegir cuál procesar, configurar todos los parámetros clave de `app.py` de forma interactiva y ejecutar el proceso. Funciona en Windows, macOS y Linux usando únicamente Python estándar y `subprocess`.

## Glosario

- **Script**: `run_interactive.py`, el script Python de menú interactivo descrito en este documento.
- **App**: `app.py`, el script principal de generación de kits Color-by-Numbers.
- **Directorio_Entrada**: El directorio `in/` relativo al directorio de trabajo del Script.
- **Checkpoint_SAM**: Archivo `.pth` del modelo SAM ubicado en el directorio raíz del proyecto.
- **Perfil**: Conjunto predefinido de valores para `--max-width` y parámetros relacionados (A4 normal o A2 póster).
- **Configuración**: Conjunto completo de parámetros que se pasarán a la App al ejecutar.
- **Parámetro**: Argumento de línea de comandos aceptado por la App (p. ej. `--colors`, `--sam-device`).
- **Menú_Principal**: Pantalla inicial del Script que lista las imágenes disponibles.
- **Menú_Configuración**: Pantalla que muestra los parámetros agrupados por categoría y permite editarlos.
- **Extensiones_Soportadas**: Conjunto de extensiones de archivo reconocidas: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp` (insensible a mayúsculas).

---

## Requisitos

### Requisito 1: Detección de imágenes disponibles

**User Story:** Como usuario, quiero que el script detecte automáticamente todas las imágenes en `in/`, para no tener que escribir rutas manualmente.

#### Criterios de Aceptación

1. WHEN el Script se inicia, THE Script SHALL escanear el Directorio_Entrada en busca de archivos con Extensiones_Soportadas.
2. WHEN el escaneo del Directorio_Entrada se completa, THE Script SHALL mostrar el Menú_Principal con una lista numerada de las imágenes encontradas, ordenadas alfabéticamente por nombre de archivo.
3. IF el Directorio_Entrada no existe o no contiene archivos con Extensiones_Soportadas, THEN THE Script SHALL mostrar un mensaje de error descriptivo e indicar al usuario cómo añadir imágenes, y terminar con código de salida distinto de cero.
4. THE Script SHALL reconocer extensiones de archivo en Extensiones_Soportadas de forma insensible a mayúsculas y minúsculas.

---

### Requisito 2: Selección de imagen

**User Story:** Como usuario, quiero elegir qué imagen procesar desde un menú numerado, para no tener que editar ningún archivo de configuración.

#### Criterios de Aceptación

1. WHEN el Menú_Principal se muestra, THE Script SHALL solicitar al usuario que introduzca el número correspondiente a la imagen deseada.
2. IF el usuario introduce un número fuera del rango válido o un valor no numérico, THEN THE Script SHALL mostrar un mensaje de error y volver a solicitar la entrada sin terminar el proceso.
3. WHEN el usuario selecciona una imagen válida, THE Script SHALL almacenar la ruta completa de la imagen seleccionada y derivar el directorio de salida como el nombre base del archivo sin extensión.

---

### Requisito 3: Configuración avanzada interactiva

**User Story:** Como usuario, quiero ver y editar todos los parámetros clave antes de ejecutar, para ajustar el resultado sin conocer los argumentos de línea de comandos.

#### Criterios de Aceptación

1. WHEN el usuario ha seleccionado una imagen, THE Script SHALL mostrar el Menú_Configuración con todos los Parámetros agrupados en cuatro categorías: Perfil/Salida, Paleta/Auto-K, SLIC/Bordes y SAM/Contornos/Numeración.
2. THE Script SHALL mostrar el valor actual de cada Parámetro junto a su nombre y descripción breve en el Menú_Configuración.
3. WHEN el usuario elige editar un Parámetro, THE Script SHALL solicitar el nuevo valor, validarlo según el tipo esperado (entero, flotante, booleano, cadena de opciones fijas) y actualizar el valor en memoria.
4. IF el usuario introduce un valor de tipo incorrecto o fuera del rango permitido para un Parámetro, THEN THE Script SHALL mostrar un mensaje de error descriptivo y volver a solicitar el valor sin perder los cambios anteriores.
5. WHEN el usuario confirma la Configuración, THE Script SHALL proceder a la validación del Checkpoint_SAM antes de ejecutar la App.
6. THE Script SHALL exponer los siguientes Parámetros en el Menú_Configuración:
   - **Perfil/Salida**: perfil de salida (A4 normal `--max-width 4961` / A2 póster `--max-width 7016`), orientación (`portrait`/`landscape`).
   - **Paleta/Auto-K**: auto-k (sí/no), k-min, k-max, target-ssim, colors (k fijo cuando auto-k está desactivado).
   - **SLIC/Bordes**: slic-n, slic-compact, edge-deltaE, smooth-open, smooth-close, min-region-area.
   - **SAM/Contornos/Numeración**: sam-device, sam-pps, sam-min-area, sam-iou, sam-stability, line-thickness, force-closed, close-gaps-radius, font-size, numbers-min-area.

---

### Requisito 4: Validación del Checkpoint SAM

**User Story:** Como usuario, quiero recibir un mensaje de error claro si el checkpoint SAM no está presente, para saber exactamente qué archivo descargar y dónde colocarlo.

#### Criterios de Aceptación

1. WHEN el usuario confirma la Configuración, THE Script SHALL buscar el archivo Checkpoint_SAM en el directorio raíz del proyecto.
2. IF el Checkpoint_SAM no existe en el directorio raíz del proyecto, THEN THE Script SHALL mostrar un mensaje de error que indique el nombre exacto del archivo esperado, la ruta donde debe colocarse y un comando o URL de descarga de referencia, y no ejecutará la App.
3. WHEN el Checkpoint_SAM existe, THE Script SHALL continuar con la ejecución de la App.

---

### Requisito 5: Ejecución de la App

**User Story:** Como usuario, quiero que el script construya y ejecute el comando correcto para `app.py` con todos los parámetros configurados, para no tener que escribirlo manualmente.

#### Criterios de Aceptación

1. WHEN la validación del Checkpoint_SAM es exitosa, THE Script SHALL construir la lista de argumentos para la App incluyendo todos los Parámetros de la Configuración activa y ejecutarla mediante `subprocess`.
2. THE Script SHALL pasar `--input`, `--out`, `--sam-checkpoint` y todos los Parámetros configurados como argumentos individuales en la llamada a `subprocess`, sin usar interpolación de cadenas en shell.
3. WHILE la App se está ejecutando, THE Script SHALL transmitir la salida estándar y la salida de error de la App al terminal del usuario en tiempo real.
4. WHEN la App termina con código de salida cero, THE Script SHALL mostrar un mensaje de éxito indicando el directorio de salida generado.
5. IF la App termina con código de salida distinto de cero, THEN THE Script SHALL mostrar un mensaje de error indicando que el proceso falló y el código de salida recibido.

---

### Requisito 6: Compatibilidad con Windows

**User Story:** Como usuario de Windows, quiero ejecutar el script con `python run_interactive.py` sin instalar herramientas adicionales.

#### Criterios de Aceptación

1. THE Script SHALL usar únicamente módulos de la biblioteca estándar de Python 3.8 o superior y `subprocess` para invocar la App; no introducirá dependencias externas adicionales.
2. THE Script SHALL construir todas las rutas de archivo usando `pathlib.Path` para garantizar compatibilidad con los separadores de ruta de Windows (`\`).
3. THE Script SHALL invocar la App usando `sys.executable` como intérprete Python en la llamada a `subprocess`, para garantizar que se use el mismo entorno Python activo.
4. THE Script SHALL funcionar correctamente cuando el directorio de trabajo actual sea el directorio raíz del proyecto (`c:\GIT\color_by_numbers`).
