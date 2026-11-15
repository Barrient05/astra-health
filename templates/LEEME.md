# Astra Health: versión del curso

Varias páginas HTML que Python (Flask) hace funcionar. Mismo diseño que el proyecto completo,
pero con el código reducido a lo esencial para estudiarlo.

## Cómo correrla

```
python -m pip install -r requirements.txt
python app.py
```
(Si ya tenías Flask, lo nuevo es `requests`, que sirve para consultar a NASA.)

Abre http://127.0.0.1:5000. Para apagarla: Ctrl + C en la terminal.

## Las páginas

| Dirección | Qué hay |
|---|---|
| `/` | **Panel**: mapa corporal animado, Ver día y Reproducir misión, qué hacer ahora, sistemas con sus peligros RIDGE, tendencia, radiación por fase y clima espacial real. |
| `/registro` | **Registro diario**: dictado, pulso por Bluetooth o a mano, prueba de reacción, prueba de pie, peso, ultrasonido y síntomas. |
| `/rutina` | **Rutina**: tareas del día con puntos, nivel, racha e insignias. |
| `/indicadores` | **Indicadores**: tabla con tu línea base y promedios, gráfica y cómo se mide cada uno. |
| `/planes` | **Planes de acción**: crearlos, quitarlos y ver qué hace cada uno. |
| `/nota` | **Nota para médicos**: la nota clínica en formato SOAP, lista para copiar. |
| `/guia` | **Guía de salud**: 17 mediciones con equipo, pasos, por qué importa y cuándo avisar. |
| `/fuentes` | **Fuentes**: todas las referencias con el dato usado y dónde aparece. |
| `/acerca` | **Cómo funciona**: el ciclo, el cálculo del riesgo, RIDGE, entornos y riesgos de NASA. |

## Qué hay en cada archivo (léelos en este orden)

| Archivo | Qué hace |
|---|---|
| `datos.py` | Qué medimos (indicadores, pruebas, sistemas, síntomas, planes), la tripulación con su historia, la simulación de cada día y el guardado en `datos/estado.json`. |
| `salud.py` | Los cálculos: métricas, puntaje 0–100 por sistema, nivel y color, pronóstico a 30 días, protocolos (qué hacer y a quién avisar) y signos de hoy. |
| `entornos.py` | Nave, estación, vehículo lunar o base en Marte: gravedad, radiación diaria y retraso de comunicación. También las fases del viaje (lanzamiento, cinturones de Van Allen, crucero), que cambian la dosis del día. |
| `clima.py` | Clima espacial real: pide a NASA DONKI los eventos solares con `requests`, los guarda en `datos/donki.json`, calcula la alerta de refugio y crea eventos simulados para la presentación. |
| `rutina.py` | Tareas del día, puntos, nivel, racha e insignias. |
| `nota.py` | La nota clínica SOAP para los médicos de vuelo. |
| `dictado.py` | Convierte lo que dicta el astronauta («pulso setenta y dos») en campos del registro, con reglas en español y sin internet. |
| `guia.py` | La guía de salud: 17 mediciones con equipo, cómo medir, por qué importa, cuándo avisar y fuentes. |
| `fuentes.py` | Catálogo de referencias (NASA, estudios, guías clínicas y reportes del equipo) con el dato exacto que tomamos de cada una. |
| `riesgos_nasa.py` | Los riesgos oficiales del Human Research Program de NASA y qué tanto los cubre el prototipo. |
| `catalogo_acerca.py` | Los 5 peligros RIDGE y la radiación por zona, para la página "Cómo funciona". |
| `idiomas.py` | La función `_()` que traduce cada texto al idioma elegido, y `numero()`, que escribe los decimales como se usan en cada idioma. |
| `traducciones/` | Un archivo por idioma (`en.json`, `pt.json`, `fr.json`): la clave es el texto en español y el valor, su traducción. |
| `herramientas/catalogo.py` | Revisa las traducciones: qué falta, qué sobra y si los marcadores `{así}` coinciden. |
| `app.py` | Las rutas web: una función por página, más las que reciben formularios (`/registro`, `/avanzar`, `/entorno`, `/clima-real`, `/donki`, `/plan`, `/tarea`, `/reiniciar`). |
| `templates/base.html` | El marco de todas las páginas: cabecera, menú, idioma, tripulación y pie. Las demás plantillas lo heredan con `{% extends %}`. |
| `templates/partes/cita.html` | Trozo reutilizable: escribe una cita "Autor (año)" con enlace. Se incluye con `{% include %}`. |
| `static/css/estilos.css` | El diseño (el mismo del proyecto completo). `curso.css` agrega los ajustes de estas páginas. |
| `static/js/pagina.js` | La gráfica del panel, el clic y el resaltado de los órganos, y Ver día / Reproducir misión: piden `/api/dia/<n>` y repintan sin recargar. |
| `static/js/indicadores.js` | La gráfica de cada indicador, con su rango y tu línea base. |
| `static/js/registro.js` | Prueba de reacción, dictado por voz y conteo manual de pulso: necesitan el navegador. |
| `static/js/pulso_bluetooth.js` | Lee el pulso de un reloj o banda por Bluetooth (o lo simula) y lo pone en el campo de pulso. |

