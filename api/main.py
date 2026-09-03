"""Servicio de validación de RFC.

Sirve dos cosas desde un solo proceso:

  GET  /              la interfaz (app/index.html)
  POST /api/validar   la validación del RFC

Tenerlo junto es a propósito: Selenium prueba la interfaz que consume esta
misma API, y Locust le mete carga a la API directamente. Las dos herramientas
apuntan al mismo sistema, no a dos copias que podrían divergir.
"""

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

# RFC mexicano: 3 letras para persona moral o 4 para persona física,
# 6 dígitos de fecha (AAMMDD), y 3 caracteres de homoclave.
RFC = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")

APP_DIR = Path(__file__).resolve().parent.parent / "app"

app = FastAPI(title="Validación de RFC")


class Solicitud(BaseModel):
    rfc: str = ""


class Respuesta(BaseModel):
    valido: bool
    mensaje: str


@app.get("/")
def interfaz() -> FileResponse:
    return FileResponse(APP_DIR / "index.html")


@app.post("/api/validar", response_model=Respuesta)
def validar(solicitud: Solicitud) -> Respuesta:
    rfc = solicitud.rfc.strip().upper()

    if not rfc:
        return Respuesta(valido=False, mensaje="El RFC es obligatorio.")

    if not RFC.match(rfc):
        return Respuesta(valido=False, mensaje="El RFC no tiene un formato válido.")

    return Respuesta(valido=True, mensaje=f"RFC válido: {rfc}")
