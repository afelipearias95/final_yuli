import dash
import pandas as pd
import plotly.graph_objs as go
import plotly.express as px
import plotly.io as pio # Importa el tema oscuro de Plotly
import pytz
import dash_leaflet as dl
import dash_leaflet.express as dlx
from dash import dcc, html
from datetime import datetime
from dash.dependencies import Input, Output
import calendar
from utils import (
    get_database_connection,
    obtener_numero_de_pozos,
    generate_data_card,
    get_last_updated_time,
)

external_stylesheets = [
    'https://fonts.googleapis.com/css?family=Lato',
    '/assets/style.css',
]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# SECCION DE CONEXIONES Y CONSULTAS MYSQL
# ---------------------------------------------------------------------------------------------------------------------------------------------------

# Conexión con el servidor MySQL
conexion = get_database_connection()

# Consulta SQL para obtener los datos sumados por mes
query = """SELECT 
    YEAR(Date) AS Año,
    MONTH(Date) AS Mes,
    SUM(Presion_intake) AS Suma_Presion_intake,
    SUM(Freq) AS Suma_Freq,
    SUM(Caudal) AS Suma_Caudal,
    SUM(WOR) AS Suma_WOR,
    SUM(WCUT) AS Suma_WCUT,
    SUM(BWPD) AS Suma_BWPD,
    SUM(BOPD) AS Suma_BOPD
FROM critical_var_2
GROUP BY Año, Mes
"""

# Leer los datos desde MySQL y crear un DataFrame
df = pd.read_sql(query, conexion)

# Consulta SQL para obtener los datos

query_var_3 = """
SELECT a.Well_Id,
	   YEAR(Volume_Date) AS Año,
       MONTH(Volume_Date) AS Mes,
       SUM(Oil) AS Suma_Oil,
       SUM(Gas) AS Suma_Gas,
       b.UWI
FROM data_diaria_volumetrica_updated a
JOIN wells_master_updated b
ON a. Well_Id = b. Well_Id
GROUP BY UWI, Mes, Año
"""

query_tarjetas_var_2 = "SELECT Caudal, WOR FROM Critical_Variables_Updated"
query_tarjetas_var_3 = "SELECT Hours, Oil, Water, Gas FROM data_diaria_volumetrica_updated"

querymap = "SELECT UWI, Geo_latitude, Geo_longitude, Wellhead_depth FROM wells_master_updated"

# Obtener datos
df_query_var_3 = pd.read_sql(query_var_3, conexion)
df_var_2 = pd.read_sql(query_tarjetas_var_2, conexion)
df_var_3 = pd.read_sql(query_tarjetas_var_3, conexion)

# Obtener datos de producción de Oil y Gas por cada Well_Id
well_production_data = df_query_var_3

df_map = pd.read_sql(querymap, conexion)

# Obtener la hora actual en Colombia
colombia_tz = pytz.timezone('America/Bogota')
formatted_time = get_last_updated_time(colombia_tz)

# Obtener el número de pozos
numero_de_pozos = obtener_numero_de_pozos(conexion)

# Consulta SQL para obtener las sumas agrupadas por "Well Id"
query_sumas_por_pozo = """
SELECT a.Well_Id,
       SUM(Gas) AS Total_Gas_Pozo,
       SUM(Oil) AS Total_Oil_Pozo,
       SUM(Water) AS Total_Water_Pozo,
       b.UWI,
       b.Geo_latitude,
       b.Geo_longitude,
       b.Sistema_Levantamiento,
       b.Purpose
FROM data_diaria_volumetrica_updated a
JOIN wells_master_updated b
ON a. Well_Id = b. Well_Id
GROUP BY Well_Id
"""

# Ejecutar la consulta SQL y cargar los resultados en un DataFrame
df_sumas_por_pozo = pd.read_sql(query_sumas_por_pozo, conexion)

# Calcular las proporciones por pozo
df_sumas_por_pozo['Proporcion_Gas_Pozo'] = (df_sumas_por_pozo['Total_Gas_Pozo'] / (df_sumas_por_pozo['Total_Gas_Pozo'] + df_sumas_por_pozo['Total_Oil_Pozo'] + df_sumas_por_pozo['Total_Water_Pozo'])) * 100
df_sumas_por_pozo['Proporcion_Oil_Pozo'] = (df_sumas_por_pozo['Total_Oil_Pozo'] / (df_sumas_por_pozo['Total_Gas_Pozo'] + df_sumas_por_pozo['Total_Oil_Pozo'] + df_sumas_por_pozo['Total_Water_Pozo'])) * 100
df_sumas_por_pozo['Proporcion_Water_Pozo'] = (df_sumas_por_pozo['Total_Water_Pozo'] / (df_sumas_por_pozo['Total_Gas_Pozo'] + df_sumas_por_pozo['Total_Oil_Pozo'] + df_sumas_por_pozo['Total_Water_Pozo'])) * 100

