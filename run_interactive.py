#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_interactive.py — Menú interactivo para Color-by-Numbers Generator
Detecta imágenes en in/, permite configurar parámetros y ejecuta app.py.
Requiere Python 3.8+ y solo usa la biblioteca estándar.
"""

import sys
import subprocess
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
SAM_CHECKPOINT_NAME = "sam_vit_b_01ec64.pth"
SAM_DOWNLOAD_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"

# ──────────────────────────────────────────────────────────────────────────────
# Perfiles de caso de uso
# ──────────────────────────────────────────────────────────────────────────────
COLOR_PROFILES = [
    {
        "key": "acuarela_basica",
        "label": "Acuarelas básicas (caja escolar)",
        "description": "12–16 colores. Ideal para cajas de 12 o 16 acuarelas.",
        "k_min": 10, "k_max": 16, "colors": 12,
    },
    {
        "key": "lapices_24",
        "label": "Lápices de colores 24 (Faber-Castell)",
        "description": "18–24 colores. Para cajas de 24 lápices.",
        "k_min": 16, "k_max": 24, "colors": 20,
    },
    {
        "key": "lapices_48",
        "label": "Lápices de colores 48/60",
        "description": "24–36 colores. Para cajas grandes de 48 o 60 lápices.",
        "k_min": 24, "k_max": 36, "colors": 30,
    },
    {
        "key": "mostacillas",
        "label": "Mostacillas / Hama beads",
        "description": "16–32 colores. Paleta discreta típica de kits de mostacillas.",
        "k_min": 16, "k_max": 32, "colors": 24,
    },
    {
        "key": "pixel_art_retro",
        "label": "Pixel art retro (Game Boy / NES)",
        "description": "4–16 colores. Paletas muy limitadas estilo consola clásica.",
        "k_min": 4, "k_max": 16, "colors": 8,
    },
    {
        "key": "pixel_art_moderno",
        "label": "Pixel art moderno",
        "description": "16–32 colores. Más detalle que el retro, estilo indie.",
        "k_min": 16, "k_max": 32, "colors": 24,
    },
    {
        "key": "oleo_acrilico",
        "label": "Óleo / Acrílico (mezcla manual)",
        "description": "8–14 colores. Pocos colores base que se mezclan en el lienzo.",
        "k_min": 6, "k_max": 14, "colors": 10,
    },
    {
        "key": "manual",
        "label": "Manual (definir manualmente)",
        "description": "Tú controlas k-min, k-max y colores directamente.",
        "k_min": None, "k_max": None, "colors": None,
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Esquema de parámetros
# Cada entrada: key, label, default, type, choices, min, max, category, description
# ──────────────────────────────────────────────────────────────────────────────
PARAM_SCHEMA = [
    # ── Perfil / Salida ──────────────────────────────────────────────────────
    {
        "key": "profile", "label": "Perfil de salida",
        "default": "a4", "type": str,
        "choices": ["a4", "a2"], "min": None, "max": None,
        "category": "Perfil/Salida",
        "description": "a4 = max-width 4961px  |  a2 = max-width 7016px (poster)",
    },
    {
        "key": "orientation", "label": "Orientación",
        "default": "landscape", "type": str,
        "choices": ["portrait", "landscape"], "min": None, "max": None,
        "category": "Perfil/Salida",
        "description": "Orientación de la página en el PDF final",
    },
    # ── Paleta / Auto-K ──────────────────────────────────────────────────────
    {
        "key": "auto_k", "label": "Auto-K",
        "default": True, "type": bool,
        "choices": None, "min": None, "max": None,
        "category": "Paleta/Auto-K",
        "description": "Buscar automáticamente el número óptimo de colores",
    },
    {
        "key": "colors", "label": "Colores fijos (si Auto-K=False)",
        "default": 12, "type": int,
        "choices": None, "min": 2, "max": 64,
        "category": "Paleta/Auto-K",
        "description": "Número de colores cuando Auto-K está desactivado",
    },
    {
        "key": "k_min", "label": "K mínimo",
        "default": 12, "type": int,
        "choices": None, "min": 2, "max": 64,
        "category": "Paleta/Auto-K",
        "description": "Número mínimo de colores en la búsqueda Auto-K",
    },
    {
        "key": "k_max", "label": "K máximo",
        "default": 24, "type": int,
        "choices": None, "min": 2, "max": 64,
        "category": "Paleta/Auto-K",
        "description": "Número máximo de colores en la búsqueda Auto-K",
    },
    {
        "key": "target_ssim", "label": "Target SSIM",
        "default": 0.965, "type": float,
        "choices": None, "min": 0.5, "max": 1.0,
        "category": "Paleta/Auto-K",
        "description": "Fidelidad mínima requerida (0.5–1.0). Más alto = más colores",
    },
    # ── SLIC / Bordes ────────────────────────────────────────────────────────
    {
        "key": "slic_n", "label": "SLIC segmentos",
        "default": 4000, "type": int,
        "choices": None, "min": 100, "max": 20000,
        "category": "SLIC/Bordes",
        "description": "Número de superpíxeles SLIC. Más = más detalle fino",
    },
    {
        "key": "slic_compact", "label": "SLIC compacidad",
        "default": 8.0, "type": float,
        "choices": None, "min": 0.1, "max": 100.0,
        "category": "SLIC/Bordes",
        "description": "Peso espacial vs color. Menor = más fiel al color",
    },
    {
        "key": "edge_deltaE", "label": "Umbral borde ΔE",
        "default": 3.5, "type": float,
        "choices": None, "min": 0.5, "max": 30.0,
        "category": "SLIC/Bordes",
        "description": "Diferencia de color mínima para trazar un borde. Menor = más líneas",
    },
    {
        "key": "smooth_open", "label": "Suavizado apertura",
        "default": 0, "type": int,
        "choices": None, "min": 0, "max": 10,
        "category": "SLIC/Bordes",
        "description": "Radio de apertura morfológica (elimina ruido pequeño)",
    },
    {
        "key": "smooth_close", "label": "Suavizado cierre",
        "default": 1, "type": int,
        "choices": None, "min": 0, "max": 10,
        "category": "SLIC/Bordes",
        "description": "Radio de cierre morfológico (rellena huecos pequeños)",
    },
    {
        "key": "min_region_area", "label": "Área mínima de región",
        "default": 30, "type": int,
        "choices": None, "min": 1, "max": 5000,
        "category": "SLIC/Bordes",
        "description": "Píxeles mínimos para que una región sea válida",
    },
    # ── SAM / Contornos / Numeración ─────────────────────────────────────────
    {
        "key": "sam_device", "label": "Dispositivo SAM",
        "default": "cuda", "type": str,
        "choices": ["auto", "cpu", "cuda", "mps", "dml"], "min": None, "max": None,
        "category": "SAM/Contornos/Numeración",
        "description": "cuda = NVIDIA GPU (recomendado)  |  cpu = estable  |  dml = AMD/Intel GPU (experimental)",
    },
    {
        "key": "sam_pps", "label": "SAM puntos por lado",
        "default": 128, "type": int,
        "choices": None, "min": 8, "max": 256,
        "category": "SAM/Contornos/Numeración",
        "description": "Más puntos = más detalle SAM, pero más lento",
    },
    {
        "key": "sam_min_area", "label": "SAM área mínima",
        "default": 400, "type": int,
        "choices": None, "min": 1, "max": 50000,
        "category": "SAM/Contornos/Numeración",
        "description": "Área mínima (px) para que SAM genere una máscara",
    },
    {
        "key": "sam_iou", "label": "SAM IoU threshold",
        "default": 0.90, "type": float,
        "choices": None, "min": 0.0, "max": 1.0,
        "category": "SAM/Contornos/Numeración",
        "description": "Umbral de calidad de máscara SAM",
    },
    {
        "key": "sam_stability", "label": "SAM stability score",
        "default": 0.93, "type": float,
        "choices": None, "min": 0.0, "max": 1.0,
        "category": "SAM/Contornos/Numeración",
        "description": "Umbral de estabilidad de máscara SAM",
    },
    {
        "key": "line_thickness", "label": "Grosor de línea",
        "default": 1, "type": int,
        "choices": None, "min": 1, "max": 10,
        "category": "SAM/Contornos/Numeración",
        "description": "Grosor en píxeles de los contornos del outline",
    },
    {
        "key": "force_closed", "label": "Forzar contornos cerrados",
        "default": True, "type": bool,
        "choices": None, "min": None, "max": None,
        "category": "SAM/Contornos/Numeración",
        "description": "Garantiza que todos los contornos estén cerrados (recomendado)",
    },
    {
        "key": "close_gaps_radius", "label": "Radio cierre de huecos",
        "default": 1, "type": int,
        "choices": None, "min": 0, "max": 10,
        "category": "SAM/Contornos/Numeración",
        "description": "Radio de cierre morfológico aplicado a los bordes",
    },
    {
        "key": "font_size", "label": "Tamaño de fuente",
        "default": 14, "type": int,
        "choices": None, "min": 6, "max": 72,
        "category": "SAM/Contornos/Numeración",
        "description": "Tamaño de los números en el outline",
    },
    {
        "key": "numbers_min_area", "label": "Área mínima para numerar",
        "default": 20, "type": int,
        "choices": None, "min": 1, "max": 5000,
        "category": "SAM/Contornos/Numeración",
        "description": "Área mínima (px) para que una región reciba número",
    },
]

PROFILE_MAX_WIDTH = {"a4": 4961, "a2": 7016}


# ──────────────────────────────────────────────────────────────────────────────
# Utilidades puras
# ──────────────────────────────────────────────────────────────────────────────
def scan_images(input_dir: Path) -> list:
    """Devuelve lista de imágenes en input_dir, ordenadas alfabéticamente."""
    if not input_dir.exists():
        print(f"\n❌ El directorio '{input_dir}' no existe.")
        print("   Crea la carpeta 'in\\' y coloca tus imágenes dentro.")
        sys.exit(1)

    images = sorted(
        [p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS],
        key=lambda p: p.name.lower(),
    )

    if not images:
        exts = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        print(f"\n❌ No se encontraron imágenes en '{input_dir}'.")
        print(f"   Extensiones soportadas: {exts}")
        print("   Coloca al menos una imagen en la carpeta 'in\\'.")
        sys.exit(1)

    return images


def derive_output_dir(image_path: Path) -> str:
    """Devuelve el nombre base del archivo sin extensión."""
    return image_path.stem


def validate_param(value_str: str, schema_entry: dict):
    """
    Convierte y valida value_str según schema_entry.
    Devuelve (valor_convertido, None) si válido, (None, mensaje_error) si no.
    """
    t = schema_entry["type"]
    choices = schema_entry.get("choices")
    vmin = schema_entry.get("min")
    vmax = schema_entry.get("max")
    label = schema_entry["label"]

    # Booleano
    if t is bool:
        if value_str.lower() in ("s", "si", "sí", "y", "yes", "true", "1"):
            return True, None
        if value_str.lower() in ("n", "no", "false", "0"):
            return False, None
        return None, f"'{value_str}' no es válido para '{label}'. Usa s/n o true/false."

    # Cadena con opciones fijas
    if t is str and choices:
        if value_str in choices:
            return value_str, None
        return None, f"'{value_str}' no es válido para '{label}'. Opciones: {', '.join(choices)}"

    # Entero
    if t is int:
        try:
            v = int(value_str)
        except ValueError:
            return None, f"'{value_str}' no es un número entero válido para '{label}'."
        if vmin is not None and v < vmin:
            return None, f"El valor mínimo para '{label}' es {vmin}."
        if vmax is not None and v > vmax:
            return None, f"El valor máximo para '{label}' es {vmax}."
        return v, None

    # Flotante
    if t is float:
        try:
            v = float(value_str)
        except ValueError:
            return None, f"'{value_str}' no es un número decimal válido para '{label}'."
        if vmin is not None and v < vmin:
            return None, f"El valor mínimo para '{label}' es {vmin}."
        if vmax is not None and v > vmax:
            return None, f"El valor máximo para '{label}' es {vmax}."
        return v, None

    # Cadena libre
    return value_str, None


def validate_checkpoint(project_root: Path):
    """
    Busca archivos .pth en project_root.
    Devuelve el Path si existe, None si no.
    """
    pth_files = sorted(project_root.glob("*.pth"))
    if not pth_files:
        return None
    if len(pth_files) > 1:
        print(f"\n⚠️  Se encontraron {len(pth_files)} archivos .pth. Se usará: {pth_files[0].name}")
    return pth_files[0]


def build_args(image_path: Path, output_dir: str, checkpoint: Path, config: dict) -> list:
    """
    Construye la lista de argumentos para subprocess.
    Primer elemento: sys.executable. Segundo: app.py.
    """
    args = [sys.executable, "app.py"]

    args += ["--input", str(image_path)]
    args += ["--out", output_dir]
    args += ["--sam-checkpoint", str(checkpoint)]

    # Perfil → max-width
    profile = config.get("profile", "a4")
    args += ["--max-width", str(PROFILE_MAX_WIDTH.get(profile, 4961))]

    args += ["--orientation", config["orientation"]]

    # Auto-K
    if config["auto_k"]:
        args.append("--auto-k")
        args += ["--k-min", str(config["k_min"])]
        args += ["--k-max", str(config["k_max"])]
        args += ["--target-ssim", str(config["target_ssim"])]
    else:
        args += ["--colors", str(config["colors"])]

    # SLIC / Bordes
    args += ["--slic-n", str(config["slic_n"])]
    args += ["--slic-compact", str(config["slic_compact"])]
    args += ["--edge-deltaE", str(config["edge_deltaE"])]
    args += ["--smooth-open", str(config["smooth_open"])]
    args += ["--smooth-close", str(config["smooth_close"])]
    args += ["--min-region-area", str(config["min_region_area"])]

    # SAM
    args += ["--sam-device", config["sam_device"]]
    args += ["--sam-pps", str(config["sam_pps"])]
    args += ["--sam-min-area", str(config["sam_min_area"])]
    args += ["--sam-iou", str(config["sam_iou"])]
    args += ["--sam-stability", str(config["sam_stability"])]

    # Contornos
    args += ["--line-thickness", str(config["line_thickness"])]
    if config["force_closed"]:
        args.append("--force-closed")
    args += ["--close-gaps-radius", str(config["close_gaps_radius"])]

    # Numeración
    args += ["--font-size", str(config["font_size"])]
    args += ["--numbers-min-area", str(config["numbers_min_area"])]

    return args


def run_app(args: list) -> int:
    """Ejecuta app.py con streaming de salida en tiempo real. Devuelve el código de salida."""
    try:
        proc = subprocess.Popen(args)
        proc.wait()
        return proc.returncode
    except FileNotFoundError:
        print("\n❌ No se encontró 'app.py'. Asegúrate de ejecutar el script desde el directorio raíz del proyecto.")
        return 1


# ──────────────────────────────────────────────────────────────────────────────
# UI / Menús
# ──────────────────────────────────────────────────────────────────────────────
def show_selection_menu(images: list) -> Path:
    """Muestra el menú de selección de imagen y devuelve la elegida."""
    print("\n" + "═" * 60)
    print("  🎨  Color-by-Numbers Generator")
    print("═" * 60)
    print("\n  Imágenes disponibles en 'in\\':\n")
    for i, img in enumerate(images, start=1):
        print(f"    [{i}]  {img.name}")
    print()

    while True:
        try:
            raw = input("  Elige una imagen (número): ").strip()
            n = int(raw)
            if 1 <= n <= len(images):
                return images[n - 1]
            print(f"  ⚠️  Introduce un número entre 1 y {len(images)}.")
        except ValueError:
            print("  ⚠️  Introduce un número válido.")


def _default_config() -> dict:
    return {s["key"]: s["default"] for s in PARAM_SCHEMA}


def _format_value(val) -> str:
    if isinstance(val, bool):
        return "Sí" if val else "No"
    return str(val)


def show_color_profile_menu(config: dict) -> dict:
    """Muestra el menú de perfiles de caso de uso y ajusta k_min, k_max, colors."""
    print("\n" + "═" * 60)
    print("  🎨  Perfil de colores")
    print("═" * 60)
    print("\n  ¿Para qué material es este kit?\n")
    for i, p in enumerate(COLOR_PROFILES, start=1):
        marker = "  " if p["key"] != "manual" else "  "
        k_info = f"  ({p['k_min']}–{p['k_max']} colores)" if p["k_min"] else ""
        print(f"    [{i:>2}]  {p['label']}{k_info}")
        print(f"          {p['description']}")

    print()
    while True:
        try:
            raw = input("  Elige un perfil (número): ").strip()
            n = int(raw)
            if 1 <= n <= len(COLOR_PROFILES):
                profile = COLOR_PROFILES[n - 1]
                break
            print(f"  ⚠️  Introduce un número entre 1 y {len(COLOR_PROFILES)}.")
        except ValueError:
            print("  ⚠️  Introduce un número válido.")

    if profile["key"] != "manual":
        config["auto_k"] = True
        config["k_min"] = profile["k_min"]
        config["k_max"] = profile["k_max"]
        config["colors"] = profile["colors"]
        print(f"\n  ✅ Perfil '{profile['label']}' aplicado.")
        print(f"     Auto-K activado: buscará entre {profile['k_min']} y {profile['k_max']} colores.")
    else:
        print("\n  Modo manual: ajusta k-min, k-max y colores en la configuración avanzada.")

    return config


def show_config_menu(config: dict) -> dict:
    """Muestra el menú de configuración avanzada y devuelve la config confirmada."""
    # Agrupar parámetros por categoría manteniendo orden
    categories = {}
    for s in PARAM_SCHEMA:
        cat = s["category"]
        categories.setdefault(cat, []).append(s)

    # Construir índice global de parámetros (1-based)
    indexed = []
    for cat_params in categories.values():
        for s in cat_params:
            indexed.append(s)

    while True:
        print("\n" + "═" * 60)
        print("  ⚙️   Configuración avanzada")
        print("═" * 60)

        idx = 1
        cat_start = {}
        for cat, params in categories.items():
            print(f"\n  ── {cat} ──")
            for s in params:
                val_str = _format_value(config[s["key"]])
                print(f"    [{idx:>2}]  {s['label']:<35} {val_str}")
                cat_start[idx] = s
                idx += 1

        print("\n  ── Acciones ──")
        print("    [c]  Confirmar y ejecutar")
        print("    [r]  Resetear a valores por defecto")
        print("    [q]  Salir\n")

        raw = input("  Elige un número para editar, o una acción: ").strip().lower()

        if raw == "c":
            return config
        if raw == "q":
            print("\n  Hasta luego.")
            sys.exit(0)
        if raw == "r":
            config = _default_config()
            print("  ✅ Valores reseteados a los valores por defecto.")
            continue

        try:
            n = int(raw)
            if not (1 <= n <= len(indexed)):
                print(f"  ⚠️  Número fuera de rango (1–{len(indexed)}).")
                continue
        except ValueError:
            print("  ⚠️  Opción no reconocida.")
            continue

        schema_entry = indexed[n - 1]
        key = schema_entry["key"]
        current = _format_value(config[key])

        # Mostrar ayuda de entrada
        hint = ""
        if schema_entry["choices"]:
            hint = f"  Opciones: {', '.join(schema_entry['choices'])}"
        elif schema_entry["type"] is bool:
            hint = "  Opciones: s (sí) / n (no)"
        elif schema_entry["min"] is not None:
            hint = f"  Rango: {schema_entry['min']} – {schema_entry['max']}"

        print(f"\n  Editando: {schema_entry['label']}")
        print(f"  {schema_entry['description']}")
        if hint:
            print(hint)

        while True:
            new_raw = input(f"  Valor actual [{current}]: ").strip()
            if new_raw == "":
                break  # mantener valor actual
            val, err = validate_param(new_raw, schema_entry)
            if err:
                print(f"  ⚠️  {err}")
            else:
                config[key] = val
                print(f"  ✅ '{schema_entry['label']}' actualizado a: {_format_value(val)}")
                break

    return config


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    project_root = Path(__file__).parent
    input_dir = project_root / "in"

    # Fase 1: Selección de imagen
    images = scan_images(input_dir)
    selected = show_selection_menu(images)
    output_dir = derive_output_dir(selected)
    print(f"\n  ✅ Imagen seleccionada: {selected.name}")
    print(f"  📁 Directorio de salida: res\\{output_dir}")

    # Fase 2: Perfil de colores
    config = _default_config()
    config = show_color_profile_menu(config)

    # Fase 3: Configuración avanzada
    config = show_config_menu(config)

    # Fase 3: Validar checkpoint SAM
    checkpoint = validate_checkpoint(project_root)
    if checkpoint is None:
        print("\n❌ No se encontró el checkpoint SAM.")
        print(f"   Archivo esperado : {SAM_CHECKPOINT_NAME}")
        print(f"   Ubicación        : {project_root}")
        print(f"   Descarga         : {SAM_DOWNLOAD_URL}")
        print("\n   Comando de descarga (PowerShell):")
        print(f"   Invoke-WebRequest -Uri '{SAM_DOWNLOAD_URL}' -OutFile '{SAM_CHECKPOINT_NAME}'")
        sys.exit(1)

    # Actualizar output_dir para que vaya a res/
    out_path = str(project_root / "res" / output_dir)

    # Construir y ejecutar
    args = build_args(selected, out_path, checkpoint, config)

    print("\n" + "═" * 60)
    print("  🚀  Iniciando procesamiento...")
    print("═" * 60)
    print(f"\n  Comando:\n  {' '.join(args)}\n")

    code = run_app(args)

    print("\n" + "═" * 60)
    if code == 0:
        print(f"  ✅ Proceso completado. Resultados en: res\\{output_dir}")
    else:
        print(f"  ❌ El proceso terminó con error (código {code}).")
    print("═" * 60)

    sys.exit(code)


if __name__ == "__main__":
    main()
