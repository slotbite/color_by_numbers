#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_web_app.py — Tests para las funciones puras de web_app.py.

Las funciones puras (load_env_config, scan_images, results_exist) son importables
sin que streamlit esté instalado, ya que web_app.py solo importa streamlit dentro
de las funciones de renderizado (render_*) y main().
"""

import os
from pathlib import Path

import pytest

# Importar solo las funciones puras — no requieren streamlit
from web_app import load_env_config, results_exist, scan_images


# ──────────────────────────────────────────────────────────────────────────────
# test_load_env_config_defaults
# ──────────────────────────────────────────────────────────────────────────────

def test_load_env_config_defaults(monkeypatch):
    """Sin variables de entorno, devuelve los valores por defecto."""
    # Eliminar las variables si existen en el entorno
    monkeypatch.delenv("SAM_CHECKPOINT_PATH", raising=False)
    monkeypatch.delenv("INPUT_DIR", raising=False)
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    monkeypatch.delenv("PORT", raising=False)

    cfg = load_env_config()

    assert cfg["SAM_CHECKPOINT_PATH"] == "./sam_vit_b_01ec64.pth"
    assert cfg["INPUT_DIR"] == "./in"
    assert cfg["OUTPUT_DIR"] == "./res"
    assert cfg["PORT"] == "8501"


# ──────────────────────────────────────────────────────────────────────────────
# test_load_env_config_reads_env_vars
# ──────────────────────────────────────────────────────────────────────────────

def test_load_env_config_reads_env_vars(monkeypatch):
    """Con variables de entorno seteadas, devuelve exactamente esos valores."""
    monkeypatch.setenv("SAM_CHECKPOINT_PATH", "/custom/sam.pth")
    monkeypatch.setenv("INPUT_DIR", "/custom/input")
    monkeypatch.setenv("OUTPUT_DIR", "/custom/output")
    monkeypatch.setenv("PORT", "9000")

    cfg = load_env_config()

    assert cfg["SAM_CHECKPOINT_PATH"] == "/custom/sam.pth"
    assert cfg["INPUT_DIR"] == "/custom/input"
    assert cfg["OUTPUT_DIR"] == "/custom/output"
    assert cfg["PORT"] == "9000"


# ──────────────────────────────────────────────────────────────────────────────
# test_results_exist_false_when_missing
# ──────────────────────────────────────────────────────────────────────────────

def test_results_exist_false_when_missing(tmp_path):
    """Devuelve False cuando faltan los archivos PNG de resultado."""
    # Directorio vacío
    assert results_exist(str(tmp_path)) is False

    # Solo uno de los tres archivos
    (tmp_path / "01_outline_numbered.png").touch()
    assert results_exist(str(tmp_path)) is False

    # Dos de los tres
    (tmp_path / "02_colored_reference.png").touch()
    assert results_exist(str(tmp_path)) is False


def test_results_exist_false_for_nonexistent_dir():
    """Devuelve False cuando el directorio no existe."""
    assert results_exist("/nonexistent/path/that/does/not/exist") is False


# ──────────────────────────────────────────────────────────────────────────────
# test_results_exist_true_when_present
# ──────────────────────────────────────────────────────────────────────────────

def test_results_exist_true_when_present(tmp_path):
    """Devuelve True cuando los 3 PNGs existen en el directorio."""
    (tmp_path / "01_outline_numbered.png").touch()
    (tmp_path / "02_colored_reference.png").touch()
    (tmp_path / "03_palette.png").touch()

    assert results_exist(str(tmp_path)) is True


def test_results_exist_true_ignores_extra_files(tmp_path):
    """Devuelve True aunque haya archivos adicionales en el directorio."""
    (tmp_path / "01_outline_numbered.png").touch()
    (tmp_path / "02_colored_reference.png").touch()
    (tmp_path / "03_palette.png").touch()
    (tmp_path / "color_by_numbers_kit.pdf").touch()
    (tmp_path / "palette.csv").touch()

    assert results_exist(str(tmp_path)) is True


# ──────────────────────────────────────────────────────────────────────────────
# test_scan_images_filters_extensions
# ──────────────────────────────────────────────────────────────────────────────

def test_scan_images_filters_extensions(tmp_path):
    """Solo devuelve archivos con extensiones soportadas."""
    # Crear archivos con extensiones soportadas
    supported = ["foto.jpg", "imagen.jpeg", "dibujo.png", "arte.webp", "mapa.bmp"]
    # Crear archivos con extensiones NO soportadas
    unsupported = ["documento.pdf", "datos.csv", "texto.txt", "video.mp4", "archivo.zip"]

    for name in supported + unsupported:
        (tmp_path / name).touch()

    result = scan_images(tmp_path)
    result_names = {p.name for p in result}

    # Todos los soportados deben estar
    for name in supported:
        assert name in result_names, f"Falta archivo soportado: {name}"

    # Ninguno de los no soportados debe estar
    for name in unsupported:
        assert name not in result_names, f"Archivo no soportado incluido: {name}"


def test_scan_images_case_insensitive_extensions(tmp_path):
    """Filtra extensiones de forma case-insensitive."""
    (tmp_path / "foto.JPG").touch()
    (tmp_path / "imagen.PNG").touch()
    (tmp_path / "arte.Webp").touch()
    (tmp_path / "documento.PDF").touch()

    result = scan_images(tmp_path)
    result_names = {p.name for p in result}

    assert "foto.JPG" in result_names
    assert "imagen.PNG" in result_names
    assert "arte.Webp" in result_names
    assert "documento.PDF" not in result_names


def test_scan_images_sorted_alphabetically(tmp_path):
    """Devuelve los archivos ordenados alfabéticamente por nombre."""
    names = ["zebra.jpg", "apple.png", "mango.bmp", "banana.jpeg"]
    for name in names:
        (tmp_path / name).touch()

    result = scan_images(tmp_path)
    result_names = [p.name for p in result]

    assert result_names == sorted(names, key=str.lower)


def test_scan_images_empty_dir(tmp_path):
    """Devuelve lista vacía para un directorio vacío."""
    result = scan_images(tmp_path)
    assert result == []


def test_scan_images_nonexistent_dir(tmp_path):
    """Devuelve lista vacía si el directorio no existe."""
    result = scan_images(tmp_path / "no_existe")
    assert result == []
