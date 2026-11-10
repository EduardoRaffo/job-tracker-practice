🇬🇧 [Read in English](README.md)

# Job Tracker API

API REST para llevar el seguimiento de candidaturas de empleo: guardas cada oferta, cambias su estado (guardada, aplicada, entrevista...) y consultas el historial. Proyecto de práctica para repasar FastAPI, SQLite y testing con pytest.

## Tecnologías

- Python 3.10+
- [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- Pydantic v2 (validación de datos)
- SQLite (módulo estándar `sqlite3`, consultas parametrizadas)
- pytest + httpx (tests)

## Instalación

```powershell
git clone https://github.com/EduardoRaffo/job-tracker-practice.git
cd job-tracker-practice
python -m venv .venv
.venv\Scripts\Activate.ps1      # en Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Documentación interactiva (Swagger UI): http://127.0.0.1:8000/docs

La base de datos `tracker.db` se crea sola en la carpeta de ejecución la primera vez que se hace una petición.

## Endpoints

| Método | Ruta | Descripción | Respuestas |
|--------|------|-------------|------------|
| GET | `/health` | Comprueba que la API está viva | 200 |
| POST | `/applications` | Crea una candidatura | 201 / 422 |
| GET | `/applications` | Lista todas las candidaturas (lista vacía si no hay ninguna) | 200 |
| GET | `/applications/{id}` | Devuelve una candidatura | 200 / 404 |
| PATCH | `/applications/{id}` | Actualiza solo los campos enviados | 200 / 404 / 422 |
| DELETE | `/applications/{id}` | Elimina una candidatura | 204 / 404 |

### Ejemplo

```bash
curl -X POST http://127.0.0.1:8000/applications \
  -H "Content-Type: application/json" \
  -d '{"company": "Acme", "position": "Junior Python", "status": "applied"}'
```

```json
{
  "company": "Acme",
  "position": "Junior Python",
  "status": "applied",
  "id": 1
}
```

## Modelo de datos

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | entero | Autogenerado, no se reutiliza al borrar |
| `company` | texto | Obligatorio, de 1 a 120 caracteres |
| `position` | texto | Obligatorio, de 1 a 120 caracteres |
| `status` | enum | `saved` (por defecto), `applied`, `interview`, `offer`, `rejected` |

## Tests

```bash
pytest -q
```

Los tests sustituyen la dependencia `get_db` por una base de datos SQLite temporal (`dependency_overrides` + `tmp_path`), así que nunca tocan `tracker.db`. Cubren los seis endpoints, incluidos los casos de error (404, validación) y el PATCH con cuerpo vacío.

## Qué he aprendido

- Diseñar una API REST con FastAPI: rutas, códigos de estado y modelos Pydantic para validar entradas y salidas.
- Persistencia con SQLite y consultas parametrizadas, con una conexión por petición mediante inyección de dependencias (`Depends`).
- Actualizaciones parciales con PATCH (`model_dump(exclude_unset=True)`).
- Leer tracebacks y depurar errores 422 y 500.
- Escribir tests aislados con pytest, fixtures y `dependency_overrides`.

## Licencia

[MIT](LICENSE)
