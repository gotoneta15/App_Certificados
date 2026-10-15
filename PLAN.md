# PLAN.md — Plan de implementación por etapas

Academia Horizonte: app web Flask que cruza 2 Excel, aplica reglas R1–R6 y emite certificados PDF.
Orden: primero validar el cruce de datos, luego el backend, al final la interfaz.
Cada etapa se valida antes de seguir. Modo Plan: este archivo es solo el plan, sin código.

## Etapa 1 — Validar el cruce de datos (bodega + reglas)

Qué hacer:
1. Leer `INSUMOS/Maestro_Estudiantes.xlsx` (hoja `Estudiantes`, 24 filas) y `INSUMOS/Registro_Evaluaciones.xlsx` (hoja `Evaluaciones`, 88 filas) con `pandas` + `openpyxl`, identificación como texto (`limpiar_identificacion()`).
2. Agrupar por identificación + programa (R1); promedio = suma de notas / módulos cursados (3 o 4 según programa); asistencia = promedio de `Asistencia_Pct`; redondeo a 2 decimales (R2).
3. Clasificar con límites inclusivos: Aprobación (≥70 y ≥80), Participación (<70 y ≥80), Sin certificado (<80); detectar las 3 inconsistencias R6.
4. Vive en: `services/carga_excel.py` (lectura) + `models/certificados.py` (reglas) + `cargar_datos.py` (script de carga).

Cómo validar antes de seguir:
- `uv run python cargar_datos.py` imprime 24 estudiantes / 88 evaluaciones.
- Resumen: 19 Aprobación, 3 Participación, 1 Sin certificado, 3 inconsistencias (`304560321`, `999880777`, Fernanda Zúñiga 36.25).
- Casos: `101230456` = 91.25/96.25 Aprobación; Luis Acuña = 72.0/81.67 Aprobación.
- Pasa el subagente `tester-datos`. Sin esto en verde, no se sigue.

## Etapa 2 — Backend con Flask (cocina)

Qué hacer (toda la lógica aquí, nunca en la interfaz):
1. `models/datos.py`: único acceso a BD (Supabase si `DATABASE_URL` responde, si no SQLite `academia.db`).
2. `services/generador_pdf.py`: PDF A4 horizontal con `fpdf2`, colores `#14213D`/`#B8923D`; rechaza no-certificables.
3. `controllers/`: rutas `/` (tablero), `/cargar` (GET formulario + POST con los 2 archivos), `/certificado/<id>/<programa>` (400 si no elegible), `/descargar-todos` (ZIP de 22 PDFs). Sin cálculos ni SQL en controladores.
4. `app.py`: fábrica `create_app()`, puerto 5000.

Cómo validar antes de seguir:
- `uv run python app.py` arranca sin errores; `/` responde, `/?format=json` devuelve el resumen.
- PDF individual de un Aprobación descarga bien; el de Fernanda Zúñiga devuelve 400; `/descargar-todos` trae ZIP con 22 PDFs.
- Pasan `tester-datos` (datos) y `revisor` (MVC + sin secretos).

## Etapa 3 — Interfaz (salón, solo muestra)

Qué hacer:
1. `views/base.html`, `views/tablero.html` (resumen, tabla de estudiantes, alertas de inconsistencias), `views/cargar.html` (formulario de los 2 Excel).
2. Estilo azul marino `#14213D` y dorado `#B8923D`. Las plantillas no calculan: solo muestran lo que les pasa el controlador.

Cómo validar (cierre del proyecto):
- Flujo completo a mano: abrir `/`, subir los Excel en `/cargar`, ver el tablero con 19/3/1/3, descargar un PDF y el ZIP.
- Pasan `tester-datos` y `revisor`. Recién ahí la app está terminada.
