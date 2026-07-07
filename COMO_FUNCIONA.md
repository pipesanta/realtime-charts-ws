# Cómo funciona el proyecto (guía paso a paso)

Esta guía explica **todo el recorrido** que hace un dato, desde el Excel hasta la
línea que se dibuja en el navegador. Está pensada para alguien que sabe algo de
**Python** pero **nada de JavaScript**, así que cada concepto nuevo de JS se
compara con su equivalente en Python.

---

## 1. La idea general en una frase

> El servidor (Python) recalcula el análisis **cada 3 segundos** y lo **empuja**
> a todos los navegadores abiertos. Cada navegador recibe ese dato y **redibuja
> su gráfica**, sin recargar la página.

Piensa en el servidor como una **emisora de radio**: transmite cada 3 segundos, y
todos los navegadores que estén "sintonizados" reciben lo mismo al mismo tiempo.
Esa "sintonía" que se queda abierta se llama **WebSocket** (lo vemos en el paso 4).

---

## 2. El mapa de archivos

Estos son los archivos que participan en el ciclo, en orden:

| Orden | Archivo | Lenguaje | Qué hace |
|-------|---------|----------|----------|
| 1 | `analyzer.py` | Python | Lee el Excel y calcula varianza/valor medio por planta. |
| 2 | `main.py` | Python | Cada 3s corre el análisis y lo envía por WebSocket. También entrega las páginas HTML. |
| 3 | `templates/*.html` | HTML | La estructura visual de cada página (títulos, menú, dónde va la gráfica). |
| 4 | `static/js/*.js` | JavaScript | Se ejecuta **dentro del navegador**: recibe los datos y dibuja la gráfica. |

**Clave para entender todo:** el Python (`analyzer.py`, `main.py`) corre en **tu
máquina/servidor**. El JavaScript (`static/js/*.js`) corre en **la máquina de cada
persona que abre la página**, dentro de su navegador. Son dos computadoras
distintas hablando por la red.

---

## 3. Backend: del Excel al JSON (Python)

### Paso 3.1 — `analyzer.py` calcula los números

Cuando se crea un objeto `BehaviorAnalyzer()`, se ejecuta todo el análisis y el
resultado queda en `self.df` (una tabla de pandas). Por ejemplo:

| PlantaGeneracion | Varianza | ValorMedio |
|------------------|----------|------------|
| SOGAMO--GEN2_    | 1.28     | -30.30     |
| TESALI--GEN1_    | 1.06     | -34.76     |
| ...              | ...      | ...        |

Esto ya lo entiendes porque es Python puro (pandas). Lo importante: **el
resultado final es esta tabla**.

### Paso 3.2 — `main.py` convierte la tabla a JSON

```python
def compute_snapshot() -> str:
    analyzer = BehaviorAnalyzer()             # corre el análisis
    registros = analyzer.df.to_dict(orient="records")  # tabla -> lista de diccionarios
    hora = dt.datetime.now().strftime("%H:%M:%S")      # hora del cálculo
    return json.dumps({"hora": hora, "registros": registros})  # diccionario -> texto JSON
```

Además de la lista de plantas, el mensaje incluye la **hora del cálculo** (`hora`).
Esto sirve para dos cosas: que la gráfica sepa en qué punto del eje X poner cada
dato, y que el historial (ver paso 4.1) se dibuje con la hora real en que se
calculó, no con la hora en que el navegador lo recibió.

`to_dict(orient="records")` convierte la tabla en una **lista de diccionarios**,
uno por fila:

```python
[
    {"PlantaGeneracion": "SOGAMO--GEN2_", "Varianza": 1.28, "ValorMedio": -30.30},
    {"PlantaGeneracion": "TESALI--GEN1_", "Varianza": 1.06, "ValorMedio": -34.76},
]
```

Luego `json.dumps(...)` lo convierte en **texto** (un string). ¿Por qué texto?
Porque por la red solo se puede enviar texto, no objetos de Python. Ese texto se
llama **JSON** y se ve casi igual que un diccionario de Python:

```json
{"hora": "14:05:03", "registros": [{"PlantaGeneracion": "SOGAMO--GEN2_", "Varianza": 1.28, "ValorMedio": -30.3}]}
```

