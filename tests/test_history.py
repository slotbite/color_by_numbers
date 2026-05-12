#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_history.py — Tests para history.py (Fase 2 del spec web-ui).

Incluye tests unitarios y tests basados en propiedades con Hypothesis.
"""

import json
import tempfile
from pathlib import Path

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from history import ExecutionRecord, load_history, save_entry, get_history

# ──────────────────────────────────────────────────────────────────────────────
# Estrategias Hypothesis
# ──────────────────────────────────────────────────────────────────────────────

# Timestamps ISO 8601 simples (sin zona horaria para simplicidad)
iso_timestamps = st.builds(
    lambda y, mo, d, h, mi, s: f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{mi:02d}:{s:02d}Z",
    y=st.integers(min_value=2020, max_value=2030),
    mo=st.integers(min_value=1, max_value=12),
    d=st.integers(min_value=1, max_value=28),
    h=st.integers(min_value=0, max_value=23),
    mi=st.integers(min_value=0, max_value=59),
    s=st.integers(min_value=0, max_value=59),
)

# job_id en formato <YYYYMMDD_HHMMSS>_<image_stem>
job_ids = st.builds(
    lambda ts, stem: f"{ts}_{stem}",
    ts=st.from_regex(r"20[2-3]\d[01]\d[0-3]\d_[0-2]\d[0-5]\d[0-5]\d", fullmatch=True),
    stem=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
        min_size=1,
        max_size=20,
    ),
)

# Estrategia para generar ExecutionRecord arbitrarios
execution_records = st.builds(
    ExecutionRecord,
    job_id=job_ids,
    image_name=st.text(min_size=1, max_size=50).map(lambda s: s + ".jpg"),
    config=st.fixed_dictionaries({
        "color_profile": st.sampled_from(["manual", "lapices_24", "acuarela_basica"]),
        "k_min": st.integers(min_value=2, max_value=32),
        "k_max": st.integers(min_value=2, max_value=64),
        "colors": st.integers(min_value=2, max_value=64),
        "auto_k": st.booleans(),
        "edge_deltaE": st.floats(min_value=0.5, max_value=30.0, allow_nan=False),
        "sam_pps": st.integers(min_value=8, max_value=256),
        "slic_n": st.integers(min_value=100, max_value=20000),
    }),
    k_result=st.integers(min_value=2, max_value=64),
    status=st.sampled_from(["pending", "running", "completed", "error"]),
    started_at=iso_timestamps,
    duration_s=st.one_of(st.none(), st.floats(min_value=0.0, max_value=3600.0, allow_nan=False)),
    output_dir=st.text(min_size=1, max_size=100),
    error_msg=st.one_of(st.none(), st.text(min_size=1, max_size=200)),
)


# ──────────────────────────────────────────────────────────────────────────────
# Tests unitarios
# ──────────────────────────────────────────────────────────────────────────────

def test_history_empty_on_missing_file(tmp_path):
    """load_history devuelve [] si el archivo no existe."""
    missing = tmp_path / "nonexistent" / "history.json"
    result = load_history(missing)
    assert result == []


def test_save_and_load_round_trip(tmp_path):
    """Guardar y cargar un registro produce el mismo resultado."""
    history_file = tmp_path / "history.json"
    record = ExecutionRecord(
        job_id="20240115_143205_frida02",
        image_name="frida02.jpg",
        config={"color_profile": "lapices_24", "k_min": 16, "k_max": 24},
        k_result=18,
        status="completed",
        started_at="2024-01-15T14:32:05Z",
        duration_s=187.4,
        output_dir="/data/res/frida02__k18_pps32_dE35_slic4000_lapices24__20240115_143205",
        error_msg=None,
    )

    save_entry(history_file, record)
    loaded = load_history(history_file)

    assert len(loaded) == 1
    loaded_record = loaded[0]
    assert loaded_record.job_id == record.job_id
    assert loaded_record.image_name == record.image_name
    assert loaded_record.config == record.config
    assert loaded_record.k_result == record.k_result
    assert loaded_record.status == record.status
    assert loaded_record.started_at == record.started_at
    assert loaded_record.duration_s == record.duration_s
    assert loaded_record.output_dir == record.output_dir
    assert loaded_record.error_msg == record.error_msg


def test_save_updates_existing_entry(tmp_path):
    """Guardar dos veces el mismo job_id actualiza el registro (no duplica)."""
    history_file = tmp_path / "history.json"
    record_v1 = ExecutionRecord(
        job_id="20240115_143205_frida02",
        image_name="frida02.jpg",
        config={"k_min": 10},
        k_result=12,
        status="running",
        started_at="2024-01-15T14:32:05Z",
        duration_s=None,
        output_dir="/data/res/frida02",
        error_msg=None,
    )
    record_v2 = ExecutionRecord(
        job_id="20240115_143205_frida02",  # mismo job_id
        image_name="frida02.jpg",
        config={"k_min": 10},
        k_result=14,
        status="completed",
        started_at="2024-01-15T14:32:05Z",
        duration_s=200.0,
        output_dir="/data/res/frida02",
        error_msg=None,
    )

    save_entry(history_file, record_v1)
    save_entry(history_file, record_v2)

    loaded = load_history(history_file)
    assert len(loaded) == 1  # no duplicado
    assert loaded[0].status == "completed"
    assert loaded[0].k_result == 14
    assert loaded[0].duration_s == 200.0


def test_history_sorted_desc(tmp_path):
    """Múltiples registros se devuelven ordenados por started_at descendente."""
    history_file = tmp_path / "history.json"

    timestamps = [
        "2024-01-10T10:00:00Z",
        "2024-01-15T14:32:05Z",
        "2024-01-12T08:00:00Z",
        "2024-01-20T20:00:00Z",
    ]

    for i, ts in enumerate(timestamps):
        record = ExecutionRecord(
            job_id=f"job_{i:03d}",
            image_name=f"image_{i}.jpg",
            config={},
            k_result=10,
            status="completed",
            started_at=ts,
            duration_s=100.0,
            output_dir=f"/data/res/job_{i}",
            error_msg=None,
        )
        save_entry(history_file, record)

    loaded = load_history(history_file)
    assert len(loaded) == 4

    # Verificar orden descendente
    for i in range(len(loaded) - 1):
        assert loaded[i].started_at >= loaded[i + 1].started_at


def test_history_atomic_write_no_corruption(tmp_path):
    """
    Si el archivo existe y se guarda un nuevo registro, el archivo original
    no se corrompe (la escritura es atómica).
    """
    history_file = tmp_path / "history.json"

    # Guardar un registro inicial
    record1 = ExecutionRecord(
        job_id="20240115_143205_frida02",
        image_name="frida02.jpg",
        config={"k_min": 10},
        k_result=12,
        status="completed",
        started_at="2024-01-15T14:32:05Z",
        duration_s=100.0,
        output_dir="/data/res/frida02",
        error_msg=None,
    )
    save_entry(history_file, record1)

    # Verificar que el archivo es JSON válido antes de la segunda escritura
    with open(history_file, "r", encoding="utf-8") as f:
        data_before = json.load(f)
    assert len(data_before) == 1

    # Guardar un segundo registro
    record2 = ExecutionRecord(
        job_id="20240116_090000_among_us",
        image_name="among_us.jpg",
        config={"k_min": 8},
        k_result=8,
        status="completed",
        started_at="2024-01-16T09:00:00Z",
        duration_s=150.0,
        output_dir="/data/res/among_us",
        error_msg=None,
    )
    save_entry(history_file, record2)

    # El archivo debe seguir siendo JSON válido y contener ambos registros
    with open(history_file, "r", encoding="utf-8") as f:
        data_after = json.load(f)
    assert len(data_after) == 2

    # No debe quedar fichero .tmp
    tmp_file = history_file.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_config_preserved_in_record(tmp_path):
    """La config guardada en el registro es idéntica a la original."""
    history_file = tmp_path / "history.json"
    original_config = {
        "color_profile": "lapices_24",
        "profile": "a4",
        "orientation": "landscape",
        "auto_k": True,
        "colors": 20,
        "k_min": 16,
        "k_max": 24,
        "target_ssim": 0.965,
        "slic_n": 4000,
        "slic_compact": 8.0,
        "edge_deltaE": 3.5,
        "smooth_open": 0,
        "smooth_close": 1,
        "min_region_area": 30,
        "sam_device": "cpu",
        "sam_pps": 32,
        "sam_min_area": 400,
        "sam_iou": 0.90,
        "sam_stability": 0.93,
        "line_thickness": 1,
        "force_closed": True,
        "close_gaps_radius": 1,
        "font_size": 14,
        "numbers_min_area": 20,
    }

    record = ExecutionRecord(
        job_id="20240115_143205_frida02",
        image_name="frida02.jpg",
        config=original_config,
        k_result=18,
        status="completed",
        started_at="2024-01-15T14:32:05Z",
        duration_s=187.4,
        output_dir="/data/res/frida02",
        error_msg=None,
    )

    save_entry(history_file, record)
    loaded = load_history(history_file)

    assert len(loaded) == 1
    assert loaded[0].config == original_config


# ──────────────────────────────────────────────────────────────────────────────
# Tests basados en propiedades (Hypothesis)
# ──────────────────────────────────────────────────────────────────────────────

# Feature: web-ui, Property 7: Round-trip de serialización del historial
@given(record=execution_records)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_history_round_trip(record):
    """
    Para cualquier ExecutionRecord con valores arbitrarios, serializar con
    save_entry y deserializar con load_history produce un registro idéntico.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        history_file = Path(tmpdir) / "history.json"
        save_entry(history_file, record)
        loaded = load_history(history_file)

    assert len(loaded) >= 1
    # Buscar el registro por job_id
    found = next((r for r in loaded if r.job_id == record.job_id), None)
    assert found is not None
    assert found.job_id == record.job_id
    assert found.image_name == record.image_name
    assert found.config == record.config
    assert found.k_result == record.k_result
    assert found.status == record.status
    assert found.started_at == record.started_at
    assert found.output_dir == record.output_dir
    assert found.error_msg == record.error_msg
    # duration_s: comparar con tolerancia para floats
    if record.duration_s is None:
        assert found.duration_s is None
    else:
        assert found.duration_s == pytest.approx(record.duration_s, rel=1e-6)


