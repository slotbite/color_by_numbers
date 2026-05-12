# Plan de Tareas — `web-ui`

## Fase 1: `config_schema.py` — Esquema de parámetros y validación

- [ ] 1.1 Crear `config_schema.py` copiando `PARAM_SCHEMA`, `COLOR_PROFILES` y `PROFILE_MAX_WIDTH` desde `run_interactive.py`
  - Exportar las tres constantes sin modificar sus valores
  - Añadir `SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}`
  - Añadir la clave `"color_profile"` al esquema de config (tipo `str`, default `"manual"`) para registrar qué perfil se usó

- [ ] 1.2 Implementar `default_config() -> dict` en `config_schema.py`
  - Devuelve `{s["key"]: s["default"] for s in PARAM_SCHEMA}`

- [ ] 1.3 Implementar `apply_color_profile(config: dict, profile_key: str) -> dict` en `config_schema.py`
  - Busca el perfil por `key` en `COLOR_PROFILES`
  - Si no es `"manual"`, actualiza `k_min`, `k_max`, `colors` y `auto_k`
  - Devuelve nueva config (no muta el original)

- [ ] 1.4 Implementar `validate_config(config: dict) -> list[str]` en `config_schema.py`
  - Itera sobre `PARAM_SCHEMA` y verifica tipo, rango `[min, max]` y `choices`
  - Cada error incluye el nombre del parámetro y el rango/opciones permitidas
  - Devuelve lista vacía si todo es válido

- [ ] 1.5 Implementar `build_args(image_path, output_dir, checkpoint, config) -> list[str]` en `config_schema.py`
  - Equivalente a `build_args` de `run_interactive.py`
  - Incluye todos los parámetros de `PARAM_SCHEMA` relevantes

- [ ] 1.6 Implementar `make_output_dir(output_base, image_stem, config, k_result, started_at) -> Path` en `config_schema.py`
  - Genera el nombre del directorio con parámetros clave en camelCase:
    `<imageStem>__k<K>_pps<PPS>_dE<DELTAE*10>_slic<SLICN>_<colorProfile>__<YYYYMMDD_HHMMSS>`
  - Ejemplo: `frida02__k14_pps32_dE35_slic4000_lapices24__20240115_143205`
  - Crea el directorio con `mkdir(parents=True, exist_ok=True)` antes de devolver el Path
  - `deltaE` se multiplica x10 y se redondea para evitar puntos en el nombre del directorio

- [ ] 1.7 Escribir tests de propiedad para `config_schema.py` en `tests/test_config_schema.py`
  - `test_scan_images_filters_extensions` — Propiedad 1
  - `test_scan_images_sorted` — Propiedad 2
  - `test_build_args_completeness` — Propiedad 3
  - `test_apply_color_profile` — Propiedad 4
  - `test_validate_config_rejects_invalid` — Propiedad 10
  - `test_validate_config_accepts_valid` — Propiedad 11
  - `test_default_config_has_all_keys` — test unitario
  - `test_make_output_dir_name_format` — verifica que el nombre del directorio contiene todos los segmentos esperados (imageStem, k, pps, dE, slic, profile, timestamp)
  - `test_make_output_dir_creates_directory` — verifica que el directorio se crea en disco

- [ ] 1.8 Verificar que todos los tests de la Fase 1 pasan (`pytest tests/test_config_schema.py -v`)

---

## Fase 2: `history.py` — Historial persistente JSON

- [ ] 2.1 Definir `ExecutionRecord` como dataclass en `history.py`
  - Campos: `job_id`, `image_name`, `config`, `k_result`, `status`, `started_at`, `duration_s`, `output_dir`, `error_msg`
  - `job_id` sigue el formato `<YYYYMMDD_HHMMSS>_<image_stem>` (legible y ordenable)
  - `output_dir` contiene el path con parámetros codificados generado por `make_output_dir`
  - Añadir métodos `to_dict()` y `from_dict(d: dict)` para serialización JSON

- [ ] 2.2 Implementar `load_history(history_path: Path) -> list[ExecutionRecord]` en `history.py`
  - Lee el archivo JSON; devuelve `[]` si no existe o está corrupto (loguea el error)
  - Ordena por `started_at` descendente antes de devolver

- [ ] 2.3 Implementar `save_entry(history_path: Path, record: ExecutionRecord) -> None` en `history.py`
  - Carga el historial existente, añade/actualiza el registro por `job_id`
  - Escribe en fichero temporal y renombra (escritura atómica)
  - Crea el directorio padre si no existe

- [ ] 2.4 Implementar `get_history(history_path: Path) -> list[ExecutionRecord]` como alias de `load_history`

