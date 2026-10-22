"""
Pruebas automáticas de la aplicación de certificados.

Estas pruebas usan el cliente de pruebas de Flask, que simula un navegador
sin necesidad de levantar el servidor. Las credenciales se definen aquí para
que el resultado no dependa del archivo .env de cada computadora.
"""

import io
import os
import re
from pathlib import Path

import pytest
from openpyxl import load_workbook

# ---------------------------------------------------------------------------
# Credenciales exclusivas de las pruebas. Se escriben ANTES de importar app.py
# para que la fábrica create_app() las use en lugar de las del archivo .env.
# ---------------------------------------------------------------------------
ADMIN_CORREO = "admin.pruebas@academia.cr"
ADMIN_CLAVE = "clave-admin-de-prueba"
USUARIO_CORREO = "usuario.pruebas@academia.cr"
USUARIO_CLAVE = "clave-usuario-de-prueba"

os.environ["ADMIN_CORREO"] = ADMIN_CORREO
os.environ["ADMIN_CLAVE"] = ADMIN_CLAVE
os.environ["USUARIO_CORREO"] = USUARIO_CORREO
os.environ["USUARIO_CLAVE"] = USUARIO_CLAVE
os.environ["SECRET_KEY"] = "clave-secreta-solo-para-pruebas"

from app import create_app  # noqa: E402  (se importa después de definir el entorno)

# Ruta absoluta a los Excel de fábrica, sin depender de la carpeta actual.
RUTA_INSUMOS = Path(__file__).resolve().parent.parent / "INSUMOS"
ID_CAMILA = "101230456"


@pytest.fixture()
def cliente():
    """
    Crea una aplicación nueva y devuelve su cliente de pruebas.
    Cada prueba recibe una sesión limpia, como si fuera un navegador nuevo.
    """
    aplicacion = create_app()
    aplicacion.config.update(TESTING=True)
    return aplicacion.test_client()


def _normalizar_identificacion(valor):
    """
    Convierte la identificación a texto sin espacios ni el sufijo .0 que
    a veces agrega Excel a los números.
    """
    if valor is None:
        return ""

    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto


def _valor_kpi(html, clase_tarjeta):
    """
    Lee el número que muestra una tarjeta del tablero (por ejemplo,
    kpi-aprobacion) usando una búsqueda sencilla en el HTML.
    """
    patron = (
        rf'<div class="kpi-card {clase_tarjeta}">'
        r".*?"
        r'<div class="kpi-value">(\d+)</div>'
    )
    coincidencia = re.search(patron, html, flags=re.DOTALL)

    assert coincidencia, f"No se encontró la tarjeta {clase_tarjeta} en la pantalla."
    return int(coincidencia.group(1))


# ---------------------------------------------------------------------------
# PRUEBAS
# ---------------------------------------------------------------------------


def test_sin_sesion_redirige_a_login(cliente):
    """
    Simula a una persona que abre la página principal sin haber entrado.
    La app debe mandarla a /login en vez de mostrarle datos de estudiantes.
    """
    respuesta = cliente.get("/")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/login")


def test_clave_incorrecta_no_entra(cliente):
    """
    Simula un intento de entrada con el correo correcto pero una clave
    equivocada. Debe quedarse en la pantalla de login con un aviso de error.
    """
    respuesta = cliente.post(
        "/login",
        data={
            "correo": "correo.que.no.existe@academia.cr",
            "clave": "esta-clave-no-es-correcta",
        },
    )
    html = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 200
    assert "Correo o contraseña incorrectos." in html

    # Además de mostrar el error, no debe haber creado una sesión.
    with cliente.session_transaction() as sesion:
        assert "correo" not in sesion


def test_usuario_no_puede_cargar(cliente):
    """
    Simula una sesión ya iniciada con rol "usuario". Aunque conozca la ruta,
    no debe poder entrar a la carga de archivos: la respuesta debe ser 403.
    """
    with cliente.session_transaction() as sesion:
        sesion["correo"] = USUARIO_CORREO
        sesion["rol"] = "usuario"

    respuesta = cliente.get("/cargar")

    assert respuesta.status_code == 403


def test_excel_modificado_cambia_contadores(cliente):
    """
    Simula a un administrador que sube un Registro_Evaluaciones modificado.
    Las cuatro notas de Camila Rojas Méndez se cambian a 40 en una copia en
    memoria, sin tocar el Excel original de INSUMOS. El tablero debe mostrar
    18 aprobaciones, 4 participaciones y 1 sin certificado.
    """
    # Entro como administrador usando las credenciales de prueba.
    respuesta_login = cliente.post(
        "/login",
        data={"correo": ADMIN_CORREO, "clave": ADMIN_CLAVE},
    )
    assert respuesta_login.status_code == 302

    # Leo el maestro original y lo envuelvo en BytesIO para subirlo en memoria.
    maestro = io.BytesIO((RUTA_INSUMOS / "Maestro_Estudiantes.xlsx").read_bytes())

    # Leo las evaluaciones originales en memoria; el archivo del disco no se toca.
    evaluaciones_originales = (
        RUTA_INSUMOS / "Registro_Evaluaciones.xlsx"
    ).read_bytes()
    libro = load_workbook(io.BytesIO(evaluaciones_originales))
    hoja = libro["Evaluaciones"]

    # Busco las columnas por su nombre para no depender del orden exacto.
    encabezados = [celda.value for celda in hoja[1]]
    columna_id = encabezados.index("Identificacion")
    columna_nota = encabezados.index("Nota")

    # Cambio a 40 todas las notas de Camila dentro de esta copia del libro.
    filas_modificadas = 0
    for fila in hoja.iter_rows(min_row=2):
        if _normalizar_identificacion(fila[columna_id].value) == ID_CAMILA:
            fila[columna_nota].value = 40
            filas_modificadas += 1

    assert filas_modificadas > 0, "No se encontraron evaluaciones de Camila."

    # Guardo el libro modificado en otro buffer de memoria para enviarlo.
    evaluaciones_modificadas = io.BytesIO()
    libro.save(evaluaciones_modificadas)
    evaluaciones_modificadas.seek(0)

    # Envío los dos archivos al panel con el botón "Procesar y ver en pantalla".
    respuesta = cliente.post(
        "/cargar",
        data={
            "accion": "ver",
            "archivo_maestro": (maestro, "Maestro_Estudiantes.xlsx"),
            "archivo_evaluaciones": (
                evaluaciones_modificadas,
                "Registro_Evaluaciones.xlsx",
            ),
        },
    )
    html = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 200
    assert _valor_kpi(html, "kpi-aprobacion") == 18
    assert _valor_kpi(html, "kpi-participacion") == 4
    assert _valor_kpi(html, "kpi-sin-certificado") == 1
