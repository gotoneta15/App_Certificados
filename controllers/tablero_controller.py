"""
Controlador del Tablero Principal
Orquesta la consulta de datos para la vista del tablero y la carga de archivos Excel.
No realiza cálculos de negocio directamente: delega en los modelos y servicios.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from jinja2.exceptions import TemplateNotFound
from models.certificados import procesar_datos_tablero
from services.carga_excel import cargar_datos_desde_excel

tablero_bp = Blueprint("tablero", __name__)


@tablero_bp.route("/", methods=["GET"])
def index():
    """
    Ruta principal: muestra el tablero con el resumen de métricas,
    listado de estudiantes consolidados e inconsistencias detectadas.
    """
    datos = procesar_datos_tablero()

    # Si se solicita formato JSON explícitamente
    if request.args.get("format") == "json" or request.is_json:
        return jsonify(datos)

    try:
        return render_template(
            "tablero.html",
            resumen=datos["resumen"],
            estudiantes=datos["estudiantes"],
            inconsistencias=datos["inconsistencias"],
            certificables=datos["certificables"],
        )
    except TemplateNotFound:
        # Fallback si disenador-vistas aún no ha creado tablero.html
        try:
            return render_template(
                "index.html",
                resumen=datos["resumen"],
                estudiantes=datos["estudiantes"],
                inconsistencias=datos["inconsistencias"],
                certificables=datos["certificables"],
            )
        except TemplateNotFound:
            return jsonify(
                {
                    "mensaje": "Vista HTML en proceso de diseño. Retornando datos del tablero en formato JSON.",
                    **datos,
                }
            )


@tablero_bp.route("/cargar", methods=["GET", "POST"])
def cargar():
    """
    Ruta para la carga y actualización de los dos archivos Excel.
    Soporta subida de archivos mediante formulario o recarga desde la carpeta insumos/.
    """
    if request.method == "POST":
        archivo_maestro = request.files.get("archivo_maestro") or request.files.get("archivo_estudiantes")
        archivo_evaluaciones = request.files.get("archivo_evaluaciones")

        try:
            # Si se proporcionan archivos mediante el formulario, utilizarlos
            if (
                archivo_maestro
                and archivo_maestro.filename
                and archivo_evaluaciones
                and archivo_evaluaciones.filename
            ):
                resultado = cargar_datos_desde_excel(
                    ruta_maestro=archivo_maestro,
                    ruta_evaluaciones=archivo_evaluaciones,
                )
            else:
                # Recargar desde los insumos locales por defecto
                resultado = cargar_datos_desde_excel()

            flash(
                f"Datos cargados exitosamente: {resultado.get('estudiantes_insertados', 0)} estudiantes y "
                f"{resultado.get('evaluaciones_insertadas', 0)} evaluaciones.",
                "success",
            )
        except Exception as e:
            flash(f"Error al cargar los datos: {str(e)}", "danger")

        return redirect(url_for("tablero.index"))

    # Petición GET: intentar renderizar la vista de carga
    try:
        return render_template("cargar.html")
    except TemplateNotFound:
        return jsonify(
            {
                "mensaje": "Ruta /cargar disponible. Para recargar datos envíe una petición POST.",
                "metodo": "POST",
                "destino": "/cargar",
            }
        )
