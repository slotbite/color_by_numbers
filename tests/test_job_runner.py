#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_job_runner.py — Tests para job_runner.py (Fase 3 del spec web-ui).
"""

import threading
import time
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from job_runner import Job, JobQueue, MAX_WORKERS


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_job(job_id: str = "test_job_001", tmp_path: Path = None) -> Job:
    """Crea un Job mínimo para tests."""
    base = tmp_path or Path(".")
    return Job(
        job_id=job_id,
        image_path="in/test.jpg",
        image_stem="test",
        args=["python", "app.py", "--input", "in/test.jpg"],
        config={
            "auto_k": True,
            "k_max": 24,
            "k_min": 12,
            "colors": 12,
            "color_profile": "manual",
            "edge_deltaE": 3.5,
            "sam_pps": 32,
            "slic_n": 4000,
        },
        output_base=base,
    )


def _make_mock_popen(returncode: int = 0, stdout_lines: list[str] = None):
    """
    Crea un mock de subprocess.Popen que devuelve stdout vacío (o las líneas dadas)
    y el returncode configurado.
    """
    lines = stdout_lines or []
    mock_proc = MagicMock()
    mock_proc.stdout = iter(lines)
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = returncode
    return mock_proc


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_job_initial_status_pending(tmp_path):
    """Un Job recién creado tiene status 'pending'."""
    job = _make_job(tmp_path=tmp_path)
    assert job.status == "pending"


def test_enqueue_returns_job_id(tmp_path):
    """enqueue devuelve el job_id del job."""
    completed_event = threading.Event()

    def on_complete(job):
        completed_event.set()

    queue = JobQueue(on_complete=on_complete)
    job = _make_job(job_id="my_unique_id", tmp_path=tmp_path)

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _make_mock_popen(returncode=0)
        returned_id = queue.enqueue(job)
        completed_event.wait(timeout=5)

    queue.shutdown()
    assert returned_id == "my_unique_id"


def test_job_completes_successfully(tmp_path):
    """Mock subprocess returncode=0 → job.status == 'completed'."""
    completed_event = threading.Event()

    def on_complete(job):
        completed_event.set()

    queue = JobQueue(on_complete=on_complete)
    job = _make_job(tmp_path=tmp_path)

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _make_mock_popen(returncode=0)
        queue.enqueue(job)
        completed_event.wait(timeout=5)

    queue.shutdown()
    assert job.status == "completed"
    assert job.returncode == 0


def test_job_fails_on_error(tmp_path):
    """Mock subprocess returncode=1 → job.status == 'error'."""
    completed_event = threading.Event()

    def on_complete(job):
        completed_event.set()

    queue = JobQueue(on_complete=on_complete)
    job = _make_job(tmp_path=tmp_path)

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _make_mock_popen(returncode=1)
        queue.enqueue(job)
        completed_event.wait(timeout=5)

    queue.shutdown()
    assert job.status == "error"
    assert job.returncode == 1


def test_max_3_workers_simultaneous(tmp_path):
    """
    Encola 5 jobs con subprocess mockeado que duerme 0.2s.
    Verifica que active_count nunca supera MAX_WORKERS (3).
    """
    max_seen = 0
    lock = threading.Lock()
    completed_count = [0]
    all_done = threading.Event()
    n_jobs = 5

    def on_complete(job):
        with lock:
            completed_count[0] += 1
            if completed_count[0] == n_jobs:
                all_done.set()

    def slow_popen(*args, **kwargs):
        """Simula un proceso que tarda 0.2s."""
        time.sleep(0.2)
        return _make_mock_popen(returncode=0)

    queue = JobQueue(on_complete=on_complete)

    # Monitorear active_count en un thread separado
    stop_monitor = threading.Event()

    def monitor():
        nonlocal max_seen
        while not stop_monitor.is_set():
            count = queue.active_count()
            with lock:
                if count > max_seen:
                    max_seen = count
            time.sleep(0.01)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()

    with patch("subprocess.Popen", side_effect=slow_popen):
        for i in range(n_jobs):
            job = _make_job(job_id=f"job_{i:03d}", tmp_path=tmp_path)
            queue.enqueue(job)

        all_done.wait(timeout=10)

    stop_monitor.set()
    monitor_thread.join(timeout=2)
    queue.shutdown()

    assert max_seen <= MAX_WORKERS, (
        f"active_count llegó a {max_seen}, pero MAX_WORKERS={MAX_WORKERS}"
    )


def test_on_complete_called(tmp_path):
    """Verifica que el callback on_complete se invoca al terminar."""
    called_jobs = []
    completed_event = threading.Event()

    def on_complete(job):
        called_jobs.append(job)
        completed_event.set()

    queue = JobQueue(on_complete=on_complete)
    job = _make_job(tmp_path=tmp_path)

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _make_mock_popen(returncode=0)
        queue.enqueue(job)
        completed_event.wait(timeout=5)

    queue.shutdown()
    assert len(called_jobs) == 1
    assert called_jobs[0].job_id == job.job_id
