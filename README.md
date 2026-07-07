# PruebaQQ

Panel web en tiempo real que analiza el comportamiento de potencia reactiva por planta de generación (varianza y valor medio sobre los últimos 20 minutos), recalculado cada 3 segundos y transmitido por WebSocket a todos los navegadores conectados.

Actualmente los datos se leen de `BD_Prueba.xlsx` (fuente dummy para simular datos reales). Si el archivo no existe, el proyecto genera datos aleatorios automáticamente.

> 🚀 **¿Solo quieres levantar el servidor?** Sigue la **[GUIA_EJECUCION.md](GUIA_EJECUCION.md)**: comandos paso a paso según tu terminal (CMD, PowerShell o Git Bash) y según si es la primera vez o ya lo tienes instalado.

## Entorno virtual (Python)

Este proyecto usa un entorno virtual ubicado en `.venv`.

### Activar el entorno virtual

#### PowerShell (Windows)

```powershell
.\.venv\Scripts\Activate.ps1
```

Si aparece un error de politica de ejecucion, ejecuta primero:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Y luego vuelve a activar:

```powershell
.\.venv\Scripts\Activate.ps1
```

#### CMD (Símbolo del sistema de Windows)

```cmd
.venv\Scripts\activate.bat
```

#### Git Bash

```bash
source .venv/Scripts/activate
```

### Crear el entorno virtual (si no existe)

```powershell
py -m venv .venv
```

### Instalar dependencias

```powershell
pip install -r requirements.txt
```

### Desactivar el entorno virtual

```bash
deactivate
```

## Ejecutar el servidor

Con el entorno virtual activado:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0` hace que el servidor escuche en todas las interfaces de red de la máquina, no solo en `localhost`. Es lo que permite que otros equipos de la red se conecten.
- En tu propia máquina puedes entrar con `http://localhost:8000`.

## Acceder desde otra máquina de la red

1. **Averigua la IP de la máquina donde corre el servidor** (la que ejecutó el comando `uvicorn`):

   ```powershell
   ipconfig
   ```

   Busca la "Dirección IPv4" de tu adaptador de red (ej. `192.168.1.45`).

2. **Verifica que el Firewall de Windows permita el puerto** (la primera vez que corras `uvicorn` normalmente aparece un aviso; acepta permitir el acceso en redes privadas). Si no aparece el aviso o el acceso sigue bloqueado, agrega una regla manualmente:

   ```powershell
   New-NetFirewallRule -DisplayName "PruebaQQ Panel" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```

3. **Desde cualquier otra máquina en la misma red**, abre en el navegador:

   ```
   http://<IP-DE-LA-MAQUINA-SERVIDOR>:8000
   ```

   Por ejemplo: `http://192.168.1.45:8000`

4. Todos los que abran esa dirección verán las gráficas actualizarse en tiempo real (cada 3 segundos), sin necesidad de recargar la página.

> Nota: el servidor y los clientes deben estar en la misma red local (mismo WiFi/LAN) para que la IP sea alcanzable. Si la máquina servidor se apaga o cambia de red, la IP puede cambiar y hay que repetir el paso 1.

## Rutas disponibles

- `/` — Inicio (página básica de bienvenida).
- `/varianza` — Varianza en tiempo real por planta (Plotly.js).
- `/varianza-chartjs` — misma gráfica de varianza, pero con Chart.js (ejemplo comparativo de librería).
- `/valores-medios` — Valor medio actual por planta.

## Cómo funciona el ciclo completo (backend → gráfica)

En resumen: **Excel → analyzer.py → main.py (cada 3s) → WebSocket → JS del navegador → gráfica**.

1. **`analyzer.py`** lee `BD_Prueba.xlsx` y calcula, por planta, la varianza y el valor medio. El resultado queda en una tabla (`self.df`).
2. **`main.py`** tiene una tarea (`broadcast_loop`) que corre sola, cada 3 segundos, desde que arranca el servidor: crea un `BehaviorAnalyzer` nuevo, toma su tabla y la convierte a JSON.
3. Ese JSON se envía por el **WebSocket** (`/ws`) a todos los navegadores que estén conectados en ese momento — a todos a la vez, no uno por uno.
4. En el navegador, el archivo JS de cada página (`static/js/*.js`) está escuchando ese WebSocket. Cuando llega un mensaje nuevo, guarda el dato y le pide a la librería de gráficas (Plotly o Chart.js) que se redibuje.
5. Como el WebSocket queda abierto, no hace falta recargar la página: la gráfica se actualiza sola cada vez que llega un mensaje nuevo.

> 📖 **¿Nuevo en el proyecto o no sabes JavaScript?** Lee **[COMO_FUNCIONA.md](COMO_FUNCIONA.md)**: explica todo el ciclo paso a paso, siguiendo un dato desde el Excel hasta la gráfica, y traduce cada concepto de JavaScript a su equivalente en Python.

## Estructura del proyecto

- `analyzer.py` — lógica de análisis (`BehaviorAnalyzer`): lectura de datos, filtrado por ventana de tiempo y cálculo de varianza/valor medio.
- `main.py` — servidor FastAPI: rutas de navegación, WebSocket y loop de actualización periódica.
- `templates/` — páginas HTML (Jinja2) con el menú de navegación compartido.
- `static/` — CSS y JavaScript del frontend (Plotly.js para las gráficas).
- `Conexion.py` — prototipo original con gráfica local (matplotlib), no forma parte del servidor web.
