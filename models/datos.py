"""
Capa de Modelo - Acceso a Datos
Módulo que interactúa con la base de datos Supabase (PostgreSQL) usando psycopg.
Cuando Supabase o DATABASE_URL no están disponibles, provee soporte local transparente
utilizando SQLite (academia.db) para persistencia relacional local completa.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

RUTA_SQLITE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "academia.db")


def get_connection():
    """
    Obtiene una conexión a la base de datos Supabase usando DATABASE_URL.
    Se utiliza prepare_threshold=None debido al pooler de Supabase (PgBouncer/Supavisor).
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL no está configurada en las variables de entorno (.env)."
        )
    return psycopg.connect(database_url, prepare_threshold=None)


def conexion_supabase_disponible() -> bool:
    """
    Comprueba de forma rápida si Supabase responde y tiene credenciales válidas.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False
    try:
        with psycopg.connect(
            database_url, prepare_threshold=None, connect_timeout=3
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return True
    except Exception:
        return False


def get_sqlite_connection() -> sqlite3.Connection:
    """
    Obtiene una conexión a la base de datos local SQLite.
    """
    conn = sqlite3.connect(RUTA_SQLITE)
    conn.row_factory = sqlite3.Row
    return conn


def _buscar_archivo_insumos(nombre_archivo: str) -> str:
    """
    Localiza un archivo dentro de la carpeta insumos o INSUMOS.
    """
    for carpeta in ["insumos", "INSUMOS"]:
        ruta = os.path.join(carpeta, nombre_archivo)
        if os.path.exists(ruta):
            return ruta
    return os.path.join("insumos", nombre_archivo)


def _inicializar_sqlite_si_vacio() -> None:
    """
    Crea las tablas en SQLite y, si no existen registros, carga los datos iniciales
    desde los archivos Excel en insumos/.
    """
    crear_tablas_sqlite()
    with get_sqlite_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM estudiantes;")
        conteo_est = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM evaluaciones;")
        conteo_eval = cur.fetchone()[0]

    if conteo_est == 0 or conteo_eval == 0:
        try:
            from services.carga_excel import (
                procesar_excel_estudiantes,
                procesar_excel_evaluaciones,
            )

            ruta_maestro = _buscar_archivo_insumos("Maestro_Estudiantes.xlsx")
            ruta_eval = _buscar_archivo_insumos("Registro_Evaluaciones.xlsx")

            if os.path.exists(ruta_maestro) and os.path.exists(ruta_eval):
                estudiantes = procesar_excel_estudiantes(ruta_maestro)
                evaluaciones = procesar_excel_evaluaciones(ruta_eval)
                insertar_estudiantes_sqlite(estudiantes)
                insertar_evaluaciones_sqlite(evaluaciones)
        except Exception:
            pass


def crear_tablas_sqlite() -> None:
    """
    Crea las tablas de estudiantes y evaluaciones en SQLite.
    """
    sql_est = """
    CREATE TABLE IF NOT EXISTS estudiantes (
        identificacion TEXT PRIMARY KEY,
        nombre_completo TEXT,
        correo TEXT,
        programa TEXT,
        cohorte TEXT
    );
    """
    sql_eval = """
    CREATE TABLE IF NOT EXISTS evaluaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identificacion TEXT,
        programa TEXT,
        modulo TEXT,
        nota REAL,
        asistencia_pct REAL,
        fecha_cierre TEXT
    );
    """
    with get_sqlite_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql_est)
        cur.execute(sql_eval)
        conn.commit()


def crear_tablas() -> None:
    """
    Crea las tablas de estudiantes y evaluaciones en Supabase o en SQLite local.
    """
    if not conexion_supabase_disponible():
        crear_tablas_sqlite()
        _inicializar_sqlite_si_vacio()
        return

    sql_estudiantes = """
    CREATE TABLE IF NOT EXISTS estudiantes (
        identificacion TEXT PRIMARY KEY,
        nombre_completo TEXT,
        correo TEXT,
        programa TEXT,
        cohorte TEXT
    );
    """

    sql_evaluaciones = """
    CREATE TABLE IF NOT EXISTS evaluaciones (
        id SERIAL PRIMARY KEY,
        identificacion TEXT,
        programa TEXT,
        modulo TEXT,
        nota NUMERIC,
        asistencia_pct NUMERIC,
        fecha_cierre DATE
    );
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_estudiantes)
            cur.execute(sql_evaluaciones)
        conn.commit()


