#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
job_runner.py — Cola de ejecuciones con ThreadPoolExecutor para web-ui.
"""

import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

MAX_WORKERS = 3


@dataclass
class Job:
    """Representa una ejecución del generador Color-by-Numbers."""

    job_id: str
    image_path: str
    image_stem: str
    args: list[str]                    # argumentos para subprocess
    config: dict                       # copia de la configuración
    output_base: Path                  # directorio base de resultados
    status: str = "pending"            # "pending" | "running" | "completed" | "error"
    log: str = ""                      # stdout capturado
    returncode: Optional[int] = None
    started_at: Optional[float] = None  # time.time()
    finished_at: Optional[float] = None
    output_dir: str = ""               # path final con parámetros codificados
    k_result: int = 0                  # número de colores real (extraído del log)


class JobQueue:
    """
    Cola de ejecuciones con ThreadPoolExecutor(max_workers=3).
    Thread-safe: usa threading.Lock para acceso a _jobs.
    """

    def __init__(self, on_complete: Callable[[Job], None]):
        """
        on_complete: callback invocado cuando un job termina (éxito o error).
        Se llama desde el thread del worker, no desde el thread principal.
        """
        self.on_complete = on_complete
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        self._jobs: list[Job] = []
        self._lock = threading.Lock()

    def enqueue(self, job: Job) -> str:
        """
        Añade job a la cola y lo envía al executor.
        Devuelve job.job_id.
        """
        with self._lock:
            self._jobs.append(job)
        self._executor.submit(self._run_job, job)
        return job.job_id

    def _run_job(self, job: Job) -> None:
        """Ejecuta el job en un thread del pool."""
        from config_schema import make_output_dir

        # Estimar k para el nombre del directorio inicial
        if job.config.get("auto_k"):
            k_estimate = job.config.get("k_max", 24)
        else:
            k_estimate = job.config.get("colors", 12)

        # Crear directorio de salida con la estimación inicial
        output_dir = make_output_dir(
            job.output_base,
            job.image_stem,
            job.config,
            k_estimate,
            datetime.now(),
        )

        # Actualizar args para incluir --out con el path real
        # Reemplazar el placeholder --out si ya existe, o añadirlo
        args = list(job.args)
        if "--out" in args:
            idx = args.index("--out")
            args[idx + 1] = str(output_dir)
        else:
            args += ["--out", str(output_dir)]

        job.args = args
        job.status = "running"
        job.started_at = time.time()
        job.output_dir = str(output_dir)

        # Ejecutar subprocess con UTF-8 forzado en Windows
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        try:
            proc = subprocess.Popen(
                job.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            # Leer stdout línea a línea
            k_result = 0
            log_lines = []
            for line in proc.stdout:
                log_lines.append(line)
                # Extraer k_result del patrón "🎯 Auto-K → N"
                m = re.search(r"Auto-K\s*→\s*(\d+)", line)
                if m:
                    k_result = int(m.group(1))

            proc.wait()
            job.log = "".join(log_lines)
            job.returncode = proc.returncode
            job.k_result = k_result

        except Exception as exc:
            job.log += f"\n[job_runner error] {exc}"
            job.returncode = -1
            k_result = 0

        # Si k_result real difiere del estimado, renombrar el directorio
        if k_result != 0 and k_result != k_estimate:
            try:
                new_output_dir = make_output_dir(
                    job.output_base,
                    job.image_stem,
                    job.config,
                    k_result,
                    datetime.fromtimestamp(job.started_at),
                )
                # Solo renombrar si el nuevo path es diferente
                if new_output_dir != output_dir and output_dir.exists():
                    output_dir.rename(new_output_dir)
                    job.output_dir = str(new_output_dir)
            except Exception:
                # Si el renombrado falla, mantener el nombre original
                pass

        job.finished_at = time.time()
        job.status = "completed" if job.returncode == 0 else "error"

        self.on_complete(job)

    def get_jobs(self) -> list[Job]:
        """Devuelve copia de la lista de todos los jobs (cualquier estado)."""
        with self._lock:
            return list(self._jobs)

    def active_count(self) -> int:
        """Número de jobs con status == 'running'."""
        with self._lock:
            return sum(1 for j in self._jobs if j.status == "running")

    def shutdown(self) -> None:
        """Espera a que terminen los workers activos y cierra el executor."""
        self._executor.shutdown(wait=True)
