#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_config_schema.py — Tests para config_schema.py (Fase 1)
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

from config_schema import (
    PARAM_SCHEMA,
    COLOR_PROFILES,
    default_config,
    apply_color_profile,
    validate_config,
    build_args,
    make_output_dir,
)


# ──────────────────────────────────────────────────────────────────────────────
# test_default_config_has_all_keys
# ──────────────────────────────────────────────────────────────────────────────

def test_default_config_has_all_keys():
    """default_config() debe contener todas las claves definidas en PARAM_SCHEMA."""
    config = default_config()
    schema_keys = {s["key"] for s in PARAM_SCHEMA}
    assert schema_keys == set(config.keys()), (
        f"Claves faltantes: {schema_keys - set(config.keys())}, "
        f"claves extra: {set(config.keys()) - schema_keys}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# test_apply_color_profile_updates_fields
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_color_profile_updates_fields():
    """apply_color_profile actualiza k_min, k_max, colors, auto_k sin mutar el original."""
    # Usar un perfil no-manual con valores conocidos
    profile = next(p for p in COLOR_PROFILES if p["key"] != "manual")
    original = default_config()
    original_copy = dict(original)

    result = apply_color_profile(original, profile["key"])

    # No muta el original
    assert original == original_copy, "apply_color_profile mutó el dict original"

    # Actualiza los campos correctos
    assert result["k_min"] == profile["k_min"]
    assert result["k_max"] == profile["k_max"]
    assert result["colors"] == profile["colors"]
    assert result["auto_k"] is True
    assert result["color_profile"] == profile["key"]

    # No modifica otros campos
    for key in original:
        if key not in ("k_min", "k_max", "colors", "auto_k", "color_profile"):
            assert result[key] == original[key], f"Campo '{key}' fue modificado inesperadamente"


# ──────────────────────────────────────────────────────────────────────────────
# test_apply_color_profile_manual_no_change
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_color_profile_manual_no_change():
    """El perfil 'manual' no debe cambiar k_min ni k_max."""
    config = default_config()
    original_k_min = config["k_min"]
    original_k_max = config["k_max"]

    result = apply_color_profile(config, "manual")

    assert result["k_min"] == original_k_min
    assert result["k_max"] == original_k_max
    assert result["color_profile"] == "manual"


# ──────────────────────────────────────────────────────────────────────────────
# test_validate_config_accepts_defaults
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_config_accepts_defaults():
    """default_config() no debe producir ningún error de validación."""
    config = default_config()
    errors = validate_config(config)
    assert errors == [], f"Se esperaba lista vacía, se obtuvo: {errors}"


# ──────────────────────────────────────────────────────────────────────────────
# test_validate_config_rejects_out_of_range
# ──────────────────────────────────────────────────────────────────────────────

def test_validate_config_rejects_out_of_range():
    """Un valor fuera de rango debe producir un error que incluya el nombre del parámetro."""
    config = default_config()
    # k_min tiene min=2, max=64 — ponemos un valor fuera de rango
    config["k_min"] = 1  # por debajo del mínimo (2)

    errors = validate_config(config)

    assert len(errors) > 0, "Se esperaba al menos un error de validación"
    # El error debe mencionar el parámetro
    assert any("k_min" in e for e in errors), (
        f"El error no menciona 'k_min'. Errores: {errors}"
    )


# ──────────────────────────────────────────────────────────────────────────────
# test_build_args_starts_with_executable
# ──────────────────────────────────────────────────────────────────────────────

def test_build_args_starts_with_executable():
    """El primer elemento debe ser sys.executable y el segundo 'app.py'."""
    config = default_config()
    args = build_args("in/test.jpg", "res/out", "sam.pth", config)

    assert args[0] == sys.executable, f"Se esperaba sys.executable, se obtuvo: {args[0]}"
    assert args[1] == "app.py", f"Se esperaba 'app.py', se obtuvo: {args[1]}"


# ──────────────────────────────────────────────────────────────────────────────
# test_build_args_auto_k_true
# ──────────────────────────────────────────────────────────────────────────────

def test_build_args_auto_k_true():
    """Cuando auto_k=True, los args deben incluir --auto-k y no --colors."""
    config = default_config()
    config["auto_k"] = True
    args = build_args("in/test.jpg", "res/out", "sam.pth", config)

    assert "--auto-k" in args, "--auto-k debe estar presente cuando auto_k=True"
    assert "--colors" not in args, "--colors no debe estar presente cuando auto_k=True"


# ──────────────────────────────────────────────────────────────────────────────
# test_build_args_auto_k_false
# ──────────────────────────────────────────────────────────────────────────────

def test_build_args_auto_k_false():
    """Cuando auto_k=False, los args deben incluir --colors N y no --auto-k."""
    config = default_config()
    config["auto_k"] = False
    config["colors"] = 16
    args = build_args("in/test.jpg", "res/out", "sam.pth", config)

    assert "--auto-k" not in args, "--auto-k no debe estar presente cuando auto_k=False"
    assert "--colors" in args, "--colors debe estar presente cuando auto_k=False"
    # Verificar que el valor de colors está en los args
    colors_idx = args.index("--colors")
    assert args[colors_idx + 1] == "16", f"Se esperaba '16', se obtuvo: {args[colors_idx + 1]}"


# ──────────────────────────────────────────────────────────────────────────────
# test_build_args_force_closed_true
# ──────────────────────────────────────────────────────────────────────────────

def test_build_args_force_closed_true():
    """Cuando force_closed=True, los args deben incluir --force-closed."""
    config = default_config()
    config["force_closed"] = True
    args = build_args("in/test.jpg", "res/out", "sam.pth", config)

    assert "--force-closed" in args, "--force-closed debe estar presente cuando force_closed=True"


def test_build_args_force_closed_false():
    """Cuando force_closed=False, los args no deben incluir --force-closed."""
    config = default_config()
    config["force_closed"] = False
    args = build_args("in/test.jpg", "res/out", "sam.pth", config)

    assert "--force-closed" not in args, "--force-closed no debe estar presente cuando force_closed=False"


# ──────────────────────────────────────────────────────────────────────────────
# test_make_output_dir_name_format
# ──────────────────────────────────────────────────────────────────────────────

def test_make_output_dir_name_format(tmp_path):
    """El nombre del directorio debe contener imageStem, k, pps, dE, slic, profile y timestamp."""
    config = default_config()
    config["color_profile"] = "lapices_24"
    config["sam_pps"] = 32
    config["edge_deltaE"] = 3.5
    config["slic_n"] = 4000

    k_result = 14
    started_at = datetime(2024, 1, 15, 14, 32, 5)
    image_stem = "frida02"

    result_path = make_output_dir(tmp_path, image_stem, config, k_result, started_at)
    name = result_path.name

    assert image_stem in name, f"imageStem '{image_stem}' no encontrado en '{name}'"
    assert f"k{k_result}" in name, f"'k{k_result}' no encontrado en '{name}'"
    assert f"pps{config['sam_pps']}" in name, f"'pps{config['sam_pps']}' no encontrado en '{name}'"
    # dE = 3.5 * 10 = 35
    dE_int = round(config["edge_deltaE"] * 10)
    assert f"dE{dE_int}" in name, f"'dE{dE_int}' no encontrado en '{name}'"
    assert f"slic{config['slic_n']}" in name, f"'slic{config['slic_n']}' no encontrado en '{name}'"
    assert config["color_profile"] in name, f"profile '{config['color_profile']}' no encontrado en '{name}'"
    assert "20240115_143205" in name, f"timestamp '20240115_143205' no encontrado en '{name}'"


# ──────────────────────────────────────────────────────────────────────────────
# test_make_output_dir_creates_directory
# ──────────────────────────────────────────────────────────────────────────────

def test_make_output_dir_creates_directory(tmp_path):
    """make_output_dir debe crear el directorio en disco."""
    config = default_config()
    started_at = datetime(2024, 6, 1, 10, 0, 0)

    result_path = make_output_dir(tmp_path, "test_image", config, 12, started_at)

    assert result_path.exists(), f"El directorio '{result_path}' no fue creado"
    assert result_path.is_dir(), f"'{result_path}' no es un directorio"
