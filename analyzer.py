# Calcula, para cada planta de generación, qué tan variable ha sido su potencia
# reactiva en los últimos 20 minutos. Este es el único lugar donde se hace el
# análisis; main.py solo lo invoca y reparte el resultado (self.df) a los clientes.
import datetime as dt
import pandas as pd


class BehaviorAnalyzer():
    # Al crear el objeto se ejecuta todo el análisis de una vez: se cargan los
    # datos, se recorta la ventana de tiempo y se calcula el resultado final (self.df).
    def __init__(self):
        self.data = self.extract_data_from_excel()
        self.get_time_span()
        self.elements_analices = []
        self.analize_reactive_power()
        self.df = pd.DataFrame(self.elements_analices).sort_values(by='Varianza', ascending=False).reset_index()

    # Se queda solo con los registros de los últimos 20 minutos por planta.
    def get_time_span(self):
        now = dt.datetime.now()
        start_time = now - dt.timedelta(minutes=20)
        for gen_unit, data_df in self.data.items():
            # Filtro de los últimos 20 minutos
            data = data_df[data_df["Hora"].between(start_time.time(), now.time())]
            self.data[gen_unit] = data

    # Lee el Excel (una hoja por planta) y deja la columna "Hora" lista para comparar.
    # Esta es la única función que sabe de dónde vienen los datos: si mañana se
    # reemplaza el Excel por una base de datos, solo hay que cambiar esta función.
    def extract_data_from_excel(self):
        excel_data = {sheet: contend for sheet, contend in pd.read_excel("BD_Prueba.xlsx", sheet_name=None).items()}
        for gen_unit, data_df in excel_data.items():
            data_df["Hora"] = pd.to_datetime(data_df['Hora'], format='%H:%M:%S').dt.time
            excel_data[gen_unit] = data_df
        return excel_data

    # Calcula la varianza (qué tanto se aleja el valor de su promedio) y el valor
    # medio de potencia reactiva para una planta, usando integración simple (área bajo la curva).
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

    # Recorre cada planta y arma la lista de resultados (self.elements_analices)
    # que luego se convierte en el DataFrame final. Se ignoran plantas con muy
    # pocos registros (menos de 4) porque el cálculo no sería confiable.
    def analize_reactive_power(self):
        for gen_unit, generation_data in self.data.items():
            if len(generation_data) > 3:
                variation, medium_value = self.compute_variance(generation_data)
                self.elements_analices.append({
                    "PlantaGeneracion": gen_unit,
                    "Varianza": variation,
                    "ValorMedio": medium_value
                })
