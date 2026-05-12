# Documento de Diseño: Script de Menú Interactivo para Color-by-Numbers

## Visión General

`run_interactive.py` es un script Python de menú interactivo en terminal que reemplaza los scripts bash `run.sh` y `run_gpu.sh`. Detecta automáticamente las imágenes disponibles en `in/`, presenta un menú numerado para seleccionar la imagen a procesar, permite configurar todos los parámetros clave de `app.py` de forma interactiva y ejecuta el proceso. Usa únicamente la biblioteca estándar de Python 3.8+ y `subprocess`, garantizando compatibilidad con Windows, macOS y Linux.

---

## Arquitectura

El script sigue una arquitectura de flujo lineal con tres fases bien diferenciadas:

```
Inicio
  │
  ▼
[1] Fase de Selección
    ├── Escanear in/ → lista de imágenes
    ├── Mostrar Menú Principal
    └── Leer selección del usuario
  │
  ▼
[2] Fase de Configuración
    ├── Inicializar Configuración con valores por defecto
    ├── Mostrar Menú de Configuración (agrupado por categoría)
    ├── Leer ediciones del usuario (bucle hasta confirmar)
    └── Validar Checkpoint SAM
  │
  ▼
[3] Fase de Ejecución
    ├── Construir lista de argumentos
    ├── Ejecutar app.py via subprocess (streaming de salida)
    └── Mostrar resultado (éxito / error)
```

No hay estado global mutable. Toda la información fluye a través de objetos de datos inmutables o diccionarios pasados explícitamente entre funciones.

---

## Componentes e Interfaces

### `scan_images(input_dir: Path) -> list[Path]`

