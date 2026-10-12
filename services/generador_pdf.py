"""
Capa de Servicio - Generador de Certificados en PDF
Utiliza fpdf2 en orientación horizontal (A4) con la paleta de colores institucional:
Azul marino (#14213D) y Dorado (#B8923D).
"""

import io
from typing import Any, Dict
from fpdf import FPDF
from models.certificados import es_certificable, ESTADO_APROBACION, ESTADO_PARTICIPACION

# Colores institucionales
COLOR_AZUL_MARINO = (20, 33, 61)   # #14213D
COLOR_DORADO = (184, 146, 61)       # #B8923D
COLOR_GRIS_OSCURO = (60, 64, 72)
COLOR_GRIS_CLARO = (120, 125, 135)
COLOR_FONDO_CAJA = (248, 249, 252)


class CertificadoPDF(FPDF):
    """
    Plantilla personalizada para certificados con diseño y márgenes institucionales.
    """

    def dibujar_marcos(self):
        """
        Dibuja los marcos dobles y ornamentos en las esquinas.
        """
        # Marco exterior en Azul Marino (grosor 1.8 mm)
        self.set_draw_color(*COLOR_AZUL_MARINO)
        self.set_line_width(1.8)
        self.rect(8, 8, 281, 194)

        # Marco interior en Dorado (grosor 0.8 mm)
        self.set_draw_color(*COLOR_DORADO)
        self.set_line_width(0.8)
        self.rect(12, 12, 273, 186)

        # Ornamentos en esquinas interiores (cuadros decorativos en dorado)
        self.set_fill_color(*COLOR_DORADO)
        tam = 3.5
        # Esquinas
        self.rect(13, 13, tam, tam, "F")
        self.rect(285 - tam - 1, 13, tam, tam, "F")
        self.rect(13, 198 - tam - 1, tam, tam, "F")
        self.rect(285 - tam - 1, 198 - tam - 1, tam, tam, "F")