## Cómo fluye una acción (ejemplo: guardar el registro)

1. El formulario de `registro.html` envía los datos a la ruta `/registro` (método POST).
2. `registro()` en `app.py` valida los campos con `datos.LIMITES`, los guarda con `datos.guardar()` y redirige al panel.
3. `panel()` vuelve a calcular todo con `salud.py` y `render_template` pinta la página con los nuevos valores.

## Clima espacial real (NASA DONKI)

1. El botón **Consultar NASA ahora** llama a `clima.actualizar()`: Python pide a NASA los eventos de partículas
   solares (SEP) y las fulguraciones (FLR) de los últimos 30 días, y los guarda.
2. Con el interruptor **Usar el clima espacial real** encendido, `clima.alerta()` revisa si hubo un SEP en las
   últimas 72 horas. Si lo hubo, el panel muestra la alerta de refugio y aparece el protocolo crítico.
3. Al **avanzar la misión**, `app.py` suma la dosis del evento (30 mSv al día durante 2 días, menos en la
   Estación o en Marte). Con el plan de refugio, la dosis baja.
4. Si no hay tormenta en curso, el botón **Ensayar con el último evento real** permite practicar el protocolo.
5. **Simulador de eventos** (dentro del bloque de radiación): si el día de la presentación no hay ninguna
   tormenta real, crea una de prueba (tormenta de partículas, fulguración X o M) fechada hace 2 horas,
   12 horas o 2 días. Queda marcada como **SIMULADO** en la lista, en la alerta y en el protocolo, para que
   nadie la confunda con los datos de NASA. El botón **Quitar los eventos simulados** los borra.

Si no hay internet, la página explica el motivo y conserva la última consulta guardada.

## El mapa y la animación de la misión

- Cada órgano recibe el color de su nivel. Los que están **críticos laten** (animación `pulso` en `estilos.css`).
- Al pasar el cursor por un sistema de la lista, su órgano se resalta en el mapa, y al revés.
- Los **botones de sistema** sobre la gráfica (y también la lista de sistemas y los órganos del mapa) cambian
  qué se grafica **sin recargar la página**: se piden los datos a Python y se redibuja la gráfica.
- **Ver día** mueve la misión a cualquier día pasado y **Reproducir misión** la recorre como una película:
  JavaScript pide `/api/dia/<n>` y repinta el mapa, los signos, los sistemas, el anillo, la radiación y la gráfica.
  Python sigue haciendo todos los cálculos; el navegador solo pinta lo que recibe.

## Idiomas

El selector de la cabecera (ES / EN / PT / FR) cambia toda la página: textos, reglas, guía, fuentes, mensajes
y lo que escribe JavaScript. El idioma elegido se guarda en la sesión, así que se mantiene al navegar y al enviar
formularios. También se puede compartir un enlace con el idioma: `http://127.0.0.1:5000/?lang=en`.

Cómo funciona:
1. El código sigue en español. Todo texto visible pasa por `_()`: en Python `_("Avanzar un día")`, en las
   plantillas `{{ _("Avanzar un día") }}` y en JavaScript `t("Simulación detenida.")`.
2. Los textos de los catálogos (los que Python lee al arrancar) se marcan con `N_()` y se traducen al mostrarlos.
3. `_()` busca el texto en `traducciones/<idioma>.json`. Si no lo encuentra, muestra el español.
4. Los textos con datos usan marcadores: `_("Día {dia} de {total}", dia=120, total=180)`.

Si agregas o cambias un texto en español, corre `python herramientas/catalogo.py`: te dice qué falta traducir.
Los títulos de las fuentes se dejan en su idioma original, como se citan normalmente.

## Tripulación (datos simulados)

- **Jimena Rangel**, comandante: hallazgo sin síntomas en el ultrasonido de la vena yugular y, después, cara hinchada.
- **César Tovar**, ingeniero de vuelo: duerme menos, más estrés, baja el ánimo y el apetito (pierde peso); fiebre los días 110 a 112.
- **Cynthia Calzadilla**, especialista médica: deja el ejercicio de resistencia (huesos), toma poca agua (riñones) y tiene visión borrosa (SANS).
- **Jesús Barrientos**, especialista de misión: hace cada vez menos ejercicio aeróbico; su corazón pierde condición.

## Reiniciar la simulación

Arriba del panel, "Reiniciar en" tiene dos botones:

