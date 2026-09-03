"""Prueba de carga del servicio de validación de RFC.

Selenium responde "¿funciona?". Esto responde una pregunta distinta:
"¿aguanta?". Un servicio puede pasar todas las pruebas funcionales y aun así
derrumbarse el primer día que entren doscientas personas al mismo tiempo.

Ejecución con interfaz web (para explorar y ver gráficas en vivo):
    uv run locust -f load/locustfile.py --host http://127.0.0.1:8000

Ejecución sin interfaz (para CI, con umbrales que hacen fallar la corrida):
    uv run locust -f load/locustfile.py --host http://127.0.0.1:8000 \
        --headless --users 50 --spawn-rate 10 --run-time 30s
"""

from locust import HttpUser, between, events, task

# Umbrales de aceptación. Viven aquí, en código versionado, y no como
# argumentos sueltos en la línea de comandos del CI: así se revisan en un pull
# request como cualquier otro cambio, y quedan a la vista de quien lea el
# proyecto.
#
# Sin umbrales, una prueba de carga siempre "pasa": mide y reporta, pero no
# protege de nada. El umbral es lo que la convierte en prueba.
MAX_PROPORCION_DE_FALLOS = 0.01   # 1% de las peticiones
MAX_P95_MS = 500                  # 95 de cada 100 usuarios por debajo de esto


@events.quitting.add_listener
def _verificar_umbrales(environment, **_):
    """Decide el código de salida del proceso al terminar la corrida.

    Se mide el percentil 95 y no el promedio: el promedio esconde la cola. Un
    servicio con promedio de 2 ms puede tener un 1% de usuarios esperando 3
    segundos, y son justo esos los que se van.
    """
    stats = environment.stats.total
    p95 = stats.get_response_time_percentile(0.95) or 0

    problemas = []
    if stats.fail_ratio > MAX_PROPORCION_DE_FALLOS:
        problemas.append(
            f"proporción de fallos {stats.fail_ratio:.2%} "
            f"(máximo {MAX_PROPORCION_DE_FALLOS:.2%})"
        )
    if p95 > MAX_P95_MS:
        problemas.append(f"p95 de {p95:.0f} ms (máximo {MAX_P95_MS} ms)")

    if problemas:
        for problema in problemas:
            print(f"UMBRAL EXCEDIDO: {problema}")
        environment.process_exit_code = 1
    else:
        print(
            f"Umbrales cumplidos: fallos {stats.fail_ratio:.2%}, p95 {p95:.0f} ms"
        )
        environment.process_exit_code = 0

# Tráfico realista: la mayoría de los RFC que llegan son correctos, pero
# siempre entra una proporción de basura. Medir solo con datos válidos daría
# una lectura optimista: la rama de error podría ser la lenta y no se vería.
RFC_VALIDOS = [
    "ABC123456XY0",
    "ABCD123456XY0",
    "ÑAA010101AAA",
    "XYZ987654AB1",
]

RFC_INVALIDOS = [
    "",
    "AB",
    "1234567890AB",
    "ABC-123456-XY0",
]


class UsuarioValidador(HttpUser):
    """Un usuario simulado que valida RFC contra el servicio."""

    # Tiempo de reflexión entre acciones. Sin esto, cada usuario dispararía
    # peticiones en un bucle cerrado y estarías midiendo la velocidad de
    # Locust, no un patrón de uso real. Una persona escribe un RFC y espera
    # un momento antes del siguiente.
    wait_time = between(0.5, 2.0)

    @task(4)
    def validar_rfc_correcto(self):
        """El caso común: pesa 4 veces más que el resto."""
        rfc = RFC_VALIDOS[self.environment.runner.user_count % len(RFC_VALIDOS)]

        # catch_response permite juzgar la respuesta, no solo cronometrarla.
        # Sin esto, Locust marca como exitoso cualquier HTTP 200 — incluso si
        # el contenido es incorrecto. Una respuesta rápida y equivocada sigue
        # siendo un defecto.
        with self.client.post(
            "/api/validar",
            json={"rfc": rfc},
            name="/api/validar [válido]",
            catch_response=True,
        ) as respuesta:
            if respuesta.status_code != 200:
                respuesta.failure(f"HTTP {respuesta.status_code}")
            elif not respuesta.json().get("valido"):
                respuesta.failure(f"rechazó un RFC válido: {rfc}")
            else:
                respuesta.success()

    @task(1)
    def validar_rfc_incorrecto(self):
        """La rama de error también se mide: rechazar debe ser barato."""
        rfc = RFC_INVALIDOS[self.environment.runner.user_count % len(RFC_INVALIDOS)]

        with self.client.post(
            "/api/validar",
            json={"rfc": rfc},
            name="/api/validar [inválido]",
            catch_response=True,
        ) as respuesta:
            if respuesta.status_code != 200:
                respuesta.failure(f"HTTP {respuesta.status_code}")
            elif respuesta.json().get("valido"):
                respuesta.failure(f"aceptó un RFC inválido: {rfc!r}")
            else:
                respuesta.success()

    @task(1)
    def abrir_la_interfaz(self):
        """Cargar la página también cuesta: entra en la medición."""
        self.client.get("/", name="/ [interfaz]")