def generate_pie_chart(row, text_size=11):
    labels = ['Gas', 'Oil', 'Water']
    values = [row['Total_Gas_Pozo'], row['Total_Oil_Pozo'], row['Total_Water_Pozo']]
    colors = ['#663366', '#FF6633', '#0099FF']  # Colores personalizados: morado, naranja y azul

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        marker=dict(colors=colors),
        textinfo='label+percent',  # Muestra etiquetas y porcentaje
        textfont=dict(size=text_size, family='Arial, sans-serif', color='black'),  # Configura la fuente del texto
    )])

    fig.update_layout(
        showlegend=False,  # Oculta la leyenda
        margin=dict(l=0, r=0, t=0, b=0),  # Ajusta los márgenes
        width=150,  # Ajusta el ancho del gráfico
        height=150,  # Ajusta la altura del gráfico
    )

    return dcc.Graph(figure=fig, config={'displayModeBar': False})

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# SECCION DE GRAFICAS Y TARJETAS
# ---------------------------------------------------------------------------------------------------------------------------------------------------

# Estilos comunes de las gráficas de dispersión
common_style = {
    'display': 'inline-block',
    'backgroundColor': '#000000',
    'width': '45%',
    'height': '350px',
    'color': 'white',
}

# Profundidad de pozos

def trajectory_wells(df_map):
    wellhead_depth = df_map['Wellhead_depth']
    geo_longitude = df_map['Geo_longitude']
    geo_latitude = df_map['Geo_latitude']
    uwi_list = df_map['UWI']
    wellhead_depth_invertido = [-depth for depth in wellhead_depth]

    fig = go.Figure()

    colors_UWIS = {
        'Well001': 'rgba(67, 160, 71, 0.6)',
        'Well002': 'rgba(188, 170, 164, 1)',
        'Well004': 'rgba(0, 204, 255, 0.2)',
        'Well005': 'rgba(183, 28, 28, 0.4)',
        'Well006': 'rgba(255, 87, 34, 0.3)',
        'Well007': 'rgba(186, 104, 200, 0.2)',
        'Well008': 'rgba(255, 255, 157, 0.5)',
        'Well009': 'rgba(204, 153, 255, 0.2)',
        'Well010': 'rgba(102, 255, 204, 0.6)',
        'Well012': 'rgba(204, 255, 204, 1)',
        'Well013': 'rgba(255, 255, 204, 0.2)',
        'Well014': 'rgba(255, 255, 153, 0.2)',
        'Well015': 'rgba(255, 153, 204, 0.6)',
        'Well016': 'rgba(153, 204, 102, 0.4)',
        'Well017': 'rgba(153, 153, 204, 1)',
        'Well018': 'rgba(97, 97, 97, 0.6)',
        'Well019': 'rgba(141, 110, 99, 0.6)'
    }

    for i in range(len(wellhead_depth)):
        fig.add_trace(go.Scatter3d(
            x=[geo_longitude[i]],
            y=[geo_latitude[i]],
            z=[0],
            mode='markers+text',
            marker=dict(
                size=5,
                color=colors_UWIS.get(uwi_list[i], 'rgba(0, 0, 0, 0.6)'),
                opacity=1
            ),
            textposition='bottom center',
            showlegend=True,
            name=uwi_list[i]
        ))

    for i in range(len(wellhead_depth)):
        fig.add_trace(go.Scatter3d(
            x=[geo_longitude[i], geo_longitude[i]],
            y=[geo_latitude[i], geo_latitude[i]],
            z=[0, wellhead_depth_invertido[i]],
            mode='lines+text',
            line=dict(
                color=colors_UWIS.get(uwi_list[i], 'rgba(0, 0, 0, 0.6)'),
                width=2
            ),
            showlegend=False,
            name=uwi_list[i]
        ))

    fig.update_scenes(
        aspectmode='cube'
    )

    fig.update_layout(
        scene=dict(
            xaxis_title='Long',
            yaxis_title='Lat',
            zaxis_title='Depth'
        ),
        scene_camera=dict(
            up=dict(x=0, y=0, z=1),
            center=dict(x=0, y=0, z=0),
            eye=dict(x=1.5, y=1.5, z=0)
        ),
        template="plotly_dark",
        margin=dict(l=0, r=0, b=0, t=20),
        height=300,
        width=400,
        legend=dict(
            font=dict(size=10),
            x=0.7,  # Ajusta la posición horizontal de la leyenda
            y=0.4,   # Ajusta la posición vertical de la leyenda
        ),
        plot_bgcolor='#000000',
        paper_bgcolor='#000000'
    )

    return fig

# Crea una lista de elementos que deseas incluir en wells_depth_card
wells_depth_children = [
    html.Div(
        "Wells Trajectory",
        style={
            'paddingTop': '10px',
            'textAlign': 'center',
            'align-content': 'center',
            'color': 'white',
            'borderBottom': '1px solid white',
            'paddingBottom': '10px',
            'fontWeight': 'bold',
        },
    ),
    html.Div(
        dcc.Graph(
            figure=trajectory_wells(df_map),
            config={
                'displayModeBar': True  # Asegúrate de que displayModeBar esté configurado como True
            }
        ),
        # style={'maxHeight': '300px', 'overflowY': 'auto'}  # Establece una altura máxima y activa la barra de desplazamiento vertical
    ),
]

# Ahora, crea wells_depth_card y pasa la lista de children
wells_depth_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=wells_depth_children,
)