- **Día 1**: la misión empieza desde cero. No hay historial, todos los indicadores están en su línea base, no hay protocolos y las gráficas están vacías. Sirve para ver la app como la usaría una tripulación el día del lanzamiento.
- **Día 120**: simula 120 días de misión antes de abrir. Así la app ya tiene tendencias, protocolos activos y gráficas con forma. Es la que conviene para una demostración.

El día de arranque es el argumento `dia_inicial` de `datos.estado_inicial()`. También puedes borrar `datos/estado.json` a mano: la app vuelve a crear la misión en el día 120.

## Datos reales de un reloj

Casi todo se simula, pero hay una excepción marcada en la app con la etiqueta **REAL**:
el pulso en reposo de Jesús Barrientos son 72 324 lecturas de un reloj inteligente,
463 días entre julio de 2025 y noviembre de 2026.

- `datos/reloj/frecuencia_cardiaca.csv` — la exportación original, sin tocar.
- `herramientas/importar_reloj.py` — la convierte en `datos/reloj.json`, un valor por día.
  Correr con `python herramientas/importar_reloj.py` cada vez que exportes datos nuevos.
- `reloj.py` — la app lo lee de ahí y decide qué día real le toca a cada día de la misión:
  los 180 días de la misión son los últimos 180 días medidos, en orden.
- En `datos.py`, el astronauta con `"reloj": True` usa ese pulso en vez del simulado, y su
  línea base es la mediana de sus primeros 30 días medidos.
- Cada registro dice qué campos son reales (`"reales": ["fc"]`) y con qué respaldo
  (`"medicion"`: fecha, cuántas lecturas, promedio y máximo de ese día).

El pulso en reposo se calcula como lo hacen los relojes comerciales: la mediana del cuarto
más bajo de las lecturas de 00:00 a 06:00; si no hubo lecturas de madrugada, el percentil 5
del día. Si borras `datos/reloj.json`, la app vuelve sola a simular ese pulso.

## Los cinco peligros del reto (RIDGE)

El reto nombra radiación, aislamiento y confinamiento, gravedad alterada y entorno cerrado y hostil.
Cada uno tiene indicadores propios en la app:

| Peligro | Qué lo mide |
|---|---|
| Radiación | dosis diaria y acumulada, eventos de NASA DONKI, límite de 600 mSv |
| Distancia de la Tierra | el retraso de comunicación decide quién actúa en cada protocolo |
| Gravedad alterada | entorno, hueso y músculo, prueba de ponerse de pie |
| Aislamiento y confinamiento | `contacto` (días sin llamada personal), `cohesion` (relación con la tripulación), `actividad` (horas despierto en movimiento) |
| Entorno cerrado y hostil | `co2` y `ruido`, medidos por la nave |

Los tres de aislamiento salen de lo que NASA revisa en sus conferencias psicológicas privadas
(sueño, carga de trabajo, ánimo, relación con la tripulación y con tierra) y del estudio Mars-500,
donde la actividad despierto cayó cerca de 7 % en 520 días de encierro. Sus umbrales están
en `salud.py` y sus fuentes en `fuentes.py` (`nasa_bhp`, `nasa_aislamiento`, `mars500`, `nasa_ruido`).

`co2` y `ruido` los miden los sensores de la nave: son iguales para toda la tripulación (semilla
`nave:<día>` en `generar_dia`) y no se teclean en el registro. Se ven en la barra "La nave hoy",
arriba del panel.

## Los cuatro entornos

El selector de entorno (nave, estación, vehículo lunar, base en Marte) cambia la gravedad, la dosis de radiación por día, el retraso con la Tierra y qué ejercicio se puede hacer. La misión simulada es siempre el viaje de 180 días a Marte: **los otros tres entornos son escenarios para comparar** qué le pasaría a la misma tripulación en otro destino, no etapas del viaje. Cada uno trae sus fuentes en `entornos.py`.

## Ejercicios sugeridos

1. En `datos.py`, agrega un quinto astronauta a `TRIPULACION_BASE` (copia uno y cambia nombre, `id` y su historia).
2. En `salud.py`, cambia el umbral de "Poca agua consumida" de 2.5 a 3.0 L y mira cómo cambian los protocolos.
3. En `entornos.py`, agrega un entorno nuevo (por ejemplo, una base lunar) y pruébalo en el panel.
4. En `rutina.py`, crea una insignia nueva y define su meta.
5. En `datos.py`, cambia una fuente en `FUENTES_INDICADOR` y mira cómo cambia la cita del campo y la página Fuentes.
6. En `clima.py`, agrega un tipo nuevo al simulador (por ejemplo, una fulguración clase C) en `TIPOS_SIMULADOS`.
7. Agrega un quinto idioma: súmalo a `IDIOMAS` en `idiomas.py`, copia `traducciones/en.json` con el nuevo código y traduce los valores.
