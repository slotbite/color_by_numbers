#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web_app.py — Interfaz Streamlit para el generador Color-by-Numbers.

Estructura:
  load_env_config()        -> dict
  scan_images(input_dir)   -> list[Path]
  results_exist(output_dir)-> bool
  render_config_panel(env) -> tuple[Optional[Path], dict]
  render_jobs_panel(queue, history_path) -> None
  render_history_panel(history_path)     -> None
  render_comparison_panel(history_path)  -> None
  main()
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Funciones puras (importables sin streamlit) ────────────────────────────────

from config_schema import (
    PARAM_SCHEMA,
    COLOR_PROFILES,
    SUPPORTED_EXTENSIONS,
    default_config,
    apply_color_profile,
    validate_config,
    build_args,
)
from history import ExecutionRecord, get_history, save_entry
from job_runner import Job, JobQueue


def load_env_config() -> dict:
    """
    Lee variables de entorno y devuelve un dict con la configuración del entorno.
    Valores por defecto si no están definidas.
    """
    return {
        "SAM_CHECKPOINT_PATH": os.environ.get(
            "SAM_CHECKPOINT_PATH", "./sam_vit_b_01ec64.pth"
        ),
        "INPUT_DIR": os.environ.get("INPUT_DIR", "./in"),
        "OUTPUT_DIR": os.environ.get("OUTPUT_DIR", "./res"),
        "PORT": os.environ.get("PORT", "8501"),
    }


def scan_images(input_dir: Path) -> list:
    """
    Escanea input_dir en busca de archivos con SUPPORTED_EXTENSIONS.
    Filtra case-insensitive y ordena alfabéticamente por nombre.
    """
    if not input_dir.exists() or not input_dir.is_dir():
        return []
    files = [
        f
        for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files, key=lambda p: p.name.lower())


def results_exist(output_dir: str) -> bool:
    """
    Devuelve True si los 3 archivos PNG de resultado existen en output_dir.
    """
    base = Path(output_dir)
    return (
        (base / "01_outline_numbered.png").exists()
        and (base / "02_colored_reference.png").exists()
        and (base / "03_palette.png").exists()
    )


def _job_to_record(job: Job) -> ExecutionRecord:
    """Convierte un Job completado a ExecutionRecord para guardar en el historial."""
    started_iso = (
        datetime.fromtimestamp(job.started_at, tz=timezone.utc).isoformat()
        if job.started_at
        else datetime.now(tz=timezone.utc).isoformat()
    )
    duration = (
        job.finished_at - job.started_at
        if job.started_at and job.finished_at
        else None
    )
    image_name = Path(job.image_path).name if job.image_path else ""
    error_msg = None
    if job.status == "error":
        # Últimas 5 líneas del log como mensaje de error
        lines = job.log.strip().splitlines()
        error_msg = "\n".join(lines[-5:]) if lines else "Error desconocido"

    return ExecutionRecord(
        job_id=job.job_id,
        image_name=image_name,
        config=dict(job.config),
        k_result=job.k_result,
        status=job.status,
        started_at=started_iso,
        duration_s=duration,
        output_dir=job.output_dir,
        error_msg=error_msg,
    )


def _snap_to_step(value: float, vmin: float, vmax: float, step: float) -> float:
    """Redondea value al múltiplo de step más cercano desde vmin, dentro de [vmin, vmax]."""
    import math
    snapped = round(round((value - vmin) / step) * step + vmin, 10)
    return max(vmin, min(vmax, snapped))


def _enqueue_job(env: dict, image_path: Path, config: dict, queue) -> str:
    """Crea un Job y lo encola. Devuelve el job_id."""
    import streamlit as st
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_stem = image_path.stem
    job_id = f"{ts}_{image_stem}"

    args = build_args(
        image_path=str(image_path),
        output_dir="",
        checkpoint=env["SAM_CHECKPOINT_PATH"],
        config=config,
    )

    job = Job(
        job_id=job_id,
        image_path=str(image_path),
        image_stem=image_stem,
        args=args,
        config=dict(config),
        output_base=Path(env["OUTPUT_DIR"]),
    )

    queue.enqueue(job)
    st.success(f"✅ Ejecución `{job_id}` encolada.")
    return job_id

