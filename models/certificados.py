"""
Capa de Modelo - Reglas de Negocio y Certificados
Aplica estrictamente las reglas R1 a R6 estipuladas en AGENTS.md.
"""

from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from models.datos import obtener_estudiantes, obtener_evaluaciones

# Constantes de negocio obligatorias
NOTA_MINIMA = 70.0
ASISTENCIA_MINIMA = 80.0
ASISTENCIA_CRITICA = 50.0

ESTADO_APROBACION = "Aprobación"
ESTADO_PARTICIPACION = "Participación"
ESTADO_SIN_CERTIFICADO = "Sin certificado"
ESTADO_SIN_EVALUACIONES = "Sin evaluaciones"


def calcular_promedios(evaluaciones: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    R2: Calcula promedio de nota y promedio de asistencia_pct,
    redondeados a 2 decimales.
    """
    if not evaluaciones:
        return 0.0, 0.0

    total_notas = sum(float(ev.get("nota", 0.0)) for ev in evaluaciones)
    total_asist = sum(float(ev.get("asistencia_pct", 0.0)) for ev in evaluaciones)
    n = len(evaluaciones)

    promedio_nota = round(total_notas / n, 2)
    promedio_asistencia = round(total_asist / n, 2)
    return promedio_nota, promedio_asistencia


def clasificar_estado(promedio_nota: float, promedio_asistencia: float) -> str:
    """
    Clasifica según las reglas de negocio:
    - R3: Aprobación (promedio >= 70 y asistencia >= 80).
    - R4: Participación (promedio < 70 y asistencia >= 80).
    - R5: Sin certificado (asistencia < 80).
    """
    if promedio_asistencia >= ASISTENCIA_MINIMA:
        if promedio_nota >= NOTA_MINIMA:
            return ESTADO_APROBACION
        else:
            return ESTADO_PARTICIPACION
    else:
        return ESTADO_SIN_CERTIFICADO


def es_certificable(estado: str, tiene_inconsistencia: bool = False) -> bool:
    """
    Determina si un estudiante es elegible para recibir certificado.
    Solo estudiantes con estado 'Aprobación' o 'Participación' y sin inconsistencias
    pueden certificarse.
    """
    if tiene_inconsistencia:
        return False
    return estado in (ESTADO_APROBACION, ESTADO_PARTICIPACION)


def procesar_datos_tablero(
    estudiantes_raw: Optional[List[Dict[str, Any]]] = None,
    evaluaciones_raw: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Orquesta el cálculo completo del tablero aplicando las reglas R1 a R6.
    Retorna el resumen de control, la lista de estudiantes consolidados,
    las inconsistencias y los registros elegibles para emitir certificados.
    """
    if estudiantes_raw is None:
        estudiantes_raw = obtener_estudiantes()
    if evaluaciones_raw is None:
        evaluaciones_raw = obtener_evaluaciones()

    # Mapeo de estudiantes del maestro
    maestro_por_id: Dict[str, Dict[str, Any]] = {}
    for e in estudiantes_raw:
        ident = str(e.get("identificacion", "")).strip()
        if ident:
            maestro_por_id[ident] = e

    # R1: Agrupar evaluaciones por identificacion + programa
    evals_por_clave: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    ids_en_evaluaciones: set[str] = set()
    for ev in evaluaciones_raw:
        ident = str(ev.get("identificacion", "")).strip()
        prog = str(ev.get("programa", "")).strip()
        if ident:
            ids_en_evaluaciones.add(ident)
            evals_por_clave[(ident, prog)].append(ev)

    ids_maestro = set(maestro_por_id.keys())

    # R6: Detección de inconsistencias
    inconsistencias: List[Dict[str, Any]] = []

    # 1. Estudiante del maestro sin evaluaciones
    ids_sin_eval = ids_maestro - ids_en_evaluaciones
    for id_sin in sorted(ids_sin_eval):
        est = maestro_por_id[id_sin]
        inconsistencias.append(
            {
                "tipo": "Sin evaluaciones",
                "identificacion": id_sin,
                "nombre": est.get("nombre_completo", ""),
                "programa": est.get("programa", ""),
                "cohorte": est.get("cohorte", ""),
                "descripcion": "Estudiante registrado en el catálogo maestro sin registros de evaluación.",
                "promedio_nota": None,
                "promedio_asistencia": None,
            }
        )

    # 2. Identificación con evaluaciones que no está en el maestro
    ids_no_maestro = ids_en_evaluaciones - ids_maestro
    for id_no in sorted(ids_no_maestro):
        # Tomar programa y calcular promedios de sus evaluaciones
        evals_huerfanas = [
            ev
            for (i, _), ev_list in evals_por_clave.items()
            if i == id_no
            for ev in ev_list
        ]
        prog_huerfano = (
            evals_huerfanas[0].get("programa", "") if evals_huerfanas else ""
        )
        p_nota, p_asist = (
            calcular_promedios(evals_huerfanas) if evals_huerfanas else (0.0, 0.0)
        )
        inconsistencias.append(
            {
                "tipo": "No registrado en maestro",
                "identificacion": id_no,
                "nombre": "No registrado en maestro",
                "programa": prog_huerfano,
                "cohorte": "N/A",
                "descripcion": f"Identificación {id_no} presenta evaluaciones pero no existe en el catálogo maestro.",
                "promedio_nota": p_nota,
                "promedio_asistencia": p_asist,
            }
        )

    # Procesar estudiantes del maestro con evaluaciones
    estudiantes_consolidados: List[Dict[str, Any]] = []
    certificables: List[Dict[str, Any]] = []

    conteo_aprobacion = 0
    conteo_participacion = 0
    conteo_sin_certificado = 0

    for ident, est in sorted(
        maestro_por_id.items(), key=lambda x: x[1].get("nombre_completo", "")
    ):
        programa = str(est.get("programa", "")).strip()
        evals = evals_por_clave.get((ident, programa), [])

        # Si no tiene evaluaciones bajo su programa exacto, buscar si tiene bajo otro programa
        if not evals:
            evals_alternas = [
                ev
                for (i, _), ev_list in evals_por_clave.items()
                if i == ident
                for ev in ev_list
            ]
            if evals_alternas:
                evals = evals_alternas
                programa = evals[0].get("programa", programa)

        if not evals:
            # Estudiante sin evaluaciones (ya reportado en inconsistencias)
            registro = {
                "identificacion": ident,
                "nombre_completo": est.get("nombre_completo", ""),
                "correo": est.get("correo", ""),
                "programa": est.get("programa", ""),
                "cohorte": est.get("cohorte", ""),
                "promedio_nota": None,
                "promedio_asistencia": None,
                "estado": ESTADO_SIN_EVALUACIONES,
                "es_certificable": False,
                "tiene_inconsistencia": True,
                "motivo_inconsistencia": "Sin registros de evaluación",
            }
            estudiantes_consolidados.append(registro)
            continue

        prom_nota, prom_asist = calcular_promedios(evals)
        estado = clasificar_estado(prom_nota, prom_asist)

        tiene_inconsist = False
        motivo_inconsist = ""

        # 3. Asistencia menor a 50 %
        if prom_asist < ASISTENCIA_CRITICA:
            tiene_inconsist = True
            motivo_inconsist = f"Asistencia menor al 50% ({prom_asist}%)"
            inconsistencias.append(
                {
                    "tipo": "Asistencia crítica (< 50%)",
                    "identificacion": ident,
                    "nombre": est.get("nombre_completo", ""),
                    "programa": programa,
                    "cohorte": est.get("cohorte", ""),
                    "descripcion": f"Asistencia promedio crítica ({prom_asist}%), inferior al 50%.",
                    "promedio_nota": prom_nota,
                    "promedio_asistencia": prom_asist,
                }
            )

        # Conteo según reglas de clasificación
        if estado == ESTADO_APROBACION:
            conteo_aprobacion += 1
        elif estado == ESTADO_PARTICIPACION:
            conteo_participacion += 1
        elif estado == ESTADO_SIN_CERTIFICADO:
            conteo_sin_certificado += 1

        apto = es_certificable(estado, tiene_inconsistencia=tiene_inconsist)

        registro = {
            "identificacion": ident,
            "nombre_completo": est.get("nombre_completo", ""),
            "correo": est.get("correo", ""),
            "programa": programa,
            "cohorte": est.get("cohorte", ""),
            "promedio_nota": prom_nota,
            "promedio_asistencia": prom_asist,
            "estado": estado,
            "es_certificable": apto,
            "tiene_inconsistencia": tiene_inconsist,
            "motivo_inconsistencia": motivo_inconsist,
            "total_evaluaciones": len(evals),
        }

        estudiantes_consolidados.append(registro)
        if apto:
            certificables.append(registro)

    resumen = {
        "aprobacion": conteo_aprobacion,
        "participacion": conteo_participacion,
        "sin_certificado": conteo_sin_certificado,
        "inconsistencias": len(inconsistencias),
        "total_estudiantes": len(estudiantes_raw),
        "total_evaluaciones": len(evaluaciones_raw),
        "total_certificables": len(certificables),
    }

    return {
        "resumen": resumen,
        "estudiantes": estudiantes_consolidados,
        "inconsistencias": inconsistencias,
        "certificables": certificables,
    }


def obtener_estudiante_para_certificado(
    identificacion: str, programa: str
) -> Dict[str, Any]:
    """
    Busca y valida la elegibilidad de un estudiante para emitir su certificado.
    Si el estudiante tiene estado 'Sin certificado' o tiene inconsistencias,
    lanza ValueError.
    """
    datos = procesar_datos_tablero()
    id_buscada = str(identificacion).strip()
    prog_buscado = str(programa).strip().lower()

    estudiante_hallado = None
    for est in datos["estudiantes"]:
        if (
            str(est["identificacion"]).strip() == id_buscada
            and str(est["programa"]).strip().lower() == prog_buscado
        ):
            estudiante_hallado = est
            break

    # Si no coincide exactamente con el programa, buscar por identificación
    if not estudiante_hallado:
        for est in datos["estudiantes"]:
            if str(est["identificacion"]).strip() == id_buscada:
                estudiante_hallado = est
                break

    if not estudiante_hallado:
        raise ValueError(
            f"No se encontró al estudiante con identificación {identificacion} para el programa {programa}."
        )

    if not estudiante_hallado.get("es_certificable"):
        estado = estudiante_hallado.get("estado", "Desconocido")
        motivo = estudiante_hallado.get("motivo_inconsistencia") or "No cumple con las reglas de certificación"
        raise ValueError(
            f"El estudiante {estudiante_hallado.get('nombre_completo')} ({identificacion}) "
            f"tiene estado '{estado}' y no es elegible para certificado. Motivo: {motivo}."
        )

    return estudiante_hallado


def obtener_certificados_validos() -> List[Dict[str, Any]]:
    """
    Retorna la lista de los 22 estudiantes válidos para generación de certificados
    (19 Aprobación + 3 Participación).
    """
    datos = procesar_datos_tablero()
    return datos["certificables"]
