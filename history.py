#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
history.py — Historial persistente JSON de ejecuciones Color-by-Numbers.
"""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ExecutionRecord:
    """Registro de una ejecución del generador Color-by-Numbers."""

    job_id: str          # "<YYYYMMDD_HHMMSS>_<image_stem>"
    image_name: str      # nombre del archivo de imagen (con extensión)
    config: dict         # copia completa de todos los parámetros
    k_result: int        # número de colores real usado (post Auto-K)
    status: str          # "pending" | "running" | "completed" | "error"
    started_at: str      # ISO 8601
    duration_s: Optional[float]  # segundos; None si no terminó
    output_dir: str      # path con parámetros clave codificados
    error_msg: Optional[str]     # mensaje de error; None si no hubo error

    def to_dict(self) -> dict:
        """Serializa el registro a un dict compatible con JSON."""
        return {
            "job_id": self.job_id,
            "image_name": self.image_name,
            "config": self.config,
            "k_result": self.k_result,
            "status": self.status,
            "started_at": self.started_at,
            "duration_s": self.duration_s,
            "output_dir": self.output_dir,
            "error_msg": self.error_msg,
        }

    @staticmethod
    def from_dict(d: dict) -> "ExecutionRecord":
        """Deserializa un dict (leído de JSON) a un ExecutionRecord."""
        return ExecutionRecord(
            job_id=d["job_id"],
            image_name=d["image_name"],
            config=d["config"],
            k_result=d["k_result"],
            status=d["status"],
            started_at=d["started_at"],
            duration_s=d.get("duration_s"),
            output_dir=d["output_dir"],
            error_msg=d.get("error_msg"),
        )


def load_history(history_path: Path) -> list[ExecutionRecord]:
    """
    Lee el historial desde history_path.
    Devuelve lista ordenada por started_at descendente.
    Si el archivo no existe o está corrupto, imprime un warning y devuelve [].
    """
    if not history_path.exists():
        return []

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = [ExecutionRecord.from_dict(entry) for entry in data]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(
            f"WARNING: history.py — no se pudo leer '{history_path}': {exc}",
            file=sys.stderr,
        )
        return []

    # Ordenar por started_at descendente (ISO 8601 es lexicográficamente ordenable)
    records.sort(key=lambda r: r.started_at, reverse=True)
    return records


def save_entry(history_path: Path, record: ExecutionRecord) -> None:
    """
    Añade o actualiza un registro en el historial (identificado por job_id).
    Escritura atómica: escribe en fichero .tmp y renombra.
    Crea el directorio padre si no existe.
    """
    # Asegurar que el directorio padre existe
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # Cargar historial existente
    existing = load_history(history_path)

    # Construir índice por job_id para añadir/actualizar
    records_by_id: dict[str, ExecutionRecord] = {r.job_id: r for r in existing}
    records_by_id[record.job_id] = record

    # Serializar todos los registros
    data = [r.to_dict() for r in records_by_id.values()]

    # Escritura atómica: fichero temporal en el mismo directorio → rename
    tmp_path = history_path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, history_path)
    except Exception:
        # Limpiar el temporal si algo falla
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def get_history(history_path: Path) -> list[ExecutionRecord]:
    """Alias de load_history. Devuelve la lista ordenada por started_at desc."""
    return load_history(history_path)
