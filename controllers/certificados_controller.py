"""
Controlador de Certificados
Gestiona la emisión y descarga individual y masiva de certificados en PDF y ZIP.
No realiza cálculos de negocio directamente: delega en los modelos y servicios.
"""

import io
import zipfile
import re
from flask import Blueprint, abort, jsonify, send_file, request, flash, redirect, url_for
from models.certificados import (
    obtener_estudiante_para_certificado,
    obtener_certificados_validos,
)
from services.generador_pdf import generar_certificado_pdf

certificados_bp = Blueprint("certificados", __name__)


def _limpiar_nombre_archivo(cadena: str) -> str:
    """
    Sanitiza una cadena para su uso seguro como nombre de archivo.
    """
    cadena_limpia = re.sub(r"[^\w\s-]", "", cadena, flags=re.UNICODE).strip()
    return re.sub(r"[-\s]+", "_", cadena_limpia)


@certificados_bp.route("/certificado/<identificacion>/<path:programa>", methods=["GET"])
@certificados_bp.route("/certificado/<identificacion>", methods=["GET"])
def descargar_certificado(identificacion: str, programa: str = ""):
    """
    Genera y entrega el certificado PDF individual para un estudiante elegible.
    Si el estudiante tiene estado 'Sin certificado' o posee inconsistencias,
    rechaza la solicitud con código HTTP 400.
    """
    try:
        estudiante = obtener_estudiante_para_certificado(identificacion, programa)
    except ValueError as e:
        # Error de elegibilidad o estudiante no encontrado
        return jsonify({"error": str(e), "identificacion": identificacion}), 400

    try:
        pdf_bytes = generar_certificado_pdf(estudiante)
    except Exception as e:
        return jsonify({"error": f"Fallo al generar el PDF: {str(e)}"}), 500

    nombre_archivo = f"Certificado_{identificacion}.pdf"
    as_attachment = request.args.get("descargar", "0") in ("1", "true", "True")

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=as_attachment,
        download_name=nombre_archivo,
    )


@certificados_bp.route("/descargar-todos", methods=["GET"])
def descargar_todos():
    """
    Genera un archivo ZIP en memoria con todos los certificados válidos
    (19 de Aprobación + 3 de Participación = 22 certificados en total)
    y lo envía para descarga directa.
    """
    try:
        estudiantes_validos = obtener_certificados_validos()
        if not estudiantes_validos:
            return jsonify({"error": "No hay certificados elegibles para emitir."}), 404

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for est in estudiantes_validos:
                pdf_bytes = generar_certificado_pdf(est)
                nombre_alumno = _limpiar_nombre_archivo(est.get("nombre_completo", "estudiante"))
                estado = _limpiar_nombre_archivo(est.get("estado", "certificado"))
                ident = str(est.get("identificacion", "")).strip()

                nombre_pdf = f"Certificado_{estado}_{ident}_{nombre_alumno}.pdf"
                zip_file.writestr(nombre_pdf, pdf_bytes)

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="Certificados_Academia.zip",
        )
    except Exception as e:
        return jsonify({"error": f"Error al empaquetar los certificados en ZIP: {str(e)}"}), 500
