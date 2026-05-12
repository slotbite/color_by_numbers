#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_schema.py — Esquema de parámetros, validación y construcción de argumentos
para el generador Color-by-Numbers. Extraído de run_interactive.py.
"""

import sys
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# ──────────────────────────────────────────────────────────────────────────────
# Perfiles de caso de uso (copia exacta de run_interactive.py)
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
# Esquema de parámetros (copia exacta de run_interactive.py + entrada color_profile)
# ──────────────────────────────────────────────────────────────────────────────
PARAM_SCHEMA = [
    # ── Perfil de color (añadido para web-ui) ────────────────────────────────
    {
        "key": "color_profile", "label": "Perfil de color",
        "default": "manual", "type": str,
        "choices": [p["key"] for p in COLOR_PROFILES], "min": None, "max": None,
        "category": "Perfil/Salida",
        "description": "Perfil de caso de uso artístico",
    },
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
        "default": "cpu", "type": str,
        "choices": ["auto", "cpu", "cuda", "mps", "dml"], "min": None, "max": None,
        "category": "SAM/Contornos/Numeración",
        "description": "cpu = estable  |  dml = AMD/Intel GPU (experimental, puede fallar con SAM)",
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
# Funciones públicas
# ──────────────────────────────────────────────────────────────────────────────

def default_config() -> dict:
    """Devuelve un dict {key: default} para todos los parámetros del esquema."""
    return {s["key"]: s["default"] for s in PARAM_SCHEMA}


def apply_color_profile(config: dict, profile_key: str) -> dict:
    """
    Aplica un perfil de color a la config.
    Si el perfil no es 'manual', actualiza k_min, k_max, colors, auto_k y color_profile.
    Devuelve nueva config (no muta el original).
    """
    new_config = dict(config)
    profile = next((p for p in COLOR_PROFILES if p["key"] == profile_key), None)
    if profile is None or profile["key"] == "manual":
        new_config["color_profile"] = "manual"
        return new_config

    new_config["k_min"] = profile["k_min"]
    new_config["k_max"] = profile["k_max"]
    new_config["colors"] = profile["colors"]
    new_config["auto_k"] = True
    new_config["color_profile"] = profile["key"]
    return new_config


def validate_config(config: dict) -> list[str]:
    """
    Valida todos los parámetros de config contra PARAM_SCHEMA.
    Devuelve lista de mensajes de error (vacía si todo es válido).
    Cada mensaje incluye el nombre del parámetro y el rango/opciones permitidas.
    """
    errors = []
    for s in PARAM_SCHEMA:
        key = s["key"]
        if key not in config:
            continue
        value = config[key]
        t = s["type"]
        choices = s.get("choices")
        vmin = s.get("min")
        vmax = s.get("max")
        label = s["label"]

        # Verificar tipo (bool es subclase de int, verificar primero)
        if t is bool:
            if not isinstance(value, bool):
                errors.append(f"'{label}' ({key}): se esperaba bool, se recibió {type(value).__name__}.")
            continue

        if not isinstance(value, t):
            # Permitir int donde se espera float
            if t is float and isinstance(value, int):
                pass
            else:
                errors.append(f"'{label}' ({key}): se esperaba {t.__name__}, se recibió {type(value).__name__}.")
                continue

        # Verificar choices
        if choices is not None:
            if value not in choices:
                errors.append(
                    f"'{label}' ({key}): valor '{value}' no válido. Opciones: {', '.join(str(c) for c in choices)}."
                )
            continue

        # Verificar rango
        if vmin is not None and value < vmin:
            errors.append(
                f"'{label}' ({key}): valor {value} fuera de rango [{vmin}, {vmax}]."
            )
        elif vmax is not None and value > vmax:
            errors.append(
                f"'{label}' ({key}): valor {value} fuera de rango [{vmin}, {vmax}]."
            )

    return errors


def build_args(image_path: str, output_dir: str, checkpoint: str, config: dict) -> list[str]:
    """
    Construye la lista de argumentos para subprocess equivalente a build_args de run_interactive.py.
    Primer elemento: sys.executable. Segundo: 'app.py'.
    """
    args = [sys.executable, "app.py"]

    args += ["--input", str(image_path)]
    args += ["--out", str(output_dir)]
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


def make_output_dir(
    output_base: Path,
    image_stem: str,
    config: dict,
    k_result: int,
    started_at: datetime,
) -> Path:
    """
    Construye y crea el directorio de trabajo para una ejecución.

    Nombre: <imageStem>__k<K>_pps<PPS>_dE<DELTAE*10>_slic<SLICN>_<colorProfile>__<YYYYMMDD_HHMMSS>
    Ejemplo: frida02__k14_pps32_dE35_slic4000_lapices24__20240115_143205

    - deltaE se multiplica x10 y se redondea para evitar puntos en el nombre.
    - Crea el directorio con mkdir(parents=True, exist_ok=True).
    - Devuelve el Path absoluto al directorio creado.
    """
    dE_int = round(config["edge_deltaE"] * 10)
    profile = config.get("color_profile", "manual")
    ts = started_at.strftime("%Y%m%d_%H%M%S")
    name = (
        f"{image_stem}"
        f"__k{k_result}"
        f"_pps{config['sam_pps']}"
        f"_dE{dE_int}"
        f"_slic{config['slic_n']}"
        f"_{profile}"
        f"__{ts}"
    )
    path = output_base / name
    path.mkdir(parents=True, exist_ok=True)
    return path
