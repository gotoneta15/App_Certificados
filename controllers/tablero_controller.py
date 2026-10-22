"""
Controlador del Tablero Principal
Orquesta la consulta de datos para la vista del tablero y la carga de archivos
Excel. No realiza cálculos de negocio: delega en los modelos y servicios.
"""

import io
from datetime import datetime

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from jinja2.exceptions import TemplateNotFound

from controllers.auth_controller import requiere_login, solo_admin
from models.certificados import procesar_datos_tablero
from services.carga_excel import leer_datos_excel
from services.generador_excel import generar_excel_resultados

tablero_bp = Blueprint("tablero", __name__)

# Límite por archivo y textos que se muestran en los avisos.
MAX_ARCHIVO_BYTES = 4 * 1024 * 1024
EXTENSIONES_EXCEL = (".xlsx", ".xls")
ORIGEN_FABRICA = "Datos de fábrica (carpeta INSUMOS)"
MIMETYPE_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class ErrorCarga(Exception):
    """
    Error controlado de la carga: falta un archivo, no es Excel o pesa demasiado.
    Se muestra directamente al usuario porque su mensaje está en español.
    """


def _datos_de_fabrica():
    """
    Lee los Excel oficiales de INSUMOS y calcula el tablero sin tocar la BD.
    """
    estudiantes, evaluaciones = leer_datos_excel()
    return procesar_datos_tablero(
        estudiantes_raw=estudiantes,
        evaluaciones_raw=evaluaciones,
    )


def _render_tablero(datos, origen_datos, datos_subidos=False):
    """
    Renderiza el tablero con los datos calculados y el origen que se muestra
    en el panel de administrador.
    """
    return render_template(
        "tablero.html",
        resumen=datos["resumen"],
        estudiantes=datos["estudiantes"],
        inconsistencias=datos["inconsistencias"],
        certificables=datos["certificables"],
        origen_datos=origen_datos,
        datos_subidos=datos_subidos,
    )


def _descargar_excel(datos, origen_datos):
    """
    Genera el Excel de resultados en memoria y lo envía como descarga.
    """
    buffer = generar_excel_resultados(datos, origen_datos)
    nombre = datetime.now().strftime("Resultados_%Y%m%d_%H%M%S.xlsx")
    return send_file(
        buffer,
        mimetype=MIMETYPE_EXCEL,
        as_attachment=True,
        download_name=nombre,
    )


def _preparar_archivo(archivo, etiqueta):
    """
    Valida un archivo subido y lo convierte en un buffer de memoria (BytesIO).
    Devuelve el buffer y el nombre original del archivo.
    """
    nombre = (archivo.filename or "").strip()

    # VALIDACIÓN: debe existir un archivo y tener extensión de Excel.
    if not nombre:
        raise ErrorCarga(f"Falta el archivo de {etiqueta}.")

    if not nombre.lower().endswith(EXTENSIONES_EXCEL):
        raise ErrorCarga(
            f"El archivo «{nombre}» no es un Excel válido. Use un archivo .xlsx o .xls."
        )

    # Leo el contenido en memoria. No se guarda nada en el disco.
    contenido = archivo.read()

    if not contenido:
        raise ErrorCarga(f"El archivo «{nombre}» está vacío.")

    if len(contenido) > MAX_ARCHIVO_BYTES:
        raise ErrorCarga(
            f"El archivo «{nombre}» pesa más de 4 MB. "
            "Reduzca su tamaño antes de volver a intentarlo."
        )

    # BytesIO es como una caja de archivo dentro de la memoria RAM: guarda los
    # bytes igual que una carpeta guarda hojas, pero sin tocar el disco. Así
    # pandas puede leer el Excel subido y luego la caja se descarta.
    return io.BytesIO(contenido), nombre


@tablero_bp.route("/", methods=["GET"])
@requiere_login
def index():
    """
    Ruta principal: muestra el tablero con los datos de fábrica de INSUMOS.
    El panel para subir archivos aparece solo si el rol es administrador.
    """
    datos = _datos_de_fabrica()

    # Si se solicita formato JSON explícitamente
    if request.args.get("format") == "json" or request.is_json:
        return jsonify(datos)

    try:
        return _render_tablero(datos, ORIGEN_FABRICA)
    except TemplateNotFound:
        # Respaldo por si la plantilla del tablero todavía no existe.
        return jsonify(
            {
                "mensaje": "Vista HTML en proceso de diseño. Retornando datos del tablero en formato JSON.",
                **datos,
            }
        )


@tablero_bp.route("/cargar", methods=["GET", "POST"])
@requiere_login
@solo_admin
def cargar():
    """
    GET: redirige al panel del tablero. Con accion=excel descarga los datos de
    fábrica.
    POST: procesa los dos Excel subidos, los mantiene en memoria y muestra el
    tablero recalculado o descarga un Excel con los resultados.
    """
    if request.method == "GET":
        # Enlace "descargar resultados de fábrica".
        if request.args.get("accion") == "excel":
            return _descargar_excel(_datos_de_fabrica(), ORIGEN_FABRICA)

        # El formulario de carga vive en la página principal.
        return redirect(url_for("tablero.index", _anchor="panel-admin"))

    # ------------------------- POST: carga de archivos -------------------------
    accion = request.form.get("accion", "ver")
    archivo_maestro = request.files.get("archivo_maestro")
    archivo_evaluaciones = request.files.get("archivo_evaluaciones")

    # VALIDACIÓN: para el panel se necesitan los dos archivos.
    if (
        not archivo_maestro
        or not archivo_maestro.filename
        or not archivo_evaluaciones
        or not archivo_evaluaciones.filename
    ):
        flash(
            "Debe seleccionar los dos archivos: el Maestro de estudiantes y el "
            "Registro de evaluaciones.",
            "danger",
        )
        return redirect(url_for("tablero.index", _anchor="panel-admin"))

    try:
        buffer_maestro, nombre_maestro = _preparar_archivo(
            archivo_maestro, "Maestro de estudiantes"
        )
        buffer_evaluaciones, nombre_evaluaciones = _preparar_archivo(
            archivo_evaluaciones, "Registro de evaluaciones"
        )

        # Reutilizo la lectura existente y las reglas de negocio del modelo.
        estudiantes, evaluaciones = leer_datos_excel(
            buffer_maestro, buffer_evaluaciones
        )
        datos = procesar_datos_tablero(
            estudiantes_raw=estudiantes,
            evaluaciones_raw=evaluaciones,
        )
    except ErrorCarga as error:
        flash(str(error), "danger")
        return redirect(url_for("tablero.index", _anchor="panel-admin"))
    except Exception:
        flash(
            "No se pudieron leer los Excel. Verifique que sean archivos válidos y "
            "que tengan las hojas «Estudiantes» y «Evaluaciones» con sus columnas.",
            "danger",
        )
        return redirect(url_for("tablero.index", _anchor="panel-admin"))

    origen_datos = f"Archivos subidos: {nombre_maestro} y {nombre_evaluaciones}"

    # Un botón muestra el tablero; el otro descarga el Excel de resultados.
    if accion == "excel":
        return _descargar_excel(datos, origen_datos)

    return _render_tablero(datos, origen_datos, datos_subidos=True)