def generar_certificado_pdf(datos_estudiante: Dict[str, Any]) -> bytes:
    """
    Genera el certificado en PDF para un estudiante elegible.
    Si el estudiante tiene estado 'Sin certificado' o posee inconsistencias,
    lanza ValueError.

    Retorna los bytes del PDF generado.
    """
    estado = datos_estudiante.get("estado", "")
    tiene_inconsist = datos_estudiante.get("tiene_inconsistencia", False)

    if not es_certificable(estado, tiene_inconsistencia=tiene_inconsist):
        ident = datos_estudiante.get("identificacion", "desconocida")
        nombre = datos_estudiante.get("nombre_completo", "desconocido")
        raise ValueError(
            f"El estudiante '{nombre}' (ID: {ident}) tiene estado '{estado}' "
            f"y no es elegible para emisión de certificado."
        )

    # Inicializar documento A4 Horizontal
    pdf = CertificadoPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # Marco ornamental
    pdf.dibujar_marcos()

    # 1. Encabezado Institucional
    pdf.set_y(18)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(0, 7, "ACADEMIA DE TECNOLOGÍA Y NEGOCIOS", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*COLOR_DORADO)
    pdf.cell(0, 5, "EXCELENCIA Y FORMACIÓN PROFESIONAL CONTINUA", align="C", new_x="LMARGIN", new_y="NEXT")

    # Línea decorativa dorada
    pdf.set_draw_color(*COLOR_DORADO)
    pdf.set_line_width(0.6)
    pdf.line(115, 32, 182, 32)

    # 2. Concesión
    pdf.set_y(36)
    pdf.set_font("Helvetica", "I", 11)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(0, 6, "Otorga el presente", align="C", new_x="LMARGIN", new_y="NEXT")

    # 3. Título Dinámico
    pdf.set_y(44)
    pdf.set_font("Helvetica", "B", 24)
    if estado == ESTADO_APROBACION:
        titulo = "CERTIFICADO DE APROBACIÓN"
        pdf.set_text_color(*COLOR_AZUL_MARINO)
    else:
        titulo = "CERTIFICADO DE PARTICIPACIÓN"
        pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(0, 11, titulo, align="C", new_x="LMARGIN", new_y="NEXT")

    # 4. Destinatario
    pdf.set_y(58)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(0, 5, "A:", align="C", new_x="LMARGIN", new_y="NEXT")

    nombre_completo = str(datos_estudiante.get("nombre_completo", "")).strip().upper()
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*COLOR_DORADO)
    pdf.cell(0, 10, nombre_completo, align="C", new_x="LMARGIN", new_y="NEXT")

    identificacion = str(datos_estudiante.get("identificacion", "")).strip()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_GRIS_OSCURO)
    pdf.cell(0, 5, f"Identificación: {identificacion}", align="C", new_x="LMARGIN", new_y="NEXT")

    # 5. Reconocimiento y Programa
    pdf.set_y(78)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*COLOR_GRIS_OSCURO)
    pdf.cell(
        0,
        6,
        "Por haber completado satisfactoriamente los requisitos académicos del programa:",
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    programa = str(datos_estudiante.get("programa", "")).strip()
    pdf.set_y(86)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(0, 8, programa, align="C", new_x="LMARGIN", new_y="NEXT")

    cohorte = str(datos_estudiante.get("cohorte", "")).strip()
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(0, 6, f"Cohorte: {cohorte}", align="C", new_x="LMARGIN", new_y="NEXT")

    # 6. Indicadores de Desempeño (Cajas elegantes)
    prom_nota = datos_estudiante.get("promedio_nota", 0.0)
    prom_asist = datos_estudiante.get("promedio_asistencia", 0.0)

    y_cajas = 106
    w_caja = 60
    h_caja = 20

    # Caja 1: Promedio de Nota
    x1 = 80
    pdf.set_fill_color(*COLOR_FONDO_CAJA)
    pdf.set_draw_color(*COLOR_DORADO)
    pdf.set_line_width(0.5)
    pdf.rect(x1, y_cajas, w_caja, h_caja, "DF")

    pdf.set_xy(x1, y_cajas + 2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(w_caja, 4, "PROMEDIO DE NOTA", align="C")

    pdf.set_xy(x1, y_cajas + 8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(w_caja, 8, f"{prom_nota:.2f} / 100", align="C")

    # Caja 2: Asistencia
    x2 = 157
    pdf.set_fill_color(*COLOR_FONDO_CAJA)
    pdf.set_draw_color(*COLOR_DORADO)
    pdf.set_line_width(0.5)
    pdf.rect(x2, y_cajas, w_caja, h_caja, "DF")

    pdf.set_xy(x2, y_cajas + 2)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(w_caja, 4, "ASISTENCIA TOTAL", align="C")

    pdf.set_xy(x2, y_cajas + 8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(w_caja, 8, f"{prom_asist:.2f}%", align="C")

    # 7. Firmas institucionales
    y_firmas = 148
    pdf.set_draw_color(*COLOR_AZUL_MARINO)
    pdf.set_line_width(0.6)
    pdf.line(55, y_firmas, 115, y_firmas)
    pdf.line(182, y_firmas, 242, y_firmas)

    pdf.set_xy(45, y_firmas + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(80, 5, "Dirección Académica", align="C")

    pdf.set_xy(45, y_firmas + 7)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(80, 4, "Academia de Formación", align="C")

    pdf.set_xy(172, y_firmas + 2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*COLOR_AZUL_MARINO)
    pdf.cell(80, 5, "Coordinación de Programa", align="C")

    pdf.set_xy(172, y_firmas + 7)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(80, 4, "Registro y Certificaciones", align="C")

    # 8. Pie de página institucional
    pdf.set_y(178)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*COLOR_GRIS_CLARO)
    pdf.cell(
        0,
        4,
        f"Certificado emitido oficialmente por el Sistema de Acreditación de la Academia | ID: {identificacion}",
        align="C",
    )

    return bytes(pdf.output())


def generar_certificado_pdf_io(datos_estudiante: Dict[str, Any]) -> io.BytesIO:
    """
    Genera el certificado y retorna un objeto io.BytesIO listo para enviar
    mediante send_file en Flask.
    """
    pdf_bytes = generar_certificado_pdf(datos_estudiante)
    return io.BytesIO(pdf_bytes)
