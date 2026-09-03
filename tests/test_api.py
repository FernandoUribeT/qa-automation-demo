"""Pruebas de la API — la base de la pirámide.

Son muchas y baratas: no abren navegador, no levantan servidor. TestClient
llama a la aplicación en memoria, así que cada una corre en milisegundos.

Aquí es donde va la cobertura de casos: todas las variantes de RFC válido e
inválido se prueban a este nivel. Probar cada una de ellas por interfaz
costaría segundos en lugar de milisegundos, y no detectaría nada que estas no
detecten ya.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

cliente = TestClient(app)


def validar(rfc):
    return cliente.post("/api/validar", json={"rfc": rfc}).json()


@pytest.mark.parametrize(
    "rfc",
    [
        "ABC123456XY0",   # persona moral: 3 letras
        "ABCD123456XY0",  # persona física: 4 letras
        "ÑAA010101AAA",   # la Ñ es válida en un RFC
        "abc123456xy0",   # minúsculas: se normalizan antes de validar
        "  ABC123456XY0  ",  # espacios alrededor: se recortan
    ],
)
def test_acepta_un_rfc_bien_formado(rfc):
    assert validar(rfc)["valido"] is True


@pytest.mark.parametrize(
    "rfc, motivo",
    [
        ("", "vacío"),
        ("   ", "solo espacios"),
        ("AB", "muy corto"),
        ("ABC12345", "le faltan dígitos a la fecha"),
        ("ABCDE123456XY0", "cinco letras iniciales"),
        ("1234567890AB", "empieza con números"),
        ("ABC123456XY0EXTRA", "más largo de lo permitido"),
        ("ABC-123456-XY0", "trae guiones"),
    ],
)
def test_rechaza_un_rfc_mal_formado(rfc, motivo):
    assert validar(rfc)["valido"] is False, f"debió rechazarlo por: {motivo}"


def test_el_mensaje_de_vacio_es_distinto_al_de_formato():
    """Un RFC vacío y uno mal escrito son errores distintos.

    Devolver el mismo mensaje para ambos obligaría al usuario a adivinar qué
    hizo mal. Esta prueba fija esa distinción para que nadie la colapse por
    accidente al refactorizar.
    """
    assert validar("")["mensaje"] != validar("XX")["mensaje"]


def test_el_rfc_devuelto_viene_normalizado():
    assert validar("  abc123456xy0  ")["mensaje"] == "RFC válido: ABC123456XY0"


def test_la_peticion_sin_campo_rfc_no_revienta():
    """Robustez: un cliente mal escrito no debe tumbar el servicio."""
    respuesta = cliente.post("/api/validar", json={})
    assert respuesta.status_code == 200
    assert respuesta.json()["valido"] is False


def test_la_interfaz_se_sirve_en_la_raiz():
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Validación de RFC" in respuesta.text
