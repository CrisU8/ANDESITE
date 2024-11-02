import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Rendimiento de Camiones",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Activar tema oscuro en Altair
alt.themes.enable("dark")

# Cargar y procesar datos
df = pd.read_csv("./data/timeseries_data_cleaned.csv", parse_dates=['date'])
df_1 = df.groupby(["truck", "date"]).agg(
    total_ton_per_day=('ton', 'sum'),
    loads_per_day=('ton', 'count'),
    count_ph06=('loader', lambda x: (x == 'PH06').sum()),
    count_ph48=('loader', lambda x: (x == 'PH48').sum()),
    count_ph55=('loader', lambda x: (x == 'PH55').sum()),
    count_ph58=('loader', lambda x: (x == 'PH58').sum()),
    avg_distance_empty=('distance_empty', 'mean'),
    avg_distance_full=('distance_full', 'mean'),
    avg_truck_total_cycle=('truck_total_cycle', 'mean'),
    avg_load_cycle=('loader_total_cycle', 'mean'),
    avg_ton_per_shovel=('ton_per_shovel', 'mean'),
    avg_speed=('speed', 'mean')
).reset_index()

# Configuración de la barra lateral
with st.sidebar:
    st.title('🚛 Dashboard de Rendimiento de Camiones')

    year_list = list(df.date.dt.year.unique())[::-1]
    month_list = list(df.date.dt.month.unique())[::-1]

    selected_year = st.selectbox('Selecciona un año', year_list, index=len(year_list) - 1)
    selected_month = st.selectbox('Selecciona un mes', month_list, index=len(month_list) - 1)
    df_selected_year = df_1[(df_1.date.dt.year == selected_year) & (df_1.date.dt.month == selected_month)]

# Gráficos de HEATMAP y RANKING
HEATMAP = px.density_heatmap(
    df_selected_year,
    x="date",
    y="truck",
    z="total_ton_per_day",
    color_continuous_scale="Viridis",
    labels={'total_ton_per_day': 'Total ton', 'truck': 'Truck', 'date': 'Date'},
    title="Distribución de Tonelaje Diario por Camión"
)

average_per_truck = df_selected_year.groupby('truck').agg(
    average_daily_ton=('total_ton_per_day', 'mean'),
    average_daily_loads=('loads_per_day', 'mean'),
    average_daily_distance_empty=('avg_distance_empty', 'mean'),
    average_daily_distance_full=('avg_distance_full', 'mean')
).reset_index()

# Ordenar según el promedio de toneladas diarias
average_per_truck = average_per_truck.sort_values(by='average_daily_ton', ascending=True)

RANKING = px.bar(
    average_per_truck,
    x='average_daily_ton',
    y='truck',
    orientation='h',
    title='Average Daily Ton per Truck',
    labels={'average_daily_ton': 'Average Daily Ton', 'truck': 'Truck'},
    color='average_daily_ton',
    color_continuous_scale='Viridis'
)

# Calcular métricas clave
speed_avg = df_selected_year.avg_speed.mean()
distance_empty = df_selected_year.avg_distance_empty.mean()
distance_full = df_selected_year.avg_distance_full.mean()
ton_per_shovel_efficiency = (1 - (120 / df_selected_year.avg_ton_per_shovel.mean())) if df_selected_year.avg_ton_per_shovel.mean() != 0 else 0
loader_time_avg = df_selected_year.avg_load_cycle.mean()

# DataFrame de eficiencia de palas
df['ton_per_shovel'] = df['ton']/df['n_shovel']
df_loader_efficiency = df.groupby('loader').agg(
    avg_cycle_time=('loader_total_cycle', 'mean'),
    avg_ton_per_shovel=('ton_per_shovel','mean')).reset_index()

# Configurar las columnas
col = st.columns((1.5, 4.5, 2), gap='medium')

# Columna izquierda: métricas clave y eficiencia de ton_per_shovel
with col[0]:
    st.markdown("#### Métricas clave")

    st.metric("Velocidad Promedio", f"{speed_avg:.1f} km/h")
    st.metric("Distancia Vacío Promedio", f"{distance_empty:.0f} km")
    st.metric("Distancia Llena Promedio", f"{distance_full:.0f} km")
    st.metric("Tiempo de Carga Promedio", f"{loader_time_avg:.1f} seg")

    import altair as alt

    ton_per_shovel_efficiency_percentage = round(ton_per_shovel_efficiency * 100, 2)


    # Función para crear el gráfico de dona
    def make_donut(input_response, input_text, input_color):
        if input_color == 'blue':
            chart_color = ['#29b5e8', '#155F7A']
        elif input_color == 'green':
            chart_color = ['#27AE60', '#12783D']
        elif input_color == 'orange':
            chart_color = ['#F39C12', '#875A12']
        elif input_color == 'red':
            chart_color = ['#E74C3C', '#781F16']
        else:
            chart_color = ['#CCCCCC', '#666666']

        source = pd.DataFrame({
            "Topic": ['', input_text],
            "% value": [100 - input_response, input_response]
        })
        source_bg = pd.DataFrame({
            "Topic": ['', input_text],
            "% value": [100, 0]
        })

        plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=45, cornerRadius=20).encode(
            theta="% value",
            color=alt.Color("Topic:N", scale=alt.Scale(domain=[input_text, ''], range=chart_color), legend=None)
        ).properties(width=130, height=130)

        plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=25).encode(
            theta="% value",
            color=alt.Color("Topic:N", scale=alt.Scale(domain=[input_text, ''], range=chart_color), legend=None)
        ).properties(width=130, height=130)

        text = plot.mark_text(
            align='center',
            color=chart_color[0],
            font="Lato",
            fontSize=32,
            fontWeight=700,
            fontStyle="italic"
        ).encode(text=alt.value(f'{input_response} %'))

        return plot_bg + plot + text


    # Determinar el color del gráfico de acuerdo con el nivel de eficiencia
    efficiency_color = 'green' if ton_per_shovel_efficiency < 0.2 else 'orange' if ton_per_shovel_efficiency < 0.4 else 'red'

    # Mostrar el gráfico de dona en Streamlit
    st.markdown("#### Eficiencia de Tonelaje por Palada")
    st.altair_chart(make_donut(ton_per_shovel_efficiency_percentage, "Eficiencia", efficiency_color),
                    use_container_width=True)

# Columna central: gráficos de ranking y distribución de tonelaje
with col[1]:
    st.plotly_chart(RANKING, use_container_width=True)
    st.plotly_chart(HEATMAP, use_container_width=True)

# Columna derecha: tabla de eficiencia de palas
with col[2]:
    st.subheader("Eficiencia de Palas")

    st.dataframe(
        df_loader_efficiency,
        column_order=("loader", "avg_cycle_time", "avg_ton_per_shovel"),
        hide_index=True,
        use_container_width=True)
