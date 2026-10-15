# AGENTS.md — App de Certificados de Academia Horizonte

Academia Horizonte (formación técnica a empresas): al cerrar cada cohorte emite un certificado por estudiante. Hoy es manual en Excel/Word; se automatiza como app web Flask (sin IA, solo reglas fijas R1–R6).

## Stack y comandos (usar `uv`, nunca `pip`)

- Python 3.12 (`requires-python = ">=3.12"` en `pyproject.toml`). Deps: `flask, pandas, openpyxl, fpdf2, psycopg[binary], python-dotenv`.
- Cargar/verificar datos: `uv run python cargar_datos.py` → debe imprimir 24 estudiantes / 88 evaluaciones.
- Arrancar: `uv run python app.py` → puerto 5000. Fábrica `create_app()` en `app.py`; `template_folder="views"`.
- No hay suite de tests ni CI. La verificación es: cifras de control del tablero (abajo) + revisión de subagentes.
- Decisiones (detalle y orden de construcción en `PLAN.md`): `pandas` + `openpyxl` para Excel (agrupados y promedios en pocas líneas; solo `openpyxl` obligaría a programarlos a mano); `Flask` para la web (4 rutas + Jinja incluido; `Django` sobra y `FastAPI` trata el HTML como segunda clase); `fpdf2` para PDF (sin dependencias externas).

## Datos y BD (fuente de errores más común)

- Carpeta real en disco: `INSUMOS/` (mayúsculas, "bodega", NO se modifica): `Maestro_Estudiantes.xlsx` (hoja `Estudiantes`, 24 filas, lista oficial), `Registro_Evaluaciones.xlsx` (hoja `Evaluaciones`, 88 filas, `Nota` 0–100 y asistencia por módulo). El código acepta `insumos/` o `INSUMOS/`, pero el default de `services/carga_excel.py` es `insumos/` en minúsculas.
- `Identificacion` siempre es texto sin espacios: usar `limpiar_identificacion()` de `services/carga_excel.py` (maneja floats y sufijo `.0`). Nunca comparar como número.
- BD dual en `models/datos.py` (único archivo que toca la BD):
  - Si `DATABASE_URL` (de `.env`, vía `python-dotenv`) responde → Supabase/PostgreSQL con `psycopg.connect(..., prepare_threshold=None)` (obligatorio por el pooler PgBouncer/Supavisor).
  - Si no → fallback local SQLite `academia.db`, auto-creado y auto-poblado desde los Excel (`_inicializar_sqlite_si_vacio`). Por eso la app arranca aunque no haya `.env`.
- Esquema: `estudiantes(identificacion TEXT PK, nombre_completo, correo, programa, cohorte)`; `evaluaciones(id autoincremental, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre)`.

## Reglas de negocio (`models/certificados.py`, no duplicarlas en otro lado)

- Constantes: `NOTA_MINIMA = 70`, `ASISTENCIA_MINIMA = 80`, `ASISTENCIA_CRITICA = 50` (límites inclusivos).
- R1: agrupar por `identificacion + programa` (un certificado por estudiante y programa). R2: promedio = suma de `nota` / cantidad de módulos; asistencia = promedio de `asistencia_pct`; redondeo a 2 decimales.
- R3 Aprobación: nota ≥ 70 y asistencia ≥ 80. R4 Participación: nota < 70 y asistencia ≥ 80. R5 Sin certificado: asistencia < 80.
- R6 inconsistencias (no certificables, van como alerta): maestro sin evaluaciones; id con evaluaciones fuera del maestro; asistencia promedio < 50.
- Solo `Aprobación` y `Participación` sin inconsistencia son certificables (`es_certificable()`).

## Cifras de control (la entrega solo vale si salen)

- Resumen: 19 Aprobación, 3 Participación, 1 Sin certificado, 3 inconsistencias.
- Inconsistencias: `304560321` (Javier Espinoza, sin evaluaciones), `999880777` (no está en el maestro), Fernanda Zúñiga (asistencia 36.25).
- Casos: Camila Rojas Méndez `101230456` = 91.25 / 96.25 Aprobación; Luis Acuña Blanco = 72.0 / 81.67 Aprobación.

## Arquitectura MVC (la audita el subagente revisor)

Metáfora del dueño: bodega = datos, cocina = backend (toda la lógica aquí, nunca en la interfaz), salón = frontend (solo muestra, no calcula ni decide).

- `models/datos.py`: único acceso a BD. `models/certificados.py`: lógica pura (`procesar_datos_tablero()`, `obtener_estudiante_para_certificado()`, `obtener_certificados_validos()`).
- `services/carga_excel.py`: lee/valida Excel y persiste vía `models/datos.py`. `services/generador_pdf.py`: PDF con `fpdf2`, A4 horizontal, colores `#14213D` / `#B8923D`; rechaza no-certificables con `ValueError`.
- `controllers/`: solo rutas, sin cálculos ni SQL. `tablero_controller`: `/` (acepta `?format=json`; cae a JSON si falta la plantilla), `/cargar` (GET formulario, POST con `archivo_maestro`+`archivo_evaluaciones` o recarga desde Excel local). `certificados_controller`: `/certificado/<id>` y `/certificado/<id>/<programa>` (400 si no elegible, PDF inline salvo `?descargar=1`), `/descargar-todos` (ZIP de 22 PDFs).
- `views/` (Jinja): `base.html`, `tablero.html`, `cargar.html`. Solo presentación.

## Restricciones

- Nunca modificar `INSUMOS/`. Nunca leer ni mostrar `.env` (está en `.gitignore`); secretos solo por `os.getenv`, jamás hardcodeados.
- Responder en español sencillo (usuario principiante). Código simple y comentado en español, señalando variables, tipos, condicionales, bucles y funciones. Antes de construir, mostrar plan corto y esperar aprobación. Trabajar por entregas pequeñas indicando archivos y capa (models/services/controllers/views).
- Al cerrar cada entrega: pasar el subagente `tester-datos` (solo verifica, no edita) y luego el subagente `revisor` (solo lectura, audita MVC y secretos). Subagentes disponibles en `.agents/agents/`: `backend-flask`, `disenador-vistas`, `tester-datos`, `revisor`.
