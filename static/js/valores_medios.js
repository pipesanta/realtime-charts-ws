// Se conecta al mismo WebSocket (/ws) que la página de Varianza, pero en vez
// de guardar historial solo muestra el valor medio más reciente por planta (barras).
const estadoEl = document.getElementById("estado");
const graficaEl = document.getElementById("grafica");

// Gráfica de barras vacía al cargar; se reemplaza completa en cada mensaje del WebSocket.
Plotly.newPlot(graficaEl, [], {
    title: "Valor medio actual por planta",
    xaxis: { title: "Planta" },
    yaxis: { title: "Valor medio" },
    margin: { t: 40 },
});

// Ordena las plantas de mayor a menor valor medio y redibuja las barras.
function actualizarGrafica(registros) {
    const ordenados = [...registros].sort((a, b) => b.ValorMedio - a.ValorMedio);

    const traza = {
        x: ordenados.map((r) => r.PlantaGeneracion),
        y: ordenados.map((r) => r.ValorMedio),
        type: "bar",
        marker: { color: "#34d399" },
    };

    Plotly.react(graficaEl, [traza], {
        title: "Valor medio actual por planta",
        xaxis: { title: "Planta" },
        yaxis: { title: "Valor medio" },
        margin: { t: 40 },
    });
}

// Abre el WebSocket hacia el backend y reintenta solo si se desconecta.
function conectar() {
    const protocolo = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocolo}://${location.host}/ws`);

    ws.onopen = () => {
        estadoEl.textContent = "Conectado";
        estadoEl.className = "conectado";
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        actualizarGrafica(data.registros || []);
    };

    ws.onclose = () => {
        estadoEl.textContent = "Desconectado. Reintentando en 3s...";
        estadoEl.className = "desconectado";
        setTimeout(conectar, 3000);
    };

    ws.onerror = () => ws.close();
}

conectar();
