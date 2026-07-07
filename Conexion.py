import datetime as dt
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class BehaviorAnalyzer():
    def __init__(self):
        self.data = self.extract_data_from_excel()
        self.get_time_span()
        self.elements_analices = []
        self.analize_reactive_power()
        self.df = pd.DataFrame(self.elements_analices).sort_values(by='Varianza', ascending=False).reset_index()

    def get_time_span(self):
        now = dt.datetime.now()
        start_time = now - dt.timedelta(minutes=20)
        for gen_unit, data_df in self.data.items():
            # Filtro de los últimos 20 minutos
            data = data_df[data_df["Hora"].between(start_time.time(), now.time())]
            self.data[gen_unit] = data

    def extract_data_from_excel(self):
        excel_data = {sheet: contend for sheet, contend in pd.read_excel("BD_Prueba.xlsx", sheet_name=None).items()}
        for gen_unit, data_df in excel_data.items():
            data_df["Hora"] = pd.to_datetime(data_df['Hora'], format='%H:%M:%S').dt.time
            excel_data[gen_unit] = data_df
        return excel_data

    def compute_variance(self, Q_df):
        Q_df["AreaQ"] = Q_df["Valor"] * Q_df["DeltaSeg"]
        QEnergy = Q_df["AreaQ"].sum()
        elapsed_seconds_time = ((Q_df["FechaHora"].iloc[0] - Q_df["FechaHora"].iloc[-1]) * (-1)).total_seconds()
        
        if elapsed_seconds_time == 0:  # Evitar división por cero
            return 0, 0
            
        medium_Q_value = QEnergy / elapsed_seconds_time
        Q_df["x-medio_x"] = abs(Q_df["Valor"] - medium_Q_value)
        prom_deltas = Q_df["x-medio_x"].mean()
        return round(prom_deltas, 2), round(medium_Q_value, 2)

    def analize_reactive_power(self):
        for gen_unit, generation_data in self.data.items():
            if len(generation_data) > 3:
                variation, medium_value = self.compute_variance(generation_data)
                self.elements_analices.append({
                    "PlantaGeneracion": gen_unit,
                    "Varianza": variation,
                    "ValorMedio": medium_value
                })


# ==========================================
# CONFIGURACIÓN DE LA GRÁFICA DINÁMICA
# ==========================================

# Estructura para almacenar el historial que se va a graficar
historial_tiempos = []
# Diccionario donde la clave es la 'PlantaGeneracion' y el valor es una lista con su historial de varianzas
historial_varianzas = {} 

fig, ax = plt.subplots(figsize=(10, 5))
plt.title("Análisis de Varianza en Tiempo Real")
plt.xlabel("Tiempo de Ejecución")
plt.ylabel("Varianza")
plt.grid(True)

def actualizar_grafica(frame):
    """Esta función se ejecuta automáticamente en cada intervalo de tiempo"""
    # 1. Instanciar la clase y ejecutar el cálculo actual
    analyzer = BehaviorAnalyzer()
    df_actual = analyzer.df
    
    if df_actual.empty:
        return
    
    # 2. Registrar el tiempo de ejecución actual
    tiempo_actual = dt.datetime.now().strftime("%H:%M:%S")
    historial_tiempos.append(tiempo_actual)
    
    # Mantener solo los últimos 20 registros en pantalla para no saturar la gráfica
    if len(historial_tiempos) > 20:
        historial_tiempos.pop(0)
        
    # 3. Limpiar los ejes para el nuevo redibujado, manteniendo títulos
    ax.clear()
    ax.set_title("Análisis de Varianza en Tiempo Real (Últimos 20 cálculos)")
    ax.set_xlabel("Tiempo de Ejecución")
    ax.set_ylabel("Varianza")
    ax.grid(True)
    
    # 4. Procesar los datos de cada planta en el DF actual
    for _, fila in df_actual.iterrows():
        planta = fila["PlantaGeneracion"]
        varianza = fila["Varianza"]
        
        # Si la planta es nueva, inicializar su lista de historial vacía
        if planta not in historial_varianzas:
            # Llenar con Nones/Ceros anteriores para alinear con el eje X si es necesario
            historial_varianzas[planta] = [0] * (len(historial_tiempos) - 1)
            
        historial_varianzas[planta].append(varianza)
        
        # Ajustar longitud del historial de la planta al tamaño del eje X
        if len(historial_varianzas[planta]) > len(historial_tiempos):
            historial_varianzas[planta].pop(0)
            
    # 5. Graficar las líneas de cada planta con sus respectivas Leyendas (Legends)
    for planta, valores in historial_varianzas.items():
        # Asegurar correspondencia de tamaños entre X e Y en plantas que entraron tarde al ciclo
        valores_graficar = valores[-len(historial_tiempos):]
        if len(valores_graficar) < len(historial_tiempos):
            valores_graficar = [0] * (len(historial_tiempos) - len(valores_graficar)) + valores_graficar
            
        ax.plot(historial_tiempos, valores_graficar, marker='o', label=planta)
    
    # 6. Mostrar leyendas dinámicas y rotar etiquetas del tiempo
    ax.legend(loc="upper left")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

# Crear la animación: Ejecuta 'actualizar_grafica' cada 3000 milisegundos (3 segundos)
# cache_frame_data=False evita advertencias de memoria en ejecuciones largas
ani = FuncAnimation(fig, actualizar_grafica, interval=3000, cache_frame_data=False)

# Mostrar la ventana interactiva
plt.show()