> **Idea importante:** JSON es el "idioma común" entre Python y JavaScript. Python
> arma el JSON, lo manda como texto, y JavaScript lo vuelve a convertir en algo
> que puede usar. Ninguno de los dos necesita entender el lenguaje del otro, solo
> este texto intermedio.

### Paso 3.3 — El "reloj" que dispara todo cada 3 segundos

```python
async def broadcast_loop():
    while True:                                       # bucle infinito
        payload = await asyncio.to_thread(compute_snapshot)  # calcula el JSON
        history.append(payload)                       # lo guarda en el historial
        await manager.broadcast(payload)              # lo manda a TODOS los navegadores
        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)  # espera 3 segundos y repite
```

Es un `while True` que nunca termina: calcula, guarda, envía a todos, espera 3
segundos, y vuelve a empezar. Este bucle arranca solo cuando el servidor se
enciende (ver `startup_event` en `main.py`).

`manager.broadcast(payload)` recorre la lista de navegadores conectados y le
manda el mismo texto a cada uno. `history.append(payload)` guarda una copia del
mensaje para poder entregárselo a quien se conecte más tarde (ver paso 4.1).

---

## 4. El puente: WebSocket

Aquí está la parte nueva. Normalmente un navegador funciona así:

- **HTTP normal (lo que ya conoces):** el navegador **pregunta** ("dame la página
  /varianza") y el servidor **responde** una vez. Fin. Si quieres datos nuevos,
  tienes que volver a preguntar (recargar la página).

- **WebSocket (lo que usamos aquí):** el navegador abre una conexión **una sola
  vez** y **se queda escuchando**. El servidor puede **empujar** mensajes cuando
  quiera, sin que el navegador vuelva a preguntar. Es como dejar la línea
  telefónica abierta en vez de colgar y volver a llamar cada vez.

Por eso las gráficas se actualizan solas: la conexión nunca se cierra, y el
servidor manda un mensaje nuevo cada 3 segundos.

En `main.py`, el WebSocket vive en la ruta `/ws`:

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)      # registra este navegador en la lista
    for payload in list(history):         # le envía primero el historial reciente
        await websocket.send_text(payload)
    try:
        while True:
            await websocket.receive_text()  # mantiene la conexión viva
    except WebSocketDisconnect:
        manager.disconnect(websocket)     # si se va, lo quita de la lista
```

### Paso 4.1 — El historial: por qué la gráfica aparece llena al instante

**El problema.** Como el servidor calcula cada 3 segundos, si solo enviara los
mensajes nuevos, alguien que abre la página tendría que esperar mucho para ver la
gráfica llena: 1 punto a los 3s, 2 puntos a los 6s… y así hasta 20 puntos en un
minuto. Poco práctico.

**La solución.** El servidor **recuerda** los últimos cálculos y se los entrega de
golpe a cada navegador nuevo apenas se conecta. Así la gráfica se ve completa desde
el primer segundo, y a partir de ahí sigue recibiendo los mensajes en vivo.

Esto se logra con dos piezas en `main.py`:

```python
from collections import deque

