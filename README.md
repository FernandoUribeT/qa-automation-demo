# qa-automation-demo

Suite de automatización de pruebas sobre un servicio de validación de RFC:
pruebas de API, pruebas de interfaz con Selenium, prueba de carga con Locust, y
un pipeline de CI que corre todo en cada cambio.

El sistema bajo prueba es propio y deliberadamente pequeño. Automatizar contra
un sitio de terceros produce pruebas frágiles —cambian su HTML y la suite falla
sin que nada esté realmente roto— además de mandarle tráfico automatizado a
alguien que no lo pidió.

## Qué hay

| Carpeta | Contenido |
|---|---|
| `api/` | Servicio FastAPI: sirve la interfaz y expone `POST /api/validar` |
| `app/` | Interfaz de una página que consume esa API |
| `tests/test_api.py` | Pruebas de API: rápidas, en memoria, cubren los casos |
| `tests/test_ui.py` | Pruebas de interfaz con Selenium sobre Chrome headless |
| `load/locustfile.py` | Prueba de carga con Locust y umbrales de aceptación |
| `.github/workflows/` | Pipeline de CI |

## Pirámide de pruebas

Las pruebas de API cubren todas las variantes de RFC válido e inválido; las de
Selenium son pocas y responden una pregunta distinta: si la interfaz está bien
conectada al servicio y muestra lo que debe.

Probar las trece variantes por navegador tardaría minutos en vez de
milisegundos y no encontraría ningún defecto que las de API no encuentren
antes. Por eso hay 17 pruebas de API y 4 de interfaz.

Hay un caso que solo la interfaz puede detectar, y por eso existe: que un
segundo resultado no reemplace al primero y el usuario termine viendo dos
mensajes contradictorios en pantalla. La lógica responde bien las dos veces; el
defecto está únicamente en el DOM.

## Esperas, no `sleep`

Las pruebas de interfaz usan `WebDriverWait` con condición explícita. Un
`time.sleep(1)` desperdicia tiempo cuando la respuesta llega en 20 ms, y falla
cuando un día tarda 1.2 s por red lenta o CI cargado — sin que nada esté roto.
Esa es la causa más común de pruebas inestables.

## Carga: percentiles, no promedios

Una corrida local de 50 usuarios durante 20 s: 794 peticiones, 0 fallos.

| Métrica | Valor |
|---|---|
| Promedio | 2 ms |
| Mediana (p50) | 1 ms |
| p95 | 10 ms |
| p99 | 46 ms |

El promedio esconde la cola: uno de cada cien usuarios esperó 46 veces más que
la mediana. Por eso el reporte va por percentiles.

El job de carga en CI lleva umbrales (`--check-fail-ratio`,
`--check-avg-response-time`). Sin ellos Locust siempre termina en verde y el
pipeline no protege de nada.

## Ejecutar

```bash
uv sync --dev

# Todas las pruebas funcionales (API + interfaz)
uv run pytest -v

# Solo las de API, sin abrir navegador
uv run pytest tests/test_api.py

# Prueba de carga: primero levantar el servicio
uv run uvicorn api.main:app --port 8000
uv run locust -f load/locustfile.py --host http://127.0.0.1:8000
```

Selenium 4 administra el chromedriver por su cuenta; solo hace falta tener
Chrome instalado.

## Requisitos

Python 3.13, Chrome, y [uv](https://docs.astral.sh/uv/).
