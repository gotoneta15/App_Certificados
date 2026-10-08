# AGENTS.md — APP_CERTIFICADOS

Greenfield repo: no code, no toolchain, no tests yet. Only data inputs exist.

## Inputs (read-only source of truth)

- `INSUMOS/Maestro_Estudiantes.xlsx` — sheet `Estudiantes`, 24 rows + header:
  `Identificacion | Nombre_Completo | Correo | Programa | Cohorte`
- `INSUMOS/Registro_Evaluaciones.xlsx` — sheet `Evaluaciones`, 88 rows + header:
  `Identificacion | Programa | Modulo | Nota | Asistencia_Pct | Fecha_Cierre`
- Never edit files under `INSUMOS/`. Treat them as immutable fixtures.
- Both sheets use inline strings (no `sharedStrings.xml`); parse accordingly.

## Data invariants (verified from the files)

- Join key is `Identificacion` (numeric string). `Programa` must also match.
- Programs: `Técnico en IA Aplicada` (16 students, 4 módulos) and
  `Excel Avanzado para Negocios` (8 students, 3 módulos).
- Module counts differ per program — do not hardcode 4 modules.
- Known edge cases that code must handle explicitly:
  - `999880777` has 4 evaluation rows but NO `Maestro` entry → orphan, never certify; flag it.
  - `304560321` (Espinoza León Javier) is in `Maestro` but has ZERO evaluation rows → no certificate.
  - `111230984` has `Nota = 0` rows (abandono) → no certificate.
- Text contains Spanish accents (`Técnico`, `Módulo`); keep everything UTF-8, preserve accents in outputs.

## Environment gotchas

- Windows host with NO Python/Node installed (only Store stubs) and NO git repo as of 2026-09-30.
  Verify with `Get-Command python, node` before assuming a runtime; document any runtime you introduce.
- When scaffolding the app, add: `README.md` (run/build/test commands), `.gitignore` (outputs, `__pycache__`, `node_modules`),
  and keep generated certificates out of git — write them to `SALIDA/` (create on demand).

## Idioma y Comunicación

- Responder y comunicarse SIEMPRE en español.
- Explicaciones claras, sencillas y didácticas, orientadas a principiantes.

