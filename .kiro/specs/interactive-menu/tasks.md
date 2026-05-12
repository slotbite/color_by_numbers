# Plan de Implementación: Script de Menú Interactivo

## Visión General

Implementar `run_interactive.py` en el directorio raíz del proyecto. El script se construye de forma incremental: primero el núcleo de datos y utilidades puras (fácilmente testables), luego la lógica de UI/interacción, y finalmente el ensamblado completo.

## Tareas

- [ ] 1. Crear estructura del módulo y esquema de parámetros
  - Crear `run_interactive.py` con la cabecera del módulo, imports estándar (`sys`, `os`, `pathlib`, `subprocess`) y la constante `PARAM_SCHEMA` con todos los parámetros definidos en el diseño (categoría, tipo, valor por defecto, choices, min/max, descripción).
  - Incluir los 22 parámetros configurables agrupados en las cuatro categorías: Perfil/Salida, Paleta/Auto-K, SLIC/Bordes, SAM/Contornos/Numeración.
  - _Requisitos: 3.6_

- [ ] 2. Implementar utilidades puras de datos
  - [ ] 2.1 Implementar `scan_images(input_dir: Path) -> list[Path]`
    - Escanear el directorio con `Path.iterdir()`, filtrar por Extensiones_Soportadas (insensible a mayúsculas), ordenar alfabéticamente.
    - Lanzar `SystemExit` con mensaje descriptivo si el directorio no existe o no hay imágenes.
    - _Requisitos: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 2.2 Escribir test de propiedad para `scan_images` — ordenación
    - **Propiedad 1: Ordenación alfabética de imágenes**
    - **Valida: Requisito 1.2**
    - Usar Hypothesis: generar listas aleatorias de nombres de archivo, crear archivos temporales, verificar orden.
    - `# Feature: interactive-menu, Property 1: scan_images devuelve lista ordenada alfabéticamente`

  - [ ]* 2.3 Escribir test de propiedad para `scan_images` — insensibilidad a mayúsculas
    - **Propiedad 2: Insensibilidad a mayúsculas en extensiones**
    - **Valida: Requisito 1.4**
    - Usar Hypothesis: generar variaciones aleatorias de capitalización de extensiones soportadas.
    - `# Feature: interactive-menu, Property 2: scan_images reconoce extensiones con cualquier capitalización`

  - [ ] 2.4 Implementar `derive_output_dir(image_path: Path) -> str`
    - Devolver `image_path.stem` (nombre base sin extensión final).
    - _Requisitos: 2.3_

  - [ ]* 2.5 Escribir test de propiedad para `derive_output_dir`
    - **Propiedad 4: Derivación correcta del directorio de salida**
    - **Valida: Requisito 2.3**
    - Usar Hypothesis: generar nombres de archivo aleatorios con extensiones soportadas, verificar que el resultado es el stem correcto.
    - `# Feature: interactive-menu, Property 4: derive_output_dir devuelve nombre base sin extensión`

  - [ ] 2.6 Implementar `validate_param(value_str: str, schema_entry: dict) -> tuple`
    - Convertir y validar según `schema_entry["type"]`, `choices`, `min`, `max`.
    - Devolver `(valor_convertido, None)` si válido, `(None, mensaje_error)` si no.
    - _Requisitos: 3.3, 3.4_

  - [ ]* 2.7 Escribir test de propiedad para `validate_param`
    - **Propiedad 5: Validación de tipos de parámetros**
    - **Valida: Requisitos 3.3, 3.4**
    - Usar Hypothesis: para cada parámetro del esquema, generar valores de tipo incorrecto y verificar rechazo.
    - `# Feature: interactive-menu, Property 5: validate_param rechaza valores de tipo incorrecto`

- [ ] 3. Checkpoint — Verificar tests de utilidades puras
  - Asegurarse de que todos los tests pasan. Consultar al usuario si surgen dudas.