def create_map():

    # Diccionario de mapeo de sistemas de levantamiento a iconos
    sistema_icon_mapping = {
        'BES': 'assets/ESP.png',
        'BME': 'assets/BM.png',
        'GAS LIFT': 'assets/GASLIFT.png',
        'PCP': 'assets/PCP.png'
    }

    # Crea el mapa y los marcadores
    map_ = dl.Map(
        center=[5.533995902516049, -73.35830183000226],
        zoom=6.49,  # Nivel de zoom
        children=[
            dl.TileLayer(url='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png')
        ],
        style={'width': '400px', 'height': '300px'}
    )

    # Agrega marcadores para cada pozo en el DataFrame df_sumas_por_pozo
    for _, row in df_sumas_por_pozo.iterrows():  # Utiliza df_sumas_por_pozo en lugar de df_map
        sistema_levantamiento = row['Sistema_Levantamiento']
        purpose = row['Purpose']

        # Obtiene la ruta del icono basado en el sistema de levantamiento
        icon_url = sistema_icon_mapping.get(sistema_levantamiento, 'assets/icono_pozo6.png')

        custom_icon = {
            'iconUrl': icon_url,  # Usa la ruta del icono correspondiente
            'iconSize': [45, 45],  # Tamaño del icono personalizado (ajusta según tus necesidades)
        }

        # Crea el texto para el tooltip con UWI y Purpose
        tooltip_text = f'*UWI: {row["UWI"]}, *Purpose: {purpose}'

        # Crea el marcador con el icono personalizado y el tooltip modificado
        marker = dl.Marker(
            position=[row['Geo_latitude'], row['Geo_longitude']],
            icon=custom_icon,
            children=[
                dl.Tooltip(tooltip_text, direction='top'),  # Muestra UWI y Purpose en el tooltip
                dl.Popup(html.Div([generate_pie_chart(row)]))
            ]
        )

        # Agrega todos los marcadores al mapa usando la propiedad 'children'
        map_.children.append(marker)

    return map_

# Agrega el título de la tarjeta aquí
wells_location_card = html.Div(
    style={'height': '350px', 'width': '60%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Wells Location",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        create_map(),  # Inserta el mapa directamente después del título
    ],
)

def barrel_price():
    return html.Iframe(src="https://www.preciopetroleo.net/productos/tv-brent.html", height="460px", width="410px",
        style={'transform': 'scale(0.75)'})

# Agrega el título de la tarjeta aquí
Barrel_price_realtime_card = html.Div(
    style={'height': '400px', 'textAlign': 'center', 'border-radius': '10px', 'box-shadow': '0px 0px 5px 2px rgba(255, 255, 255, 0.2)', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Barrel Price Real Time (BRENT/WTI)",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        html.Div(  # Contenedor para el iframe con margen superior
            barrel_price(),
            style={'marginTop': '-50px', 'marginLeft': '-46px'}
        ),
    ],
)

def presion_caudal_graph(df):
    figure = {
        'data': [
            go.Scatter(
                x=df['Suma_Presion_intake'],
                y=df['Suma_Caudal'],
                mode='markers',
                marker=dict(
                    size=8,
                    symbol='circle',
                    color='#0066FF',
                    line=dict(
                        width=0.4,
                        color='#212121'
                    )
                ),
                text=df['Mes'],
            )
        ],
        'layout': go.Layout(
            xaxis={'title': 'Presion_Intake', 'color': 'white'},
            yaxis={'title': 'Caudal', 'color': 'white'},
            hovermode='closest',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            margin=dict(l=50, r=0, b=50, t=20),
            height=300,
            width=400
        )
    }

    return dcc.Graph(
        id='presion-caudal-graph',
        config={'displayModeBar': True},
        style={'display': 'inline-block',
            'backgroundColor': '#000000',
            'color': 'white',},
        figure=figure
    )

def freq_caudal_graph(df):
    figure = {
        'data': [
            go.Scatter(
                x=df['Suma_Freq'],
                y=df['Suma_Caudal'],
                mode='markers',
                marker=dict(
                    size=8,
                    symbol='circle',
                    color='#0066FF',
                    line=dict(
                        width=0.4,
                        color='#212121'
                    ),
                ),
                text=df['Mes'],
            )
        ],
        'layout': go.Layout(
            xaxis={'title': 'Freq', 'color': 'white'},
            yaxis={'title': 'Caudal', 'color': 'white'},
            hovermode='closest',
            plot_bgcolor='#000000',
            paper_bgcolor='#000000',
            margin=dict(l=50, r=0, b=50, t=20),
            height=300,
            width=400
        )
    }

    return dcc.Graph(
        id='freq-caudal-graph',
        config={'displayModeBar': True},
        style={'display': 'inline-block',
            'backgroundColor': '#000000',
            'color': 'white'},
        figure=figure
    )

# Agrega el título de la tarjeta aquí
presion_caudal_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Intake Pressure vs Flow",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        presion_caudal_graph(df),  # Inserta el mapa directamente después del título
    ],
)

# Agrega el título de la tarjeta aquí
freq_caudal_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Frequency vs Flow",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        freq_caudal_graph(df),  # Inserta el mapa directamente después del título
    ],
)

# Define un diccionario de colores para WCUT y WOR por año
custom_colors_wcut = {
    2021: 'rgba(188, 170, 164, 0.2)', #gris
    2022: 'rgba(0, 204, 255, 0.3)', #azul
    2023: 'rgba(186, 104, 200, 0.2)', #morado
}