def limpiar_tablas() -> None:
    """
    Vacía las tablas evaluaciones y estudiantes para permitir recargas limpias.
    """
    if not conexion_supabase_disponible():
        crear_tablas_sqlite()
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM evaluaciones;")
            cur.execute("DELETE FROM estudiantes;")
            try:
                cur.execute("DELETE FROM sqlite_sequence WHERE name='evaluaciones';")
            except Exception:
                pass
            conn.commit()
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE evaluaciones RESTART IDENTITY;")
            cur.execute("TRUNCATE TABLE estudiantes;")
        conn.commit()


def insertar_estudiantes_sqlite(estudiantes: List[Dict[str, Any]]) -> None:
    """
    Inserta por lote una lista de diccionarios de estudiantes en SQLite.
    """
    if not estudiantes:
        return
    crear_tablas_sqlite()
    sql = """
    INSERT INTO estudiantes (identificacion, nombre_completo, correo, programa, cohorte)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(identificacion) DO UPDATE SET
        nombre_completo = excluded.nombre_completo,
        correo = excluded.correo,
        programa = excluded.programa,
        cohorte = excluded.cohorte;
    """
    datos = [
        (
            str(e["identificacion"]).strip(),
            e.get("nombre_completo", ""),
            e.get("correo", ""),
            e.get("programa", ""),
            e.get("cohorte", ""),
        )
        for e in estudiantes
    ]
    with get_sqlite_connection() as conn:
        cur = conn.cursor()
        cur.executemany(sql, datos)
        conn.commit()


def insertar_evaluaciones_sqlite(evaluaciones: List[Dict[str, Any]]) -> None:
    """
    Inserta por lote una lista de diccionarios de evaluaciones en SQLite.
    """
    if not evaluaciones:
        return
    crear_tablas_sqlite()
    sql = """
    INSERT INTO evaluaciones (identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    datos = [
        (
            str(ev["identificacion"]).strip(),
            ev.get("programa", ""),
            ev.get("modulo", ""),
            float(ev.get("nota", 0.0)),
            float(ev.get("asistencia_pct", 0.0)),
            str(ev.get("fecha_cierre") or ""),
        )
        for ev in evaluaciones
    ]
    with get_sqlite_connection() as conn:
        cur = conn.cursor()
        cur.executemany(sql, datos)
        conn.commit()


def insertar_estudiantes(estudiantes: List[Dict[str, Any]]) -> None:
    """
    Inserta por lote una lista de diccionarios de estudiantes en Supabase o SQLite.
    """
    if not estudiantes:
        return

    if not conexion_supabase_disponible():
        insertar_estudiantes_sqlite(estudiantes)
        return

    sql = """
    INSERT INTO estudiantes (identificacion, nombre_completo, correo, programa, cohorte)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (identificacion) DO UPDATE SET
        nombre_completo = EXCLUDED.nombre_completo,
        correo = EXCLUDED.correo,
        programa = EXCLUDED.programa,
        cohorte = EXCLUDED.cohorte;
    """

    datos = [
        (
            str(e["identificacion"]).strip(),
            e.get("nombre_completo"),
            e.get("correo"),
            e.get("programa"),
            e.get("cohorte"),
        )
        for e in estudiantes
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, datos)
        conn.commit()


def insertar_evaluaciones(evaluaciones: List[Dict[str, Any]]) -> None:
    """
    Inserta por lote una lista de diccionarios de evaluaciones en Supabase o SQLite.
    """
    if not evaluaciones:
        return

    if not conexion_supabase_disponible():
        insertar_evaluaciones_sqlite(evaluaciones)
        return

    sql = """
    INSERT INTO evaluaciones (identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre)
    VALUES (%s, %s, %s, %s, %s, %s);
    """

    datos = [
        (
            str(ev["identificacion"]).strip(),
            ev.get("programa"),
            ev.get("modulo"),
            ev.get("nota"),
            ev.get("asistencia_pct"),
            ev.get("fecha_cierre"),
        )
        for ev in evaluaciones
    ]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, datos)
        conn.commit()


def contar_estudiantes() -> int:
    """
    Retorna la cantidad de registros en la tabla estudiantes.
    """
    if not conexion_supabase_disponible():
        _inicializar_sqlite_si_vacio()
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM estudiantes;")
            res = cur.fetchone()
            return int(res[0]) if res else 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM estudiantes;")
            resultado = cur.fetchone()
            return int(resultado[0]) if resultado else 0


def contar_evaluaciones() -> int:
    """
    Retorna la cantidad de registros en la tabla evaluaciones.
    """
    if not conexion_supabase_disponible():
        _inicializar_sqlite_si_vacio()
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM evaluaciones;")
            res = cur.fetchone()
            return int(res[0]) if res else 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM evaluaciones;")
            resultado = cur.fetchone()
            return int(resultado[0]) if resultado else 0


def obtener_estudiantes() -> List[Dict[str, Any]]:
    """
    Obtiene todos los estudiantes registrados.
    """
    if not conexion_supabase_disponible():
        _inicializar_sqlite_si_vacio()
        sql = """
        SELECT identificacion, nombre_completo, correo, programa, cohorte
        FROM estudiantes
        ORDER BY nombre_completo ASC;
        """
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    sql = """
    SELECT identificacion, nombre_completo, correo, programa, cohorte
    FROM estudiantes
    ORDER BY nombre_completo ASC;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()