- [ ] 4. Implementar construcción del comando y validación del checkpoint
  - [ ] 4.1 Implementar `validate_checkpoint(project_root: Path) -> Path | None`
    - Buscar archivos `.pth` en `project_root` con `Path.glob("*.pth")`.
    - Devolver el primero ordenado alfabéticamente, o `None` si no hay ninguno.
    - _Requisitos: 4.1, 4.2, 4.3_

  - [ ]* 4.2 Escribir tests unitarios para `validate_checkpoint`
    - Caso: checkpoint presente → devuelve Path correcto.
    - Caso: checkpoint ausente → devuelve None.
    - Caso: múltiples checkpoints → devuelve el primero alfabéticamente con advertencia.
    - _Requisitos: 4.1, 4.2, 4.3_

  - [ ] 4.3 Implementar `build_args(image_path, output_dir, checkpoint, config) -> list[str]`
    - Primer elemento: `sys.executable`. Segundo: `"app.py"`.
    - Traducir `profile` interno a `--max-width` (a4→4961, a2→7016).
    - Parámetros booleanos `True` → flag sin valor; `False` → omitir.
    - `auto_k=True` → añadir `--auto-k`; `auto_k=False` → añadir `--colors N`.
    - Todos los valores como elementos separados en la lista (nunca concatenados).
    - _Requisitos: 5.1, 5.2, 6.3_

  - [ ]* 4.4 Escribir test de propiedad para `build_args` — completitud
    - **Propiedad 6: Completitud del comando construido**
    - **Valida: Requisitos 5.1, 5.2, 6.3**
    - Usar Hypothesis: generar objetos Config aleatorios válidos, verificar que todos los argumentos esperados están presentes.
    - `# Feature: interactive-menu, Property 6: build_args contiene todos los argumentos de la configuración`

  - [ ]* 4.5 Escribir test de propiedad para `build_args` — valores con caracteres especiales
    - **Propiedad 7: Seguridad de argumentos con valores especiales**
    - **Valida: Requisito 5.2**
    - Usar Hypothesis: generar valores con espacios y caracteres especiales, verificar que aparecen como elementos separados.
    - `# Feature: interactive-menu, Property 7: build_args trata valores con caracteres especiales como elementos separados`

  - [ ]* 4.6 Escribir tests unitarios para `build_args`
    - Perfil `a4` → `--max-width 4961` presente.
    - Perfil `a2` → `--max-width 7016` presente.
    - `auto_k=True` → `--auto-k` presente, `--colors` ausente.
    - `auto_k=False` → `--colors N` presente, `--auto-k` ausente.
    - `force_closed=True` → `--force-closed` presente.
    - `force_closed=False` → `--force-closed` ausente.
    - _Requisitos: 5.1, 5.2_

- [ ] 5. Checkpoint — Verificar tests de construcción de comandos
  - Asegurarse de que todos los tests pasan. Consultar al usuario si surgen dudas.

- [ ] 6. Implementar lógica de UI e interacción
  - [ ] 6.1 Implementar `run_app(args: list[str]) -> int`
    - Usar `subprocess.Popen` con `stdout=None, stderr=None` para streaming en tiempo real.
    - Devolver `process.returncode`.
    - _Requisitos: 5.3, 5.4, 5.5_

  - [ ]* 6.2 Escribir tests unitarios para `run_app`
    - Mockear `subprocess.Popen`: código de salida 0 → devuelve 0.
    - Mockear `subprocess.Popen`: código de salida distinto de 0 → devuelve ese código.
    - _Requisitos: 5.4, 5.5_

  - [ ] 6.3 Implementar `show_selection_menu(images: list[Path]) -> Path`
    - Mostrar lista numerada de imágenes con nombre de archivo.
    - Bucle de entrada: validar que la entrada es un entero en `[1, len(images)]`.
    - Mostrar mensaje de error y re-solicitar si la entrada es inválida.
    - _Requisitos: 2.1, 2.2_

  - [ ]* 6.4 Escribir test de propiedad para validación de selección
    - **Propiedad 3: Rechazo de entradas inválidas en selección de imagen**
    - **Valida: Requisito 2.2**
    - Usar Hypothesis: generar entradas inválidas (strings no numéricos, enteros fuera de rango), verificar rechazo.
    - `# Feature: interactive-menu, Property 3: entradas inválidas de selección son rechazadas`

  - [ ] 6.5 Implementar `show_config_menu(config: dict) -> dict`
    - Mostrar parámetros agrupados por categoría con valor actual y descripción.
    - Opciones: número de parámetro para editar, `c` para confirmar, `r` para resetear a defaults.
    - Al editar: llamar a `validate_param`, mostrar error si inválido, actualizar si válido.
    - Devolver la configuración confirmada.
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 7. Implementar función `main()` y ensamblar el flujo completo
  - Orquestar las tres fases: selección → configuración → ejecución.
  - Llamar a `scan_images`, `show_selection_menu`, `derive_output_dir`.
  - Llamar a `show_config_menu`.
  - Llamar a `validate_checkpoint`; si devuelve `None`, mostrar mensaje de error con nombre esperado (`sam_vit_b_01ec64.pth`), ruta y URL de descarga, y terminar con `sys.exit(1)`.
  - Llamar a `build_args` y `run_app`.
  - Mostrar mensaje de éxito o error según el código de salida.
  - Añadir bloque `if __name__ == "__main__": main()`.
  - _Requisitos: 1.1, 2.3, 4.1, 4.2, 4.3, 5.1, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4_

- [ ] 8. Checkpoint final — Verificar todos los tests y flujo completo
  - Ejecutar la suite de tests completa. Asegurarse de que todos los tests pasan.
  - Verificar manualmente que el script arranca con `python run_interactive.py` en el directorio raíz del proyecto.
  - Consultar al usuario si surgen dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para una implementación MVP más rápida.
- Cada tarea referencia los requisitos específicos para trazabilidad.
- Los checkpoints garantizan validación incremental en cada fase.
- Los tests de propiedad usan Hypothesis con mínimo 100 iteraciones por propiedad.
- Los tests unitarios cubren casos límite y condiciones de error específicas.
- `build_args` nunca usa `shell=True` ni interpolación de cadenas para evitar inyección de comandos.
