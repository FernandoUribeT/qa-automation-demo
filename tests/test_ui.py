"""Pruebas de interfaz con Selenium — la punta de la pirámide.

Son pocas y caras: cada una abre un Chrome real. Por eso aquí NO se repite la
cobertura de casos que ya cubre test_api.py. Estas responden una pregunta
distinta: ¿la interfaz está bien conectada al servicio y muestra lo que debe?

Un error clásico al empezar es probar las 13 variantes de RFC por navegador.
Tardaría minutos en vez de milisegundos y no encontraría ningún defecto que
las pruebas de API no encuentren antes.
"""

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Localizadores en un solo lugar. Si mañana cambia el HTML se corrige aquí, no
# en cada prueba. Repartir selectores por todo el archivo es el error que hace
# que un cambio de front rompa quince pruebas a la vez.
CAMPO_RFC = (By.ID, "rfc")
BOTON_VALIDAR = (By.ID, "validar")
RESULTADO = (By.ID, "resultado")

ESPERA_MAXIMA = 10


def validar_en_la_interfaz(navegador, servidor, rfc):
    """Llena el formulario, lo envía, y devuelve el elemento del resultado."""
    navegador.get(servidor)
    navegador.find_element(*CAMPO_RFC).send_keys(rfc)
    navegador.find_element(*BOTON_VALIDAR).click()

    # La pieza clave de toda la prueba.
    #
    # El resultado no existe en el DOM hasta que la API responde. Sin esperar,
    # Selenium lo buscaría de inmediato, no lo encontraría, y la prueba
    # fallaría aunque la aplicación funcione bien.
    #
    # Lo que NO se debe hacer aquí es time.sleep(1):
    #   - si la respuesta tarda 20 ms, se desperdician 980 ms por prueba
    #   - si un día tarda 1.2 s (red lenta, CI cargado), falla sin que nada
    #     esté roto — eso es una prueba flaky
    #
    # WebDriverWait revisa periódicamente y sigue en cuanto la condición se
    # cumple: rápido cuando todo va bien, paciente cuando hace falta.
    return WebDriverWait(navegador, ESPERA_MAXIMA).until(
        EC.visibility_of_element_located(RESULTADO)
    )


def test_un_rfc_valido_se_muestra_como_exito(navegador, servidor):
    resultado = validar_en_la_interfaz(navegador, servidor, "ABC123456XY0")

    assert "RFC válido: ABC123456XY0" in resultado.text
    assert "exito" in resultado.get_attribute("class")


def test_un_rfc_invalido_se_muestra_como_error(navegador, servidor):
    resultado = validar_en_la_interfaz(navegador, servidor, "XX")

    assert "no tiene un formato válido" in resultado.text
    assert "error" in resultado.get_attribute("class")


def test_el_campo_vacio_muestra_su_propio_mensaje(navegador, servidor):
    resultado = validar_en_la_interfaz(navegador, servidor, "")

    assert "obligatorio" in resultado.text
    assert "error" in resultado.get_attribute("class")


def test_una_segunda_validacion_reemplaza_el_resultado_anterior(navegador, servidor):
    """El resultado viejo no debe quedarse en pantalla junto al nuevo.

    Es un defecto de interfaz que las pruebas de API jamás detectarían: la
    lógica responde bien las dos veces, pero el usuario ve dos mensajes
    contradictorios al mismo tiempo.
    """
    validar_en_la_interfaz(navegador, servidor, "XX")

    campo = navegador.find_element(*CAMPO_RFC)
    campo.clear()
    campo.send_keys("ABC123456XY0")
    navegador.find_element(*BOTON_VALIDAR).click()

    WebDriverWait(navegador, ESPERA_MAXIMA).until(
        EC.text_to_be_present_in_element(RESULTADO, "RFC válido")
    )

    assert len(navegador.find_elements(*RESULTADO)) == 1
