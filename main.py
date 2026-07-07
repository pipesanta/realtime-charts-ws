# Servidor web: sirve las páginas (rutas @app.get) y mantiene abierto el
# WebSocket (/ws) por el que se empuja, cada 3 segundos, el resultado del
# análisis (BehaviorAnalyzer) a todos los navegadores conectados.
import asyncio
import datetime as dt
import json
from collections import deque

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from analyzer import BehaviorAnalyzer

UPDATE_INTERVAL_SECONDS = 3
# Cuántos cálculos recientes guarda el servidor en memoria. Cuando un navegador
# se conecta, recibe de inmediato estos últimos mensajes (sin esperar 3s x N).
# Coincide con MAX_PUNTOS del frontend para que la gráfica se vea llena al entrar.
HISTORY_SIZE = 20

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Buffer con los últimos HISTORY_SIZE mensajes ya calculados. deque(maxlen=...)
# descarta solo el más viejo cuando se llena, así siempre tiene los N recientes.
history: deque[str] = deque(maxlen=HISTORY_SIZE)


# Lleva la lista de navegadores conectados por WebSocket y sabe cómo
# enviarles un mensaje a todos a la vez (broadcast).
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    # Se llama cuando un navegador abre el WebSocket; lo agrega a la lista.
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    # Se llama cuando un navegador se desconecta; lo quita de la lista.
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    # Envía el mismo mensaje a todos los navegadores conectados.
    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


# Corre el análisis (BehaviorAnalyzer) y lo convierte a JSON listo para enviar.
# Es una función normal (no async) porque hace trabajo pesado (leer el Excel);
# por eso broadcast_loop la corre en un hilo aparte con asyncio.to_thread.
def compute_snapshot() -> str:
    analyzer = BehaviorAnalyzer()
    registros = analyzer.df.to_dict(orient="records")
    # "hora" es la hora del cálculo en el servidor. El frontend la usa para el
    # eje X, así los mensajes del historial se ubican en su momento real.
    hora = dt.datetime.now().strftime("%H:%M:%S")
    return json.dumps({"hora": hora, "registros": registros})


# El "corazón" del tiempo real: cada 3 segundos recalcula el análisis, lo guarda
# en el historial y lo transmite a todos los clientes conectados. Corre solo, en
# segundo plano, desde que arranca el servidor (ver startup_event).
async def broadcast_loop():
    while True:
        try:
            payload = await asyncio.to_thread(compute_snapshot)
            history.append(payload)  # guarda este cálculo para los que se conecten luego
            await manager.broadcast(payload)
        except Exception as exc:
            print(f"Error calculando/enviando snapshot: {exc}")
        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)


# Arranca broadcast_loop en segundo plano apenas el servidor queda listo.
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_loop())


# Cada ruta @app.get("/algo") entrega una página HTML (un template) cuando el
# navegador visita esa dirección. "activo" le dice al menú de navegación cuál
# link resaltar.
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {"activo": "inicio"})


@app.get("/varianza")
async def varianza(request: Request):
    return templates.TemplateResponse(request, "varianza.html", {"activo": "varianza"})


@app.get("/varianza-chartjs")
async def varianza_chartjs(request: Request):
    return templates.TemplateResponse(request, "varianza_chartjs.html", {"activo": "varianza-chartjs"})


@app.get("/valores-medios")
async def valores_medios(request: Request):
    return templates.TemplateResponse(request, "valores_medios.html", {"activo": "valores-medios"})


# Canal en vivo: el navegador se conecta una vez a "/ws" y se queda escuchando
# los mensajes que manda broadcast_loop cada 3 segundos (ver static/js/*.js).
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Apenas se conecta, le mandamos el historial reciente para que vea la
    # gráfica llena de inmediato, sin esperar los próximos cálculos.
    for payload in list(history):
        await websocket.send_text(payload)
    try:
        while True:
            # Mantiene viva la conexión; no esperamos mensajes del cliente.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
