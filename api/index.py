"""Puerta de entrada para Vercel: expone la app Flask como función serverless."""

import sys
from pathlib import Path

# Agrego la carpeta del proyecto para poder importar app.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402  (la app Flask ya creada en app.py)
