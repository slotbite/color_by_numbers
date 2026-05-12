# AGENT_CONTEXT.md — Color-by-Numbers Generator

Documento de contexto para que un agente retome el trabajo en este proyecto.
Última actualización: sesión de desarrollo web-ui.

---

## Descripción del proyecto

Generador de kits "Pintar por Números" de alta calidad usando:
- **SAM** (Segment Anything Model de Meta) — macro-bordes coherentes
- **K-Means** — paleta de colores reducida
- **SLIC + ΔE2000** — microdetalles y umbrales de borde

Produce: outline numerado (PNG), referencia coloreada (PNG), paleta (PNG + CSV) y kit completo (PDF).

---

## Entorno de desarrollo

- **OS**: Windows 11, CMD/PowerShell
- **Python**: 3.12.10 (instalado en `C:\Users\cvargas_xbrein\AppData\Local\Programs\Python\Python312\`)
- **Directorio del proyecto**: `c:\GIT\color_by_numbers`
- **GPU**: AMD Radeon 880M (iGPU integrada en Ryzen AI PRO 360) — **NO compatible con SAM** (DirectML falla con SAM). SAM corre en **CPU**.
- **No hay NVIDIA/CUDA** disponible.

---

## Instalación desde cero

### 1. Dependencias base

```cmd
pip install opencv-python pillow scikit-image numpy matplotlib reportlab scipy
```

### 2. PyTorch CPU (sin CUDA)

```cmd
pip install torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cpu
```

> **Nota**: `torch-directml` está instalado (`pip install torch-directml`) pero NO se usa para SAM porque causa `UnicodeDecodeError` en Windows. El parámetro `--sam-device` debe ser `cpu`.

### 3. Segment Anything Model

```cmd
pip install git+https://github.com/facebookresearch/segment-anything.git
```

### 4. Web UI y tests

```cmd
pip install streamlit>=1.35 hypothesis>=6.100
```

### 5. Checkpoint SAM (~375 MB)

Descargar y colocar en el directorio raíz del proyecto:

```python
# Ejecutar desde c:\GIT\color_by_numbers
python -c "import urllib.request; urllib.request.urlretrieve('https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth', 'sam_vit_b_01ec64.pth')"
```

O con PowerShell:
```powershell
Invoke-WebRequest -Uri "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth" -OutFile "sam_vit_b_01ec64.pth"
```

El archivo `sam_vit_b_01ec64.pth` (375 MB) está en `.gitignore` y **no se incluye en el repositorio**.

### 6. Verificar instalación

```cmd
python -m pytest tests/ -q
```

Resultado esperado: **38 passed**.

---

## Estructura del proyecto

```
c:\GIT\color_by_numbers\
│
├── app.py                  # Script CLI principal del generador
├── run_interactive.py      # Menú interactivo en terminal (Windows)
│
├── config_schema.py        # PARAM_SCHEMA, COLOR_PROFILES, validación, build_args, make_output_dir
├── history.py              # ExecutionRecord dataclass + historial JSON atómico
├── job_runner.py           # JobQueue con ThreadPoolExecutor(max_workers=3)
├── web_app.py              # Interfaz Streamlit completa
├── styles.css              # Glassmorphism dark mode CSS
│
├── Dockerfile              # Imagen Docker basada en python:3.12-slim
├── docker-compose.yml      # Volúmenes: SAM checkpoint, in/, res/
├── requirements.txt        # Dependencias Python
│
├── sam_vit_b_01ec64.pth    # Checkpoint SAM (NO en git, descargar manualmente)
│
├── in/                     # Imágenes de entrada (JPG, PNG, WEBP, BMP)
│   ├── 841746d49989fc4526f27062dc91af91.jpg
│   ├── Dibujos Acuarela Realistas.jpg
│   └── f96f009da309019d2ec844e291dfedbf.jpg
│
├── res/                    # Resultados generados
│   └── <imageStem>__k<K>_pps<PPS>_dE<DELTAE*10>_slic<SLICN>_<profile>__<YYYYMMDD_HHMMSS>/
│       ├── 01_outline_numbered.png
│       ├── 02_colored_reference.png
│       ├── 03_palette.png
│       ├── color_by_numbers_kit.pdf
│       └── palette.csv
│
├── tests/
│   ├── test_config_schema.py   # 12 tests (unitarios)
│   ├── test_history.py         # 9 tests (unitarios + Hypothesis PBT)
│   ├── test_job_runner.py      # 6 tests (unitarios con mocks)
│   └── test_web_app.py         # 11 tests (unitarios, funciones puras)
│
└── .kiro/specs/
    ├── interactive-menu/       # Spec del menú terminal (completado)
    └── web-ui/                 # Spec de la web UI (completado)
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

---

## Cómo ejecutar

### Web UI (recomendado)

```cmd
python -m streamlit run web_app.py
```

Abre `http://localhost:8501` en el browser.

### Menú interactivo en terminal

```cmd
python run_interactive.py
```

### CLI directo

```cmd
python app.py --input "in/imagen.jpg" --out "res/salida" --sam-checkpoint sam_vit_b_01ec64.pth --sam-device cpu --auto-k --k-min 12 --k-max 24 --force-closed
```

### Docker

```cmd
docker-compose up --build
```

La app queda disponible en `http://localhost:8501`.

---

## Convención de nombres de directorios de salida

Cada ejecución genera un directorio con nombre descriptivo en camelCase:

```
<imageStem>__k<K>_pps<PPS>_dE<DELTAE*10>_slic<SLICN>_<colorProfile>__<YYYYMMDD_HHMMSS>
```

Ejemplo:
```
frida02__k14_pps32_dE35_slic4000_lapices_24__20240115_143205
```

- `k14` → 14 colores (resultado real de Auto-K)
- `pps32` → SAM con 32 puntos por lado
- `dE35` → umbral ΔE 3.5 (×10 para evitar punto en el nombre)
- `slic4000` → 4000 segmentos SLIC
- `lapices_24` → perfil Lápices 24 Faber-Castell
- `20240115_143205` → timestamp de inicio

---

## Perfiles de color disponibles

| Clave | Label | K-min | K-max |
|---|---|---|---|
| `acuarela_basica` | Acuarelas básicas (caja escolar) | 10 | 16 |
| `lapices_24` | Lápices de colores 24 (Faber-Castell) | 16 | 24 |
| `lapices_48` | Lápices de colores 48/60 | 24 | 36 |
| `mostacillas` | Mostacillas / Hama beads | 16 | 32 |
| `pixel_art_retro` | Pixel art retro (Game Boy / NES) | 4 | 16 |
| `pixel_art_moderno` | Pixel art moderno | 16 | 32 |
| `oleo_acrilico` | Óleo / Acrílico (mezcla manual) | 6 | 14 |
| `manual` | Manual (definir manualmente) | — | — |

---

## Variables de entorno (web UI / Docker)

| Variable | Default local | Default Docker | Descripción |
|---|---|---|---|
| `SAM_CHECKPOINT_PATH` | `./sam_vit_b_01ec64.pth` | `/data/sam_vit_b_01ec64.pth` | Ruta al checkpoint SAM |
| `INPUT_DIR` | `./in` | `/data/in` | Carpeta de imágenes de entrada |
| `OUTPUT_DIR` | `./res` | `/data/res` | Carpeta de resultados |
| `PORT` | `8501` | `8501` | Puerto de Streamlit |

---

## Estado actual y trabajo pendiente

### Completado ✅

- `app.py` — generador CLI completo con SAM + SLIC + ΔE2000
- `run_interactive.py` — menú terminal con perfiles de color
- `config_schema.py` — esquema de parámetros, validación, `make_output_dir`
- `history.py` — historial JSON persistente y atómico
- `job_runner.py` — cola con máx. 3 workers paralelos
- `web_app.py` — interfaz Streamlit con:
  - Dark mode + glassmorphism CSS
  - Selector de carpeta libre + file_uploader
  - Perfiles de color predefinidos
  - Sliders/toggles/selectores para todos los parámetros
  - Cola de ejecuciones con estado en tiempo real
  - Historial con botón "▶️ Ejecutar esta config" (lanza directo sin tocar sidebar)
  - Comparación visual lado a lado
- `Dockerfile` + `docker-compose.yml`
- 38 tests pasando

### Bugs conocidos / trabajo pendiente 🔧

- El error de browser `"A listener indicated an asynchronous response..."` es una extensión de Chrome interfiriendo, no es de la app. Se puede ignorar.
- El botón "↩️ Reutilizar config" carga la config en el sidebar pero requiere un `st.rerun()` adicional para que los sliders reflejen los valores. Funciona correctamente pero puede sentirse lento.
- La web UI no tiene autenticación — no exponer a internet sin añadir `streamlit-authenticator` u otro mecanismo.
- El historial (`res/history.json`) crece indefinidamente. Considerar paginación o límite de entradas.
- Los tiempos de procesamiento con CPU son largos (5–20 min por imagen). Para acelerar: bajar `sam_pps` a 32 en pruebas.

### Ideas para continuar

- Añadir barra de progreso real (parsear el stdout de `app.py` para extraer etapas)
- Exportar comparación como imagen side-by-side descargable
- Añadir campo de notas por ejecución en el historial
- Soporte para procesar múltiples imágenes en batch desde la UI
- Añadir métricas de calidad (SSIM) visibles en el historial

---

## Notas técnicas importantes

### Windows + emojis en subprocess
`app.py` usa emojis en sus prints (🧠, 🎯, ✅). En Windows con CP1252, esto causa `UnicodeEncodeError`.
**Fix aplicado**: `job_runner.py` lanza el subprocess con `PYTHONIOENCODING=utf-8` y `PYTHONUTF8=1` en el entorno.

### Streamlit session_state y widgets
No se puede escribir en `st.session_state["param_<key>"]` después de que el widget con esa key fue instanciado en el mismo ciclo de render. 
**Fix aplicado**: se usa `pending_config` como estado intermedio + `st.rerun()` + borrado de keys antes de instanciar widgets.

### DirectML y SAM
`torch-directml` está instalado pero SAM falla con él en Windows (`UnicodeDecodeError` interno en `F.pad`). Siempre usar `--sam-device cpu`.

### Sliders float y step
Streamlit lanza un warning si el valor inicial de un slider float no es alcanzable con el `step` dado.
**Fix aplicado**: función `_snap_to_step()` en `web_app.py` redondea los valores al múltiplo de step más cercano.