Escanea `input_dir` en busca de archivos con extensiones soportadas (`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, insensible a mayúsculas). Devuelve la lista ordenada alfabéticamente por nombre de archivo. Lanza `SystemExit` con mensaje descriptivo si el directorio no existe o no contiene imágenes.

### `derive_output_dir(image_path: Path) -> str`

Devuelve el nombre base del archivo sin extensión. Ejemplo: `in/Frida 02.jpg` → `"Frida 02"`.

### `PARAM_SCHEMA: dict`

Diccionario que define todos los parámetros configurables. Cada entrada tiene:

```python
{
  "key": str,           # nombre del argumento CLI (sin --)
  "label": str,         # etiqueta legible para el menú
  "default": Any,       # valor por defecto
  "type": type,         # int | float | bool | str
  "choices": list|None, # opciones válidas para str con opciones fijas
  "min": num|None,      # valor mínimo para int/float
  "max": num|None,      # valor máximo para int/float
  "category": str,      # "Perfil/Salida" | "Paleta/Auto-K" | "SLIC/Bordes" | "SAM/Contornos/Numeración"
  "description": str,   # descripción breve para el menú
}
```

Los parámetros expuestos y sus valores por defecto (basados en `run.sh`):

| Categoría | Clave CLI | Tipo | Por defecto |
|---|---|---|---|
| Perfil/Salida | `profile` (interno) | str | `"a4"` (choices: `a4`, `a2`) |
| Perfil/Salida | `orientation` | str | `"landscape"` (choices: `portrait`, `landscape`) |
| Paleta/Auto-K | `auto_k` | bool | `True` |
| Paleta/Auto-K | `colors` | int | `12` |
| Paleta/Auto-K | `k_min` | int | `12` |
| Paleta/Auto-K | `k_max` | int | `24` |
| Paleta/Auto-K | `target_ssim` | float | `0.965` |
| SLIC/Bordes | `slic_n` | int | `4000` |
| SLIC/Bordes | `slic_compact` | float | `8.0` |
| SLIC/Bordes | `edge_deltaE` | float | `3.5` |
| SLIC/Bordes | `smooth_open` | int | `0` |
| SLIC/Bordes | `smooth_close` | int | `1` |
| SLIC/Bordes | `min_region_area` | int | `30` |
| SAM/Contornos/Numeración | `sam_device` | str | `"auto"` (choices: `auto`, `cpu`, `cuda`, `mps`) |
| SAM/Contornos/Numeración | `sam_pps` | int | `128` |
| SAM/Contornos/Numeración | `sam_min_area` | int | `400` |
| SAM/Contornos/Numeración | `sam_iou` | float | `0.90` |
| SAM/Contornos/Numeración | `sam_stability` | float | `0.93` |
| SAM/Contornos/Numeración | `line_thickness` | int | `1` |
| SAM/Contornos/Numeración | `force_closed` | bool | `True` |
| SAM/Contornos/Numeración | `close_gaps_radius` | int | `1` |
| SAM/Contornos/Numeración | `font_size` | int | `14` |
| SAM/Contornos/Numeración | `numbers_min_area` | int | `20` |

> **Nota sobre `profile`**: Es un parámetro interno del Script que no se pasa directamente a `app.py`. Cuando el usuario selecciona `a4`, se usa `--max-width 4961`; cuando selecciona `a2`, se usa `--max-width 7016`.

### `validate_param(value_str: str, schema_entry: dict) -> tuple[Any, str|None]`

Convierte y valida un valor de cadena según el esquema del parámetro. Devuelve `(valor_convertido, None)` si es válido, o `(None, mensaje_error)` si no lo es.

### `build_args(image_path: Path, output_dir: str, checkpoint: Path, config: dict) -> list[str]`

Construye la lista de argumentos para `subprocess`. El primer elemento es `sys.executable`, el segundo es `"app.py"`. Todos los parámetros se añaden como elementos individuales de la lista (nunca como cadena interpolada). Los parámetros booleanos `True` se añaden como flags sin valor; los `False` se omiten.

### `validate_checkpoint(project_root: Path) -> Path | None`

Busca archivos `.pth` en `project_root`. Si encuentra exactamente uno, lo devuelve. Si no encuentra ninguno, devuelve `None`. Si encuentra varios, devuelve el primero ordenado alfabéticamente y muestra una advertencia.

### `run_app(args: list[str]) -> int`

Ejecuta el proceso con `subprocess.Popen`, transmite `stdout` y `stderr` en tiempo real al terminal del usuario y devuelve el código de salida.

### `show_selection_menu(images: list[Path]) -> Path`

Muestra el Menú Principal y gestiona el bucle de entrada hasta obtener una selección válida.

### `show_config_menu(config: dict) -> dict`

Muestra el Menú de Configuración agrupado por categoría, gestiona el bucle de edición y devuelve la configuración final confirmada.

### `main()`

Función de entrada. Orquesta las tres fases: selección → configuración → ejecución.

---

## Modelos de Datos

### Objeto `Config`

Diccionario Python plano `{clave: valor}` donde las claves corresponden a los campos `key` del `PARAM_SCHEMA`. Se inicializa con los valores `default` del esquema y se actualiza con las ediciones del usuario.

```python
config = {
    "profile": "a4",
    "orientation": "landscape",
    "auto_k": True,
    "colors": 12,
    "k_min": 12,
    "k_max": 24,
    "target_ssim": 0.965,
    "slic_n": 4000,
    "slic_compact": 8.0,
    "edge_deltaE": 3.5,
    "smooth_open": 0,
    "smooth_close": 1,
    "min_region_area": 30,
    "sam_device": "auto",
    "sam_pps": 128,
    "sam_min_area": 400,
    "sam_iou": 0.90,
    "sam_stability": 0.93,
    "line_thickness": 1,
    "force_closed": True,
    "close_gaps_radius": 1,
    "font_size": 14,
    "numbers_min_area": 20,
}
```

### Construcción del comando

```python
# Ejemplo de lista de argumentos construida por build_args():
[
    sys.executable,          # "python" o ruta completa al intérprete
    "app.py",
    "--input", "in/Frida 02.jpg",
    "--out", "Frida 02",
    "--sam-checkpoint", "sam_vit_b_01ec64.pth",
    "--max-width", "4961",
    "--orientation", "landscape",
    "--auto-k",              # flag booleano True → sin valor
    "--k-min", "12",
    "--k-max", "24",
    "--target-ssim", "0.965",
    "--slic-n", "4000",
    # ... resto de parámetros
]
```

---

## Propiedades de Corrección

*Una propiedad es una característica o comportamiento que debe ser verdadero en todas las ejecuciones válidas de un sistema — esencialmente, una declaración formal sobre lo que el sistema debe hacer. Las propiedades sirven como puente entre las especificaciones legibles por humanos y las garantías de corrección verificables por máquinas.*

### Propiedad 1: Ordenación alfabética de imágenes

*Para cualquier* conjunto de nombres de archivo de imagen válidos en el Directorio_Entrada, la lista devuelta por `scan_images` debe estar ordenada alfabéticamente de forma ascendente por nombre de archivo.

**Valida: Requisito 1.2**

---

### Propiedad 2: Insensibilidad a mayúsculas en extensiones

*Para cualquier* nombre de archivo cuya extensión sea una variación de capitalización de las Extensiones_Soportadas (p. ej. `.JPG`, `.Png`, `.WEBP`), `scan_images` debe incluir ese archivo en el resultado.

**Valida: Requisito 1.4**

---

### Propiedad 3: Rechazo de entradas inválidas en selección de imagen

*Para cualquier* cadena de entrada que no sea un entero en el rango `[1, N]` donde N es el número de imágenes disponibles, la función de validación de selección debe rechazarla y devolver un indicador de error.

**Valida: Requisito 2.2**

---

### Propiedad 4: Derivación correcta del directorio de salida

*Para cualquier* ruta de imagen con cualquier extensión soportada y cualquier nombre de archivo (incluyendo nombres con espacios, caracteres especiales o múltiples puntos), `derive_output_dir` debe devolver exactamente el nombre base sin la extensión final.

**Valida: Requisito 2.3**

---

### Propiedad 5: Validación de tipos de parámetros

*Para cualquier* parámetro del esquema y cualquier valor de cadena de tipo incorrecto (p. ej. texto para un parámetro entero, número fuera de rango, cadena no incluida en `choices`), `validate_param` debe devolver un mensaje de error no nulo y no devolver un valor convertido válido.

**Valida: Requisitos 3.3, 3.4**

---

### Propiedad 6: Completitud del comando construido

*Para cualquier* objeto `Config` válido, `build_args` debe producir una lista de argumentos que contenga exactamente un argumento para cada parámetro activo de la configuración, con `sys.executable` como primer elemento y `"app.py"` como segundo.

**Valida: Requisitos 5.1, 5.2, 6.3**

---

### Propiedad 7: Seguridad de argumentos con valores especiales

*Para cualquier* valor de parámetro que contenga espacios, comillas o caracteres especiales de shell, `build_args` debe incluir ese valor como un elemento separado e independiente en la lista (no concatenado con la clave), de forma que `subprocess` lo trate como un único argumento sin interpretación de shell.

**Valida: Requisito 5.2**

> **Reflexión sobre redundancia**: Las Propiedades 6 y 7 son complementarias, no redundantes: la Propiedad 6 verifica completitud (todos los parámetros están presentes), mientras que la Propiedad 7 verifica seguridad (los valores con caracteres especiales no se corrompen). Ambas son necesarias.

---

## Manejo de Errores

| Situación | Comportamiento |
|---|---|
| `in/` no existe | Mensaje de error + `sys.exit(1)` |
| `in/` existe pero sin imágenes soportadas | Mensaje de error con instrucciones + `sys.exit(1)` |
| Entrada de selección inválida | Mensaje de error + re-solicitar (sin terminar) |
| Valor de parámetro inválido | Mensaje de error + re-solicitar (sin perder cambios) |
| Checkpoint SAM no encontrado | Mensaje de error con nombre esperado, ruta y URL de descarga + no ejecutar |
| `app.py` termina con error | Mensaje de error con código de salida + `sys.exit(código)` |
| `app.py` no encontrado | `FileNotFoundError` capturado + mensaje descriptivo + `sys.exit(1)` |

---

## Estrategia de Testing

### Enfoque dual

- **Tests unitarios**: verifican comportamientos específicos, casos límite y condiciones de error con ejemplos concretos.
- **Tests de propiedad**: verifican propiedades universales sobre rangos amplios de entradas generadas aleatoriamente.

### Librería de property-based testing

Se usará **Hypothesis** (ya disponible en el entorno del proyecto a través de las dependencias de testing estándar de Python). Cada test de propiedad se ejecutará con un mínimo de 100 iteraciones.

### Tests de propiedad (uno por propiedad del diseño)

Cada test de propiedad referencia su propiedad del diseño con el tag:
`# Feature: interactive-menu, Property N: <texto>`

- **Propiedad 1** — `test_scan_images_sorted`: genera listas aleatorias de nombres de archivo válidos, crea los archivos en un directorio temporal y verifica que `scan_images` devuelve la lista ordenada.
- **Propiedad 2** — `test_scan_images_case_insensitive`: genera variaciones aleatorias de capitalización de extensiones soportadas y verifica que todas son reconocidas.
- **Propiedad 3** — `test_invalid_selection_rejected`: genera entradas inválidas aleatorias (strings no numéricos, enteros fuera de rango) y verifica que la función de validación las rechaza.
- **Propiedad 4** — `test_derive_output_dir`: genera nombres de archivo aleatorios con extensiones soportadas y verifica que `derive_output_dir` devuelve el nombre base sin extensión.
- **Propiedad 5** — `test_validate_param_rejects_wrong_types`: genera valores de tipo incorrecto para cada parámetro del esquema y verifica que `validate_param` devuelve error.
- **Propiedad 6** — `test_build_args_completeness`: genera objetos `Config` aleatorios válidos y verifica que `build_args` contiene todos los argumentos esperados con `sys.executable` primero.
- **Propiedad 7** — `test_build_args_special_chars`: genera valores de parámetros con espacios y caracteres especiales y verifica que aparecen como elementos separados en la lista.

### Tests unitarios (ejemplos y casos límite)

- Directorio `in/` vacío → `SystemExit`
- Directorio `in/` inexistente → `SystemExit`
- Checkpoint SAM no encontrado → mensaje de error correcto, sin ejecución
- Checkpoint SAM encontrado → flujo continúa
- `app.py` termina con código 0 → mensaje de éxito
- `app.py` termina con código distinto de 0 → mensaje de error con código
- Perfil `a4` → `--max-width 4961` en el comando
- Perfil `a2` → `--max-width 7016` en el comando
- `auto_k=True` → flag `--auto-k` presente, `--colors` ausente
- `auto_k=False` → `--colors N` presente, `--auto-k` ausente
- `force_closed=True` → flag `--force-closed` presente
- `force_closed=False` → flag `--force-closed` ausente
