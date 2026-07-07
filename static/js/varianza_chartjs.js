// Misma idea que varianza.js (historial de varianza por planta vía WebSocket),
// pero dibujado con Chart.js en vez de Plotly, para comparar ambas librerías.
const MAX_PUNTOS = 20;

const historialTiempos = []; // horas mostradas en el eje X
const datasetsPorPlanta = {}; // { planta: dataset de Chart.js con su historial }
const COLORES = ["#34d399", "#60a5fa", "#f87171", "#fbbf24", "#a78bfa", "#f472b6", "#38bdf8", "#facc15"];
let colorIndex = 0; // va rotando para asignar un color distinto a cada planta nueva

const estadoEl = document.getElementById("estado");
const ctx = document.getElementById("grafica").getContext("2d");

// Gráfica de líneas vacía al cargar la página (sin datasets todavía).
const chart = new Chart(ctx, {
    type: "line",
    data: { labels: historialTiempos, datasets: [] },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "nearest", axis: "x", intersect: false },
        scales: {
            x: {
                title: { display: true, text: "Hora de cálculo", color: "#e5e7eb" },
                ticks: { color: "#9ca3af" },
                grid: { color: "#374151" },
            },
            y: {
                title: { display: true, text: "Varianza", color: "#e5e7eb" },
                ticks: { color: "#9ca3af" },
                grid: { color: "#374151" },
            },
        },
        plugins: {
            legend: { labels: { color: "#e5e7eb" } },
        },
    },
});

// Recibe la lista de plantas con su varianza actual, la agrega al historial
// de cada planta (creando su dataset si es la primera vez que aparece) y
// pide a Chart.js que redibuje (chart.update()).
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

        if (!(planta in datasetsPorPlanta)) {
            const color = COLORES[colorIndex % COLORES.length];
            colorIndex++;
            const dataset = {
                label: planta,
                data: new Array(historialTiempos.length - 1).fill(null),
                borderColor: color,
                backgroundColor: color,
                tension: 0.2,
                spanGaps: true,
            };
            datasetsPorPlanta[planta] = dataset;
            chart.data.datasets.push(dataset);
        }
        datasetsPorPlanta[planta].data.push(varianza);
    }

    for (const planta in datasetsPorPlanta) {
        const dataset = datasetsPorPlanta[planta];
        if (!plantasRecibidas.has(planta)) {
            dataset.data.push(null);
        }
        if (dataset.data.length > MAX_PUNTOS) {
            dataset.data.shift();
        }
    }

    chart.update();
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
