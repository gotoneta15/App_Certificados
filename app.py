"""
Aplicación Principal Flask - Sistema de Emisión de Certificados
Punto de entrada de la aplicación web.
"""

import os
from flask import Flask
from controllers.tablero_controller import tablero_bp
from controllers.certificados_controller import certificados_bp


def create_app() -> Flask:
    """
    Fábrica de la aplicación Flask.
    Configura la carpeta de plantillas 'views' y registra los controladores.
    """
    aplicacion = Flask(__name__, template_folder="views")
    aplicacion.secret_key = os.getenv("SECRET_KEY", "academia_certificados_clave_secreta_2026")

    # Registro de Blueprints de la capa de controladores
    aplicacion.register_blueprint(tablero_bp)
    aplicacion.register_blueprint(certificados_bp)

    return aplicacion


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