def render_config_panel(env: dict):
    """
    Renderiza el Panel_Configuración en el sidebar.
    Devuelve (imagen_seleccionada: Optional[Path], config: dict).
    """
    import streamlit as st

    default_input_dir = Path(env["INPUT_DIR"])

    with st.sidebar:
        st.markdown("## 🎨 Configuración")

        # ── Selector de carpeta + subida de archivos ────────────────────────
        st.markdown("**📁 Imágenes de entrada**")

        # Campo de texto para cambiar la carpeta
        folder_path_str = st.text_input(
            "Carpeta",
            value=str(st.session_state.get("input_dir_override", default_input_dir)),
            key="input_dir_text",
            placeholder="Ej: C:/mis_imagenes o ./in",
            help="Escribe la ruta de cualquier carpeta con imágenes",
        )
        input_dir = Path(folder_path_str)
        st.session_state["input_dir_override"] = input_dir

        # Subida directa de archivos (alternativa al campo de carpeta)
        with st.expander("⬆️ O sube imágenes directamente", expanded=False):
            uploaded = st.file_uploader(
                "Arrastra o selecciona imágenes",
                type=["jpg", "jpeg", "png", "webp", "bmp"],
                accept_multiple_files=True,
                key="uploaded_images",
            )
            if uploaded:
                # Guardar los archivos subidos en la carpeta de entrada por defecto
                default_input_dir.mkdir(parents=True, exist_ok=True)
                for uf in uploaded:
                    dest = default_input_dir / uf.name
                    dest.write_bytes(uf.read())
                st.success(f"✅ {len(uploaded)} imagen(es) guardada(s) en `{default_input_dir}`")
                # Apuntar la carpeta activa a donde se guardaron
                input_dir = default_input_dir
                st.session_state["input_dir_override"] = input_dir

        # Escanear la carpeta activa
        images = scan_images(input_dir)

        # ── Selector de imagen ──────────────────────────────────────────────
        selected_image: Optional[Path] = None
        if not images:
            st.warning(f"No se encontraron imágenes en `{input_dir}`.")
        else:
            image_names = [img.name for img in images]
            selected_name = st.selectbox(
                f"{len(images)} imagen(es) disponible(s)",
                options=image_names,
                key="selected_image_name",
            )
            selected_image = input_dir / selected_name
            # Vista previa miniatura
            try:
                st.image(str(selected_image), width=200, caption=selected_name)
            except Exception:
                st.caption(f"Vista previa no disponible: {selected_name}")

        st.divider()

        # ── Selector de perfil de color ─────────────────────────────────────
        profile_labels = [p["label"] for p in COLOR_PROFILES]
        profile_keys = [p["key"] for p in COLOR_PROFILES]

        current_profile = st.session_state.config.get("color_profile", "manual")
        current_idx = profile_keys.index(current_profile) if current_profile in profile_keys else len(profile_keys) - 1

        selected_profile_label = st.selectbox(
            "🎨 Perfil de color",
            options=profile_labels,
            index=current_idx,
            key="color_profile_selector",
        )
        selected_profile_key = profile_keys[profile_labels.index(selected_profile_label)]

        # Aplicar perfil si cambió
        if selected_profile_key != st.session_state.config.get("color_profile"):
            st.session_state.config = apply_color_profile(
                st.session_state.config, selected_profile_key
            )

        # Mostrar descripción del perfil
        profile_obj = next((p for p in COLOR_PROFILES if p["key"] == selected_profile_key), None)
        if profile_obj:
            st.caption(profile_obj["description"])

        st.divider()

        # ── Controles por categoría ─────────────────────────────────────────
        config = dict(st.session_state.config)

        # Agrupar parámetros por categoría (excluir color_profile, ya manejado arriba)
        categories: dict[str, list] = {}
        for param in PARAM_SCHEMA:
            if param["key"] == "color_profile":
                continue
            cat = param.get("category", "General")
            categories.setdefault(cat, []).append(param)

        for cat_name, params in categories.items():
            with st.expander(f"⚙️ {cat_name}", expanded=False):
                for param in params:
                    key = param["key"]
                    label = param["label"]
                    desc = param.get("description", "")
                    ptype = param["type"]
                    choices = param.get("choices")
                    vmin = param.get("min")
                    vmax = param.get("max")
                    current_val = config.get(key, param["default"])

                    if ptype is bool:
                        config[key] = st.checkbox(label, value=bool(current_val), key=f"param_{key}")
                    elif choices is not None:
                        idx = choices.index(current_val) if current_val in choices else 0
                        config[key] = st.selectbox(label, options=choices, index=idx, key=f"param_{key}")
                    elif ptype is int and vmin is not None and vmax is not None:
                        config[key] = st.slider(
                            label,
                            min_value=int(vmin),
                            max_value=int(vmax),
                            value=int(current_val),
                            step=1,
                            key=f"param_{key}",
                        )
                    elif ptype is float and vmin is not None and vmax is not None:
                        step = 0.01
                        safe_val = _snap_to_step(float(current_val), float(vmin), float(vmax), step)
                        config[key] = st.slider(
                            label,
                            min_value=float(vmin),
                            max_value=float(vmax),
                            value=safe_val,
                            step=step,
                            key=f"param_{key}",
                        )
                    else:
                        config[key] = st.text_input(label, value=str(current_val), key=f"param_{key}")

                    if desc:
                        st.caption(desc)

        st.divider()

        # ── Botón de lanzamiento ────────────────────────────────────────────
        launch = st.button("🚀 Lanzar ejecución", use_container_width=True, type="primary")
        if launch:
            st.session_state["launch_clicked"] = True
            st.session_state.config = config

    return selected_image, config


