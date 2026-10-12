"""
Script de Carga de Datos Inicial
Ejecuta la creación de tablas, la importación de datos desde los archivos Excel
y reporta la cantidad de registros persistidos en Supabase.
"""

import sys
from services.carga_excel import cargar_datos_desde_excel
from models.datos import contar_estudiantes, contar_evaluaciones


def main():
    print("--- Iniciando proceso de carga de datos a Supabase ---")
    try:
        resultado = cargar_datos_desde_excel()
        print(f"Estudiantes procesados del archivo: {resultado['estudiantes_insertados']}")
        print(f"Evaluaciones procesadas del archivo: {resultado['evaluaciones_insertadas']}")

        total_estudiantes = contar_estudiantes()
        total_evaluaciones = contar_evaluaciones()

        print("\n--- Verificación en Base de Datos Supabase ---")
        print(f"Filas en tabla 'estudiantes': {total_estudiantes}")
        print(f"Filas en tabla 'evaluaciones': {total_evaluaciones}")

        if total_estudiantes == 24 and total_evaluaciones == 88:
            print("\n>> CARGA COMPLETADA EXITOSAMENTE: Cifras de control coinciden (24 estudiantes, 88 evaluaciones).")
        else:
            print(f"\n>> ADVERTENCIA: Se esperaban 24 estudiantes y 88 evaluaciones, pero se encontraron {total_estudiantes} y {total_evaluaciones}.")

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un fallo durante la carga de datos: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