def obtener_evaluaciones() -> List[Dict[str, Any]]:
    """
    Obtiene todas las evaluaciones registradas.
    """
    if not conexion_supabase_disponible():
        _inicializar_sqlite_si_vacio()
        sql = """
        SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
        FROM evaluaciones
        ORDER BY identificacion ASC, modulo ASC;
        """
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    sql = """
    SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
    FROM evaluaciones
    ORDER BY identificacion ASC, modulo ASC;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql)
            return cur.fetchall()


def obtener_estudiante_por_id(identificacion: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene un estudiante específico por su identificación.
    """
    id_limpia = str(identificacion).strip()
    if not conexion_supabase_disponible():
        _inicializar_sqlite_si_vacio()
        sql = """
        SELECT identificacion, nombre_completo, correo, programa, cohorte
        FROM estudiantes
        WHERE identificacion = ?;
        """
        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, (id_limpia,))
            row = cur.fetchone()
            return dict(row) if row else None

    sql = """
    SELECT identificacion, nombre_completo, correo, programa, cohorte
    FROM estudiantes
    WHERE identificacion = %s;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, (id_limpia,))
            return cur.fetchone()


def obtener_evaluaciones_por_estudiante(
    identificacion: str, programa: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Obtiene las evaluaciones de un estudiante, opcionalmente filtrando por programa.
    """
    id_limpia = str(identificacion).strip()
    if not conexion_supabase_disponible():
        _inicializar_sqlite_si_vacio()
        if programa:
            sql = """
            SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
            FROM evaluaciones
            WHERE identificacion = ? AND programa = ?
            ORDER BY modulo ASC;
            """
            params = (id_limpia, programa)
        else:
            sql = """
            SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
            FROM evaluaciones
            WHERE identificacion = ?
            ORDER BY modulo ASC;
            """
            params = (id_limpia,)

        with get_sqlite_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    if programa:
        sql = """
        SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
        FROM evaluaciones
        WHERE identificacion = %s AND programa = %s
        ORDER BY modulo ASC;
        """
        params = (id_limpia, programa)
    else:
        sql = """
        SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
        FROM evaluaciones
        WHERE identificacion = %s
        ORDER BY modulo ASC;
        """
        params = (id_limpia,)

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
