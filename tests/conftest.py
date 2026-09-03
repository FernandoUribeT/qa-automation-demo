"""Andamiaje compartido por las pruebas.

Un conftest.py es un archivo especial de pytest: lo que se define aquí queda
disponible en las pruebas del directorio sin necesidad de importarlo.
"""

import socket
import threading
import time

import pytest
import uvicorn
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from api.main import app


def _puerto_libre() -> int:
    """Pide al sistema operativo un puerto disponible.

    Fijar un puerto a mano (8000, por ejemplo) hace que dos corridas
    simultáneas choquen, y que la suite falle en CI por una razón que no
    tiene nada que ver con el código.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def servidor():
    """Levanta la API real y devuelve su URL base.

    scope="session": se levanta una sola vez para toda la corrida. La API no
    guarda estado entre peticiones, así que compartirla es seguro y evita
    pagar el arranque en cada prueba.
    """
    puerto = _puerto_libre()
    config = uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="warning")
    server = uvicorn.Server(config)

    hilo = threading.Thread(target=server.run, daemon=True)
    hilo.start()

    # Esperar a que quede listo antes de entregar la URL. Sin esto, la primera
    # prueba puede intentar conectarse antes de que el servidor escuche, y
    # fallar de forma intermitente — el clásico test flaky de arranque.
    limite = time.monotonic() + 15
    while not server.started:
        if time.monotonic() > limite:
            raise RuntimeError("el servidor no arrancó a tiempo")
        time.sleep(0.05)

    yield f"http://127.0.0.1:{puerto}"

    # Todo lo posterior al yield es limpieza: corre al terminar la sesión,
    # incluso si las pruebas fallaron.
    server.should_exit = True
    hilo.join(timeout=10)


@pytest.fixture
def navegador():
    """Entrega un Chrome limpio y lo cierra al terminar la prueba.

    scope por defecto (function): cada prueba recibe un navegador nuevo. Es
    más lento que reutilizarlo, pero garantiza que no herede cookies ni estado
    de la prueba anterior. Mismo principio del CI: empezar limpio para que el
    resultado sea confiable.
    """
    opciones = Options()
    # headless: sin ventana visible. Imprescindible en CI, donde no hay
    # pantalla en la que dibujar.
    opciones.add_argument("--headless=new")
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--disable-dev-shm-usage")
    opciones.add_argument("--window-size=1280,800")

    # Selenium 4 descarga y administra el chromedriver correcto por su cuenta
    # (Selenium Manager). No hace falta instalarlo ni fijar su ruta.
    driver = webdriver.Chrome(options=opciones)
    driver.implicitly_wait(0)  # sin espera implícita: las esperas van explícitas

    yield driver

    driver.quit()
