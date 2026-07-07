// Se conecta al WebSocket del servidor (/ws) y dibuja, con Plotly, cómo
// cambia la varianza de cada planta a lo largo del tiempo (últimos 20 puntos).
const MAX_PUNTOS = 20;

const historialTiempos = []; // horas mostradas en el eje X
const historialVarianzas = {}; // { planta: [valores de varianza en esas horas] }

const estadoEl = document.getElementById("estado");
const graficaEl = document.getElementById("grafica");

// Gráfica vacía al cargar la página; se va llenando cuando llegan datos por WebSocket.
Plotly.newPlot(graficaEl, [], {
    title: "Varianza por planta (últimos 20 cálculos)",
    xaxis: { title: "Hora de cálculo" },
    yaxis: { title: "Varianza" },
    margin: { t: 40 },
});

// Recibe la lista de plantas con su varianza actual (un "registro" del backend)
// y la agrega al historial de cada planta antes de volver a dibujar la gráfica.
// "hora" es la hora del cálculo en el servidor (para ubicar el punto en el eje X).
function actualizarGrafica(registros, hora) {
    const horaActual = hora || new Date().toLocaleTimeString("es-CO");
    historialTiempos.push(horaActual);
    if (historialTiempos.length > MAX_PUNTOS) {
        historialTiempos.shift();
    }

    const plantasRecibidas = new Set();

    for (const fila of registros) {
        const planta = fila["PlantaGeneracion"];
        const varianza = fila["Varianza"];
        plantasRecibidas.add(planta);

        if (!(planta in historialVarianzas)) {
            historialVarianzas[planta] = new Array(historialTiempos.length - 1).fill(null);
        }
        historialVarianzas[planta].push(varianza);
        if (historialVarianzas[planta].length > MAX_PUNTOS) {
            historialVarianzas[planta].shift();
        }
    }

    // Plantas que ya no reportan datos en este ciclo: rellenar con null para no romper el eje X.
    for (const planta in historialVarianzas) {
        if (!plantasRecibidas.has(planta)) {
            historialVarianzas[planta].push(null);
            if (historialVarianzas[planta].length > MAX_PUNTOS) {
                historialVarianzas[planta].shift();
            }
        }
    }

    const trazas = Object.entries(historialVarianzas).map(([planta, valores]) => {
        const inicio = Math.max(0, valores.length - historialTiempos.length);
        return {
            x: historialTiempos,
            y: valores.slice(inicio),
            mode: "lines+markers",
            name: planta,
        };
    });

    Plotly.react(graficaEl, trazas, {
        title: "Varianza por planta (últimos 20 cálculos)",
        xaxis: { title: "Hora de cálculo" },
        yaxis: { title: "Varianza" },
        margin: { t: 40 },
    });
}

// Abre el WebSocket hacia el backend. Cada mensaje que llega es un nuevo
// cálculo (cada 3s); si la conexión se cae, reintenta sola cada 3 segundos.
function conectar() {
    const protocolo = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocolo}://${location.host}/ws`);

    ws.onopen = () => {
        estadoEl.textContent = "Conectado";
        estadoEl.className = "conectado";
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        actualizarGrafica(data.registros || [], data.hora);
    };

    ws.onclose = () => {
        estadoEl.textContent = "Desconectado. Reintentando en 3s...";
        estadoEl.className = "desconectado";
        setTimeout(conectar, 3000);
    };

    ws.onerror = () => ws.close();
}

conectar();
