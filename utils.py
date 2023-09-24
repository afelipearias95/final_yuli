# ---------------------------------------------------------------------------------------------------------------------------------------------------
# Este modulo es para funciones reutilizables del main o dasboard principal
# ---------------------------------------------------------------------------------------------------------------------------------------------------

import mysql.connector
from datetime import datetime
from dash import html

def get_database_connection():
    db_config = {
        "host": "104.196.38.12",
        "user": "root",
        "password": "z8]$>V;XU]@c,G}*",
        "database": "tablero_geohallitians"
    }
    
    try:
        conexion = mysql.connector.connect(**db_config)
        database = db_config["database"]
        print(f"Conexión exitosa a la Base de Datos '{database}'!")
        return conexion
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None

def obtener_numero_de_pozos(conexion):
    if conexion:
        # Consulta SQL para contar los pozos en la tabla wells_master
        query_pozos = "SELECT COUNT(DISTINCT UWI) AS total_uwi_unicos FROM tablero_geohallitians.wells_master_updated"

        # Ejecuta la consulta
        cursor = conexion.cursor()
        cursor.execute(query_pozos)
    
        # Obtiene el resultado
        resultado = cursor.fetchone()[0]
    
        return resultado
    else:
        return 0

def generate_data_card(title, data, color):
    return html.Div(
        style={'height': '110px', 'textAlign': 'center', 'align-content': 'right', 'align-items': 'right', 'border-radius':'7px', 'box-shadow': '0px 0px 5px 2px rgba(255, 255, 255, 0.2)', 'backgroundColor': '#131313', 'margin-bottom': '30px'},
        children=[
            html.Div(
                title,
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
                data,
                style={'paddingTop': '7px', 'fontSize': '300%', 'color': color, 'textAlign': 'center'},
            ),
        ],
    )

def get_last_updated_time(timezone):
    current_time = datetime.now(timezone)
    return current_time.strftime('%Y-%m-%d %H:%M:%S')
