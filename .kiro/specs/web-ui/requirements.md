# Documento de Requisitos

## Introducción

Este documento describe los requisitos para `web-ui`, una aplicación web construida con Streamlit que expone la funcionalidad de `app.py` (generador de kits "Pintar por Números" basado en SAM + SLIC + ΔE2000) a través de una interfaz gráfica. La aplicación permite al usuario subir imágenes, configurar todos los parámetros del generador mediante controles visuales, lanzar múltiples ejecuciones en paralelo (máximo 3 simultáneas), consultar el historial de ejecuciones pasadas y comparar resultados visualmente. La aplicación se distribuye como contenedor Docker y monta el checkpoint SAM y las imágenes de entrada como volúmenes externos.

---

## Glosario

- **Web_App**: La aplicación Streamlit descrita en este documento (`web_app.py` o equivalente).
- **App**: `app.py`, el script Python de generación de kits Color-by-Numbers.
- **Ejecución**: Una invocación de la App con una imagen y una configuración determinadas, gestionada por la Web_App.
- **Configuración**: Conjunto completo de parámetros que se pasan a la App en una Ejecución (equivalente al esquema de parámetros de `run_interactive.py`).
- **Perfil_Color**: Conjunto predefinido de valores para `k_min`, `k_max` y `colors` que corresponde a un caso de uso artístico (acuarelas, lápices, pixel art, óleo, etc.).
- **Cola**: Mecanismo interno de la Web_App que gestiona las Ejecuciones pendientes y en curso, garantizando que no más de 3 se ejecuten simultáneamente.
- **Historial**: Registro persistente de todas las Ejecuciones completadas, almacenado en formato JSON o Parquet.
- **Resultado**: Conjunto de archivos generados por una Ejecución exitosa: `01_outline_numbered.png`, `02_colored_reference.png`, `03_palette.png`, `color_by_numbers_kit.pdf` y `palette.csv`.
- **Checkpoint_SAM**: Archivo `.pth` del modelo SAM montado como volumen Docker en el directorio raíz del contenedor.
- **Volumen_Imágenes**: Directorio `in/` montado como volumen Docker que contiene las imágenes de entrada disponibles.
- **Volumen_Resultados**: Directorio `res/` montado como volumen Docker donde se escriben los Resultados de cada Ejecución.
- **Extensiones_Soportadas**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp` (insensible a mayúsculas).
- **Panel_Configuración**: Sección de la interfaz que muestra los controles de parámetros agrupados por categoría.
- **Panel_Historial**: Sección de la interfaz que muestra las Ejecuciones pasadas y permite consultarlas.
- **Panel_Comparación**: Sección de la interfaz que muestra dos Ejecuciones lado a lado para comparación visual.

---

## Requisitos

### Requisito 1: Interfaz visual con diseño minimalista

**User Story:** Como usuario, quiero una interfaz web con diseño dark mode y efecto glassmorphism, para tener una experiencia visual agradable y no sobrecargada al configurar y lanzar ejecuciones.

#### Criterios de Aceptación

1. THE Web_App SHALL aplicar un tema dark mode como estilo visual base en toda la interfaz.
2. THE Web_App SHALL aplicar estilos CSS de efecto glassmorphism (fondos semitransparentes con desenfoque) a los paneles y tarjetas de la interfaz.
3. THE Web_App SHALL organizar la interfaz en secciones claramente diferenciadas: Panel_Configuración, lista de Ejecuciones activas, Panel_Historial y Panel_Comparación.
4. THE Web_App SHALL mostrar únicamente los controles relevantes para la sección activa, evitando sobrecargar la pantalla con elementos innecesarios.

---

### Requisito 2: Selección de imagen de entrada

**User Story:** Como usuario, quiero seleccionar una imagen del directorio de entrada montado como volumen, para no tener que subir archivos manualmente cada vez.

#### Criterios de Aceptación

1. WHEN la Web_App se inicia, THE Web_App SHALL escanear el Volumen_Imágenes en busca de archivos con Extensiones_Soportadas y mostrar la lista resultante en el Panel_Configuración.
2. THE Web_App SHALL mostrar la lista de imágenes disponibles ordenada alfabéticamente por nombre de archivo.
3. IF el Volumen_Imágenes no contiene archivos con Extensiones_Soportadas, THEN THE Web_App SHALL mostrar un mensaje informativo indicando que no hay imágenes disponibles y la ruta del volumen esperada.
4. WHEN el usuario selecciona una imagen de la lista, THE Web_App SHALL mostrar una vista previa en miniatura de la imagen seleccionada en el Panel_Configuración.

---

### Requisito 3: Configuración de parámetros con controles visuales

**User Story:** Como usuario, quiero configurar todos los parámetros del generador mediante sliders y selectores visuales, para ajustar el resultado sin conocer los argumentos de línea de comandos.

#### Criterios de Aceptación

1. THE Web_App SHALL exponer todos los parámetros del esquema de `run_interactive.py` en el Panel_Configuración, agrupados en las mismas cuatro categorías: Perfil/Salida, Paleta/Auto-K, SLIC/Bordes y SAM/Contornos/Numeración.
2. THE Web_App SHALL representar los parámetros numéricos con rango definido (enteros y flotantes con `min` y `max`) mediante sliders con los valores mínimo, máximo y por defecto del esquema.
3. THE Web_App SHALL representar los parámetros de tipo booleano mediante toggles (checkbox o switch).
4. THE Web_App SHALL representar los parámetros con opciones fijas (`choices`) mediante selectores desplegables.
5. WHEN el usuario selecciona un Perfil_Color predefinido, THE Web_App SHALL actualizar automáticamente los controles de `k_min`, `k_max`, `colors` y `auto_k` con los valores del perfil seleccionado.
6. THE Web_App SHALL ofrecer los siguientes Perfiles_Color predefinidos: Acuarelas básicas, Lápices 24, Lápices 48/60, Mostacillas/Hama beads, Pixel art retro, Pixel art moderno, Óleo/Acrílico y Manual.
7. THE Web_App SHALL mostrar una descripción breve de cada parámetro junto a su control, equivalente a la descripción del esquema de `run_interactive.py`.
8. WHEN el usuario modifica cualquier control del Panel_Configuración, THE Web_App SHALL actualizar el valor del parámetro correspondiente en memoria de forma inmediata, sin requerir confirmación explícita.

---

### Requisito 4: Lanzamiento de ejecuciones en paralelo con cola

**User Story:** Como usuario, quiero lanzar múltiples ejecuciones con distintas configuraciones y verlas correr simultáneamente, para comparar resultados de forma eficiente.

#### Criterios de Aceptación

1. WHEN el usuario pulsa el botón de lanzar ejecución, THE Web_App SHALL encolar la Ejecución con la imagen y Configuración actuales del Panel_Configuración.
2. THE Web_App SHALL ejecutar como máximo 3 Ejecuciones de forma simultánea; las Ejecuciones adicionales permanecerán en estado pendiente en la Cola hasta que se libere un slot.
3. WHILE una Ejecución está en curso, THE Web_App SHALL mostrar su estado (pendiente, en ejecución, completada, error) en la lista de Ejecuciones activas.
4. WHILE una Ejecución está en curso, THE Web_App SHALL mostrar el progreso de la Ejecución mediante la salida estándar capturada de la App, actualizada en tiempo real o con refresco periódico no superior a 5 segundos.
5. WHEN una Ejecución finaliza con éxito, THE Web_App SHALL actualizar su estado a completada y mostrar los Resultados disponibles en la interfaz.
6. IF una Ejecución finaliza con error, THEN THE Web_App SHALL actualizar su estado a error y mostrar el mensaje de error capturado de la salida de error de la App.
7. THE Web_App SHALL asignar un identificador único a cada Ejecución en el momento de su encolado, compuesto por la marca de tiempo y el nombre de la imagen.

---

### Requisito 5: Visualización de resultados en la interfaz

**User Story:** Como usuario, quiero ver las imágenes generadas directamente en la interfaz web, para evaluar el resultado sin abrir el sistema de archivos.

#### Criterios de Aceptación

1. WHEN una Ejecución se completa con éxito, THE Web_App SHALL mostrar las tres imágenes del Resultado (`01_outline_numbered.png`, `02_colored_reference.png`, `03_palette.png`) en la interfaz, dentro de la tarjeta de la Ejecución correspondiente.
2. THE Web_App SHALL ofrecer un enlace o botón de descarga para el archivo PDF (`color_by_numbers_kit.pdf`) y el CSV de paleta (`palette.csv`) de cada Ejecución completada.
3. THE Web_App SHALL mostrar los metadatos de la Ejecución junto a los Resultados: nombre de la imagen, Perfil_Color utilizado, número de colores resultante, marca de tiempo de inicio y duración total.

---

### Requisito 6: Historial persistente de ejecuciones

**User Story:** Como usuario, quiero consultar las ejecuciones pasadas y sus configuraciones desde la interfaz, para reproducir o ajustar configuraciones que dieron buenos resultados.

#### Criterios de Aceptación

1. WHEN una Ejecución finaliza (con éxito o con error), THE Web_App SHALL guardar en el Historial un registro que incluya: identificador único, nombre de la imagen, Configuración completa, estado final, marca de tiempo de inicio, duración y ruta al directorio de Resultados.
2. THE Historial SHALL persistir en un archivo JSON o Parquet en el Volumen_Resultados, de forma que sobreviva a reinicios del contenedor.
3. THE Web_App SHALL mostrar el Panel_Historial con la lista de Ejecuciones pasadas ordenadas por marca de tiempo descendente.
4. WHEN el usuario selecciona una Ejecución del Panel_Historial, THE Web_App SHALL mostrar la Configuración completa utilizada y los Resultados disponibles de esa Ejecución.
5. WHEN el usuario selecciona una Ejecución del Panel_Historial y pulsa "Reutilizar configuración", THE Web_App SHALL cargar la Configuración de esa Ejecución en el Panel_Configuración, lista para ser lanzada de nuevo.

---

### Requisito 7: Comparación visual de dos ejecuciones

**User Story:** Como usuario, quiero comparar visualmente los resultados de dos ejecuciones lado a lado, para elegir la configuración que produce el mejor resultado artístico.

#### Criterios de Aceptación

1. THE Web_App SHALL permitir al usuario seleccionar dos Ejecuciones completadas (desde la lista activa o el Panel_Historial) para mostrarlas en el Panel_Comparación.
2. WHEN el usuario activa el Panel_Comparación con dos Ejecuciones seleccionadas, THE Web_App SHALL mostrar las imágenes `01_outline_numbered.png`, `02_colored_reference.png` y `03_palette.png` de ambas Ejecuciones en columnas paralelas.
3. THE Web_App SHALL mostrar junto a cada columna los metadatos de la Ejecución correspondiente: nombre de imagen, Perfil_Color, número de colores y duración.

---

### Requisito 8: Despliegue en Docker con volúmenes externos

**User Story:** Como operador, quiero desplegar la aplicación en Docker con el checkpoint SAM y las imágenes montados como volúmenes, para no incluir datos pesados dentro de la imagen y facilitar la actualización de imágenes de entrada.

#### Criterios de Aceptación

1. THE Web_App SHALL distribuirse como imagen Docker basada en Python 3.12 con todas las dependencias del proyecto (`torch`, `opencv`, `scikit-image`, `segment-anything`, `streamlit` y sus dependencias) instaladas en la imagen.
2. THE Web_App SHALL leer la ruta del Checkpoint_SAM desde una variable de entorno `SAM_CHECKPOINT_PATH`, con valor por defecto `/data/sam_vit_b_01ec64.pth`.
3. THE Web_App SHALL leer la ruta del Volumen_Imágenes desde una variable de entorno `INPUT_DIR`, con valor por defecto `/data/in`.
4. THE Web_App SHALL leer la ruta del Volumen_Resultados desde una variable de entorno `OUTPUT_DIR`, con valor por defecto `/data/res`.
5. THE Web_App SHALL exponer el puerto de Streamlit mediante una variable de entorno `PORT`, con valor por defecto `8501`.
6. IF el Checkpoint_SAM no existe en la ruta configurada al iniciar la Web_App, THEN THE Web_App SHALL mostrar un aviso visible en la interfaz indicando la ruta esperada y que las ejecuciones no podrán completarse hasta que el archivo esté disponible.
7. THE Web_App SHALL incluir un archivo `docker-compose.yml` de referencia que defina los tres montajes de volumen (Checkpoint_SAM, Volumen_Imágenes, Volumen_Resultados) y la variable de entorno `PORT`.

---

### Requisito 9: Validación de parámetros antes de lanzar

**User Story:** Como usuario, quiero recibir retroalimentación inmediata si algún parámetro está fuera de rango antes de lanzar una ejecución, para no desperdiciar tiempo en ejecuciones con configuraciones inválidas.

#### Criterios de Aceptación

1. WHEN el usuario pulsa el botón de lanzar ejecución, THE Web_App SHALL validar que todos los parámetros de la Configuración activa están dentro de los rangos definidos en el esquema antes de encolar la Ejecución.
2. IF algún parámetro está fuera de rango o tiene un valor inválido, THEN THE Web_App SHALL mostrar un mensaje de error descriptivo indicando el nombre del parámetro y el rango permitido, y no encolará la Ejecución.
3. WHEN el usuario pulsa el botón de lanzar ejecución sin haber seleccionado una imagen, THE Web_App SHALL mostrar un mensaje de error indicando que es necesario seleccionar una imagen, y no encolará la Ejecución.