custom_colors_wor = {
    2021: 'rgba(255, 255, 157, 0.4)', #amarillo
    2022: 'rgba(255, 87, 34, 0.6)', #naranja
    2023: 'rgba(183, 28, 28, 1)', #rojo
}

# Agrupar los datos por año y mes
df_grouped = df.groupby(['Año', 'Mes']).agg({
    'Suma_WCUT': 'mean',  # Puedes usar 'mean', 'sum', o cualquier otra función de agregación que necesites
    'Suma_WOR': 'mean'
}).reset_index()

# Obtener la lista de años en tus datos
años = df_grouped['Año'].unique()

# Función para crear gráficas de WCUT/WOR
def create_wc_wor_graph(df_grouped, custom_colors_wcut, custom_colors_wor):
    años = df_grouped['Año'].unique()
    traces = []

    for año in años:
        data_año = df_grouped[df_grouped['Año'] == año]
        trace_wcut = go.Scatter(
            x=data_año['Mes'],
            y=data_año['Suma_WCUT'],
            mode='lines',
            name=f'WCUT {año}',
            line=dict(
                width=2,
                color=custom_colors_wcut.get(año, '#000033')  # Puedes personalizar los colores aquí
            )
        )
        trace_wor = go.Scatter(
            x=data_año['Mes'],
            y=data_año['Suma_WOR'],
            mode='lines',
            name=f'WOR {año}',
            line=dict(
                width=2,
                color=custom_colors_wor.get(año, '#3366CC')  # Puedes personalizar los colores aquí
            )
        )
        traces.append(trace_wcut)
        traces.append(trace_wor)

    wc_wor_graph = dcc.Graph(
        id='wc-wor-graph',
        config={'displayModeBar': True},
        style={
            'display': 'inline-block',
            'backgroundColor': '#000000',
            'width': '400px',
            'height': '300px',
            'color': 'white',
            'align-items': 'center',
        },
        figure={
            'data': traces,
            'layout': go.Layout(
                xaxis={'title': 'Month', 'color': 'white', 'titlefont': {'size': 12}, 'tickfont': {'size': 9}},
                yaxis={'title': 'Units', 'color': 'white', 'titlefont': {'size': 12}, 'tickfont': {'size': 9}},
                hovermode='closest',
                plot_bgcolor='#000000',
                paper_bgcolor='#000000',
                margin=dict(l=50, r=0, b=20, t=20),
                height=300,
                legend=dict(
                    font=dict(
                        size=9
                    )
                ),
            )
        }
    )

    return wc_wor_graph

# Define un diccionario de colores para BOPD y BWPD por año
colors_bopd = {
    2021: 'rgba(188, 170, 164, 0.2)', #gris
    2022: 'rgba(0, 204, 255, 0.3)', #azul
    2023: 'rgba(186, 104, 200, 0.2)', #morado
}

colors_bwpd = {
    2021: 'rgba(255, 255, 157, 0.4)', #amarillo
    2022: 'rgba(255, 87, 34, 0.6)', #naranja
    2023: 'rgba(183, 28, 28, 1)', #rojo
}


# Función para crear gráficas de BOPD/BWPD
def create_bopd_bwpd_graph(df, colors_bopd, colors_bwpd):
    años = df['Año'].unique()
    traces_bopd_bwpd = []

    for año in años:
        data_año = df[df['Año'] == año]
        trace_bopd = go.Scatter(
            x=data_año['Mes'],
            y=data_año['Suma_BOPD'],
            mode='lines',
            name=f'BOPD {año}',
            line=dict(
                width=2,
                color=colors_bopd.get(año, '#9966CC')  # Usar el color del diccionario, o un color predeterminado
            )
        )
        trace_bwpd = go.Scatter(
            x=data_año['Mes'],
            y=data_año['Suma_BWPD'],
            mode='lines',
            name=f'BWPD {año}',
            line=dict(
                width=2,
                color=colors_bwpd.get(año, '#009966')  # Usar el color del diccionario, o un color predeterminado
            )
        )
        traces_bopd_bwpd.append(trace_bopd)
        traces_bopd_bwpd.append(trace_bwpd)

    bopd_bwpd_graph = dcc.Graph(
        id='bopd-bwpd-graph',
        config={'displayModeBar': True},
        style={
            'display': 'inline-block',
            'backgroundColor': '#000000',
            'width': '400px',
            'height': '300px',
            'color': 'white',
            'align-items': 'center',
        },
        figure={
            'data': traces_bopd_bwpd,
            'layout': go.Layout(
                xaxis={'title': 'Month', 'color': 'white', 'titlefont': {'size': 12}, 'tickfont': {'size': 9}},
                yaxis={'title': 'Units', 'color': 'white', 'titlefont': {'size': 12}, 'tickfont': {'size': 9}},
                hovermode='closest',
                plot_bgcolor='#000000',
                paper_bgcolor='#000000',
                margin=dict(l=50, r=0, b=20, t=20),
                height=300,
                legend=dict(
                    font=dict(
                        size=9
                    )
                ),
            )
        }
    )

    return bopd_bwpd_graph

# Agrega el título de la tarjeta aquí
wc_wor_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "WC vs WOR",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        create_wc_wor_graph(df_grouped, custom_colors_wcut, custom_colors_wor),  # Pasar los argumentos aquí
    ],
)