# Feature: web-ui, Property 8: Historial ordenado por timestamp descendente
@given(
    records=st.lists(
        execution_records,
        min_size=2,
        max_size=10,
        unique_by=lambda r: r.job_id,
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_history_sorted_desc_property(records):
    """
    Para cualquier lista de registros con job_ids distintos, get_history
    devuelve la lista ordenada por started_at de más reciente a más antiguo.
    """
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        history_file = Path(tmpdir) / "history.json"
        for record in records:
            save_entry(history_file, record)
        loaded = get_history(history_file)

    assert len(loaded) == len(records)

    for i in range(len(loaded) - 1):
        assert loaded[i].started_at >= loaded[i + 1].started_at


# Feature: web-ui, Property 9: Reutilización de configuración preserva todos los parámetros
@given(record=execution_records)
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture])
def test_config_reuse_preserves_params(record):
    """
    Para cualquier ExecutionRecord guardado en el historial, la configuración
    extraída del registro contiene exactamente las mismas claves y valores
    que la configuración original.
    """
    original_config = dict(record.config)

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        history_file = Path(tmpdir) / "history.json"
        save_entry(history_file, record)
        loaded = load_history(history_file)

    found = next((r for r in loaded if r.job_id == record.job_id), None)
    assert found is not None
    assert found.config == original_config
    assert set(found.config.keys()) == set(original_config.keys())
