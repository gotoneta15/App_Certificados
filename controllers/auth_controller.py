"""
Controlador de Acceso
Gestiona el inicio y cierre de sesión de los dos usuarios definidos por
variables de entorno. No usa base de datos: las credenciales viven en el
entorno y la sesión de Flask guarda únicamente el correo y el rol.
"""

import os
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)

# Valores de demostración: solo se usan cuando faltan las variables de entorno.
# No son credenciales reales; sirven para probar la pantalla sin configurar .env.
DEMO_ADMIN_CORREO = "admin@academia-demo.cr"
DEMO_ADMIN_CLAVE = "admin123"
DEMO_USUARIO_CORREO = "usuario@academia-demo.cr"
DEMO_USUARIO_CLAVE = "usuario123"


def _leer_usuarios():
    """
    Lee las credenciales desde el entorno y arma la lista de usuarios.
    Si falta el correo o la clave de un rol, usa el usuario de demostración
    correspondiente y marca que la pantalla debe mostrar el aviso.
    """
    admin_correo = os.environ.get("ADMIN_CORREO")
    admin_clave = os.environ.get("ADMIN_CLAVE")
    usuario_correo = os.environ.get("USUARIO_CORREO")
    usuario_clave = os.environ.get("USUARIO_CLAVE")

    usuarios = []
    hay_demo = False

    # Usuario administrador
    if admin_correo and admin_clave:
        usuarios.append(
            {
                "correo": admin_correo.strip(),
                "clave": admin_clave,
                "rol": "admin",
                "demo": False,
            }
        )
    else:
        usuarios.append(
            {
                "correo": DEMO_ADMIN_CORREO,
                "clave": DEMO_ADMIN_CLAVE,
                "rol": "admin",
                "demo": True,
            }
        )
        hay_demo = True

    # Usuario normal
    if usuario_correo and usuario_clave:
        usuarios.append(
            {
                "correo": usuario_correo.strip(),
                "clave": usuario_clave,
                "rol": "usuario",
                "demo": False,
            }
        )
    else:
        usuarios.append(
            {
                "correo": DEMO_USUARIO_CORREO,
                "clave": DEMO_USUARIO_CLAVE,
                "rol": "usuario",
                "demo": True,
            }
        )
        hay_demo = True

    return usuarios, hay_demo


def _buscar_usuario(usuarios, correo, clave):
    """
    Busca un usuario comparando el correo sin distinguir mayúsculas.
    Devuelve el diccionario del usuario o None si las credenciales no coinciden.
    """
    correo_normalizado = correo.strip().lower()

    for usuario in usuarios:
        if (
            usuario["correo"].strip().lower() == correo_normalizado
            and usuario["clave"] == clave
        ):
            return usuario

    return None


def requiere_login(vista):
    """
    Decorador de acceso: deja pasar solo si hay una sesión iniciada.
    Si no hay correo guardado en la sesión, redirige a la pantalla de entrada.
    """

    @wraps(vista)
    def envoltura(*args, **kwargs):
        # CONDICIONAL: sin correo en sesión no se muestra ningún dato.
        if not session.get("correo"):
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)

    return envoltura


def solo_admin(vista):
    """
    Decorador de autorización: deja pasar solo si el rol de la sesión es admin.
    Si el rol es distinto, responde con un error 403 y la página de aviso.
    """

    @wraps(vista)
    def envoltura(*args, **kwargs):
        # CONDICIONAL: cualquier rol que no sea "admin" queda bloqueado.
        if session.get("rol") != "admin":
            return render_template("sin_permiso.html"), 403
        return vista(*args, **kwargs)

    return envoltura


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET: muestra el formulario de entrada.
    POST: valida correo y clave; si coinciden, guarda correo y rol en la sesión.
    """
    # Si ya hay una sesión activa, no tiene sentido volver a mostrar el login.
    if request.method == "GET" and session.get("correo"):
        return redirect(url_for("tablero.index"))

    usuarios, modo_demo = _leer_usuarios()
    error = None
    correo_ingresado = ""

    if request.method == "POST":
        correo_ingresado = (request.form.get("correo") or "").strip()
        clave = request.form.get("clave") or ""
        usuario = _buscar_usuario(usuarios, correo_ingresado, clave)

        if usuario:
            # Empiezo una sesión limpia y guardo solo lo necesario para mostrarla.
            session.clear()
            session["correo"] = usuario["correo"]
            session["rol"] = usuario["rol"]
            return redirect(url_for("tablero.index"))

        error = "Correo o contraseña incorrectos."

    # Solo envío a la vista las credenciales de demostración que estén activas.
    usuarios_demo = [usuario for usuario in usuarios if usuario["demo"]]

    return render_template(
        "login.html",
        error=error,
        correo_ingresado=correo_ingresado,
        modo_demo=modo_demo,
        usuarios_demo=usuarios_demo,
    )


@auth_bp.route("/salir")
def salir():
    """
    Borra todos los datos de la sesión y vuelve a la pantalla de entrada.
    """
    session.clear()
    return redirect(url_for("auth.login"))
