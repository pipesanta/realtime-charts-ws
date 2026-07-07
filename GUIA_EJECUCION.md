# Guía de ejecución paso a paso

Esta guía te dice **exactamente qué comandos escribir** para levantar el servidor,
según:

- **Qué terminal usas**: CMD, PowerShell o Git Bash.
- **Si es la primera vez** (hay que crear el entorno e instalar dependencias) o
  **si ya lo tienes montado** (solo activar y arrancar).

> Antes de empezar, abre la terminal **dentro de la carpeta del proyecto**
> (`realtime-charts-ws`). Si no sabes cómo: abre la carpeta en el Explorador de
> Windows, y en la barra de direcciones escribe `cmd`, `powershell` o
> `git bash here` (según la terminal) y pulsa Enter.

---

## ¿Qué es esto del "entorno virtual" y por qué?

Un **entorno virtual** (`.venv`) es una carpeta donde se instalan las librerías
de Python **solo para este proyecto**, sin ensuciar el Python global de tu PC.
Así, las versiones que pide este proyecto (FastAPI, pandas, etc.) no chocan con
las de otros proyectos.

El flujo mental siempre es el mismo:

1. **Crear** el entorno (una sola vez). → `py -m venv .venv`
2. **Activar** el entorno (cada vez que abres una terminal nueva). → varía según la terminal
3. **Instalar** las dependencias (la primera vez, o cuando cambien). → `pip install -r requirements.txt`
4. **Arrancar** el servidor. → `uvicorn main:app --host 0.0.0.0 --port 8000`

La diferencia entre "primera vez" y "siguientes veces" es solo que la primera
haces los 4 pasos, y después normalmente solo haces el **2** y el **4**.

---

## CMD (Símbolo del sistema de Windows)

### 🟢 Primera vez (montar todo desde cero)

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 🔵 Siguientes veces (ya está todo instalado)

```cmd
.venv\Scripts\activate.bat
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## PowerShell (Windows)

### 🟢 Primera vez (montar todo desde cero)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

> ⚠️ Si al activar sale un error de **política de ejecución**
> (`... no se puede cargar porque la ejecución de scripts está deshabilitada`),
> ejecuta esto **una vez** en la misma ventana y vuelve a activar:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
>
> Esto permite ejecutar el script de activación **solo en esa ventana** (no
> cambia la configuración permanente de tu PC).

### 🔵 Siguientes veces (ya está todo instalado)

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Git Bash

### 🟢 Primera vez (montar todo desde cero)

```bash
py -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 🔵 Siguientes veces (ya está todo instalado)

```bash
source .venv/Scripts/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## ¿Qué hace cada comando? (explicado en simple)

| Comando | Qué hace |
|---|---|
| `py -m venv .venv` | **Crea** la carpeta `.venv` con un Python aislado para este proyecto. Solo se hace una vez. |
| `.venv\Scripts\activate.bat` (CMD) | **Activa** el entorno: a partir de aquí, `python` y `pip` apuntan al de `.venv`. |
| `.\.venv\Scripts\Activate.ps1` (PowerShell) | Igual que arriba, pero con la sintaxis de PowerShell. |
| `source .venv/Scripts/activate` (Git Bash) | Igual que arriba, pero con la sintaxis de Bash. |
| `pip install -r requirements.txt` | **Instala** las librerías que el proyecto necesita, listadas en `requirements.txt`. |
| `uvicorn main:app --host 0.0.0.0 --port 8000` | **Arranca** el servidor web. |
| `deactivate` | **Sale** del entorno virtual (vuelve al Python normal). Opcional. |

### Sobre el comando que arranca el servidor

`uvicorn main:app --host 0.0.0.0 --port 8000`

- `uvicorn` → el programa que corre el servidor.
- `main:app` → "en el archivo `main.py`, usa el objeto `app`" (la aplicación FastAPI).
- `--host 0.0.0.0` → escucha en **todas** las interfaces de red, no solo en tu
  PC. Esto es lo que permite que **otros equipos de la oficina** entren.
- `--port 8000` → el puerto por el que responde. Puedes cambiarlo (ej. `--port 8080`)
  si el 8000 está ocupado.

---

## ¿Cómo sé que arrancó bien? (URLs para entrar y compartir)

Apenas arranca, el servidor imprime en la consola algo así:

```
====================================================
  Servidor PruebaQQ en marcha
----------------------------------------------------
  Local (esta PC):     http://localhost:8000
  Red (oficina):       http://192.168.1.45:8000
====================================================
  Comparte la URL de 'Red' con los demas equipos de
  la oficina (deben estar en la misma red local).
```

- **URL Local** → ábrela en el navegador de **tu propia PC**.
- **URL de Red** → esa es la que **compartes** con los demás de la oficina. Usa
  la **IP de tu PC** como dirección; los otros equipos deben estar en la **misma
  red local** (mismo WiFi/cable) para poder entrar.

> La primera vez que arranques, Windows puede mostrar un aviso del **Firewall**
> pidiendo permiso de red. Acepta permitir el acceso en **redes privadas** para
> que los demás equipos puedan conectarse. (Más detalles y regla manual del
> firewall en el [README.md](README.md).)

---

## ¿Necesito el archivo `BD_Prueba.xlsx`?

**No es obligatorio.** Si el archivo `BD_Prueba.xlsx` no está en la carpeta, el
proyecto **genera datos aleatorios** automáticamente para poder funcionar y
demostrarse. Verás este aviso en la consola:

```
[analyzer] 'BD_Prueba.xlsx' no encontrado: usando datos aleatorios simulados.
```

Si más adelante colocas el archivo real en la carpeta, el proyecto lo usará solo,
sin cambiar nada.

---

## Para detener el servidor

En la misma terminal donde corre, pulsa **`Ctrl + C`**.

---

## Resumen ultra rápido

| | Primera vez | Siguientes veces |
|---|---|---|
| **CMD** | `py -m venv .venv` → `.venv\Scripts\activate.bat` → `pip install -r requirements.txt` → `uvicorn main:app --host 0.0.0.0 --port 8000` | `.venv\Scripts\activate.bat` → `uvicorn main:app --host 0.0.0.0 --port 8000` |
| **PowerShell** | `py -m venv .venv` → `.\.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt` → `uvicorn main:app --host 0.0.0.0 --port 8000` | `.\.venv\Scripts\Activate.ps1` → `uvicorn main:app --host 0.0.0.0 --port 8000` |
| **Git Bash** | `py -m venv .venv` → `source .venv/Scripts/activate` → `pip install -r requirements.txt` → `uvicorn main:app --host 0.0.0.0 --port 8000` | `source .venv/Scripts/activate` → `uvicorn main:app --host 0.0.0.0 --port 8000` |
