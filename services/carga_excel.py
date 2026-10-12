"""
Capa de Servicio - Carga y Validación de Archivos Excel
Lee los insumos de estudiantes y evaluaciones, valida su formato
y delega la persistencia al módulo models/datos.py.
"""

import os
from typing import Any, Dict, Optional, Union
import pandas as pd
from models.datos import (
    crear_tablas,
    limpiar_tablas,
    insertar_estudiantes,
    insertar_evaluaciones,
)

COLUMNAS_ESTUDIANTES = [
    "Identificacion",
    "Nombre_Completo",
    "Correo",
    "Programa",
    "Cohorte",
]

COLUMNAS_EVALUACIONES = [
    "Identificacion",
    "Programa",
    "Modulo",
    "Nota",
    "Asistencia_Pct",
    "Fecha_Cierre",
]


def limpiar_identificacion(val: Any) -> str:
    """
    Normaliza la identificación como texto limpio sin espacios ni decimales espurios.
    """
    if pd.isna(val):
        return ""
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val)).strip()
        return str(val).strip()
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.strip()


def procesar_excel_estudiantes(origen: Any) -> list[Dict[str, Any]]:
    """
    Lee y valida la hoja 'Estudiantes' del archivo maestro.
    """
    df = pd.read_excel(
        origen,
        sheet_name="Estudiantes",
        dtype={"Identificacion": str},
    )

    columnas_faltantes = [c for c in COLUMNAS_ESTUDIANTES if c not in df.columns]
    if columnas_faltantes:
        raise ValueError(
            f"El archivo de Estudiantes no contiene las columnas requeridas: {columnas_faltantes}"
        )

    estudiantes = []
    for _, row in df.iterrows():
        ident = limpiar_identificacion(row["Identificacion"])
        if not ident:
            continue
        estudiantes.append(
            {
                "identificacion": ident,
                "nombre_completo": (
                    str(row["Nombre_Completo"]).strip()
                    if pd.notna(row["Nombre_Completo"])
                    else ""
                ),
                "correo": (
                    str(row["Correo"]).strip() if pd.notna(row["Correo"]) else ""
                ),
                "programa": (
                    str(row["Programa"]).strip() if pd.notna(row["Programa"]) else ""
                ),
                "cohorte": (
                    str(row["Cohorte"]).strip() if pd.notna(row["Cohorte"]) else ""
                ),
            }
        )
    return estudiantes


def procesar_excel_evaluaciones(origen: Any) -> list[Dict[str, Any]]:
    """
    Lee y valida la hoja 'Evaluaciones' del archivo de evaluaciones.
    """
    df = pd.read_excel(
        origen,
        sheet_name="Evaluaciones",
        dtype={"Identificacion": str},
    )

    columnas_faltantes = [c for c in COLUMNAS_EVALUACIONES if c not in df.columns]
    if columnas_faltantes:
        raise ValueError(
            f"El archivo de Evaluaciones no contiene las columnas requeridas: {columnas_faltantes}"
        )

    evaluaciones = []
    for _, row in df.iterrows():
        ident = limpiar_identificacion(row["Identificacion"])
        if not ident:
            continue

        fecha_cierre = None
        if pd.notna(row["Fecha_Cierre"]):
            try:
                fecha_cierre = pd.to_datetime(row["Fecha_Cierre"]).strftime("%Y-%m-%d")
            except Exception:
                fecha_cierre = str(row["Fecha_Cierre"]).strip()

        evaluaciones.append(
            {
                "identificacion": ident,
                "programa": (
                    str(row["Programa"]).strip() if pd.notna(row["Programa"]) else ""
                ),
                "modulo": (
                    str(row["Modulo"]).strip() if pd.notna(row["Modulo"]) else ""
                ),
                "nota": float(row["Nota"]) if pd.notna(row["Nota"]) else 0.0,
                "asistencia_pct": (
                    float(row["Asistencia_Pct"])
                    if pd.notna(row["Asistencia_Pct"])
                    else 0.0
                ),
                "fecha_cierre": fecha_cierre,
            }
        )
    return evaluaciones


def cargar_datos_desde_excel(
    ruta_maestro: Optional[Union[str, Any]] = None,
    ruta_evaluaciones: Optional[Union[str, Any]] = None,
) -> Dict[str, int]:
    """
    Orquesta la lectura de ambos Excel, la creación de tablas si no existen,
    el vaciado previo de las tablas y la inserción de los nuevos datos.
    """
    if ruta_maestro is None:
        ruta_maestro = os.path.join("insumos", "Maestro_Estudiantes.xlsx")
    if ruta_evaluaciones is None:
        ruta_evaluaciones = os.path.join("insumos", "Registro_Evaluaciones.xlsx")

    # 1. Procesar datos desde los Excel
    lista_estudiantes = procesar_excel_estudiantes(ruta_maestro)
    lista_evaluaciones = procesar_excel_evaluaciones(ruta_evaluaciones)

    # 2. Asegurar tablas y vaciar datos existentes
    crear_tablas()
    limpiar_tablas()

    # 3. Insertar registros por lote
    insertar_estudiantes(lista_estudiantes)
    insertar_evaluaciones(lista_evaluaciones)

    return {
        "estudiantes_insertados": len(lista_estudiantes),
        "evaluaciones_insertadas": len(lista_evaluaciones),
    }