# Agrega el título de la tarjeta aquí
bopd_bwpd_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "BOPD vs BWPD",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        create_bopd_bwpd_graph(df, colors_bopd, colors_bwpd),  # Pasar los argumentos aquí
    ],
)

def format_month_year(year_month):
    year, month = map(int, year_month.split('-'))
    month_name = calendar.month_abbr[month]
    return f"{month_name}/{str(year)[-2:]}"

# Función para formatear los valores en K (miles) o M (millones)
def format_yaxis(y):
    if y >= 1e6:
        return f'{y / 1e6:.0f}M'
    elif y >= 1e3:
        return f'{y / 1e3:.0f}K'
    else:
        return str(int(y))  # Mostrar valores enteros para valores menores a 1,000
    

def oil_production(well_production_data):
    well_production_data_sorted = well_production_data.sort_values(by=['UWI', 'Mes'])
    well_production_data_sorted['YearMonth'] = well_production_data_sorted['Año'].astype(str) + '-' + well_production_data_sorted['Mes'].astype(str)
    oil_data = well_production_data_sorted[['UWI', 'YearMonth', 'Suma_Oil', 'Well_Id']]

    custom_colors_oil = {
    'D0A25FCC-4989-4D49-86C1-CAA92F1B3001': 'rgba(67, 160, 71, 0.6)',  # Color verde
    'D0A25FCC-4989-4D49-86C1-CDA92F1B3002': 'rgba(188, 170, 164, 1)',  # Color gris
    'D0A25FCC-4989-4D49-86C1-CDA92F1B3004': 'rgba(0, 204, 255, 0.2)',  # Color azul
    'D0A25FCC-4989-4D49-86C1-CDA92F1B3005': 'rgba(183, 28, 28, 0.4)',  # Color rojo
    'D0A25FCC-4989-4D49-86C1-CKA92F1B3006': 'rgba(255, 87, 34, 0.3)',  # Color naranja
    'D0A25FCC-4989-4D49-86C1-CPA92F1B3007': 'rgba(186, 104, 200, 0.2)',  # Color morado
    'D0A25FCC-4989-4D49-86C1-CDA92F1B3008': 'rgba(255, 255, 157, 0.5)',  # Color amarillo
    'D0A25FCC-4989-4D49-86C1-CMN92F1B3009': 'rgba(204, 153, 255, 0.2)', # color lila
    '54E7CE87-3AC7-49B2-B794-5730BE7C97010': 'rgba(102, 255, 204, 0.6)', # color celeste
    '971F0184-A90B-4029-99E4-F81C5FAB82012': 'rgba(204, 255, 204, 1)', # ccolor menta
    'F95DACDF-1568-4F15-95BF-DE04D3D26013': 'rgba(255, 255, 204, 0.2)', # color piel claro
    'D0A25FCC-4989-4D49-86C1-JKT92F1B3014': 'rgba(255, 255, 153, 0.2)', # color amarillo claro pastel
    'D0A25FCC-4989-4D49-86C1-CDF92F1B3015': 'rgba(255, 153, 204, 0.6)', # color rosado
    'D0A25FCC-4989-4D49-86C1-CAA92F1B3016': 'rgba(153, 204, 102, 0.4)', # color guayabo
    'D0A25FCC-4989-4D49-86C1-CDA92F1B3017': 'rgba(153, 153, 204, 1)', # color azul morado
    'D0A25FCC-4989-4D49-86C1-CDA92F1B3018': 'rgba(97, 97, 97, 0.6)', # color gris oscuro
    'D0A25FCC-4989-4D49-86C1-CDY92F1B3019': 'rgba(141, 110, 99, 0.6)' # color marrón claro
    }

    traces_oil = []

    for well_id, data in oil_data.groupby('Well_Id'):
        uwi = data['UWI'].iloc[0]

        trace_oil = go.Scatter(
            x=data['YearMonth'],
            y=data['Suma_Oil'],
            mode='lines+markers',
            line=dict(color=custom_colors_oil.get(well_id, 'rgba(0, 0, 0, 1)')),
            name=str(uwi),
            fill='tozeroy',
            fillcolor=custom_colors_oil.get(well_id, 'rgba(0, 0, 1, 1)')
        )
        traces_oil.append(trace_oil)

    all_year_months = sorted(well_production_data_sorted['YearMonth'].unique())

    xaxis_labels = [format_month_year(year_month) for year_month in all_year_months]

    max_oil_production = well_production_data_sorted['Suma_Oil'].max()
    max_range_oil = 1000 * ((int(max_oil_production) // 1000) + 1)

    y_tickvals = [0]
    y_ticktext = ['0']
    for i in range(1000, max_range_oil + 1, 1000):
        y_tickvals.append(i)
        y_ticktext.append(f'{i / 1000:.0f}K')

    layout_oil = go.Layout(
        xaxis={'title': 'Month-Year', 'color': 'white', 'tickvals': all_year_months, 'ticktext': xaxis_labels,
               'titlefont': {'size': 12},
               'tickfont': {'size': 9},
        },
        yaxis={'title': 'Oil Production', 'color': 'white',
               'titlefont': {'size': 12},
               'tickfont': {'size': 9},
               'tickvals': y_tickvals,
               'ticktext': y_ticktext,
               'dtick': 1000,
               'range': [0, max_range_oil]
        },
        hovermode='closest',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000',
        legend={'font': {'size': 10}, 'traceorder': 'normal'},
        margin=dict(l=50, r=50, b=50, t=30),  # Eliminar márgenes
    )

    oil_graph = dcc.Graph(
        id='oil-production-graph',
        config={'displayModeBar': True},
        style={
            'display': 'inline-block',
            'backgroundColor': '#000000',
            'width': '400px',
            'height': '300px',
            'color': 'white',
            'align-items':'center',
        },
        figure={
            'data': traces_oil,
            'layout': layout_oil
        }
    )

    return oil_graph

def gas_production(well_production_data):
    well_production_data_sorted = well_production_data.sort_values(by=['UWI', 'Mes'])
    well_production_data_sorted['YearMonth'] = well_production_data_sorted['Año'].astype(str) + '-' + well_production_data_sorted['Mes'].astype(str)
    gas_data = well_production_data_sorted[['UWI', 'YearMonth', 'Suma_Gas', 'Well_Id']]

    custom_colors_gas = {
        'D0A25FCC-4989-4D49-86C1-CAA92F1B3001': 'rgba(67, 160, 71, 0.6)',  # Color verde
        'D0A25FCC-4989-4D49-86C1-CDA92F1B3002': 'rgba(188, 170, 164, 0.6)',  # Color gris
        'D0A25FCC-4989-4D49-86C1-CDA92F1B3004': 'rgba(0, 204, 255, 0.2)',  # Color azul
        'D0A25FCC-4989-4D49-86C1-CDA92F1B3005': 'rgba(183, 28, 28, 0.4)',  # Color rojo
        'D0A25FCC-4989-4D49-86C1-CKA92F1B3006': 'rgba(255, 87, 34, 0.6)',  # Color naranja
        'D0A25FCC-4989-4D49-86C1-CPA92F1B3007': 'rgba(186, 104, 200, 0.2)',  # Color morado
        'D0A25FCC-4989-4D49-86C1-CDA92F1B3008': 'rgba(255, 255, 157, 0.5)',  # Color amarillo
        'D0A25FCC-4989-4D49-86C1-CMN92F1B3009': 'rgba(204, 153, 255, 0.2)', # color lila
        '54E7CE87-3AC7-49B2-B794-5730BE7C97010': 'rgba(102, 255, 204, 0.6)', # color celeste
        '971F0184-A90B-4029-99E4-F81C5FAB82012': 'rgba(204, 255, 204, 0.2)', # ccolor menta
        'F95DACDF-1568-4F15-95BF-DE04D3D26013': 'rgba(255, 255, 204, 0.2)', # color piel claro
        'D0A25FCC-4989-4D49-86C1-JKT92F1B3014': 'rgba(255, 255, 153, 0.2)', # color amarillo claro pastel
        'D0A25FCC-4989-4D49-86C1-CDF92F1B3015': 'rgba(255, 153, 204, 0.6)', # color rosado
        'D0A25FCC-4989-4D49-86C1-CAA92F1B3016': 'rgba(153, 204, 102, 0.4)', # color guayabo
        'D0A25FCC-4989-4D49-86C1-CDA92F1B3017': 'rgba(153, 153, 204, 1)', # color azul morado
        'D0A25FCC-4989-4D49-86C1-CDA92F1B3018': 'rgba(97, 97, 97, 0.6)', # color gris oscuro
        'D0A25FCC-4989-4D49-86C1-CDY92F1B3019': 'rgba(141, 110, 99, 0.6)' # color marrón claro
    }

    traces_gas = []

    for well_id, data in gas_data.groupby('Well_Id'):
        uwi = data['UWI'].iloc[0]

        trace_gas = go.Scatter(
            x=data['YearMonth'],
            y=data['Suma_Gas'],
            mode='lines+markers',
            line=dict(color=custom_colors_gas.get(well_id, 'rgba(0, 0, 0, 1)')),
            name=str(uwi),
            fill='tozeroy',
            fillcolor=custom_colors_gas.get(well_id, 'rgba(0, 0, 1, 1)')
        )
        traces_gas.append(trace_gas)

    all_year_months = sorted(well_production_data_sorted['YearMonth'].unique())

    xaxis_labels = [format_month_year(year_month) for year_month in all_year_months]

    max_gas_production = well_production_data_sorted['Suma_Gas'].max()
    max_range_gas = 1000 * ((int(max_gas_production) // 1000) + 1)

    y_tickvals = [0]
    y_ticktext = ['0']
    for i in range(1000, max_range_gas + 1, 1000):
        y_tickvals.append(i)
        y_ticktext.append(f'{i / 1000:.0f}K')

    layout_gas = go.Layout(
        xaxis={'title': 'Month-Year', 'color': 'white', 'tickvals': all_year_months, 'ticktext': xaxis_labels,
               'titlefont': {'size': 12},
               'tickfont': {'size': 9},
        },
        yaxis={'title': 'Gas Production', 'color': 'white',
               'titlefont': {'size': 12},
               'tickfont': {'size': 9},
               'tickvals': y_tickvals,
               'ticktext': y_ticktext,
               'dtick': 1000,
               'range': [0, max_range_gas]
        },
        hovermode='closest',
        plot_bgcolor='#000000',
        paper_bgcolor='#000000',
        legend={'font': {'size': 10}, 'traceorder': 'normal'},
        margin=dict(l=50, r=50, b=50, t=30),  # Eliminar márgenes
    )

    gas_graph = dcc.Graph(
        id='gas-production-graph',
        config={'displayModeBar': True},
        style={
            'display': 'inline-block',
            'backgroundColor': '#000000',
            'width': '400px',
            'height': '300px',
            'color': 'white',
            'align-items': 'center',
        },
        figure={
            'data': traces_gas,
            'layout': layout_gas
        }
    )

    return gas_graph

# Llama a oil_production() y gas_production() con well_production_data como argumento
oil_production_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Oil Production",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        oil_production(well_production_data),  # Pasa well_production_data como argumento
    ],
)

# Llama a gas_production() con well_production_data como argumento
gas_production_card = html.Div(
    style={'height': '350px', 'width': '100%', 'textAlign': 'center', 'border-radius': '10px', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Gas Production",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        gas_production(well_production_data),  # Pasa well_production_data como argumento
    ],
)


# Función para formatear números en notación K (miles) y M (millones)
def format_number(number):
    if abs(number) >= 1e6:
        return f"{number / 1e6:.2f} M"
    elif abs(number) >= 1e3:
        return f"{number / 1e3:.2f} K"
    else:
        return f"{number:.2f}"

# Tarjetas de datos
wells_card = generate_data_card("Producing Wells", f"{numero_de_pozos}", '#00CCFF')
total_oil_card = generate_data_card("Total Oil", format_number(df_var_3['Oil'].sum()), '#FF6633')
total_water_card = generate_data_card("Total Water", format_number(df_var_3['Water'].sum()), '#0066FF')
total_gas_card = generate_data_card("Total Gas", format_number(df_var_3['Gas'].sum()), '#663366')
total_hours_card = generate_data_card("Total Hours", format_number(df_var_3['Hours'].sum()), '#009966')
average_caudal_card = generate_data_card("Average Caudal", format_number(df_var_2['Caudal'].mean()), ' #CC9900')

total_gas = df_var_3['Gas'].sum()  
total_oil = df_var_3['Oil'].sum()  
total_water = df_var_3['Water'].sum()

# Calcula las proporciones
proporcion_gas = total_gas / (total_gas + total_oil + total_water) * 100
proporcion_oil = total_oil / (total_gas + total_oil + total_water) * 100
proporcion_water = total_water / (total_gas + total_oil + total_water) * 100

# Crea un gráfico de torta de proporción de todos los campos

pie_card = html.Div(
    style={'height': '230px', 'textAlign': 'center', 'border-radius':'7px', 'box-shadow': '0px 0px 5px 2px rgba(255, 255, 255, 0.2)', 'backgroundColor': '#131313'},
    children=[
        html.Div(
            "Oil/Gas/Water Proportion",
            style={
                'paddingTop': '10px',
                'textAlign': 'center',
                'align-content': 'center',
                'color': 'white',
                'borderBottom': '1px solid white',
                'paddingBottom': '10px',
                'fontWeight': 'bold',
            },
        ),
        dcc.Graph(
            id='pie-chart',
            config={'displayModeBar': True},
            style={'height': '170px', 'paddingTop': '10px'},  # Ajusta la altura y el espaciado interno
            figure={
                'data': [
                    go.Pie(
                        labels=['Gas', 'Oil', 'Water'],
                        values=[proporcion_gas, proporcion_oil, proporcion_water],
                        hoverinfo='label+percent',
                        textinfo='percent',
                        textfont=dict(color='black', size=8, family='Lato'),  # Personalizar fuente del porcentaje
                        insidetextfont=dict(color='black', size=14, family='Lato'),  # Personalizar fuente de las etiquetas
                        marker=dict(colors=['#663366', '#FF6633']),
                        hole=0.3,
                    )
                ],
                'layout': go.Layout(
                    plot_bgcolor='#131313',
                    paper_bgcolor='#131313',
                    margin={'t': 0, 'b': 0, 'l': 0.5, 'r': 0},  # Ajusta el margen
                ),
            },
        ),
    ],
)
# ---------------------------------------------------------------------------------------------------------------------------------------------------
# SECCION DEL LAYOUT DE LA APP
# ---------------------------------------------------------------------------------------------------------------------------------------------------

app.layout = html.Div(style={'fontFamily': 'Lato', 'display': 'flex', 'flexDirection': 'column'}, children=[
    html.Div(style={'display': 'flex', 'backgroundColor' : '#131313', 'border-radius':'7px'}, children=[
        html.Img(src='assets/spe_logo_dim.png', style={'width': '5%', 'align-self': 'flex-start', 'margin-top': '0px', 'margin-bottom': '0px'}),
        html.H1("PRODUCTION KPI's", style={'color': 'white',
                'alignItems': 'center',
                'fontWeight': 'bold',
                'flex-grow': '1',
                'fontSize': '30px',
                'margin-left': '40%',
            }),
        html.Div(f'Last Updated: {formatted_time} (Colombia Time)', style={'color': '#424242', 'margin': '1px 0', 'align-items': 'top', 'fontSize': '14px', 'fontWeight': 'bold'}),
    ]),

    html.Div(style={'display': 'flex'}, children=[

        #Primera columna

        # Barra de control
        # Primera columna
        html.Div(style={'width': '17%', 'margin-top': '0px'}, children=[
                html.Div(style={'backgroundColor': '#131313', 'border-radius': '7px', 'max-height': '50vh'}, children=[
                    html.H3("Filters", style={'textAlign': 'center', 'color': 'white', 'borderBottom': '1px solid white', 'paddingTop': '10px', 'paddingBottom': '10px'}),
                    # Por ejemplo, puedo agregar un dropdown para seleccionar opciones
                    dcc.Dropdown(
                        id='dropdown-option',
                        options=[
                            {'label': 'Month', 'value': 'Month'},
                            {'label': 'Day', 'value': 'Month'},
                            {'label': 'Year', 'value': 'Year'},
                            # Agrego más opciones según mis necesidades más adelante
                        ],
                        value='Month',  # Valor por defecto
                        style={'margin-bottom': '10px'}
                    ),
                    # Otros componentes dcc aquí (botones, sliders, etc.)

                    dcc.Slider(3, 12, 3, value=12),

                    # Checkbox 1
                    dcc.Checklist(
                        options=[
                            {'label': 'Total', 'value': 'Total'},
                            {'label': 'Versus', 'value': 'Versus'},
                            {'label': 'Average', 'value': 'Average'},
                        ],
                        value=['Total'],
                        style={'textAlign': 'center', 'color': 'white', 'margin-top': '15px', 'columnCount': 3, 'margin-bottom': '15px'}
                    ),

                    # Checkbox 2
                    dcc.Checklist(
                        options=[
                            {'label': 'Field SPE-2', 'value': 'Field SPE-2'},
                            {'label': 'Field SPE-3', 'value': 'Field SPE-3'},
                            {'label': 'Field SPE-4', 'value': 'Field SPE-4'},
                            {'label': 'Field SPE-5', 'value': 'Field SPE-5'},
                            {'label': 'Field SPE-6', 'value': 'Field SPE-6'},
                        ],
                        value=['Field SPE-2', 'Field SPE-3', 'Field SPE-4', 'Field SPE-5', 'Field SPE-6'],
                        style={'textAlign': 'center', 'color': 'white', 'margin-top': '15px', 'columnCount': 2, 'margin-bottom': '15px'}
                    ),

                    # Dropdown pero múltiple
                    dcc.Dropdown(
                        ['BES', 'GAS LIFT', 'BME', 'PCP'], ['BES', 'GAS LIFT', 'BME', 'PCP'], style={'backgroundColor': '#000000', 'margin-top': '5px'},
                        multi=True
                    ),

                    # Botón final
                    html.Div(dcc.Input(id='input-box', type='text'), style={'margin-top': '15px'}),
                    html.Button('Submit', id='button-example-1'),
                    html.Div(id='output-container-button', children='Enter a value and press submit', style={'color': 'white'}),
                ]),

                
                # Agregar el gráfico de torta dentro de la misma columna pero separado
                html.Div(style={'margin-top': '30px'}, children=[
                    pie_card,
                ]),

                html.Div(style={'margin-top': '30px'}, children=[
                    Barrel_price_realtime_card,
                ]),               
        ]),

        #Segunda columna
        html.Div(style={'margin-left': '30px', 'display': 'flex', 'align-content': 'center', 'flex-direction': 'column', 'margin-top': '20px'}, children=[
            # Primera fila de gráficas
            html.Div(style={'display': 'flex'}, children=[
                wells_location_card,  # Llama a la función para crear el mapa
                html.Div(style={'margin-left': '30px'}, children=[
                    oil_production_card,
                ]),
                html.Div(style={'margin-left': '30px'}, children=[
                    gas_production_card,
                ]),
            ]),

            # Segunda fila de gráficas
            html.Div(style={'display': 'flex', 'margin-top': '30px'}, children=[
                html.Div(style={'width': '50%', 'align': 'center'}, children=[
                    wells_depth_card  # Agrega la tarjeta wells_depth_card aquí
                ]),
                html.Div(style={'margin-left': '30px'}, children=[
                    wc_wor_card,
                ]),
                html.Div(style={'margin-left': '30px'}, children=[
                    bopd_bwpd_card,
                ]),
            ]),

            # Tercera fila de gráficas
            html.Div(style={'display': 'flex', 'margin-top': '30px'}, children=[
                html.Div(children=[
                    presion_caudal_card,  # Agrega la tarjeta wells_depth_card aquí
                ]),
                html.Div(style={'margin-left': '30px'}, children=[
                    freq_caudal_card,  # Agrega la tarjeta wells_depth_card aquí
                ]),
            ]),

            # Cuarta fila de gráficas
            html.Div(style={'display': 'flex'}, children=[
            ]),
        ]),

        # Tercera columna
        html.Div(
            style={'width': '13%', 'margin-top': '20px', 'margin-left': '30px'},
            children=[
                wells_card,
                total_oil_card,
                total_water_card,
                total_gas_card,
                total_hours_card,
                average_caudal_card
            ],
        ),
    ]),
    html.Footer(children='Julieth Muñoz, Yulitza Parada, Silvio Pacheco (Geohallitians 2023)©', style={'textAlign': 'center', 'color': '#424242', 'align-items': 'end', 'margin': '0'})
])

if __name__ == '__main__':
    app.run_server(debug=True)
