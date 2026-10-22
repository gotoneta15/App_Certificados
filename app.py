"""
Aplicación Principal Flask - Sistema de Emisión de Certificados
Punto de entrada de la aplicación web.
"""

import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, flash, redirect, url_for
from controllers.auth_controller import auth_bp
from controllers.tablero_controller import tablero_bp
from controllers.certificados_controller import certificados_bp

# Carpeta del proyecto: donde está este archivo app.py.
# Así las rutas relativas (INSUMOS/, views/) funcionan
# sin importar desde qué carpeta se arranque la app.
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

# Cargo el archivo .env de la carpeta del proyecto para que estén disponibles
# las credenciales ADMIN_* y USUARIO_* durante el arranque de la aplicación.
load_dotenv(BASE_DIR / ".env")


def create_app() -> Flask:
    """
    Fábrica de la aplicación Flask.
    Configura la carpeta de plantillas 'views' y registra los controladores.
    """
    aplicacion = Flask(__name__, template_folder="views")

    # La clave firmará la cookie de sesión. Se lee del entorno para no dejarla
    # escrita en el repositorio; si no existe, genero una temporal para que la
    # app funcione en local. En Vercel hay que configurar SECRET_KEY para que la
    # sesión se mantenga entre instancias y reinicios.
    aplicacion.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # Vercel rechaza peticiones de más de 4.5 MB. Dejo el límite en 4 MB para
    # tener margen y avisar con un mensaje claro si alguien sube algo más grande.
    aplicacion.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    # Registro de Blueprints de la capa de controladores
    aplicacion.register_blueprint(auth_bp)
    aplicacion.register_blueprint(tablero_bp)
    aplicacion.register_blueprint(certificados_bp)

    @aplicacion.errorhandler(413)
    def archivo_demasiado_grande(error):
        # Cuando Flask corta la petición por tamaño, vuelvo al tablero con aviso.
        flash(
            "La carga supera el límite de 4 MB. Suba archivos más pequeños.",
            "danger",
        )
        return redirect(url_for("tablero.index", _anchor="panel-admin"))

    return aplicacion


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