HISTORY_SIZE = 20                          # cuántos cálculos recordar
history = deque(maxlen=HISTORY_SIZE)       # "cola" que se queda con los N más recientes
```

Un `deque` (cola) con `maxlen` es como una lista con capacidad fija: cuando ya tiene
20 elementos y entra uno nuevo, **descarta solo el más viejo automáticamente**. Así
siempre guarda los últimos 20, sin crecer para siempre en memoria.

El recorrido completo del historial es:

1. Cada 3s, `broadcast_loop` calcula un mensaje y hace `history.append(payload)`
   (lo guarda) antes de transmitirlo.
2. Cuando un navegador se conecta, el WebSocket recorre `history` y le manda esos
   mensajes guardados uno por uno, **de inmediato**.
3. Como cada mensaje trae su propia `hora` (paso 3.2), la gráfica los ubica en el
   punto correcto del eje X aunque lleguen todos juntos en ese instante.

> **Nota:** el historial vive en la **memoria** del servidor. Si reinicias el
> servidor, empieza vacío otra vez (no se guarda en disco). El tamaño se controla
> con `HISTORY_SIZE` y está pensado para coincidir con los 20 puntos que muestra la
> gráfica (`MAX_PUNTOS` en el JavaScript).

---

## 5. Frontend: del JSON a la gráfica (JavaScript)

Este es el archivo `static/js/varianza.js`. Corre **dentro del navegador de cada
persona**. Vamos por partes, comparando con Python.

### Paso 5.1 — Mini-diccionario Python ↔ JavaScript

Antes de leer el código, esta tabla te deja entender el 90% de lo que ves:

| En Python | En JavaScript | Notas |
|-----------|---------------|-------|
| `x = 5` | `const x = 5;` | `const` = no cambia; `let` = sí cambia. JS usa `;` al final. |
| `mi_lista = []` | `const lista = [];` | Igual, una lista/arreglo. |
| `mi_dict = {}` | `const obj = {};` | En JS se llama "objeto", pero es como un diccionario. |
| `dic["clave"]` | `obj["clave"]` o `obj.clave` | JS permite las dos formas. |
| `len(lista)` | `lista.length` | |
| `lista.append(x)` | `lista.push(x)` | |
| `lista.pop(0)` | `lista.shift()` | Quita el primer elemento. |
| `def f(a):` | `function f(a) {` | El cuerpo va entre `{ }` en vez de por indentación. |
| `for x in lista:` | `for (const x of lista) {` | |
| comentario `#` | comentario `//` | |

Con eso, el código de JS se lee casi como Python con llaves y puntos y coma.

### Paso 5.2 — Conectarse y escuchar los mensajes

```javascript
function conectar() {
    const ws = new WebSocket(`ws://${location.host}/ws`);  // abre la conexión al servidor

    ws.onmessage = (event) => {              // <-- ESTO se ejecuta CADA VEZ que llega un mensaje
        const data = JSON.parse(event.data); // texto JSON -> objeto de JavaScript
        actualizarGrafica(data.registros, data.hora);  // le pasa las plantas y la hora del cálculo
    };

    ws.onclose = () => {
        setTimeout(conectar, 3000);          // si se cae la conexión, reintenta en 3s
    };
}
conectar();  // arranca todo
```

La parte más importante y más distinta de Python es **`ws.onmessage`**. No es una
función que "llamas" tú; es una función que **le entregas al navegador para que
él la llame por ti** cada vez que llegue un mensaje del servidor. En Python no es
tan común este patrón; piénsalo como: *"cuando llegue un mensaje, ejecuta esto
automáticamente"*.

- `JSON.parse(event.data)` es el **espejo** de `json.dumps` de Python: convierte
  el texto JSON de vuelta en un objeto que JavaScript puede usar (una lista de
  diccionarios, igual a la que armó Python).
- `(event) => { ... }` es simplemente otra forma de escribir una función en JS
  (se llama "función flecha"). Equivale a `def anonima(event): ...` en Python.

### Paso 5.3 — Dibujar la gráfica

`actualizarGrafica(registros, hora)` recibe la lista de plantas (la misma que salió
del Excel) y la hora del cálculo, y hace tres cosas:

1. Anota en el eje X la `hora` que mandó el servidor (`historialTiempos`).
2. Guarda la varianza de cada planta en su historial (`historialVarianzas`), y
   mantiene solo los últimos 20 valores para que la gráfica no crezca infinito.
3. Le entrega esos datos a **Plotly** (la librería de gráficas) con
   `Plotly.react(...)`, que redibuja las líneas.

No necesitas entender cada línea de manejo de listas: lo esencial es que **toma
los números que llegaron y le dice a Plotly "dibújalos"**. Cada 3 segundos llega
un mensaje nuevo, esta función corre otra vez, y la gráfica avanza un paso. Cuando
te acabas de conectar, esta función corre varias veces seguidas (una por cada
mensaje del historial), y por eso la gráfica aparece llena de una vez.

---

## 6. El ciclo completo, de principio a fin

Juntando todo, esto es lo que pasa cada 3 segundos:

```
   [ Excel BD_Prueba.xlsx ]
            │  (analyzer.py lo lee y calcula)
            ▼
   [ Tabla: planta, varianza, valor medio ]
            │  (main.py: to_dict + json.dumps, agrega la hora)
            ▼
   [ Texto JSON: hora + registros ]
            │  (main.py: history.append -> se guarda en el historial)
            │  (WebSocket /ws: manager.broadcast a TODOS los navegadores)
            ▼════════════════ red ════════════════▶  (viaja a cada navegador)
            │
            ▼  (JavaScript: ws.onmessage)
   [ JSON.parse -> lista de plantas ]
            │  (actualizarGrafica)
            ▼
   [ Plotly / Chart.js dibuja las líneas ]
            │
            ▼
   [ La persona ve la gráfica moverse sola ]
```

Y cuando **alguien nuevo se conecta**, antes de esperar el siguiente cálculo el
servidor le envía de una vez todo el historial guardado, así que su gráfica arranca
llena:

```
   [ Navegador nuevo abre /ws ]
            │
            ▼  (main.py recorre "history" y lo envía)
   [ Últimos 20 mensajes guardados ] ═══ red ═══▶ [ Gráfica llena al instante ]
            │
            ▼
   [ luego siguen llegando los mensajes en vivo cada 3s ]
```

Y como el WebSocket queda abierto, este recorrido se repite solo cada 3 segundos,
para **todas** las personas conectadas a la vez.

---

## 7. Preguntas frecuentes

### Sobre el diseño del proyecto

**¿Por qué hay dos lenguajes?** Python es excelente para leer datos y calcular
(pandas), pero no puede dibujar dentro del navegador. El navegador **solo entiende
JavaScript**. Por eso Python calcula y JavaScript dibuja; se comunican por JSON.

**¿Qué es FastAPI y qué es uvicorn?** `FastAPI` es la librería de Python con la que
está escrito el servidor (las rutas `@app.get`, el WebSocket, etc.). `uvicorn` es el
programa que **enciende** ese servidor y lo deja escuchando en un puerto. Por eso lo
arrancas con `uvicorn main:app` (que significa: "toma el objeto `app` que está
dentro de `main.py` y ponlo a correr").

**¿Qué significa `async` / `await` que aparece en `main.py`?** Es la forma en que
Python atiende a **muchos navegadores a la vez** sin bloquearse. Sin `async`, mientras
el servidor le habla a una persona, los demás tendrían que esperar en fila. Con
`async`, puede atender a todos casi al mismo tiempo. Para mantener el proyecto no
necesitas dominarlo; basta con saber que por eso aguanta varias personas conectadas.

**¿Qué son los `templates/` y por qué tienen `{% ... %}`?** Son las páginas HTML.
Usamos una librería (Jinja2) que permite tener un `base.html` con el menú, y que las
demás páginas lo "hereden" en vez de copiar el menú en cada una. Los `{% ... %}` son
instrucciones para Jinja2 (por ejemplo, marcar qué link del menú está activo). Es
parecido a los f-strings de Python (`f"Hola {nombre}"`), pero para HTML.

**¿Para qué sirve la carpeta `static/`?** Guarda los archivos que el navegador
descarga tal cual: el JavaScript (`static/js/`) y los estilos/colores
(`static/css/`). Se llaman "estáticos" porque el servidor no los modifica, solo los
entrega.

**¿Por qué sigue ahí `Conexion.py` si no se usa?** Es el prototipo original que
dibujaba la gráfica con matplotlib en una ventana local (para una sola persona). Se
dejó como referencia histórica, pero **no forma parte del servidor web**. Puedes
ignorarlo o borrarlo sin afectar nada.

**¿Qué es exactamente un "puerto" (el 8000)?** Una misma máquina puede tener varios
programas escuchando en la red a la vez; el puerto es como el "número de
apartamento" que los distingue. Cuando alguien abre `http://192.168.1.45:8000`, el
`:8000` le dice a qué programa de esa máquina quiere hablar (a nuestro servidor).

**¿Por qué no mando el Excel directamente al navegador en vez de JSON?** Porque el
navegador no necesita todo el Excel (que puede pesar mucho), solo el resultado ya
calculado: unas pocas líneas de planta/varianza/valor medio. Enviar solo ese
resumen en JSON es mucho más liviano y rápido para la red.

**¿Qué hace la clase `ConnectionManager` de `main.py`?** Lleva la **lista de
navegadores conectados** y sabe mandarles un mensaje a todos de una vez. Es como la
lista de suscriptores de la emisora: cuando llega el momento de transmitir, recorre
la lista y le envía a cada uno.

**¿Por qué la gráfica ya aparece con datos apenas abro la página, sin esperar?** El
servidor guarda en memoria los últimos cálculos (variable `history` en `main.py`,
tamaño `HISTORY_SIZE`). Cuando un navegador se conecta, primero le manda de golpe ese
historial reciente y luego sigue con los mensajes nuevos cada 3 segundos. Así no
tienes que esperar a que se vaya llenando punto por punto. La explicación completa
está en el **paso 4.1**.

**¿Por qué el cálculo corre en un "hilo aparte" (`asyncio.to_thread`)?** Leer el
Excel y calcular tarda un momento. Si eso se hiciera en la línea principal, el
servidor quedaría "congelado" para todos durante ese ratito. Al mandarlo a un hilo
aparte, el servidor sigue atendiendo a los demás mientras calcula.

**¿Cuál gráfica dejo, la de Plotly o la de Chart.js?** Las dos muestran lo mismo;
existen solo para que compares las dos librerías. Cuando decidas cuál te gusta,
puedes borrar la otra (su template, su archivo JS y su ruta en `main.py`) sin
afectar el resto.

### Cómo lo uso y lo mantengo

**¿Cómo arranco el proyecto?** Activa el entorno virtual y corre
`uvicorn main:app --host 0.0.0.0 --port 8000`. Los pasos completos están en el
`README.md`.

**¿Cómo detengo el servidor?** En la terminal donde está corriendo, presiona
`Ctrl + C`.

**¿Dónde cambio los datos de origen (el Excel)?** Solo en la función
`extract_data_from_excel` de `analyzer.py`. El resto del proyecto no se entera de
dónde vienen los datos.

**¿Dónde cambio cada cuánto se actualiza?** En `main.py`, la variable
`UPDATE_INTERVAL_SECONDS = 3` (segundos).

**¿Cómo agrego una planta nueva?** Como cada planta es una hoja del Excel, basta con
agregar una hoja nueva con el mismo formato de columnas. El código la detecta sola,
no hay que tocar nada más.

**Quiero una gráfica nueva, ¿qué toco?** Tres cosas: un archivo en `templates/`
(la página), un archivo en `static/js/` (que se conecta al `/ws` y dibuja), y una
ruta `@app.get(...)` en `main.py`. Puedes copiar los de `varianza` como plantilla.

**¿Cómo cambio los colores o el tipo de gráfica?** Eso vive en el archivo JavaScript
de esa página (`static/js/...`). Por ejemplo, en `valores_medios.js` el color de las
barras está en `marker: { color: "#34d399" }`. Con la tabla de traducción del paso
5.1 puedes leer y ajustar ese archivo sin saber JavaScript a fondo.

**¿Necesito instalar algo nuevo?** Solo la primera vez, con
`pip install -r requirements.txt` (con el entorno virtual activado). Si algún día
agregas una librería nueva de Python, instálala y luego actualiza ese archivo con
`pip freeze > requirements.txt`.

**¿Tengo que saber JavaScript para mantener esto?** Para cambiar los cálculos, no:
todo eso es Python. Solo tocarías JavaScript si quieres cambiar **cómo se ve** la
gráfica (colores, tipo de gráfica), y con la tabla del paso 5.1 puedes leer el
código sin problema.

**¿Cómo muestro más (o menos) de 20 puntos en la gráfica?** En el archivo JavaScript
de esa página está la línea `const MAX_PUNTOS = 20;`. Cambia el número y listo.

**¿Cómo cambio el nombre de una página en el menú?** El menú está en
`templates/base.html`. Ahí verás la lista de links (`<a href="...">Texto</a>`);
edita el texto entre las etiquetas `<a>` y `</a>`.

**¿Puedo dejar el servidor corriendo todo el día para que otros siempre lo vean?**
Sí, mientras la máquina esté encendida y la terminal con `uvicorn` abierta. Si
quieres que arranque solo o que no dependa de una terminal abierta, eso ya es
"dejarlo como servicio", un paso más avanzado que se puede agregar después.

**Cambié algo en `main.py` o `analyzer.py` pero no veo el cambio.** El servidor lee
esos archivos una sola vez al arrancar. Detén `uvicorn` (`Ctrl + C`) y vuélvelo a
arrancar. Truco: si agregas `--reload` al comando (`uvicorn main:app --reload`), se
reinicia solo cada vez que guardas un archivo (útil mientras desarrollas).

**Cambié el JavaScript o el CSS pero el navegador muestra lo viejo.** El navegador
guarda una copia (caché) para ir más rápido. Recarga forzando la actualización con
`Ctrl + F5`.

**¿Puedo ponerle una contraseña para que no cualquiera entre?** El proyecto hoy no
tiene inicio de sesión: quien alcance la IP y el puerto puede ver las gráficas. Para
uso interno en la oficina suele bastar. Si necesitas restringir el acceso, se puede
agregar autenticación más adelante (es un tema aparte).

### Cuando algo sale mal

**Abrí la página y no veo ninguna gráfica / dice "Desconectado".** Revisa que el
servidor (`uvicorn`) siga corriendo en la terminal. Si se cerró o dio error, la
página no recibe datos. El texto de estado arriba de la gráfica te dice si está
"Conectado" o "Desconectado".

**La gráfica aparece pero está vacía (sin líneas).** Puede que el Excel no tenga
datos dentro de la ventana de los últimos 20 minutos, o que las plantas tengan muy
pocos registros (el análisis ignora plantas con menos de 4 filas). Revisa los datos
de `BD_Prueba.xlsx`.

**Sale un error `Address already in use` (dirección en uso) al arrancar.** Significa
que el puerto 8000 ya está ocupado (quizás dejaste otro `uvicorn` corriendo). Cierra
el anterior con `Ctrl + C`, o arranca en otro puerto: `--port 8001`.

**¿Dónde veo los errores del servidor?** En la **terminal** donde corre `uvicorn`.
Ahí aparecen los mensajes, incluidos los `print` de errores del `broadcast_loop`.

**Un compañero no puede abrir mi IP.** Casi siempre es el **Firewall de Windows** o
que no están en la misma red. Revisa la sección "Acceder desde otra máquina" del
`README.md`.

**Si dos personas abren la página, ¿se estorban entre sí?** No. El servidor le manda
una copia del mismo mensaje a cada navegador. Cada quien tiene su propia gráfica; lo
que hace una persona (zoom, ocultar una línea) no afecta a las demás.

**Tengo el Excel abierto en mi PC y el servidor da error al leerlo.** Puede pasar si
el archivo está bloqueado mientras lo editas. Ciérralo (o guarda una copia para
editar) y el servidor volverá a leerlo en el siguiente ciclo.

**Cierro la pestaña del navegador, ¿se apaga el servidor?** No. El navegador es solo
un "espectador". El servidor sigue corriendo en su terminal hasta que lo detengas con
`Ctrl + C`. Cerrar la pestaña solo cierra el WebSocket de esa persona.

**La página va lenta o pesada.** La causa más común es la librería de gráficas
(Plotly pesa varios MB la primera carga). Si es un problema, la página de Chart.js es
más liviana. También ayuda no mostrar demasiados puntos (`MAX_PUNTOS`).

**Las horas de la gráfica no coinciden con las del Excel.** El eje X usa la hora del
**reloj del navegador** en el momento en que llega cada dato, no la hora que viene
dentro del Excel. Son cosas distintas: una es "cuándo se calculó", la otra es "de
cuándo son los datos".

### Sobre los datos y el análisis

**¿Qué significa la "Varianza" que se grafica?** En este proyecto es una medida de
**qué tanto se aleja** el valor de una planta respecto a su propio promedio en los
últimos 20 minutos. Varianza alta = el valor está fluctuando mucho; varianza baja =
está estable. El cálculo exacto está en `compute_variance` de `analyzer.py`.

**¿Qué es el "Valor Medio"?** Es el promedio de la potencia reactiva de esa planta en
la ventana de tiempo analizada. Puede ser negativo según cómo esté operando la planta;
eso es normal y viene tal cual de los datos.

**¿Por qué algunas plantas no aparecen?** El análisis ignora las plantas con menos de
4 registros en la ventana de 20 minutos, porque con tan pocos datos el cálculo no
sería confiable (ver `analize_reactive_power` en `analyzer.py`).

**¿Qué columnas necesita tener cada hoja del Excel?** Las que usa el cálculo:
`Hora`, `Valor`, `DeltaSeg` y `FechaHora`. Si agregas una planta (hoja) nueva, debe
tener esas mismas columnas para que el análisis funcione.

**¿Qué pasa si cambio el origen de datos (por ejemplo, a una base de datos)?**
Mientras la función `extract_data_from_excel` siga **devolviendo los datos con el
mismo formato** (un diccionario de plantas con esas columnas), el resto del proyecto
—el análisis, el WebSocket y las gráficas— sigue funcionando igual sin cambios.