- [ ] 2.5 Escribir tests de propiedad para `history.py` en `tests/test_history.py`
  - `test_history_round_trip` — Propiedad 7 (genera `ExecutionRecord` aleatorios con Hypothesis)
  - `test_history_sorted_desc` — Propiedad 8
  - `test_config_reuse_preserves_params` — Propiedad 9
  - `test_history_empty_on_missing_file` — test unitario de ejemplo
  - `test_history_atomic_write` — test unitario de ejemplo

- [ ] 2.6 Verificar que todos los tests de la Fase 2 pasan (`pytest tests/test_history.py -v`)

---

## Fase 3: `job_runner.py` — Cola de ejecuciones con ThreadPoolExecutor

- [ ] 3.1 Definir `Job` como dataclass en `job_runner.py`
  - Campos: `job_id`, `args`, `status`, `log`, `returncode`, `started_at`, `finished_at`
  - `status` inicializado a `"pending"`

- [ ] 3.2 Implementar `JobQueue.__init__` en `job_runner.py`
  - Crea `ThreadPoolExecutor(max_workers=3)`
  - Inicializa `_jobs: list[Job]` y `_lock: threading.Lock`
  - Recibe `on_complete: Callable[[Job], None]`

- [ ] 3.3 Implementar `JobQueue.enqueue(job: Job) -> str` en `job_runner.py`
  - Añade el job a `_jobs` bajo lock
  - Envía `_run_job(job)` al executor
  - Devuelve `job.job_id`

- [ ] 3.4 Implementar `_run_job(job: Job)` (método privado) en `job_runner.py`
  - Llama a `make_output_dir(output_base, image_stem, config, k_result, started_at)` para crear el work path
    - Usa `config["k_max"]` como `k_result` inicial si Auto-K está activo (se renombra al finalizar si difiere)
  - Actualiza `job.status = "running"`, `job.started_at` y `job.output_dir`
  - Ejecuta `subprocess.Popen(job.args, stdout=PIPE, stderr=STDOUT)`
  - Lee stdout línea a línea, acumula en `job.log` y extrae `k_result` del patrón `🎯 Auto-K → N`
  - Al terminar: si `k_result` real difiere del estimado, renombra el directorio y actualiza `job.output_dir`
  - Actualiza `job.status`, `job.returncode`, `job.finished_at`
  - Invoca `on_complete(job)` con el `k_result` real

- [ ] 3.5 Implementar `JobQueue.get_jobs()`, `JobQueue.active_count()` y `JobQueue.shutdown()`

- [ ] 3.6 Escribir tests para `job_runner.py` en `tests/test_job_runner.py`
  - `test_queue_max_workers` — Propiedad 5 (usa mocks de subprocess con `time.sleep`)
  - `test_job_id_uniqueness` — Propiedad 6
  - `test_job_status_transitions` — test unitario de ejemplo (mock subprocess returncode=0)
  - `test_job_status_error` — test unitario de ejemplo (mock subprocess returncode=1)

- [ ] 3.7 Verificar que todos los tests de la Fase 3 pasan (`pytest tests/test_job_runner.py -v`)

---

## Fase 4: `styles.css` y `web_app.py` — Interfaz Streamlit

- [ ] 4.1 Crear `styles.css` con estilos glassmorphism dark mode
  - Variables CSS: `--bg-dark`, `--glass-bg`, `--glass-border`, `--accent`
  - Clases: `.glass-card` (backdrop-filter + background semitransparente), `.status-badge`
  - Paleta oscura: fondo `#0d0d0d`, tarjetas `rgba(255,255,255,0.05)`

- [ ] 4.2 Implementar `load_env_config() -> dict` en `web_app.py`
  - Lee `SAM_CHECKPOINT_PATH` (default `/data/sam_vit_b_01ec64.pth`)
  - Lee `INPUT_DIR` (default `/data/in`)
  - Lee `OUTPUT_DIR` (default `/data/res`)
  - Lee `PORT` (default `8501`)

- [ ] 4.3 Implementar `scan_images(input_dir: Path) -> list[Path]` en `web_app.py`
  - Filtra por `SUPPORTED_EXTENSIONS` (case-insensitive)
  - Ordena alfabéticamente por nombre

- [ ] 4.4 Implementar `results_exist(output_dir: str) -> bool` en `web_app.py`
  - Verifica que los 3 archivos PNG existen en `output_dir`

- [ ] 4.5 Implementar `render_config_panel(config: dict) -> dict` en `web_app.py`
  - Selector de imagen con vista previa en miniatura
  - Selector de Perfil_Color (llama a `apply_color_profile` al cambiar)
  - Controles agrupados por categoría según `PARAM_SCHEMA`:
    - `int`/`float` con rango → `st.slider`
    - `bool` → `st.checkbox`
    - `choices` → `st.selectbox`
  - Descripción de cada parámetro con `st.caption`