def render_jobs_panel(queue: JobQueue, history_path: Path) -> None:
    """Renderiza la lista de ejecuciones activas con estado, log y resultados."""
    import streamlit as st

    st.subheader("⚙️ Ejecuciones activas")

    jobs = list(reversed(queue.get_jobs()))  # más reciente primero

    if not jobs:
        st.info("No hay ejecuciones en cola. Lanza una desde el panel de configuración.")
        return

    for job in jobs:
        status = job.status
        status_colors = {
            "pending": "#6b7280",
            "running": "#3b82f6",
            "completed": "#22c55e",
            "error": "#ef4444",
        }
        status_labels = {
            "pending": "⏳ Pendiente",
            "running": "🔄 En ejecución",
            "completed": "✅ Completado",
            "error": "❌ Error",
        }
        color = status_colors.get(status, "#6b7280")
        label = status_labels.get(status, status)

        badge_html = (
            f'<span style="display:inline-block;padding:0.2rem 0.6rem;'
            f'border-radius:9999px;font-size:0.75rem;font-weight:600;'
            f'background-color:{color}22;color:{color};'
            f'border:1px solid {color}66;">{label}</span>'
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{job.job_id}** &nbsp; {badge_html}", unsafe_allow_html=True)
        with col2:
            if job.started_at and job.finished_at:
                duration = job.finished_at - job.started_at
                st.caption(f"⏱ {duration:.1f}s")
            elif job.started_at:
                elapsed = time.time() - job.started_at
                st.caption(f"⏱ {elapsed:.0f}s…")

        with st.expander(f"📋 Log — {job.job_id}", expanded=(status == "error")):
            if job.log:
                st.code(job.log, language=None)
            else:
                st.caption("Sin salida aún.")

        # Resultados si completado
        if status == "completed" and job.output_dir and results_exist(job.output_dir):
            out = Path(job.output_dir)
            img_col1, img_col2, img_col3 = st.columns(3)
            with img_col1:
                st.image(str(out / "01_outline_numbered.png"), caption="Outline numerado")
            with img_col2:
                st.image(str(out / "02_colored_reference.png"), caption="Referencia coloreada")
            with img_col3:
                st.image(str(out / "03_palette.png"), caption="Paleta")

            dl_col1, dl_col2 = st.columns(2)
            pdf_path = out / "color_by_numbers_kit.pdf"
            csv_path = out / "palette.csv"
            with dl_col1:
                if pdf_path.exists():
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "📥 Descargar PDF",
                            data=f.read(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            key=f"dl_pdf_{job.job_id}",
                        )
            with dl_col2:
                if csv_path.exists():
                    with open(csv_path, "rb") as f:
                        st.download_button(
                            "📥 Descargar CSV",
                            data=f.read(),
                            file_name=csv_path.name,
                            mime="text/csv",
                            key=f"dl_csv_{job.job_id}",
                        )

        # Mostrar últimas líneas del log en rojo si hay error
        if status == "error" and job.log:
            lines = job.log.strip().splitlines()
            last_lines = "\n".join(lines[-10:])
            st.markdown(
                f'<div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.4);'
                f'border-radius:8px;padding:0.75rem;color:#ef4444;font-family:monospace;'
                f'font-size:0.8rem;white-space:pre-wrap;">{last_lines}</div>',
                unsafe_allow_html=True,
            )

        st.divider()


def render_history_panel(history_path: Path) -> None:
    """Renderiza el Panel_Historial con las últimas 20 ejecuciones."""
    import streamlit as st

    st.subheader("📋 Historial")

    records = get_history(history_path)[:20]

    if not records:
        st.info("No hay ejecuciones en el historial todavía.")
        return

    for record in records:
        with st.expander(f"🗂 {record.job_id} — {record.image_name}", expanded=False):
            meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
            with meta_col1:
                st.metric("Imagen", record.image_name)
            with meta_col2:
                st.metric("Perfil", record.config.get("color_profile", "—"))
            with meta_col3:
                st.metric("K resultado", record.k_result)
            with meta_col4:
                dur = f"{record.duration_s:.1f}s" if record.duration_s else "—"
                st.metric("Duración", dur)

            st.caption(f"Estado: **{record.status}** | Inicio: {record.started_at}")

            with st.expander("⚙️ Configuración completa", expanded=False):
                st.json(record.config)

            if record.output_dir and results_exist(record.output_dir):
                out = Path(record.output_dir)
                img_col1, img_col2, img_col3 = st.columns(3)
                with img_col1:
                    st.image(str(out / "01_outline_numbered.png"), caption="Outline numerado")
                with img_col2:
                    st.image(str(out / "02_colored_reference.png"), caption="Referencia coloreada")
                with img_col3:
                    st.image(str(out / "03_palette.png"), caption="Paleta")

                # ── Botones de descarga ─────────────────────────────────────
                dl_col1, dl_col2, dl_col3, dl_col4, dl_col5 = st.columns(5)
                pdf_path = out / "color_by_numbers_kit.pdf"
                csv_path = out / "palette.csv"
                outline_path = out / "01_outline_numbered.png"
                ref_path     = out / "02_colored_reference.png"
                palette_path = out / "03_palette.png"

                with dl_col1:
                    if pdf_path.exists():
                        st.download_button(
                            "📥 PDF",
                            data=pdf_path.read_bytes(),
                            file_name=pdf_path.name,
                            mime="application/pdf",
                            key=f"hist_dl_pdf_{record.job_id}",
                            use_container_width=True,
                        )
                with dl_col2:
                    if csv_path.exists():
                        st.download_button(
                            "📥 CSV paleta",
                            data=csv_path.read_bytes(),
                            file_name=csv_path.name,
                            mime="text/csv",
                            key=f"hist_dl_csv_{record.job_id}",
                            use_container_width=True,
                        )
                with dl_col3:
                    if outline_path.exists():
                        st.download_button(
                            "📥 Outline",
                            data=outline_path.read_bytes(),
                            file_name=f"{record.job_id}_outline.png",
                            mime="image/png",
                            key=f"hist_dl_outline_{record.job_id}",
                            use_container_width=True,
                        )
                with dl_col4:
                    if ref_path.exists():
                        st.download_button(
                            "📥 Referencia",
                            data=ref_path.read_bytes(),
                            file_name=f"{record.job_id}_referencia.png",
                            mime="image/png",
                            key=f"hist_dl_ref_{record.job_id}",
                            use_container_width=True,
                        )
                with dl_col5:
                    if palette_path.exists():
                        st.download_button(
                            "📥 Paleta",
                            data=palette_path.read_bytes(),
                            file_name=f"{record.job_id}_paleta.png",
                            mime="image/png",
                            key=f"hist_dl_palette_{record.job_id}",
                            use_container_width=True,
                        )

            if st.button("↩️ Reutilizar config", key=f"reuse_{record.job_id}"):
                # Guardar en estado pendiente — se aplicará al inicio del próximo ciclo
                # antes de que los widgets se instancien (ver main())
                st.session_state["pending_config"] = dict(record.config)
                st.rerun()

            if st.button("▶️ Ejecutar esta config", key=f"run_{record.job_id}", type="primary"):
                st.session_state["direct_run"] = {
                    "config": dict(record.config),
                    "image_name": record.image_name,
                }
                st.rerun()

def render_comparison_panel(history_path: Path) -> None:
    """Renderiza el Panel_Comparación con dos ejecuciones del historial."""
    import streamlit as st

    st.subheader("🔍 Comparar ejecuciones")

    records = get_history(history_path)

    if len(records) < 2:
        st.info("Necesitas al menos 2 ejecuciones en el historial para comparar.")
        return

    job_ids = [r.job_id for r in records]

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        id_a = st.selectbox("Ejecución A", options=job_ids, index=0, key="compare_a")
    with col_sel2:
        id_b = st.selectbox("Ejecución B", options=job_ids, index=min(1, len(job_ids) - 1), key="compare_b")

    record_a = next((r for r in records if r.job_id == id_a), None)
    record_b = next((r for r in records if r.job_id == id_b), None)

    if not record_a or not record_b:
        st.error("No se encontraron los registros seleccionados.")
        return

    col_a, col_b = st.columns(2)

    for col, record, label in [(col_a, record_a, "A"), (col_b, record_b, "B")]:
        with col:
            st.markdown(f"### Ejecución {label}: `{record.job_id}`")
            st.caption(f"Imagen: **{record.image_name}** | Perfil: **{record.config.get('color_profile', '—')}**")
            st.caption(f"K resultado: **{record.k_result}** | Estado: **{record.status}**")
            if record.duration_s:
                st.caption(f"Duración: **{record.duration_s:.1f}s**")

            if record.output_dir and results_exist(record.output_dir):
                out = Path(record.output_dir)
                st.image(str(out / "01_outline_numbered.png"), caption="Outline numerado", use_container_width=True)
                st.image(str(out / "02_colored_reference.png"), caption="Referencia coloreada", use_container_width=True)
                st.image(str(out / "03_palette.png"), caption="Paleta", use_container_width=True)
            else:
                st.warning("Resultados no disponibles para esta ejecución.")

            with st.expander("⚙️ Config", expanded=False):
                st.json(record.config)


def main():
    import streamlit as st

    st.set_page_config(
        layout="wide",
        page_title="🎨 Color by Numbers",
        page_icon="🎨",
    )

    # ── Inyectar CSS ────────────────────────────────────────────────────────
    css_path = Path(__file__).parent / "styles.css"
    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # ── Inicializar session_state ───────────────────────────────────────────
    env = load_env_config()
    history_path = Path(env["OUTPUT_DIR"]) / "history.json"

    if "job_queue" not in st.session_state:
        st.session_state.job_queue = JobQueue(
            on_complete=lambda job: save_entry(history_path, _job_to_record(job))
        )
    if "config" not in st.session_state:
        st.session_state.config = default_config()

    # ── Aplicar config pendiente (de "Reutilizar config") ──────────────────
    # Debe ejecutarse ANTES de que cualquier widget se instancie en este ciclo.
    # Borramos las keys param_<key> para que los widgets lean el nuevo valor
    # de st.session_state.config en lugar del valor anterior.
    if "pending_config" in st.session_state:
        new_cfg = st.session_state.pop("pending_config")
        st.session_state.config = new_cfg
        # Borrar las keys de widgets para forzar re-inicialización con nuevos valores
        for param in PARAM_SCHEMA:
            st.session_state.pop(f"param_{param['key']}", None)
        st.session_state.pop("color_profile_selector", None)

    # ── Aviso si checkpoint no existe ──────────────────────────────────────
    if not Path(env["SAM_CHECKPOINT_PATH"]).exists():
        st.warning(
            f"⚠️ Checkpoint SAM no encontrado en `{env['SAM_CHECKPOINT_PATH']}`. "
            "Las ejecuciones fallarán."
        )

    # ── Tabs principales ────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["⚙️ Ejecutar", "📋 Historial", "🔍 Comparar"])

    with tab1:
        selected_image, config = render_config_panel(env)

        if st.session_state.pop("launch_clicked", False):
            errors = validate_config(config)
            if not selected_image:
                st.error("Selecciona una imagen antes de lanzar.")
            elif errors:
                for e in errors:
                    st.error(e)
            else:
                _enqueue_job(env, selected_image, config, st.session_state.job_queue)

        # ── Lanzamiento directo desde historial ─────────────────────────────
        direct = st.session_state.pop("direct_run", None)
        if direct:
            input_dir = Path(env["INPUT_DIR"])
            image_path = input_dir / direct["image_name"]
            if not image_path.exists():
                st.error(f"La imagen `{direct['image_name']}` ya no existe en `{input_dir}`.")
            else:
                errors = validate_config(direct["config"])
                if errors:
                    st.error("La config del historial tiene parámetros inválidos:")
                    for e in errors:
                        st.error(e)
                else:
                    _enqueue_job(env, image_path, direct["config"], st.session_state.job_queue)
                    st.success(f"▶️ Ejecutando `{direct['image_name']}` con config del historial.")

        render_jobs_panel(st.session_state.job_queue, history_path)

    with tab2:
        render_history_panel(history_path)

    with tab3:
        render_comparison_panel(history_path)

    # ── Auto-refresco si hay jobs activos ───────────────────────────────────
    if st.session_state.job_queue.active_count() > 0:
        time.sleep(3)
        st.rerun()


if __name__ == "__main__":
    main()