- [ ] 4.6 Implementar `render_jobs_panel(job_queue: JobQueue)` en `web_app.py`
  - Lista de jobs con badge de estado (pendiente/en ejecución/completado/error)
  - Expander con log capturado para cada job
  - Para jobs completados: muestra las 3 imágenes si `results_exist()` es True
  - Botones de descarga para PDF y CSV

- [ ] 4.7 Implementar `render_history_panel(history_path: Path)` en `web_app.py`
  - Lista de ejecuciones pasadas ordenada por timestamp desc
  - Expander con configuración completa y resultados para cada entrada
  - Botón "Reutilizar configuración" que carga la config en `st.session_state`

- [ ] 4.8 Implementar `render_comparison_panel` en `web_app.py`
  - Selector de dos ejecuciones (de la lista activa o del historial)
  - Dos columnas con imágenes y metadatos de cada ejecución

- [ ] 4.9 Implementar el flujo principal de `web_app.py`
  - `st.set_page_config(layout="wide", page_title="Color by Numbers")`
  - Inyectar CSS con `st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)`
  - Inicializar `JobQueue` en `st.session_state` (singleton)
  - Botón "Lanzar": llama a `validate_config`, muestra errores o encola el job
  - Refresco automático con `st.rerun()` o `time.sleep` + refresco periódico ≤ 5s

- [ ] 4.10 Escribir tests para `web_app.py` en `tests/test_web_app.py`
  - `test_env_config_reads_vars` — Propiedad 12 (monkeypatching de `os.environ`)
  - `test_results_exist_false_when_missing` — test unitario de ejemplo
  - `test_results_exist_true_when_present` — test unitario de ejemplo
  - `test_validate_config_no_image` — test unitario de ejemplo

- [ ] 4.11 Verificar que todos los tests de la Fase 4 pasan (`pytest tests/test_web_app.py -v`)

---

## Fase 5: Docker — `Dockerfile` y `docker-compose.yml`

- [ ] 5.1 Crear `Dockerfile` basado en `python:3.12-slim`
  - Instalar dependencias del sistema: `libgl1`, `libglib2.0-0` (requeridas por OpenCV)
  - Copiar `requirements.txt` e instalar dependencias Python (incluyendo `streamlit`)
  - Copiar el código fuente (`app.py`, `web_app.py`, `job_runner.py`, `config_schema.py`, `history.py`, `styles.css`)
  - Variables de entorno por defecto: `SAM_CHECKPOINT_PATH`, `INPUT_DIR`, `OUTPUT_DIR`, `PORT`
  - `EXPOSE $PORT`
  - `CMD ["sh", "-c", "streamlit run web_app.py --server.port=$PORT --server.address=0.0.0.0"]`

- [ ] 5.2 Crear `docker-compose.yml` de referencia
  - Servicio `web-ui` con `build: .`
  - Volúmenes:
    - `./sam_vit_b_01ec64.pth:/data/sam_vit_b_01ec64.pth:ro`
    - `./in:/data/in:ro`
    - `./res:/data/res:rw`
  - Variables de entorno: `PORT=8501`
  - `ports: ["8501:8501"]`

- [ ] 5.3 Actualizar `requirements.txt` añadiendo `streamlit>=1.35`, `hypothesis>=6.100` (para tests)

- [ ] 5.4 Verificar que la imagen Docker construye sin errores (`docker build -t color-by-numbers-web .`)

- [ ] 5.5 Verificar smoke test: `docker-compose up` arranca la app y responde en `http://localhost:8501`

---

## Fase 6: Integración y verificación final

- [ ] 6.1 Ejecutar la suite completa de tests (`pytest tests/ -v --tb=short`)
  - Todos los tests de propiedades deben pasar con ≥ 100 ejemplos (perfil CI)
  - Cobertura mínima de las funciones puras: 80%

- [ ] 6.2 Verificar flujo end-to-end manual
  - Arrancar con `docker-compose up`
  - Seleccionar una imagen del volumen `in/`
  - Configurar un perfil de color y lanzar una ejecución
  - Verificar que el estado cambia de pendiente → en ejecución → completado
  - Verificar que las imágenes aparecen en la interfaz
  - Verificar que el historial persiste tras reiniciar el contenedor (`docker-compose restart`)

- [ ] 6.3 Verificar que lanzar 4 ejecuciones simultáneas mantiene máximo 3 workers activos

- [ ] 6.4 Verificar que la validación de parámetros muestra errores descriptivos antes de encolar

- [ ] 6.5 Verificar el Panel_Comparación con dos ejecuciones completadas

- [ ] 6.6 Verificar que "Reutilizar configuración" carga correctamente los parámetros en el Panel_Configuración
